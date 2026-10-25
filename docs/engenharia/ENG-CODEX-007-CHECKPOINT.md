# ENG-CODEX-007 — checkpoint de continuidade

Atualizado: 2026-10-25 14:52 -03:00
Última unidade concluída: **E07 — pessoas, projetos, aliases, entrevistas e idiomas, validada localmente**
Unidade em andamento: **E08 — ledger de alegações e rumores (análise do schema existente; sem edição E08 ainda)**
Próxima unidade após E08: **E09 — scheduler configurável, default OFF**

## Estado do trabalho

- Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28) autoriza a sequência E01–E19 em branch de implementação e PR draft. A [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29) é somente o pacote documental do Fundador 2; foi lida pelo ref `7072655d44602e83d8bc2dbdd87d08391b711ad0` e não foi alterada.
- Branch de produto: `codex/eng-codex-007-factory-radar`, upstream `origin/codex/eng-codex-007-factory-radar`; base HEAD #26 `4de16640e67bd16c61468955e96e4ffa850d4cab`. PR de implementação [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), aberta/draft/sem merge, baseada na branch da #26.
- PRs #24 → #25 → #26 continuam abertas/draft/sem merge. #26 recebeu review `COMMENTED` favorável ao handoff A0–D2 com ressalvas; não é aprovação de merge. `origin/main=ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; a cadeia acumulada está 53 commits à frente e `merge-tree` local não detectou conflitos.
- PRs #8/#10/#18 e #13/#14/#19/#27 continuam independentes e sem merge. Consultar E01 para os HEADs e responsabilidades por componente.
- Revalidação E02: PR #30 continua draft/aberta/sem merge; push confirmado em `10532233fe5a50a349c8440002ec3ca4a8dfcdcc`, mesmo HEAD local/remoto no último `ls-remote`; `origin/main=ce8f6a7b65c2050d5da851491c9c89835f82c3a2`.
- E03: PR #30 aberta/draft/sem merge; commit de implementação e push confirmados em `e161e084cb5fbe99ed1f06751079b8de795182bb`, mesmo HEAD local/remoto no `ls-remote`; antes das alterações E03, HEAD era `747dfa841e1b47aee7dd0244b6f091df029abb80`.
- E04: código/testes no commit `509a882`; relatório, índice e checkpoint inicial no commit `f5e358e0f75a8e2d1ee4c997da26716e0bf96882`; ambos enviados. PR #30 segue aberta/draft/sem merge; E04 está concluída e validada conforme o relatório abaixo.
- E05 código/testes no commit `313baeeb1384354189c49a2a3ec206dc8a428ae1`; relatório/índice/checkpoint em `d4bbb81e2c8d0019f4d6062f42062803ab6097e4`, handoffs na Issue #28 (`6400677577`) e PR #30 (`6400677792`); checklist E01–E05 marcado com evidências.
- E06 código/testes no commit `eddc0e904b0a220f24651209a4e4da2d27153423`; relatório/índice/checkpoint no commit `1d78eb83100b5fc3dba0c3989a0e1142c0360725`; ambos enviados e sincronizados. Handoffs publicados na Issue #28 e PR #30; checklist E01–E06 marcado com evidências. PR #30 continua draft/aberta/sem merge.
- E07 implementação/testes em `b63c620e39d3e4ac4fea3ebdca37a71d10cde653`; relatório/índice/checkpoint final em `dace58c53132c6db4ef5bd21c1795cc73709a80f`; ambos enviados. Suíte integral 147/147. Handoffs Issue #28 [6401083176](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6401083176) e PR #30 [6401083777](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6401083777); checkbox E07 atualizado. PR #30 segue draft/aberta/sem merge.

## Evidências E01 executadas nesta sessão

