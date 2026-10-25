"""Policy-gated, bounded connectors for public Radar metadata.

Network access is opt-in per SourceProfile. Production requests use HTTPS,
explicit host allowlists, public-IP checks, and an IP pinned after DNS
resolution. The module does not use proxies, credentials, cookies, or automatic
redirect handling, and it never schedules polling by itself.
"""

from __future__ import annotations

import email.utils
import hashlib
import http.client
import ipaddress
import json
import re
import socket
import ssl
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from threading import Lock
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import parse_qsl, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from .orchestration import _assert_no_credentials
from .radar_policy import DomainQuotaGuard


class ConnectorPolicyError(ValueError):
    """Raised when a source or request fails an explicit safety policy."""


_SECRET_QUERY_KEYS = {
    "access_token", "refresh_token", "id_token", "token", "oauth_token", "api_key", "apikey", "key",
    "access_key", "client_secret", "secret", "signature", "sig", "auth", "credential", "credentials",
    "x_amz_credential", "x_amz_signature", "x_amz_security_token", "password", "cookie", "authorization",
    "code", "code_verifier", "authorization_code",
}
_REQUIRED_OPERATION = {
    "rss_atom": "feed_read",
    "public_api": "api_metadata_read",
    "public_html": "page_metadata_read",
}
_USER_AGENT = "RevistaGamerRadar/0.1 (public metadata; bounded requests)"
_ALLOWED_KINDS = set(_REQUIRED_OPERATION)
_REDIRECT_CODES = {301, 302, 303, 307, 308}
_RESPONSE_HEADER_ALLOWLIST = {"content-type", "etag", "last-modified", "retry-after", "location"}


