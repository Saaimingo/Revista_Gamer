# REVISTA BACK — HANDOFF DA DIREÇÃO / BLOCO 02 → BLOCO 03
## Folhear realista, câmera cinematográfica, zoom técnico e páginas duplas (01/11/2026)

**Origem excepcional:** conversa realizada **por engano pelo diretor no Chat Bloco 02 — Personagens e Identidade Narrativa**. O diretor esclareceu expressamente que o assunto pertence ao **Bloco 03 — Identidade Visual e Experiência de Leitura** e pediu para transferir **todo o contexto e a avaliação dos protótipos ao GitHub**, encerrando a discussão técnica no Bloco 02.  
**Destinatário e proprietário das próximas decisões:** Bloco 03. **Este documento foi redigido pelo Bloco 02 como fiel handoff da fala e avaliação do diretor, não como substituição da autoridade, nem como especificação final de engine.**  
**Situação:** REGISTRO DE DIREÇÃO + RESULTADOS DE ENSAIOS EXPERIMENTAIS + REQUISITOS EM DISCUSSÃO. Não foi aprovada implementação definitiva, biblioteca, nova marca, imagens finais, merge, deploy ou publicação.  
**Data:** 01/11/2026. **Repositório:** `Saaimingo/Revista_Gamer`. **Branch de entrega:** `bloco03/diretriz-avaliar-motores-leitura-responsiva-2026-10-26`, [PR #46](https://github.com/Saaimingo/Revista_Gamer/pull/46).  
**Prioridade de leitura do Bloco 03:** este handoff → [diretriz de avaliar engines, híbrido e responsividade (26/10)](DIRETRIZ-DA-DIRECAO-AVALIAR-MOTORES-DE-LEITURA-RESPONSIVA-2026-10-26.md) → [README do setor](../README.md) → [v0.3 consolidada](../prototipos/estrutura-vazia-v03-consolidada/README.md).

---

## 1. Mensagem literal em substância do diretor ao Bloco 03

> “Eu usei sem querer o Bloco 02 dos personagens. Leve tudo isso para o Bloco 03, porque ele já tem todo o contexto do leitor híbrido e não quero misturar os blocos.”

O diretor **não abandonou** a experiência anterior. Pelo contrário: os ensaios de interação trouxeram elementos novos ao leitor existente. O Bloco 02 reconheceu, ao consultar o GitHub, que parte importante já existia no Bloco 03; por isso, **não apresentar o novo trabalho como recomeço da revista**, nem alterar a fábrica editorial.

**Objetivo visual:** fazer uma revista digital que oferece a nostalgia da revista física aberta e da página virada com a mão, mas aproveita as vantagens digitais: movimento cinematográfico **sem alterar a fotografia original**, inspeção técnica por zoom, suporte a aberturas de duas páginas e responsividade de verdade.

**Frase operacional de design:** *o leitor vê uma revista de verdade; as ferramentas surgem do conteúdo e do gesto, não de painéis que envolvem uma revista em outro aplicativo*. Sem menus laterais de zoom, barra de teste acima/abaixo, retângulo de livro dentro de interface genérica ou efeitos automáticos disputando o texto. O menu discreto/hambúrguer e os controles de acessibilidade já previstos pelo Bloco 03 **não devem ser arbitrariamente eliminados**, mas ficam fora da superfície editorial durante leitura imersiva, acessíveis quando necessários.

---

## 2. O que já existia e NÃO DEVE SER RECRIADO

**Base histórica existente no repositório, verificada pelo Bloco 02:**
- [`v0.3 consolidada`](../prototipos/estrutura-vazia-v03-consolidada/README.md): Folhear e Contínua, paginação dinâmica, testes de integridade/reflow, fontes ajustáveis, sumário, textos/figuras/tabelas, capa/contracapa e anúncio opcional; preservação de conteúdo e testes automatizados. Não equivale à física de virar papel.
- [Leitor piloto 29/10](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/README.md): capa + abertura de 2 faces em desktop/viewport largo, uma em tela estreita, modo Contínua, menu hambúrguer e tentativas de estética unificada. **Prévia técnica, não identidade final homologada.**
- [Diretriz 26/10](DIRETRIZ-DA-DIRECAO-AVALIAR-MOTORES-DE-LEITURA-RESPONSIVA-2026-10-26.md): já mandava investigar **leitor atual A**, biblioteca HTML como **StPageFlip B**, plataforma pronta C e **híbrido D** sem descartar CSS/HTML/UX existente; comparar recursos/limitações em desktop, tablet e smartphone; verificar licença e não confundir `usePortrait`/one page com **leitura contínua**.
- [Diretriz de identidade visual de 20/10](DIRETRIZ-DA-DIRECAO-INTEGRAR-MOCKS-E-LEITOR-V03-2026-10-20.md): preservar capas cinematográficas, chamadas laterais, marca e miolo editorial dos mocks junto à arquitetura responsiva e aos dois modos de leitura.

**Constatação no código do leitor v0.3/piloto**, inspecionado em 01/11: `isWide() { return window.innerWidth > 900 }` e `spreadStart(n)` agrupam faces em pares quando a tela é considerada larga; `renderFlip` coloca lado a lado dois elementos HTML, mas a transição usa transformações CSS discretas, não uma **folha real dobrando diagonalmente**. Isso é **visão de duas páginas**, não promessa de **composição editorial única sobre duas faces** e tampouco física de papel. O corte de 900 px é uma regra do protótipo, não deve se tornar uma proibição de abertura dupla num celular em paisagem.

**Conclusão:** completar a v0.3 e a investigação da PR #46. Não criar outra fábrica, outro render editorial incompatível, outro menu global ou reconstruir a revista como PDF estático.

---

## 3. Linha do tempo dos estudos feitos no Bloco 02, avaliação REAL da direção

### Estudo visual A/B/C: três pranchas ilustrativas (NÃO prova de execução)

Foram produzidas **três pranchas conceituais** na mesma estética gamer escura da Back, usadas pelo diretor para visualizar:
- **A — capa cinematográfica:** cenário de fantasia com zoom lento, parallax suave, névoa, lua, áreas de texto preservadas. Diretor reconheceu que o movimento global de imagem é desejável; a prancha por si é estática, não um efeito implementado.
- **B — folhear:** simulação visual de revista física com sombra, verso e página se curvando. Ilustra a intenção, não prova que o leitor real faz isso.
- **C — imagens técnicas interativas:** GPU demonstrativa, hotspots, zoom regional e comparação visual. É conceito, não benchmark de placa NVIDIA/AMD/Intel; os números exibidos nas pranchas são elementos fictícios de composição, **não fatos**.

**Importante:** as três são **complementares**, não modos mutuamente exclusivos a escolher. O diretor disse expressamente: *“os três têm que estar contidos”* na experiência final.

### Laboratório funcional 1 — `Revista_Back_Laboratorio_A_vs_B.html`

HTML experimental autocontido, três páginas/cenas ilustrativas em **duas leituras lado a lado**, com controle de avance/retorno: à esquerda **movimento de câmera** (aproximar/afastar/deslocar), à direita tentativa de **virada com movimento**. Também se tentou ampliar regiões de hardware.

**Veredito do diretor, sem suavizar:** **APROVADOS COMO CONCEITO** dois movimentos: (a) imagem inteira **se aproxima suavemente**; (b) imagem inteira **se afasta lentamente**. **REPROVADOS NA EXECUÇÃO**: folhear, artificial e sem sensação de papel, e zoom técnico que apenas deslocava a imagem, sem centralizar/ampliar a peça desejada. Ele disse que o zoom “realmente não funcionou”. **Não reutilizar esse zoom como solução.**

### Laboratório funcional 2 — demonstração interativa dentro do Chat Bloco 02

Protótipo com duas abas isoladas: **folhear orgânico em canvas com faixas curvas, frente/verso/sombra** e **placa-mãe demonstrativa vetorial** com regiões CPU, VRM, M.2, PCIe e RAM, foco via botões/pontos e zoom sobre o centro da região, permitindo arrastar.

**Veredito do diretor:** folhear **melhorou bastante**, mas não chegou ao ideal. Recomendou que **a ponta inferior direita seja puxada** para iniciar a dobra, e que a folha acompanhe o movimento da mão/mouse. **Zoom técnico agradou**, após ele localizar a segunda aba. O menu lateral, barra de zoom, hotspots com grandes símbolos “+” e controles eram **ferramentas de laboratório**, não layout aceito para a revista.

### Laboratório funcional 3 — `Revista_Back_Laboratorio_Integrado_Folhear_Zoom.html`

HTML experimental integrado, **com imagens incorporadas ao arquivo** para teste sem internet, combinando página de revista, efeito cinematográfico lento, inspeção técnica embutida na imagem e gesto de canto para folhear; sem o painel lateral visível da demonstração anterior. Não foi validado de forma conclusiva por ferramenta automática de navegador em todos os dispositivos. O HTML foi disponibilizado ao diretor como **prévia experimental**; não pertence à baseline v0.3.

**Veredito do diretor:** “ficou melhor”, “cada vez está melhor”; **zoom contextual de componentes agradou**, **aproximação/afastamento de imagens agradaram** e ficaram “quase perfeitos” como direção; **folhear ainda não convenceu**, parecia “forçado”, pouco orgânico. A identidade aproximada/laboratorial pode reduzir a percepção de realismo, mas não devemos culpar apenas o visual. Ele quer testar o motor numa verdadeira composição do Bloco 03, não mais uma “revista dentro de um quadrado” com interface estranha.

**Estado honesto dos arquivos de ensaio:** os HTMLs foram criados e entregues **como anexos na conversa do Chat Bloco 02**, não foram incorporados à árvore Git do Bloco 03 por esta transferência. A demonstração interativa central foi exibida diretamente no chat, não como biblioteca pronta. **Este handoff preserva o histórico e os requisitos; não alegar que os arquivos executáveis estão versionados na PR #46.** Se a engenharia precisar do código literal, obter esses dois HTMLs anexados à conversa ou autorização de importação apropriada; jamais substituir por uma implementação inventada alegando ser o protótipo testado. A pasta de conversa também contém as três pranchas conceituais.

### Estado de aceitação que deve orientar os próximos protótipos

| Recurso | Avaliação expressa do diretor | Regra de continuidade |
|---|---|---|
| Zoom lento da imagem inteira **para perto** | **Conceito aprovado**, qualidade visual já agradou | Preservar, adaptar à identidade, não mexer na imagem-fonte |
| Zoom lento da imagem inteira **para longe** | **Conceito aprovado**, qualidade visual já agradou | Preservar, adaptar à identidade, movimento discreto |
| **Zoom técnico por área/peça** | Execução inicial reprovada; versão contextual posterior **muito bem recebida**, perto do desejado | Levar para integração e validar na página real sem UI de laboratório |
| Folhear físico | **AINDA NÃO APROVADO** apesar de sucessivas melhorias | Prioridade número 1 para comparar engine pronta e sensação de papel |
| Página dupla | Conceito **já existente**, ampliado expressamente pelo diretor | Tratar par como unidade de composição, inclusive imagem atravessando as faces |
| Nova identidade visual | **Nenhuma alteração aprovada** | Bloco 03 reaproveita identidade real; protótipo não redefine marca ou design |

---

## 4. Requisitos novos de imagem cinematográfica (APROVADOS EM CONCEITO)

**Caso motivador:** uma ilustração/foto oficial, por exemplo um material de *Resident Evil* disponibilizado em press kit pela Capcom: **não é necessário modificar o arquivo original**, recortar permanentemente, redesenhar personagens ou inventar elementos. A própria janela de visualização funciona como câmera digital: a foto existente **se aproxima** lentamente, pode **se afastar** lentamente ou mudar pouco o enquadramento, criando profundidade/efeito túnel. CSS `transform: scale`/posicionamento da imagem/clipping são hipóteses de implementação de baixo custo, não recursos exclusivos de IA.

**Regras:**
- Entrada imutável, sempre com versão/fonte/crédito/direitos registrados; transformação é **somente de apresentação** durante a leitura.
- Preferir zoom discreto, slow ease, sem distrair, sem deslocar manchetes/citações ou exigir atenção. Pode pausar quando página não está visível e com `prefers-reduced-motion`.
- Se o leitor interagir com o zoom técnico, **pausar o movimento cinematográfico**; prioridade do controle humano.
- Não inventar textura/detalhe a partir de imagem pequena; usar mídia com resolução adequada. A licença do press kit precisa ser conferida pelo Bloco 05; “kit liberado” não significa autorização irrestrita para toda transformação.
- Não sobrepor múltiplos efeitos em toda página, nem mover texto enquanto alguém lê.

**Status:** A aproximação e o afastamento, como comportamentos, foram **aprovados**; duração, intensidade, e quais tipos de imagens os recebem são **parâmetros do Bloco 03 a testar**.

---

## 5. Requisitos novos de zoom técnico e hotspots invisíveis/contextuais

**Casos do diretor:** inspeção da ventoinha e geometria de refrigeração de GPU; desenho e contatos de CPU; componentes e caminhos/ligações de uma placa-mãe, **CPU → M.2 NVMe**, RAM, VRM, PCIe; comparação de sistemas e materiais. O propósito é **ver melhor e compreender o que o jornalista explica**, não ornamentar a foto.

**Experimento rejeitado:** arrastar a imagem inteira horizontalmente chamando isso de “zoom” ou pôr botões `+` ostensivos e menu de componentes ao lado da matéria.

**Comportamento desejado no desktop:**
1. Foto/diagrama ocupa seu slot nativo na página, com legenda editorial real. Sem modal obrigatório, toolbar de zoom persistente ou mudança de composição.
2. Ao **passar mouse numa região semanticamente marcada** (ex.: conector M.2), dar *indicação discreta* de que é inspecionável e **zoom gradual centrado precisamente no ponto/área**. O diretor sugeriu inclusive ativar automaticamente pela aproximação do mouse. **Testar hover com pequena latência/dwell para evitar disparos involuntários**; usar click/toggle para travar quando necessário.
3. A região escolhida é ampliada **de verdade**, mantendo a peça focalizada e permitindo pan dentro dos limites; ao sair/fechar, retorno suave ao enquadramento original. Legenda técnica contextual pode aparecer **dentro** da página, sem impor painel que mude o design da reportagem.
4. Coordenadas/áreas devem ser vinculadas à imagem na resolução original e sobreviver ao redimensionamento responsivo.

**Comportamento no celular/tablet:**
- Não há `hover` verdadeiro. Toque na região abre foco; gesto de pinça e arraste quando ampliado; tocar novamente, gesto de retorno ou comando acessível fecha foco. Não depender de passar mouse para descobrir/interagir.
- O leitor deve conseguir escolher a região **mesmo com um dedo** e também acessar hotspots por teclado/leitor de tela, com nomes `CPU`, `VRM`, `M.2`, etc.
- Em modo inspeção, **a foto captura o gesto de pan**, não o leitor de páginas; ao sair, volta o gesto de folhear. Controlar conflitos de eventos `pointer`, swipe, pinch e toque.
- **Não fabricar ligações elétricas** com base na fotografia: topologias PCIe/SSD só podem ser afirmadas usando diagrama/manual/medições de fonte. Exemplo anterior era esquema fictício, não placa comercial certificada.

**Proposta técnica não homologada:** uma camada interativa de regiões normalizadas/hotspots semanticamente invisíveis com foco via CSS transforms ou biblioteca de zoom de imagem testada. Avaliar hover suave **versus clique** com usuário real. Nada de painel lateral na revista final.

**Status:** o diretor **gostou da versão contextual** e quer integrá-la à identidade verdadeira; isso **não equivale a aprovação do código do laboratório como implementação final**.

---

## 6. PRIORIDADE MAIOR: físico de virar folha que ainda não convenceu o diretor

A animação atual melhorou mas parece **forçada/artificial**. O diretor quer **a experiência tátil/visual da folha**, com ponta inferior direita respondendo ao mouse/dedo, **dentro da página inteira**. A v0.3 usa `rotateY`/transições leves e os labs tentaram curvar faixas, mas não alcançaram o padrão esperado.

### Critérios observáveis de folheamento

- **Sem botão “Próxima” visível no miolo como requisito primário.** Na própria superfície da revista, o **canto inferior direito** oferece affordance discreta ao hover/proximidade/touch; ao puxar para o centro/esquerda, **a ponta inferior levanta primeiro**, com dobras em perspectiva coerente, sombra dinâmica que acompanha a dobra e exposição do **verso real daquela folha**.
- A curvatura **não pode ser a página inteira girando como porta**; deve responder **continuamente à posição do ponteiro/dedo**, preferencialmente com deformação diagonal.
- Com um arraste curto e soltura, a folha **retorna** à posição original; ultrapassando um limiar válido, **completa** a virada. Verificar retorno, inversão de sentido e não navegar acidentalmente ao inspecionar uma fotografia.
- Em páginas duplas, virar **apenas uma folha**, com a superfície direita tornando-se o verso esquerdo do próximo par e revelando a nova face à direita. **Frente/verso coerentes** e numeração lógica preservada; não trocar dois painéis como slides independentes.
- Sombras/texturas discretas e perspectiva compatíveis com papel fino, sem efeito exagerado de borracha/tecido; sem travadas, fantasmas de texto, serrilhado, espelhamento errado no verso ou desaparecimento de links.
- Mesmo motor deve permitir virar para trás pelo lado esquerdo e, se possível, navegação alternativa (teclado/toque/menu acessível) sem obrigar movimento para quem usa reduced-motion.

### Avaliar engines prontos antes de novo algoritmo caseiro

A investigação já foi determinada pela Direção na [PR #46](https://github.com/Saaimingo/Revista_Gamer/pull/46): **StPageFlip** (páginas HTML, capa isolada, eventos, sombras/curva/touch), opções como Turn.js sob verificação de licença e integração, Paged.js como paginador (não como promessa de dobra). **Não afirmar que alguma já resolveu sem rodar a comparação com conteúdo real da Back.** Verificar no celular, performance, CSS/DOM, sombra, gesto do canto **inferior direito** e se a orientação da folha realmente transmite a nostalgia desejada. Usar [demo pública do StPageFlip](https://nodlik.github.io/StPageFlip/) apenas como referência do motor, não como avaliação concluída em nossa identidade.

**Critério de veto editorial:** “ficou melhor” **não é aprovação**. O diretor foi explícito: folhear ainda precisa convencer. O Bloco 03 compara alternativas num mesmo layout e decide o que **propor**; a aprovação é da direção.

---

## 7. Páginas duplas / “duas faces” são uma COMPETÊNCIA EDITORIAL, não só breakpoint

**Demonstração verbal do diretor:** numa tela de 27” ou monitor horizontal amplo, após ver a **capa (face 01)**, a revista se abre com **faces 02 (esquerda) e 03 (direita)**; a próxima abertura será **04–05**, depois **06–07**. A matéria pode atravessar a dupla. Não confundir **folha física** (frente e verso) com **face numerada**. Capa e contracapa normalmente ficam isoladas; a contagem dos pares segue numeração editorial consistente.

**Exemplos editoriais exigidos:**
- Mapa panorâmico de um jogo distribuído por **duas páginas abertas**, com pontos de interesse e texto/legenda legíveis, com atenção à dobra central.
- Diagrama da arquitetura de placa-mãe distribuído por 04–05, partindo da CPU na esquerda até PCIe/SSD M.2 na direita, com informações **verificadas** sobre ligações e capacidade.
- Grande arte panorâmica autorizada com zoom/pan sobre **o par como superfície única**, sem duplicar/inverter fatos em cada face.
- Matéria com texto substancial distribuído de modo editorial em ambas as páginas; **duas páginas abertas podem pertencer à mesma reportagem**, e a virada não pode cortar uma figura essencial no centro sem plano.

**Estado atual:** o v0.3/piloto já exibe dois HTMLs lado a lado. **Não há evidência de schema de `spread` semântico único com regiões/âncoras atravessando páginas nem de interação ampliada sobre o par completo**. Não confundir display de duas páginas com prova desses recursos.

**Modelo de dados/contrato a estudar (não imposto):** `physical_page_id`, `face_number`, `spread_id`, `spread_role=left|right|cover|backcover`, `story_id`, `anchored_blocks`, `spread_asset_id`, `gutter_safe_area`, `reading_anchor`. O layout deve decidir com conhecimento de `spread` e do espaço central; **o conteúdo lógico permanece o mesmo ao alternar Folhear/Contínua**. Se figura abrange dupla, preservar sua semântica e seu crédito sem renderizar duas imagens contraditórias.

### Desktop, tablet e celular horizontal

- **Desktop ultrawide/widescreen:** dupla por padrão quando legibilidade comportar, não dois livros separados.
- **Tablet:** retrato uma face ou dupla se couber; paisagem tende a dupla, mas respeita altura útil, densidade e tamanho de fonte.
- **Celular em pé:** uma face com texto confortável ou modo Contínua; não usar miniaturas de duas páginas como única leitura.
- **Celular deitado:** **oferecer explicitamente visão de duas páginas**, e explicar de modo discreto que girar o aparelho habilita a experiência, **desde que haja legibilidade**. Num 844×390 típico, duas páginas de altura total deixam texto pequeno; permitir **visão geral em dupla com zoom/pan** ou leitura confortável individual, em vez de forçar fonte ilegível. Escolha manual possível; não usar só `window.innerWidth > 900` como regra que impede o teste. Se orientação/viewport não permitir dupla prática, dar alternativa sem esconder conteúdo.
- **Mudança de orientação/modo:** manter **mesmo par, matéria e âncora de leitura**; não voltar à capa, não perder parágrafos, não duplicar blocos e não disparar auto-scroll de forma inesperada.

**Regra de disputa de gesto:** em leitura, arrastar canto = folhear; em foto ampliada = pan/zoom; em scroll = scroll; em panorâmica dupla = pan de spread; definir prioridade e affordance sem capturar todos os swipes.

---

## 8. Identidade visual, mídia, desempenho e acessibilidade (sem negociação tácita)

**Identidade do Bloco 03 permanece soberana:** marca `BACK`, capa cinematográfica, paletas e miolo jornalístico dos mocks aprovados apenas na medida já ratificada; não remodelar a revista a partir de laboratório com barra e menus. **A revista é a viewport**. Incluir menu discreto apenas quando necessário, preferências preservadas, texto selecionável, links/sumário e áudio iniciado por ação, conforme projeto anterior.

**Imagens oficiais:** foto/press kit é ativo com titular e licença, salvo aprovação Bloco 05; animação de enquadramento não altera os bytes do original, mas uso/crédito e eventuais restrições do titular continuam sob análise. Nada de atribuir ilustração original de IA como screenshot do jogo, inventar uma placa real a partir do desenho nem divulgar conteúdo de testes como matéria publicada.

**Performance:** demonstrar em desktop, tablet e Android razoavelmente modesto, evitando renderizar a edição inteira como 100 canvases ou criar clones pesados de todas as páginas. Priorizar GPU transforms quando cabível, mídia em resolução adequada sob demanda, lazy loading, sem redesenho desnecessário, sem orçamento inventado. Medir FPS, memória e estabilidade realmente, não prometer 60 FPS sem benchmarks. Zoom não poderá degradar textos/legendas; preferir DOM HTML vivo.

**Acessibilidade:** movimento reduzido → efeito estático/simplificado; todos os controles por teclado e por toque; zoom acessível por foco; cor/contraste; evitar interações exclusivamente por `hover`; âncoras de texto estáveis entre modos; permitir sair de qualquer interação sem perder posição.

**Diferenciar estados:** laboratório, proposta visual, código funcional, experiência aprovada e deploy são coisas distintas.

---

## 9. Sequência recomendada ao Bloco 03 (SEM autorizar Codex por este handoff)

1. **Receber esta transferência e reler documentos existentes**: v0.3, diretrizes 20/10 e 26/10, PR #46. Reconhecer no primeiro retorno ao diretor o que é antigo e o que é novo.
2. **Comparação de folhear no layout REAL da revista**, mesmos 4–6 pares com HTML real: engine candidata pronta (StPageFlip) versus v0.3 e, se viável, outro motor de licença verificável; testar **canto inferior direito arrastável, retorno, frente/verso, curva, sombra**. Não reconstruir outro motor caseiro sem demonstrar por que engine pronta falha.
3. **Estender teste de página dupla** para `01 isolada → 02–03 → 04–05`, com **um mapa que atravessa o par** e com uma reportagem textual extensa; abrir/fechar, zoom de spread, centro seguro, giro mobile horizontal opcional.
4. **Incorporar zoom contextual de hardware sem UI de laboratório**, com mapa de áreas, hover/discoverability e toque/pan no celular; testar CPU, VRM, DIMM, M.2 e PCIe em imagem técnica de resolução suficiente (reais só com fontes/autorização).
5. **Aplicar câmera lenta aproximar/afastar** em arte original/permitida, sem mover texto e sem conflitar com inspeção/folhear.
6. **Inspecionar e comparar no mesmo conteúdo e mesmas dimensões**, conforme diretriz de 26/10: 390×844, 844×390, 768×1024, 1024×768, 1440×900, zoom de fonte 100–150%, reduced-motion, orientação alterada durante leitura, Android real quando possível. Medir legibilidade e performance; não apresentar capture bonita como prova do mecanismo.
7. **Mostrar ao diretor dois conjuntos de demonstrações**: (a) página dupla e foto técnica funcionando dentro da Back; (b) folhear físico com sua melhor engine e com gesto visível de canto. Pedir aceitação **separada** de cada componente, sobretudo o folhear.
8. **Só após avaliação/decisão** entregar missão de engenharia ao Codex, com biblioteca/versão/licença/scope/rollback/testes; **não** alterar motor editorial, personagens, jornalistas, imagens oficiais nem publicar.

### Critérios de aceite finais que o Bloco 03 deve PROPOR ao diretor

| ID | Exigência de teste | Falha rejeitada |
|---|---|---|
| V01 | Cena aproxima lentamente a foto e retorna sem mexer em texto | Recriar/corromper a imagem ou deixar tudo em movimento constante |
| V02 | Cena afasta lentamente a foto com enquadramento controlado | Corte irrelevante e efeito que distrai |
| V03 | Hover desktop no M.2 centra e amplia a **área correta** | Deslocar a foto sem aumento focal |
| V04 | Toque/pinça no M.2 funciona sem menu lateral | Hotspot impossível de tocar ou gesto captura o folhear |
| V05 | Canto inferior direito **levanta e dobra diagonalmente** durante o arraste | Girar retângulo como porta / salto de slide |
| V06 | Soltar antes do limiar devolve a folha; após limiar completa | Página avançar sem intenção |
| V07 | Frente/verso e pares 02–03 / 04–05 coerentes | Troca de duas imagens sem lógica física |
| V08 | Mapa/diagrama pode ocupar uma **dupla semântica** | Duas imagens isoladas, dobra cortando informação essencial |
| V09 | Celular em paisagem oferece visão da dupla sem obrigar letras minúsculas | Bloqueio fixo de 900 px ou layout ilegível |
| V10 | Trocar orientação/Folhear/Contínua mantém mesmo trecho | Voltar à capa ou perder parágrafos |
| V11 | Modo sem movimento e teclado/toque operam igualmente | Dependência exclusiva de mouse/hover |
| V12 | Sem toolbar/menu de laboratório na página | Alterar identidade/privilegiar painel externo |
| V13 | Arte/diagrama com proveniência, limites e créditos | Inventar resultado técnico, screenshot oficial ou direito de uso |

## 10. Delimitação de responsabilidade e encerramento da transferência

**Bloco 02:** transmitiu neste documento fielmente os experimentos e avaliações dirigidas pelo diretor, incluindo **o que reprovou**. Não redefinirá leitor, não mexerá no DNA de Carranca/Beto/Nina e não executará implementação visual fora da autoridade do setor.  
**Bloco 03:** **assume continuidade** desta frente visual/UX a partir das bases antigas e deste novo registro. Deve consultar contexto próprio e propor trabalho/testes próximos, sem copiar cegamente algoritmos experimentais.  
**Fundador/Direção:** mantém deliberação de identidade final, biblioteca, qualidade da dobra e autorização de implementação.  
**Codex:** atua quando receber missão aprovada; não é correto presumir que uma ideia ou este handoff autoriza deploy, compra de serviço, alteração de fábrica ou merge.

**Recado essencial:** O diretor valorizou os ganhos reais de **zoom técnico contextual** e **aproximação/afastamento da imagem original**, mas a **folha ainda não parece papel**. O Bloco 03 deve resolver o folhear sem perder a identidade, e fazer com que a **abertura dupla** não seja só uma regra de largura de tela, mas parte da linguagem editorial da Revista Back.

**Estado de transferência:** CONTEXTO ENTREGUE AO BLOCO 03; **os protótipos HTML executáveis permanecem nos anexos da conversa do Bloco 02 e ainda não estão versionados no GitHub**. A avaliação da direção está documentada aqui para que o próximo chat Bloco 03 não precise reconstruir a conversa inteira.
