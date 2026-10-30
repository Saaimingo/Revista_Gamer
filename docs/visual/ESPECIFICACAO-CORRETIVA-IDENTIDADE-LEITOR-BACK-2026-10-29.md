# BLOCO 03 → BLOCO FUNDADOR — PARECER CORRETIVO DE IDENTIDADE VISUAL E LEITOR DA REVISTA BACK

**Data:** 29/10/2026  
**Emissor:** Bloco 03 — Identidade Visual e Experiência de Leitura  
**Destinatário:** Bloco Fundador, para incorporar ao próximo handoff/prompt técnico ao Codex  
**Origem:** observação direta do diretor, que levou a este Bloco **capturas de todas as faces da primeira prévia navegável de dez páginas** (capa, duplas 2–3, 4–5, 6–7, 8–9 e contracapa 10). O Bloco 03 também leu o HTML, o README e o `design-qa.md` da implementação correspondente no GitHub.  
**Estado:** **diagnóstico e especificação corretiva de requisitos visuais já decididos pela direção**; não é homologação da prévia, ordem de execução independente ao Codex nem autorização para publicar ou alterar as personas.

## 0. Recado central da direção, sem diluição de escopo

> “O problema que eu trouxe ao Bloco 03 é a **IDENTIDADE VISUAL**. Não está ruim, mas não chega perto do que construímos. O hambúrguer ficou **fora da revista**; a revista é um quadrado centralizado, deixando tela sem uso. No celular, tablet, notebook, desktop e até TV, a própria revista deve ocupar **toda a área útil da tela**. Se houver duas páginas, a esquerda ocupa a metade esquerda e a direita a metade direita. A capa e a navegação que aprovei já estão decididas.”

**Decisões expressas do diretor — não reabrir:**
1. A leitura no celular é **imersiva**. A face da revista ocupa a área útil integral do viewport (descontadas apenas as áreas inevitáveis do navegador/sistema); nenhum cabeçalho, painel de controles ou rodapé de navegação pode reduzir o espaço editorial.
2. **Um botão hambúrguer discreto, SOBREPOSTO DENTRO da face**, abre todos os controles: Folhear, Contínua, tipografia, espaçamento, sumário, tema e demais ajustes. Menu fechado por padrão. Não deixar seletor Folhear/Contínua, setas, contador de sistema, barra fixa ou botões de avançar/voltar permanentemente visíveis **fora ou sobre** a área editorial. Em Folhear, oferecer gesto/tap em zonas laterais discretas; comandos acessíveis dentro do menu e teclado. Em Contínua, rolagem natural. Preferência explícita salva e respeitada.
3. A arquitetura da **capa** está definida: **BACK** grande, central e no topo; chamadas secundárias legíveis dos dois lados; grande imagem cinematográfica ao centro, em profundidade; manchete principal integrada na região inferior; **sem patrocinador, arte até a última borda**. Essa arquitetura persiste em edições de terror, mundo aberto, hardware etc., com variação temática sem perder a marca.
4. No computador/tela grande, o leitor deve ser igualmente **imersivo e responsivo**: se estiver mostrando duas faces, a página esquerda usa aproximadamente a metade esquerda do viewport e a página direita a metade direita, com uma dobra central discreta; sem livro pequeno dentro de moldura escura. Em telas estreitas, uma face por vez. Não simplesmente ampliar um bitmap ou PDF: textos HTML vivos, legíveis e refluíveis.
5. A direção aprovou a **experiência funcional mobile do Bloco 03** (revisão 27/10) e a **arquitetura de capa**; os cinco modelos de miolo são base em evolução. O alvo agora é fidelidade no produto real, não outra galeria PNG.

**IMPORTANTE:** o fundador já conhece o uso indevido de informações de bastidores da fábrica como páginas da revista. O diretor explicitou que esse tema está sendo tratado em outro setor; **NÃO É a causa principal deste parecer**. Não deixar a discussão de gates, SIWC, apuração, personalidade do Carranca ou revisão do texto deslocar a correção de UX/identidade do Bloco 03.