def _nonempty(value: Any, name: str, *, max_length: int = 2_000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ConnectorPolicyError(f"{name} precisa ser texto não vazio de até {max_length} caracteres.")
    text = value.strip()
    try:
        _assert_no_credentials(text, name)
    except ValueError as error:
        raise ConnectorPolicyError(f"{name} parece conter credenciais.") from error
    return text


def _aware_datetime(value: Any, name: str, *, allow_date: bool = False) -> datetime | date:
    if not isinstance(value, str) or not value.strip():
        raise ConnectorPolicyError(f"{name} precisa ser data/hora ISO-8601.")
    text = value.strip()
    if allow_date and re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        try:
            return date.fromisoformat(text)
        except ValueError as error:
            raise ConnectorPolicyError(f"{name} precisa ser data ISO-8601 válida.") from error
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise ConnectorPolicyError(f"{name} precisa ser data/hora ISO-8601.") from error
    if parsed.tzinfo is None:
        raise ConnectorPolicyError(f"{name} precisa declarar fuso horário.")
    return parsed


def _safe_url_parts(url: str, *, allow_loopback_http: bool = False) -> tuple[Any, str, int]:
    if any(ord(character) < 32 or ord(character) == 127 for character in url):
        raise ConnectorPolicyError("URL contém caracteres de controle.")
    try:
        parts = urlsplit(url)
        host = (parts.hostname or "").rstrip(".").casefold()
        port = parts.port
    except ValueError as error:
        raise ConnectorPolicyError("URL inválida.") from error
    if not host or parts.username or parts.password or parts.fragment:
        raise ConnectorPolicyError("URL precisa omitir credenciais e fragmentos.")
    if any(key.casefold().replace("-", "_") in _SECRET_QUERY_KEYS for key, _ in parse_qsl(parts.query, keep_blank_values=True)):
        raise ConnectorPolicyError("URL contém parâmetro de credencial.")
    if parts.scheme == "https":
        port = 443 if port is None else port
        if port != 443:
            raise ConnectorPolicyError("Somente HTTPS na porta padrão 443 é permitido.")
    elif parts.scheme == "http" and allow_loopback_http:
        port = 80 if port is None else port
        try:
            address = ipaddress.ip_address(host)
        except ValueError as error:
            raise ConnectorPolicyError("HTTP de teste só aceita endereço IP loopback literal.") from error
        if not address.is_loopback:
            raise ConnectorPolicyError("HTTP sem TLS só é permitido para teste em loopback.")
    else:
        raise ConnectorPolicyError("Conector exige HTTPS; HTTP fica restrito ao servidor loopback de teste.")
    if not 1 <= port <= 65535:
        raise ConnectorPolicyError("Porta da URL inválida.")
    try:
        _assert_no_credentials(url, "url")
    except ValueError as error:
        raise ConnectorPolicyError("URL parece conter credenciais.") from error
    return parts, host, port


def _safe_public_reference_url(url: str) -> str | None:
    try:
        parts, host, _ = _safe_url_parts(url)
    except ConnectorPolicyError:
        return None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return url
    if not ip.is_global or ip.is_reserved or ip.is_private or ip.is_loopback:
        return None
    return url if parts.scheme == "https" else None


@dataclass(frozen=True)
class SourceProfile:
    source_id: str
    connector_kind: str
    root_url: str
    allowed_hosts: tuple[str, ...]
    allowed_operations: tuple[str, ...]
    access_policy: str = "unreviewed"
    terms_checked_at: str | None = None
    robots_policy: str = "unknown"
    robots_checked_at: str | None = None
    min_poll_interval_seconds: int = 3_600
    max_response_bytes: int = 1_000_000
    timeout_seconds: float = 10.0
    max_redirects: int = 3
    failure_budget: int = 3
    retry_base_seconds: int = 30
    feed_url: str | None = None
    robots_rules_by_host: Mapping[str, str] | None = None

    @classmethod
    def from_mapping(cls, value: Any) -> "SourceProfile":
        if not isinstance(value, Mapping):
            raise ConnectorPolicyError("SourceProfile precisa ser objeto.")
        allowed = {
            "source_id", "connector_kind", "root_url", "allowed_hosts", "allowed_operations", "access_policy",
            "terms_checked_at", "robots_policy", "robots_checked_at", "min_poll_interval_seconds",
            "max_response_bytes", "timeout_seconds", "max_redirects", "failure_budget", "retry_base_seconds", "feed_url",
            "robots_rules_by_host",
        }
        if set(value) - allowed:
            raise ConnectorPolicyError("SourceProfile contém campos não reconhecidos.")
        source_id = _nonempty(value.get("source_id"), "source_id", max_length=256)
        kind = value.get("connector_kind")
        if kind not in _ALLOWED_KINDS:
            raise ConnectorPolicyError("connector_kind precisa ser rss_atom, public_api ou public_html.")
        root_url = _nonempty(value.get("root_url"), "root_url", max_length=4_000)
        _, root_host, _ = _safe_url_parts(root_url)
        feed_url = value.get("feed_url")
        if feed_url is not None:
            feed_url = _nonempty(feed_url, "feed_url", max_length=4_000)
            _, feed_host, _ = _safe_url_parts(feed_url)
        else:
            feed_host = root_host
        hosts_value = value.get("allowed_hosts", [root_host, feed_host])
        if not isinstance(hosts_value, (list, tuple)) or not hosts_value:
            raise ConnectorPolicyError("allowed_hosts precisa ser uma lista não vazia.")
        hosts = tuple(sorted({
            _nonempty(host, "allowed_host", max_length=253).rstrip(".").casefold()
            for host in hosts_value
        }))
        if not set((root_host, feed_host)).issubset(hosts):
            raise ConnectorPolicyError("root_url e feed_url precisam estar na allowlist de hosts.")
        for host in hosts:
            if "/" in host or ":" in host or "@" in host:
                raise ConnectorPolicyError("allowed_hosts aceita somente hosts exatos, sem portas ou caminhos.")
        raw_rules = value.get("robots_rules_by_host", {})
        if not isinstance(raw_rules, Mapping):
            raise ConnectorPolicyError("robots_rules_by_host precisa mapear host para texto de regras verificadas.")
        robots_rules: dict[str, str] = {}
        for raw_host, raw_text in raw_rules.items():
            rule_host = _nonempty(raw_host, "robots_host", max_length=253).rstrip(".").casefold()
            if rule_host not in hosts:
                raise ConnectorPolicyError("Snapshot robots pertence a host fora da allowlist.")
            if not isinstance(raw_text, str) or not raw_text.strip() or len(raw_text) > 64_000:
                raise ConnectorPolicyError("Snapshot robots precisa ser texto de até 64.000 caracteres.")
            _nonempty(raw_text, "robots_rules", max_length=64_000)
            if not re.search(r"(?im)^\s*user-agent\s*:", raw_text):
                raise ConnectorPolicyError("Snapshot robots precisa conter grupo User-agent.")
            robots_rules[rule_host] = raw_text
        operations = value.get("allowed_operations", [])
        if not isinstance(operations, (list, tuple)) or any(not isinstance(item, str) for item in operations):
            raise ConnectorPolicyError("allowed_operations precisa ser lista de texto.")
        access_policy = value.get("access_policy", "unreviewed")
        if access_policy not in {"unreviewed", "allowed", "blocked", "suspended"}:
            raise ConnectorPolicyError("access_policy inválida.")
        robots_policy = value.get("robots_policy", "unknown")
        if robots_policy not in {"unknown", "allowed", "blocked", "discovery_only"}:
            raise ConnectorPolicyError("robots_policy inválida.")
        terms_checked_at = value.get("terms_checked_at")
        if terms_checked_at is not None:
            _aware_datetime(terms_checked_at, "terms_checked_at", allow_date=True)
        robots_checked_at = value.get("robots_checked_at")
        if robots_checked_at is not None:
            _aware_datetime(robots_checked_at, "robots_checked_at", allow_date=True)
        numeric = {
            "min_poll_interval_seconds": (value.get("min_poll_interval_seconds", 3_600), 1, 86_400),
            "max_response_bytes": (value.get("max_response_bytes", 1_000_000), 1, 5_000_000),
            "max_redirects": (value.get("max_redirects", 3), 0, 5),
            "failure_budget": (value.get("failure_budget", 3), 1, 10),
            "retry_base_seconds": (value.get("retry_base_seconds", 30), 1, 3_600),
        }
        for name, (number, low, high) in numeric.items():
            if isinstance(number, bool) or not isinstance(number, int) or not low <= number <= high:
                raise ConnectorPolicyError(f"{name} precisa estar entre {low} e {high}.")
        timeout = value.get("timeout_seconds", 10.0)
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not 0.1 <= timeout <= 30:
            raise ConnectorPolicyError("timeout_seconds precisa estar entre 0.1 e 30 segundos.")
        return cls(
            source_id, kind, root_url, hosts, tuple(operations), access_policy,
            terms_checked_at, robots_policy, robots_checked_at,
            numeric["min_poll_interval_seconds"][0], numeric["max_response_bytes"][0], float(timeout),
            numeric["max_redirects"][0], numeric["failure_budget"][0], numeric["retry_base_seconds"][0], feed_url,
            robots_rules,
        )

    def validate_for_fetch(self, *, now: datetime, allow_loopback_http: bool = False) -> None:
        if self.connector_kind not in _ALLOWED_KINDS:
            raise ConnectorPolicyError("connector_kind inválido.")
        source_id = _nonempty(self.source_id, "source_id", max_length=256)
        if source_id != self.source_id:
            raise ConnectorPolicyError("source_id inválido.")
        _, root_host, _ = _safe_url_parts(self.root_url, allow_loopback_http=allow_loopback_http)
        allowed_hosts = {host.rstrip(".").casefold() for host in self.allowed_hosts}
        if root_host not in allowed_hosts:
            raise ConnectorPolicyError("root_url não consta na allowlist de hosts.")
        if self.connector_kind == "rss_atom":
            if not self.feed_url:
                raise ConnectorPolicyError("Feed RSS/Atom exige feed_url explícita.")
            _, feed_host, _ = _safe_url_parts(self.feed_url, allow_loopback_http=allow_loopback_http)
            if feed_host not in allowed_hosts:
                raise ConnectorPolicyError("feed_url não consta na allowlist de hosts.")
        if self.access_policy != "allowed":
            raise ConnectorPolicyError("Fonte sem access_policy=allowed; nenhuma requisição foi feita.")
        if self.robots_policy != "allowed" or self.robots_checked_at is None:
            raise ConnectorPolicyError("Robots/política da fonte não foi verificada e aprovada; coleta bloqueada.")
        if not isinstance(self.robots_rules_by_host, Mapping) or not allowed_hosts.issubset(self.robots_rules_by_host):
            raise ConnectorPolicyError("Snapshot robots verificado é obrigatório para cada host permitido.")
        if self.terms_checked_at is None:
            raise ConnectorPolicyError("Termos da fonte não foram registrados; coleta bloqueada.")
        for name, value in (("terms_checked_at", self.terms_checked_at), ("robots_checked_at", self.robots_checked_at)):
            checked = _aware_datetime(value, name, allow_date=True)
            checked_at = datetime.combine(checked, datetime.min.time(), tzinfo=timezone.utc) if isinstance(checked, date) and not isinstance(checked, datetime) else checked.astimezone(timezone.utc)
            if checked_at > now:
                raise ConnectorPolicyError(f"{name} não pode estar no futuro.")
        if not isinstance(self.allowed_operations, (list, tuple)) or _REQUIRED_OPERATION[self.connector_kind] not in self.allowed_operations:
            raise ConnectorPolicyError("Operação de leitura não consta na allowlist desta fonte.")
        checks = (
            (self.min_poll_interval_seconds, 1, 86_400, "min_poll_interval_seconds"),
            (self.max_response_bytes, 1, 5_000_000, "max_response_bytes"),
            (self.max_redirects, 0, 5, "max_redirects"),
            (self.failure_budget, 1, 10, "failure_budget"),
            (self.retry_base_seconds, 1, 3_600, "retry_base_seconds"),
        )
        for value, minimum, maximum, name in checks:
            if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
                raise ConnectorPolicyError(f"{name} precisa estar entre {minimum} e {maximum}.")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)) or not 0.1 <= self.timeout_seconds <= 30:
            raise ConnectorPolicyError("timeout_seconds precisa estar entre 0.1 e 30 segundos.")

    def robots_allows(self, url: str, *, allow_loopback_http: bool = False) -> bool:
        parts, host, _ = _safe_url_parts(url, allow_loopback_http=allow_loopback_http)
        rules = (self.robots_rules_by_host or {}).get(host)
        if not rules:
            return False
        parser = RobotFileParser()
        parser.set_url(f"{parts.scheme}://{host}/robots.txt")
        parser.parse(rules.splitlines())
        return parser.can_fetch(_USER_AGENT, url)

    def target_url(self) -> str:
        return self.feed_url if self.connector_kind == "rss_atom" and self.feed_url else self.root_url


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: Mapping[str, str]
    body: bytes


