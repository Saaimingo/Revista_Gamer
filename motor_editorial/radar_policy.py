"""Deterministic local-window and persistent domain-quota policies for Radar."""

from __future__ import annotations

import ipaddress
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Mapping, Protocol
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_LOCAL_TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")
_DOMAIN_LABEL_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class DomainQuotaStore(Protocol):
    def reserve_domain_request(
        self,
        *,
        domain: str,
        quota_date: str,
        timezone_name: str,
        quota_limit: int,
        request_key: str,
        reserved_at: str,
    ) -> bool: ...


class DomainQuotaGuard(Protocol):
    def reserve_request(
        self,
        domain: str,
        *,
        now: datetime | str,
        request_key: str | None = None,
    ) -> "QuotaDecision": ...


@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    retry_at: str | None = None
    reason: str | None = None


def load_timezone(name: str) -> ZoneInfo:
    if not isinstance(name, str) or not name or len(name) > 128:
        raise ValueError("Fuso horário IANA inválido.")
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(
            f"Fuso horário IANA desconhecido: {name}. Instale requirements-radar.txt."
        ) from error


def parse_local_time(value: str) -> time:
    if not isinstance(value, str) or not _LOCAL_TIME_RE.fullmatch(value):
        raise ValueError("Horário local deve usar o formato HH:MM de 24 horas.")
    hour, minute = (int(part) for part in value.split(":"))
    return time(hour, minute)


def normalize_domain(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Domínio precisa ser texto.")
    candidate = value.strip().rstrip(".")
    if not candidate or len(candidate) > 253 or any(ch.isspace() for ch in candidate):
        raise ValueError("Domínio inválido.")
    try:
        return ipaddress.ip_address(candidate).compressed.casefold()
    except ValueError:
        pass
    try:
        ascii_domain = candidate.encode("idna").decode("ascii").casefold()
    except UnicodeError as error:
        raise ValueError("Domínio inválido.") from error
    labels = ascii_domain.split(".")
    if not labels or any(not _DOMAIN_LABEL_RE.fullmatch(label) for label in labels):
        raise ValueError("Domínio inválido.")
    return ascii_domain


def normalize_domain_quotas(value: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(value, Mapping) or not value:
        raise ValueError("Informe pelo menos uma quota diária por domínio.")
    quotas: dict[str, int] = {}
    for raw_domain, limit in value.items():
        domain = normalize_domain(raw_domain)
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("Quota diária por domínio deve ser inteiro positivo.")
        if domain in quotas:
            raise ValueError("Domínios duplicados após normalização.")
        quotas[domain] = limit
    return dict(sorted(quotas.items()))


def _aware_utc(value: datetime | str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise ValueError("Relógio precisa fornecer data/hora com fuso explícito.")
    return parsed.astimezone(timezone.utc)


def next_daily_window_utc(
    local_time: str,
    timezone_name: str,
    reference: datetime | str,
    *,
    include_equal: bool = True,
) -> datetime:
    """Return the next local wall-clock window as UTC.

    Ambiguous fall-back times use the first occurrence (`fold=0`). A nonexistent
    spring-forward wall time shifts forward by the DST gap through a UTC roundtrip.
    """
    wall_time = parse_local_time(local_time)
    zone = load_timezone(timezone_name)
    instant = _aware_utc(reference)
    local_day = instant.astimezone(zone).date()
    for offset in range(370):
        day = local_day + timedelta(days=offset)
        candidate = datetime.combine(day, wall_time).replace(tzinfo=zone, fold=0)
        candidate_utc = candidate.astimezone(timezone.utc)
        roundtrip = candidate_utc.astimezone(zone)
        # Entirely skipped civil days have no occurrence in this zone.
        if roundtrip.date() != day:
            continue
        if candidate_utc > instant or (include_equal and candidate_utc == instant):
            return candidate_utc
    raise ValueError("Não foi possível calcular a próxima janela diária.")


class PersistentDomainQuotaGuard:
    """Atomic per-domain daily request caps stored in the isolated Radar DB."""

    def __init__(
        self,
        store: DomainQuotaStore,
        *,
        quotas: Mapping[str, int],
        timezone_name: str,
    ) -> None:
        self.store = store
        self.quotas = normalize_domain_quotas(quotas)
        self.timezone_name = timezone_name
        self.zone = load_timezone(timezone_name)

    def reserve_request(
        self,
        domain: str,
        *,
        now: datetime | str,
        request_key: str | None = None,
    ) -> QuotaDecision:
        current = _aware_utc(now)
        normalized_domain = normalize_domain(domain)
        local_day = current.astimezone(self.zone).date()
        reset_local = datetime.combine(
            local_day + timedelta(days=1), time.min, tzinfo=self.zone
        )
        retry_at = reset_local.astimezone(timezone.utc).isoformat(timespec="seconds")
        limit = self.quotas.get(normalized_domain)
        if limit is None:
            return QuotaDecision(False, retry_at, "domain_quota_not_configured")
        allowed = self.store.reserve_domain_request(
            domain=normalized_domain,
            quota_date=local_day.isoformat(),
            timezone_name=self.timezone_name,
            quota_limit=limit,
            request_key=request_key or str(uuid.uuid4()),
            reserved_at=current.isoformat(timespec="seconds"),
        )
        if not allowed:
            return QuotaDecision(False, retry_at, "domain_daily_quota")
        return QuotaDecision(True)
