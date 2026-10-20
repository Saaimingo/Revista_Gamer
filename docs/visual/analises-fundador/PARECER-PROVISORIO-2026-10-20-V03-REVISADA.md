# Parecer provisório do Chat Fundador — Bloco 03 / v0.3 revisada

**Data:** 20/10/2026  
**Objeto:** `docs/visual/prototipos/estrutura-vazia-v03-revisada/` (HTML navegável, README, LEIA-ME, resultado-testes.json e teste Playwright), commits de 20/10/2026 na `main`.  
**Estado:** **REVISÃO TÉCNICA E CONCEITUAL PROVISÓRIA — NÃO É ACEITE FINAL.** A direção discutirá o parecer com o Bloco 03 antes de qualquer tarefa nova. Não autoriza Codex, publicação ou congelamento visual.

## 1. Reconhecimento da entrega

Diferentemente do pacote anterior, o Bloco 03 **versionou no GitHub o HTML de fato executável** (autocontido), roteiro de abertura, resultados estruturados e teste Python/Playwright. A documentação registra honestamente que os PNGs e o ZIP originais **não** foram transferidos e que a identidade editorial é experimental. Isso atende a uma pendência de verificabilidade que havia no parecer inicial da v0.3.

**Acertos de implementação observados na leitura do código:**

- **F1:** `fitStoryBlocks()` monta uma face real de medição, testa altura com margem, divide texto extenso por palavras sem eliminar conteúdo e reserva `needs-scroll` para bloco indivisível grande. O teste automatizado compara texto normalizado dos dois modos e observa overflow invisível. Isto é evolução real sobre a v0.3 anterior, na qual havia texto oculto.
- **F2:** `buildPages()` insere `neutral-verso` quando necessário para que a última face seja externa e a contracapa permaneça isolada. A navegação no desktop diferencia primeira, faces opostas e última face.
- **Ergonomia:** painel de preferências recolhível no celular, canal adicional `globalLive` para avisos acessíveis e barra inferior flutuante desativada em `redraw()`; a leitura Contínua mantém conteúdo HTML com fonte ajustável, não um raster de páginas.
- **Teste reproduzível:** `tests/test_integridade.py` percorre Folhear até a última face em 1024×768 e 390×844, com Matéria extensa/150%, verifica contracapa, overflow oculto, texto normalizado e erros JS; seu uso exige Python, Playwright e Chromium instalados.

**Limite fundamental da auditoria do fundador nesta rodada:** li diretamente os arquivos na `main` e analisei sua lógica; **não consegui baixar o HTML para meu ambiente de execução nem rodei o teste Playwright independentemente**. Os resultados de `resultado-testes.json` são evidências **reportadas pelo Bloco 03**, não certificação independente. Não afirmar que F1/F2 foram homologados por mim.

## 2. Pendências a devolver ao Bloco 03

### B03-R1 — Comportamento das preferências ao cruzar breakpoint (corrigir antes de aceite funcional)

**Falha inferida diretamente do código:** na inicialização o script executa `if(innerWidth<=560) $('settingsShell').open=false`. Em desktop a CSS oculta o `summary` (`.settings-shell>summary{display:none}`), e a rotina `resize` apenas executa `redraw()`, **sem sincronizar o estado do `details` com a mudança de breakpoint**. Logo, abrir em 390px e depois ampliar para 1024px pode manter as preferências fechadas com o controle de reabertura escondido. No sentido inverso, iniciar no desktop e depois reduzir para 390px pode manter o painel expandido, ocupando a área nobre que se pretendia economizar.

**Pedido:** definir política responsiva que preserve a escolha explícita quando cabível, mas garanta que configurações permaneçam acessíveis nos dois lados do breakpoint. Acrescentar teste de **390→1024→390** e **1024→390→1024**, contemplando painel que o leitor abriu/fechou manualmente. Não presumir que a simples mudança de largura resolve a usabilidade.

### B03-R2 — Esclarecer relatório de quantidade de faces e rastreabilidade

