# ENG-CODEX-007 E19 — trio na fábrica, validação offline

**Estado:** `PARTIAL_OFFLINE_ONLY / REAL_EVALUATION_NOT_EXECUTED`  
**Data:** 2026-10-25 20:17 -03:00  
**Branch:** `codex/eng-codex-007-factory-radar`  
**PR da missão:** [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), aberta, draft e sem merge.

## O que foi exercitado

O teste integrado E15 foi ampliado para enfileirar três tarefas `persona_writer` na mesma instância de `AgentQueue`, usando o mesmo `TaskDispatcher` e ledger SQLite temporário que acabaram de executar o ensaio multipauta Radar/fábrica. As três tarefas apontam para a mesma pauta/edição fictícia, compartilham o mesmo brief, dossier e `ResearchPacket` sintético de pesquisa complementar, e têm `input_payload_hash` idêntico. Cada envelope mantém seu próprio `persona_id` e hash de marcador sintético.

O `TaskDispatcher` recebeu o novo parâmetro opcional `persona_instruction_resolver`, invocado somente para `persona_writer`. Os três despachos concluíram no executor determinístico de teste e cada contexto confiável continha uma única seção `persona:<id>` com o marcador daquele envelope; o packet compartilhado permaneceu no campo separado de evidência não confiável. Não se produziu artigo ou `StoryDraft`, não se avaliou estilo e não se usou texto real de DNA. O resultado `succeeded` significa somente que o contrato/ledger processou o envelope sintético.

Três casos negativos também ficaram no mesmo ledger:

- sem resolvedor configurado, a tarefa foi bloqueada como `agent_contract_invalid` antes de chamar o executor;
- resolvedor que devolve o marcador de outra persona foi bloqueado pelo hash do envelope;
- exceção do resolvedor foi convertida em bloqueio da tarefa, sem deixá-la reclamada e sem chamar o executor.

O teste repetiu o replay do pipeline multipauta após incluir as tarefas do trio. Os IDs/resultados permaneceram estáveis e nenhuma tarefa adicional foi criada. A pesquisa de base veio do packet local que usa transporte/fixture sintéticos `.invalid`; E19 não abriu rede, não consultou fonte pública e não chamou modelo/provedor.

## Limite de conclusão

Este ensaio valida a injeção e o isolamento contratual do papel dentro do ledger/dispatcher compartilhado. Ele não substitui o executor sintético da etapa editorial E14 pelo redator real nem prova que uma saída `StoryDraft` preserve a identidade durante a esteira. As matrizes T01–T16 continuam `not_executed` para os três jornalistas (**0/48 casos**); P e J continuam `not_evaluated`; revisão humana `pending_direction`.

A cota Plus em 100% não remove a proibição de SIWC/Plus real já registrada pelo usuário. E17 permanece `BLOCKED_BY_SCOPE`; E18 e E19 ficam parciais offline. Nenhuma consulta de conta/modelo, login, probe, inferência, credencial, gasto, fallback pago ou API faturável foi usada. Nada foi mesclado, publicado ou implantado; `published=false`.

## Validação e entrega

CPython 3.11.9 no `.venv`:

- Foco integrado: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory_multipauta motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_persona_trials_offline -q` — **24/24 OK em 7,620 s**.
- Suíte integral serial: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **198/198 OK em 141,677 s**.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0; Git apenas avisou sobre normalização LF→CRLF no teste alterado.

Código e teste integrados enviados no commit `d804e7c` (`test: route isolated personas through shared factory ledger`). O relatório e checkpoint registram os limites de E17–E19. DNAs, matrizes aprovadas, amostras e ativos visuais não foram editados ou copiados; banco runtime, scheduler e workers não foram usados.

## Próximo passo e situação final

As unidades offline tecnicamente possíveis foram executadas. E17 segue bloqueada; E18/E19 permanecem parciais aguardando, respectivamente, a avaliação isolada real e a avaliação real integrada P/J, que não podem ser alegadas com marcadores sintéticos. O handoff final da missão deve manter as caixas E17/E18/E19 desmarcadas, relatar os limites e apontar para este relatório, o relatório E18 e o checkpoint. Sem autorização específica vigente, não realizar os testes SIWC/Plus.
