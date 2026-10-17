"""Escape-safe HTML renderers for the internal panel and demo preview."""

from __future__ import annotations

import html
import json
import re
from typing import Any

from .domain import EDITION_LABELS, STORY_LABELS


STYLE = """
:root { color-scheme: light; font-family: system-ui, sans-serif; color: #20242b; background: #f3f5f8; }
body { max-width: 980px; margin: 0 auto; padding: 24px; line-height: 1.5; }
header, main, section, article, aside { background: white; border: 1px solid #d9dee7; border-radius: 10px; padding: 18px; margin: 14px 0; }
h1, h2, h3 { line-height: 1.2; }
a { color: #174ea6; }
button, input[type=submit] { border: 0; border-radius: 6px; background: #164ea3; color: white; padding: 10px 14px; font: inherit; cursor: pointer; }
button:focus, a:focus, input:focus { outline: 3px solid #f4c542; outline-offset: 2px; }
input[type=text] { box-sizing: border-box; width: min(100%, 420px); padding: 9px; margin: 4px 0 10px; }
label { display: block; font-weight: 600; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: left; border-bottom: 1px solid #e4e8ef; padding: 8px; vertical-align: top; }
.banner { background: #fff4cc; border: 2px solid #a26700; color: #442d00; font-weight: 800; letter-spacing: .04em; text-align: center; }
.muted { color: #586174; }
.status { display: inline-block; border-radius: 999px; background: #e9eef7; padding: 2px 9px; }
.problem { border-left: 4px solid #b3261e; padding: 8px 12px; background: #fff6f5; }
.art { min-height: 150px; background: linear-gradient(135deg, #c7d4f2, #e9cbaa); border-radius: 10px; display: grid; place-items: center; overflow: hidden; }
.art svg { width: min(100%, 520px); height: 160px; }
.placeholder { border: 2px dashed #8b5e00; background: #fff8e6; padding: 14px; border-radius: 8px; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; }
@media (max-width: 600px) { body { padding: 12px; } table { font-size: .92rem; } }
"""


def _e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def _paragraphs(content: str) -> str:
    chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
    return "\n".join(f"<p>{_e(chunk).replace(chr(10), '<br>')}</p>" for chunk in chunks)


