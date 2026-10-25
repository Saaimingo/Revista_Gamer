# ENG-CODEX-007 E13 — Dispatcher, dependências e pesquisa retomável

**Status:** implementada e validada localmente em 25/10/2026.
**Branch/PR:** `codex/eng-codex-007-factory-radar`, PR draft #30 aberta, sem merge.
**Issue:** [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28).
**Próxima unidade:** E14 — handoff editorial com evidências e revisões.

## Entrega

A E13 reaproveita uma única `AgentQueue` e um único `TaskDispatcher`. A migração aditiva do Motor SQLite v6→v7 cria `agent_task_dependencies`, com arestas persistentes, chaves estrangeiras e bloqueio de autorreferência. A fila só reclama tarefas quando todas as predecessoras foram concluídas; uma predecessora terminal em falha/bloqueio/incerteza/cancelamento bloqueia o dependente, enquanto tarefas independentes continuam aptas. A criação de tarefas confere idempotência também sobre o conjunto de dependências; inclusão tardia valida existência e ciclos.

O `TaskDispatcher` aceita rotas determinísticas explícitas por `task_type`/`executor_id` e um roteador de resultados após a conclusão durável. Tarefas `agent.role.*` continuam passando pelo catálogo, hash/versão, schema de entrada/saída, gate humano e fronteira entre instrução e evidência. O executor determinístico da pesquisa chama o `ResearchService` compartilhado; ele não gera texto editorial e não configura provider externo por padrão.

Quando um resultado de papel contém `ResearchRequest` v1.1, o roteador confere tarefa pai, papel, persona, artigo e revisão, enfileira pesquisa com dependência na tarefa de origem e chave idempotente. Ao concluir a pesquisa, verifica `ResearchPacket` e o resultado de origem, então cria continuação do mesmo papel/artigo, ligada à tarefa de pesquisa. O packet é anexado separadamente como evidência não confiável e sua referência/hash entra nos inputs versionados. O replay de resultados bem-sucedidos reconstitui handoffs após reinício; repeti-lo não duplica a pesquisa nem a continuação.

## Evidência observada

- CPython 3.11.9 no `.venv` do repositório.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_orchestration motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_agent_workflow -q` — **60/60 OK em 31,121 s**.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **192/192 OK em 140,515 s**, serial.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.
- A fixture E13 despachou papéis sintéticos de duas pautas no mesmo dispatcher, completou pesquisa local sem provider, retomou o `ResearchPacket` no artigo correto e simulou reinício antes dos dois handoffs. A busca local sem documentos produziu packet `not_found`; não foi tratada como evidência factual.
- As regressões também cobrem migração v6→v7, dependências em espera, bloqueio terminal, trabalho independente, ciclo, idempotência, heartbeat e fencing/lease existentes.

## Commits

- Código e testes: `6acb123` — `feat: route Radar research through durable agent workflow`.
- Higiene final do módulo: `705efc1` — `style: clean research workflow module ending`.
- Relatório, README setorial e checkpoint: registrados no commit documental desta E13.

## Limites e pendências

Os executores desta validação são sintéticos; nenhum LLM foi chamado e nenhum DNA de jornalista foi alterado. Não houve fonte pública, SIWC/Plus, API paga, banco runtime, worker/scheduler de produção, publicação, deploy ou merge. O `ResearchService` recebeu um Radar SQLite temporário vazio e permaneceu sem provider. Resultados e pacotes precisam continuar passando por gates humanos previstos no regimento; a conclusão de tarefa não publica nem aprova conteúdo.

Os bancos Motor e Radar continuam separados, portanto não há transação distribuída entre os dois arquivos. O `ResearchRequest` fica no resultado/tarefa durável da fila antes da execução, o serviço grava request/packet no Radar e o roteador reproduz handoffs por idempotência após reinício. Uma eventual falha do roteador após conclusão permanece visível como `workflow_route_pending` no resultado do dispatch e recuperável por `resume_completed_routes()`.
