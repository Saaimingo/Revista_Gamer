# ENG-CODEX-012 — Contratos concretos de integração, orquestração e persistência
**Anexo obrigatório** à arquitetura-mestra e matriz de falhas da ENG-CODEX-012, 26/10/2026. É especificação de interfaces-alvo para IMPLEMENTAÇÃO, não alegação de que o schema atual tem todos os campos descritos. Adaptar/versionar contratos existentes em vez de criar classes paralelas incompatíveis.

## 1. Regra de construção: atualizar os donos, não construir uma segunda fábrica

**Um dono por responsabilidade:**
- motor_editorial/orchestration.py: AgentQueue, TaskDispatcher, leases/fencing/dependências/execução/recovery ownership.
- motor_editorial/agent_contracts.py: envelope da tarefa, perfis de papel, pesquisa tipada, referência de artefato, resultado, validação de hashes e versões.
- motor_editorial/agent_roles.json: perfis de triage_analyst, evidence_investigator, assignment_editor, persona_writer, fact_checker, editorial_reviewer, media_researcher, layout_planner. Papéis agenticos só são executados quando uma tarefa exige decisão cognitiva real. Versão/hash congelados.
- motor_editorial/agent_siwc.py: executor SIWC e armazenamento durável do raw response, structured response, usage/latência e estado da chamada externa.
- motor_editorial/radar_store.py: documentos, fontes, entidades, claims, versões, observações e research packets.
- motor_editorial/radar_connectors.py: HTTP/allowlist/robots/SSL/SSRF/timeouts/quotas e metadados seguros da coleta.
- motor_editorial/radar_incremental.py: snapshot, deduplicação, extração de FeedItem/entidades de metadados, eventos e continuidade.
- motor_editorial/radar_triage.py: batch de triagem e links tipados event→document→item.
- motor_editorial/research_service.py: índice/cache, adapter/provider público autorizado, proveniência, status de evidência, orçamento e payload de resultado.
- motor_editorial/research_mediation.py: question/purpose livres → ResearchRequest v1.1 com política confiável; sem comparação textual literal.
- motor_editorial/agent_workflow.py: ResearchResultRouter + ResearchTaskExecutor e handoff do pacote.
- motor_editorial/editorial.py e factory.py: revisões, composição, gates, story packages, integração de drafts e preview com imagem.
- motor_editorial/layout/: contrato e engine de layout; não produzir texto jornalístico artificial.
- motor_editorial/eng_codex_011.py: ensaio/test harness e execução da missão 011. Seus tratamentos específicos devem migrar ao módulo dono quando generalizáveis; não transformar runner 011 em backend permanente.
- Interface de operação: CLI/dashboard de estado, ações autorizadas e prévia; não deve esconder logs em scripts exploratórios.

Codex deve confirmar este mapeamento lendo código corrente. Se os arquivos/funções divergirem, registrar divergência e corrigir esta proposta; não inventar que interface já existe.

## 2. Payload mínimo por fronteira — produtores/consumidores e invariantes

### I01. SourcePolicy → Connector
**Dono produtor:** configuração autorizada pelo humano/Motor. **Consumidor:** RadarConnectorService.
**Dados obrigatórios:** source_id; canonical origin; kind RSS/API/HTML; exact allowed hosts and operations; path constraints; terms_checked_at e provenance; robots_checked_at/provenance; max response bytes; timeout; min interval; quota por host+missão; redirects; access_policy. **Não confiável:** URL sugerida por LLM ou página.
**Pré-condições:** política não expirada, sem secret em URL, DNS e IP públicos, HTTPS, rate limit disponível.
**Saída:** FetchResult com requested_url, final_url, http_status nullable, fetch.status, content_type, bytes, hash, fetched_at, error_code/phase, retry_at, requested_domain; body bruto apenas sob retenção expressa.
**Pós-condições:** reserva de quota durável ANTES de request externo. Não aceitar 200 vazio como prova de extração.
**Caso negativo:** 200 HTML quando esperado JSON → parse_unsupported com detalhes seguros, não “found”.
**Teste:** matriz R01–R17.

