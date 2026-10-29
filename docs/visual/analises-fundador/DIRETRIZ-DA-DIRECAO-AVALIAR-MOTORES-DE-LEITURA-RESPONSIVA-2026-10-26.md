# DIRETRIZ DA DIREÇÃO — BLOCO 03
## Avaliar motores de revista digital existentes e experiência de leitura adaptativa por tela

**Data:** 26/10/2026  
**Solicitante:** Direção da Revista Back (repositório técnico `Revista_Gamer`)  
**Destinatário:** Bloco 03 — Identidade Visual e Experiência de Leitura  
**Natureza:** prerrogativa expressa para **investigação e comparação de alternativas**; não é escolha antecipada de biblioteca, ordem de substituir código ou aprovação para produção.  
**Status:** avaliação solicitada; decisão técnica e visual permanece pendente de comparação e aprovação da Direção.

### 1. A pergunta exata da Direção

> Por que desenvolver do zero a mecânica visual de uma revista virtual quando há bibliotecas e plataformas de flipbook existentes? O Bloco 03 deve verificar se conseguimos aproveitar parte ou todo o leitor pronto, inclusive se o próprio mecanismo já adapta automaticamente o comportamento para celular, tablet e notebook. Uma revista digital não precisa ser operada do mesmo jeito em todos os dispositivos.

**Separar duas coisas que não devem ser confundidas:**
1. **A fábrica editorial:** pesquisa, jornalistas, checagem, direitos, composição e produção de conteúdos. Este pedido não altera a ENG-CODEX-012 nem esses contratos.
2. **O leitor público:** como o visitante vê páginas, imagens, texto, navega e lê em diferentes tamanhos de tela. É EXCLUSIVAMENTE este segundo componente que deve ser comparado com software existente.

O Bloco 03 continua responsável por identidade visual, capa, miolo, UX, responsividade, legibilidade, acessibilidade e critérios de aceite. O Codex implementará somente a opção aprovada mais tarde; não mandar reconstruir a fábrica.

### 2. Hipótese a investigar — comprar/adotar/adaptar versus construir

Testar lado a lado:
- **A — leitor atual:** `docs/visual/prototipos/estrutura-vazia-v03-consolidada/`, com modos Folhear e Contínua, reflow e paginação verificados em laboratório. É o baseline: **não apagar nem descartar** este trabalho. Preservar sua integridade de texto, links, fontes ajustáveis, sumário, anúncio opcional e identidade gráfica.
- **B — biblioteca open source integrada:** StPageFlip (`page-flip`), ou outra candidata de licença verificada. Aproveitar mecanismo de virada de páginas; conservar diagramação, texto real e visual da Back. Testar como renderiza **HTML real, não somente fotos de páginas/PDF**. Verificar peso, manutenção, erros abertos, eventos de navegação, licença MIT e compatibilidade.
- **C — plataforma/leitor de revista pronto:** serviço de flipbook/visualização por PDF ou HTML incorporado, quando fizer sentido para comparação. Verificar custo real, marca do serviço, dependência de hospedagem externa, privacidade, exportação, personalização e capacidade de integrar textos vivos e interatividade. Não contratar, cadastrar, hospedar nem publicar nada durante esta avaliação.
- **D — híbrido:** motor de flipbook para telas grandes e modo Contínua já desenvolvido para smartphone, ambos consumindo os MESMOS blocos editoriais e referências de conteúdo. Considerar inclusive reutilizar somente animação/controles e manter o paginador existente.

**Orientação:** não presumir que uma solução pronta seja melhor nem que o mecanismo artesanal já seja a escolha correta. Medir e demonstrar. Código de terceiros deve ser usado pela licença/API autorizadas; nunca copiar código proprietário de produto comercial.

### 3. O ponto central: celular NÃO é tablet NÃO é notebook

Projetar por **largura efetiva, altura, densidade, orientação, preferência do leitor e modo de entrada**, não apenas por detecção frágil de user-agent.

