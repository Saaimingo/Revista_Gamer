# ENG-CODEX-006 — C0: mapa de contratos e integração

Data: 2026-10-24
Status: **levantamento técnico em branch experimental; sem integração na `main` e sem aceite editorial**.
Branch: `codex/eng-codex-006-e2e-experiment`
Base B2/B3: `codex/eng-codex-006-pipeline-reconcile@fa6eecf`
Dependência A4: `codex/eng-codex-005-offline-layout@ab7d11f`

## Limite da composição

O trabalho A4 foi integrado somente nesta branch C0, por dependência. PR #18, branches-fonte A4/B1/B2 e `main` continuam sem alteração. A PR #18 continua independente e sem merge; B1/B2/B3 continuam registrados nas PRs #24/#25. Esta composição é código candidato para testes offline, não declaração de que as PRs foram integradas à `main` ou aceitas pela direção.

## Contratos observados

| Etapa/artefato | Forma e validação observadas | Identidade e proveniência |
| --- | --- | --- |
| Entrada editorial B2 | Pacote limitado por `normalize_source_packet()`: `article_type`, pauta, nota e fontes com IDs únicos `S1`…; exige pelo menos dois publicadores e tipos oficial/secundário. URL HTTPS é validada como dado, sem requisição de rede. | `AgentTask` persiste `task_type`, payload, executor, `idempotency_key`, `profile_id`, versão e hash do perfil. |
| Estágios B2 | `editorial.stage`: `source_analysis`, `outline`, `draft`, `fact_check`, `review`, `correction`, `final_fact_check`, `final_review`; as saídas são estruturadas, limitadas e conferem IDs citados com o pacote. | O `TaskDispatcher` verifica o perfil disponível e seu hash antes de executar; usa lease/fencing e grava estado/resultado em `agent_tasks` e eventos em `agent_task_events`. |
| Revisão B2 | `article_revision_sha256()` cobre `headline`, `dek`, `body_markdown` e `source_ids`. A revisão inclui `reviewed_revision_sha256` e `reviewed_revision_stage`; `review_matches_revision()` exige correspondência com a versão corrente. `pass` mantém `human_review_required=true`; não aprova publicação. | O perfil `internal-controlled-editorial-experiment@1.2.0` é uma identidade técnica do executor e não uma persona pública. O hash B2 (`profile_id`, versão, instruções) não é o hash de identidade A4. |
| `StoryPackage.v0` A4 | Envelope com `artifact_id`, `schema_version`, `revision`, `content_sha256` canônico e payload estruturado: pauta/edição, `story_revision`, title/dek, sections ordenadas, IDs de fontes, identidades e revisão sintética. | `story_revision_sha256()` cobre `story_id`, revisão, title/dek, sections, source IDs e identities. A revisão do pacote precisa apontar para esse hash vigente. |
| Identidades A4 | `editor`, `writer_persona` e `reviewer` declaram `profile_id`, versão, descrição e `profile_sha256()` canônico por papel. O `LayoutPlan` repete esses IDs/versões/hashes e valida igualdade com o pacote. | O hash A4 (`role`, `profile_id`, versão, descrição) não deve ser comparado nem substituído pelo hash B2 de instruções. C1 deve usar perfis fictícios versionados e preservar separadamente a proveniência dos `AgentTask`s B2. |
| Mídia/layout A4 | `MediaInventory.v0` sela inventário e direitos; `LayoutReference.v0` admite somente metadados sintéticos; `LayoutPlan.v0` permanece `proposed`; `CompositionValidation.v0` registra cada check como PASS/FAIL. Hashes vinculam matéria, inventário, índice e referências. A ordem/sequência do plano deve refletir os blocos editoriais. | Mídia sintética usa placeholder com `synthetic=true`, `rights_status=synthetic_fixture`, `license.status=not_applicable_synthetic_placeholder` e modo `internal_preview`. `pending`, `blocked` e anúncio não passam pelo gate de prévia. |
| Aprovação/saída | Aprovação editorial `pass`, validação de composição PASS e gate humano após prévia são eventos distintos. O gate de C1 será explicitamente simulado. | Resultado permanece `approved_internally`/`awaiting_approval` conforme o ponto do ensaio e `published=false`; nenhuma aprovação sintética é prova de aprovação de direção ou publicação externa. |

## Ponte de dados a provar em C1

1. Conservar os objetos estruturados B2 e IDs de fonte; não reconstruir citações procurando texto livre. O mapeamento para `StoryPackage.sections` deve ser determinístico e sem perda: manter title/dek/body e vínculos de fontes, com `block_id`s estáveis derivados de matéria/revisão/ordem.
2. Antes de selar o pacote, exigir que a revisão B2 final corresponda ao hash do objeto de artigo corrente. Manter `article_revision_sha256` como proveniência de origem e calcular separadamente `story_revision_sha256` sobre o payload A4 traduzido. A revisão A4 requerida pelo contrato deve ser identificada como fixture sintética; nunca reutilizar o hash B2 como se pertencesse ao domínio A4.
3. Alimentar o pacote com identidades neutras e versionadas para os papéis A4, mantendo no ledger a versão/hash do perfil executor B2. Validar que o `LayoutPlan` preserva essas identidades exatamente e não anuncia uma persona real.
4. Fixar uma revisão de perfil e de conteúdo por tarefa. Após correção, usar novo hash de artigo, novo pacote/revisão, novo plano e nova prévia; objetos derivados da revisão anterior não podem passar o gate.
5. Permitir aprovação interna somente depois da CompositionValidation PASS e da prévia interna. O ensaio anota que a aprovação é simulada e não muda `published=false`.

## Dispatcher e armazenamento escolhidos

`AgentQueue` e um único `TaskDispatcher` B1/B2 serão usados por toda a cadeia C1–C4, com executores sintéticos substituíveis para etapas de agente e funções determinísticas do layout. Os resultados/eventos ficam no mesmo `Store` SQLite, nas tabelas `agent_tasks` e `agent_task_events`; chaves idempotentes incluem run, etapa e hashes de entrada.

O runner legado A4 `run_layout_demo()` chama `Workflow._execute_step()` e grava em `execution_attempts`. C1 não chamará esse runner: invocará as funções determinísticas do layout por tarefas do dispatcher compartilhado, evitando uma segunda trilha de execução concorrente. `LayoutReferenceIndex` é apenas um catálogo local de metadados, sem fila, lease ou eventos de worker. Agendamento e chamadas SIWC ficam desligados.

## Critério de saída de C0

- A4 e B1–B3 estão juntos apenas na branch experimental e os contratos acima têm ligação explícita e testável.
- O contrato e as colisões documentais estão documentados; o código fonte das branches de origem continua intacto.
- A suíte completa offline da composição passa, `compileall` passa e `git diff --check` passa antes de marcar C0 concluído.
- As provas C1–C4 podem começar usando uma única `AgentQueue`/`TaskDispatcher`, perfis neutros versionados e gate humano simulado.
