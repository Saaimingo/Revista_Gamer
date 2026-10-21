# Revista Gamer — Arquitetura da Fábrica Editorial: agentes, memória visual e composição inteligente

**Data:** 20/10/2026  
**Autoria:** Chat Fundador, consolidando direção expressa pelo diretor  
**Estado:** **DIRETRIZ DE ARQUITETURA RATIFICADA EM CONVERSA + CONTRATOS INICIAIS PROPOSTOS PARA PROVA OFFLINE**. Não significa implementação, aceite de UX, publicação ou licença de mídia.  
**Integrações:** Motor Editorial v0.2 na `main`; orquestrador CODEX-003 em PR #8, fluxo editorial CODEX-004 em PR #10; leitor visual v0.3 consolidado do Bloco 03; [Issue #15](https://github.com/Saaimingo/Revista_Gamer/issues/15) para união estética/funcional.

## 1. Esclarecimento do diretor: blocos temporários ≠ agentes permanentes

Os **Blocos 02 a 06 são chats/setores temporários de CONCEPÇÃO**: debatem, especificam, validam protótipos e registram conhecimento. **Não participam da operação automatizada** nem vão receber uma matéria em cada edição. Quando terminarem, suas entregas viram perfis, regras, componentes, dados e interfaces consumidos pelo Motor Editorial. Não projetar pipelines que chamem os chats ou usem sua memória como dependência em runtime.

**Não há obrigação de “um agente por bloco”.** Um agente é uma função de processamento sob orquestração; uma persona (Ranzinza, Gamer, Historiador) é uma identidade editorial carregada sob demanda por uma função redatora. Funções com saída determinística não precisam de LLM.

**Premissa da direção:** a inteligência de diagramação precisa conhecer a história da editoração, para adaptar **padrões** — não copiar páginas antigas — às expectativas digitais atuais. O acervo de revistas históricas é **memória de soluções editoriais** para o diagramador.

## 2. Situação de engenharia efetivamente verificada em 20/10

**Integrado à main:** Motor v0.2 com SQLite, fluxos simulados multipauta, controle de revisões/direitos e composição de edição em prévia; ainda não possui diagramador autônomo ou biblioteca histórica.

**Aguardando integração:** PR #8 contém a fila persistente, agendador inativo, dispatcher, executores, perfis versionados, lease/fencing/heartbeat e testes offline. PR #10 depende do PR #8 e traz pipeline editorial controlado com fonte, rascunho, checagem, revisão, correção e gate humano. Corrigir Issue #11 foi concluído tecnicamente com 70 testes offline reportados; **isso não implica merge de #8/#10**. Não construir módulo novo supondo que esses PRs já estão na `main`. A engenharia deve declarar sua branch-base, dependências e estratégia de integração incremental.

**Lacuna:** não existe ainda contrato operacional estruturado para o **plano semântico de matéria** → **inventário/licença de imagens** → **plano de composição** → **motor de páginas** → **validação**. É preciso estabelecer os pontos de encaixe agora, antes de acoplar novos executores.

## 3. Organograma funcional — agentes e sistemas de responsabilidade clara