**Smartphone estreito em retrato (ex.: 360–430 px):**
- Avaliar se a biblioteca muda automaticamente para **uma página**, para **scroll contínuo**, ou somente reduz visualmente uma revista fixa (são comportamentos diferentes).
- Dar preferência a leitura confortável com **texto refluído em largura utilizável**, rolagem natural, imagens redimensionadas e sem zoom obrigatório para ler cada linha.
- Se o flipbook oferecer apenas *single page* ou swipe, isso **NÃO significa modo de leitura contínua**. Testar integração híbrida com o modo Contínua do v0.3.
- Permitir que o usuário escolha Folhear ou Contínua quando ambos forem legíveis, e **salvar a escolha** de modo previsível, com opção de desfazer o automático.
- Garantir que swipe para folhear não capture todo gesto vertical que o usuário precisa para rolar a página.
- Ao girar a tela, ampliar fonte ou mudar para modo contínuo, **preservar âncora/trecho de leitura**; não retornar à capa nem esconder parágrafos.
- Sem áudio iniciado automaticamente, animação obrigatória, sobreposição de barra ao texto ou pop-up invasivo.

**Tablet em retrato ou paisagem (ex.: 768–1024 px, variável):**
- Verificar se o formato aceita uma página confortável em retrato e duas faces em paisagem **somente se couberem legivelmente**.
- Testar toque, arrastar a página, rolar texto longo, virar página e ajustar fonte. Não assumir que tablet reproduz exatamente o desktop.
- Avaliar se o modo Folhear realmente beneficia a leitura; oferecer Contínua e respeitar reduced-motion.

**Notebook/desktop (ex.: 1024–1920 px e zoom do navegador):**
- Testar folha/duas faces com giro visual convincente, capa e contracapa isoladas, sombra/dobra e navegação por teclado/mouse.
- Texto selecionável, legível e indexável; imagens com alt e direitos; links/citações e sumário funcionais.
- Testar zoom 125%/150% e janela estreita; layout não pode truncar textos nem inventar faces em branco erradas para acomodar livro.

**Em todos os dispositivos:**
- Modos opcionais e previsíveis (Folhear/Contínua); preferência de `prefers-reduced-motion`; transição sem perda de scroll/âncora; conteúdo idêntico em ambos.
- Adaptação NÃO é somente encolher PDF; usar texto HTML vivo quando viável.
- Compatibilidade com recursos de acessibilidade, seleção/cópia de texto permitido, navegação por teclado, links internos, busca/sumário e carregamento progressivo.
- Estimar impacto em aparelhos modestos (~4 GB RAM); controlar custo de renderizar livros longos, muitas imagens, clones de DOM, handlers/listeners e animações por quadro.

### 4. Descoberta inicial verificável — StPageFlip NÃO deve ser superestimada

