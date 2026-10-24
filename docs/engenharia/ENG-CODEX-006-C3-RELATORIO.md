# ENG-CODEX-006 — C3: fluxos negativos e retomada

Data: 2026-10-24 17:26 America/Sao_Paulo

Status: **C3 concluída em branch experimental; sem merge ou aceite editorial.**

Branch: `codex/eng-codex-006-e2e-experiment`

PR: [#26](https://github.com/Saaimingo/Revista_Gamer/pull/26), draft.

## Cenários exercitados

| Cenário | Resultado observado |
| --- | --- |
| Divergência explícita entre fontes fictícias | análise e checagem marcam incerteza; revisão termina em `hold`; não cria inventário, pacote, plano, preview ou gate. |
| Identidade do revisor divergente da fixture | etapa de StoryPackage fica `blocked`; não há preview nem gate. |
| Direitos `pending` | a composição registra `media_rights_gate=FAIL` e para antes de renderizar preview/gate. |
| Direitos bloqueados/revogados | `blocked` também falha no mesmo gate. O contrato A4 não reconhece `revoked`; o ensaio usa o estado existente `blocked`, sem inventar um novo estado de direitos. |
| Plano adulterado com hash recalculado e plano antigo após nova revisão | `editorial_order_and_sequence` reprova a ordem indevida; `story_revision_current` reprova o plano que aponta ao hash anterior. |
| Interrupção após checagem factual persistida | ao reabrir o Store, a execução retoma; as etapas confirmadas continuam uma vez cada e a cadeia termina sem publicação. |
| Falha transitória em `visual_needs` | a tarefa fica em `retry_wait` na tentativa 1; após o atraso mínimo, o mesmo ID termina `succeeded` na tentativa 2; etapas anteriores não são duplicadas. |

As falhas permanecem registradas no ledger único `agent_tasks`/`agent_task_events`. Em todos os casos bloqueados não há avanço indevido ao preview ou ao gate; os cenários retomados continuam com `published=false` e zero chamadas externas.

## Validação executada

Ambiente: CPython 3.11.9.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory -v` — 8/8 OK em 17,922 s.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_layout -v` — 14/14 OK em 4,388 s; inclui a ordem/sequência re-hashada.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_editorial -v` — 17/17 OK em 10,632 s.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_orchestration.AgentOrchestrationTests.test_retryable_failure_waits_then_resumes_with_next_attempt -v` — 1/1 OK em 0,378 s.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_orchestration -v` — 34/34 OK em 19,561 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.

Na primeira execução do módulo de orquestração, 33/34 passaram: `test_retryable_failure_waits_then_resumes_with_next_attempt` esperou `idle`, mas a espera real de um segundo podia vencer antes da asserção. O teste foi tornado determinístico comparando um instante explícito imediatamente anterior a `available_at`; o caso isolado e a repetição completa passaram. A lógica de produto não foi alterada nesse ajuste.

## Limites

Os controles de divergência/direitos são fixtures e injeções locais de teste; não classificam direitos de obras reais nem aprovam conteúdo. Os testes SIWC do módulo de orquestração usam fixtures/transports offline; nenhuma chamada real Plus/SIWC, API paga, publicação ou deploy foi feita.