| Papel operacional proposto | Entrada | Saída primária | Quem consome | IA necessária? |
|---|---|---|---|---|
| **Pesquisador/apurador** | pauta, fontes e critérios autorizados | afirmações, evidências, divergências e IDs de fontes | editor e checador | possível; consulta externa só com autorização |
| **Editor de pauta/estrutura** | apuração, prioridades, limites de edição | brief + seções ordenadas + profundidade + necessidades visuais (mapa, cronologia, comparativo, fotos etc.) | redator, mídias e diagramador | possível |
| **Redator com persona versionada** | brief, evidências, DNA de cronista aprovado | texto por seções e blocos estruturados, com atribuição | checador | possível; **persona não é agente separado por princípio** |
| **Checador/revisor** | texto, fontes e hashes da versão | parecer pass/revise/hold, correções apontadas; versão checada | orquestrador, editor, composição | possível + validadores locais |
| **Curadoria de mídias** | necessidades visuais e inventário de ativos | assets aprovados para a modalidade pretendida, créditos, restrições de corte/transformação | diagramador + gate de direitos | humano + automação determinística; IA auxiliar opcional |
| **Diagramador / planejador visual** | matéria revisada, finalidade de cada seção, assets elegíveis, biblioteca histórica, identidade da edição | **LayoutPlan versionado:** sequência de módulos, composição de página/dupla, hierarquia, uso de mídias, alternativas mobile | motor determinístico de composição | IA multimodal **opcional e sob demanda**, após prova offline |
| **Motor de layout/paginação** | LayoutPlan, blocos semânticos, capacidades de tela e leitor v0.3 | HTML e páginas/duplas responsivas + mapa de âncoras/folhas | verificador visual + preview | **programa determinístico**, não agente obrigatório |
| **Validador de composição** | HTML/render, conteúdo esperado, licenças, tamanhos de tela | PASS/FAIL e evidências; motivo de bloqueio e retrabalho | orquestrador e diretor | programa determinístico; inspeção visual pode ser auxiliar |
| **Direção humana** | prévia, parecer e documentação | aprovação/revisão editorial/visual e, separadamente, eventual autorização de publicação | orquestrador | pessoa, **nunca substituída por PASS de teste** |

O **orquestrador** é o gerente de tarefas. Agentes não devem comandar livremente uns aos outros: entregam artefatos, e o motor valida o contrato e despacha dependências. Não presumir que todo artigo passa linearmente por todos os trabalhadores: o grafo pode ter coleta/curadoria independentes, verificações bloqueantes e revisões iterativas limitadas.

## 4. Interfaces centrais a estabilizar antes de crescer

As descrições seguintes são **contratos de dados de v0**, não nomes de classes definitivas nem JSON Schema aprovado:

1. **`StoryPackage.v0`**: story_id/edition_id; revisão/hash; título/dek; cronista (profile_id/version/hash); seções ordenadas com `block_id`, tipo semântico (heading, paragraph, pullquote, table, figure_request, map_request, timeline, comparison etc.), texto, source_ids e prioridade/escopo; relação entre blocos; necessidades de mídia. Não transformar imagem escaneada em texto da revista.
2. **`MediaInventory.v0`**: `asset_id`, obra/titular, origem, hash, dimensões, modalidade de licença/uso, status verificado ou pendente, crédito, cortes/edições permitidos, relação com blocos. Asset sem autorização **não pode ir para preview publicável**; uma prévia interna pode usar slot neutro identificado, sem insinuar licença.
3. **`LayoutReference.v0`**: `reference_id`, fonte/publicação/ano/edição/página quando conhecidos, caminho **privado** ou URL sob acesso legítimo, hash, posição/orientação, tags de composição, finalidade editorial, o problema resolvido historicamente, pontos fortes, limitações, adaptação digital sugerida, nível de confiança de metadados, escopo de consulta e direitos. Ex.: `dupla-de-consoles`, `mapa-panoramico`, `reportagem-com-imagens-menores`, `poster-colecionavel`, `abertura-cinematografica`.
4. **`LayoutPlan.v0`**: identificadores de story/revisão; theme/template versionados; sequência de blocos; escolha de componentes; referências históricas consultadas e sua **justificativa funcional**, não cópia de arte; preferência de página simples ou dupla; `spread_id`/grupos inseparáveis (mapa, comparação, pôster); estratégia mobile/contínua; cobertura de texto; assets e créditos; slots de anúncios opcionais e separados. Um layout é **proposta revisável**, não conteúdo editorial novo.
5. **`CompositionValidation.v0`**: hash das entradas/saídas; checks de integralidade do texto/ordem/IDs, nenhuma mídia sem gate, sem overflow invisível, contraste/reflow nos cenários previstos, separação anúncio/editorial, figura+legenda e sumário/âncoras; PASS/FAIL/INCONCLUSIVE e motivo. PASS **não publica**.

**Contratos não negociáveis:** versões e hashes em cada handoff, entradas idempotentes, outputs substituíveis, erros claros, limite de ciclos, logs sem segredos/texto privado desnecessário, preservação do leitor v0.3. O executor nunca ganha permissão implícita de publicar só por produzir artefato válido.

