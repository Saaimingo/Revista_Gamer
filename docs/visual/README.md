# Setor: visual e experiência de leitura

Status: conceito aprovado em linhas gerais; designs e requisitos mensuráveis pendentes.

## Pilares

Identidade central reconhecível com direção temática por edição (horror pode ser escuro, hardware mais tecnológico, nostalgia colorida); páginas com riqueza visual de revista tradicional e interatividade opcional.

## Formato-piloto

Hipótese: **10 folhas virtuais, 20 faces/páginas** no total, incluindo capa e contracapa. Folhear respeita frente e verso; desktop pode exibir duas faces em páginas opostas, mobile uma face. Oferecer modo direto sem animação, navegação por sumário, zoom e texto acessível (não rasterizar todos os textos em imagens).

Extras opcionais: abertura cinematográfica antes da capa, áudio acionado pelo leitor, imagem interativa, wallpaper/encarte original ou autorizado, PDF colecionável se viável. Não transformar publicação em catálogo de vídeos. Áudio nunca deve tocar sem ação do usuário; permitir pular/anular animação.

## Restrições de experiência

Funcionamento em notebook modesto com ~4 GB de RAM, tablets e smartphones; carregar mídia pesada só sob demanda, formatos otimizados, respeito à preferência de movimento reduzido, navegação por teclado e compatibilidade com leitura por voz.

## Entregas a Engenharia

Tokens de identidade, componentes e estados, protótipos com tamanhos responsivos, representação da dobra/verso, especificações de animação, performance medida, acessibilidade testada, contrato de posicionamento editorial e espaços reservados para anúncios **sem acesso a mídias editoriais**.


## Estudos de identidade e protótipos — 17/10/2026

O diretor autorizou documentar dois estudos gráficos comparáveis, **sem aprová-los como identidade definitiva**. Ambos possuem oito faces de mock (capa + seis faces internas + contracapa) e testam capa cinematográfica com miolo editorial que privilegia a redação dos cronistas. A referência de aproximadamente 70% de prioridade à escrita nas matérias internas é uma **hipótese em avaliação**, não regra fixa para cada editoria.

- [Visão comparativa e pontos a decidir](estudos/ESTUDO-COMPARATIVO-DOIS-MOCKS-TEMATICOS-2026-10-17.md).
- [Catálogo dos dois protótipos e situação dos PNGs](prototipos/README.md).
- [Mock A — terror, capa escura e exemplo de anúncio](prototipos/mock-a-terror/README.md).
- [Mock B — GTA VI, capa colorida e retorno ao tema-base nas demais editorias](prototipos/mock-b-gta/README.md).
- [Parecer provisório do fundador — revisão dos dois mocks e orientações de retomada](analises-fundador/PARECER-PROVISORIO-2026-10-17-MOCKS-A-B.md) — avaliação independente, NÃO identidade aprovada.

- [Parecer provisório do fundador — Estrutura Vazia v0.1 (ZIP HTML + seis prévias)](analises-fundador/PARECER-PROVISORIO-2026-10-17-ESTRUTURA-VAZIA-V01.md) — inspeção funcional de layouts e questões de legibilidade mobile; não é identidade aprovada nem implementação da revista.
- [Parecer provisório do fundador — Estrutura Vazia v0.2](analises-fundador/PARECER-PROVISORIO-2026-10-17-ESTRUTURA-VAZIA-V02.md) — resposta a P1–P6, verificação de layout responsivo e paginação experimental; continuidade em discussão.


- [Parecer provisório do fundador — Estrutura Vazia v0.3 (19/10/2026)](analises-fundador/PARECER-PROVISORIO-2026-10-19-ESTRUTURA-VAZIA-V03.md) — revisão das capturas e do HTML recebido, com testes complementares do modo Folhear (texto oculto em 1024px/150% e contracapa emparelhada em 21 faces) e sugestões de ergonomia mobile; não é aprovação de identidade nem implementação. A v0.3 permanece como arquivo anexo da conversa, não versionado aqui.

**Estado operacional:** documentação em GitHub; arquivos PNG binários gerados e organizados no pacote de entrega ao diretor, mas **pendentes de transferência efetiva para o repositório**. Não alegar que os arquivos visuais estão presentes até validação por leitura do próprio GitHub. As imagens contêm IP/marcas reconhecíveis e informações fictícias, exigindo análise de direitos e revisão antes de uso público.

## Conciliação visual solicitada pela direção — estudo de capa e miolo (20/10/2026)