### I02. FetchResult → IncrementalRadarService/RadarStore
**Entrada:** status de transport, metadata parseado, URL canônica/humana, release tag/version, published_at, autoria, conteúdo resumível permitido, SHA, source policy version.
**Saída:** document_id/snapshot_id/event_id(s), origin_group_id, material_change/no_change, parse_count, rejected_count/reason, lineage, status do armazenamento.
**Invariante:** se o envelope alega N documentos persistidos, cada ID existe e pertence a fonte autorizada; duplicata do mesmo snapshot não cria segunda pauta.
**Caso negativo:** documento persistido e link de claim falhou → fase persistida + recovery idempotente local, não novo fetch.

### I03. DiscoveryBatch → triage_analyst
**Produtor:** RadarGeneralService. **Consumidor:** perfil real do papel, por TaskDispatcher.
**Input:** batch_id, item_ids, event_ids, documents, fontes, candidatos, tipo de evento, datas, tags, referências, restrições e prioridade determinística.
**Output:** lista de decisões por candidato ou grupo com refs, linha principal/reserva/monitoramento/descarte, categoria, relevância, motivo e falta de confirmação.
**Validação:** referenced_event∈batch; resolva ligação event→document→item; suggested_lane permitido. Conservar decisão íntegra e explicar rejeições.
**Caso negativo:** evento referenciado mas item_id ausente na resposta do LLM → vincular pelo registro Radar sem nova inferência.

### I04. Candidatos → evidence_investigator
**Input:** fontes/snapshots realmente obtidos, candidate links, brief de apuração, limites, lista de alegações existentes e perguntas.
**Output:** EvidenceDossier com facts/rumors/reports/claims, source_ids/doc_ids, primeira origem conhecida, timestamps, validações, contraditórios, questions e adequação editorial.
**Validação:** cada material_claim aponta evidência persistida; texto natural de claim_id pode ser armazenado como label, ID técnico gerado pelo Motor. Sem fonte real = missing_evidence, não claim oficial.
**Caso negativo:** 10 claims escritos naturalmente → IDs seguros por hash+namespace sem alterar respostas; comprovar texto original por SHA.

### I05. CandidateDossier → assignment_editor
**Input:** estado da carteira/edição, candidatos elegíveis inclusive monitoramento rastreável, investigação, restrições de fonte e jornalismo.
**Output:** candidate_item_id único; journalist_persona_id validado; EditorialBrief (angle, genre, questions, modules, gaps, needs_more_research, image_needs sem presumir rights).
**Validação:** candidato e jornalista do catálogo; proposta editorial consistente e não inventada pelo programa; sem poder alterar DNA.
**Caso negativo:** escolha equivocada sem prova → marcar hold e pedir revisão de atribuição, não inserir título de fixture no lugar.

### I06. Brief + DNA + EvidenceDossier → persona_writer
**Input trusted:** role instructions verificados + manifesto persona/version/hash com bytes preservados.
**Input untrusted:** textos de fontes, citações, comentários de fóruns; isolados para impedir prompt injection.
**Input narrativo:** título de pauta sugerido, ângulo, contexto, evidências reais, conteúdo aberto à interpretação responsável e perguntas. Metadados de schema/política não devem virar prosa.
**Output:** ArticleDraft integral, seções, headline/dek, citations/evidence IDs por seção, material_claims tipadas, gaps, requested_research natural (pode ser vazio), necessidade de mídia e revision metadata.
**Validação:** persona_hash e role_hash, refs existentes, Unicode completo, texto integral imutável. Não exigir que redator gere slug sem espaços nem permita contato externo arbitrário.
**Caso negativo:** hash muda por newline final → corrigir loader sem rerun SIWC.

### I07. requested_research → ResearchRequest v1.1
**Produtor:** persona_writer/evidence_investigator/triage_analyst conforme papel autorizar; sugestão livre NÃO é ferramenta de rede.
**Consumidor:** research_mediation.py.
**Entrada livre:** question, purpose, contexto da lacuna/claim e identificadores do parent task.
**Saída tipada:** request_id, parent_task_id, story_id, story_revision_id, requester_role_id, requester_persona_id, research_profile_id/version, question original, queries derivadas, entity_ids, required_evidence_kinds, preferred_source_ids/domains, allowed_scope, max_sources/requests/bytes/duration, known_evidence_ids, exclusions, languages, time_window, idempotency_key e human_gate_if_sensitive.
**Validação:** Motor deriva TODA permissão e orçamento de política versionada, decide tipo de fonte pelo assunto, vincula a parent result durável e revisão correta. Parafrasear/usar acento é permitido, URL livre não.
**Caso negativo:** pedido por benchmark sem fonte aprovada → hold_reason + pedido preservado, jamais fallback indiscriminado.