## 5. Memória histórica do diagramador — banco de referências, NÃO biblioteca de cópia

O diretor pretende trazer mais exemplos selecionados de revistas de 1997, 2002/2003 e outras épocas/editoras. O corpus deve crescer **curado, pequeno e de alta qualidade** antes de se pensar em milhões de páginas ou indexação complexa.

Cada amostra precisa ter **duas camadas distintas**:

- **Referência visual histórica:** o documento/imagem **somente para análise privada, quando autorizado**. Guardar os scans em acervo local/privado com controle de acesso; **não subir automaticamente páginas integrais protegidas ao GitHub público**. O repositório pode manter metadados, hashes, taxonomia e apontadores não sensíveis; thumbnails/derivações somente se seu uso e exposição forem permitidos. Direitos de **estudar como composição** não dão direito de republicar arte, texto, mapa, marca ou página na revista.
- **Cartão de solução editorial:** anotar *problema que aquela página resolvia*, distribuição de texto/foto/mapa, quando usar, pontos fortes e limitações do papel, como adaptar digitalmente, e contraexemplos. Esta descrição é o principal índice pesquisável.

**Pipeline do acervo:** ingresso pelo diretor ou curadoria legítima → registro de proveniência/direitos/metadados → anotação funcional/taxonomia → indexação local → busca por intenção (`story.section`, `media.capabilities`, `desired_effect`) → recuperação de 3–6 referências pertinentes com justificativa → planejamento visual → layout + QA.

**Primeira implementação econômica:** arquivos de manifesto versionados + índice **SQLite local** com filtros/tags e pesquisa textual. Indexação semântica, embeddings, banco vetorial ou análise por modelo multimodal **somente se o catálogo e testes demonstrarem que a busca simples é insuficiente** e houver disponibilidade, orçamento e elegibilidade apropriados. Se não houver visão de arquivos no executor real, usar **descrições estruturadas** previamente analisadas; nunca fingir que o modelo viu a imagem.

**Amostras da conversa ainda não são arquivos hospedados automaticamente no processo.** O Bloco 03 poderá trabalhar suas regras estéticas; a curadoria prepara o acervo; os scans não se tornam automaticamente fontes de fatos sobre hardware/jogos. Diferenciar `historical_layout_reference` de `editorial_asset` e `commercial_asset`: tipos diferentes, permissões diferentes, **nenhuma promoção silenciosa de uso**.

## 6. Páginas duplas e leitura mobile sem perder o trabalho editorial

Quando a composição for uma **dupla intencional**, atribuir `spread_id` e `composition_mode: spanning` a um componente ou conjunto. Não confundir com duas faces vizinhas exibidas lado a lado.

- **Desktop:** páginas opostas coordenadas, capa e contracapa isoladas, face esquerda/direita sem desalinhamento. Composição projetada para duas faces, quando aplicável.
- **Mobile retrato:** aviso opcional e curto de que a dupla é melhor vista na horizontal, com escolha acessível e sem bloquear a leitura.
- **Mobile paisagem:** apresentar a dupla/panorâmica, com gesto de zoom e deslocamento quando necessário.
- **Rotação bloqueada/não suportada:** alternativa legível e íntegra (exibir panorama escalável/rolável e acesso ao conteúdo associado). Não depender de API capaz de forçar giro do dispositivo.
- **Contínua:** mesmo conteúdo, mapa/comparativo incorporado como componente expandível; não cortar metade de ilustração nem duplicar textos em dois percursos diferentes.

O motor precisa preservar conteúdo mesmo sob fonte 150%, espaços amplos, grande tabela/legenda e telas pequenas. Refluxo pode aumentar faces além da hipótese inicial de 20, sem mutilar a reportagem. Futuramente pode existir pôster desdobrável, mas isso **não** substitui o modelo de duas faces/verso.

## 7. Etapas de implementação propostas — não explodir custos/complexidade