class Transport(Protocol):
    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse: ...


class PinnedHTTPTransport:
    """Direct HTTP transport that connects to a previously checked IP address."""

    def __init__(self, *, allow_loopback_http: bool = False):
        self.allow_loopback_http = allow_loopback_http
        self._tls_context = ssl.create_default_context()

    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse:
        parts, host, port = _safe_url_parts(url, allow_loopback_http=allow_loopback_http and self.allow_loopback_http)
        address = ipaddress.ip_address(pinned_address)
        is_test_loopback = parts.scheme == "http" and address.is_loopback and self.allow_loopback_http
        if parts.scheme != "https" and not is_test_loopback:
            raise ConnectorPolicyError("Transporte HTTP sem TLS bloqueado.")
        connection: http.client.HTTPConnection
        if parts.scheme == "https":
            connection = http.client.HTTPSConnection(host, port=port, timeout=timeout_seconds, context=self._tls_context)
        else:
            connection = http.client.HTTPConnection(host, port=port, timeout=timeout_seconds)
        sock = socket.create_connection((str(address), port), timeout=timeout_seconds)
        if parts.scheme == "https":
            sock = self._tls_context.wrap_socket(sock, server_hostname=host)
        connection.sock = sock
        path = parts.path or "/"
        if parts.query:
            path = f"{path}?{parts.query}"
        safe_headers = dict(headers)
        safe_headers["Connection"] = "close"
        try:
            connection.request("GET", path, headers=safe_headers)
            response = connection.getresponse()
            raw_length = response.getheader("Content-Length")
            if raw_length and raw_length.isdigit() and int(raw_length) > max_response_bytes:
                raise ConnectorPolicyError("Resposta excede max_response_bytes.")
            body = response.read(max_response_bytes + 1)
            if len(body) > max_response_bytes:
                raise ConnectorPolicyError("Resposta excede max_response_bytes.")
            response_headers = {
                key.casefold(): value[:4_096]
                for key, value in response.getheaders()
                if key.casefold() in _RESPONSE_HEADER_ALLOWLIST
            }
            return HttpResponse(response.status, response_headers, body)
        finally:
            connection.close()


