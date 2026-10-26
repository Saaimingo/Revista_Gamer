# ENG-CODEX-012 — Checkpoint de arquitetura e contratos

**Atualizado:** 2026-10-26
**Issue:** [#42](https://github.com/Saaimingo/Revista_Gamer/issues/42)
**Documentação normativa:** [PR #43](https://github.com/Saaimingo/Revista_Gamer/pull/43), os três documentos foram lidos integralmente antes de qualquer mudança.
**Branch:** `codex/eng-codex-012-architecture-contracts`, derivada de `codex/eng-codex-011-live-factory@27c6703`.
**Status:** em andamento. U00–U04 concluídas; próxima unidade U05. Nenhuma chamada SIWC/Plus ou pesquisa pública nesta missão.

## Limites ativos

- ENG-011 usou as quatro requisições públicas autorizadas. Nenhuma pesquisa pública adicional está autorizada por esta missão; não repetir pesquisa nem resposta SIWC arquivada.
- Preservar todos os DNAs aprovados e os artefatos privados integrais; não copiar matéria integral ou resposta privada ao repositório.
- Sem API paga, publicação, merge ou deploy. Aprovação humana final continua pendente.
- ENG-012 U10 (piloto público real novo) permanece bloqueada até autorização específica posterior; continuar unidades offline e usar registros existentes.

## Feito nesta retomada

- Revalidado live branch/upstream/status/commits: branch ENG-011 limpa e sincronizada em `27c6703`; consultadas Issue #41 e comentário de handoff, que confirmam Issue aberta, limite 4/4 esgotado e ENG-011 não homologada.
- Lidos os documentos locais obrigatórios e os três contratos ENG-012 da PR #43 antes de alteração arquitetural.
- Auditado o `research-flow.json` e o `ledger/radar.sqlite3` privados em modo read-only. Resposta detalhada Proton: HTTP 200, 2.120 bytes, hash `8400dc8314939d00f3e0346df6ee15a3dbcc33b34773df48b0fd7cf719efc988`; documento Radar `3fa4064bb5d46d9e07a384806ca51735`; pacote `56610495-0ee9-4403-bbfd-70d61643ac64`, `blocked`, sem document/claim refs.
- **Causa raiz localizada sem nova consulta:** depois de persistir o documento e `statement_by` em `radar_document_entities`, `GitHubReleaseResearchProvider.search` consulta `RadarStore.get_row("radar_topics", "topic_id", topic_id)`. A allowlist de `get_row` omite essa tabela, embora `list_rows` a permita. A chamada lança `RadarStoreError` antes de criar tópico/claim. O estado parcial no SQLite confirma exatamente esse ponto da sequência. `ResearchService.execute` esconde a etapa/código sob resultado bloqueado e constraint genérica; a exceção original não foi registrada.
- Branch ENG-012 criada e rastreada por `origin/codex/eng-codex-012-architecture-contracts`; matriz e checkpoint U00 foram commitados em `8266585` e enviados ao GitHub.
- Matriz módulo a módulo e por unidade está em `docs/engenharia/ENG-CODEX-012-MATRIZ-RASTREABILIDADE.md`.
- Corrigido no dono do contrato: `RadarStore.get_row` agora aceita `(radar_topics, topic_id)` e emite código/fase sanitizados para chaves não permitidas.
- `ResearchExecutionDiagnostic` v1.0 separa `phase`, `code` e `exception_type` da prosa do `ResearchPacket`; resultado persistente da tarefa Radar passou a v1.1, mantendo leitura retrocompatível do resultado v1.0. A mensagem da exceção não é serializada.
- Issue #42 foi revalidada ao vivo; a Direção reiterou 7 chamadas arquivadas (109.336 tokens, 142.047 ms), estratégia de corrigir contratos antes de novo uso de franquia, autorização para trabalho Plus necessário e ausência de autorização para novas consultas públicas além das 4/4 da ENG-011.
- U02 generalizou o contrato de resultado de agentes: `AgentResultEnvelope` agora grava v1.1 com `usage_receipt_ref` tipado e hash-checked, mantendo leitura/serialização v1.0. Cada execução SIWC persiste recibo de uso por tarefa/tentativa, vinculando tokens, latência, resposta, hash e ID de resposta do provedor; custo real e percentual de franquia ficam explicitamente indisponíveis.
- U03 tornou a persistência da resposta SIWC recuperável: request imutável; resposta e manifesto publicados como bundle local atômico; leituras verificam task binding e hashes; artefatos flat existentes continuam legíveis. A recuperação local valida input atual, DNA/hash aprovado, instruções, modelo/esforço, resposta concluída e recibo, reconstrói o envelope sem chamar SIWC e é tentada antes de novo claim.
- U03 substituiu reparos específicos do runner por APIs gerais da fila para adotar resultado externo já persistido, reconciliar campos ausentes de um resultado concluído sem trocar sua resposta e reencaminhar falha pré-externa identificada. Tentativas com chamada externa iniciada passam a `uncertain` e retries legados com marcador externo são colocados em quarentena.
- A fronteira externa de pesquisa agora é marcada pelo callback imediatamente antes do transporte, não ao iniciar tarefa. O conector Radar chama o callback uma vez antes da primeira requisição e o repassa por `IncrementalRadarService`/provider; bloqueios prévios à rede não marcam chamada.
- U04 corrigiu os contratos gerais de coleta do Radar em `radar_connectors.py`, `radar_policy.py`, `radar_incremental.py` e `radar_store.py`: SourceProfile v1.1 mantém leitura v1.0, inclui identidade/classe/canal, HTTPS público sem autenticação, allowlist exata de host e caminho, termos/robots, direitos separados de acesso, parser/schema, idioma, limites e quotas versionados.
- A implementação e regressões U04 foram commitadas em `af8cc6e` e enviadas à branch da PR #44; a descrição draft da PR foi atualizada com escopo, provas offline e limites da evidência.
- Parsers JSON agora exigem schema reconhecido (`github_release_v1` ou `metadata_records_v1`), distinguem URL humana de endpoint técnico e descartam `body_excerpt` sem direito autorizado inclusive nos perfis legados. HTTP 200 com schema incompatível fica `parse=unsupported` e `ingest=not_attempted`; HTTP 200 sem registros termina `no_new_story`, sem criar documento. Paths percent-encoded são decodificados repetidamente para impedir traversal duplamente codificado.
- Quotas v1.1 são reservadas em SQLite antes de cada transporte e limitam host/dia, missão e fonte/missão; registro da resposta persiste request id, status HTTP, URLs, tipo, bytes, hash e fingerprint/version do perfil sem corpo bruto. Uma tabela append-only registra parse e ingest separadamente, códigos sanitizados, contagens e refs de documentos/eventos; replay do mesmo evento é idempotente.
- Migração Radar v7→v8 preserva fetches/quota anteriores, preenche status como `legacy` e cria o ledger de processamento. A validação cobre classes oficial/independente/comunidade/replicador, paths, traversal codificado, quotas entre hosts, schemas de API, integração fetch→parse→ingest, HTTP 200 sem pauta e migrações; nenhum DNS/transporte real ou pesquisa pública foi executado.

## Validação e resultados

- Regressão antes da correção: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store.RadarStoreTests.test_get_row_reads_topic_by_typed_primary_key -q` — falhou com `RadarStoreError: Tabela/chave de leitura não suportada.`.
- Regressão após a correção: lookup de tópico, diagnóstico estruturado, persistência após reiniciar `AgentQueue` e bloqueio de continuação vazia — 4/4 passaram.
- Validação focada em CPython 3.11.9: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_orchestration motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_research_service motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_eng_codex_011_runner -q` — 124 testes em 45.664 s, OK.
- U02/U03, suíte integrada focada em CPython 3.11: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_orchestration motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_research_service motor_editorial.tests.test_factory_multipauta -q` — 120 testes em 250.395 s, OK.
- U02/U03: `py_compile` nos 14 módulos de código/teste modificados — OK; `git diff --check` — OK antes da atualização deste checkpoint.
- U04, CPython 3.11 do `.venv`: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_policy motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental` — 46 testes em 11,500 s, OK. Abrange perfis v1.1, path/SSRF, quotas, parser, recibos de etapa, integração incremental e migração v7→v8; transporte/resolver são fakes locais.
- Regressão integrada após U04: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_orchestration motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_research_service motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_eng_codex_011_runner -q` — 134 testes em 49,535 s, OK. Sem chamadas de SIWC/Plus nem pesquisa pública.
- U04: `.venv\Scripts\python.exe -m py_compile` nos quatro módulos Radar alterados e três arquivos de teste — OK; `git diff --check` — OK antes da atualização dos documentos.
- Recuperação após interrupção entre persistência e conclusão da fila validou resposta e receipt com hashes idênticos, `attempts=1` e zero chamadas no cliente SIWC reiniciado; reparo do vínculo receipt no manifesto também reaproveitou arquivo existente por tarefa/tentativa. Testes locais/sintéticos comprovam apenas os estados cobertos, não homologação real de provedor.
- Consultas SQLite de diagnóstico feitas com URI `mode=ro`. Nenhum registro, fonte ou pacote ENG-011 foi modificado.
- Nenhuma chamada SIWC/Plus nem consulta pública foi realizada durante a implementação/validação; respostas arquivadas não foram repetidas.

## Unidades concluídas

- **U00:** inventário e matriz por módulo/unidade.
- **U01:** causa raiz comprovada nos registros, allowlist corrigida, falha técnica estruturada separada do packet e resultado Radar persistido com diagnóstico na fila.
- **U02:** compatibilidade de envelope de resultado v1.0/v1.1 e recibo de uso persistido e ligado por hash.
- **U03:** resposta/manifesto atômicos, recuperação local sem chamada externa, fronteira externa correta e operações genéricas de adoção/reconciliação/requeue; validado com 120 testes offline focados.
- **U04:** SourceProfile v1.1 e compatibilidade v1.0, paths estritos, parser JSON por schema reconhecido, quotas persistentes, hash/bytes/request/profile version e recibos separados de transporte/parse/ingest; migração v7→v8 e integração local comprovadas com 46 testes focados e regressão cruzada de 134 testes. Não prova coleta pública.

## Próximo passo

1. U05–U07: completar handoffs da pauta entre triagem, investigador, editor, jornalista, pedido de pesquisa, fact-check e revisor, vinculados à story/revision/persona corretas.
2. U08: localizar draft e imagem existentes com direitos demonstráveis; servir preview HTTP local e comprovar visualmente texto e imagem no navegador.
3. U09: provar isolamento multipauta e agregação de orçamento sem duplicidade; uma pauta bloqueada não interrompe as demais.
4. Registrar matriz/checkpoint e commits/push a cada unidade revisável; manter PR #44 draft, sem merge. U10 fica bloqueada até autorização específica para novas consultas públicas.

## Critérios ainda abertos

Handoffs U05–U07, preview real em navegador U08, isolamento multipauta U09 e nova homologação U10 (bloqueada por autorização de pesquisa esgotada). A missão não está concluída enquanto algum critério obrigatório permanecer aberto.