O Chat Fundador registrou o **[exemplo integrado dos Mocks A/B e do novo Estudo Visual 01](prototipos/demonstracao-integrada-fundador-2026-10-20/README.md)**, com **[HTML autocontido](prototipos/demonstracao-integrada-fundador-2026-10-20/index.html)** para comparação. A direção rejeitou a substituição implícita por uma capa genérica e pediu retomar **nome grande central no topo, destaque central com arte cinematográfica, chamadas laterais e espaço publicitário somente se houver patrocinador**. Este exemplo não aprova marca final, mídias externas nem substitui o leitor funcional da v0.3. O Bloco 03 deve distinguir se o Estudo Visual 01 anterior era abstração deliberada ou mudança de conceito não autorizada e dialogar sobre o resultado.

## Entrega navegável do Bloco 03 — v0.3 revisada (20/10/2026)

O laboratório revisado de **casca editorial** está disponível **como HTML real e documentos de teste no GitHub**, em:
**[docs/visual/prototipos/estrutura-vazia-v03-revisada/](prototipos/estrutura-vazia-v03-revisada/README.md)**.

- [HTML autocontido para baixar e abrir no navegador](prototipos/estrutura-vazia-v03-revisada/index.html)
- [Roteiro para o fundador](prototipos/estrutura-vazia-v03-revisada/LEIA-ME.md)
- [Resultados de verificação](prototipos/estrutura-vazia-v03-revisada/resultado-testes.json)
- [Teste reproduzível Playwright](prototipos/estrutura-vazia-v03-revisada/tests/test_integridade.py)

**Motivo da revisão:** [parecer provisório do fundador sobre v0.3](analises-fundador/PARECER-PROVISORIO-2026-10-19-ESTRUTURA-VAZIA-V03.md), em especial **F1 (texto escondido com matéria longa/150%)** e **F2 (contracapa emparelhada quando contagem ímpar)**. A revisão também testa compactação dos controles mobile e elimina barra flutuante sobre a leitura contínua.


- [Parecer provisório do fundador sobre o laboratório v0.3 **revisado** — 20/10/2026](analises-fundador/PARECER-PROVISORIO-2026-10-20-V03-REVISADA.md) — reconhecimento das correções e dos testes registrados, com pendências para comportamento de preferências ao trocar mobile↔desktop, explicação do contador de faces, cobertura de testes e uso de conteúdo real. Não constitui homologação independente nem nova ordem ao Codex.

**Estado:** HTML e documentos acima versionados e verificados; ZIP e capturas PNG originais da v0.3 revisada ainda **não** transferidos ao GitHub. Os PNGs anteriores dos mocks A/B continuam com sua pendência própria. **Nada está aprovado como identidade final ou produção.** A próxima ação é análise da direção e do fundador, sem encaminhamento automático ao Codex.

## Laboratório v0.3 consolidado — correções B03-R1 a B03-R5 (20/10/2026)

Após o [parecer provisório sobre a v0.3 revisada](analises-fundador/PARECER-PROVISORIO-2026-10-20-V03-REVISADA.md), o Bloco 03 disponibilizou a **[v0.3 consolidada, executável e testável](prototipos/estrutura-vazia-v03-consolidada/README.md)**.

- [HTML autocontido](prototipos/estrutura-vazia-v03-consolidada/index.html) — Folhear/Contínua, preferências reativas a mudanças de tamanho e publicidade facultativa
- [Resultados com faces geradas, identidades únicas, visitas e sequências](prototipos/estrutura-vazia-v03-consolidada/resultado-testes.json)
- [Teste Playwright com casos responsivos, leitura, diálogo, imagem/legenda e tabela oversized](prototipos/estrutura-vazia-v03-consolidada/tests/test_integridade.py)
- [Guia de revisão e limitações](prototipos/estrutura-vazia-v03-consolidada/README.md)

**Evidência local:** 10 cenários automatizados concluídos em Chromium headless. Cenário 1024×768/150%/espaçamento ampliado/matéria longa: 56 faces geradas, 56 identidades únicas e 56 visitas. Cenário 390×844 nas mesmas condições: 68/68/68. Não é teste em aparelhos físicos ou homologação externa.

**Estado:** fase de integridade/ergonomia do protótipo consolidada para avaliação da direção. **Nenhuma identidade, edição nem implementação definitiva aprovada**. A v0.3 revisada anterior permanece íntegra para comparação; o ZIP e as prévias locais da consolidação não constam como binários no repositório, mas o HTML é reproduzível a partir do GitHub.