def render_preview(edition_id: str, detail: dict[str, Any], scenario_label: str) -> str:
    story = detail["story"]
    current_version = story["current_revision_number"]
    revision = next(
        row for row in detail["revisions"] if row["version"] == current_version
    )
    sources = "\n".join(
        "<li><strong>" + _e(row["source_label"]) + "</strong> — "
        + _e(row["title"]) + " <span class=\"muted\">(referência fictícia: "
        + _e(row["source_reference"]) + ")</span></li>"
        for row in detail["sources"]
    )
    media_blocks: list[str] = []
    for media in detail["media"]:
        if media["decision"] == "include":
            media_blocks.append(
                "<figure class=\"art\" data-asset-id=\"" + _e(media["asset_id"]) + "\" role=\"img\" "
                "aria-label=\"Ilustração geométrica original de teste\">"
                "<svg viewBox=\"0 0 600 180\" aria-hidden=\"true\" focusable=\"false\">"
                "<rect width=\"600\" height=\"180\" fill=\"#dbe6ff\"/>"
                "<circle cx=\"135\" cy=\"90\" r=\"52\" fill=\"#4c64a8\"/>"
                "<path d=\"M0 150 L160 65 L290 155 L430 55 L600 150 V180 H0Z\" fill=\"#273c67\"/>"
                "<text x=\"320\" y=\"105\" fill=\"#fff\" font-size=\"24\" text-anchor=\"middle\">"
                "ARTE ORIGINAL DE TESTE</text></svg></figure>"
            )
        elif media["decision"] == "placeholder":
            media_blocks.append(
                "<div class=\"placeholder\" role=\"note\"><strong>Placeholder interno</strong> — "
                + _e(media["title"]) + ": " + _e(media["reason"])
                + " Nenhum arquivo do ativo foi incorporado.</div>"
            )
    media_status = "\n".join(
        "<li>" + _e(row["title"]) + ": " +
        (
            "incluído para " + _e(row["usage_mode"])
            if row["decision"] == "include"
            else "substituído por placeholder: " + _e(row["reason"])
            if row["decision"] == "placeholder"
            else "omitido: " + _e(row["reason"])
        ) + "</li>"
        for row in detail["media"]
    )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Prévia interna — {_e(edition_id)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="banner" role="note">SIMULAÇÃO — NÃO PUBLICAR</header>
  <main>
    <p class="muted">{_e(scenario_label)} · edição {_e(edition_id)}</p>
    <h1>Revista Gamer — edição de demonstração</h1>
    <article>
      <h2>{_e(story['question'])}</h2>
      {_paragraphs(revision['content'])}
      {''.join(media_blocks)}
      <h3>Fontes fictícias da demonstração</h3>
      <ul>{sources}</ul>
      <h3>Estado de direitos nesta simulação</h3>
      <ul>{media_status}</ul>
      <p class="muted">Versão de matéria {_e(current_version)} · estado {_e(STORY_LABELS.get(story['state'], story['state']))}</p>
    </article>
  </main>
</body>
</html>
"""


def render_edition_preview(
    edition_id: str,
    ordered_details: list[tuple[int, dict[str, Any]]],
    scenario_label: str,
) -> str:
    """Render the active edition membership in persisted editorial order."""
    sections: list[str] = []
    for position, detail in ordered_details:
        story = detail["story"]
        revision_number = story["current_revision_number"]
        legacy = render_preview(edition_id, detail, scenario_label)
        match = re.search(r"<article>(.*?)</article>", legacy, flags=re.DOTALL)
        if match is None:
            raise ValueError("A matéria não pôde ser renderizada para a prévia interna.")
        sections.append(
            '<section class="edition-story" data-story-id="' + _e(story["id"]) + '">'
            + f'<p class="muted">Matéria {_e(position)} · ID {_e(story["id"])} · '
            + f'versão vigente {_e(revision_number)}</p>'
            + match.group(1)
            + "</section>"
        )
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>Prévia interna — {_e(edition_id)}</title>
  <style>{STYLE}</style>
</head>
<body>
  <header class="banner" role="note">SIMULAÇÃO — NÃO PUBLICAR</header>
  <main>
    <p class="muted">{_e(scenario_label)} · edição {_e(edition_id)}</p>
    <h1>Revista Gamer — edição multipauta de demonstração</h1>
    <p>Ordem editorial persistida; cada matéria exibe sua revisão vigente, fontes fictícias e estado próprio de direitos de mídia.</p>
    {''.join(sections)}
  </main>
</body>
</html>
"""


def render_panel_page(title: str, content: str, *, message: str = "") -> str:
    notice = f'<p role="status" class="banner">{_e(message)}</p>' if message else ""
    return f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="noindex,nofollow">
  <title>{_e(title)} — Motor Editorial</title>
  <style>{STYLE}</style>
</head>
<body>
  <header><p class="muted">Revista Gamer · ferramenta local</p><h1>{_e(title)}</h1></header>
  {notice}
  {content}
</body>
</html>
"""


def dashboard_html(data: dict[str, Any], message: str = "", csrf_token: str = "") -> str:
    state_counts = "".join(
        f"<tr><th>{_e(row['state'])}</th><td>{_e(row['total'])}</td></tr>"
        for row in data["items"]
    ) or "<tr><td colspan=2>Nenhum item importado.</td></tr>"
    stories = "".join(
        "<tr><td><a href=\"/stories/" + _e(row["id"]) + "\">" + _e(row["id"]) +
        "</a></td><td>" + _e(row["question"]) + "</td><td><span class=\"status\">" +
        _e(STORY_LABELS.get(row["state"], row["state"])) + "</span></td><td>" +
        _e(row["processing_status"]) + "</td><td>" +
        (f"<form method=\"post\" action=\"/stories/{_e(row['id'])}/run\">"
         f"<input type=\"hidden\" name=\"csrf\" value=\"{_e(csrf_token)}\">"
         "<button type=\"submit\">Executar/retomar esta pauta</button></form>"
         if row["multipauta_member"] and row["processing_status"] in {"in_progress", "recoverable_failure"} else "—")
        + "</td></tr>"
        for row in data["stories"]
    ) or "<tr><td colspan=5>Nenhuma pauta criada.</td></tr>"
    editions = "".join(
        "<tr><td>" + _e(row["id"]) + "</td><td>" +
        _e(EDITION_LABELS.get(row["status"], row["status"])) + "</td><td><a href=\"/editions/" +
        _e(row["id"]) + "/preview\">Abrir prévia interna</a></td><td>" +
        (f"<form method=\"post\" action=\"/editions/{_e(row['id'])}/approve\">"
         f"<input type=\"hidden\" name=\"csrf\" value=\"{_e(csrf_token)}\">"
         "<label>Nome do diretor/aprovador <input type=\"text\" name=\"actor\" required></label>"
         "<label>Digite APROVAR APENAS INTERNAMENTE <input type=\"text\" name=\"confirmation\" required></label>"
         "<button type=\"submit\">Registrar aprovação interna</button></form>"
         if row["status"] == "awaiting_human_approval" else "—") + "</td></tr>"
        for row in data["editions"]
    ) or "<tr><td colspan=4>Nenhuma edição montada.</td></tr>"
    editions = "".join(
        "<tr><td>" + _e(row["id"]) + "</td><td>" +
        _e(EDITION_LABELS.get(
            row["status"] if row["composition_status"] == "legacy_v1" else row["composition_status"],
            row["status"],
        )) + "</td><td>" +
        ("<a href=\"/editions/" + _e(row["id"]) + "/preview\">Abrir prévia interna</a>"
         if row["composition_status"] in {"legacy_v1", "ready_for_approval", "approved_internally"}
         else "Prévia indisponível enquanto houver bloqueios") + "</td><td>" +
        (f"<form method=\"post\" action=\"/editions/{_e(row['id'])}/approve\">"
         f"<input type=\"hidden\" name=\"csrf\" value=\"{_e(csrf_token)}\">"
         "<label>Nome do diretor/aprovador <input type=\"text\" name=\"actor\" required></label>"
         "<label>Digite APROVAR APENAS INTERNAMENTE <input type=\"text\" name=\"confirmation\" required></label>"
         "<button type=\"submit\">Registrar aprovação interna</button></form>"
         if row["status"] == "awaiting_human_approval"
         and row["composition_status"] in {"legacy_v1", "ready_for_approval"} else "—")
        + "</td></tr>"
        for row in data["editions"]
    ) or "<tr><td colspan=4>Nenhuma edição montada.</td></tr>"
    edition_by_id = {row["id"]: dict(row) for row in data["editions"]}
    active_required_counts: dict[str, int] = {}
    for member in data.get("edition_memberships", []):
        if member["active"] and member["required"]:
            active_required_counts[member["edition_id"]] = active_required_counts.get(member["edition_id"], 0) + 1
    membership_rows = []
    for member in data.get("edition_memberships", []):
        edition = edition_by_id.get(member["edition_id"], {})
        is_open = edition.get("composition_status") in {
            "preparing", "waiting_on_blockers", "ready_for_approval"
        }
        if not member["active"]:
            action = "Excluída por " + _e(member["excluded_by"]) + ": " + _e(member["exclusion_reason"])
        elif is_open and member["required"] and active_required_counts.get(member["edition_id"], 0) > 2:
            action = (
                f"<form method=\"post\" action=\"/editions/{_e(member['edition_id'])}/stories/{_e(member['story_id'])}/exclude\">"
                f"<input type=\"hidden\" name=\"csrf\" value=\"{_e(csrf_token)}\">"
                "<label>Responsável <input type=\"text\" name=\"actor\" required></label>"
                "<label>Motivo <input type=\"text\" name=\"reason\" minlength=\"8\" required></label>"
                "<label>Digite EXCLUIR PAUTA DA EDICAO <input type=\"text\" name=\"confirmation\" required></label>"
                "<button type=\"submit\">Excluir somente desta edição</button></form>"
            )
        else:
            action = "—"
        membership_rows.append(
            "<tr><td>" + _e(member["edition_id"]) + "</td><td>" + str(member["position"]) +
            "</td><td><a href=\"/stories/" + _e(member["story_id"]) + "\">" +
            _e(member["question"]) + "</a></td><td>" +
            _e(STORY_LABELS.get(member["state"], member["state"])) + "</td><td>" + action + "</td></tr>"
        )
    membership_section = (
        "<section><h2>Matérias e ordem da edição</h2><p>Exclusões exigem responsável, motivo e confirmação humana; a pauta segue no histórico.</p>"
        "<table><thead><tr><th>Edição</th><th>Ordem</th><th>Pauta</th><th>Estado</th><th>Ação interna</th></tr></thead><tbody>"
        + ("".join(membership_rows) or "<tr><td colspan=5>Nenhuma pauta atribuída a edição.</td></tr>")
        + "</tbody></table></section>"
    )
    attempts = "".join(
        "<tr><td>" + _e(row["stage"]) + "</td><td>" + _e(row["attempt_number"]) +
        "</td><td>" + _e(row["status"]) + "</td><td>" + _e(row["error_summary"] or "—") + "</td></tr>"
        for row in data["attempts"]
    ) or "<tr><td colspan=4>Nenhuma etapa executada.</td></tr>"
    events = "".join(
        "<tr><td>" + _e(row["occurred_at"]) + "</td><td>" + _e(row["entity_type"]) +
        " / " + _e(row["entity_id"]) + "</td><td>" + _e(row["action"]) + "</td><td>" +
        _e(row["actor"]) + "</td></tr>"
        for row in data["events"]
    ) or "<tr><td colspan=4>Nenhum evento registrado.</td></tr>"
    run = data["run"]
    run_summary = (
        "<p>Execução: <strong>" + _e(run["id"]) + "</strong> — " +
        _e(run["status"]) + "</p>" if run else "<p>Nenhuma execução iniciada.</p>"
    )
    content = f"""
<main>
  <section>
    <h2>Simulação offline</h2>
    <p>Os dados são fictícios. A execução não consulta a internet e não publica conteúdo.</p>
    {run_summary}
    <form method="post" action="/demo/run"><input type="hidden" name="csrf" value="{_e(csrf_token)}"><button type="submit">Executar ou retomar simulação</button></form>
  </section>
  {membership_section}
  <section><h2>Itens por estado</h2><table><tbody>{state_counts}</tbody></table></section>
  <section><h2>Pautas</h2><table><thead><tr><th>ID</th><th>Pergunta editorial</th><th>Estado editorial</th><th>Estado de execução</th><th>Execução individual</th></tr></thead><tbody>{stories}</tbody></table></section>
  <section><h2>Edições internas</h2><table><thead><tr><th>Edição</th><th>Estado</th><th>Prévia</th><th>Ação humana</th></tr></thead><tbody>{editions}</tbody></table></section>
  <section><h2>Tentativas recentes</h2><table><thead><tr><th>Etapa</th><th>Tentativa</th><th>Resultado</th><th>Detalhe</th></tr></thead><tbody>{attempts}</tbody></table></section>
  <section><h2>Histórico recente</h2><table><thead><tr><th>Horário UTC</th><th>Registro</th><th>Ação</th><th>Responsável</th></tr></thead><tbody>{events}</tbody></table></section>
</main>
"""
    return render_panel_page("Painel local", content, message=message)


def story_html(detail: dict[str, Any]) -> str:
    story = detail["story"]
    sources = "".join(
        "<li><strong>" + _e(row["source_label"]) + "</strong> — " + _e(row["title"]) +
        " <span class=\"muted\">" + _e(row["source_reference"]) + "</span></li>"
        for row in detail["sources"]
    )
    revisions: list[str] = []
    for row in detail["revisions"]:
        review = "Sem resultado de revisão" if row["review_approved"] is None else (
            "Aprovada" if row["review_approved"] else "Devolvida para correção"
        )
        findings = ""
        if row["findings_json"]:
            decoded = json.loads(row["findings_json"])
            findings = "".join(
                "<div class=\"problem\"><strong>" + _e(item.get("problem")) +
                "</strong><p>" + _e(item.get("detail")) + "</p></div>"
                for item in decoded
            )
        revisions.append(
            "<article><h3>Versão " + _e(row["version"]) + " — " + _e(review) +
            "</h3><pre>" + _e(row["content"]) + "</pre>" + findings + "</article>"
        )
    media = "".join(
        "<li>" + _e(row["title"]) + " — permissão: " + _e(row["permission_status"]) +
        "; decisão: " + _e(row["decision"]) + ". " + _e(row["reason"]) + "</li>"
        for row in detail["media"]
    ) or "<li>Ainda sem decisões de mídia.</li>"
    events = "".join(
        "<li>" + _e(row["occurred_at"]) + " — " + _e(row["action"]) +
        " por " + _e(row["actor"]) + "</li>"
        for row in detail["events"]
    ) or "<li>Nenhum evento.</li>"
    content = f"""
<main>
  <p><a href="/">Voltar ao painel</a></p>
  <section><h2>{_e(story['question'])}</h2><p>Estado: <span class="status">{_e(STORY_LABELS.get(story['state'], story['state']))}</span></p><p>ID: {_e(story['id'])}</p></section>
  <section><h2>Fontes e itens associados</h2><ul>{sources}</ul></section>
  <section><h2>Versões e revisão</h2>{''.join(revisions)}</section>
  <section><h2>Direitos de mídia</h2><ul>{media}</ul></section>
  <section><h2>Eventos da pauta</h2><ol>{events}</ol></section>
</main>
"""
    return render_panel_page("Detalhe da pauta", content)
