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
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from threading import Lock
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import parse_qsl, unquote, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

from .orchestration import _assert_no_credentials
from .radar_policy import DomainQuotaGuard, PersistentDomainQuotaGuard


class ConnectorPolicyError(ValueError):
    """Raised when a source or request fails an explicit safety policy."""

    def __init__(self, message: str, *, code: str = "connector_policy_error", phase: str = "source_policy"):
        super().__init__(message)
        self.code = code
        self.phase = phase


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
SOURCE_PROFILE_SCHEMA_VERSION = "1.1"
_SUPPORTED_SOURCE_PROFILE_SCHEMA_VERSIONS = {"1.0", SOURCE_PROFILE_SCHEMA_VERSION}
_SOURCE_CLASSES = {"official", "independent", "community", "replicator"}
_REUSE_POLICIES = {"metadata_only", "short_excerpt"}
_API_SCHEMA_IDS = {"github_release_v1", "metadata_records_v1"}
_PARSER_SCHEMA_BY_KIND = {
    "rss_atom": "rss_atom_v1",
    "public_html": "public_html_metadata_v1",
}
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


def _safe_path_prefix(value: Any) -> str:
    prefix = _nonempty(value, "allowed_path_prefix", max_length=1_000)
    if not prefix.startswith("/") or "?" in prefix or "#" in prefix or "\\" in prefix:
        raise ConnectorPolicyError("allowed_path_prefix precisa ser um caminho absoluto sem query ou fragmento.")
    decoded = _fully_decode_path(prefix)
    if decoded is None:
        raise ConnectorPolicyError("allowed_path_prefix contém codificação ambígua.")
    if any(part in {".", ".."} for part in decoded.split("/")) or "\\" in decoded:
        raise ConnectorPolicyError("allowed_path_prefix contém segmento ambíguo.")
    return decoded.rstrip("/") or "/"


def _fully_decode_path(value: str) -> str | None:
    decoded = value
    for _ in range(8):
        next_value = unquote(decoded)
        if next_value == decoded:
            return decoded
        decoded = next_value
    return None