- CPython 3.11.9: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → 95/95 OK em 65,982 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git merge-tree --write-tree origin/main origin/codex/eng-codex-006-e2e-experiment` → sem conflito, árvore `68a1223f97e4d1e499346ba52c1054698eb60cbf`.
- `motor_editorial/runtime/motor.sqlite3` foi apenas localizado por metadados; não foi aberto nem consultado. O D0 contém observação histórica em modo somente leitura (runtime v4; schema do código v5).
- Sem chamadas SIWC/Plus, APIs pagas, fontes externas, migração, publicação ou deploy; `published=false`.

## Evidências E02 executadas nesta sessão

- CPython 3.11.9, suíte focada: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts -v` → **12/12 OK**, 1,417 s.
- Suíte completa: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **107/107 OK**, 69,575 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0; `git diff --check` passou. A primeira checagem staged encontrou uma linha em branco final no módulo; removida e a checagem staged repetida sem erro.
- Implementados contratos versionados e catálogo; integração opcional no `TaskDispatcher` e no `AgentQueue` existente; fixtures cobrem role/versão/hash, tool scope, prompt injection, input tampering, resultados inválidos e `ResearchRequest/Packet`.
- Relatório E02: `docs/engenharia/ENG-CODEX-007-E02-CONTRATOS-VERSIONADOS.md`. Arquivos de código/teste: `motor_editorial/agent_contracts.py`, `motor_editorial/orchestration.py`, `motor_editorial/tests/test_agent_contracts.py`.
- Nenhum acesso ao SQLite runtime, migração, SIWC/Plus real, API paga, fonte externa, publicação, deploy ou merge; `SCHEMA_VERSION=5`, `published=false`.

## Evidências E03 executadas nesta sessão

- CPython 3.11.9, E02+E03 focados: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_agent_contracts -v` → **20/20 OK**, 1,159 s.
- Suíte completa: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **115/115 OK**, 65,036 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0; `git diff --check` passou.
- Catálogo embarcado carregado: 8 perfis, 6 habilitados, `media_researcher` e `layout_planner` desligados. Fixtures cobrem entrada/saída válida e rejeição de campo extra/saída incompleta para cada papel.
- Relatório: `docs/engenharia/ENG-CODEX-007-E03-CATALOGO-PAPEIS-FUNCIONAIS.md`; índice atualizado em `docs/engenharia/README.md`; novos arquivos `motor_editorial/agent_roles.json`, `motor_editorial/tests/fixtures/agent_role_fixtures_v1.json`, `motor_editorial/tests/test_agent_role_catalog.py`.
- Nenhuma inferência, chamada SIWC/Plus, API paga, fonte externa, mídia real, acesso/migração do SQLite runtime, publicação, deploy ou merge. `published=false`.

## Evidências E04 executadas nesta sessão

- CPython 3.11.9, testes focados: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store -v` → **9/9 OK**, 1,686 s.
- Suíte completa: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **124/124 OK**, 73,891 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0; `git diff --check` passou.
- `motor_editorial/radar_store.py` implementa schema independente v1 e namespace `radar_*`, rejeição do caminho runtime, validação de namespace, FKs, armazenamento de fontes/documentos/eventos/entidades/alegações/pesquisas/carteira, históricos append-only e backup/restauração SQLite.
- Fixture de migração v0 preservou a origem com defaults conservadores; backup restaurou a fixture original sem migração; URL inválida após criação transacional do schema causou rollback integral; tabelas fora do namespace foram recusadas.
- Relatório: `docs/engenharia/ENG-CODEX-007-E04-RADAR-STORE.md`; testes: `motor_editorial/tests/test_radar_store.py`. `motor_editorial.db.SCHEMA_VERSION=5` não foi alterado; `RADAR_SCHEMA_VERSION=1` é local ao arquivo de teste isolado.
- Nenhuma abertura ou migração do SQLite runtime, coleta/rede, inferência, SIWC/Plus, API paga, publicação, deploy ou merge. Bancos de teste foram temporários; `published=false`.

## Evidências E05 executadas nesta sessão