class PerOriginLimiter:
    """Nonblocking minimum-interval limiter shared by source profiles on a host."""

    def __init__(self, monotonic: Callable[[], float] = time.monotonic):
        self._monotonic = monotonic
        self._last_by_origin: dict[str, float] = {}
        self._min_interval_by_origin: dict[str, int] = {}
        self._blocked_until_by_origin: dict[str, float] = {}
        self._lock = Lock()

    def reserve(self, origin: str, min_interval_seconds: int) -> float:
        with self._lock:
            now = self._monotonic()
            self._min_interval_by_origin[origin] = max(
                min_interval_seconds, self._min_interval_by_origin.get(origin, 0)
            )
            blocked = max(0.0, self._blocked_until_by_origin.get(origin, 0.0) - now)
            if blocked:
                return blocked
            previous = self._last_by_origin.get(origin)
            effective_interval = self._min_interval_by_origin[origin]
            if previous is not None and now - previous < effective_interval:
                return effective_interval - (now - previous)
            self._last_by_origin[origin] = now
            return 0.0

    def cooldown(self, origin: str, seconds: int) -> None:
        with self._lock:
            until = self._monotonic() + max(1, seconds)
            self._blocked_until_by_origin[origin] = max(until, self._blocked_until_by_origin.get(origin, 0.0))

    def cooldown_remaining(self, origin: str) -> float:
        with self._lock:
            return max(0.0, self._blocked_until_by_origin.get(origin, 0.0) - self._monotonic())


@dataclass
class SourceRuntimeState:
    consecutive_failures: int = 0
    suspended: bool = False
    next_retry_at: str | None = None


@dataclass(frozen=True)
class FetchResult:
    source_id: str
    status: str
    requested_url: str
    final_url: str
    http_status: int | None
    fetched_at: str
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
    retry_at: str | None = None
    redirect_count: int = 0
    metadata: Any = None
    error_code: str | None = None
    payload_sha256: str | None = None


def _retry_after_seconds(value: str | None, now: datetime, fallback: int, *, maximum: int = 86_400) -> int:
    if value:
        value = value.strip()
        if value.isdigit():
            return min(maximum, max(1, int(value)))
        try:
            retry_at = email.utils.parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return min(maximum, max(1, int((retry_at.astimezone(timezone.utc) - now).total_seconds())))
        except (TypeError, ValueError, OverflowError):
            pass
    return min(maximum, max(1, fallback))