## 1. Evidências verificadas e causa técnica

**Implementação examinada:**
- Branch: [`codex/revista-back-primeira-edicao-20261029`](https://github.com/Saaimingo/Revista_Gamer/tree/codex/revista-back-primeira-edicao-20261029).
- [HTML do leitor piloto](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/index.html).
- [README da prévia](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/README.md).
- [Design QA do Codex](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/design-qa.md).

**Causa técnica diretamente observável no HTML:** o CSS define `--sheet-w:min(43vw,505px)`, calcula a altura da folha a partir dessa largura e limita `.stage-wrap` com `max-width:1450px`. Há regras adicionais que mantêm o conceito de **folha como cartão dentro de palco**. Em viewports grandes, uma folha jamais ultrapassa 505 px por esse token; duas folhas não ocupam as duas metades inteiras da tela. A captura de desktop confirma grandes áreas externas vazias. A interface de menu foi posicionada como um controle do *aplicativo*, não como overlay integrado à face editorial.

**Atenção ao termo “responsivo”:** passar em cinco viewports sem overflow horizontal é necessário, mas **insuficiente**. O `design-qa.md` registra ausência de overflow/erros e um resultado “passed”, porém **não verifica a ocupação real do viewport, a posição do hambúrguer relativa à face nem a equivalência gráfica com a referência aprovada**. Essa aprovação técnica não é aceite artístico do diretor.

**Origem das capturas:** fornecidas diretamente pelo diretor nesta conversa. Não estão anexadas nem presumidas como arquivos binários disponíveis nesta branch do GitHub. Este documento registra observações visuais, não afirma que subiu os prints.

## 2. Diagnóstico tela por tela da prévia recebida

### Tela 1 — CAPA (face 01/10)

**O que aparece:** ilustração de castelo/vale e lua; logotipo e manchete; chamadas laterais. O conjunto fica **como uma folha estreita centralizada em um fundo mais amplo**, em vez de tomar a tela. A arte domina menos do que deveria, o nome BACK fica relativamente reduzido, e chamadas/título disputam uma área muito menor que a tela disponível.

**Correção requerida:** o **próprio plano da capa** deve ser full-viewport. Marca BACK grande no topo **da face, não do site**; ilustração tratada como composição full-bleed com ponto focal e gradientes de contraste, chamadas em camadas laterais e manchete inferior com hierarquia clara. A cena chega até a borda de baixo na ausência de patrocínio. Capa fica **isolada** no modo Folhear, inclusive no desktop.

### Tela 2 — EDITORIAL E SUMÁRIO (faces 02–03)

**O que aparece:** duas folhas relativamente pequenas e centralizadas. O editorial parece uma folha de comunicação de estado da produção, com caixas; o sumário é uma lista essencialmente textual. A densidade e o desenho não correspondem à dupla editorial + sumário aprovada nos estudos.

**Correção requerida:** duas faces **encostadas visualmente no eixo central e distribuídas por toda a largura útil**. Editorial com hierarquia tipográfica forte, colunas, figura/citação quando houver conteúdo e rubricas consistentes; sumário com entradas visualmente distintas, miniaturas permitidas, números, editorias e links navegáveis. Não exigir personagens/fotos não aprovados para provar o layout: placeholders visuais de teste são suficientes. No celular, cada face ocupa a tela e é exibida individualmente.

### Tela 3 — ABERTURA DA REPORTAGEM + PRIMEIRO TEXTO (faces 04–05)

**O que aparece:** abertura de Gothic Remake com título moderado, imagem retangular de apoio e muito espaço subutilizado. Na face seguinte, blocos de texto corrido com quase nenhum projeto gráfico além do cabeçalho.

**Correção requerida:** aplicar **Modelo B03-03 — Grande Reportagem**: abertura de impacto com manchete grande, linha de apoio e cena editorial protagonista; na continuação, texto real legível, capitular ou lead, intertítulos, pelo menos um módulo visual/contextual quando houver, legendas, assinatura e destaques proporcionais. **Não** pintar parágrafos num PNG; texto permanece HTML selecionável. Se o artigo não fornecer mídia suficiente, melhorar composição com tipografia, ritmo, citação e espaços editoriais legítimos; nunca inventar fatos ou aumentar uma imagem sem critério.

### Tela 4 — CONTINUAÇÃO DA REPORTAGEM + FONTES (faces 06–07)

**O que aparece:** grande descompasso entre duas faces: à esquerda texto de continuação; à direita há uma face quase vazia com fontes. O leitor vê **um vazio visual enorme**, resultado de dividir informações sem reequilibrar páginas, e não de uma decisão editorial intencional.

**Correção requerida:** paginação sensível ao volume de conteúdo, evitando meia revista vazia em duplas; fonte/referências podem ser uma seção contextual e auditável no final da matéria ou módulo colapsável, conforme contrato editorial. Em caso de texto curto, reflow/rebalanceamento; em caso de artigo extenso, gerar quantas faces forem necessárias, sem cortar texto. Imagens/citações/legendas devem viajar com seus blocos, sem clones desnecessários.

### Tela 5 — FONTES, PROVENIÊNCIA E ESTADO EDITORIAL (faces 08–09)

**O que aparece:** blocos burocráticos muito destacados, repetição de avisos, área restante quase vazia. Visualmente, isso se parece com relatório de execução da fábrica.

**Correção requerida (escopo visual apenas):** o leitor público deve utilizar componentes editoriais, não a aparência gráfica do painel de operações. Caixas de status não podem virar a gramática dominante do miolo. **Não** mudar critérios de aprovação, fontes ou revisões neste trabalho: os responsáveis editoriais resolvem o conteúdo e a exposição dessas informações. Para ensaio de layout, usar corpo editorial de teste já disponível e metadados isolados do miolo.

### Tela 6 — CONTRACAPA (face 10/10)

**O que aparece:** fundo em degradê e chamada textual simples, com grandes regiões vazias, sem uma composição de fechamento com força comparável à capa.

**Correção requerida:** contracapa isolada, full-viewport e integrada à identidade BACK, com arte de fechamento original/de teste, assinatura visual e poucas chamadas bem resolvidas. Nenhum módulo de patrocínio vazio. Não inventar endereço de site, QR válido ou patrocinadores.

**Diagnóstico transversal das seis telas:** o padrão estético repete “folha escura, etiqueta pequena, texto e caixas”. Há responsividade suficiente para caber, **não para ocupar a tela nem para parecer a revista que a direção aprovou**. O problema central é a ausência de um **contrato obrigatório de composição e de geometria do leitor**, não uma prova de incapacidade do modelo Luna.

## 3. Especificação obrigatória de geometria e interação — B03-G

**B03-G01 — Área da revista:** a superfície editorial deve utilizar toda a área útil da viewport, **sem moldura externa permanente ou `max-width` de livro**. Testar com viewport dinâmica `dvh`, `vw` e áreas seguras; rolagem do navegador e barras do sistema operacional não são controláveis pela aplicação. Áreas internas podem ter margens editoriais legíveis, mas **não** grandes espaços vazios *fora* da(s) página(s).

**B03-G02 — Uma face:** em celular estreito/retrato e em tablet retrato quando duas faces não forem legíveis, renderizar **uma página de largura ~100% da área útil** e altura adequada ao viewport. Em Folhear, o conteúdo longo deve criar faces adicionais por reflow, não ser comprimido em letras minúsculas nem oculto.

**B03-G03 — Duas faces:** em telas largas compatíveis, página esquerda e direita recebem aproximadamente **50% da largura útil cada**; dobra central discreta; ambas ocupam a altura útil, com conteúdo e mídias redesenhados conforme largura/altura. Não usar o formato A4 fixo como desculpa para barras pretas/áreas imensas. Capa/contracapa **isoladas**. Quando a legibilidade não permitir duas faces, usar uma face mesmo em tela grande com janela estreita/zoom alto.

**B03-G04 — Controle invisível:** menu hambúrguer **dentro da revista, sobreposto à página** (posição relativa ao plano visível da página, respeitando safe area), fechado por padrão. A zona tátil não deve cobrir manchetes nem legendas; prever espaço de proteção interno ao conteúdo onde ele aparece. Sem barra superior externa, setas inferiores, contador de sistema, seletor de modo ou moldura operacional. Números de página **editoriais** discretos dentro do projeto da página são permitidos, distintos de controles de navegação. Foco, ESC e acessibilidade preservados.

**B03-G05 — Folhear:** mudar face por swipe horizontal e/ou regiões de toque de borda, teclado e controles dentro do menu; gesto vertical fica disponível para rolar conteúdo que precise. Efeito de virada pode ser biblioteca ou próprio, preferencialmente com movimento reduzido. Não usar animação se ela comprometer leitura.

**B03-G06 — Contínua:** scroll vertical natural, mesma identidade gráfica e mesmos blocos/legendas, sem páginas espremidas, sem barra de sistema sobre o texto. Relembrar posição/âncora ao alternar de Folhear para Contínua e vice-versa, girar tela, alterar fonte e espaçamento. A escolha explícita de modo prevalece sobre seleção automática.

**B03-G07 — Tela grande/TV:** as mesmas regras de ocupação valem em 1366×768, 1440×900, 1920×1080 e 3840×2160. Na TV, a composição cresce e redistribui colunas/imagens; não multiplicar indiscriminadamente a largura das linhas de texto. Manter tamanhos de leitura confortáveis e navegação compatível com teclado/controle.

**B03-G08 — Integridade:** texto não some nem duplica entre modos/resoluções; sumário conduz à âncora lógica correta; links, figuras, tabelas, citações e `figcaption` permanecem juntos ou com transição explícita. Conteúdo não deve depender de rasterizar páginas inteiras.

## 4. Gramática obrigatória de identidade — B03-I

**B03-I01 — Assinatura:** BACK imponente no topo da capa. Paleta base grafite/preto, branco, vermelho e roxo (tons/contraste definidos nos componentes), com cor de destaque temática por edição; a marca reconhecível não muda com o tema.

**B03-I02 — Capas:** arte cinematográfica em profundidade, chamadas laterais subordinadas, manchete principal inferior, sem anúncio quando nenhum estiver ativado. A capa nunca pode ser redesenhada como lista de informações ou cartão do aplicativo.

**B03-I03 — Miolo:** alternância intencional entre abertura visual, páginas de corpo editorial com colunas/legibilidade, módulos de apoio, intertítulos, capitulares, citações, imagens contextualizadas, legendas e fechamento. Evitar que todas as faces tenham o mesmo cabeçalho + bloco de texto + caixa. O visual deve ser reconhecido como a BACK mesmo sem a capa.

**B03-I04 — Templates:** mapear a biblioteca interna do Bloco 03 por identidade estável: `B03-01` nota rápida; `B03-02` radar; `B03-03` grande reportagem/dossiê; `B03-04` análise técnica; `B03-05` visual/comunidade. Para este teste, **B03-03 é obrigatório**. São modos de composição, **não cinco quantidades fixas de páginas**. A redação poderá escolher um template, reutilizá-lo e ajustar módulos. Não obrigar foto/video a existir; módulos opcionais não geram espaços vazios.

**B03-I05 — Mídia multimodal:** imagem principal, figuras menores, legenda, zoom e vídeo opcional como módulo editorial, acessível por acionamento explícito, com fallback textual. Não iniciar som automaticamente. Distinguir protótipo de material destinado à publicação; nesta prova, usar mídias sintéticas/permitidas e declarar seu caráter ilustrativo.

**B03-I06 — Comercial:** publicidade não deve dominar o template editorial; patrocinador apenas quando houver contrato/ativação, com separação e identificação inequívoca. Sem patrocínio, não reservar faixa vazia no rodapé da capa ou miolo.

## 5. Contrato recomendado para engenharia/diagramador — sem refazer fábrica

A fonte única da verdade é a **estrutura semântica da matéria + contrato visual versionado do Bloco 03**. O executor pode sugerir a composição, mas não redesenhar a identidade nem criar uma folha fixa de 505px por conveniência.

Exigir no handoff entre matéria → plano de páginas → leitor campos equivalentes a:
- `visual_contract_version`: versão congelável do perfil BACK/Bloco 03;
- `template_id`: `B03-01` … `B03-05` (neste teste `B03-03`);
- `editorial_blocks`: manchete, lead, parágrafos, intertítulos, citação, figuras com legenda, fontes e eventuais módulos multimídia;
- `cover_components`: logo, arte, chamadas laterais, manchete principal, `sponsor_enabled`;
- `reading_modes`: Folhear/Contínua sobre os **mesmos blocos**, sem duplicar conteúdo;
- `responsive_constraints`: geometria full-viewport, face(s) adaptativas, breakpoints por legibilidade e regra de preservação de âncoras;
- `design_evidence`: screenshots de viewport, medições de bounding boxes, verificação visual humana.

Esses campos são **proposta de contrato**; nomes exatos e integração ao esquema existente devem ser decididos pela engenharia sem duplicar o Motor Editorial. Não substituir as entidades atuais da fábrica sem migração/reversão planejadas.

## 6. Tarefas corretivas propostas para o próximo prompt ao Codex

**P0 — Fidelidade geométrica (antes de polimento):**
1. Remover a restrição de `505px`/palco central como geometria do leitor público. Manter apenas limitações de largura **internas à mancha de texto**, não da superfície de leitura.
2. Leitor ocupar viewport no desktop e celular. Dupla preencher metade esquerda/metade direita, sem áreas externas ociosas; capa e contracapa isoladas.
3. Colocar hambúrguer dentro do plano da revista, overlay e sem deslocar conteúdo; recolher TODOS os controles de sistema para o menu. Eliminar navegação permanente inferior/exterior; preservar swipe, scroll e teclado.
4. Reflow preservando legibilidade, integralidade do texto, âncoras e continuidade em zoom 150%, orientação/viewport e troca de modos.

**P1 — Recuperar identidade visual:**
5. Recriar a capa Gothic com a **arquitetura da capa BACK aprovada**, com composição cinematográfica que ocupe o plano.
6. Reconstruir abertura/continuação da matéria pelo **Modelo B03-03**, com variação real de hierarquia, densidade, imagem, legenda e caixas de apoio, sem reduzir tudo a cartões escuros.
7. Editorial/sumário/contracapa com composição específica; impedir duplas em que metade esteja quase vazia sem propósito editorial.
8. Ligar os cinco templates ao contrato do diagramador. Não pedir que o LLM invente cada página do zero; usar componentes determinísticos e decisões editoriais versionadas.

**P2 — Polimento e regressão:**
9. Contraste, legibilidade em tela grande/pequena, media lazy-load, desempenho em dispositivos modestos, reduzido movimento, foco e leitura por voz.
10. Comparações lado a lado das **mesmas telas** com referências do Bloco 03, não só um `design-qa: passed` de ausência de overflow.

**NÃO FAZER neste escopo:** reescrever Carranca/Beto/Nina, alterar notícias, refazer coleta/checagem/revisor, mexer nos gates, mudar marca, publicar, acionar API/SIWC, produzir nova edição, adotar outra biblioteca flipbook sem decisão. Pode usar um texto de ensaio substancial ou a mesma reportagem já existente como entrada de layout, independentemente de seu status de revisão, **exclusivamente na prévia privada**.

## 7. Critérios verificáveis de aceite — necessários, nunca só `no-overflow`

1. **Matriz de telas:** 360×740, 390×844, 768×1024, 1024×768, 1366×768, 1440×900, 1920×1080 e, se viável, 3840×2160; retrato/paisagem, fonte 100% e 150%, matéria curta/longa.
2. **Geometria medida:** registrar `getBoundingClientRect()` da(s) face(s) frente ao viewport. Folha única ocupa virtualmente largura útil total; em dupla, largura combinada das faces ocupa virtualmente a largura útil toda, com divisão aproximadamente 50/50, descontando apenas dobra/áreas seguras e **sem wrapper central limitante**. Altura editorial usa viewport útil; conteúdo refluído não é amputado. Quando o conteúdo precisar de mais faces, gerar mais faces.
3. **Ausência de interface permanente:** screenshots com menu fechado devem mostrar somente conteúdo editorial e o pequeno hambúrguer **sobre** a folha; sem botões/contadores/segmentações externos. Provar abertura/fechamento do drawer e todos os controles no interior dele.
4. **Continuidade:** escolher um parágrafo no meio da matéria, trocar Folhear↔Contínua, girar tela, alterar fonte, voltar; comprovar âncora estável e texto integral.
5. **Reprodução do Modelo 03:** cotejar capa, abertura e continuação com a referência aprovada; mostrar hierarquia, composição, imagem/caption e ritmo editorial. **Avaliação humana do Bloco 03 e diretor** necessária, não substituída por teste automático.
6. **Dupla e contracapa:** capa/contracapa isoladas, pares corretos, sem folha extra indevida e sem uma face praticamente vazia por falha de paginação.
7. **Relatório honesto:** capturas por viewport e modo, diferenças remanescentes e testes realmente executados; preservar v0.3 e os protótipos anteriores, permitir rollback. Teste em navegador responsivo não se confunde com aparelho físico.

**Gate de aceite:** (a) integridade/UX automatizada, (b) **fidelidade artístico-editorial inspecionada e ratificada pelo diretor**. Um `design-qa passed` técnico sem o segundo gate **não** autoriza declarar a identidade integrada.

## 8. Handoff ao fundador e prioridade recomendada

**Ação solicitada ao Bloco Fundador:** incorporar esta especificação ao próximo prompt do Codex **como contrato visual obrigatório da implementação**, separado dos problemas de redação e apuração já conhecidos. O caminho de menor retrabalho é corrigir o leitor existente na branch de trabalho, com screenshots antes/depois, sem reiniciar a fábrica. Consultar primeiro a branch/arquivos atuais para evitar sobrescrever mudanças locais.

**Referências normativas e de ensaio:**
- [Diretriz original: unir mocks cinematográficos ao leitor v0.3](https://github.com/Saaimingo/Revista_Gamer/blob/main/docs/visual/analises-fundador/DIRETRIZ-DA-DIRECAO-INTEGRAR-MOCKS-E-LEITOR-V03-2026-10-20.md).
- [Issue #15 — integração visual e funcional](https://github.com/Saaimingo/Revista_Gamer/issues/15).
- [Laboratório v0.3 consolidada](https://github.com/Saaimingo/Revista_Gamer/tree/main/docs/visual/prototipos/estrutura-vazia-v03-consolidada).
- **Arquivos de referência entregues ao diretor e inspecionados pelo Codex local:** `Revista_BACK_B03_Mobile_Imersivo_2026-10-27.zip` (interação mobile aprovada); `Revista_BACK_Bloco03_Cinco_Modelos_Editorais.zip` (biblioteca editorial, em evolução). A presença destes ZIPs em Downloads do PC **não** significa que seus bytes estejam neste repositório; conferir no ambiente local.
- [Roteiro de retomada da primeira edição](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/engenharia/REVISTA-BACK-RETOMADA-PRIMEIRA-EDICAO-2026-10-29.md).

**Conclusão:** A prévia demonstra que existe uma cadeia técnica capaz de gerar HTML navegável, mas **não demonstra implementação fiel da identidade BACK**. O problema observável é de contrato visual, geometria de viewport e templates. Nenhuma observação aqui é diagnóstico definitivo de insuficiência do GPT-6 Luna. O diretor pede que a próxima execução **pareça e se comporte como a revista que aprovou**, não como um livro pequeno dentro de um site.