### I08. ResearchRequest → ResearchService/ResearchProvider → ResearchPacket
**Entrada:** request tipado, fonte indexada e provider aprovado, quotas e prova de permissão.
**Saída:** ResearchPacket com request_id, status, document_refs, claim_refs, source_lineage, relevant_excerpts_short, missing_evidence, constraints, retry_at, fetched_at, content_hash, retrieval_log_ref.
**Validação:** compare versão/snapshot, host, source, documento, epistemic status e linguagem; claim oficial exige documento oficial realmente persistido; HTTP 200 sem documento não satisfaz status found.
**Caso negativo:** API deu 200, mas parser ou register_claim falhou → blocked/partial com reason_code da fase; nunca esconder exceção e reportar apenas tipo.
**Retenção:** guardar bytes se autorização permite; caso não, declarar incapacidade de reprocessar e não afirmar que material foi preservado.

### I09. ResearchPacket → ResearchResultRouter → mesmo escritor
**Produtor:** ResearchTaskExecutor no TaskDispatcher.
**Validação de identidade:** parent_task_id, story_id, story_revision_id, persona_id/version/hash, request_id, perfil e policy hash; pacote não pode ser obsoleto nem reatribuído.
**Regra de roteamento:** packet útil → tarefa continue/revise do MESMO personagem com delta e fontes; packet blocked/vazio → nenhum SIWC de continuação, registrar hold/reorientação editorial. Packet partial útil → decisão de continuidade justificada com revisão e lacunas.
**Caso negativo:** packet de outro story enviado por colisão de IDs → rejeitar e alertar, nunca “aproveitar” pesquisa.

### I10. StoryDraft → fact_checker
**Entrada:** original integral e CURRENT revision hash, EvidenceDossier, ResearchPackets verdadeiros e citações.
**Saída:** FactCheckVerdict por afirmação e fonte com pass/fail/hold/needs_revision, severity e reasons referenciando seção; sem alterar texto por conta própria.
**Validação:** hash verificado e evidências existentes; rumour e medição de terceiros atribuídos. Um veredicto de versão antiga nunca libera nova revisão.
**Caso negativo:** nova alegação entra depois de PASS → invalidar aquele aceite.

### I11. Verdict → writer revision
**Entrada:** issues objetivas, referências, prioridades, texto integral anterior + persona imutável.
**Saída:** nova versão integral com change rationale e citacoes, registro imutável; texto anterior não sobrescrito.
**Validação:** mudanças semânticas exigem nova checagem; ajustes de schema/IDs semântica-neutros NÃO exigem gastar uma chamada de modelo.
**Caso negativo:** claim_refs usa reference de documento; somente mover campo em derivado se comprovado sem perder atribuição.

### I12. CurrentDraft + FactCheckVerdict → editorial_reviewer
**Entrada:** versão válida e checagem da mesma SHA, brief, DNA, voz e critérios P/T/J/F.
**Saída:** review approve_recommended/revise/hold (usar valores existentes ou versionar), apontando problemas concretos por parágrafo e evidências.
**Validação:** revisor independente não pode imitar um gate humano, nem inventar novo dado sem ResearchRequest permitido.
**Caso negativo:** reviewer pede alteração factual → redator e recheck; não atribuir PASS automático.

### I13. CurrentDraft → MediaResearcher + RightsGate
**Entrada:** blocos e necessidades de imagem, inventário editorial com autorização e política por canal.
**Saída:** asset candidates, license evidence, alt text, captions, rights status, restrictions e fallback sem mídia.
**Validação:** nenhuma imagem sem direito é habilitada para publicação; preview interno pode ter licenças mais restritas e deve expor esse estado. Separar editorial de publicidade.
**Caso negativo:** arquivo privado ImageGen existe mas não tem URL web pública → usar caminho local seguro no preview; não inferir direitos para redes.

