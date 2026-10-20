# Revista Gamer · Bloco 03 — v0.3 consolidada

**Estado: LABORATÓRIO EXPERIMENTAL. Não é identidade nem leitor final aprovado.**

## Como o fundador reproduz

1. Baixe/clone o repositório e abra `index.html` no navegador (HTML autocontido, sem rede).
2. No topo, alterne **Folhear** e **Contínua**. No celular, abra **Preferências de leitura** para definir fonte, espaçamento e teste de matéria extensa.
3. Redimensione a tela em 390→1024→390 e 1024→390→1024 e confira que as preferências nunca ficam inacessíveis; a escolha de abrir/fechar feita no celular é preservada.
4. Em **1024×768**, habilite **Matéria extensa**, **150% de fonte**, **espaçamento Muito amplo**; percorra da capa à contracapa. O texto deve continuar sem ficar oculto; a contracapa é externa isolada.
5. Ative **Simular anúncio** para ver a face reservada; desative para confirmar que não se reserva espaço comercial ocioso.
6. Veja o sumário, ajuste configurações, alterne modos e observe o texto de ensaio sem perda. O modelo não publica matérias, imagens ou anúncios reais.

## Teste automatizado verificável

- Requisitos: Python, `pip install playwright` e `python -m playwright install chromium`.
- Execute `python tests/test_integridade.py` nesta pasta.
- Se já possui Chromium instalado: `CHROMIUM_EXECUTABLE=/usr/bin/chromium python tests/test_integridade.py`.
- O teste lê o HTML local, sem utilizar rede nem autenticação, e registra `resultado-testes.json`.
- O teste visita todas as faces em cenários selecionados. Registra **quantidade lógica de faces**, **quantidade de identidades únicas**, **quantidade de visitas**, sequência de chaves das faces exibidas, início e contracapa, integridade do texto, possíveis erros e overflow.

## O que foi tratado após o parecer de 20/10/2026

- **B03-R1**: preferências reativas a breakpoints, com política explícita para escolha feita no celular. Desktop mantém o painel visível e acessível.
- **B03-R2**: contador de faces com identidades `data-key` verificadas, distinguindo total gerado, visitas e faces únicas.
- **B03-R3**: matriz de cenários (tamanhos de tela, fontes, espaçamentos, matéria curta/extensa), leitura nos dois modos e navegação por teclado para **figura com legenda** e **tabela superdimensionadas**.
- **B03-R4**: foco do diálogo e restauração ao fechar; inspeção de largura horizontal e prévias automáticas. **Não substitui teste em aparelhos reais, leitores de tela nem benchmark num notebook de 4 GB**.
- **B03-R5**: face comercial opcional, ausente por padrão. Textos e mídias continuam demonstrações, não conteúdo editorial aprovado. Integração com Motor Editorial ainda não autorizada.

## Evidências desta rodada

- Total de cenários automatizados concluídos: **10**.
- Em **1024×768**, matéria extensa, fonte 150% e espaçamento 1.3: **56 faces lógicas, 56 únicas, 56 visitas**.
- Em **390×844**, matéria extensa, fonte 150% e espaçamento 1.3: **68 faces lógicas, 68 únicas, 68 visitas**.
- Os cenários verificados não indicaram texto escondido, largura global excedente nem diferenças no texto integral entre Folhear/Contínua.
- Detalhes completos: [`resultado-testes.json`](resultado-testes.json). Script: [`tests/test_integridade.py`](tests/test_integridade.py).

## Restrições e responsabilidade

É uma **casca vazia** do Bloco 03; Blocos 02/04/05/06 conservam responsabilidade exclusiva por personagens, matérias, mídias/direitos e comercial. O conteúdo atual é teste neutro. A v0.3 revisada anterior permanece no repositório para comparação. Não acionar Codex, publicar edição nem congelar nome/identidade visual por inferência.

### Pendências honestas antes do leitor real

Validação com um dispositivo Android real, tablet e notebook modesto; leitura de voz/leitor de tela; desempenho e mais formatos de matéria reais; estabilidade de âncoras ao reflow; licença/obtenção de imagens e avaliação final da direção.