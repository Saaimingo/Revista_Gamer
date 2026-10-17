"""Loopback-only local operator panel. There is intentionally no publish route."""

from __future__ import annotations

import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlencode, urlsplit

from .domain import MotorError
from .render import dashboard_html, render_panel_page, story_html
from .workflow import Motor


MAX_FORM_BYTES = 4096


def create_server(motor: Motor, port: int = 8765) -> ThreadingHTTPServer:
    csrf_token = secrets.token_urlsafe(24)

    class Handler(BaseHTTPRequestHandler):
        server_version = "MotorEditorial/0.2"
        sys_version = ""

        def log_message(self, _format: str, *_args: object) -> None:
            # The panel keeps operational output in its SQLite audit trail.
            return

        def _send(self, status: int, body: str, *, content_type: str = "text/html; charset=utf-8") -> None:
            encoded = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; style-src 'unsafe-inline'; img-src data:; "
                "form-action 'self'; base-uri 'none'; frame-ancestors 'none'",
            )
            self.end_headers()
            self.wfile.write(encoded)

        def _redirect(self, message: str) -> None:
            location = "/?" + urlencode({"message": message})
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                query = parse_qs(urlsplit(self.path).query)
                message = query.get("message", [""])[0]
                self._send(200, dashboard_html(motor.store.dashboard(), message, csrf_token))
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) == 2 and parts[0] == "stories":
                story_id = parts[1]
                detail = motor.store.story_detail(story_id)
                if detail is None:
                    self._send(404, render_panel_page("Não encontrado", "<main><p>Pauta não encontrada.</p><p><a href=\"/\">Voltar</a></p></main>"))
                    return
                self._send(200, story_html(detail))
                return
            if len(parts) == 3 and parts[0] == "editions" and parts[2] == "preview":
                try:
                    preview_revalidated = motor.revalidate_edition_preview_for_access(parts[1])
                except (MotorError, ValueError, OSError):
                    self._send(
                        409,
                        render_panel_page(
                            "Prévia desatualizada",
                            "<main><p>Não foi possível revalidar a prévia. Ela não será exibida; volte ao painel e resolva as pendências.</p><p><a href=\"/\">Voltar</a></p></main>",
                        ),
                    )
                    return
                edition = motor.store.get_edition(parts[1])
                if edition is None:
                    self._send(404, render_panel_page("Não encontrado", "<main><p>Edição não encontrada.</p></main>"))
                    return
                if edition["composition_status"] not in {
                    "legacy_v1", "ready_for_approval", "approved_internally"
                }:
                    self._send(409, render_panel_page("Prévia pendente", "<main><p>A edição aguarda resolução das pautas integrantes.</p><p><a href=\"/\">Voltar</a></p></main>"))
                    return
                try:
                    preview = motor.store.safe_artifact_path(edition["preview_path"])
                    body = preview.read_text(encoding="utf-8")
                except (OSError, ValueError):
                    self._send(404, render_panel_page("Prévia indisponível", "<main><p>O arquivo de prévia não está disponível.</p></main>"))
                    return
                if preview_revalidated:
                    notice = (
                        '<aside role="status" style="margin:16px;padding:12px;background:#fff4cc;'
                        'border:2px solid #a26700">A composição foi revalidada. Examine esta prévia '
                        'antes de registrar uma nova aprovação interna.</aside>'
                    )
                    body = body.replace("</body>", notice + "</body>", 1)
                self._send(200, body)
                return
            self._send(404, render_panel_page("Rota não encontrada", "<main><p>Esta rota não existe no Motor Editorial v0.2.</p><p><a href=\"/\">Voltar ao painel</a></p></main>"))

        def do_POST(self) -> None:
            length_header = self.headers.get("Content-Length", "0")
            try:
                length = int(length_header)
            except ValueError:
                self._send(400, render_panel_page("Requisição inválida", "<main><p>Tamanho de formulário inválido.</p></main>"))
                return
            if length < 0 or length > MAX_FORM_BYTES:
                self._send(413, render_panel_page("Formulário muito grande", "<main><p>O formulário excede o limite local.</p></main>"))
                return
            form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace"))
            if form.get("csrf", [""])[0] != csrf_token:
                self._send(403, render_panel_page("Confirmação expirada", "<main><p>Recarregue o painel antes de enviar a ação.</p><p><a href=\"/\">Voltar</a></p></main>"))
                return

            path = urlsplit(self.path).path
            if path == "/demo/run":
                try:
                    result = motor.run_multipauta_demo()
                except (MotorError, ValueError) as error:
                    self._send(
                        400,
                        dashboard_html(motor.store.dashboard(), str(error), csrf_token),
                    )
                    return
                self._redirect(result.message)
                return
            parts = [part for part in path.split("/") if part]
            if len(parts) == 3 and parts[0] == "stories" and parts[2] == "run":
                story = motor.store.get_story(parts[1])
                if story is None:
                    self._send(404, render_panel_page("Não encontrado", "<main><p>Pauta não encontrada.</p></main>"))
                    return
                try:
                    result = motor.run_multipauta_story(story["run_id"], story["id"])
                except (MotorError, ValueError) as error:
                    self._send(400, dashboard_html(motor.store.dashboard(), str(error), csrf_token))
                    return
                self._redirect(result.message)
                return
            if (len(parts) == 5 and parts[0] == "editions"
                    and parts[2] == "stories" and parts[4] == "exclude"):
                try:
                    motor.exclude_story_from_edition(
                        parts[1], parts[3], form.get("actor", [""])[0],
                        form.get("reason", [""])[0], form.get("confirmation", [""])[0],
                    )
                except MotorError as error:
                    self._send(400, dashboard_html(motor.store.dashboard(), str(error), csrf_token))
                    return
                self._redirect("Exclusão interna registrada; a pauta foi mantida no histórico.")
                return
            if len(parts) == 3 and parts[0] == "editions" and parts[2] == "approve":
                try:
                    motor.approve_internally(
                        parts[1],
                        form.get("actor", [""])[0],
                        form.get("confirmation", [""])[0],
                    )
                except MotorError as error:
                    self._send(400, dashboard_html(motor.store.dashboard(), str(error), csrf_token))
                    return
                self._redirect("Aprovação humana interna registrada. Nenhum conteúdo foi publicado.")
                return
            self._send(404, render_panel_page("Ação não disponível", "<main><p>Esta ação não existe no Motor Editorial v0.2.</p><p><a href=\"/\">Voltar ao painel</a></p></main>"))

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server


def serve(motor: Motor, port: int = 8765) -> None:
    server = create_server(motor, port)
    host, actual_port = server.server_address
    print(f"Painel local em http://{host}:{actual_port}/ (Ctrl+C para encerrar)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nPainel encerrado.")
    finally:
        server.server_close()
