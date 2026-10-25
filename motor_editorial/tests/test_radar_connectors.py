from __future__ import annotations

import socket
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Mapping

from motor_editorial.radar_connectors import (
    ConnectorPolicyError,
    HttpResponse,
    PerOriginLimiter,
    PinnedHTTPTransport,
    RadarConnectorService,
    SourceProfile,
    parse_public_html,
    parse_public_json,
    parse_rss_atom,
)


NOW = "2026-10-25T12:00:00+00:00"
PUBLIC_IP = "8.8.8.8"


def make_profile(
    *, source_id: str = "news-1", kind: str = "rss_atom", host: str = "news.example.invalid",
    access_policy: str = "allowed", robots_policy: str = "allowed", terms_checked_at: str | None = "2026-10-24",
    robots_checked_at: str | None = "2026-10-24", max_bytes: int = 1_000_000,
    min_interval: int = 1, max_redirects: int = 3, robots_rules: str = "User-agent: *\nAllow: /",
) -> SourceProfile:
    mapping: dict[str, Any] = {
        "source_id": source_id,
        "connector_kind": kind,
        "root_url": f"https://{host}/feed" if kind == "rss_atom" else f"https://{host}/",
        "allowed_hosts": [host],
        "allowed_operations": [{"rss_atom": "feed_read", "public_api": "api_metadata_read", "public_html": "page_metadata_read"}[kind]],
        "access_policy": access_policy,
        "terms_checked_at": terms_checked_at,
        "robots_policy": robots_policy,
        "robots_checked_at": robots_checked_at,
        "robots_rules_by_host": {host: robots_rules},
        "min_poll_interval_seconds": min_interval,
        "max_response_bytes": max_bytes,
        "timeout_seconds": 2,
        "max_redirects": max_redirects,
    }
    if kind == "rss_atom":
        mapping["feed_url"] = f"https://{host}/feed"
    return SourceProfile.from_mapping(mapping)


class FakeResolver:
    def __init__(self, mapping: Mapping[str, str] | None = None):
        self.mapping = dict(mapping or {})
        self.calls: list[tuple[str, int]] = []

    def __call__(self, host: str, port: int, *, type: int) -> list[tuple[Any, ...]]:
        self.calls.append((host, port))
        address = self.mapping.get(host, PUBLIC_IP)
        family = socket.AF_INET6 if ":" in address else socket.AF_INET
        sockaddr = (address, port, 0, 0) if family == socket.AF_INET6 else (address, port)
        return [(family, socket.SOCK_STREAM, 6, "", sockaddr)]


class FakeTransport:
    def __init__(self, *responses: HttpResponse | BaseException):
        self.responses = list(responses)
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def request(
        self, url: str, pinned_address: str, *, headers: Mapping[str, str], timeout_seconds: float,
        max_response_bytes: int, allow_loopback_http: bool = False,
    ) -> HttpResponse:
        self.calls.append((url, pinned_address, dict(headers)))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


