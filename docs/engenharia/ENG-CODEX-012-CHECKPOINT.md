# ENG-CODEX-012 — Checkpoint de arquitetura e contratos

**Atualizado:** 2026-10-26
**Issue:** [#42](https://github.com/Saaimingo/Revista_Gamer/issues/42)
**Documentação normativa:** [PR #43](https://github.com/Saaimingo/Revista_Gamer/pull/43), os três documentos foram lidos integralmente antes de qualquer mudança.
**Branch:** `codex/eng-codex-012-architecture-contracts`, derivada de `codex/eng-codex-011-live-factory@27c6703`.
**Status:** em andamento. U00 e U01 concluídas; U02/U03 em seguida. Nenhuma chamada SIWC/Plus ou pesquisa pública nesta missão.

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

## Validação e resultados

- Regressão antes da correção: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store.RadarStoreTests.test_get_row_reads_topic_by_typed_primary_key -q` — falhou com `RadarStoreError: Tabela/chave de leitura não suportada.`.
- Regressão após a correção: lookup de tópico, diagnóstico estruturado, persistência após reiniciar `AgentQueue` e bloqueio de continuação vazia — 4/4 passaram.
- Validação focada em CPython 3.11.9: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_orchestration motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_research_service motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_eng_codex_011_runner -q` — 124 testes em 45.664 s, OK.
- Consultas SQLite de diagnóstico feitas com URI `mode=ro`. Nenhum registro, fonte ou pacote ENG-011 foi modificado.
- Nenhuma chamada externa foi realizada durante a implementação/validação.

## Unidades concluídas

- **U00:** inventário e matriz por módulo/unidade.
- **U01:** causa raiz comprovada nos registros, allowlist corrigida, falha técnica estruturada separada do packet e resultado Radar persistido com diagnóstico na fila.

## Próximo passo

1. U02: revisar versões de envelopes/resultados, persistência de respostas/hash/uso e consumidores da mudança de resultado Radar v1.1; decidir migrações e compatibilidade de histórico.
2. U03: mapear cada fronteira de crash na fila/SIWC e na coleta; garantir que resposta completa/receipt seja reutilizado e chamada externa incerta não seja repetida.
3. Validar U02/U03 com regressões de fila reiniciada e respostas arquivadas; nenhuma chamada Plus/Radar nova.
4. Atualizar matriz/checkpoint, fazer commit/push após a unidade e abrir PR draft para revisão técnica quando os contratos formarem uma mudança revisável.

## Critérios ainda abertos

Contratos gerais U02, recuperação confiável U03, arquitetura Radar offline U04, handoffs U05–U07, preview real em navegador U08, isolamento multipauta U09 e nova homologação U10 (bloqueada por autorização de pesquisa esgotada). A missão não está concluída enquanto algum critério obrigatório permanecer aberto.