### I14. CurrentDraft + rights-qualified assets → LayoutPlan/Renderer
**Entrada:** versão SHA aprovada para preview, seções reais, mídias elegíveis, identidade visual, regras mobile/desktop.
**Saída:** HTML/CSS, arquivos media relativos seguros, manifest + SHA, validation report e URL loopback.
**Validação:** nenhuma seção vazia por erro de schema, nenhuma URL quebrada, conteúdo escapado contra script injection, imagem carrega por HTTP 200 real no browser.
**Caso negativo:** file:// bloqueado → servidor 127.0.0.1; verificar viewport e screenshot; caso browser inacessível, NOT_VALIDATED.

### I15. Preview → HumanGate → publicação (futuro)
**Entrada:** versão/hash, direitos por ativo/canal, fact-check/review/hash vigentes, preview observado.
**Saída:** gate awaiting_human_approval e decisão assinada/situada por pessoa autorizada. publish fica disabled na homologação.
**Validação:** simulação jamais promove published=true nem autoriza postagem/rede social/afiliado.
**Caso negativo:** edição mudou após aprovação → invalida aprovação afetada e exige novo ato humano.

## 3. Modelo de execução e reabertura — decisões mecânicas obrigatórias

A) **Nunca iniciou externo e contrato falhou:** corrigir entrada/adapter, provar snapshot igual e reopen_pre_external por ledger, sem duplicar task, com nova tentativa auditada.

B) **Externo confirmado e resposta completa persistida:** load bytes com hash, validar role schema, adaptar semanticamente neutro, marcar recovered, encaminhar ao próximo consumer; custo extra = 0.

C) **Externo incerto:** phase uncertain; recuperar por status/recibo do provider quando disponível, senão esperar decisão; nunca retry automático.

D) **Coleta HTTP concluída e arquivo corpo permitido persistido:** reparse local e inserir idempotentemente documentos/claims faltantes; quota usada permanece usada; nunca “resetar” conta.

E) **Coleta HTTP concluída e só metadata/hash persistidos:** não existe replay possível; corrigir código offline, só depois solicitar autorização de nova busca. Não inventar corpo do documento.

F) **ResearchPacket partial com prova útil:** avaliação automática de severidade da lacuna e gate do editor; escritor pode seguir sem alegar o não comprovado.

G) **ResearchPacket blocked sem documentos/claims:** nenhum novo escritor, marcar motivo e reorientar pauta/fonte/outra matéria.

H) **Jornalista mudou fatos:** revisão com novo SHA + fact-check correspondente; parecer velho invalidado.

I) **Direitos falharam:** alternativa permitida, caso contrário hold apenas mídia/canal e não publicação; revisão textual pode progredir.

J) **Browser não abriu:** preview não validado, reparar apresentação sem chamar SIWC; nunca declarar E2E.

K) **Orçamento consumido:** fila durável aguarda quota/autorização; não usar API paga como “resgate”.

L) **Outra pauta pronta enquanto uma está bloqueada:** independência por story/edition, permite avanço e substituição devidamente registrada. Não apagar pendências.

**Estados operacionais devem ser explícitos**: parser_failure, ingestion_failure, evidence_missing, rights_hold, authorization_hold, insufficient_source, review_stale, external_uncertain, model_unavailable, quota_exhausted, preview_not_opened e manual_approval_required são classes DISTINTAS de causa, mesmo que as enumerações internas sejam versionadas.

## 4. Regras de implementação de persistência e transação

1. Operação apenas depois de reserva durável de budget/lease, sem reservar duas vezes na reabertura da mesma task.
2. Mudança de fase, evidências, versão e eventos escrita atomicamente quando pertencem à mesma unidade. Se SQLite não permite atomicidade entre banco e arquivo: write temp+fsync/rename seguro, evento de intenção no banco e reconciliação periódica pelo hash.
3. Todo ID de evento/docs/tasks tem namespace e origem. Canonicalização de strings afeta IDs derivados, nunca corpo literário ou DNA.
4. Definir chave única por idempotency key + papel + story_revision + parent_task; replay do mesmo input retorna mesmo task/result quando succeeded.
5. Nada de commit de trabalho no GitHub como substituto de salvar dados runtime, banco ou manifest de artefatos privados.
6. SQLite: backup/migração versionada com rollback e teste de versão futura recusada. Hash e versão do response originais imutáveis.
7. Logs públicos sem prompts integrais de pessoas, sem OAuth, sem conteúdos licenciados além do permitido, sem paths privados expostos inutilmente. Metadados suficientes para auditoria e debugging local.
8. Usage: uma linha por chamada real confirmada, se houve output; cache/recuperação não contabiliza nova inferência. Separar input/output/reasoning/total tokens, latência, custo API pago (zero/indisponível), franquia Plus observada manualmente.
9. Encerrar toda fase com contador de callbacks externos, número de tasks reused, status do gate e link para proof local.
10. Cada ajuste de contrato exige testes de consumidores anteriores e migração do histórico ENG-011 para leitura, sem corromper originais.

