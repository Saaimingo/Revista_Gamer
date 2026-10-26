# ENG-CODEX-012 — Arquitetura-mestra funcional da Revista Back / Revista Gamer
**Direção, 26/10/2026. Natureza:** ordem técnica de revisão integral de contratos e implantação incremental; NÃO representa sistema já implementado ou validado. **Estado:** diretriz da Direção para engenharia, sujeita a preservação de decisões prévias e validação por evidência real.

## 0. Ordem, escopo e critério de honestidade

Este documento descreve COMO a fábrica editorial deve operar quando concluída. O Codex deve executar uma revisão arquitetural de ponta a ponta, confrontar cada regra com o código efetivo, apontar lacunas, corrigir as lacunas em unidades recuperáveis e demonstrar funcionamento real. Não tratar mera existência de um método, teste mockado, fixture ou contrato documentado como comprovação de produção.

A missão ENG-CODEX-011 (Issue #41) produziu **execução PARCIAL** em 26/10: 7 chamadas reais SIWC, 109.336 tokens, 142.047 ms reportados, triagem, investigador, editor, Carranca, checagem inicial e revisões arquivadas. O modelo escolheu Proton 11.0-2e e Carranca. Foram consumidas 4/4 consultas externas autorizadas; a última recebeu HTTP 200 com 2.120 bytes e SHA-256 mas o Radar não produziu alegações/documentos, resultando em pacote blocked. Não houve prova do retorno de pesquisa ao redator, checagem final, revisão editorial final, integração de imagem ou prévia conferida no navegador. O conteúdo bruto dessa resposta HTTP e a causa exata não foram preservados. Jamais narrar essa missão como E2E concluído. Não inventar o resultado ausente.

**Fronteira de autorização:** o diretor deseja que engenharia avance até tornar a fábrica funcional, inclusive usando a franquia restante Plus/SIWC para validação relevante; isso NÃO é autorização para APIs monetizadas, dados privados, alteração de OAuth/contas, expansão irrestrita de fontes, publicação, redes sociais ou deploy. A verba pública explícita ENG-011 segue **4/4 esgotada**. Qualquer nova pesquisa externa exige missão/política versionada adicional autorizada; implementação offline, inspeção local dos logs, testes sobre artefatos já persistidos e prévia local são permitidos. Não tentar reclassificar chamadas antigas como gratuitas para burlá-las.

**Tese arquitetural:** IA decide, interpreta, investiga, escreve e revisa; código controla segurança, proveniência, identidade, filas, regras determinísticas, orçamentos, idempotência, persistência e renderização. O Motor NÃO obriga agentes a formular linguagem humana como identificador técnico. Uma matéria pode aguardar evidência e outra seguir adiante. Uma execução externa incerta NUNCA é repetida às cegas. Bloqueios legais, de direitos, privacidade, segurança e publicação exigem retenção e não são “contornáveis” por criatividade.

## 1. Hierarquia da verdade, baseline e auditoria inicial

1. Ler AGENTS.md, README.md, docs/governanca/BIBLIA-DO-PROJETO.md, DECISOES.md, MAPA-SETORES.md, STATUS-GERAL.md, docs/operacao/PROTOCOLO-HANDOFF.md, CONTRATO-ENTREGAS.md; ler os materiais reais das pastas de personagens, redação, visual, acervo, comercial e engenharia. São documentos com datas e níveis de aprovação diferentes: nenhuma descrição antiga de personagens ou protótipo substitui decisão posterior. Registrar divergências, sem apagar história.
2. Analisar o estado real do código na branch acumulada 011, com base ENG-010; reconciliar as melhorias de ENG-009 (preservação de originais e métricas) SEM mesclar PRs antigas ou descartar trabalho. Ler explicitamente motor_editorial/agent_roles.json, agent_contracts.py, agent_siwc.py, agent_workflow.py, orchestration.py, research_mediation.py, research_service.py, radar_connectors.py, radar_incremental.py, radar_triage.py, radar_store.py, editorial.py, factory.py, eng_codex_011.py, layout/ e respectivos testes.
3. Produzir MATRIZ DE RASTREABILIDADE: requisito deste documento | código atual | versão de contrato | implementado? | teste unitário? | teste real? | evidência | lacuna | ação. A ausência de teste real nunca recebe “validado”.
4. Congelar hashes/versões dos DNAs de Beto Cartucho, Arlindo Carranca e Nina Prisma antes de qualquer teste editorial; preservar originais dos ensaios 009/011 em armazenamento privado. Proibir que correções técnicas editem silenciosamente DNA ou texto bruto.
5. Diferenciar FATOS OBSERVADOS (IDs e artefatos), HIPÓTESES DIAGNÓSTICAS (com grau de confiança) e REQUISITOS NOVOS (a implementar). Não confundir proposta de arquitetura com conclusão.
6. A documentação de governança antiga pode estar desatualizada: preparar PR/parecer de reconciliação, não reescrever decisões aprovadas unilateralmente.

## 2. Arquitetura e fronteiras de responsabilidade

Camadas obrigatórias, que podem viver num monólito modular local inicialmente:
- **Configuração/Política:** autorizações versionadas, fontes, papéis, orçamentos, privacidade, direitos, periodicidade e gates; humanos aprovam política, máquinas executam dentro dela.
- **Radar/Coleta:** conectores HTTPS/RSS/APIs públicas autorizadas; obtenção/identificação de conteúdo, metadados, validação, histórico e snapshot durável; não escolher jornalista.
- **Índice/Conhecimento:** RadarStore único com entidades, documentos, versões, fontes, links, datas, direitos, alegações, controvérsias, evidências e status epistêmico.
- **Descoberta/Triagem:** montagem de eventos/grupos deduplicados, classificação agentica e carteira editorial, preservando “monitoramento”.
- **Apuração:** investigador e pesquisa por demanda, com apoio de ResearchService; entregar evidências verificáveis e perguntas não resolvidas, nunca uma conclusão inventada.
- **Direção editorial operacional:** agente editor decide pauta, ângulo, prioridade, tipo de texto, persona e necessidades visuais; supervisiona alternativas e conflitos; NÃO substitui direção humana na publicação.
- **Redação:** agente persona_writer recebe brief, DNA íntegro e evidências; escreve texto integral e solicita pesquisa adicional quando necessário.
- **Checagem e revisão:** fact_checker verifica alegações/atribuições contra fonte e versão; editorial_reviewer examina clareza, tom, leitura e continuidade; ciclo corrigível.
- **Acervo e direitos:** inventário editorial separado de material publicitário; verificação de autorização por ativo, versão e canal; opção segura sem imagem não equivale a comprovação de versão visual com imagem.
- **Composição e apresentação:** layout_planner quando necessário; contratos, renderização e validações determinísticas; prévia servida por HTTP loopback, aberta e observada realmente; leitores finais responsivos/acessíveis.
- **Operação/Observabilidade:** AgentQueue + TaskDispatcher + ledger SQLite existentes, controladores de leases/fencing, idempotência, snapshots, métricas SIWC e fluxo de exceções; nunca criar segundo orquestrador escondido.
- **Publicação/comercial:** publicação pública, redes, afiliados e patrocínios são sistemas/autorizações separados; devem consumir SOMENTE artefatos e permissões aprovados.

**Fluxo-alvo:** política → conector público → snapshot Radar → lote deduplicado → triage_analyst → carteira → evidence_investigator → assignment_editor → persona_writer → [ResearchRequest → Motor → ResearchService/Radar → ResearchPacket → mesmo papel/matéria] → texto integral → fact_checker → [revisão do redator quando necessária] → editorial_reviewer → [correção e nova checagem se necessário] → media_researcher/direitos → layout_planner → composição/render → verificação REAL no browser → pendente da Direção → publicação específica autorizada. Subfluxos e estados são persistidos em cada transição.

**Invariante transversal:** toda entidade relevante pertence a um run, story, revision e fonte identificáveis; não deslocar resultado para outra matéria e não promover evidência velha a nova revisão sem rechecagem.

## 3. Contrato-base de dados, auditoria e estados

O Codex deve preservar compatibilidade com AgentTaskEnvelope, AgentResultEnvelope, ResearchRequest v1.1, ResearchPacket, perfis JSON versionados, StoryPackage/StoryDraft e contratos de layout existentes. Quando faltar campo, introduzir migração/versão explícita e adaptador retrocompatível; nunca mudar esquema persistido silenciosamente.

### Identidades e hashes
- IDs técnicos: gerados pelo Motor de forma estável e segura, sem depender da escrita literal do agente; usar namespaces tipados e digest quando necessário. Ex.: frase “O patch corrigiu problemas de vídeo?” é TEXTO; claim_id canônico é ID estável; manter rótulo original e tabela de correspondência. Nenhuma regra “sem espaços” se aplica a títulos, frases, perguntas, citações ou descrições.
- Preservar **bytes exatos** da entrada original e SHA-256; para comparar estruturas de JSON, usar serialização canônica versionada (tipos JSON, ordem estável de chaves, política documentada de Unicode/números), sem confundir tupla/lista em Python com mudança semântica. Hash de bytes de DNA não se calcula sobre texto alterado por strip, trim ou normalização.
- Distinguir source_id, source_snapshot_id, radar event_id, candidate item_id, document_id, claim_id, edition_id, story_id, story_revision_id, task_id, request_id e response/receipt IDs. Definir resolução tipada e relacionamento explícito. Nunca fazer comparação cega event_id == item_id.
- Cada tarefa persistida contém perfil/version/hash, persona/version/hash quando aplicável, inputs/digest, origem, dependências, escopos concedidos, orçamentos, idempotency key, estado, timestamps, tentativas, artifacts/response hashes, desfecho e recovery lineage.

### Estado da pauta e da tarefa (adaptar ao modelo existente)
- Pauta: discovered → triage_pending → monitored | eligible → dossier_pending → assignment_pending → assigned → drafting → researching | fact_checking | revising → editorial_review → media_rights → layout_preview → awaiting_human_approval → approved_for_specific_action → published [somente futuro, autorização distinta].
- Desfechos não felizes: no_change, not_found, partial, needs_research, needs_editorial_decision, hold_source, hold_rights, hold_security, blocked_contract, blocked_external, uncertain_external, rejected; diferentes e auditáveis. Um estado hold NÃO significa falha geral do Motor.
- Tarefa: queued, leased/running, succeeded, blocked, failed-retryable, uncertain, exhausted, cancelled nos termos reais do AgentQueue. Não inventar transição fora do ledger; se uma transição nova for necessária, versionar migração e testar.
- Sempre gravar evento de início e fechamento com stage, papel, status, reason_code tipado, evidências, ação permitida, próxima ação e orçamento. Anotar o último ponto durável antes de executar efeito externo.

### Fronteira externo × interno
- **Antes** de invocar HTTP, SIWC ou geração de imagem, reservar orçamento, criar registro durável da intenção e idempotency key; no término preservar resposta bruta permitida, recibo, metadados de status, hash e vínculo. Quando legalmente proibido reter o corpo de fonte terceira, armazenar somente metadados permitidos e os trechos mínimos autorizados, mas então declarar impossibilidade de reconstruir a resposta e considerar estratégia de observabilidade previamente aprovada.
- Nunca fazer retry automático quando a chamada externa pode ter acontecido e não há confirmação. Resolver via reconciliação segura (consulta de status/recibo quando oferecida), cache/artefato existente ou hold; chamar usuário apenas em exceção real de autorização.
- Estado succeeded do agente não se perde por falha posterior de parsing ou roteamento. Recuperação parte do último resultado imutável, não redespacha trabalho cognitivo.

## 4. Bloco Radar: cobertura do mundo aberto, fontes, observações

### 4.1 Fontes e inventário
O GitHub é UM conector e serve muito bem a releases de software/mods/projetos. Não representa o universo jornalístico da revista. O catálogo de fontes deve comportar, sob política explícita:
1. Estúdios e fabricantes: press rooms, feeds oficiais, release notes, sites do fabricante, documentos técnicos.
2. Sites independentes de games/hardware: reportagens, reviews, metodologias e testes independentes com atribuição e links.
3. Comunidades/fóruns: relatos de jogadores, GitHub Issues, Reddit e fóruns oficiais ou especializados, diferenciados de fatos oficiais.
4. Criadores e projetos de mods: repositórios oficiais, changelogs, licença, lista de versões e relatos de compatibilidade; nunca executar binários/mods como prova.
5. Plataformas/distribuição: anúncios oficiais, atualizações, notas de versão, documentação pública e dados de compatibilidade.
6. Arquivos/história: fontes primárias documentais e material de acervo autorizado, com data e contexto.
7. Fontes futuras: conectores adicionais aprovados e contratos versionados; host/rota nunca derivado livremente de texto do modelo.

Cada SourceProfile deve conter titular, nome, canal, tipo (oficial/independente/comunidade/replicador), URL raiz canônica, hosts exatos autorizados, caminhos e operações permitidas, condições de API/RSS/robots/termos, evidência e data da verificação, autenticado? (padrão não), restrições de reuso, língua, quotas host/dia e missão, tamanho por resposta, timeout, backoff, retry, redirecionamentos, status de direitos (separado de direito de leitura), data da última coleta, provedor/adaptador e versão. Novo host/conta/escopo não é habilitado por iniciativa do modelo.

### 4.2 Coleta e ingestão
- Job inicial define janela temporal, assuntos prioritários, perfil e política; valida allowlist antes de abrir socket; HTTPS, DNS público, pinning, proteção SSRF/redirect, sem credenciais, respeito aos termos/rate limit. Duplicatas 304/ETag não geram pauta nova.
- Capturar separadamente transport_status/HTTP status/parse_status/ingest_status/rights_status. HTTP 200 **não** equivale a conteúdo relevante, extraído ou auditável.
- Para cada resposta: registrar bytes, digest, tamanho, content-type, charset, tempo, URL requisitada/URL final, request ID, origem, número de candidatos extraídos, número rejeitado e motivo tipado. Guardar o corpo bruto apenas conforme termos/direitos e segurança do conteúdo. Requer mecanismo de redaction para segredos/PII.
- Parser por tipo: RSS/Atom, JSON oficial com esquema reconhecido, HTML público permitido. Parser desconhecido = parser_unsupported e candidato não validado; nunca marcar sucesso sem documento.
- Extração de URL humana/original e URL técnica/API; distinguir release API de link na página humana. Documentos e snapshots obtêm ID estável. Eventos só nascem de novo conteúdo/mudança material e devem referenciar documento persistido.
- Dedupe de URLs/canonical/ETag/digests, redes de republicação, notícia reescrita, atualização do mesmo anúncio e fontes realmente independentes. Um portal republicador não se transforma em nova origem.
- Se zero evidência / fonte parcial / limite de conexão: registrar reason_code e marcar apenas fonte/lote; demais fontes prosseguem. Não repetir resposta vazia em loop e não inferir conteúdo pela URL.
- O Motor deve permitir descoberta periódica planejada e pesquisa sob demanda, sem usar dois índices concorrentes. Agendas reais desativadas até autorização específica de operação contínua.

### 4.3 Triagem
Entrada do triage_analyst: DiscoveryBatch com candidatos, event_ids, item_ids, documentos, fontes, data, categoria, duplicações, confiabilidade e recortes curtos permitidos; nenhuma escolha de pauta pré-escrita pelo programador.
Saída: classificação de impacto, novidade, relevância gamer, categoria, sugestão de editoria, prioridade, risco de rumor, necessidade de confirmação, linha principal/reserva/monitoramento/descartar com motivo, evidence_refs originais. A IA não concede permissão de fonte.
Motor resolve event_id/document_id/item_id por índice de ligações tipado, validando a pertinência ao lote. A classificação “monitoramento” é decisão real, não descarte automático; editor pode receber item monitorado e, com fontes e ângulo sustentado, escolher pauta; nunca promover tudo indiscriminadamente.
Sem candidatos elegíveis: fechar lote com “no_story_yet”; registrar fontes, permitir próximo lote no agendamento autorizado; não inventar pauta de fixture para forçar sucesso.

### 4.4 Carteira
Manter carteira priorizada dinâmica, com reservas, atualidade, estado de apuração, categoria, candidatos duplicados, concorrência e histórico. O desenho antigo propõe 10 principais + 10 reservas; tratar capacidade como configuração e não obrigação de criar vinte matérias a cada execução. Remover/rebaixar quando fato expira ou prova falha; não apagar trilha.

## 5. Investigação / EvidenceDossier

Entrada de evidence_investigator: uma ou várias candidatas rastreáveis, snapshots, alegações, URLs de origem e limites de acesso/escopo. Apurar como agente REAL: diferenciar anúncio, nota oficial, publicação de terceiros, opinião, medição independente e relato de comunidade; identificar contradições e versões. Não inventar teste próprio, FPS, desempenho, palavras de entrevista ou consenso.

Saída persistida EvidenceDossier: evento, título, contexto, datas, resumo executivo de bastidor, alegações tipadas, evidence_id por afirmação, publisher, origem (primeira e intermediária), extrato curto autorizado, condições de teste/versões, relatórios divergentes, rumores identificados, perguntas em aberto, prioridade factual, índice de suficiência por afirmação e sugestões de próximas fontes. Se fonte não foi efetivamente lida, identificá-la como candidato, não como evidência consultada.

ClaimLedger deve separar presença da referência e confiança na conclusão. Ex.: “o autor publicou atualização” pode ser fato por fonte oficial; “corrigiu todos os travamentos” exige demonstração ou atribuição específica. Rumor não vira confirmado quando repetido por muitas cópias. A proveniência pertence a documento e versão.

Erro no envelope após resposta válida do agente deve acionar normalização/recuperação **determinística** preservando bruto, sem gastar nova chamada. Frase legível de claim_id recebe ID interno seguro e tabela de origem, não descarte completo da investigação.

## 6. Editor operacional / Assignments

Entrada do assignment_editor: candidatos elegíveis e monitorados rastreáveis, EvidenceDossiers, carteira, prioridade temporal e gêneros aceitos. Saída é uma **decisão real do agente**: candidate_item_id, pauta e ângulo, tema, gênero/formatos (nota, reportagem, comparação, entrevista documental, guia, série, detonado), justificativa, persona escolhida, urgência, dimensão de pesquisa, questões centrais, lacunas, hipóteses que NÃO devem ser vendidas como fatos, módulos de leitura e requisitos visuais ainda sujeitos a direitos.

Seleção: somente candidate_id incluído em dossiê; persona existe e hash é aprovado. Auditoria persiste por que escolheu. Se nenhum assunto merecer matéria, editor pode aprovar monitoramento ou pedir investigação adicional, sem inventar candidato. Se fonte necessária faltar, pode escolher ÂNGULO MAIS ESTREITO que já seja verificável, desde que o recorte continue relevante e seja explicitamente aprovado pelo processo editorial agentico. Nunca transformar “não encontrei informação” em um artigo inteiro sobre falta de informação só para fechar pipeline.

O editor tem autoridade para retrabalhar a pauta ou trocar jornalista antes da primeira redação, não para forçar uma alteração de DNA. Mudanças após redação criam nova revisão/atribuição vinculada, não sobrescrevem o original.

## 7. Bloco 02: jornalistas e identidades (separados de papéis operacionais)

**Arlindo Carranca / Ranzinza** — cobertura de hardware, infraestrutura tecnológica dos games, GPUs/CPUs, engines, drivers, compatibilidade e IA associada a jogos. Rigor de analista, ironia comedida, exigência de evidências e comparações, mérito quando existe; não alegar testes físicos feitos pela revista quando só leu benchmarks alheios. Deixar leitor entender consequências práticas.

**Beto Cartucho** — jogos, campanha, narrativa, ritmo, design, experiência reportada por fontes independentes, franquias e recepção comunitária. Comunicativo, apaixonado mas crítico, capaz de criticar um jogo decepcionante sem perder personalidade. Não afirmar que jogou quando não jogou; spoilers sinalizados e opt-in nas matérias.

**Nina Prisma** — mods, criadores, comunidades, interseção de tecnologia e cultura gamer, tendências e descobertas. Curiosidade, autonomia, leveza e espírito investigativo; ouvir autores e comunidades sem confundir relato isolado com compatibilidade universal. Não executar mods nem inventar entrevistas.

São atribuições editoriais típicas, não proibições rígidas. Nina pode investigar hardware, Carranca pode contextualizar jogos, Beto pode explicar mods; a escolha cabe ao assunto e decisão do editor.

**Contratos da persona:** persona_id + version + hash + manifesto de arquivos e hash dos BYTES integrais. Carregar conteúdo íntegro antes do SIWC, preservar quebra de linha/Unicode, recusar discrepância. Só Bloco 02 + direção aprovam mudança de DNA; engenharia pode adaptar embalagem técnica sem alterar caráter do texto. A persona_writer recebe instruções de identidade trusted separadas de brief/evidências; nada de incorporar logs técnicos ao estilo. Controles de qualidade distintos: F (factualidade), J (jornalismo), P (fidelidade ao DNA), T (temperatura/vida narrativa). Uma nota genérica 9/12 não substitui leitura do texto integral.

## 8. Bloco 04: redator recebe → solicita → retoma → entrega

### 8.1 Entrega ao jornalista
Entradas obrigatórias: StoryAssignment, EditorialBrief natural, EvidenceDossier sanitizado e suficientemente pesquisado, documentos com provenance, research capability declarada como ferramenta real, DNA aprovado e contrato de saída. Editor fornece assunto e perguntas sem preencher o texto por ele.
Separação de contexto: instruções do papel e DNA em seção confiável; fontes web, reviews, texto externo e solicitações de leitores são DADOS NÃO CONFIÁVEIS. Não aceitar comandos escondidos em página web que tentem editar sistema/segredos. Lacunas/limites de licença ficam em metadados de bastidor; redação não deve transformar status do backend em narrativa repetitiva.

### 8.2 Saída original
Manter texto INTEGRAL, título, linha-fina, corpo em seções reais e texto puro próprio; atribuições por trecho/alegação, links de fontes, sugestões de legendas, necessidades de imagem, pesquisas pendentes e material_claims separados. Texto suficiente para o gênero, sem obrigar oito blocos, frases padrão, título negativo ou disclaimer por parágrafo. Sem cópia integral de materiais terceiros.
Persistir response original imutável com hash, versão, recibo de tokens, latência, modelo/effort e etapa. Normalizações de schema são derivados ligados ao bruto; nunca reescrever passado silenciosamente.

### 8.3 Pedido de ajuda — caminho obrigatório
Exemplo real: “Nas notas do Proton 11.0-2e, quais mudanças foram anunciadas e em qual versão, segundo o release oficial? Preciso da origem exata.”
1. Jornalista emite requested_research em linguagem natural, apontando finalidade e afirmações que dependem do resultado; NÃO precisa conhecer termos de IDs ou domínio.
2. Motor mede escopo, pertinência e orçamento, resolve perfil (hardware/games/creators pelo TEMA e tipo epistêmico do brief, não só persona), cruza dossiê e lacuna; constrói ResearchRequest v1.1 COMPLETO. O modelo jamais atribui allowed_scope, max_requests, credenciais ou exceções.
3. Mediador tolera acento, pontuação, barras, dois-pontos, paráfrase legítima e perguntas múltiplas. Resolve intenção por entidades e contexto confiável, não igualdade exata de question/purpose; se ambígua, faz hold apenas da pesquisa, preserva pedido e oferece esclarecimento editorial automático dentro do orçamento.
4. Motor enfileira pedido idempotente filho do task_id, story_id, story_revision_id, persona_id, pergunta, versão da política e content-hash de contexto. ResearchService consulta índice/cache primeiro; se necessário, adapter externo autorizado com orçamento.
5. Resultado é ResearchPacket versionado e persistido com status encontrado/parcial/não encontrado/bloqueado, documentos/claims verificáveis, source_lineage, trechos curtos, lacunas e restrições. HTTP 200 sozinho jamais satisfaz o pedido. Separar “fonte recebida” de “claim validado”.
6. Router devolve packet à **mesma história, revisão e papel solicitante**, com novos dados, delta/evidências/limites e solicitação original. Não chamar outro jornalista inadvertidamente nem iniciar matéria do zero. A continuação é uma nova tarefa vinculada ao original e consome chamada real apenas se o packet trouxer valor novo validado.
7. O jornalista integra os achados, ajusta afirmações/citações e produz uma revisão integral nova; sem inventar resultados. Hash e histórico preservam original e revisão.
8. Se faltar evidência: voltar ao editor, que pode encontrar fonte alternativa dentro da política, estreitar pauta, retirar afirmação insegura, marcar monitoramento ou segurar a matéria; o Motor **não** pode gerar continuação vazia e desperdiçar SIWC. Nunca encaminhar packet blocked/vazio como se pesquisado.

### 8.4 Limites e exceções
No máximo rodadas versionadas e orçadas por assunto, com contagem no ledger. Sem loop infinito editor↔jornalista↔pesquisa. Exaurida pesquisa e não existindo recorte verificável, matéria fica hold, outras pautas continuam. Diretor é acionado apenas para exceção de custo, direito, fonte fora da política, mudança editorial de impacto ou publicação, não a cada pergunta normal.

## 9. Checagem factual, revisão e ciclo editorial

**fact_checker:** recebe versão IMUTÁVEL do StoryDraft com story_revision_id + SHA, dossiê e fontes acessíveis. Para cada afirmação relevante: trecho, classe epistêmica, evidência específica lida, origem, versão, contexto, mérito, divergência, risco de generalização, risco de citação enganosa. Resultado FactCheckVerdict: pass/needs_correction/hold, findings acionáveis; nunca editar o texto direto. Sem fonte suficiente, não aprovar afirmação. Se versão mudar, parecer anterior fica stale e exige checagem relevante nova.

**persona_writer correção:** recebe somente achados objetivos, mesmas fontes e DNA; devolve versão integral vN+1, change log interno, novos hashes e eventual pesquisa justificável. Não substituir personalidade por compliance. Nunca sobrescrever original/revisão anterior. Não chamar LLM para mera mudança de ID, serialização ou caminho.

**editorial_reviewer:** recebe texto vigente e fact-check correspondente ao MESMO hash, brief e DNA; avalia gancho, fluidez, escaneabilidade, utilidade, voz, neutralidade, clareza, diversidade de fontes, título, responsabilidade e adequação visual. Se pede mudança factual, volta ao fact_checker/investigador conforme natureza; se pede estilo, volta ao jornalista e exige nova revisão. Só produz recomendação agentica, não carimbo de aprovação humana.

Ciclos limitados, com critérios por severidade: correção técnica determinística não reabre autorias; mudança semântica reabre checagem; mudança só visual revalida layout/legibilidade; mudança de evidência/release pede validação editorial. Revisão 02/03 podem existir legitimamente, mas precisam ter motivo e encadeamento claros; não gastar franquia reescrevendo cada saída por pequeno erro de schema.

**Decisão com lacuna:** fato central sem prova → hold da matéria; fato secundário sem prova → remover ou atribuir e reavaliar; fonte divergente → apresentar divergência com atribuição; material só de fonte única → declarar fonte única quando relevante; rumor → indicar rumor; comentário comunitário → amostra não representativa. Nunca mentir para cumprir cronograma.

## 10. Bloco 05: mídia, direitos e versões

Inventário editorial por titular → obra → ativo; guardar asset_id, origem/URL, licença/termos, evidência, data, usos permitidos (web, PDF, redes, derivados, animação), restrições, crédito, texto alternativo, dimensões, hash, status e revisão da autorização. Papel media_researcher propõe ativos **e alternativas** mas não concede direitos. Validador de direitos é determinístico/humano conforme política.
Para matéria real, preferir screenshot/press kit/documento com uso permitido e origem validada; opção de imagem original por ferramenta licenciada autorizada, corretamente rotulada quando ilustrativa. Não simular screenshot real, pessoa entrevistada ou teste de hardware.
Se direitos da imagem falham, encontrar alternativa autorizada; caso não exista, matéria pode seguir a revisão textual mas a **homologação de experiência com imagem** permanece pendente. Não declarar HTML final visualmente concluído usando placeholder de fixture.
Separação forte: acervo jornalístico jamais alimenta publicidade; o Bloco 06 só usa arquivos publicitários próprios autorizados, e os metadados de afiliados não alteram conclusões editoriais.

## 11. Bloco 03: layout, navegação, preview e observação REAL

LayoutPlan mapeia seções do texto vigente, posição/atribuição das imagens, capa/chamadas, grid, versão/resolução e modos mobile/desktop. Layout pode ser planejado por agente (layout_planner) mas composição, schema, links, HTML/CSS, contrastes, performance, permissões e hashing devem ser checados deterministicamente.

A revista é **revista digital gratuita**, não feed genérico: capa, miolo, contracapa, frente/verso coerentes quando modo folhear ativado; navegação direta sem animação também; desktop páginas lado a lado quando apropriado e mobile uma página legível; fontes acessíveis, texto selecionável, zoom, sumário, alt text, foco teclado, reduced motion; imagens comprimidas sem degradação editorial e carregamento progressivo. Leitura por voz opcional e sem obrigar mídia pesada.
Identidade visual central consistente (grafite/branco/vermelho/roxo e atmosfera cinematográfica premium/tecnológica conforme decisões recentes do Bloco 03); tema por edição pode variar. Não engessar proporções por porcentagens fixas sem validar legibilidade.

**Prova de navegador exigida:** renderizar versão real em diretório privado, criar servidor apenas em 127.0.0.1:porta efêmera, fornecer URL exata, abrir via navegador permitido, verificar carregamento efetivo de TEXTO, IMAGEM, fontes, links, rolagem/paginação, acessibilidade e viewport mobile/desktop. Capturar screenshot/relatório visual datado com revisão+hash e comprovar o que foi observado. Teste de bytes/HTML existe, mas não substitui inspeção em tela. Se file:// bloqueado, usar HTTP loopback legítimo; se navegador não acessível, marcar NOT_VISUALLY_VALIDATED. O diretor também deve conseguir abrir a prévia local com instruções curtas; não pressupor que caminho privado C:/ vira URL remota.

O renderer rejeita texto ou mídia de revisão obsoleta. Atualizar qualquer claim, imagem ou layout invalida aceite afetado e gera nova prévia, preservando a anterior. Prévia interna da revisão não aprovada pode abrir com marca discreta “rascunho interno — sem aprovação editorial”, sem usá-la como publicação real.

## 12. Bloco 06: publicação, distribuição, monetização e redes

Publicação pública é ação separada de “preview aprovado”: requer uma versão final específica, direitos confirmados por canal, autorização explícita humana, revisão atual válida, imagem e atribuições, domínio/infra protegidos, política de segurança, textos sobre transparência de IA e reversão de publicação. Um flag simulado ou uma fixture não pode autorizar publish.
Instagram/Facebook e outras redes são canais de divulgação, não substitutos da revista; integração futura com contas deve ter conexão autorizada, limites de plataforma, moderação, rascunho, agendamento e log. Não vincular credenciais pessoais indevidamente nem postar sem autorização. Peças comerciais, patrocínio e afiliados recebem indicação visível e contratos/direitos próprios. A seleção e a conclusão jornalística jamais dependem de anunciante/afiliado.

## 13. Operação diária, múltiplas pautas, custo e autonomia

- Funcionamento pretendido 24/7 quando infraestrutura e política forem aprovadas; no protótipo atual tudo é local, sem VPS necessária. Não iniciar schedules produtivos sem autorização específica.
- Janelas do Radar são configuráveis por assunto/domínio e com intervalos responsáveis; sem consultas a cada minuto, sem repetição quando nada mudou. Agendamento periódico e pesquisas pontuais usam o MESMO RadarStore, deduplicação e ledger.
- Múltiplas histórias independentes progridem em paralelo CONFORME quotas e leases; uma matéria em hold não congela edição inteira. Carteira e edition_id agrupam versões aprováveis; editor pode substituir matéria bloqueada por reserva com trilha.
- Orçamento cumulativo de SIWC por missão, papel, story, edição e dia; distinguir tokens de entrada/saída/raciocínio/total, duração, tentativas, cache, status, chamada reconhecidamente concluída e custo monetário real se aplicável. **Nunca inferir o percentual de franquia Plus a partir dos tokens.** Direção informou 76% no início da 011; gasto real atual não mensurado.
- Não fazer sete chamadas só para provar que sete papéis existem: chamar cada papel quando sua decisão independente agrega valor; funções determinísticas não consomem modelo; chamadas repetidas apenas quando nova evidência/alteração editorial material e resposta anterior durável foi consumida. Orçamentos devem permitir piloto real significativo sem transformar custo em API paga.
- Modelo indisponível/quota encerrada: estacionar fila duravelmente, mostrar estado, permitir retomada após acesso autorizado; não trocar de provedor, modelo, conta, OAuth ou método de autenticação sem configuração previamente aprovada. Fallback técnico só por política explícita, com perfil e rastreabilidade.
- Dashboard local deve apresentar por matéria: fonte, fase, agente designado, tarefas concluídas/bloqueadas, última evidência, falta necessária, orçamento gasto/restante, qual ação automática ainda é possível e qual gate humano aguarda. Não exigir que o diretor leia SQL/JSON para saber se a revista está avançando.
- Backup/restore do SQLite e arquivos privados; schema migration prévia com backup e rollback testados; indisponibilidade de navegador ou GPU não apaga artigo já produzido. Falhas de energia/reinício não podem perder decisões concluídas.

## 14. Critérios obrigatórios de implementação

1. Para cada papel e fronteira de contrato: schema versionado, produtor, consumidor, dados permitidos, invariantes, tipos, validação, erro tipado, política de retomada, exemplo de sucesso e pelo menos um caso negativo.
2. Para cada chamada externa: política de fonte, registro durável antes/depois, orçamento, request/response hash quando permitido, sem redespacho automático incerto.
3. Para cada decisão agentica: prompt/profile hash, source snapshots reais, modelo, resultado BRUTO/estruturado, motivo, versão da matéria, evidência, custo e downstream real.
4. Para cada falha: distinguir erro técnico recuperável de bloqueio epistêmico, direitos, segurança, orçamento ou humano; não criar ciclo automático sem limite.
5. Para cada matéria: auditar sequência de versões; checagem e revisão referenciam hash correto; imagem tem direito; preview visível corresponde à versão.
6. Para teste de ponta a ponta: escolher pauta não fornecida de antemão pelo programador, descoberta pública realmente autorizada, editor real, redator real, pesquisa complementar real (quando há necessidade legítima), retorno AO MESMO redator, checagem/revisão reais, imagem autorizada e navegador efetivamente observado, aprovação final humana pendente. Sem mock de decisões agenticas.
7. Escrever relatório factual por unidade de implementação com matrix requisito→evidência, falhas remanescentes e resultado; sem “E2E PASS” por 121 testes unitários, sem falsos positivos.
8. Não editar DNAs, não alterar PRs legadas, não publicar, não contratar, não fazer merge na main e não destruir dados originais.

## 15. Relação com o plano de teste e recuperação

O documento complementar ENG-CODEX-012-MATRIZ-DE-FALHAS-E-ACEITE-V1.md detalha cada falha histórica, as transições corretas, o contrato mínimo de recuperação e testes. Ambos são inseparáveis. Sem matriz de falhas efetivamente executada e teste de navegador, esta arquitetura é somente especificação.