class RadarConnectorService:
    """Explicit, one-shot, public-metadata retrieval under per-source policy."""

    def __init__(
        self,
        *,
        transport: Transport | None = None,
        resolver: Callable[..., Any] = socket.getaddrinfo,
        limiter: PerOriginLimiter | None = None,
        domain_quota_guard: DomainQuotaGuard | None = None,
        allow_loopback_http: bool = False,
    ):
        self.allow_loopback_http = allow_loopback_http
        self.transport = transport or PinnedHTTPTransport(allow_loopback_http=allow_loopback_http)
        self.resolver = resolver
        self.limiter = limiter or PerOriginLimiter()
        self.domain_quota_guard = domain_quota_guard
        self._states: dict[str, SourceRuntimeState] = {}
        self._state_lock = Lock()

    def state(self, source_id: str) -> SourceRuntimeState:
        with self._state_lock:
            state = self._states.get(source_id)
            if state is None:
                state = SourceRuntimeState()
                self._states[source_id] = state
            return state

    def _resolve_public_address(self, url: str) -> tuple[str, str]:
        parts, host, port = _safe_url_parts(url, allow_loopback_http=self.allow_loopback_http)
        try:
            literal = ipaddress.ip_address(host)
            addresses = [str(literal)]
        except ValueError:
            try:
                records = self.resolver(host, port, type=socket.SOCK_STREAM)
            except OSError as error:
                raise ConnectorPolicyError("Host não pôde ser resolvido.") from error
            addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses:
            raise ConnectorPolicyError("Host não retornou endereço de rede.")
        for raw_address in addresses:
            try:
                ip = ipaddress.ip_address(raw_address.split("%", 1)[0])
            except ValueError as error:
                raise ConnectorPolicyError("DNS retornou endereço IP inválido.") from error
            test_http = parts.scheme == "http" and self.allow_loopback_http and ip.is_loopback
            if not test_http and (not ip.is_global or ip.is_multicast or ip.is_unspecified or ip.is_reserved):
                raise ConnectorPolicyError("SSRF bloqueada: host resolve para faixa não pública.")
            if parts.scheme == "http" and not test_http:
                raise ConnectorPolicyError("HTTP sem TLS bloqueado fora do loopback de teste.")
        return host, addresses[0]

    @staticmethod
    def _content_type(headers: Mapping[str, str]) -> str | None:
        value = next((v for k, v in headers.items() if k.casefold() == "content-type"), None)
        return value.split(";", 1)[0].strip().casefold() if value else None

    @staticmethod
    def _header(headers: Mapping[str, str], key: str) -> str | None:
        value = next((v for k, v in headers.items() if k.casefold() == key), None)
        if value is None:
            return None
        value = value.strip()
        try:
            _assert_no_credentials(value, f"response.{key}")
        except ValueError as error:
            raise ConnectorPolicyError(f"response.{key} parece conter credenciais.") from error
        return value[:4_096] or None

    @staticmethod
    def _now(value: str | datetime | None) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)
        if isinstance(value, datetime):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as error:
                raise ConnectorPolicyError("now precisa ser data/hora ISO-8601.") from error
        else:
            raise ConnectorPolicyError("now precisa ser data/hora ISO-8601.")
        if parsed.tzinfo is None:
            raise ConnectorPolicyError("now precisa declarar fuso horário.")
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _retry_at(now: datetime, seconds: int) -> str:
        return (now + timedelta(seconds=seconds)).isoformat(timespec="seconds")

    def fetch(
        self,
        profile: SourceProfile,
        *,
        url: str | None = None,
        etag: str | None = None,
        last_modified: str | None = None,
        now: str | datetime | None = None,
    ) -> FetchResult:
        current_time = self._now(now)
        fetched_at = current_time.isoformat(timespec="seconds")
        target = url or profile.target_url()
        state = self.state(profile.source_id)
        if state.suspended:
            return FetchResult(profile.source_id, "blocked", target, target, None, fetched_at, error_code="source_suspended")
        if state.next_retry_at:
            next_retry = self._now(state.next_retry_at)
            if current_time < next_retry:
                return FetchResult(
                    profile.source_id, "rate_limited", target, target, None, fetched_at,
                    retry_at=state.next_retry_at, error_code="source_backoff",
                )
            state.next_retry_at = None
        try:
            profile.validate_for_fetch(now=current_time, allow_loopback_http=self.allow_loopback_http)
            _, initial_host, initial_port = _safe_url_parts(target, allow_loopback_http=self.allow_loopback_http)
            allowed_hosts = {host.rstrip(".").casefold() for host in profile.allowed_hosts}
            if initial_host not in allowed_hosts:
                raise ConnectorPolicyError("Host inicial não consta na allowlist da fonte.")
            if not profile.robots_allows(target, allow_loopback_http=self.allow_loopback_http):
                raise ConnectorPolicyError("Robots.txt bloqueia o caminho ou não há snapshot verificado.")
            origin = f"{urlsplit(target).scheme}://{initial_host}:{initial_port}"
            origin_cooldown = self.limiter.cooldown_remaining(origin)
            if origin_cooldown:
                return FetchResult(
                    profile.source_id, "rate_limited", target, target, None, fetched_at,
                    retry_at=self._retry_at(current_time, max(1, int(origin_cooldown + 0.999))),
                    error_code="origin_retry_after",
                )
            request_headers = {
                "User-Agent": _USER_AGENT,
                "Accept": {
                    "rss_atom": "application/atom+xml, application/rss+xml, application/xml, text/xml",
                    "public_api": "application/json, application/ld+json",
                    "public_html": "text/html, application/xhtml+xml",
                }[profile.connector_kind],
            }
            for name, value in (("If-None-Match", etag), ("If-Modified-Since", last_modified)):
                if value is not None:
                    header_text = _nonempty(value, name, max_length=1_000)
                    if "\r" in header_text or "\n" in header_text:
                        raise ConnectorPolicyError(f"{name} contém caracteres de controle.")
                    request_headers[name] = header_text
            _, initial_address = self._resolve_public_address(target)
        except ConnectorPolicyError as error:
            return FetchResult(profile.source_id, "blocked", target, target, None, fetched_at, error_code=str(error))
        wait_seconds = self.limiter.reserve(origin, profile.min_poll_interval_seconds)
        if wait_seconds:
            reason = "origin_retry_after" if self.limiter.cooldown_remaining(origin) else "origin_min_interval"
            return FetchResult(
                profile.source_id, "rate_limited", target, target, None, fetched_at,
                retry_at=self._retry_at(current_time, max(1, int(wait_seconds + 0.999))),
                error_code=reason,
            )
        visited: set[str] = set()
        current_url = target
        redirects = 0
        response: HttpResponse | None = None
        request_origin = origin
        try:
            while True:
                if current_url in visited:
                    raise ConnectorPolicyError("Ciclo de redirect detectado.")
                visited.add(current_url)
                parts, host, port = _safe_url_parts(current_url, allow_loopback_http=self.allow_loopback_http)
                if host not in allowed_hosts:
                    raise ConnectorPolicyError("Redirect para host fora da allowlist.")
                if not profile.robots_allows(current_url, allow_loopback_http=self.allow_loopback_http):
                    raise ConnectorPolicyError("Robots.txt bloqueia o redirect ou não há snapshot verificado.")
                current_origin = f"{parts.scheme}://{host}:{port}"
                if redirects and current_origin != request_origin:
                    wait_seconds = self.limiter.reserve(current_origin, profile.min_poll_interval_seconds)
                    if wait_seconds:
                        reason = "origin_retry_after" if self.limiter.cooldown_remaining(current_origin) else "origin_min_interval"
                        return FetchResult(
                            profile.source_id, "rate_limited", target, current_url,
                            response.status_code if response else None, fetched_at,
                            retry_at=self._retry_at(current_time, max(1, int(wait_seconds + 0.999))),
                            redirect_count=redirects, error_code=reason,
                        )
                    request_headers = {
                        key: value for key, value in request_headers.items()
                        if key.casefold() not in {"if-none-match", "if-modified-since"}
                    }
                request_origin = current_origin
                if redirects == 0:
                    pinned_ip = initial_address
                else:
                    _, pinned_ip = self._resolve_public_address(current_url)
                if self.domain_quota_guard is not None:
                    try:
                        quota = self.domain_quota_guard.reserve_request(
                            host, now=current_time, request_key=str(uuid.uuid4())
                        )
                    except Exception:
                        return FetchResult(
                            profile.source_id, "blocked", target, current_url,
                            response.status_code if response else None, fetched_at,
                            redirect_count=redirects, error_code="domain_quota_unavailable",
                        )
                    if not quota.allowed:
                        status = "rate_limited" if quota.reason == "domain_daily_quota" else "blocked"
                        return FetchResult(
                            profile.source_id, status, target, current_url,
                            response.status_code if response else None, fetched_at,
                            retry_at=quota.retry_at, redirect_count=redirects,
                            error_code=quota.reason or "domain_quota_blocked",
                        )
                response = self.transport.request(
                    current_url, pinned_ip, headers=request_headers, timeout_seconds=profile.timeout_seconds,
                    max_response_bytes=profile.max_response_bytes, allow_loopback_http=self.allow_loopback_http,
                )
                if len(response.body) > profile.max_response_bytes:
                    raise ConnectorPolicyError("Resposta excedeu max_response_bytes.")
                location = self._header(response.headers, "location")
                if response.status_code not in _REDIRECT_CODES:
                    break
                if not location:
                    raise ConnectorPolicyError("Redirect sem Location.")
                if redirects >= profile.max_redirects:
                    raise ConnectorPolicyError("Limite de redirects excedido.")
                current_url = urljoin(current_url, location)
                redirects += 1
            return self._classify_response(
                profile, target, current_url, response, fetched_at, current_time, redirects, state, request_origin
            )
        except ConnectorPolicyError as error:
            return FetchResult(profile.source_id, "blocked", target, current_url, response.status_code if response else None,
                               fetched_at, redirect_count=redirects, error_code=str(error))
        except (OSError, http.client.HTTPException, ssl.SSLError, TimeoutError, ValueError) as error:
            state.consecutive_failures += 1
            retry = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
            self.limiter.cooldown(request_origin, retry)
            if state.consecutive_failures >= profile.failure_budget:
                state.suspended = True
            state.next_retry_at = self._retry_at(current_time, retry)
            return FetchResult(profile.source_id, "error", target, current_url, None, fetched_at,
                               retry_at=state.next_retry_at, redirect_count=redirects,
                               error_code="transport_error")

    def _classify_response(
        self, profile: SourceProfile, requested_url: str, final_url: str, response: HttpResponse,
        fetched_at: str, now: datetime, redirects: int, state: SourceRuntimeState, origin: str,
    ) -> FetchResult:
        status = response.status_code
        headers = response.headers
        etag = self._header(headers, "etag")
        last_modified = self._header(headers, "last-modified")
        content_type = self._content_type(headers)
        retry_at = None
        error_code = None
        body = response.body
        metadata = None
        if status == 304:
            result_status = "not_modified"
            body = b""
            state.consecutive_failures = 0
            state.next_retry_at = None
        elif status in {401, 403}:
            result_status = "forbidden"
            body = b""
            error_code = "source_access_denied"
            state.suspended = True
            state.next_retry_at = None
        elif status in {404, 410}:
            result_status = "removed"
            body = b""
            error_code = "source_removed"
            state.suspended = True
            state.next_retry_at = None
        elif status == 429:
            result_status = "rate_limited"
            body = b""
            seconds = _retry_after_seconds(self._header(headers, "retry-after"), now, profile.retry_base_seconds)
            retry_at = self._retry_at(now, seconds)
            state.next_retry_at = retry_at
            self.limiter.cooldown(origin, seconds)
            error_code = "provider_rate_limit"
        elif 500 <= status <= 599:
            result_status = "error"
            body = b""
            state.consecutive_failures += 1
            fallback = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
            seconds = _retry_after_seconds(self._header(headers, "retry-after"), now, fallback)
            retry_at = self._retry_at(now, seconds)
            state.next_retry_at = retry_at
            self.limiter.cooldown(origin, seconds)
            if state.consecutive_failures >= profile.failure_budget:
                state.suspended = True
            error_code = "provider_server_error"
        elif status != 200:
            result_status = "error"
            body = b""
            error_code = "unexpected_http_status"
            state.consecutive_failures += 1
            fallback = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
            retry_at = self._retry_at(now, fallback)
            state.next_retry_at = retry_at
            self.limiter.cooldown(origin, fallback)
            if state.consecutive_failures >= profile.failure_budget:
                state.suspended = True
        else:
            accepted_types = {
                "rss_atom": {"application/rss+xml", "application/atom+xml", "application/xml", "text/xml"},
                "public_api": {"application/json", "application/ld+json"},
                "public_html": {"text/html", "application/xhtml+xml"},
            }[profile.connector_kind]
            if content_type not in accepted_types:
                result_status = "error"
                error_code = "unsupported_content_type"
                body = b""
                state.consecutive_failures += 1
                retry = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
                retry_at = self._retry_at(now, retry)
                state.next_retry_at = retry_at
                self.limiter.cooldown(origin, retry)
                if state.consecutive_failures >= profile.failure_budget:
                    state.suspended = True
            else:
                try:
                    if profile.connector_kind == "rss_atom":
                        metadata = parse_rss_atom(body, maximum_bytes=profile.max_response_bytes)
                    elif profile.connector_kind == "public_html":
                        metadata = parse_public_html(
                            body, base_url=final_url, maximum_bytes=profile.max_response_bytes,
                            allow_loopback_http=self.allow_loopback_http,
                        )
                    else:
                        metadata = project_public_api_metadata(body, maximum_bytes=profile.max_response_bytes)
                    result_status = "observed"
                    state.consecutive_failures = 0
                    state.next_retry_at = None
                except ConnectorPolicyError:
                    result_status = "error"
                    error_code = "invalid_or_unsafe_public_payload"
                    metadata = None
                    state.consecutive_failures += 1
                    retry = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
                    retry_at = self._retry_at(now, retry)
                    state.next_retry_at = retry_at
                    self.limiter.cooldown(origin, retry)
                    if state.consecutive_failures >= profile.failure_budget:
                        state.suspended = True
        payload_sha256 = hashlib.sha256(body).hexdigest() if result_status == "observed" else None
        return FetchResult(profile.source_id, result_status, requested_url, final_url, status, fetched_at,
                           content_type, etag, last_modified, retry_at, redirects, metadata, error_code,
                           payload_sha256)


