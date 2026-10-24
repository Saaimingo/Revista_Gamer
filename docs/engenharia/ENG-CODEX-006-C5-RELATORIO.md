# ENG-CODEX-006 — C5: entrega executável ponta a ponta

Data: 2026-10-24 17:50 America/Sao_Paulo

Status: **C5 concluída em branch experimental; sem aceite editorial ou merge.**

Branch: `codex/eng-codex-006-e2e-experiment`  
PR: [#26](https://github.com/Saaimingo/Revista_Gamer/pull/26), draft.

## Execução reproduzível

Ambiente observado: CPython 3.11.9. Dados, prévias HTML e relatórios CLI foram gravados em diretórios separados de `%TEMP%`, fora do repositório. Ambos os comandos usam a fixture sintética padrão.

```powershell
& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\rg-eng-codex-006-c5-pass-20261024" factory-demo --run-id codex-006-c5-pass --review-flow pass
```

Resultado observado: exit 0; `simulated_approved_internally`; 15/15 tarefas `succeeded`; ledger `agent_tasks/agent_task_events`; `CompositionValidation=PASS` com 22 checks; `publication_state=not_published`; `published=false`; `network_calls=0`, `siwc_calls=0`, `paid_api_calls=0`.

```powershell
& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\rg-eng-codex-006-c5-revise-20261024" factory-demo --run-id codex-006-c5-revise --review-flow revise
```

Resultado observado: exit 0; 18/18 tarefas `succeeded`; correção seguida de checagem factual e revisão final; `StoryPackage.v0` revisão 2; `reviewed_revision_stage=correction`; hash inicial `5e214c149bcbb84c81997ca91ac352785efeb5e3dc925c696a275ea45eb232b6` e hash corrigido `44999188d1986f36511b28bf5f5684867e82db7afaa4d7ba5a264533c86077d8`; validação PASS com 22 checks; zero chamadas externas; `published=false`.

Relatórios CLI observados em `%TEMP%`:

- `C:\Users\saimi\AppData\Local\Temp\rg-eng-codex-006-c5-pass-20261024\artifacts\factory-demo\codex-006-c5-pass\factory-demo-report.json`
- `C:\Users\saimi\AppData\Local\Temp\rg-eng-codex-006-c5-revise-20261024\artifacts\factory-demo\codex-006-c5-revise\factory-demo-report.json`

## Validação

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_orchestration.AgentOrchestrationTests.test_dispatcher_heartbeat_keeps_long_executor_owned_past_ttl -v` — 1/1 OK em 10,985 s após tornar explícita a renovação observada.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — 95/95 OK em 76,150 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.

As duas primeiras execuções da suíte completa após C4 reportaram o mesmo caso de timing em `test_dispatcher_heartbeat_keeps_long_executor_owned_past_ttl`: com TTL de 3 segundos e espera fixa de 3,4 segundos, a tarefa concorrente podia ser retomada como `queued`. O teste agora usa TTL de 6 segundos, confirma que o loop real do heartbeat registrou uma renovação bem-sucedida e tenta uma segunda reivindicação num instante explícito 100 ms após o vencimento do lease original. A extensão emitida pelo heartbeat ainda está vigente nesse instante, e a execução principal termina `succeeded`. O código de produto não mudou.

## Limites

Artigos, fontes, identidades, perfis, decisões e mídias são sintéticos. Os testes de interface usam apenas servidores loopback. `simulated_approved_internally` é resultado de fixture e não é aprovação humana real. Não houve chamada SIWC/Plus real, API paga, serviço remoto, custo, publicação ou deploy.

C5 entrega comandos e resultados reproduzíveis, fixture, relatórios da cadeia e limites da simulação. O ensaio não substitui nem declara integrada a estética do leitor v0.3 do Bloco 03.
