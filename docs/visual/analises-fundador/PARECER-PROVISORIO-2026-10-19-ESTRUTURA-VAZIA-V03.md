# Parecer provisório do fundador — Bloco 03 / Estrutura Vazia v0.3

**Data:** 19/10/2026  
**Setor:** Bloco 03 — Identidade Visual e Experiência de Leitura  
**Estado:** **PARECER PROVISÓRIO / EM AVALIAÇÃO PELA DIREÇÃO**; não aprova identidade final, implementação pelo Codex nem publicação.  
**Origem:** arquivo `index(6).html`, `LEIA-ME(1).md` e nove capturas de desktop/tablet/mobile entregues ao Chat Fundador; referência histórica: [parecer v0.2](PARECER-PROVISORIO-2026-10-17-ESTRUTURA-VAZIA-V02.md). Os binários da v0.3 foram analisados como anexos nesta conversa e **não** foram versionados no GitHub por este parecer.

## 1. Síntese integrada

**Avaliação favorável à direção do protótipo, com dois bloqueios funcionais encontrados e melhorias ergonômicas sugeridas.** A v0.3 responde à demanda da direção por **dois modos escolhidos pelo leitor** — Folhear e Contínua —, preservação da preferência, adaptação ao espaço, fontes ajustáveis e separação entre **casca visual** e conteúdo de outros setores. Não refazer a v0.3 do zero nem congelá-la como produto pronto.

Evolução conceitual: v0.1 formalizou os espaços, mas encolhia texto mobile; v0.2 corrigiu legibilidade e iniciou paginação de conteúdo demonstrativo; **v0.3 distingue explicitamente a navegação em livro da leitura contínua**, oferece fonte de 90–150%, espaçamento, tema, matéria extensa, sumário e preferências locais no código. Os dois modos devem continuar existindo; a adaptação ao dispositivo não deve anular a escolha do leitor.

## 2. Base de evidências e limites

**Observação — material:** as nove capturas mostram capa em desktop/tablet/mobile, faces opostas, fluxo contínuo e controles. O arquivo HTML é autocontido e a seção de ajuda declara conteúdo demonstrativo, não matéria real; não contém mídias oficiais ou conteúdo editorial final.

**Observação — teste complementar do fundador:** inspecionei HTML/CSS/JS e executei o protótipo em **Chromium headless via Playwright**, com o conteúdo HTML injetado em uma página de teste (o ambiente bloqueou abertura direta por `file://`). Viewports exercitadas: **1440×960, 1024×768, 800×1100, 390×844, 360×740 e 320×700**, em modo Folhear, com cenário padrão e cenário **Matéria extensa + fonte 150%**. Naveguei por faces e medi dimensões/overflow. Não observei exceções JavaScript nos cenários percorridos; não houve largura horizontal global maior que a viewport. **Isto não substitui testes em aparelhos físicos, gestos reais, leitor de tela, desempenho ou auditoria completa**.

**Observação — cenário padrão:** foram medidas 20 faces em 1440px, 21 em 1024px, 24 em 390px e 25 em 320px, coerentemente com a paginação dinâmica declarada pela entrega. O modo Contínua foi analisado pelo HTML e capturas; a prova de overflow automatizada acima focou Folhear. Não declarar validação funcional exaustiva do Contínua por estes testes.

## 3. Acertos a preservar