- CPython 3.11.9, focado: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_connectors -v` → **12/12 OK**, 0,531 s.
- Suíte completa: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **136/136 OK**, 88,750 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0; `git diff --check`/`git diff --cached --check` passaram.
- Perfis exigem política de acesso, termos revisados, snapshot robots por host e operação allowlisted. HTTPS/TLS padrão, allowlist exata, IP público pinado, DNS/redirect revalidados, limite de tamanho/tempo, cabeçalhos condicionais, `Retry-After`, backoff e suspensão foram cobertos por testes. O transporte não devolve o corpo bruto; parsers RSS/Atom/HTML/JSON expõem somente metadados.
- Cenários de rede usam transportes/resolutores simulados; um teste usa servidor loopback. Nenhuma origem pública, API, login, credencial, SIWC/Plus ou rede privada foi consultada. Estado de suspensão/cooldown é volátil; sem scheduler.
- Relatório: `docs/engenharia/ENG-CODEX-007-E05-CONETORES-LEITURA-PUBLICA.md`; testes: `motor_editorial/tests/test_radar_connectors.py`.
- Sem bloqueio técnico atual para E06 offline. Termos e robots continuam exigidos por origem antes de qualquer coleta real. O parecer de eficiência de contexto da direção (Issue #28, comentário `6400571458`) orienta E11/E13–E19 sem reabrir E01–E05.

## Evidências E06 executadas nesta sessão

- CPython 3.11.9 do `.venv`: `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- Suíte focada: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental -q` → **27/27 OK**, 6,216 s.
- Suíte completa final: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **142/142 OK**, 161,422 s.
- Uma execução integral intermediária falhou em um teste de concorrência preexistente do workflow e na limpeza da pasta temporária; o teste isolado passou 1/1 em 13,961 s e a execução integral seguinte passou 142/142. Causa da ocorrência transitória não determinada; nenhum código/teste do workflow foi alterado.
- `radar_store.py` evoluiu o arquivo isolado do Radar para schema v2 via migração aditiva v1→v2; fonte e documento atuais mantêm cache condicional, hashes de corpo/segmentos e URL de origem. `radar_fetch_events` preserva tentativas append-only e `radar_fetch_cache` usa `(source_id, request_url)` para compartilhar validadores entre perfis.
- `radar_connectors.py` expõe apenas fingerprints SHA-256 do corpo/payload, sem texto bruto; `radar_incremental.py` mantém um documento por origem+URL canônica, grava ObservationEvents e apresenta `requires_triage` determinístico, sem chamar agentes/LLM ou dispatcher.
- Query params e sua ordem são preservados; chaves de credencial são recusadas. Grupos só são ligados por URL de origem explicitamente declarada ou cópia idêntica de corpo/título/autoria compatível; bylines e documentos ficam separados.
- Provas exclusivamente em fixtures, SQLite temporário, DNS e transportes falsos. Nenhuma fonte pública, SIWC/Plus, API paga, banco runtime, scheduler, publicação, deploy ou merge; `published=false`.
- Relatório E06: `docs/engenharia/ENG-CODEX-007-E06-COLETA-INCREMENTAL-CACHE-DEDUP.md`; testes: `motor_editorial/tests/test_radar_incremental.py`, regressões em `test_radar_store.py` e `test_radar_connectors.py`.

## Arquivos e commits

- Relatório E01: `docs/engenharia/ENG-CODEX-007-E01-BASELINE-PLANO-INTEGRACAO.md`.
- Checkpoint: `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md`.
- Commit E01: `aeb7b5cdd132aed041a9fe7301c656f810389a31` (`docs: record ENG-CODEX-007 E01 baseline`), push confirmado.
- E02: `b590bc11a2ce3ea9bdbe5608ca6e13ab94d1d0ad` (`feat: add versioned agent contracts`), correção `8eda0e905a40afeb97da90cd5f8a858de807ec84` e checkpoint `10532233fe5a50a349c8440002ec3ca4a8dfcdcc`; os três enviados.
- E03 commit `e161e084cb5fbe99ed1f06751079b8de795182bb` (`feat: register ENG-CODEX-007 agent roles`), push confirmado; este checkpoint registra a confirmação e os handoffs.
- E04 commit `509a882` (`feat: add isolated ENG-CODEX-007 Radar store`), push confirmado; relatório/índice e checkpoint inicial em `f5e358e0f75a8e2d1ee4c997da26716e0bf96882` (`docs: record ENG-CODEX-007 E04 evidence`), push confirmado.
- E05 commit `313baeeb1384354189c49a2a3ec206dc8a428ae1` (`feat: add policy-gated Radar connectors`), push confirmado; relatório/índice/checkpoint final em `d4bbb81e2c8d0019f4d6062f42062803ab6097e4` (`docs: record ENG-CODEX-007 E05 evidence`), push confirmado.
- E06 commit `eddc0e904b0a220f24651209a4e4da2d27153423` (`feat: add incremental Radar collection and dedupe`), push confirmado; relatório/índice/checkpoint em `1d78eb83100b5fc3dba0c3989a0e1142c0360725` (`docs: record ENG-CODEX-007 E06 evidence`), push confirmado.
- Handoff E01: Issue #28 [6400102493](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400102493); PR #30 [6400102870](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400102870). Handoff E02: Issue #28 [6400254111](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400254111); PR #30 [6400254420](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400254420). Handoff E03: Issue #28 [6400348282](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400348282); PR #30 [6400348695](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400348695).
- Handoff E04: Issue #28 [6400474759](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400474759); PR #30 [6400475907](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400475907).
- Handoff E05: Issue #28 [6400677577](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400677577); PR #30 [6400677792](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400677792). Comentário da direção sobre eficiência de contexto: Issue #28 [6400571458](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400571458).
- Handoff E06: Issue #28 [6400926282](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400926282); PR #30 [6400926504](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400926504). A direção acrescentou roteamento futuro independente de provedor em Issue #28 [6400791472](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400791472); essa diretriz não autoriza gastos/credenciais e não altera as unidades concluídas.
- Complemento da direção sobre roteamento futuro entre provedores: Issue #28 [6400791472](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400791472). E06 não altera `fallback=none`, não chama provedores e não reabre E01–E05; E13/E17 deverão respeitar adaptadores, mocks e os gates financeiros/autorização deste comentário.

## Evidências E07 — concluída/validada localmente

- Critério da ordem: pessoas/projetos e aliases com idioma/proveniência; homônimos separados por contexto; cargos públicos com intervalos; distinguir entrevista de press release; registrar original/tradução sem copiar texto; excluir contatos/dados pessoais privados.
- `radar_store.py`: schema independente v3; migração v2→v3 transacional, preserva entidades e relações legadas, adiciona documento/contexto de identidade e novos registros append-only de cargos/entrevistas/variantes. FKs são verificadas antes do commit; uma fixture órfã demonstrou rollback para `user_version=2` sem DDL parcial.
- Validação de pessoa/projeto/alias, cargos e idioma exige documentos e fontes `allowed`. Entrevista exige vínculo com a pessoa/documento registrado. Press release exige fonte `official` e relação explícita à organização emissora. Registro de pessoa não aceita metadata livre; contexto, aliases e títulos recusam contatos. Nenhum texto de entrevista é armazenado.
- CPython 3.11.9, `.venv`: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -p 'test_radar*.py' -v` → **32/32 OK**, 4,563 s; suíte integral `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **147/147 OK**, 73,412 s; `compileall` exit 0; `git diff --check` exit 0 (avisos não fatais de conversão LF→CRLF).
- Relatório: `docs/engenharia/ENG-CODEX-007-E07-PESSOAS-ALIAS-ENTREVISTAS-IDIOMAS.md`; testes: `motor_editorial/tests/test_radar_entities.py` e migrações em `motor_editorial/tests/test_radar_store.py`.
- Commit/push da implementação e testes: `b63c620e39d3e4ac4fea3ebdca37a71d10cde653`; relatório/índice/checkpoint final: `dace58c53132c6db4ef5bd21c1795cc73709a80f`.
- Handoff Issue #28: [6401083176](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6401083176); handoff PR #30: [6401083777](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6401083777). Issue E07 marcada como concluída com evidências.
- Fixtures/SQLite temporário e hosts `.invalid` somente; sem rede pública, LLM, SIWC/Plus, API paga, runtime DB, scheduler, publicação, deploy ou merge; `published=false`.

## E08 — início de análise

- Critério da Issue #28: ledger de alegações/rumores com origem, atribuição, estado epistemológico e evolução, incluindo contradição/correção/retração; não promover alegação a fato por repetição ou fonte derivada.
- Próximo passo: inspecionar `radar_claims`, `radar_claim_sources`, `radar_claim_events`, suas operações e testes existentes, comparar com a ordem E08 e acrescentar apenas as invariantes faltantes. Usar fixtures SQLite temporárias, sem consultar fonte pública ou acionar agentes.
- Nenhuma alteração de código E08 ainda. Preservar status de rumor distinto do estado do conteúdo, fontes originais/derivadas e histórico append-only. O uso do banco runtime segue proibido nesta Issue.

## Bloqueios e retomada

Não há bloqueio técnico atual para E08 offline. Não retomar ou reexecutar C2–D2; eles foram entregues na PR #26 e receberam parecer favorável de encerramento com ressalvas. E01–E07 foram validadas, commitadas e enviadas. Os gates futuros de E16/E17 continuam: origem pública só com perfil/termos/robots aprovados; SIWC/Plus apenas após preflight e elegibilidade/consentimento, sem chamadas faturáveis.

Se houver interrupção durante E08, conferir primeiro `git status --short --branch`, upstream, HEAD remoto, PR #30, Issue #28 e este checkpoint; continuar a inspeção do ledger antes de editar. E07 está concluída conforme o relatório vinculado no índice de Engenharia. Não editar a branch/documentação da PR #29, não reconstruir o motor/OAuth/DNAs e não acessar o banco runtime real.
