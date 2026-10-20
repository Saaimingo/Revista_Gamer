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
