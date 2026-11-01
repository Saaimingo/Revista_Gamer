# Revista BACK | Bloco 03 — Especificação de materialidade do papel, folhear e página dupla

**Data:** 01/11/2026  
**Origem:** decisões e feedback do diretor nos protótipos de folheamento e mapa aberto, complementados pelo handoff do Bloco 02 (Issue #50).  
**Estado:** **direção de experiência ratificada**; parâmetros de física, integração de biblioteca e acabamento **a testar**. Não é homologação de motor, arte final, autorização para Codex, merge ou publicação.  
**Escopo:** leitor público, interação e aparência material de revista impressa digitalizada. **Não** modificar redação, DNAs, pipeline editorial, direitos de imagens, marca BACK nem os cinco templates de conteúdo já definidos.

## 1. Regra principal: a tela é a revista, não uma vitrine contendo um livro

A experiência de leitura imersiva foi aprovada. **Preservar como requisito obrigatório**:

- **Celular retrato:** uma face ocupando toda a área útil do viewport; sem moldura com grandes margens ou barras de controle.
- **Tablet/computador/tela ampla:** duas faces abertas ocupando juntas virtualmente toda a área útil, cada uma aproximadamente metade da largura, com miolo no centro; capa e contracapa isoladas.
- **Celular paisagem:** opção de visualizar uma abertura dupla, sem impor letras minúsculas. Se for impossível ler a dupla confortavelmente, oferecer zoom/pan ou leitura por face individual.
- **Hambúrguer discreto dentro do plano da revista**, fechado por padrão; opções Folhear/Contínua, ajustes, sumário e navegação acessível ficam ali. Nada de setas, contadores de aplicativo ou barras permanentes sobre/fora do conteúdo.
- **Modo Contínua** permanece; o leitor escolhe o modo. Preservar conteúdo, âncoras e preferências em troca de modo, orientação e tamanho de fonte.
- **Materialidade é interna às bordas do leitor.** Não reintroduzir uma revista pequena centralizada para simular sombras, capa rígida ou proporção de papel. Se houver conflito entre realismo e ocupar a tela, preservar o viewport e ajustar efeitos materiais.

## 2. F01 — Virada por clique/toque é a ação principal

**Feedback do diretor:** a animação de virada do motor experimental agradou; porém o ponteiro/dedo **fica preso à folha** durante o arraste, exigindo chegar ao outro lado. Isso é **reprovado na interação**. O clique curto no canto, que vira automaticamente, foi bem recebido.

**Requisito normativo:**
1. **Clique ou toque curto na região do canto inferior direito:** iniciar imediatamente uma **virada completa e autônoma**, com a física de dobra e sombra existente que agradou; não exigir arrastar nem manter pressionado.
2. **Canto inferior esquerdo:** operação simétrica para retornar, respeitando pares, frente/verso e histórico de leitura.
3. **Arraste manual não é obrigatório.** Pode ser temporariamente **desativado** se o motor não conseguir assegurar liberação. Se existir como recurso opcional, o gesto acompanha a ponta com fluidez, e ao soltar decide automaticamente por **voltar ou completar**; nunca permanecer agarrado ao cursor.
4. Eventos `pointerup`, `pointercancel`, perda de foco/janela, interrupção do toque e saída do ponteiro devem encerrar/abortar a captura de gesto de modo consistente. Não bloquear seletivamente o cursor ou a navegação por teclado.
5. Toques em imagem ampliada, seleção de texto, legenda, link ou controles contextuais **não devem disparar virada**. Definir zona de canto pequena e suficientemente acessível (alvo de toque confortável), sem cobrir elementos editoriais essenciais.
6. Considerar `flipNext('bottom')`/`flipPrev('bottom')` da API StPageFlip **como hipótese** para acionar animação automática pela parte inferior, não como prova de que a experiência está corrigida. Avaliar configuração de clique e tratamento de `pointer` do motor em teste real; não criar segundo motor paralelo.

**Critério de aceite F01:** vinte cliques/toques curtos alternados nos cantos e dez interrupções de gesto, em mouse e touchscreen, sem “folha presa”, avanço involuntário, travamento nem necessidade de arraste longo; animação considerada satisfatória em inspeção humana do diretor. **Números são metas de teste propostas, não evidência de testes executados.**

## 3. P01 — Anatomia visível de revista impressa, sem virar decoração genérica

Em dupla aberta, as faces **não podem parecer dois cartões colados com uma linha vertical desenhada**.

**Componentes obrigatórios a experimentar juntos:**

| Elemento | Comportamento visual esperado | Evitar |
|---|---|---|
| **Lombada/miolo** | Depressão óptica central estreita, com gradiente de luz/sombra assimétrico e curva suave dos dois lados, coerente com o papel | Linha reta arbitrária, divisória grosseira ou faixa preta larga |
| **Curvatura interna** | Luz e compressão sutis próximas à dobra; imagem panorâmica mantém continuidade com pequena perda/oclusão física plausível | Distorcer texto, dobrar mapa artificialmente ou esconder informação essencial |
| **Bordas externas** | Limite lateral/topo/base quase imperceptível, realçado apenas o suficiente por reflexo/sombra | Moldura externa de aplicativo, páginas com grandes bordas arredondadas |
| **Espessura/pilha** | Fina sugestão de folhas já viradas e folhas restantes nas extremidades, adaptada à posição na edição | Pilhas espessas, efeito caderno capa dura, textura borrachuda |
| **Superfície de papel** | Granulação/reflexo extremamente discretos conforme tema, subordinados ao conteúdo | Textura pesada, sujeira, desfoque ou perda de nitidez do texto |
| **Sombra da virada** | Sombra dinâmica acompanha a ponta e o verso real da folha | Rotacionar retângulo como porta, mover duas páginas juntas ou mostrar verso espelhado |
| **Mancha editorial** | Respiro e distância da lombada para texto/legendas; elementos importantes fora da área de perda | Aplicar margens físicas que deixam mais da metade da tela vazia |

A revista é **premium digital com referência ao papel impresso**, não uma animação literal de livro de capa dura. Intensidade, blur, largura de vinco e sombras serão calibrados visualmente em imagens de referência e demonstração A/B. Nenhum valor é tratado como definitivo nesta etapa.

**Critério de aceite P01:** sem interação, o diretor reconhece a dupla como um mesmo exemplar de revista **aberto**; ao virar, o verso e a espessura fazem sentido; com capa isolada, não há uma segunda página fantasma. É um **gate humano**, além do teste de CSS/DOM.

## 4. S01 — Spread semântico: páginas 02–03, 04–05, 06–07

**Não confundir duas páginas visíveis com uma composição editorial de duas faces.**

- **Capa 01** aparece isolada; abrir revela a dupla **02 esquerda / 03 direita**; virar revela **04–05**, e assim sucessivamente. Contracapa isolada. A sequência respeita frente e verso da folha.
- A dupla pode ter **um único mapa/arte atravessando o encontro central** ou um texto distribuído nas duas faces. O sistema precisa conhecer a unidade `spread` e a relação com as faces; não duplicar a imagem panorâmica como dois assets independentes descoordenados.
- **Mapa fictício de cidade** é fixture visual adequada para o ensaio, **não** mapa factual de GTA. Fazer um recorte esquerdo e direito do mesmo asset, com posição e escala consistentes. Não imprimir marcador, texto essencial, legenda ou rota indispensável em cima do vinco.
- Em **Folhear**, página dupla permanece composição, sem que cada metade vire um cartão isolado; mostrar a face correta depois da virada física. Em **Contínua**, manter o mesmo conteúdo e crédito da panorâmica, com leitura e zoom adaptados, sem duplicação semântica.
- No desktop a panorâmica usa as duas faces; no celular retrato uma face é legível, com modo de inspeção panorâmica por zoom/pan quando necessário. No celular paisagem oferecer dupla sob escolha, com possibilidade de retorno à leitura normal sem perder âncora.

**Critério de aceite S01:** mapa atravessa a dupla com estrada e horizonte alinhados e dobra crível; rotação do aparelho ou troca de modo não altera conteúdo lógico, nem deixa metade da imagem perdida.

## 5. Sequência de prototipação a entregar (sem recomeçar a fábrica)

**Ensaio A — física de virar por clique**
- Mesmo leitor híbrido/identidade BACK da baseline. Confrontar motor próprio e **StPageFlip** já pesquisado na PR #46.
- Testar a virada de canto inferior e a ausência de captura persistente, em mouse e toque.
- Preservar modo Contínua e menu hambúrguer. Se o motor externo não carregar, informar **teste não executado**, sem simular êxito.

**Ensaio B — anatomia da revista e spread**
- A mesma capa isolada + dupla **02–03** com texto e **04–05** com mapa panorâmico; distinguir visualmente vinco, bordas e pilha de folhas.
- Demonstrar aberto, durante virada e após virada. Não criar painéis de laboratório permanentes.
- Fazer duas variações controladas de lombada/materialidade (sutil e mais física) **sem mudar a marca**; diretor escolhe o equilíbrio.

**Ensaio C — regressão e acessibilidade**
- Viewports mínimos: **390×844**, **844×390**, **768×1024**, **1024×768**, **1440×900** e **1920×1080**; fonte 100%/150%; Folhear/Contínua; `prefers-reduced-motion`; teclado e toque.
- Medir `getBoundingClientRect()` das faces versus viewport; evitar largura de folha artificialmente limitada e grandes margens exteriores.
- Verificar integridade do texto, legendas, âncoras, links, ordem de leitura, ausência de overflow/corte, desempenho e fallback sem animação.
- Capturas reais antes/depois; distinguir execução em emulador de navegador de validação em aparelho físico.

**Não declarar “aprovado” apenas porque não houve overflow.** Exigir: **gate funcional** (medição/navegação) + **gate de materialidade** (avaliação do diretor). Se a simulação de papel atrapalhar legibilidade/performance, reduzir efeitos sem sacrificar texto nem tela cheia.

## 6. Ligações com o trabalho anterior e entrega à engenharia

- [Handoff integral do Bloco 02 — 01/11/2026](https://github.com/Saaimingo/Revista_Gamer/blob/bloco03/diretriz-avaliar-motores-leitura-responsiva-2026-10-26/docs/visual/analises-fundador/HANDOFF-DIRECAO-BLOCO02-PARA-BLOCO03-INTERACOES-IMERSIVAS-2026-11-01.md) e [Issue #50](https://github.com/Saaimingo/Revista_Gamer/issues/50).
- [Laboratórios HTML originais recuperados e versionados na PR #46](https://github.com/Saaimingo/Revista_Gamer/tree/bloco03/diretriz-avaliar-motores-leitura-responsiva-2026-10-26/docs/visual/prototipos/labs-bloco02-2026-11-01), além dos experimentos do próprio Bloco 03 no histórico da conversa.
- [Diretriz de comparação de bibliotecas — Issue #47](https://github.com/Saaimingo/Revista_Gamer/issues/47) e [PR #46](https://github.com/Saaimingo/Revista_Gamer/pull/46).
- [Parecer corretivo visual/full-viewport de 29/10](ESPECIFICACAO-CORRETIVA-IDENTIDADE-LEITOR-BACK-2026-10-29.md).
- [Leitor v0.3 consolidado](prototipos/estrutura-vazia-v03-consolidada/README.md).

**Handoff ao Fundador/Codex somente após rodada visual:** entregar motor candidato, versão/licença, estados de ponteiro, contrato de frente/verso/spread, fallback, desempenho e checklist de testes. **Nenhum merge, deploy, publicação ou chamada de IA foi autorizado por este documento.**

**Resumo vinculante para o Bloco 03:** a direção aprovou **a experiência imersiva, o clique simples como acionamento e o conceito de dupla com aparência de papel**; **não aprovou a implementação atual do arraste preso, nem o vinco genérico, nem uma engine definitiva**. A próxima demonstração deverá provar a diferença.