1. **Escolha do leitor (direção já expressa):** dois modos claros, em vez de obrigar todos a folhear ou a rolar; o HTML guarda preferências em `localStorage` quando disponível. Alternância reconstitui conteúdo por âncora aproximada, mas não comprova preservação exata do parágrafo em todos os casos.
2. **Revista em dupla no desktop, texto fluido no mobile:** a apresentação de 04–05 como páginas opostas transmite livro/revista, enquanto uma face mobile evita a miniatura ilegível. Fonte e espaçamento variáveis não são apenas zoom de imagem; texto permanece HTML.
3. **Blocos editoriais separados:** figura e legenda no mesmo elemento `figure`, texto, citação e tabela em blocos; capa, expediente, sumário, hardware, inspeção, comunidade, publicidade e contracapa estão representados como casca, sem apropriação de conteúdo do Bloco 02/04/05/06.
4. **Modo Contínua promissor:** leitura longa mais confortável sem quebrar reportagem a cada face; deve manter ritmo editorial e assinatura visual reconhecível para não se tornar um site genérico.
5. **Transparência de estágio:** `/ LAB`, slots nomeados, textos neutros e marcação explícita de não aprovação; nenhum anúncio, personagem, nome comercial ou reportagem foi aprovado apenas por constar no protótipo.

## 4. Problemas funcionais efetivamente reproduzidos — prioridade máxima na próxima revisão

### F1 — Conteúdo parcialmente oculto no modo Folhear com 150% de fonte

**Observação reproduzida:** em **1024×768**, com **Matéria extensa** e **Fonte 150%**, **14 das 22 faces de continuação verificadas** apresentaram `.story-body` com `scrollHeight > clientHeight` entre **13 e 101 pixels**, enquanto `overflow: hidden` está aplicado no desktop. Isso significa que trechos podem ficar **invisíveis e inacessíveis** embora o contador de páginas e a largura global aparentem normalidade. O caso não apareceu no mesmo conjunto de verificações em 1440px ou nos viewports mobile testados; não extrapolar que os demais tamanhos estão livres de falhas.

**Causa provável identificada no código (inferência):** `fitStoryBlocks()` mede um quadro estimado e trata um `flow-block` como unidade indivisível; se um bloco de texto isolado for maior que a região, ele é colocado mesmo assim. No Folhear largo a página e a story-body ocultam excedentes; os parâmetros de medição nem sempre refletem a superfície efetiva.

**Pedido de avaliação ao Bloco 03:** definir comportamento seguro para texto que não cabe — segmentar **parágrafos longos** em unidades semânticas quando permitido, expandir/continuar a reportagem, ou oferecer modo contínuo explicitamente, **nunca ocultar conteúdo**. Manter figura+legenda, citações e tabelas como blocos indivisíveis salvo regras claras. Criar teste determinístico de 1024×768, 150%, longo, que falhe se algum bloco estiver cortado.

### F2 — Contracapa não isolada quando total de faces é ímpar

**Observação reproduzida:** em **1024×768**, o cenário padrão gerou **21 faces**. Ao chegar ao fim, o Folhear exibiu **20–21 juntas**, com `credits` à esquerda e `backcover` à direita. Em **1440×960**, com 20 faces, a contracapa apareceu isolada.

**Causa provável no código (inferência):** `spreadStart()`/`renderFlip()` permitem emparelhar a última face quando a contagem é ímpar. A extensão dinâmica muda a paridade.

**Pedido de avaliação ao Bloco 03:** tornar explícita a política de paridade de folhas/versos e **garantir capa e contracapa isoladas**, com face neutra de preenchimento se necessário ou lógica de exibição independente. Revalidar numeração e sumário quando o texto amplia a quantidade de faces.

## 5. Ergonomia e direção de arte — sugestões, não defeitos absolutos

**E1 — Controles tomam área nobre no celular.** No cenário **390×844** a capa começou a cerca de **316px abaixo do topo**; em **320×700**, a cerca de **346px**. Medidas incluem topo da aplicação, preferências e indicação do laboratório. Para produto final, propor preferências recolhíveis, um comando de leitura prioritário e navegação acessível sem ocupar um terço/metade da primeira tela. O laboratório pode manter controles expansíveis.

**E2 — Barra flutuante no modo Contínua.** Nas capturas, `Início / Sumário / Folhear` permanece na borda inferior sobre a zona de leitura, competindo com o texto. Testar redução, auto-ocultação ou área inferior reservada e reabertura clara; preservar acessibilidade por teclado e toque.