class RadarConnectorTests(unittest.TestCase):
    def service(
        self, transport: FakeTransport, resolver: FakeResolver | None = None,
        limiter: PerOriginLimiter | None = None,
    ) -> RadarConnectorService:
        return RadarConnectorService(transport=transport, resolver=resolver or FakeResolver(), limiter=limiter)

    def test_profile_requires_explicit_access_terms_robots_and_operation(self) -> None:
        profile = make_profile(access_policy="unreviewed")
        transport = FakeTransport(HttpResponse(200, {"content-type": "application/rss+xml"}, b""))
        resolver = FakeResolver()
        result = RadarConnectorService(transport=transport, resolver=resolver).fetch(profile, now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("access_policy", result.error_code or "")
        self.assertEqual(transport.calls, [])
        self.assertEqual(resolver.calls, [])

        missing_terms = make_profile(terms_checked_at=None)
        result = self.service(FakeTransport(), FakeResolver()).fetch(missing_terms, now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("Termos", result.error_code or "")
        future_terms = make_profile(source_id="future", terms_checked_at="2026-10-26")
        result = self.service(FakeTransport(), FakeResolver()).fetch(future_terms, now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("futuro", result.error_code or "")
        missing_operation = SourceProfile.from_mapping({
            "source_id": "no-op", "connector_kind": "rss_atom", "root_url": "https://news.example.invalid/feed",
            "feed_url": "https://news.example.invalid/feed", "allowed_hosts": ["news.example.invalid"],
            "allowed_operations": [], "access_policy": "allowed", "terms_checked_at": "2026-10-24",
            "robots_policy": "allowed", "robots_checked_at": "2026-10-24",
            "robots_rules_by_host": {"news.example.invalid": "User-agent: *\nAllow: /"},
        })
        result = self.service(FakeTransport(), FakeResolver()).fetch(missing_operation, now=NOW)
        self.assertIn("allowlist", result.error_code or "")

    def test_robots_rules_block_disallowed_paths_before_fetch_and_redirect(self) -> None:
        rules = "User-agent: *\nDisallow: /private\nAllow: /"
        profile = make_profile(kind="public_html", source_id="robots", robots_rules=rules)
        transport = FakeTransport(HttpResponse(200, {"content-type": "text/html"}, b"<title>private</title>"))
        resolver = FakeResolver()
        result = RadarConnectorService(transport=transport, resolver=resolver).fetch(
            profile, url="https://news.example.invalid/private/article", now=NOW,
        )
        self.assertEqual(result.status, "blocked")
        self.assertIn("Robots.txt bloqueia", result.error_code or "")
        self.assertEqual(resolver.calls, [])
        self.assertEqual(transport.calls, [])

        redirect_transport = FakeTransport(
            HttpResponse(302, {"location": "/private/article"}, b""),
            HttpResponse(200, {"content-type": "text/html"}, b"should not fetch"),
        )
        result = self.service(redirect_transport).fetch(profile, url="https://news.example.invalid/public", now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(len(redirect_transport.calls), 1)

    def test_success_304_and_conditional_headers(self) -> None:
        xml = b"<rss><channel><item><title>Atualizacao</title><link>https://news.example.invalid/story/1</link><guid>item-1</guid><pubDate>2026-10-25</pubDate><description>texto que nao retemos</description></item></channel></rss>"
        transport = FakeTransport(
            HttpResponse(200, {"Content-Type": "application/rss+xml; charset=utf-8", "ETag": '"rev-1"'}, xml),
            HttpResponse(304, {"ETag": '"rev-1"'}, b""),
        )
        monotonic = [0.0]
        service = self.service(transport, limiter=PerOriginLimiter(monotonic=lambda: monotonic[0]))
        first = service.fetch(make_profile(), now=NOW)
        self.assertEqual(first.status, "observed")
        self.assertEqual(first.etag, '"rev-1"')
        entries = first.metadata
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].title, "Atualizacao")
        self.assertEqual(entries[0].url, "https://news.example.invalid/story/1")
        self.assertEqual(entries[0].external_id, "item-1")
        self.assertRegex(entries[0].body_sha256 or "", r"^[a-f0-9]{64}$")
        self.assertRegex(entries[0].content_sha256 or "", r"^[a-f0-9]{64}$")
        self.assertTrue(entries[0].body_segment_hashes)
        self.assertRegex(first.payload_sha256 or "", r"^[a-f0-9]{64}$")
        self.assertFalse(hasattr(entries[0], "description"))
        self.assertFalse(hasattr(entries[0], "body"))
        self.assertFalse(hasattr(first, "body"))

        monotonic[0] += 3_600
        second = service.fetch(make_profile(source_id="news-2"), etag='"rev-1"', now="2026-10-25T13:00:00+00:00")
        self.assertEqual(second.status, "not_modified")
        self.assertIsNone(second.metadata)
        self.assertEqual(transport.calls[1][2]["If-None-Match"], '"rev-1"')
        self.assertNotIn("Authorization", transport.calls[0][2])
        self.assertNotIn("Cookie", transport.calls[0][2])

        api = self.service(FakeTransport(HttpResponse(
            200, {"content-type": "application/json"},
            b'{"data":{"id":"build-1","title":"Build 1.2","description":"article text is omitted"}}',
        )))
        api_result = api.fetch(make_profile(kind="public_api", source_id="public-api"), now=NOW)
        self.assertEqual(api_result.status, "observed")
        self.assertEqual(api_result.metadata, {"data": {"id": "build-1", "title": "Build 1.2"}})

    def test_http_statuses_retry_after_and_source_suspension(self) -> None:
        cases = [
            (HttpResponse(403, {}, b"private body"), "forbidden", "source_access_denied"),
            (HttpResponse(404, {}, b"removed"), "removed", "source_removed"),
            (HttpResponse(410, {}, b"removed"), "removed", "source_removed"),
            (HttpResponse(500, {}, b"server detail"), "error", "provider_server_error"),
            (HttpResponse(429, {"Retry-After": "120"}, b"rate detail"), "rate_limited", "provider_rate_limit"),
        ]
        for index, (response, status, error_code) in enumerate(cases):
            with self.subTest(status=response.status_code):
                transport = FakeTransport(response)
                service = self.service(transport)
                result = service.fetch(make_profile(source_id=f"source-{index}"), now=NOW)
                self.assertEqual(result.status, status)
                self.assertEqual(result.error_code, error_code)
                self.assertIsNone(result.metadata)
                if response.status_code == 429:
                    self.assertEqual(result.retry_at, "2026-10-25T12:02:00+00:00")
                if response.status_code == 500:
                    self.assertEqual(result.retry_at, "2026-10-25T12:00:30+00:00")

        transport = FakeTransport(HttpResponse(403, {}, b""), HttpResponse(200, {"content-type": "text/html"}, b""))
        service = self.service(transport)
        profile = make_profile(source_id="suspended", kind="public_html")
        self.assertEqual(service.fetch(profile, now=NOW).status, "forbidden")
        self.assertEqual(service.fetch(profile, now="2026-10-26T12:00:00+00:00").error_code, "source_suspended")
        self.assertEqual(len(transport.calls), 1)

    def test_retry_after_cooldown_is_shared_between_profiles_on_origin(self) -> None:
        transport = FakeTransport(
            HttpResponse(429, {"retry-after": "120"}, b""),
            HttpResponse(200, {"content-type": "text/html"}, b"<title>not called</title>"),
        )
        service = self.service(transport)
        self.assertEqual(service.fetch(make_profile(source_id="first"), now=NOW).status, "rate_limited")
        second = make_profile(source_id="second", kind="public_html")
        result = service.fetch(second, now="2026-10-25T12:00:10+00:00")
        self.assertEqual(result.status, "rate_limited")
        self.assertEqual(result.error_code, "origin_retry_after")
        self.assertEqual(len(transport.calls), 1)

    def test_redirects_are_revalidated_and_ssrf_is_blocked_before_transport(self) -> None:
        transport = FakeTransport(HttpResponse(302, {"location": "https://attacker.example.invalid/private"}, b""))
        resolver = FakeResolver()
        result = RadarConnectorService(transport=transport, resolver=resolver).fetch(make_profile(), now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("fora da allowlist", result.error_code or "")
        self.assertEqual(len(transport.calls), 1)

        resolution_number = [0]

        def rebinding_resolver(host: str, port: int, *, type: int) -> list[tuple[Any, ...]]:
            resolution_number[0] += 1
            address = PUBLIC_IP if resolution_number[0] == 1 else "127.0.0.1"
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

        rebinding_transport = FakeTransport(HttpResponse(302, {"location": "/redirected"}, b""))
        rebound = RadarConnectorService(transport=rebinding_transport, resolver=rebinding_resolver).fetch(
            make_profile(source_id="rebinding"), now=NOW,
        )
        self.assertEqual(rebound.status, "blocked")
        self.assertIn("SSRF", rebound.error_code or "")
        self.assertEqual(len(rebinding_transport.calls), 1)

    def test_allowed_cross_origin_redirect_obeys_each_origin_rate_limit(self) -> None:
        profile = SourceProfile.from_mapping({
            "source_id": "redirect-source", "connector_kind": "public_html",
            "root_url": "https://news.example.invalid/", "allowed_hosts": ["news.example.invalid", "cdn.example.invalid"],
            "allowed_operations": ["page_metadata_read"], "access_policy": "allowed",
            "terms_checked_at": "2026-10-24", "robots_policy": "allowed", "robots_checked_at": "2026-10-24",
            "min_poll_interval_seconds": 60,
            "robots_rules_by_host": {
                "news.example.invalid": "User-agent: *\nAllow: /",
                "cdn.example.invalid": "User-agent: *\nAllow: /",
            },
        })
        transport = FakeTransport(
            HttpResponse(302, {"location": "https://cdn.example.invalid/page"}, b""),
            HttpResponse(200, {"content-type": "text/html"}, b"<title>Final page</title>"),
            HttpResponse(200, {"content-type": "text/html"}, b"<title>too soon</title>"),
        )
        service = self.service(transport)
        result = service.fetch(profile, etag='"news-etag"', now=NOW)
        self.assertEqual(result.status, "observed")
        self.assertEqual(result.metadata.title, "Final page")
        self.assertNotIn("If-None-Match", transport.calls[1][2])

        cdn_profile = SourceProfile.from_mapping({
            "source_id": "cdn-source", "connector_kind": "public_html", "root_url": "https://cdn.example.invalid/",
            "allowed_hosts": ["cdn.example.invalid"], "allowed_operations": ["page_metadata_read"],
            "access_policy": "allowed", "terms_checked_at": "2026-10-24", "robots_policy": "allowed",
            "robots_checked_at": "2026-10-24", "min_poll_interval_seconds": 60,
            "robots_rules_by_host": {"cdn.example.invalid": "User-agent: *\nAllow: /"},
        })
        result = service.fetch(cdn_profile, now=NOW)
        self.assertEqual(result.status, "rate_limited")
        self.assertEqual(result.error_code, "origin_min_interval")
        self.assertEqual(len(transport.calls), 2)

        private_resolver = FakeResolver({"news.example.invalid": "10.0.0.7"})
        private_transport = FakeTransport(HttpResponse(200, {"content-type": "application/rss+xml"}, b""))
        result = RadarConnectorService(transport=private_transport, resolver=private_resolver).fetch(make_profile(), now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("SSRF", result.error_code or "")
        self.assertEqual(private_transport.calls, [])

        secret_profile = make_profile(kind="public_html")
        for secret_url in (
            "https://news.example.invalid/?api_key=fixture",
            "https://news.example.invalid/?key=fixture",
            "https://news.example.invalid/?X-Amz-Signature=fixture",
        ):
            with self.subTest(secret_url=secret_url):
                transport = FakeTransport()
                result = self.service(transport, FakeResolver()).fetch(secret_profile, url=secret_url, now=NOW)
                self.assertEqual(result.status, "blocked")
                self.assertEqual(transport.calls, [])

    def test_response_size_timeout_and_failure_budget_are_bounded(self) -> None:
        oversized = FakeTransport(HttpResponse(200, {"content-type": "text/html"}, b"x" * 101))
        profile = make_profile(kind="public_html", max_bytes=100)
        result = self.service(oversized).fetch(profile, now=NOW)
        self.assertEqual(result.status, "blocked")
        self.assertIn("max_response_bytes", result.error_code or "")

        timeout = FakeTransport(
            TimeoutError("private network detail"), TimeoutError("private network detail"),
            TimeoutError("private network detail"),
        )
        profile = make_profile(kind="public_html", source_id="timeout", min_interval=1)
        monotonic = [0.0]
        service = self.service(timeout, limiter=PerOriginLimiter(monotonic=lambda: monotonic[0]))
        result = service.fetch(profile, now=NOW)
        self.assertEqual(result.status, "error")
        self.assertEqual(result.error_code, "transport_error")
        self.assertEqual(result.retry_at, "2026-10-25T12:00:30+00:00")
        monotonic[0] = 31.0
        self.assertEqual(service.fetch(profile, now="2026-10-25T12:00:31+00:00").status, "error")
        monotonic[0] = 120.0
        self.assertEqual(service.fetch(profile, now="2026-10-25T12:02:00+00:00").status, "error")
        self.assertTrue(service.state("timeout").suspended)
        self.assertEqual(len(timeout.calls), 3)

    def test_origin_limiter_keeps_strictest_interval_and_cooldown(self) -> None:
        clock = [0.0]
        limiter = PerOriginLimiter(monotonic=lambda: clock[0])
        self.assertEqual(limiter.reserve("https://example.invalid:443", 60), 0)
        clock[0] = 1.0
        self.assertEqual(limiter.reserve("https://example.invalid:443", 1), 59.0)
        limiter.cooldown("https://example.invalid:443", 120)
        self.assertEqual(limiter.reserve("https://example.invalid:443", 1), 120.0)

    def test_rss_atom_parser_and_markup_safety(self) -> None:
        atom = b'''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Release</title><id>tag:example,1</id><updated>2026-10-25T12:00:00Z</updated><link rel="alternate" href="https://news.example.invalid/release"/><link rel="enclosure" href="https://news.example.invalid/video.mp4"/></entry></feed>'''
        items = parse_rss_atom(atom)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].url, "https://news.example.invalid/release")
        self.assertEqual(items[0].external_id, "tag:example,1")
        secret_link = b'<rss><channel><item><title>Link</title><link>https://news.example.invalid/?token=fixture</link></item></channel></rss>'
        self.assertIsNone(parse_rss_atom(secret_link)[0].url)
        with self.assertRaisesRegex(ConnectorPolicyError, "DTD"):
            parse_rss_atom(b'<!DOCTYPE feed [<!ENTITY x "expanded">]><rss><item><title>&x;</title></item></rss>')

    def test_html_and_json_extract_metadata_without_retaining_article_text(self) -> None:
        html = b'<html><head><title>Patch 1.2</title><meta name="description" content="long copyrighted prose"><link rel="canonical" href="https://news.example.invalid/patch"></head><body><a href="https://news.example.invalid/details">details</a><a href="javascript:alert(1)">bad</a><a href="https://news.example.invalid/?token=fixture">secret</a><a href="https://127.0.0.1/internal">private</a></body></html>'
        metadata = parse_public_html(html, base_url="https://news.example.invalid/article")
        self.assertEqual(metadata.title, "Patch 1.2")
        self.assertEqual(metadata.canonical_url, "https://news.example.invalid/patch")
        self.assertEqual(metadata.discovered_links, ("https://news.example.invalid/details",))
        self.assertFalse(hasattr(metadata, "description"))
        self.assertEqual(parse_public_json(b'{"data":{"id":1}}'), {"data": {"id": 1}})
        with self.assertRaisesRegex(ConnectorPolicyError, "credenciais"):
            parse_public_json(b'{"token":"secret-value"}')
        with self.assertRaisesRegex(ConnectorPolicyError, "URL"):
            parse_public_html(b"<title>x</title>", base_url="file:///private")

    def test_pinned_transport_reads_only_loopback_in_explicit_test_mode(self) -> None:
        body = b"<html><title>Loopback fixture</title></html>"

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, format: str, *args: object) -> None:
                return

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/feed"
            profile = SourceProfile(
                "loopback", "public_html", url, ("127.0.0.1",), ("page_metadata_read",), "allowed",
                "2026-10-24", "allowed", "2026-10-24", 1, 1_000, 2.0,
                robots_rules_by_host={"127.0.0.1": "User-agent: *\nAllow: /"},
            )
            service = RadarConnectorService(
                transport=PinnedHTTPTransport(allow_loopback_http=True), allow_loopback_http=True,
            )
            result = service.fetch(profile, now=NOW)
            self.assertEqual(result.status, "observed")
            self.assertEqual(result.metadata.title, "Loopback fixture")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