def _path_is_allowed(url: str, prefixes: tuple[str, ...]) -> bool:
    try:
        path = _fully_decode_path(urlsplit(url).path or "/")
    except ValueError:
        return False
    if path is None:
        return False
    if any(part in {".", ".."} for part in path.split("/")) or "\\" in path:
        return False
    for prefix in prefixes:
        if prefix == "/":
            if path == "/":
                return True
        elif path == prefix or path.startswith(prefix + "/"):
            return True
    return False


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
    schema_version: str = "1.0"
    profile_version: str = "legacy"
    source_name: str | None = None
    source_owner: str | None = None
    source_class: str | None = None
    channel: str | None = None
    allowed_path_prefixes: tuple[str, ...] = ()
    terms_evidence_url: str | None = None
    authenticated: bool = False
    reuse_policy: str = "metadata_only"
    rights_status: str = "unknown"
    language: str | None = None
    quota_per_host_day: int | None = None
    quota_per_mission: int | None = None
    parser_schema_id: str | None = None
    adapter_version: str | None = None
    last_collected_at: str | None = None

    @classmethod
    def from_mapping(cls, value: Any) -> "SourceProfile":
        if not isinstance(value, Mapping):
            raise ConnectorPolicyError("SourceProfile precisa ser objeto.")
        allowed = {
            "source_id", "connector_kind", "root_url", "allowed_hosts", "allowed_operations", "access_policy",
            "terms_checked_at", "robots_policy", "robots_checked_at", "min_poll_interval_seconds",
            "max_response_bytes", "timeout_seconds", "max_redirects", "failure_budget", "retry_base_seconds", "feed_url",
            "robots_rules_by_host", "schema_version", "profile_version", "source_name", "source_owner",
            "source_class", "channel", "allowed_path_prefixes", "terms_evidence_url", "authenticated",
            "reuse_policy", "rights_status", "language", "quota_per_host_day", "quota_per_mission",
            "parser_schema_id", "adapter_version", "last_collected_at",
        }
        if set(value) - allowed:
            raise ConnectorPolicyError("SourceProfile contém campos não reconhecidos.")
        source_id = _nonempty(value.get("source_id"), "source_id", max_length=256)
        schema_version = value.get("schema_version", "1.0")
        if schema_version not in _SUPPORTED_SOURCE_PROFILE_SCHEMA_VERSIONS:
            raise ConnectorPolicyError("schema_version de SourceProfile não suportada.")
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
        raw_paths = value.get("allowed_path_prefixes")
        if raw_paths is None:
            if schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
                raise ConnectorPolicyError("SourceProfile v1.1 exige allowed_path_prefixes explícitos.")
            path_prefixes = ()
        else:
            if not isinstance(raw_paths, (list, tuple)) or not raw_paths:
                raise ConnectorPolicyError("allowed_path_prefixes precisa ser uma lista não vazia.")
            path_prefixes = tuple(sorted({_safe_path_prefix(item) for item in raw_paths}))
        source_class = value.get("source_class")
        source_name = value.get("source_name")
        source_owner = value.get("source_owner")
        profile_version = value.get("profile_version", "legacy")
        channel = value.get("channel", kind)
        terms_evidence_url = value.get("terms_evidence_url")
        authenticated = value.get("authenticated", False)
        reuse_policy = value.get("reuse_policy", "metadata_only")
        rights_status = value.get("rights_status", "unknown")
        language = value.get("language")
        quota_per_host_day = value.get("quota_per_host_day")
        quota_per_mission = value.get("quota_per_mission")
        parser_schema_id = value.get("parser_schema_id")
        adapter_version = value.get("adapter_version")
        last_collected_at = value.get("last_collected_at")
        if reuse_policy not in _REUSE_POLICIES:
            raise ConnectorPolicyError("reuse_policy precisa ser metadata_only ou short_excerpt.")
        if reuse_policy == "short_excerpt" and rights_status != "authorized":
            raise ConnectorPolicyError("short_excerpt exige rights_status=authorized; leitura p\u00fablica \u00e9 uma pol\u00edtica separada.")
        if schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
            source_name = _nonempty(source_name, "source_name", max_length=500)
            source_owner = _nonempty(source_owner, "source_owner", max_length=500)
            profile_version = _nonempty(profile_version, "profile_version", max_length=128)
            if source_class not in _SOURCE_CLASSES:
                raise ConnectorPolicyError("source_class precisa ser official, independent, community ou replicator.")
            if channel != kind:
                raise ConnectorPolicyError("channel precisa corresponder ao conector configurado.")
            if not isinstance(authenticated, bool) or authenticated:
                raise ConnectorPolicyError("Coleta Radar não aceita perfil autenticado; use somente acesso público sem credenciais.")
            if reuse_policy not in _REUSE_POLICIES:
                raise ConnectorPolicyError("reuse_policy precisa ser metadata_only ou short_excerpt.")
            if rights_status not in {"unknown", "pending", "authorized", "blocked"}:
                raise ConnectorPolicyError("rights_status inválido ou misturado com access_policy.")
            if reuse_policy == "short_excerpt" and rights_status != "authorized":
                raise ConnectorPolicyError("short_excerpt exige rights_status=authorized; leitura pública é uma política separada.")
            terms_evidence_url = _nonempty(terms_evidence_url, "terms_evidence_url", max_length=4_000)
            terms_parts, _, _ = _safe_url_parts(terms_evidence_url)
            if terms_parts.scheme != "https":
                raise ConnectorPolicyError("terms_evidence_url precisa usar HTTPS.")
            if not isinstance(language, str) or not re.fullmatch(r"[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*", language):
                raise ConnectorPolicyError("language precisa ser uma etiqueta BCP 47 simplificada.")
            for name, number in (("quota_per_host_day", quota_per_host_day), ("quota_per_mission", quota_per_mission)):
                if isinstance(number, bool) or not isinstance(number, int) or not 1 <= number <= 10_000:
                    raise ConnectorPolicyError(f"{name} precisa ser inteiro entre 1 e 10.000.")
            parser_schema_id = _nonempty(parser_schema_id, "parser_schema_id", max_length=128)
            expected_schemas = (
                _API_SCHEMA_IDS if kind == "public_api"
                else {_PARSER_SCHEMA_BY_KIND[kind]}
            )
            if parser_schema_id not in expected_schemas:
                raise ConnectorPolicyError("parser_schema_id não é compatível com connector_kind.")
            adapter_version = _nonempty(adapter_version, "adapter_version", max_length=128)
        if authenticated is not False:
            raise ConnectorPolicyError("authenticated deve ser false; credenciais e sessões não são aceitas.")
        if rights_status not in {"unknown", "pending", "authorized", "blocked"}:
            raise ConnectorPolicyError("rights_status inválido.")
        if last_collected_at is not None:
            _aware_datetime(last_collected_at, "last_collected_at", allow_date=True)
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
            source_id=source_id, connector_kind=kind, root_url=root_url, allowed_hosts=hosts,
            allowed_operations=tuple(operations), access_policy=access_policy,
            terms_checked_at=terms_checked_at, robots_policy=robots_policy, robots_checked_at=robots_checked_at,
            min_poll_interval_seconds=numeric["min_poll_interval_seconds"][0],
            max_response_bytes=numeric["max_response_bytes"][0], timeout_seconds=float(timeout),
            max_redirects=numeric["max_redirects"][0], failure_budget=numeric["failure_budget"][0],
            retry_base_seconds=numeric["retry_base_seconds"][0], feed_url=feed_url,
            robots_rules_by_host=robots_rules, schema_version=schema_version,
            profile_version=profile_version, source_name=source_name, source_owner=source_owner,
            source_class=source_class, channel=channel, allowed_path_prefixes=path_prefixes,
            terms_evidence_url=terms_evidence_url, authenticated=authenticated, reuse_policy=reuse_policy,
            rights_status=rights_status, language=language,
            quota_per_host_day=quota_per_host_day, quota_per_mission=quota_per_mission,
            parser_schema_id=parser_schema_id, adapter_version=adapter_version,
            last_collected_at=last_collected_at,
        )

    def validate_for_fetch(self, *, now: datetime, allow_loopback_http: bool = False) -> None:
        if self.schema_version not in _SUPPORTED_SOURCE_PROFILE_SCHEMA_VERSIONS:
            raise ConnectorPolicyError("schema_version de SourceProfile n\u00e3o suportada.")
        if not isinstance(self.authenticated, bool) or self.authenticated:
            raise ConnectorPolicyError("Coleta Radar n\u00e3o aceita perfil autenticado; use somente acesso p\u00fablico sem credenciais.")
        if self.rights_status not in {"unknown", "pending", "authorized", "blocked"}:
            raise ConnectorPolicyError("rights_status inv\u00e1lido ou misturado com access_policy.")
        if self.reuse_policy not in _REUSE_POLICIES:
            raise ConnectorPolicyError("reuse_policy precisa ser metadata_only ou short_excerpt.")
        if self.reuse_policy == "short_excerpt" and self.rights_status != "authorized":
            raise ConnectorPolicyError("short_excerpt exige rights_status=authorized; leitura p\u00fablica \u00e9 uma pol\u00edtica separada.")
        if self.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
            SourceProfile.from_mapping(asdict(self))
        elif self.allowed_path_prefixes:
            for prefix in self.allowed_path_prefixes:
                _safe_path_prefix(prefix)
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
            raise ConnectorPolicyError("Fonte sem access_policy=allowed; nenhuma requisição foi feita.", code="access_policy_required")
        if self.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
            if self.rights_status == "blocked":
                raise ConnectorPolicyError("rights_status=blocked impede a coleta desta fonte.")
            if not self.allowed_path_prefixes:
                raise ConnectorPolicyError("SourceProfile v1.1 exige caminhos autorizados explícitos.")
            if not _path_is_allowed(self.target_url(), self.allowed_path_prefixes):
                raise ConnectorPolicyError("Caminho de coleta fora da allowlist da fonte.")
        if self.robots_policy != "allowed" or self.robots_checked_at is None:
            raise ConnectorPolicyError("Robots/política da fonte não foi verificada e aprovada; coleta bloqueada.", code="robots_policy_required")
        if not isinstance(self.robots_rules_by_host, Mapping) or not allowed_hosts.issubset(self.robots_rules_by_host):
            raise ConnectorPolicyError("Snapshot robots verificado é obrigatório para cada host permitido.")
        if self.terms_checked_at is None:
            raise ConnectorPolicyError("Termos da fonte não foram registrados; coleta bloqueada.", code="terms_unverified")
        for name, value in (("terms_checked_at", self.terms_checked_at), ("robots_checked_at", self.robots_checked_at)):
            checked = _aware_datetime(value, name, allow_date=True)
            checked_at = datetime.combine(checked, datetime.min.time(), tzinfo=timezone.utc) if isinstance(checked, date) and not isinstance(checked, datetime) else checked.astimezone(timezone.utc)
            if checked_at > now:
                raise ConnectorPolicyError(f"{name} não pode estar no futuro.", code="policy_check_date_in_future")
        if not isinstance(self.allowed_operations, (list, tuple)) or _REQUIRED_OPERATION[self.connector_kind] not in self.allowed_operations:
            raise ConnectorPolicyError("Operação de leitura não consta na allowlist desta fonte.", code="operation_not_allowed")
        if self.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
            if self.connector_kind == "public_api" and self.parser_schema_id not in _API_SCHEMA_IDS:
                raise ConnectorPolicyError("Parser JSON oficial sem schema reconhecido.")
            if self.connector_kind != "public_api" and self.parser_schema_id != _PARSER_SCHEMA_BY_KIND[self.connector_kind]:
                raise ConnectorPolicyError("parser_schema_id não corresponde ao adaptador permitido.")
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

    def policy_sha256(self) -> str:
        payload = json.dumps(asdict(self), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


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
    payload_bytes: int = 0
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    fetch_event_id: str | None = None
    transport_status: str = "not_started"
    parse_status: str = "not_attempted"
    parser_schema_id: str | None = None
    parse_reason_code: str | None = None
    candidate_count: int = 0
    rejected_count: int = 0
    rejected_reason_counts: Mapping[str, int] = field(default_factory=dict)
    feed_items: tuple["FeedItem", ...] = ()


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
                raise ConnectorPolicyError("SSRF bloqueada: host resolve para faixa não pública.", code="ssrf_blocked")
            if parts.scheme == "http" and not test_http:
                raise ConnectorPolicyError("HTTP sem TLS bloqueado fora do loopback de teste.", code="ssrf_blocked")
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
        before_external_request: Callable[[], None] | None = None,
        on_response_received: Callable[[Mapping[str, Any]], str | None] | None = None,
        mission_id: str | None = None,
        mission_request_limit: int | None = None,
    ) -> FetchResult:
        current_time = self._now(now)
        fetched_at = current_time.isoformat(timespec="seconds")
        request_id = uuid.uuid4().hex
        target = url or profile.target_url()
        state = self.state(profile.source_id)
        if state.suspended:
            return FetchResult(profile.source_id, "blocked", target, target, None, fetched_at,
                               error_code="source_suspended", request_id=request_id)
        if state.next_retry_at:
            next_retry = self._now(state.next_retry_at)
            if current_time < next_retry:
                return FetchResult(
                    profile.source_id, "rate_limited", target, target, None, fetched_at,
                    retry_at=state.next_retry_at, error_code="source_backoff", request_id=request_id,
                )
            state.next_retry_at = None
        try:
            profile.validate_for_fetch(now=current_time, allow_loopback_http=self.allow_loopback_http)
            if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
                mission_id = _nonempty(mission_id, "mission_id", max_length=256)
                if isinstance(mission_request_limit, bool) or not isinstance(mission_request_limit, int) or mission_request_limit < 1:
                    raise ConnectorPolicyError("mission_request_limit é obrigatório no SourceProfile v1.1.", code="mission_quota_required")
                if not isinstance(self.domain_quota_guard, PersistentDomainQuotaGuard):
                    raise ConnectorPolicyError("SourceProfile v1.1 exige reserva persistente de quota.", code="persistent_quota_required")
            _, initial_host, initial_port = _safe_url_parts(target, allow_loopback_http=self.allow_loopback_http)
            allowed_hosts = {host.rstrip(".").casefold() for host in profile.allowed_hosts}
            if initial_host not in allowed_hosts:
                raise ConnectorPolicyError("Host inicial não consta na allowlist da fonte.", code="host_not_allowed")
            if profile.allowed_path_prefixes and not _path_is_allowed(target, profile.allowed_path_prefixes):
                raise ConnectorPolicyError("Caminho inicial fora da allowlist da fonte.", code="path_not_allowed")
            if not profile.robots_allows(target, allow_loopback_http=self.allow_loopback_http):
                raise ConnectorPolicyError("Robots.txt bloqueia o caminho ou não há snapshot verificado.", code="robots_disallowed")
            origin = f"{urlsplit(target).scheme}://{initial_host}:{initial_port}"
            origin_cooldown = self.limiter.cooldown_remaining(origin)
            if origin_cooldown:
                return FetchResult(
                    profile.source_id, "rate_limited", target, target, None, fetched_at,
                    retry_at=self._retry_at(current_time, max(1, int(origin_cooldown + 0.999))),
                    error_code="origin_retry_after", request_id=request_id,
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
            return FetchResult(profile.source_id, "blocked", target, target, None, fetched_at,
                               error_code=error.code, request_id=request_id)
        wait_seconds = self.limiter.reserve(origin, profile.min_poll_interval_seconds)
        if wait_seconds:
            reason = "origin_retry_after" if self.limiter.cooldown_remaining(origin) else "origin_min_interval"
            return FetchResult(
                profile.source_id, "rate_limited", target, target, None, fetched_at,
                retry_at=self._retry_at(current_time, max(1, int(wait_seconds + 0.999))),
                error_code=reason, request_id=request_id,
            )
        visited: set[str] = set()
        current_url = target
        redirects = 0
        response: HttpResponse | None = None
        fetch_event_id: str | None = None
        request_origin = origin
        try:
            while True:
                if current_url in visited:
                    raise ConnectorPolicyError("Ciclo de redirect detectado.")
                visited.add(current_url)
                parts, host, port = _safe_url_parts(current_url, allow_loopback_http=self.allow_loopback_http)
                if host not in allowed_hosts:
                    raise ConnectorPolicyError("Redirect para host fora da allowlist.", code="redirect_host_not_allowed")
                if profile.allowed_path_prefixes and not _path_is_allowed(current_url, profile.allowed_path_prefixes):
                    raise ConnectorPolicyError("Caminho de redirect fora da allowlist da fonte.", code="path_not_allowed")
                if not profile.robots_allows(current_url, allow_loopback_http=self.allow_loopback_http):
                    raise ConnectorPolicyError("Robots.txt bloqueia o redirect ou não há snapshot verificado.", code="robots_disallowed")
                current_origin = f"{parts.scheme}://{host}:{port}"
                if redirects and current_origin != request_origin:
                    wait_seconds = self.limiter.reserve(current_origin, profile.min_poll_interval_seconds)
                    if wait_seconds:
                        reason = "origin_retry_after" if self.limiter.cooldown_remaining(current_origin) else "origin_min_interval"
                        return FetchResult(
                            profile.source_id, "rate_limited", target, current_url,
                            response.status_code if response else None, fetched_at,
                            retry_at=self._retry_at(current_time, max(1, int(wait_seconds + 0.999))),
                            redirect_count=redirects, error_code=reason, request_id=request_id,
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
                            host, now=current_time, request_key=f"{request_id}:hop:{redirects}:{host}",
                            mission_id=mission_id if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION else None,
                            mission_limit=mission_request_limit if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION else None,
                            source_id=profile.source_id if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION else None,
                            source_mission_limit=profile.quota_per_mission if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION else None,
                            daily_quota_limit=profile.quota_per_host_day if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION else None,
                        )
                    except Exception:
                        return FetchResult(
                            profile.source_id, "blocked", target, current_url,
                            response.status_code if response else None, fetched_at,
                            redirect_count=redirects, error_code="domain_quota_unavailable", request_id=request_id,
                        )
                    if not quota.allowed:
                        status = "rate_limited" if quota.reason == "domain_daily_quota" else "blocked"
                        return FetchResult(
                            profile.source_id, status, target, current_url,
                            response.status_code if response else None, fetched_at,
                            retry_at=quota.retry_at, redirect_count=redirects,
                            error_code=quota.reason or "domain_quota_blocked", request_id=request_id,
                        )
                elif profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
                    return FetchResult(
                        profile.source_id, "blocked", target, current_url,
                        response.status_code if response else None, fetched_at,
                        redirect_count=redirects, error_code="persistent_quota_required", request_id=request_id,
                    )
                if before_external_request is not None:
                    before_external_request()
                    before_external_request = None
                response = self.transport.request(
                    current_url, pinned_ip, headers=request_headers, timeout_seconds=profile.timeout_seconds,
                    max_response_bytes=profile.max_response_bytes, allow_loopback_http=self.allow_loopback_http,
                )
                if len(response.body) > profile.max_response_bytes:
                    raise ConnectorPolicyError("Resposta excedeu max_response_bytes.", code="response_too_large")
                location = self._header(response.headers, "location")
                if response.status_code not in _REDIRECT_CODES:
                    break
                if not location:
                    raise ConnectorPolicyError("Redirect sem Location.")
                if redirects >= profile.max_redirects:
                    raise ConnectorPolicyError("Limite de redirects excedido.")
                current_url = urljoin(current_url, location)
                redirects += 1
            if on_response_received is not None:
                fetch_status = (
                    "observed" if response.status_code == 200 else
                    "not_modified" if response.status_code == 304 else
                    "forbidden" if response.status_code in {401, 403} else
                    "removed" if response.status_code in {404, 410} else
                    "rate_limited" if response.status_code == 429 else "error"
                )
                transport_record = {
                    "source_id": profile.source_id, "request_id": request_id,
                    "request_url": target, "final_url": current_url, "observed_at": fetched_at,
                    "http_status": response.status_code, "content_type": self._content_type(response.headers),
                    "payload_bytes": len(response.body),
                    "response_sha256": hashlib.sha256(response.body).hexdigest() if response.body else None,
                    "fetch_status": fetch_status,
                }
                try:
                    fetch_event_id = on_response_received(transport_record)
                except Exception:
                    return FetchResult(
                        profile.source_id, "error", target, current_url, response.status_code, fetched_at,
                        error_code="fetch_event_persistence_failed", request_id=request_id,
                        transport_status="response_received", payload_sha256=transport_record["response_sha256"],
                        payload_bytes=len(response.body),
                    )
            return self._classify_response(
                profile, target, current_url, response, fetched_at, current_time, redirects, state, request_origin,
                request_id=request_id, fetch_event_id=fetch_event_id,
            )
        except ConnectorPolicyError as error:
            return FetchResult(profile.source_id, "blocked", target, current_url, response.status_code if response else None,
                               fetched_at, redirect_count=redirects, error_code=error.code,
                               request_id=request_id,
                               transport_status="response_received" if response is not None else "not_started")
        except (OSError, http.client.HTTPException, ssl.SSLError, TimeoutError, ValueError) as error:
            state.consecutive_failures += 1
            retry = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
            self.limiter.cooldown(request_origin, retry)
            if state.consecutive_failures >= profile.failure_budget:
                state.suspended = True
            state.next_retry_at = self._retry_at(current_time, retry)
            return FetchResult(profile.source_id, "error", target, current_url, None, fetched_at,
                               retry_at=state.next_retry_at, redirect_count=redirects,
                               error_code="transport_error", request_id=request_id,
                               transport_status="uncertain")

    def _classify_response(
        self, profile: SourceProfile, requested_url: str, final_url: str, response: HttpResponse,
        fetched_at: str, now: datetime, redirects: int, state: SourceRuntimeState, origin: str,
        *, request_id: str, fetch_event_id: str | None,
    ) -> FetchResult:
        status = response.status_code
        payload_bytes = len(response.body)
        headers = response.headers
        etag = self._header(headers, "etag")
        last_modified = self._header(headers, "last-modified")
        content_type = self._content_type(headers)
        retry_at = None
        error_code = None
        body = response.body
        metadata = None
        feed_items: tuple[FeedItem, ...] = ()
        parse_status = "not_attempted"
        parse_reason_code: str | None = None
        candidate_count = 0
        rejected_count = 0
        rejected_reason_counts: Mapping[str, int] = {}
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
                parse_status = "unsupported"
                parse_reason_code = "unsupported_content_type"
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
                        feed_items = tuple(metadata)
                        candidate_count = len(feed_items)
                        rejected_count = sum(1 for item in feed_items if not item.url)
                        rejected_reason_counts = ({"candidate_missing_safe_url": rejected_count} if rejected_count else {})
                    elif profile.connector_kind == "public_html":
                        metadata = parse_public_html(
                            body, base_url=final_url, maximum_bytes=profile.max_response_bytes,
                            allow_loopback_http=self.allow_loopback_http,
                        )
                        if metadata.title:
                            candidate_url = metadata.canonical_url or final_url
                            candidate_url = _safe_public_reference_url(candidate_url)
                            if candidate_url:
                                feed_items = (FeedItem(
                                    metadata.title, candidate_url, None, None,
                                ),)
                                candidate_count = 1
                            else:
                                rejected_count = 1
                                rejected_reason_counts = {"candidate_missing_safe_human_url": 1}
                        else:
                            parse_status = "parsed_empty"
                            parse_reason_code = "no_page_title"
                    else:
                        if profile.schema_version == SOURCE_PROFILE_SCHEMA_VERSION:
                            outcome = parse_public_api_records(
                                body, schema_id=str(profile.parser_schema_id),
                                maximum_bytes=profile.max_response_bytes,
                            )
                            metadata = outcome.metadata
                            feed_items = outcome.feed_items
                            candidate_count = len(feed_items)
                            rejected_count = outcome.rejected_count
                            rejected_reason_counts = outcome.rejected_reason_counts
                            if rejected_count:
                                parse_reason_code = "candidate_records_rejected"
                        else:
                            metadata = project_public_api_metadata(body, maximum_bytes=profile.max_response_bytes)
                        if profile.reuse_policy != "short_excerpt" or profile.rights_status != "authorized":
                            metadata = _strip_unapproved_excerpt(metadata)
                    result_status = "observed"
                    if parse_status != "parsed_empty":
                        parse_status = "parsed" if candidate_count or metadata not in (None, {}, [], ()) else "parsed_empty"
                    state.consecutive_failures = 0
                    state.next_retry_at = None
                except ConnectorPolicyError as error:
                    result_status = "error"
                    error_code = error.code
                    parse_status = "unsupported" if error.code == "parser_unsupported" else "invalid"
                    parse_reason_code = error.code
                    metadata = None
                    feed_items = ()
                    state.consecutive_failures += 1
                    retry = min(3_600, profile.retry_base_seconds * (2 ** (state.consecutive_failures - 1)))
                    retry_at = self._retry_at(now, retry)
                    state.next_retry_at = retry_at
                    self.limiter.cooldown(origin, retry)
                    if state.consecutive_failures >= profile.failure_budget:
                        state.suspended = True
        payload_sha256 = hashlib.sha256(response.body).hexdigest() if response.body else None
        return FetchResult(profile.source_id, result_status, requested_url, final_url, status, fetched_at,
                           content_type, etag, last_modified, retry_at, redirects, metadata, error_code,
                           payload_sha256, payload_bytes, request_id=request_id,
                           fetch_event_id=fetch_event_id,
                           transport_status="response_received", parse_status=parse_status,
                           parser_schema_id=profile.parser_schema_id or _PARSER_SCHEMA_BY_KIND.get(
                               profile.connector_kind, "legacy_public_api_projection_v1",
                           ),
                           parse_reason_code=parse_reason_code, candidate_count=candidate_count,
                           rejected_count=rejected_count, rejected_reason_counts=rejected_reason_counts,
                           feed_items=feed_items)


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
    technical_url: str | None = None


@dataclass(frozen=True)
class PublicApiParseOutcome:
    metadata: Any
    feed_items: tuple[FeedItem, ...]
    rejected_count: int
    rejected_reason_counts: Mapping[str, int]


def parse_public_api_records(
    payload: bytes, *, schema_id: str, maximum_bytes: int = 1_000_000,
) -> PublicApiParseOutcome:
    """Parse only explicitly supported public API record shapes and preserve URL roles."""
    raw = parse_public_json(payload, maximum_bytes=maximum_bytes)
    metadata = project_public_api_metadata(payload, maximum_bytes=maximum_bytes)
    rejected: dict[str, int] = {}
    records: list[Mapping[str, Any]] = []
    if schema_id == "github_release_v1":
        if not isinstance(raw, Mapping) or not isinstance(raw.get("tag_name"), str):
            raise ConnectorPolicyError(
                "Schema JSON não corresponde a github_release_v1.", code="parser_unsupported", phase="parse",
            )
        records = [raw]
    elif schema_id == "metadata_records_v1":
        if isinstance(raw, list):
            container = raw
        elif isinstance(raw, Mapping):
            containers = [raw[key] for key in ("items", "results", "entries", "records", "releases") if key in raw]
            if len(containers) != 1 or not isinstance(containers[0], list):
                raise ConnectorPolicyError(
                    "Schema JSON não corresponde a metadata_records_v1.", code="parser_unsupported", phase="parse",
                )
            container = containers[0]
        else:
            raise ConnectorPolicyError(
                "Schema JSON não corresponde a metadata_records_v1.", code="parser_unsupported", phase="parse",
            )
        if any(not isinstance(item, Mapping) for item in container[:10_000]):
            raise ConnectorPolicyError(
                "Schema metadata_records_v1 contém registro não estruturado.",
                code="parser_unsupported", phase="parse",
            )
        records = [item for item in container[:10_000] if isinstance(item, Mapping)]
    else:
        raise ConnectorPolicyError("Parser JSON sem esquema registrado.", code="parser_unsupported", phase="parse")

    items: list[FeedItem] = []
    for record in records:
        title_value = record.get("name") or record.get("title") or record.get("tag_name")
        human_url_value = record.get("html_url") or record.get("human_url") or record.get("link")
        human_url = (
            _safe_public_reference_url(human_url_value.strip())
            if isinstance(human_url_value, str) and human_url_value.strip() else None
        )
        if not isinstance(title_value, str) or not title_value.strip():
            rejected["candidate_missing_title"] = rejected.get("candidate_missing_title", 0) + 1
            continue
        if human_url is None:
            rejected["candidate_missing_safe_human_url"] = rejected.get("candidate_missing_safe_human_url", 0) + 1
            continue
        api_url_value = record.get("api_url") or record.get("url")
        technical_url = (
            _safe_public_reference_url(api_url_value.strip())
            if isinstance(api_url_value, str) and api_url_value.strip() and api_url_value != human_url else None
        )
        origin_value = record.get("origin_url") or record.get("source_url")
        origin_url = (
            _safe_public_reference_url(origin_value.strip())
            if isinstance(origin_value, str) and origin_value.strip() else None
        )
        author_value = record.get("author") or record.get("publisher") or record.get("developer")
        if isinstance(author_value, Mapping):
            author_value = author_value.get("name") or author_value.get("login")
        items.append(FeedItem(
            title=title_value.strip()[:1_000], url=human_url,
            external_id=str(record.get("id") or record.get("slug") or record.get("tag_name") or "")[:500] or None,
            published_at=str(record.get("published_at") or record.get("updated_at") or record.get("release_date") or "")[:256] or None,
            byline=str(author_value).strip()[:500] if isinstance(author_value, str) and author_value.strip() else None,
            origin_url=origin_url, technical_url=technical_url,
        ))
    return PublicApiParseOutcome(metadata, tuple(items), sum(rejected.values()), rejected)


def _strip_unapproved_excerpt(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: _strip_unapproved_excerpt(nested)
            for key, nested in value.items() if str(key).casefold() != "body_excerpt"
        }
    if isinstance(value, list):
        return [_strip_unapproved_excerpt(item) for item in value]
    return value


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
    "id", "title", "name", "url", "html_url", "link", "tag_name", "published_at", "updated_at", "release_date",
    "created_at", "prerelease", "draft",
    "version", "slug", "author", "publisher", "developer", "status", "type", "platform",
}
_SAFE_API_CONTAINERS = {"data", "items", "results", "entries", "records", "releases", "builds", "versions"}