**E3 — Capa desktop central pequena e muito espaço escuro.** Julgamento estético, **não** falha técnica: o respiro pode ser intencional para simular revista física, mas a capa tem menos presença do que os pares internos. Experimentar ajustes opcionais de escala/encaixe mantendo proporção, sem forçar arte a preencher tela ou sacrificar legibilidade.

**E4 — Identidade em ambos os modos.** O Contínua funciona visualmente como artigo longo; conservar seção, separadores, assinatura do cronista, hierarquia, marca e imagens com legendas para não virar apenas uma página genérica. Não impor cabeçalho decorativo grande a todo parágrafo.

**E5 — Leitura de voz e foco.** O HTML contém semântica, `aria-live`, preferência `prefers-reduced-motion` e controles por teclado, mas **não houve auditoria real de tecnologias assistivas**. Em CSS mobile (`max-width:560px`), o elemento `.settings .status` que possui `aria-live` passa a `display:none`, portanto convém oferecer canal de feedback acessível independentemente de exibição visual. Testar abertura/fechamento do sumário com teclado, foco, retorno ao ponto de leitura e leitores de tela em dispositivos reais.

**E6 — Contato com o Motor Editorial.** Antes de especificar uma paginação final, testar **fixtures locais**, sem inferências SIWC, que reproduzam comprimento e componentes de uma reportagem curta, grande e de capa. Como insumo opcional, a amostra técnica de 578 palavras RTX 5090 pode ser usada **apenas como conteúdo de ensaio e identificada como não aprovada**, não como texto publicável. Não acionar Codex por inferência, não consumir Plus sem nova autorização e não exigir do Bloco 03 que escreva reportagem.

## 6. Encaixe intersetorial

- **Bloco 02:** o nome e o retrato-base do Ranzinza/Protótipo A estão aprovados, mas DNA/voz editoriais completos ainda estão em desenvolvimento. Os slots de avatar não autorizam inventar outra fisionomia.
- **Bloco 04 e Motor Editorial:** fornecerão textos/evidências aprovados em momento apropriado; o Bloco 03 define componentes que refluem, não cria a matéria. Amostras técnicas não são conteúdo final.
- **Bloco 05:** resolver direitos de mídia antes da publicação pública de imagens de jogos e mockups; os 16 PNGs dos mocks A/B seguem pendentes de tratamento na [Issue #7](https://github.com/Saaimingo/Revista_Gamer/issues/7).
- **Bloco 06:** publicidade e afiliação devem ser opcionais, claramente identificadas; sem anunciante não manter um grande vazio obrigatório. Nenhum nome de revista nem patrocínio está definido.

## 7. Proposta de priorização para a próxima conversa com o Bloco 03

**Prioridade 0 — Correção demonstrável:** F1 (nenhum texto oculto em 1024×768/150%/longa) e F2 (capa e contracapa respeitam isolamento sob contagem par/ímpar). Mostrar novamente cenários e resultados.

**Prioridade 1 — Legibilidade e conforto:** E1/E2 no mobile, preservar acesso a sumário e configurações; testar mínimo 320px, 360px e 390px.

**Prioridade 2 — Identidade e editorial:** E3/E4 e teste com fixtures de matérias variadas e bloco imagem+legenda/tabela/citação; revisar persistência de âncora ao redimensionar e alternar modos.

**Observação:** não propor nova versão 0.4 como requisito automático, não determinar implantação pelo Codex, não congelar logo, paleta, proporção de texto ou interface sem nova rodada com a direção. O bloco deve **discutir** o parecer antes de executar qualquer tarefa.

## 8. Conclusão

A v0.3 **amadureceu a proposta da revista**: coexistência de livro/folhear e leitura contínua, composição responsiva em blocos e delimitação de competências editoriais. Meu parecer é **seguir refinando sobre esta base, não recomeçar**. Os dois problemas F1/F2 são requisitos de integridade para qualquer futuro leitor; E1–E6 são hipóteses de UX/identidade a resolver com a direção e provas. **Nenhum item equivale à aprovação final ou autorização de publicação.**