@dataclass(frozen=True)
class FeedItem:
    title: str
    url: str | None
    external_id: str | None
    published_at: str | None
    byline: str | None = None
    body_sha256: str | None = None
    body_segment_hashes: tuple[str, ...] = ()
    body_char_count: int = 0
    origin_url: str | None = None
    content_sha256: str | None = None
    normalized_sha256: str | None = None


class _FeedPlainTextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data.strip():
            self.parts.append(data)


def _feed_body_fingerprints(
    entry: ET.Element, raw_title: str,
) -> tuple[str | None, tuple[str, ...], int, str, str]:
    body_values: list[str] = []
    for child in list(entry):
        if local_name := child.tag.rsplit("}", 1)[-1].casefold():
            if local_name in {"description", "summary", "content", "encoded"}:
                value = "".join(child.itertext())
                if value.strip():
                    body_values.append(value)
    raw_body = "\u0000".join(body_values)
    plain_parser = _FeedPlainTextParser()
    plain_parser.feed(raw_body.replace("\u0000", " "))
    normalized_body = " ".join(" ".join(plain_parser.parts).split())
    if not normalized_body:
        normalized_body = ""
        body_hash = None
        body_char_count = 0
    else:
        body_hash = hashlib.sha256(raw_body.encode("utf-8")).hexdigest()
        body_char_count = len(normalized_body)
    segment_count = min(256, max(1, (len(normalized_body) + 1_023) // 1_024)) if normalized_body else 0
    segment_hashes: list[str] = []
    for index in range(segment_count):
        start = index * len(normalized_body) // segment_count
        end = (index + 1) * len(normalized_body) // segment_count
        segment_hashes.append(hashlib.sha256(normalized_body[start:end].encode("utf-8")).hexdigest())
    normalized_title = " ".join(raw_title.split())
    exact_content_hash = hashlib.sha256(f"{raw_title}\u0000{raw_body}".encode("utf-8")).hexdigest()
    normalized_content_hash = hashlib.sha256(f"{normalized_title}\u0000{normalized_body}".encode("utf-8")).hexdigest()
    return body_hash, tuple(segment_hashes), body_char_count, exact_content_hash, normalized_content_hash


def _feed_origin_url(entry: ET.Element) -> str | None:
    for child in list(entry):
        name = child.tag.rsplit("}", 1)[-1].casefold()
        if name == "source":
            candidate = child.attrib.get("url") or child.attrib.get("href")
            if candidate:
                safe = _safe_public_reference_url(candidate.strip())
                if safe:
                    return safe
        if name == "link" and child.attrib.get("rel", "").casefold() == "via":
            candidate = child.attrib.get("href")
            if candidate:
                safe = _safe_public_reference_url(candidate.strip())
                if safe:
                    return safe
    return None


def parse_rss_atom(payload: bytes, *, maximum_bytes: int = 1_000_000) -> tuple[FeedItem, ...]:
    if not isinstance(payload, bytes) or len(payload) > maximum_bytes:
        raise ConnectorPolicyError("Feed XML excede limite de tamanho ou não está em bytes.")
    upper = payload[: min(len(payload), 4_096)].upper()
    upper = payload.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ConnectorPolicyError("DTD e entidades XML estão desabilitados.")
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as error:
        raise ConnectorPolicyError("Feed RSS/Atom malformado.") from error

    def local(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].casefold()

    def child_text(element: ET.Element, names: set[str]) -> str | None:
        for child in list(element):
            if local(child.tag) in names and child.text:
                value = " ".join(child.text.split())[:2_000]
                if value:
                    return value
        return None

    items: list[FeedItem] = []
    for entry in root.iter():
        if local(entry.tag) not in {"item", "entry"}:
            continue
        title = child_text(entry, {"title"})
        raw_title = ""
        for child in list(entry):
            if local(child.tag) == "title":
                raw_title = "".join(child.itertext())
                break
        link = None
        for child in list(entry):
            if local(child.tag) != "link":
                continue
            rel = child.attrib.get("rel", "alternate").casefold()
            candidate = child.attrib.get("href") or child.text
            if rel == "alternate" and candidate:
                link = _safe_public_reference_url(candidate.strip())
                if link:
                    break
        external_id = child_text(entry, {"guid", "id"})
        published_at = child_text(entry, {"pubdate", "published", "updated", "date"})
        byline = child_text(entry, {"author", "creator"})
        if byline is None:
            for author in entry.iter():
                if local(author.tag) == "author":
                    byline = child_text(author, {"name"})
                    if byline:
                        break
        body_sha256, body_segment_hashes, body_char_count, content_sha256, normalized_sha256 = _feed_body_fingerprints(entry, raw_title or title or "")
        origin_url = _feed_origin_url(entry)
        if title:
            items.append(FeedItem(
                title[:1_000], link, external_id, published_at, byline, body_sha256,
                body_segment_hashes, body_char_count, origin_url, content_sha256, normalized_sha256,
            ))
    return tuple(items[:10_000])


class _MetadataHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._in_title = False
        self._title_parts: list[str] = []
        self._title_length = 0
        self.canonical_url: str | None = None
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.casefold(): value for key, value in attrs if value is not None}
        if tag.casefold() == "title":
            self._in_title = True
        elif tag.casefold() == "link" and values.get("href") and "canonical" in (values.get("rel", "").casefold().split()):
            self.canonical_url = _safe_public_reference_url(urljoin(self.base_url, values.get("href", ""))[:4_000])
        elif tag.casefold() == "a" and values.get("href") and len(self.links) < 500:
            candidate = urljoin(self.base_url, values["href"])
            safe_candidate = _safe_public_reference_url(candidate[:4_000])
            if safe_candidate:
                self.links.append(safe_candidate)

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title and self._title_length < 1_000:
            remaining = 1_000 - self._title_length
            part = data[:remaining]
            self._title_parts.append(part)
            self._title_length += len(part)

    @property
    def title(self) -> str | None:
        title = " ".join(" ".join(self._title_parts).split())[:1_000]
        return title or None


@dataclass(frozen=True)
class HTMLPageMetadata:
    title: str | None
    canonical_url: str | None
    discovered_links: tuple[str, ...]


def parse_public_html(
    payload: bytes, *, base_url: str, maximum_bytes: int = 1_000_000, allow_loopback_http: bool = False,
) -> HTMLPageMetadata:
    if not isinstance(payload, bytes) or len(payload) > maximum_bytes:
        raise ConnectorPolicyError("HTML excede limite de tamanho ou não está em bytes.")
    _, base_host, _ = _safe_url_parts(base_url, allow_loopback_http=allow_loopback_http)
    try:
        text = payload.decode("utf-8-sig", errors="replace")
    except Exception as error:
        raise ConnectorPolicyError("HTML não pôde ser decodificado.") from error
    parser = _MetadataHTMLParser(base_url)
    parser.feed(text)
    canonical = parser.canonical_url
    if canonical:
        parts = urlsplit(canonical)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.hostname.casefold() != base_host:
            canonical = None
    return HTMLPageMetadata(parser.title, canonical, tuple(parser.links))


def parse_public_json(payload: bytes, *, maximum_bytes: int = 1_000_000) -> Any:
    if not isinstance(payload, bytes) or len(payload) > maximum_bytes:
        raise ConnectorPolicyError("JSON público excede limite de tamanho ou não está em bytes.")
    try:
        value = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as error:
        raise ConnectorPolicyError("Resposta JSON pública malformada.") from error
    try:
        _assert_no_credentials(value, "public_json")
    except ValueError as error:
        raise ConnectorPolicyError("Resposta JSON parece conter credenciais; payload descartado.") from error
    return value


_SAFE_API_FIELDS = {
    "id", "title", "name", "url", "link", "published_at", "updated_at", "release_date",
    "version", "slug", "author", "publisher", "developer", "status", "type", "platform",
}
_SAFE_API_CONTAINERS = {"data", "items", "results", "entries", "records", "releases", "builds", "versions"}


def project_public_api_metadata(payload: bytes, *, maximum_bytes: int = 1_000_000) -> Any:
    """Return a small metadata projection while dropping article/body fields."""
    source = parse_public_json(payload, maximum_bytes=maximum_bytes)
    budget = [1_000]

    def project(value: Any, depth: int = 0) -> Any:
        if depth > 8 or budget[0] <= 0:
            return None
        budget[0] -= 1
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, nested in value.items():
                normalized = str(key).casefold().replace("-", "_")
                if normalized in _SAFE_API_FIELDS:
                    if isinstance(nested, (str, int, float, bool)) or nested is None:
                        if normalized in {"url", "link"}:
                            safe_url = _safe_public_reference_url(nested) if isinstance(nested, str) else None
                            if safe_url:
                                result[normalized] = safe_url
                        elif isinstance(nested, str):
                            result[normalized] = nested[:500]
                        else:
                            result[normalized] = nested
                elif normalized in _SAFE_API_CONTAINERS:
                    projected = project(nested, depth + 1)
                    if projected not in (None, {}, []):
                        result[normalized] = projected
            return result
        if isinstance(value, list):
            results = [project(item, depth + 1) for item in value[:100]]
            return [item for item in results if item not in (None, {}, [])]
        return None

    return project(source)
