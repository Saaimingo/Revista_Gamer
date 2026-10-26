"""Official Sign in with ChatGPT (SIWC) OAuth and Responses adapter.

This module uses only the public OAuth and Responses endpoints documented by
OpenAI. It never reads browser profiles, ChatGPT cookies, or API keys.
"""

from __future__ import annotations

import base64
import ctypes
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from .orchestration import AgentProfile, AgentTask, TaskExecutionContext, TaskFailure
from .db import stable_hash


ISSUER = "https://auth.openai.com"
AUTHORIZATION_ENDPOINT = f"{ISSUER}/api/accounts/authorize"
TOKEN_ENDPOINT = f"{ISSUER}/api/accounts/oauth/token"
JWKS_URI = f"{ISSUER}/.well-known/jwks.json"
API_BASE = "https://api.openai.com/v1"
RESOURCE = API_BASE
REQUESTED_SCOPES = "openid profile email offline_access resource.invoke chatgpt.tokens.use.direct"
DIRECT_USAGE_SCOPE = "chatgpt.tokens.use.direct"
DYNAMIC_CLIENT_ID = "dynamic_agent_client"
AGENT_NAME = "Revista Gamer Motor Editorial"
CALLBACK_PATH = "/auth/callback"
TOKEN_FILE_NAME = "siwc-credentials.bin"
HOST_ID_FILE_NAME = "siwc-host-id.txt"

SIWC_PROBE_TASK_TYPE = "siwc.integration_probe"
SIWC_REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})
SIWC_PROBE_PROFILE = AgentProfile(
    profile_id="internal-siwc-integration-probe",
    version="1.0.0",
    instructions=(
        "Perfil técnico temporário para teste de integração. Não representa persona pública. "
        "Não produza conteúdo editorial nem alegue fatos reais. Responda somente com o JSON "
        '{"status":"ok","message":"teste de integração aprovado"}.'
    ),
)
SIWC_PROBE_PROMPT = (
    "Este é um teste técnico fictício da integração. Responda exatamente com o JSON "
    '{"status":"ok","message":"teste de integração aprovado"}. '
    "Não escreva matéria, não cite fontes e não acrescente texto fora do JSON."
)