def project_public_api_metadata(payload: bytes, *, maximum_bytes: int = 1_000_000) -> Any:
    """Return a small metadata projection while dropping article/body fields."""
    source = parse_public_json(payload, maximum_bytes=maximum_bytes)
    budget = [1_000]
    excerpt_words_left = [25]

    def project(value: Any, depth: int = 0) -> Any:
        if depth > 8 or budget[0] <= 0:
            return None
        budget[0] -= 1
        if isinstance(value, Mapping):
            result: dict[str, Any] = {}
            for key, nested in value.items():
                normalized = str(key).casefold().replace("-", "_")
                if normalized == "body" and isinstance(nested, str) and excerpt_words_left[0] > 0:
                    words = " ".join(nested.split()).split()
                    take = min(excerpt_words_left[0], len(words))
                    if take:
                        result["body_excerpt"] = " ".join(words[:take])
                        excerpt_words_left[0] -= take
                    continue
                if normalized == "author" and isinstance(nested, Mapping):
                    login = nested.get("login")
                    if isinstance(login, str) and login.strip():
                        result["author"] = login.strip()[:500]
                    continue
                if normalized in _SAFE_API_FIELDS:
                    if isinstance(nested, (str, int, float, bool)) or nested is None:
                        if normalized in {"url", "link", "html_url"}:
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