No arquivo `resultado-testes.json`, os cenários 1024×768 e 390×844 com Matéria extensa + 150% informam **56 faces geradas**; o reteste registra **57 faces visíveis visitadas**. Como o script soma os elementos `.page` apresentados a cada avanço, **esse contador pode medir visitas, não faces únicas**. Precisamos distinguir explicitamente `faces_unicas`, `visitas_a_faces`, `contagem_final_de_faces` e qualquer repetição. **Não é prova automática de página perdida**, mas o relatório atual não explica essa diferença. Solicito log de sequência `data-key`/`data-page` com as identidades efetivamente exibidas, e confirmar início, término e contracapa na mesma execução. Preservar resultados originais sem reescrever números para fazê-los parecer consistentes.

### B03-R3 — Cobertura além do cenário principal

O teste versionado cobre **dois viewports** e **uma combinação** (Matéria extensa + 150%). O JSON relata seis tamanhos no pacote original, mas alguns ensaios examinaram menos faces que o total. Complementar, prioritariamente **sem gasto SIWC**, combinações de fonte mínima/intermediária/máxima, espaçamento normal/muito amplo, diferentes larguras e troca entre Folhear e Contínua. Incluir teste em que uma figura+legenda/tabela fica maior que a área disponível: verificar que `needs-scroll` realmente é percorrível por teclado/toque e que nenhum conteúdo se perde. Um bloco com `overflow:auto` não prova sozinho que pessoas conseguem acessá-lo.

### B03-R4 — Ergonomia e acessibilidade em aparelho real

Painel mobile foi compactado, mas **não há medição atual independente da distância entre topo e primeira face**, nem prova em telefone real, tablet ou notebook de 4 GB de RAM. Falta validar foco/teclado ao abrir o sumário `role=dialog` (foco inicial existe, mas não há contenção explícita do foco dentro do diálogo), leitura de voz/leitor de tela, legibilidade e desempenho de paginação ao alterar tipografia. Preservar preferências do leitor sem sacrificar acesso a comandos ou ao texto.

### B03-R5 — Componentes editoriais reais e espaços comerciais

Os textos são *lorem* demonstrativo, as imagens são slots, e o quadro de publicidade é intencionalmente ilustrativo; **não concluem adaptação a uma matéria real**. Para próximo ensaio autorizado, usar fixtures locais da Redação/Motor Editorial, com título longo, subtítulo, citação, tabela e imagem+legenda, sem nova inferência SIWC. O espaço para publicidade deve ser **opcional de verdade**: antes de produto final, discutir como não desperdiçar uma face se não houver anunciante. Manter patrocínio separado de conteúdo jornalístico.

A nova proposta de correspondência do Ranzinza (Bloco 02) poderá futuramente exigir uma área editorial para debates, réplicas e autorização do leitor, **mas não é ordem para o Bloco 03 criar essa interface agora**. O Bloco 04 e a direção precisam definir regras de publicação e privacidade antes de qualquer componente operacional.

## 3. Priorização proposta

**P0:** R1 (preferências desktop↔mobile) e prova esclarecedora de R2 (contagem/visitas).  
**P1:** R3 (testes de texto/figuras maiores e diferentes ajustes); preservação de conteúdo e navegação.  
**P2:** R4 (testes reais de ergonomia, teclado/leitor de tela e performance) e R5 (fixtures de conteúdo e propaganda condicional).

## 4. Parecer

**Favorável à continuidade da base v0.3 revisada, mas NÃO ao congelamento da solução.** F1/F2 contam com correções plausíveis e evidências internas positivas; permanecem pendentes validação independente e ajustes de responsividade. Não exigir recomeço, nem converter automaticamente problemas de UX em decisão de identidade visual. **Próximo passo:** Bloco 03 discute este parecer com a direção, propõe solução enxuta e apresenta nova evidência. Sem implementação do Codex, PR extra, merge ou publicação por inferência.


---

## Aditivo do fundador — versão v0.3 **consolidada** (20/10/2026, revisão posterior)

