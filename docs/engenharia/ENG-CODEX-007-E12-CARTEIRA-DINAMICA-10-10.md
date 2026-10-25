# ENG-CODEX-007 E12 — Carteira dinâmica 10 + 10

- **Setor responsável:** Engenharia
- **Identificador:** ENG-CODEX-007-E12
- **Versão:** 0.1
- **Status:** validado localmente
- **Data:** 2026-10-25
- **Dependências:** [Issue #28](https://github.com/Saaimingo/Revista_Gamer/issues/28), ordem E01–E19 na [PR documental #29](https://github.com/Saaimingo/Revista_Gamer/pull/29), RadarStore e filas existentes
- **Aprovador:** Direção, pela ordem autorizada na Issue #28

## Objetivo

Manter candidatas por tópico e edição em uma carteira com dez posições principais e dez reservas por padrão. A etapa organiza IDs e metadados no Radar existente; ela não cria automaticamente vinte matérias, `story_id`, tarefas de redação, uma segunda fila ou um segundo despachante.

## Implementação

- `motor_editorial/radar_portfolio.py` adiciona `RadarPortfolioService` e `RadarPortfolioPolicy`. A política padrão é 10 + 10; o limite fica versionado e pode ser ajustado por configuração. A ordenação usa somente prioridade numérica informada, data de criação e ID estável como desempate. O serviço não infere valor editorial.
- O upsert é idempotente por `(topic_id, edition_id)`, atualiza os mesmos candidatos e registra eventos append-only. Tópicos não duplicam na carteira da edição. Candidatas fora dos dois grupos ficam em `monitoramento`; descartes continuam no histórico.
- O Radar migra aditivamente da versão 6 para a 7. Candidatas ganham estado de avaliação (`eligible`, `blocked`, `needs_evaluation`) e trava de membro; eventos ganham tipo e estados anterior/novo. A migração conserva os registros e eventos existentes.
- Eventos materiais persistidos de observação de fonte e de alegação/rumor reabrem a avaliação da candidata ligada ao tópico e preservam o evento original. `reactivate_for_material_evidence` valida o vínculo e reequilibra a carteira. Pautas bloqueadas sem vínculo ativo saem das posições e não impedem as demais de ocupar os espaços disponíveis.
- Uma candidata com `story_id` ou trava de membro não muda de posição por reordenação automática. `authorize_swap` exige uma evidência declarada de aprovação com escopo `edition_membership_change`, registra-a nos eventos e mantém as posições fixas. Esse contrato valida e audita o registro fornecido; não autentica o aprovador. A autenticação e o gate de produção pertencem à integração posterior.

## Aceite e validação

CPython 3.11.9, `.venv` do repositório, Windows:

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_portfolio -q` — **26/26 OK em 15,775 s**.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **185/185 OK em 117,425 s**.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.

As fixtures cobrem a carteira 10 + 10 sem reportagens, unicidade e atualização, promoção por prioridade fornecida, bloqueio isolado, reativação por mudança de fonte e alegação, autorização auditável de troca, proteção de membros existentes e migração v6 → v7. Os bancos usados são temporários. A primeira execução focada encontrou três defeitos de fixture/validação de credencial/acesso a `sqlite3.Row`; foram corrigidos antes da execução final aprovada.

## Limites e pendências

Nenhuma fonte pública, inferência, SIWC/Plus, API paga, banco runtime, scheduler de produção, publicação, deploy ou merge foi usado. A E13 ainda deve conectar pedidos de pesquisa e avaliações às tarefas da `AgentQueue`/`TaskDispatcher` existente. O registro de aprovação usado pelo swap é auditável, mas sua autenticidade não foi testada nem implementada nesta unidade.

## Commits e handoff

- Código/testes: `6b8a2cb8f2e12f662932ca2701cd52474d17c890`.
- Checkpoint de retomada da validação: `3636ae4c9952b7b732d2089c90d0a9963a421e06`.
- Checklist, comentário de Issue, comentário de PR e checkpoint final serão vinculados após a sincronização documental.
