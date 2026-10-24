# ENG-CODEX-006 — C2: fluxo de correção

Data: 2026-10-24 17:18 America/Sao_Paulo

Status: **C2 concluída em branch experimental; sem aceite editorial ou merge.**

Branch: `codex/eng-codex-006-e2e-experiment`

PR: [#26](https://github.com/Saaimingo/Revista_Gamer/pull/26), draft, sem merge.

## Comportamento demonstrado

O fluxo `revise` inicia com uma revisão ligada ao hash do rascunho, produz correção textual diferente, executa nova checagem factual e revisão final, e converte a correção na revisão 2 de `StoryPackage.v0`. O pacote recebe novos IDs de bloco, hashes, plano, validação e arquivo de prévia. O gate verifica que a validação e a prévia apontam para o hash atual da matéria. Reapresentar a prévia da revisão anterior ao gate da revisão 2 é rejeitado com `factory_story_revision_mismatch`.

A fila continua sendo `agent_tasks`/`agent_task_events`, com um `TaskDispatcher` por execução. Não há uso do runner A4 que escreveria no ledger concorrente `execution_attempts`.

## Evidência CLI reproduzível

Ambiente: CPython 3.11.9. Comando executado:

```powershell
& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\rg-eng-codex-006-c2-cli-proof" factory-demo --run-id codex-006-c2-cli-proof --review-flow revise
```

Saída observada: exit 0; `task_count=18`; todas as etapas `succeeded`; `simulated_approved_internally`; `StoryPackage.v0` revisão 2; `reviewed_revision_stage=correction`; `CompositionValidation` PASS com 22 checks; `published=false`; `network_calls=0`, `siwc_calls=0`, `paid_api_calls=0`.

Hashes observados nesta execução:

| Artefato | SHA-256 |
| --- | --- |
| Revisão inicial do artigo | `5e214c149bcbb84c81997ca91ac352785efeb5e3dc925c696a275ea45eb232b6` |
| Artigo corrigido e revisão final | `44999188d1986f36511b28bf5f5684867e82db7afaa4d7ba5a264533c86077d8` |
| Envelope `StoryPackage.v0` | `21eab1989fcb58e70ebe2c07467fd05b9438d2c96c6a902cbe4dc68b33488ff1` |
| Revisão da matéria no pacote | `e0b77c4834997262bb72464a1c58c20257144f25869a2835f9e9946c40cddae1` |
| `LayoutPlan.v0` | `131afc3c1b9a7d084bc5b7097a13a6c3c76e80b67189f26ea4ca4bbdeb58ba0b` |
| `CompositionValidation.v0` após render | `58958b8daf57e83045e1328f800c93ef493ee5664977a348a69d734c3fee6484` |
| HTML da prévia interna | `324df311b4dc9d55b4c792c4b07db3bc9fd9d98aeda3eb35a39e39cf2e4ae760` |

Os resultados e a prévia foram gravados em `%TEMP%`, fora do repositório. A execução CLI foi isolada da fixture de C1; o teste automatizado também executa C1 e depois `revise` no mesmo `run_id`, conferindo que IDs de tarefa, pacote, plano, prévia e gate antigos não viram artefatos correntes.

## Validação

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory.SyntheticFactoryTests.test_revise_flow_creates_new_revision_and_never_reuses_old_preview_or_gate -v` — 1/1 OK.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory -v` — 8/8 OK; inclui os cenários negativos iniciados em C3, cujo fechamento é registrado separadamente.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.

## Limites

Textos, fontes, perfis e placeholder são fictícios. `simulated_approved_internally` é somente a decisão da fixture e não representa aceite humano real, aprovação editorial da direção ou publicação. Não houve rede, SIWC/Plus, API paga, despesas, deploy ou alteração de edição real.