## 5. Sequências aceitas e rejeitadas (workflow de domínio)

**Aceito — pesquisa válida:** Story A rev 1 → writer A request X → policy allow X → Radar index + consulta externa permitida → packet X com documento D e claim C → writer A continuation rev 2 → fact-check rev 2 → review rev 2 → preview rev 2 → diretor pendente.

**Rejeitado — handoff cruzado:** Story A request X → pesquisa retorna → router aponta writer B/Story B. Mesmo que topic compatível, falta vínculo; bloquear sem tocar história B.

**Aceito — texto sem necessidade de pesquisa:** Story A com evidências suficientes → writer direto → fact-check → review, sem exigir artificialmente uma chamada Radar para marcar checkbox. A comprovação de que a CAPACIDADE de pesquisa existe exige teste próprio com pedido genuíno noutra pauta.

**Aceito — insuficiência central:** Story A sem evidência de benchmark → editor muda ângulo para explicar anúncio e lacunas relevantes sem inventar FPS OU segura pauta; se muda tema central, revisão de assignment e rastreabilidade; não publicar comparativo impossível.

**Rejeitado — processar relato de comunidade como fonte oficial:** comentário anônimo → official_statement sem vínculo formal. Deve ser community_report ou hold e atribuição.

**Rejeitado — auto publicação:** reviewer PASS + layout PASS + asset autorizado → published=true sem ação humana. Sempre bloquear.

## 6. Testes de integração mínimos que cruzam módulos (não apenas unittest da função)

- Cobrir chamadas do Radar via transport controlado com duas fontes heterogêneas; una responde, outra falha, editor recebe o lote real disponível.
- Exercitar schema source/event/item/claim com Unicode, dois-pontos, barras, CRLF, frases em português/inglês e títulos longos sem perder prosa.
- Na mesma fila SQLite persistida, model executor mock apenas para TESTES NEGATIVOS; provar fila, router e versões, reiniciar processo entre cada fronteira; comparar números de chamadas mockadas = 1 onde esperado.
- Em piloto REAL, substituir model mocks pelas chamadas SIWC existentes com papel/version/hash correto. Incluir recibos, não assumir que runner passou só por passar unittest.
- Resposta completa de investigador com claim_id human-readable produz resultado versionado a partir do mesmo artifact, com 0 chamada adicional.
- Resposta completa de escritor com requested_research natural vira ResearchRequest e packet, sem abandonar a mesma persona.
- Packet blocked/vazio não reabre writer. Packet partial com prova útil não inventa os tipos epistêmicos ausentes.
- Recurso de edição mantêm P/T/J/F e preservam DNA sha; fact-check/review apontam mesma revisão ou rejeitam stale.
- Preview HTTP loopback abre imagem, texto, links e paginação responsiva; screenshot e resultado de browser. Sem qualquer material publicado.
- Teste de fonte indexada que retorna 200 JSON release válida deve produzir item+doc+claim; se falha, error_code informa parser/ingest/claim phase e não apenas Exception genérica.
- Teste de chamada externa incerta faz STOP sem retry; outras pautas continuam.
- Teste de quota cheia impede novo HTTP mesmo quando diretor disse “use franquia do Plus”, porque orçamento de consulta e orçamento de modelo são dimensões diferentes.

## 7. Revisão e aceite por Codex

O Codex deve produzir plano de alteração por módulo dono e perfil/contrato afetado; **não** acrescentar dezenas de funções especiais de resume no runner ENG-011 para cada erro novo. Revisão de schema retrocompatível, teste, checkpoint e transição antes do próximo efeito externo. A saída de cada unidade explica: quais inputs e outputs mudaram, qual versão, quem produz e consome, como falha, como retoma, como preserva evidência, quem autoriza a próxima ação e quantas chamadas SIWC/HTTP realmente ocorreram. Falhas de segurança ou direitos mantêm bloqueio necessário. O aceite externo de publicação continua reservado ao diretor.