Documentação oficial em 26/10/2026:
- [StPageFlip — repositório, documentação e licença](https://github.com/Nodlik/StPageFlip)
- [StPageFlip — parâmetros do mecanismo](https://github.com/Nodlik/StPageFlip/blob/master/src/Settings.ts)
- [Demo oficial](https://nodlik.github.io/StPageFlip/)

A documentação apresenta `usePortrait` e eventos de mudança de orientação para livro em paisagem/retrato; a biblioteca aceita páginas HTML e modo de uma página. Há `mobileScrollSupport`, **mas esse parâmetro regula a interação de rolagem/toque com o livro**, não prova uma mudança automática para apresentação como artigo em scroll contínuo. Portanto, **NÃO afirmar que StPageFlip já resolve a leitura contínua mobile sem um teste real**. Existem relatos de problemas de ciclo de render após `destroy()` e de fluxo de folhas nas issues atuais: auditar antes de integrar. Um híbrido pode ser melhor.

Alternativas para comparação: [Turn.js](https://www.turnjs.com/) como referência de flipbook HTML, com verificação jurídica/licença e dependências; [Paged.js](https://pagedjs.org/) para paginação a partir de HTML, não como promessa de efeito flipbook. Serviços fechados podem ser apresentados como benchmark de UX, mas seus códigos internos não são copiáveis sem licença. A fonte do recurso e data de verificação devem constar do parecer.

### 5. Ensaio comparativo obrigatório (sem substituir sistema aprovado)

Usar um **mesmo conteúdo editorial permitido para teste** — idealmente um rascunho interno preservado, se autorizado para esse escopo, ou texto de demonstração substancial —, **mesmas imagens elegíveis**, mesmos títulos, seções longas, citações, legendas, tabela larga, sumário e links. Não alterar DNA dos jornalistas e não exigir novo trabalho SIWC do Codex para obter texto apenas para este teste.

Matriz mínima de viewport e estados:
- 390×844 (Android retrato), 844×390 (Android paisagem).
- 768×1024 e 1024×768 (tablet retrato/paisagem).
- 1024×768 e 1440×900 (notebook/desktop).
- Em cada viewport: fonte 100% e 150%, espaçamento ajustado, matéria curta e extensa, movimento reduzido, modos Folhear e Contínua, alternância durante a leitura, teclado e toque.
- Teste especial: smartphone folheia → alterna para scroll **no meio da reportagem** → gira aparelho → retorna para Folhear; o leitor permanece no mesmo parágrafo/âncora possível, sem texto ausente/duplicado e sem cliques perdidos.
- Testar o comportamento **automático real** da biblioteca sem customização primeiro; depois separar claramente o que foi acrescentado pela Back.
- Comparar navegação/tempo de resposta e fluidez, integridade de todas as seções, imagens/atribuições, responsividade, necessidade de zoom, CPU/RAM quando possível e dificuldade/custo de manutenção.
- Realizar ao menos teste em Chromium responsivo e teste manual em Android real se houver disponibilidade; indicar quando **não** houve teste em aparelho físico. Não declarar validação visual sem navegador aberto.

### 6. Entregas que espero do Bloco 03

1. **Parecer de viabilidade com fontes**, cobrindo as quatro estratégias A–D, funcionalidades nativas e funcionalidades que exigem integração nossa; licença, restrições e risco de dependência de fornecedor.
2. **Comparação prática navegável**, no mesmo conteúdo, em pelo menos dois caminhos viáveis: leitor v0.3 atual versus integração StPageFlip ou biblioteca mais adequada. Se um caminho não puder ser implementado nesta fase, explicitar e apresentar demonstração oficial verificável sem declarar comparação concluída.
3. **Mapa de responsividade** em celular, tablet e notebook: número de faces, orientação, comportamento do swipe/scroll, mudança automática/manual, acessibilidade e política de preferência.
4. **Comparação visual** com o conceito cinematográfico aprovado como referência para capa/miolo: biblioteca não pode reduzir a Back a PDF em imagens ou leitor genérico com branding de terceiros.
5. **Recomendação fundamentada**: adotar, adaptar ou continuar com motor próprio, destacando o que preservar da v0.3, módulos a substituir, migração gradual, testes de regressão e possibilidade de reverter.
6. **Handoff técnico posterior ao Codex**, apenas após apresentação das alternativas e decisão da Direção. Indicar biblioteca e versão exatas, licença, interface necessária, contrato com o render/editorial, testes e rollback.

### 7. Limites e decisões reservadas

Esta diretriz **AUTORIZA estudar, comparar e produzir provas internas de baixo custo no âmbito do Bloco 03**. Não autoriza substituir a casca v0.3 aprovada para laboratório, alterar o Motor Editorial, reabrir ENG-CODEX-012, comprar licença, hospedar a revista, criar contas, publicar, fazer deploy, copiar bibliotecas comerciais não licenciadas ou decretar biblioteca vencedora antes da revisão humana.

Se houver choque com requisitos aprovados, registrar alternativas e pedir deliberação. **Objetivo não é reinventar a roda nem descartar trabalho útil; é entregar ao leitor a melhor revista digital possível em cada dispositivo.**
