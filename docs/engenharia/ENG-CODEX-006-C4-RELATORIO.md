# ENG-CODEX-006 — C4: multipauta e gates de edição

Data: 2026-10-24 17:30 America/Sao_Paulo

Status: **C4 concluída em branch experimental; sem merge ou publicação.**

Branch: `codex/eng-codex-006-e2e-experiment`

PR: [#26](https://github.com/Saaimingo/Revista_Gamer/pull/26), draft.

## Comportamento demonstrado

A fixture multipauta contém três matérias: uma bloqueada pela revisão, uma elegível e uma com falha de pesquisa recuperável. A edição permanece `waiting_on_blockers`; tentar aprová-la nessa condição é rejeitado. Depois de reabrir o Store e retomar a cadeia, o trabalho concluído não é repetido e a matéria com falha recuperável chega a `media_checked`, enquanto a bloqueada continua sem elegibilidade.

A exclusão da matéria bloqueada exige ator, motivo e frase de confirmação explícita. O evento `story_excluded_from_edition` registra a decisão. Só depois disso a edição muda para `ready_for_approval`, mantém as duas matérias elegíveis no preview na ordem prevista e omite a matéria bloqueada e o ativo pendente. A exclusão não apaga a matéria do histórico. Uma regressão separada confirma que exclusões não auditadas ou inválidas são recusadas e run IDs distintos mantêm conjuntos independentes.

## Validação executada

Ambiente: CPython 3.11.9.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_workflow.MotorWorkflowTests.test_multipauta_isolates_failures_resumes_and_composes_two_ordered_articles -v` — 1/1 OK em 1,393 s.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_workflow.MotorWorkflowTests.test_multipauta_rejects_unaudited_or_invalid_exclusion_and_distinct_run_ids -v` — 1/1 OK em 2,162 s.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_workflow -v` — 22/22 OK em 25,229 s.

A suíte `test_workflow` inicia servidores loopback locais para conferir painel e preview internos. Não há requisição a serviço externo. A evidência continua sendo do Motor offline; aprovação interna nos testes não demonstra publicação.

## Limites

Todos os artigos e decisões pertencem à fixture sintética. O teste não muda banco real, não publica, não usa SIWC/Plus real, API paga, credenciais, serviço remoto ou permissão externa.