**Base examinada:** [estrutura-vazia-v03-consolidada/](../prototipos/estrutura-vazia-v03-consolidada/README.md) — HTML real, `tests/test_integridade.py` e `resultado-testes.json`, commit de publicação `f4bc80a60` e indexação na `main`. **Estado: respostas ao parecer anterior CONFERIDAS EM CÓDIGO E EM EVIDÊNCIA REPORTADA, sem homologação final.** Este aditivo não apaga as falhas historicamente encontradas na versão anterior nem aprova a identidade final.

**B03-R1 — tratado no código:** rotina `syncSettingsShell()` e escuta de `matchMedia('(max-width:560px)')` impedem que o painel permaneça fechado e inacessível no desktop. A opção mobile é preservada. O teste versionado cobre 390→1024→390 e 1024→390→1024, inclusive escolha manual de abrir/fechar, modo e fonte.

**B03-R2 — tratado em registro e teste:** `window.__rgLabAudit()` expõe chaves de faces e números; `validate_full_flip()` exige identidade única, visita exatamente uma vez a cada face e contracapa isolada. O JSON traz sequência `visited_sequence`. O cenário 1024×768/150%/espaçamento 1.3/matéria extensa reporta **56 lógicas = 56 únicas = 56 visitas**; 390×844 nas mesmas condições reporta **68 = 68 = 68**. Isto resolve a ambiguidade do relatório anterior, no escopo dos ensaios apresentados.

**B03-R3 — ampliado:** script contém seis combinações de viewport/fonte/espaçamento/comprimento, além de breakpoint, sumário, publicidade condicional e rolagem por teclado de figuras/tabelas superdimensionadas: **dez cenários registrados como PASS** no JSON. A integridade textual entre Folhear e Contínua, ausência de overflow horizontal e sem erros JS são checagens codificadas. F1 (texto invisível) e F2 (contracapa isolada) estão **tecnicamente endereçados e com evidência interna positiva**, não independemente reproduzidos pelo Chat Fundador nesta rodada.

**B03-R4 — parcialmente atendido no código:** foco inicial, contenção básica de Tab no sumário, Escape e retorno ao foco anterior foram adicionados. Ainda faltam **teste de acessibilidade com leitores de tela, gestos e navegação em aparelhos físicos**, desempenho em notebook modesto e demonstração ergonômica fora de Chromium headless.

**B03-R5 — parcialmente atendido:** face publicitária opcional por `adPreview` está ausente por padrão e não deixa lacuna quando desativada; o ensaio ainda usa texto, mídia e tabelas de demonstração. **Integração com matéria aprovada de verdade e direitos de imagens continuam pendentes.**

**Limite de verificação do fundador:** inspecionei diretamente arquivos e lógica via GitHub, mas **não executei o Playwright em minha máquina nesta rodada**, pois o acesso direto ao HTML bruto para o ambiente de teste não foi possível; os números vêm do `resultado-testes.json` do Bloco 03. Dizer “correções implementadas e testes reportados PASS” é correto; dizer “homologado independente / pronto para produção” não é.

### Decisão recomendada para o próximo passo

**Não recomeçar e não solicitar v0.4 por inércia.** O Bloco 03 respondeu satisfatoriamente às pendências mais objetivas; registrar **aceite provisório da evolução do laboratório** e passar a uma fase de integração editorial **somente quando a direção autorizar**: fixtures locais curtas/longas de texto e tabelas, uma imagem+legenda autorizada e medições em celular/tablet/notebook reais. No mobile o caso extremo chegou a 68 faces em Folhear — aceitável como teste de estresse, **não** parâmetro de tamanho da edição; validar conforto de navegação e o modo Contínua com matéria real.

**Intersetorial:** futura coluna do Ranzinza com cartas e réplica pode ocupar um slot de conteúdo já previsto, mas a regra de consentimento e edição deve vir do Bloco 04, com aval da direção, **sem** gerar formulário, automação ou canal privado aqui.

**Resultado deste aditivo: FAVORÁVEL a seguir para ensaios editoriais reais controlados; pendente aceite de produto em dispositivos e deliberação explícita da direção. Sem código alterado nem Codex acionado.**
