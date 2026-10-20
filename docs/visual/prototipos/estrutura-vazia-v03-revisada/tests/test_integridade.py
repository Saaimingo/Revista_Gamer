"""Teste reproduzível da casca vazia v0.3 revisada (não homologação).
Requisitos: pip install playwright && python -m playwright install chromium
Uso: python tests/test_integridade.py
"""
from pathlib import Path
import re
import json
from playwright.sync_api import sync_playwright

HTML = (Path(__file__).resolve().parent.parent / "index.html").read_text(encoding="utf-8")
VIEWPORTS = [(1024, 768), (390, 844)]

def normalize(value):
    return re.sub(r"\s+", " ", value).strip()

def run():
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        for width, height in VIEWPORTS:
            page = browser.new_page(
                viewport={"width": width, "height": height},
                reduced_motion="reduce"
            )
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            # Evita depender de file:// ou servidor local.
            page.set_content(HTML, wait_until="load")
            page.locator("#longText").evaluate(
                "el => {el.checked=true;el.dispatchEvent(new Event('change',{bubbles:true}));}"
            )
            page.locator("#fontRange").evaluate(
                "el => {el.value='150';el.dispatchEvent(new Event('input',{bubbles:true}));"
                "el.dispatchEvent(new Event('change',{bubbles:true}));}"
            )
            page.wait_for_timeout(350)

            pieces = []
            violations = []
            visible_faces = 0
            last = []

            for _ in range(180):
                info = page.evaluate("""() => ({
                    keys:[...document.querySelectorAll('#flipStage .page')].map(x=>x.dataset.key),
                    bodies:[...document.querySelectorAll('#flipStage .story-body')].map(x=>({
                        scroll:x.scrollHeight, client:x.clientHeight,
                        overflow:getComputedStyle(x).overflowY
                    })),
                    text:[...document.querySelectorAll('#flipStage .page--story .flow-text')].map(x=>x.innerText),
                    horizontal:Math.max(document.documentElement.scrollWidth,document.body.scrollWidth)-innerWidth
                })""")
                last = info["keys"]
                visible_faces += len(last)
                pieces.extend(info["text"])
                if info["horizontal"] > 2:
                    violations.append("Rolagem horizontal: " + str(info["horizontal"]))
                for body in info["bodies"]:
                    if body["scroll"] > body["client"] + 1 and body["overflow"] == "hidden":
                        violations.append("Texto escondido: " + str(body))
                if page.locator("#nextBtn").is_disabled():
                    break
                page.locator("#nextBtn").click()
            else:
                violations.append("Navegação não chegou ao fim")

            # Contracapa isolada em todos os tamanhos.
            if last != ["backcover"]:
                violations.append("Contracapa não isolada: " + str(last))

            page.locator("#modeScroll").click()
            page.wait_for_timeout(100)
            continuous = page.locator("#scrollRoot .story-continuous .flow-text").all_text_contents()
            same_text = normalize(" ".join(pieces)) == normalize(" ".join(continuous))
            if not same_text:
                violations.append("Texto da reportagem difere entre Folhear e Contínua")
            if errors:
                violations.append("Erro JS: " + "; ".join(errors))

            outcome = {
                "viewport": f"{width}x{height}",
                "faces_exibidas_no_percurso": visible_faces,
                "contracapa_isolada": last == ["backcover"],
                "texto_identico_nos_dois_modos": same_text,
                "violacoes": violations
            }
            results.append(outcome)
            print(json.dumps(outcome, ensure_ascii=False))
            page.close()
        browser.close()
    if any(item["violacoes"] for item in results):
        raise SystemExit("FALHA: veja as violações acima")
    print("OK: cenários determinísticos concluídos.")

if __name__ == "__main__":
    run()
