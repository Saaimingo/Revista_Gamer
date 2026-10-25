# ENG-CODEX-007 E15 — E2E multipauta Radar + fábrica

**Status:** implementado e validado localmente em branch/PR draft; não mesclado.

## Entrega

`run_factory_multipauta_demo()` compõe duas ou três pautas com uma única `AgentQueue` e um único `TaskDispatcher`. `run_factory_demo()` aceita esse contexto compartilhado e valida `ResearchPacket.v1`, seus hashes e o vínculo explícito de cada documento Radar a uma fonte do pacote editorial. `FACTORY_TASK_ROUTES` registra as tarefas determinísticas da fábrica quando o dispatcher também aplica o `AgentRoleCatalog`.

O relatório multipauta distingue pauta bloqueada, corrigida, prévia retida para decisão humana e prévia aprovada apenas pelo gate simulado. Um `TaskFailure` de uma pauta fica registrado e não impede o processamento das outras. Repetir o lote após reinício reutiliza as chaves idempotentes e mantém a mesma lista de tarefas.

## Ensaio integrado

O teste `motor_editorial/tests/test_factory_multipauta.py` usa um RSS servido por transporte falso, documentos `.invalid`, `RadarStore` temporário, `ResearchService` somente de índice e papéis determinísticos. `RadarGeneralService` cria um `DiscoveryBatch` e a tarefa de triagem; o fluxo E13 executa a investigação, pesquisa local, handoff do `ResearchPacket` e continuação; o mesmo ledger e dispatcher então executam os handoffs E14 até a fábrica/layout.

Três casos foram exercitados:

- Rumor fictício em `hold`: bloqueado antes de criar pacote de reportagem ou prévia.
- Especificação fictícia de hardware: revisão solicitou correção, houve novo hash/revisão, nova checagem e nova revisão; a prévia interna ficou retida no gate simulado.
- Mod fictício: passou pelos handoffs, direitos, composição e renderização; a prévia foi aprovada apenas pelo gate sintético interno.

O teste fecha e reabre os stores, executa `resume_completed_routes()` duas vezes e repete o lote. IDs e resultados das tarefas permanecem iguais, sem duplicação ou chamada de rede. O transporte falso foi chamado uma vez para entregar a fixture; nenhum socket HTTP foi aberto.

## Validação observada

- CPython 3.11.9 (`.venv`): `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory motor_editorial.tests.test_factory_multipauta motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_radar_triage -q` — **18/18 OK em 41,767 s**.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **195/195 OK em 132,041 s**.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` e `git diff --cached --check` passaram; Git informou apenas a normalização LF→CRLF do Windows.
- No commit-base da missão `4de16640e67bd16c61468955e96e4ffa850d4cab`, foram contados 95 métodos de teste. 94 nomes permanecem iguais. O teste de migração v5 foi atualizado/refatorado para `test_v3_migration_preserves_records_and_backup_restores_the_legacy_database`, que continua verificando `agent_tasks`, `agent_task_events`, `agent_schedules`, `lease_owner` e `lease_generation`, agora no schema atual. A suíte integral executou esse conjunto mantido/atualizado e passou.

## Limites e reprodução

O teste usa fixtures e SQLite temporário. Não houve coleta externa, provider, LLM, SIWC/Plus, API paga, banco runtime, scheduler de produção, publicação, deploy ou merge. A decisão `simulated_approved_internally` não é aceite editorial ou humano. `published=false`.

Reprodução focada:

```powershell
& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory_multipauta -v
```

Código e teste: commit `25003e5557cda08af2012a9d629730982a4f0124`. Handoffs E15 em Issue #28 e PR #30 e a confirmação de seus IDs serão registrados no checkpoint após o push deste relatório.