**Fase 0, AGORA, OFFLINE:** verificar integração de PR #8/#10 e as dependências de branch; formalizar `StoryPackage`, `LayoutReference`, `LayoutPlan`, `CompositionValidation` como esquemas/fixtures locais, índice SQLite mínimo de referências e um **executor simulado de diagramador** ligado à interface do orquestrador. Ele não precisa “ser criativo” ainda; deve provar o caminho de ponta a ponta em tarefas locais, com referências e handoffs rastreáveis. Criar testes de contratos, transições, mudança de revisão (invalida plano anterior), referência ausente, mídia sem licença, spread/mobile/contínua, ausência de publicação. Não alterar fluxo real SIWC nem a UI editorial definitiva.
  
**Fase 1, depois de validar o contrato:** consumir componentes reais do Bloco 03 e o leitor v0.3; usar três fixtures curtas (reportagem com imagens pequenas, comparação em dupla, mapa panorâmico) e montar prévia HTML íntegra, mesmo que seleção de templates seja inicialmente determinística.
  
**Fase 2, após aceite humano e disponibilidade do modelo:** executor diagramador com análise das referências/descrições e plano estruturado; comparar sugestões contra baseline determinístico, custo e qualidade; não assumir acesso a tool hosted file search pelo SIWC. Revisão humana continua obrigatória.
  
**Fase 3, somente com autorização própria:** integração de acervo de mídia real com direitos, editorias/personas finais, desempenho em dispositivos e cadeia completa de edição; proibição de autopublicação mantida.

### Critérios de aceite da Fase 0

1. Teste local offline demonstra o encadeamento **matéria fictícia revisada → necessidades visuais → recuperação de referências → proposta de plano → validação → prévia interna/bloqueio**; entrada e saída tipadas/validadas.
2. Prova de que o **orquestrador continua gerente central** e perfis/versionamento não se perderam. A execução simulada pode ser em ramo próprio ou isolada de PR #8/#10, mas não deve duplicar um dispatcher paralelo.
3. Ponta a ponta com ao menos **três tipos de composição** (a) texto + duas imagens pequenas; (b) comparativo em spread; (c) mapa panorâmico em duas faces e alternativa mobile, tudo com **slots fictícios**, sem scan de revista ou arte oficial.
4. Plano rejeita `asset` sem permissão apropriada, fonte visual inexistente e alteração de texto sob o mesmo hash. Não aceita `LayoutPlan` de revisão não vigente.
5. Relatório distingue implementação de esquema, simulação de agente e execução com modelo; lista testes que rodaram, gastos zero, nenhuma chamada SIWC, nenhuma publicação, nenhum serviço externo.
6. O desenvolvimento não altera nem faz merge de PR #8, #10, #13, #14 ou #16; mantém Issue #15 de design independente e relevante.

## 8. Divisão de responsabilidades de desenvolvimento

- **Direção:** valida finalidade e experiência; fornece aos poucos páginas históricas curadas; autoriza usos e publicação, controla gastos.
- **Chat Fundador:** consolida contratos entre funções e prioridades da fábrica, revisa aderência ao projeto.
- **Bloco 03:** termina **gramática de composição visual**, temas, componentes, modos desktop/mobile, estados/limites e critérios de qualidade; não atuará no runtime.
- **Bloco 04:** especifica brief, estrutura jornalística da reportagem, profundidade e sinais de quando pedir mapa/cronologia/comparativo; não atuará no runtime.
- **Bloco 05:** orienta licença/proveniência de mídia e também delimita escopo de consulta ao acervo histórico, sem torná-lo publicável; não atuará no runtime.
- **Codex:** implementa motor, registro de papéis, adaptadores/contratos/testes, sem criar agentes permanentes a partir dos próprios chats e sem quebrar integração pendente.

**Resultado pretendido:** a máquina editorial terá acesso a uma **memória de composição**, não memória fictícia do ChatGPT; terá **especialistas operacionais identificados por papel**, não blocos vivos; e poderá adaptar acertos de revistas antigas às demandas digitais atuais, sem copiar sua propriedade intelectual. **O diretor aprova a revista; a IA e o código a preparam.**