class SIWCError(Exception):
    """Safe-to-display SIWC error; never includes credential or response bodies."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class AuthorizationAttempt:
    client_id: str
    host_id: str
    redirect_uri: str
    state: str
    nonce: str
    code_verifier: str
    code_challenge: str
    is_new_registration: bool

    def authorization_url(self) -> str:
        query = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": REQUESTED_SCOPES,
            "resource": RESOURCE,
            "state": self.state,
            "nonce": self.nonce,
            "code_challenge_method": "S256",
            "code_challenge": self.code_challenge,
            "ext_agent_host_id": self.host_id,
        }
        if self.is_new_registration:
            query["agent_name_hint"] = AGENT_NAME
        return f"{AUTHORIZATION_ENDPOINT}?{urllib.parse.urlencode(query)}"


class CredentialStore:
    """DPAPI-protected on Windows; owner-only local file on Linux."""

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else self.default_path()
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")
        self.host_id_path = self.path.with_name(HOST_ID_FILE_NAME)
        self._thread_lock = threading.RLock()

    @staticmethod
    def default_path() -> Path:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                raise SIWCError("local_storage_unavailable", "LOCALAPPDATA não está definido.")
            return Path(base) / "RevistaGamer" / TOKEN_FILE_NAME
        if os.name == "posix":
            base = os.environ.get("XDG_DATA_HOME")
            data_home = Path(base) if base else Path.home() / ".local" / "share"
            return data_home / "revista-gamer" / TOKEN_FILE_NAME
        raise SIWCError("platform_unsupported", "Armazenamento de credenciais não suportado neste sistema.")

    @contextmanager
    def lock(self) -> Iterator[None]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            self.path.parent.chmod(0o700)
        with self._thread_lock:
            descriptor = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
            locked = False
            try:
                if os.name == "nt":
                    import msvcrt
                    if os.fstat(descriptor).st_size == 0:
                        os.write(descriptor, b"\0")
                        os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_LOCK, 1)
                    locked = True
                elif os.name == "posix":
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_EX)
                    locked = True
                yield
            finally:
                if locked and os.name == "nt":
                    import msvcrt
                    os.lseek(descriptor, 0, os.SEEK_SET)
                    msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
                elif locked and os.name == "posix":
                    import fcntl
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)

    def _encode(self, content: bytes) -> bytes:
        if os.name == "nt":
            return b"RGSIWC1" + _dpapi_protect(content)
        if os.name == "posix":
            return b"RGSIWCP" + content
        raise SIWCError("platform_unsupported", "Armazenamento de credenciais não suportado.")

    def _decode(self, content: bytes) -> bytes:
        if content.startswith(b"RGSIWC1") and os.name == "nt":
            return _dpapi_unprotect(content[7:])
        if content.startswith(b"RGSIWCP") and os.name == "posix":
            return content[7:]
        raise SIWCError("credential_file_invalid", "Arquivo local de credenciais inválido para este sistema.")

    def load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        if os.name == "posix":
            self.path.parent.chmod(0o700)
            os.chmod(self.path, 0o600)
        try:
            raw = self._decode(self.path.read_bytes())
            value = json.loads(raw.decode("utf-8"))
        except SIWCError:
            raise
        except Exception as error:
            raise SIWCError("credential_file_invalid", "Não foi possível ler as credenciais locais.") from error
        if not isinstance(value, dict):
            raise SIWCError("credential_file_invalid", "Registro local de credenciais inválido.")
        return value

    def save(self, credentials: Mapping[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name == "posix":
            self.path.parent.chmod(0o700)
        payload = self._encode(json.dumps(
            dict(credentials), ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8"))
        temporary = self.path.with_name(self.path.name + ".tmp")
        descriptor = os.open(temporary, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        try:
            with os.fdopen(descriptor, "wb") as output:
                descriptor = -1
                output.write(payload)
                output.flush()
                os.fsync(output.fileno())
            if os.name == "posix":
                os.chmod(temporary, 0o600)
            os.replace(temporary, self.path)
            if os.name == "posix":
                os.chmod(self.path, 0o600)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if temporary.exists():
                temporary.unlink()

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()

    def get_or_create_host_id(self) -> str:
        self.host_id_path.parent.mkdir(parents=True, exist_ok=True)
        if self.host_id_path.exists():
            host_id = self.host_id_path.read_text(encoding="ascii").strip()
            if host_id.startswith("urn:uuid:"):
                uuid.UUID(host_id.removeprefix("urn:uuid:"))
                return host_id
            raise SIWCError("host_id_invalid", "Identificador local de host inválido.")
        host_id = f"urn:uuid:{uuid.uuid4()}"
        temporary = self.host_id_path.with_name(self.host_id_path.name + ".tmp")
        temporary.write_text(host_id + "\n", encoding="ascii")
        if os.name == "posix":
            os.chmod(temporary, 0o600)
        os.replace(temporary, self.host_id_path)
        return host_id


def _dpapi_protect(plaintext: bytes) -> bytes:
    if os.name != "nt":
        raise SIWCError("platform_unsupported", "DPAPI existe somente no Windows.")
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    source_buffer = ctypes.create_string_buffer(plaintext)
    source = DataBlob(len(plaintext), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = DataBlob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(DataBlob), wintypes.LPCWSTR, ctypes.c_void_p, ctypes.c_void_p,
        ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    if not crypt32.CryptProtectData(ctypes.byref(source), "Revista Gamer SIWC", None, None, None, 1, ctypes.byref(output)):
        raise SIWCError("dpapi_protect_failed", "O Windows não conseguiu proteger as credenciais locais.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def _dpapi_unprotect(ciphertext: bytes) -> bytes:
    if os.name != "nt":
        raise SIWCError("platform_unsupported", "DPAPI existe somente no Windows.")
    from ctypes import wintypes

    class DataBlob(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

    source_buffer = ctypes.create_string_buffer(ciphertext)
    source = DataBlob(len(ciphertext), ctypes.cast(source_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    output = DataBlob()
    crypt32 = ctypes.windll.crypt32
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(DataBlob), ctypes.POINTER(wintypes.LPWSTR), ctypes.c_void_p,
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(DataBlob),
    ]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    if not crypt32.CryptUnprotectData(ctypes.byref(source), None, None, None, None, 1, ctypes.byref(output)):
        raise SIWCError("dpapi_unprotect_failed", "O Windows não conseguiu abrir as credenciais protegidas.")
    try:
        return ctypes.string_at(output.pbData, output.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(output.pbData)


def create_authorization_attempt(
    *,
    client_id: str,
    host_id: str,
    redirect_uri: str,
    is_new_registration: bool,
) -> AuthorizationAttempt:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode("ascii").rstrip("=")
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).decode("ascii").rstrip("=")
    return AuthorizationAttempt(
        client_id=client_id, host_id=host_id, redirect_uri=redirect_uri,
        state=secrets.token_urlsafe(32), nonce=secrets.token_urlsafe(32),
        code_verifier=verifier, code_challenge=challenge,
        is_new_registration=is_new_registration,
    )


class _CallbackHandler(BaseHTTPRequestHandler):
    attempt: AuthorizationAttempt
    callback_result: dict[str, str] | None = None
    callback_event: threading.Event

    def do_GET(self) -> None:  # noqa: N802 - stdlib handler API
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        if parsed.path != CALLBACK_PATH:
            self.send_error(404)
            return
        state = params.get("state", [""])[0]
        if not hmac.compare_digest(state, self.attempt.state):
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"State de autorizacao invalido. Volte ao terminal e tente novamente.")
            return
        result = {key: values[0] for key, values in params.items() if values}
        type(self).callback_result = result
        type(self).callback_event.set()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            "<!doctype html><meta charset='utf-8'><title>Revista Gamer</title>"
            "<p>Autorização recebida. Volte ao terminal para concluir a validação.</p>".encode("utf-8")
        )

    def log_message(self, format: str, *args: Any) -> None:
        # Query strings may contain authorization codes; never log callback URLs.
        return


def _post_form(url: str, fields: Mapping[str, str], *, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(dict(fields)).encode("ascii"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        code = f"oauth_http_{error.code}"
        raise SIWCError(code, "O endpoint oficial de autenticação recusou a operação.") from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise SIWCError("oauth_network_error", "Não foi possível conectar ao endpoint oficial de autenticação.") from None
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise SIWCError("oauth_invalid_response", "O endpoint de autenticação retornou resposta inválida.") from None
    if not isinstance(payload, dict):
        raise SIWCError("oauth_invalid_response", "O endpoint de autenticação retornou resposta inválida.")
    return payload


def _validate_id_token(id_token: str, client_id: str, nonce: str) -> dict[str, Any]:
    try:
        import jwt  # PyJWT[crypto] is an optional SIWC dependency.
    except ImportError as error:
        raise SIWCError(
            "siwc_dependency_missing",
            "Instale as dependências opcionais de SIWC com: py -m pip install -r requirements-siwc.txt",
        ) from error
    try:
        header = jwt.get_unverified_header(id_token)
        algorithm = header.get("alg")
        if algorithm not in {"RS256", "ES256"}:
            raise SIWCError("id_token_algorithm_invalid", "Algoritmo de assinatura OIDC não aceito.")
        key = jwt.PyJWKClient(JWKS_URI, timeout=15).get_signing_key_from_jwt(id_token).key
        claims = jwt.decode(
            id_token,
            key=key,
            algorithms=[algorithm],
            audience=client_id,
            issuer=ISSUER,
            leeway=5,
            options={"require": ["exp", "iss", "aud", "sub", "nonce", "iat"]},
        )
        if not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
            raise SIWCError("id_token_nonce_invalid", "O nonce do ID token não corresponde à autorização.")
        return claims
    except SIWCError:
        raise
    except Exception as error:
        # Do not surface raw JWT/JWKS exceptions; they can contain credential fragments.
        raise SIWCError("id_token_invalid", f"O ID token não passou na validação ({type(error).__name__}).") from None


class _CallbackListener:
    def __init__(self) -> None:
        self.handler = type("CallbackHandler", (_CallbackHandler,), {})
        self.handler.callback_result = None
        self.handler.callback_event = threading.Event()
        self.server = HTTPServer(("127.0.0.1", 0), self.handler)
        self.server.timeout = 0.5
        self.redirect_uri = f"http://127.0.0.1:{self.server.server_port}{CALLBACK_PATH}"

    def set_attempt(self, attempt: AuthorizationAttempt) -> None:
        self.handler.attempt = attempt

    def wait(self, timeout_seconds: int) -> dict[str, str]:
        deadline = time.monotonic() + timeout_seconds
        try:
            while not self.handler.callback_event.is_set() and time.monotonic() < deadline:
                self.server.handle_request()
        finally:
            self.server.server_close()
        if not self.handler.callback_event.is_set() or self.handler.callback_result is None:
            raise SIWCError("login_timeout", "O login não foi concluído dentro do tempo limite.")
        result = self.handler.callback_result
        if result.get("error"):
            raise SIWCError("login_denied", "A autorização foi cancelada ou recusada no navegador.")
        return result


def begin_login(
    credential_store: CredentialStore,
    *,
    show_authorization_url: Callable[[str], None],
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    if timeout_seconds < 1:
        raise ValueError("O tempo limite do login deve ser positivo.")
    host_id = credential_store.get_or_create_host_id()
    with credential_store.lock():
        existing = credential_store.load()
    client_id = str(existing["client_id"]) if existing else DYNAMIC_CLIENT_ID
    is_new = existing is None
    listener = _CallbackListener()
    redirect_uri = listener.redirect_uri
    attempt = create_authorization_attempt(
        client_id=client_id, host_id=host_id, redirect_uri=redirect_uri,
        is_new_registration=is_new,
    )
    listener.set_attempt(attempt)
    # The callback listener is already bound before the user opens the authorization URL.
    try:
        show_authorization_url(attempt.authorization_url())
        callback = listener.wait(timeout_seconds)
    except Exception:
        listener.server.server_close()
        raise
    returned_client_id = callback.get("client_id") or client_id
    if is_new and (not returned_client_id or returned_client_id == DYNAMIC_CLIENT_ID):
        raise SIWCError("dynamic_registration_incomplete", "O OpenAI não retornou um client_id emitido.")
    if is_new and not returned_client_id.startswith("oaiapp_"):
        raise SIWCError("dynamic_client_id_invalid", "O client_id emitido não tem o formato oficial esperado.")
    if not is_new and returned_client_id != client_id:
        raise SIWCError("client_id_mismatch", "O client_id retornado não corresponde à conta selecionada.")
    code = callback.get("code")
    if not code:
        raise SIWCError("authorization_code_missing", "O callback não trouxe um código de autorização.")
    token_payload = _post_form(TOKEN_ENDPOINT, {
        "grant_type": "authorization_code",
        "client_id": returned_client_id,
        "code": code,
        "code_verifier": attempt.code_verifier,
        "redirect_uri": redirect_uri,
        "resource": RESOURCE,
    })
    granted_scopes = set(str(token_payload.get("scope", "")).split())
    if DIRECT_USAGE_SCOPE not in granted_scopes:
        raise SIWCError("plan_scope_missing", "O consentimento não incluiu acesso direto ao plano ChatGPT.")
    if "offline_access" not in granted_scopes:
        raise SIWCError("offline_access_scope_missing", "O consentimento não incluiu renovação da sessão para retomada.")
    if not token_payload.get("refresh_token"):
        raise SIWCError("refresh_token_missing", "A sessão não recebeu refresh token para retomada durável.")
    if str(token_payload.get("token_type", "Bearer")).casefold() != "bearer":
        raise SIWCError("token_type_unsupported", "A autenticação não retornou token bearer.")
    id_token = str(token_payload.get("id_token", ""))
    if not id_token:
        raise SIWCError("id_token_missing", "A autenticação não retornou um ID token.")
    claims = _validate_id_token(id_token, returned_client_id, attempt.nonce)
    subject = str(claims.get("sub", ""))
    if not subject:
        raise SIWCError("id_token_subject_missing", "O ID token não contém identidade de conta validada.")
    if existing and subject != existing.get("subject"):
        raise SIWCError("account_mismatch", "A conta validada difere da conta local selecionada.")
    credential_record = {
        "issuer": ISSUER,
        "subject": subject,
        "client_id": returned_client_id,
        "host_id": host_id,
        "id_token": id_token,
        "access_token": str(token_payload.get("access_token", "")),
        "refresh_token": str(token_payload["refresh_token"]),
        "token_type": str(token_payload.get("token_type", "Bearer")),
        "expires_at": int(time.time()) + int(token_payload.get("expires_in", 3600)),
        "scopes": sorted(granted_scopes),
    }
    if not credential_record["access_token"]:
        raise SIWCError("access_token_missing", "A autenticação não retornou access token.")
    with credential_store.lock():
        credential_store.save(credential_record)
    return {
        "authenticated": True,
        "client_id_suffix": returned_client_id[-8:],
        "granted_direct_usage": True,
        "host_id": host_id,
    }


class SIWCClient:
    def __init__(self, credential_store: CredentialStore, *, timeout: int = 60):
        self.credential_store = credential_store
        self.timeout = timeout
        self.models_request_count = 0
        self.last_models_request_metrics: dict[str, Any] | None = None

    def _refresh(self, record: dict[str, Any]) -> dict[str, Any]:
        payload = _post_form(TOKEN_ENDPOINT, {
            "grant_type": "refresh_token",
            "client_id": record["client_id"],
            "refresh_token": record["refresh_token"],
            "resource": RESOURCE,
        })
        access_token = payload.get("access_token")
        refresh_token = payload.get("refresh_token") or record["refresh_token"]
        if not access_token or not refresh_token:
            raise SIWCError("refresh_invalid_response", "A renovação não retornou tokens válidos.")
        record["access_token"] = str(access_token)
        record["refresh_token"] = str(refresh_token)
        record["expires_at"] = int(time.time()) + int(payload.get("expires_in", 3600))
        if payload.get("scope"):
            record["scopes"] = sorted(set(str(payload["scope"]).split()))
        if DIRECT_USAGE_SCOPE not in record.get("scopes", []):
            raise SIWCError("plan_scope_missing", "A renovação não preservou o escopo de uso do plano.")
        return record

    def access_token(self) -> str:
        with self.credential_store.lock():
            record = self.credential_store.load()
            if not record:
                raise SIWCError("login_required", "Execute `motor_editorial siwc login` para autorizar a conta.")
            if DIRECT_USAGE_SCOPE not in record.get("scopes", []):
                raise SIWCError("plan_scope_missing", "A conta local não autorizou uso do plano ChatGPT.")
            if int(record.get("expires_at", 0)) <= int(time.time()) + 120:
                try:
                    record = self._refresh(record)
                except SIWCError:
                    raise
                except Exception:
                    raise SIWCError("refresh_failed", "Não foi possível renovar a sessão SIWC.") from None
                self.credential_store.save(record)
            return str(record["access_token"])

    def _request(self, method: str, url: str, *, body: bytes | None = None) -> bytes:
        token = self.access_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            raise _provider_http_failure(error.code, error.read(65536)) from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise SIWCError("provider_network_error", "Falha de rede ao acessar endpoint público do Responses API.") from None

    def models(self) -> list[dict[str, Any]]:
        self.models_request_count += 1
        started_at = datetime.now(timezone.utc)
        started_clock = time.monotonic()
        try:
            try:
                payload = json.loads(self._request("GET", f"{API_BASE}/models").decode("utf-8"))
            except TaskFailure as error:
                raise SIWCError(error.code, error.summary) from None
            except SIWCError:
                raise
            except (UnicodeDecodeError, json.JSONDecodeError):
                raise SIWCError("models_invalid_response", "O catálogo de modelos retornou formato inválido.") from None
            models = payload.get("models") if isinstance(payload, dict) else None
            if not isinstance(models, list):
                raise SIWCError("models_invalid_response", "O catálogo de modelos não contém a lista esperada.")
            return [
                {"slug": str(row.get("slug")), "display_name": str(row.get("display_name")),
                 "visibility": row.get("visibility")}
                for row in models if isinstance(row, dict) and row.get("slug")
            ]
        finally:
            completed_at = datetime.now(timezone.utc)
            self.last_models_request_metrics = {
                "request_number": self.models_request_count,
                "started_at": started_at.isoformat(timespec="milliseconds"),
                "completed_at": completed_at.isoformat(timespec="milliseconds"),
                "duration_ms": round((time.monotonic() - started_clock) * 1000, 3),
            }

    def _responses_json_stream(
        self,
        *,
        model: str,
        reasoning_effort: str,
        instructions: str,
        input_text: str,
        stage: str,
        context: TaskExecutionContext,
        response_sink: Callable[[str, Mapping[str, Any]], Mapping[str, Any] | None] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if reasoning_effort not in SIWC_REASONING_EFFORTS:
            raise SIWCError("reasoning_effort_invalid", "Nível de raciocínio não permitido para a chamada SIWC.")
        request_body = json.dumps({
            "model": model,
            "reasoning": {"effort": reasoning_effort},
            "instructions": instructions,
            "input": [{"role": "user", "content": input_text}],
            "store": False,
            "stream": True,
        }, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        token = self.access_token()
        started_at = time.monotonic()
        started_at_utc = datetime.now(timezone.utc)
        request = urllib.request.Request(
            f"{API_BASE}/responses", data=request_body,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            method="POST",
        )
        output: list[str] = []
        completed: dict[str, Any] | None = None
        completed_at_utc: datetime | None = None
        duration_ms: float | None = None

        def metadata_for(raw_text: str, output_state: str, *, error_code: str | None = None) -> dict[str, Any]:
            returned_model = completed.get("model") if isinstance(completed, dict) else None
            returned_reasoning = completed.get("reasoning") if isinstance(completed, dict) else None
            returned_effort = returned_reasoning.get("effort") if isinstance(returned_reasoning, dict) else None
            usage = completed.get("usage") if isinstance(completed, dict) else None
            result: dict[str, Any] = {
                "status": "ok" if output_state == "completed" else output_state,
                "provider": "openai-siwc", "endpoint": "/v1/responses", "stage": stage,
                "model_requested": model, "model": returned_model,
                "reasoning_effort_requested": reasoning_effort,
                "reasoning_effort": returned_effort,
                "request_started_at": started_at_utc.isoformat(timespec="milliseconds"),
                "completed_at": completed_at_utc.isoformat(timespec="milliseconds") if completed_at_utc else None,
                "duration_ms": duration_ms,
                "external_call_count": 1, "response_id": completed.get("id") if isinstance(completed, dict) else None,
                "usage": usage if isinstance(usage, dict) else None,
                "response_sha256": stable_hash(raw_text),
                "response_completed": completed is not None,
                "store": False, "stream": True,
                "output_state": output_state,
            }
            if error_code:
                result["error_code"] = error_code
            return result

        def preserve_response(raw_text: str, metadata: dict[str, Any]) -> None:
            if response_sink is None:
                return
            try:
                artifact = response_sink(raw_text, metadata)
            except Exception:
                raise TaskFailure(
                    "raw_response_persist_failed",
                    "A resposta SIWC recebida não pôde ser preservada no artefato local.",
                    blocked=True,
                ) from None
            if isinstance(artifact, Mapping):
                metadata["raw_artifact"] = dict(artifact)

        try:
            context.mark_external_started()
            response = urllib.request.urlopen(request, timeout=self.timeout)
            with response:
                for raw_line in response:
                    try:
                        line = raw_line.decode("utf-8").strip()
                    except UnicodeDecodeError:
                        raise TaskFailure(
                            "stream_invalid_utf8", "O stream SIWC contém uma linha que não é UTF-8 válido.",
                            uncertain=True,
                        ) from None
                    if not line.startswith("data:"):
                        continue
                    encoded = line[5:].strip()
                    if not encoded or encoded == "[DONE]":
                        continue
                    try:
                        event = json.loads(encoded)
                    except json.JSONDecodeError:
                        continue
                    event_type = event.get("type")
                    if event_type == "response.output_text.delta":
                        output.append(str(event.get("delta", "")))
                    elif event_type == "response.failed":
                        provider_error = (event.get("response") or {}).get("error") or {}
                        code = str(provider_error.get("code") or "response_failed")
                        raise _provider_code_failure(code, status=None)
                    elif event_type == "response.completed":
                        completed = event.get("response") or {}
                        completed_at_utc = datetime.now(timezone.utc)
                        duration_ms = round((time.monotonic() - started_at) * 1000, 3)
        except urllib.error.HTTPError as error:
            failure = _provider_http_failure(error.code, error.read(65536))
            raw_text = "".join(output)
            preserve_response(raw_text, metadata_for(raw_text, "provider_error", error_code=failure.code))
            raise failure from None
        except SIWCError as error:
            raw_text = "".join(output)
            preserve_response(raw_text, metadata_for(raw_text, "provider_error", error_code=error.code))
            raise
        except TaskFailure as failure:
            raw_text = "".join(output)
            output_state = "uncertain" if failure.uncertain else "provider_error"
            preserve_response(raw_text, metadata_for(raw_text, output_state, error_code=failure.code))
            raise
        except (urllib.error.URLError, TimeoutError, OSError):
            raw_text = "".join(output)
            preserve_response(raw_text, metadata_for(raw_text, "uncertain", error_code="transport_uncertain"))
            raise TaskFailure(
                "transport_uncertain",
                "A conexão caiu após o início da chamada; o resultado pode ter sido processado. Revisão humana necessária.",
                uncertain=True,
            ) from None
        if completed is None:
            raw_text = "".join(output)
            preserve_response(raw_text, metadata_for(raw_text, "incomplete", error_code="stream_incomplete"))
            raise TaskFailure(
                "stream_incomplete",
                "O stream terminou sem response.completed; não repetir automaticamente.",
                uncertain=True,
            )
        raw_text = "".join(output)
        metadata = metadata_for(raw_text, "completed")
        text = raw_text.strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            metadata["output_validation"] = "invalid_json"
            preserve_response(raw_text, metadata)
            raise TaskFailure("siwc_invalid_json_output", "A resposta SIWC não correspondeu a JSON válido.") from None
        if not isinstance(parsed, dict):
            metadata["output_validation"] = "not_object"
            preserve_response(raw_text, metadata)
            raise TaskFailure("siwc_invalid_json_output", "A resposta SIWC precisa ser um objeto JSON.")
        returned_model = completed.get("model")
        if not isinstance(returned_model, str) or not returned_model:
            metadata["output_validation"] = "model_unreported"
            preserve_response(raw_text, metadata)
            raise TaskFailure("siwc_model_unreported", "A resposta concluída não informou o modelo efetivo.")
        if returned_model != model and not returned_model.startswith(model + "-"):
            metadata["output_validation"] = "model_mismatch"
            preserve_response(raw_text, metadata)
            raise TaskFailure("siwc_model_mismatch", "O modelo efetivo retornado não corresponde ao solicitado.")
        returned_reasoning = completed.get("reasoning")
        returned_effort = returned_reasoning.get("effort") if isinstance(returned_reasoning, dict) else None
        if returned_effort != reasoning_effort:
            metadata["output_validation"] = "reasoning_effort_mismatch"
            preserve_response(raw_text, metadata)
            raise TaskFailure(
                "siwc_reasoning_effort_mismatch",
                "O esforço efetivo retornado não corresponde ao solicitado.",
            )
        if completed_at_utc is None or duration_ms is None:
            metadata["output_validation"] = "timing_missing"
            preserve_response(raw_text, metadata)
            raise TaskFailure("probe_timing_missing", "A conclusão SIWC não teve marcação local de tempo.")
        metadata["output_validation"] = "json_object"
        preserve_response(raw_text, metadata)
        return parsed, metadata

    def inference_stream(
        self, model: str, reasoning_effort: str, context: TaskExecutionContext,
    ) -> dict[str, Any]:
        parsed, metadata = self._responses_json_stream(
            model=model, reasoning_effort=reasoning_effort,
            instructions=SIWC_PROBE_PROFILE.instructions,
            input_text=SIWC_PROBE_PROMPT, stage="integration_probe", context=context,
        )
        expected = {"status": "ok", "message": "teste de integração aprovado"}
        if parsed != expected:
            raise TaskFailure("probe_unexpected_output", "A resposta real não passou na validação do teste técnico.")
        return {**metadata, "message": parsed["message"]}

    def editorial_stream(
        self,
        *,
        model: str,
        reasoning_effort: str,
        instructions: str,
        input_text: str,
        stage: str,
        context: TaskExecutionContext,
    ) -> dict[str, Any]:
        parsed, metadata = self._responses_json_stream(
            model=model, reasoning_effort=reasoning_effort,
            instructions=instructions, input_text=input_text,
            stage=stage, context=context,
        )
        return {**metadata, "structured_output": parsed}

    def editorial_stream_with_raw(
        self,
        *,
        model: str,
        reasoning_effort: str,
        instructions: str,
        input_text: str,
        stage: str,
        context: TaskExecutionContext,
        response_sink: Callable[[str, Mapping[str, Any]], Mapping[str, Any] | None],
    ) -> dict[str, Any]:
        """Run an editorial response while preserving its exact streamed text first."""
        parsed, metadata = self._responses_json_stream(
            model=model, reasoning_effort=reasoning_effort,
            instructions=instructions, input_text=input_text,
            stage=stage, context=context, response_sink=response_sink,
        )
        return {**metadata, "structured_output": parsed}


def _provider_http_failure(status: int, body: bytes) -> TaskFailure:
    code = ""
    try:
        decoded = json.loads(body.decode("utf-8"))
        error = decoded.get("error", {}) if isinstance(decoded, dict) else {}
        code = str(error.get("code") or "") if isinstance(error, dict) else ""
    except (UnicodeDecodeError, json.JSONDecodeError):
        pass
    return _provider_code_failure(code, status=status)


def _provider_code_failure(code: str, status: int | None) -> TaskFailure:
    if code == "subscription_sharing_usage_limit_exceeded" or status == 429:
        return TaskFailure(
            "usage_limit_exceeded",
            "Limite de uso do plano reportado; novas chamadas SIWC devem pausar. Consulte ChatGPT > Configurações > Uso.",
            blocked=True,
        )
    if code == "subscription_sharing_user_not_eligible":
        return TaskFailure(
            "user_not_eligible", "Esta conta, workspace ou política não está elegível para uso do plano via SIWC.",
            blocked=True,
        )
    if code in {"subscription_sharing_usage_unavailable", "subscription_sharing_user_unavailable"} or status == 503:
        return TaskFailure(
            "usage_unavailable", "Uso SIWC temporariamente indisponível; nova tentativa limitada será agendada.",
            retryable=True, retry_after_seconds=60,
        )
    if code == "subscription_sharing_unsupported_capability":
        return TaskFailure(
            "unsupported_capability", "A conta não aceita a capacidade enviada nesta chamada SIWC.",
        )
    if status in {401, 403}:
        return TaskFailure(
            "siwc_authorization_rejected", "A autorização SIWC foi recusada; autenticação ou política exige revisão.",
            blocked=True,
        )
    if status in {502, 504}:
        return TaskFailure(
            "provider_result_uncertain", "A resposta do provedor foi ambígua; revisão humana antes de repetir.",
            uncertain=True,
        )
    return TaskFailure(
        f"responses_http_{status or 'error'}",
        "O endpoint oficial de inferência recusou a chamada; consultar o código de erro documentado.",
    )


class SIWCExecutor:
    executor_id = "siwc-responses"

    def __init__(self, client: SIWCClient, *, model: str | None):
        if model is not None and not model.strip():
            raise ValueError("Informe um modelo listado para esta conta ChatGPT.")
        self.client = client
        self.model = model

    def execute(
        self,
        task: AgentTask,
        profile: AgentProfile,
        context: TaskExecutionContext,
    ) -> Mapping[str, Any]:
        if task.task_type != SIWC_PROBE_TASK_TYPE:
            raise TaskFailure(
                "siwc_task_not_approved",
                "Este executor aceita somente a prova técnica sintética de integração.",
                blocked=True,
            )
        if profile.content_hash != SIWC_PROBE_PROFILE.content_hash:
            raise TaskFailure(
                "siwc_profile_not_approved",
                "O executor SIWC aceita somente o perfil versionado de prova técnica.",
                blocked=True,
            )
        model = str(task.payload.get("model") or "").strip()
        if not model:
            raise TaskFailure(
                "model_missing", "A tarefa SIWC não tem um modelo escolhido no catálogo da conta.",
                blocked=True,
            )
        if self.model is not None and model != self.model:
            raise TaskFailure(
                "model_fallback_forbidden", "A tarefa solicitou um modelo diferente da configuração explícita.",
                blocked=True,
            )
        reasoning_effort = str(task.payload.get("reasoning_effort") or "").strip()
        if reasoning_effort not in SIWC_REASONING_EFFORTS:
            raise TaskFailure(
                "reasoning_effort_missing", "A tarefa SIWC precisa declarar explicitamente reasoning_effort.",
                blocked=True,
            )
        try:
            listed = {
                str(item["slug"]) for item in self.client.models()
                if item.get("visibility") == "list"
            }
            if model not in listed:
                raise TaskFailure(
                    "model_not_in_account_catalog",
                    "O modelo solicitado não aparece no catálogo atual desta conta SIWC.",
                    blocked=True,
                )
            return self.client.inference_stream(model, reasoning_effort, context)
        except TaskFailure:
            raise
        except SIWCError as error:
            raise TaskFailure(error.code, error.message, blocked=True) from None
