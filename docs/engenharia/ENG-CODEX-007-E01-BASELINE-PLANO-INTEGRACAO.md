# ENG-CODEX-007 — E01: baseline e plano de integração

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E01
- **Versão:** v0.1
- **Status:** validado localmente; aguarda revisão na PR de implementação
- **Data:** 2026-10-25 13:19 America/Sao_Paulo
- **Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28); pacote documental [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29), HEAD `7072655d44602e83d8bc2dbdd87d08391b711ad0`; [Issue #23](https://github.com/Saaimingo/Revista_Gamer/issues/23) e aceite do handoff D0–D2 na [PR #26](https://github.com/Saaimingo/Revista_Gamer/pull/26).
- **Responsável pela execução e validação local:** Codex. Nenhum aceite de merge ou produção é declarado.

## Resultado

E01 concluiu o inventário da linha de engenharia, identificou a base candidata e executou a suíte baseline em uma branch de implementação separada. A ponta escolhida é o HEAD acumulado da PR #26, que contém as dependências #24 → #25 → #26. A documentação da direção na PR #29 foi lida pelo ref explícito e permanece intacta.

## Branches, PRs e estado remoto observado

| Item | Base / HEAD observado | Estado observado em 2026-10-25 |
| --- | --- | --- |
| `origin/main` | `ce8f6a7b65c2050d5da851491c9c89835f82c3a2` | remoto atual; PRs antigas ainda não integradas |
| PR #24 — B1 | `main@ce8f6a7` → `3bf9f6442f044d2ae1b50f033a36ebfd7e2e8644` | aberta, draft, sem merge |
| PR #25 — B2/B3 | branch #24 `3bf9f64` → `fa6eecf3e1e2f8662b5f5b53376f245df36c6785` | aberta, draft, sem merge |
| PR #26 — C0–D2 | branch #25 `fa6eecf` → `4de16640e67bd16c61468955e96e4ffa850d4cab` | aberta, draft, sem merge; um parecer `COMMENTED` do Fundador 2, favorável ao encerramento de A0–D2 com ressalvas; não é aprovação de merge |
| PR #8 / #10 | `#8@962dcd4` / `#10@3702789` | abertas; #8 conflita com a base antiga `main@d9fbb6e`; #10 continua empilhada sobre #8 |
| PR #18 | `ab7d11f` sobre a base antiga `main@b44daf1` | aberta, sem merge |
| PRs #13 / #14 / #19 / #27 | `3d651fe` / `4b1b99c` / `21381c0` / `d38c5da` | abertas, sem merge; documentação e ativos dos personagens continuam em seus próprios branches |
| Issue #28 / PR #29 | issue aberta; documentação `7072655d` sobre `main@ce8f6a7` | missão E01–E19 autorizada; PR #29 é draft documental, separada da PR de produto |

A PR #26 tem um parecer formal com estado GitHub `COMMENTED`, não `APPROVED`. Seu conteúdo aceita o handoff técnico de ENG-CODEX-006 em revisão documental, reconhece limitações da fábrica multipauta integrada e mantém gates separados de merge, produção e publicação. A ordem E01–E19 também aparece no comentário mais recente da PR #26 e no handoff da PR #27. Nenhuma das PRs acima foi mesclada.

A branch `codex/eng-codex-007-factory-radar` parte de `4de16640e67bd16c61468955e96e4ffa850d4cab`, ponta da PR #26. O primeiro commit da missão é `aeb7b5cdd132aed041a9fe7301c656f810389a31`, enviado e sincronizado com `origin/codex/eng-codex-007-factory-radar`. A PR draft [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30) usa a branch da #26 como base e segue aberta/sem merge. O handoff E01 está na [Issue #28, comentário 6400102493](https://github.com/Saaimingo/Revista_Gamer/issues/28#issuecomment-6400102493) e na [PR #30, comentário 6400102870](https://github.com/Saaimingo/Revista_Gamer/pull/30#issuecomment-6400102870).

`git rev-list --left-right --count origin/main...origin/codex/eng-codex-006-e2e-experiment` retornou `0 53`; `git merge-tree --write-tree origin/main origin/codex/eng-codex-006-e2e-experiment` terminou sem conflito, árvore candidata `68a1223f97e4d1e499346ba52c1054698eb60cbf`. Isso identifica uma base acumulada verificável; não declara que #24–#26 estão integradas à `main`.

## Componentes existentes a reutilizar

| Área | Evidência no HEAD #26 | Diretriz E01 para a próxima etapa |
| --- | --- | --- |
| Fila / despacho | `motor_editorial/orchestration.py`: `AgentQueue` persiste no `Store`; `TaskDispatcher` valida perfil e hash, usa lease/heartbeat/fencing e um mapa único de executores | adicionar contratos/papéis ao dispatcher existente; não criar fila, ledger ou orquestrador paralelo |
| Fábrica offline | `motor_editorial/factory.py`: `run_factory_demo()` cria uma fila e um `TaskDispatcher`, registra `SyntheticFactoryExecutor`, executa estágios editoriais, direitos, `StoryPackage`, layout, prévia interna e gate simulado | preservar o caminho sintético para regressões; integrar por contratos e tarefas duráveis |
| SIWC / editorial | `motor_editorial/siwc.py`: `CredentialStore`, `SIWCClient` e `SIWCExecutor`; `motor_editorial/editorial.py`: `SIWCEditorialExecutor` para estágios editoriais versionados e gate humano; `orchestration_cli.py` expõe `siwc status/models` e `editorial run` | reutilizar OAuth/adaptadores existentes. Nenhum login, `status/models`, probe ou inferência foi executado nesta unidade |
| Layout | `motor_editorial/layout/` fornece contratos, índice e render determinístico; o runner legado `run_layout_demo()` usa o fluxo `Workflow`/`execution_attempts` | conservar a única trilha E2E baseada em `agent_tasks`/`agent_task_events`; não chamar o runner legado como segundo ledger |
| SQLite | `motor_editorial/db.py` declara `SCHEMA_VERSION=5` e 17 tabelas no D0; o relatório D0 documenta um runtime local v4 observado antes, somente em leitura | usar schema/banco de teste isolado em E04; nenhum runtime real ou migração foi acessado aqui |
| Personas | PR #13 (Carranca), #19 (Beto/Nina), ativos em #14 e handoff consolidado em #27; matrizes T01–T16 ainda não executadas segundo os handoffs | não alterar nomes, DNA, imagens ou audições; E18/E19 medem P e J em trilhas separadas |

O arquivo `motor_editorial/runtime/motor.sqlite3` existe (221184 bytes; última gravação observada em 2026-10-19 20:04:54 UTC). Não foi aberto nem consultado. A suíte abaixo usa diretórios temporários nos testes de Store, conforme inspeção dos testes; não há evidência de alteração do arquivo runtime.

## Validação executada

- Ambiente: `.venv`, CPython 3.11.9.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **95/95 OK**, 65,982 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git merge-tree --write-tree origin/main origin/codex/eng-codex-006-e2e-experiment` → sem conflito.
- `git ls-files -u` → vazio antes de abrir a branch de implementação.
- Nenhuma chamada SIWC/Plus, API paga, coleta externa, migração, publicação ou deploy foi executada. `published=false`.

## Bloqueios e próximo passo

Sem bloqueio para E02. Os gates futuros continuam separados: acesso a fontes só segundo políticas permitidas; coleta externa controlada em E16; SIWC local em E17 somente após preflight, elegibilidade e consentimento aplicável, sem fallback; aprovação editorial/publicação e merge continuam humanos e fora desta ordem.

**Próxima ação exata:** E02 — implementar schemas versionados e validáveis para `AgentRoleProfile`, `AgentTaskEnvelope`, `AgentResultEnvelope` e `ResearchRequest/Packet`, com hash/catálogo, integrados aos contratos atuais sem duplicar DNA, seguido dos testes negativos definidos no pacote PR #29.

## Fontes e limites

- Ordem executável: [Issue #28](https://github.com/Saaimingo/Revista_Gamer/issues/28), comentário de handoff da PR #27 e pacote documental da [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29).
- Base de código e reports: branches/PRs #24, #25 e #26; [C0](ENG-CODEX-006-C0-CONTRATOS.md), [D0](ENG-CODEX-006-D0-MAPA-SCHEMA-MEMORIA.md), relatórios C2–C5/D0–D2 e código nos caminhos referidos acima.
- E01 não implementa agentes funcionais, Radar, conectores, coleta, agenda, chamada SIWC nem mudanças aos DNAs.
*** Add File: docs/engenharia/ENG-CODEX-007-CHECKPOINT.md
# ENG-CODEX-007 — checkpoint de continuidade

Atualizado: 2026-10-25 13:19 America/Sao_Paulo
Última unidade: **E01 — baseline e plano de integração, concluída/validada localmente**
Próxima unidade: **E02 — schemas versionados de agentes e pesquisa**

## Estado do trabalho

- Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28) autoriza a sequência E01–E19 em branch de implementação e PR draft. A [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29) é somente o pacote documental do Fundador 2; foi lida pelo ref `7072655d44602e83d8bc2dbdd87d08391b711ad0` e não foi alterada.
- Branch de produto: `codex/eng-codex-007-factory-radar`, criada a partir do HEAD acumulado da PR #26, `4de16640e67bd16c61468955e96e4ffa850d4cab`. O upstream e a PR de implementação ainda serão registrados após o primeiro push.
- PRs #24 → #25 → #26 continuam abertas/draft/sem merge. #26 recebeu review `COMMENTED` favorável ao handoff A0–D2 com ressalvas; não é aprovação de merge. `origin/main=ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; a cadeia acumulada está 53 commits à frente e `merge-tree` local não detectou conflitos.
- PRs #8/#10/#18 e #13/#14/#19/#27 continuam independentes e sem merge. Consultar E01 para os HEADs e responsabilidades por componente.

## Evidências E01 executadas nesta sessão

- CPython 3.11.9: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → 95/95 OK em 65,982 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git merge-tree --write-tree origin/main origin/codex/eng-codex-006-e2e-experiment` → sem conflito, árvore `68a1223f97e4d1e499346ba52c1054698eb60cbf`.
- `motor_editorial/runtime/motor.sqlite3` foi apenas localizado por metadados; não foi aberto nem consultado. O D0 contém observação histórica em modo somente leitura (runtime v4; schema do código v5).
- Sem chamadas SIWC/Plus, APIs pagas, fontes externas, migração, publicação ou deploy; `published=false`.

## Arquivos e commits

- Relatório E01: `docs/engenharia/ENG-CODEX-007-E01-BASELINE-PLANO-INTEGRACAO.md`.
- Checkpoint: `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md`.
- HEAD de base: `4de16640e67bd16c61468955e96e4ffa850d4cab` (PR #26). Commit de E01 e push pendentes.
- PR de implementação draft será aberta com base na branch `codex/eng-codex-006-e2e-experiment`, mantendo PR #29 documental separada.

## Bloqueios e retomada

Não há bloqueio atual. Não retomar ou reexecutar C2–D2; eles foram entregues na PR #26 e receberam parecer favorável de encerramento com ressalvas. O próximo passo é concluir o commit/push e a PR draft desta unidade E01, registrar evidências na Issue #28 e PR de implementação, depois iniciar E02.

Se houver interrupção após o push, conferir primeiro `git status --short --branch`, upstream e HEAD remoto; depois verificar PR/Issue #28 e seguir para E02. Não editar a branch/documentação da PR #29, não reconstruir o motor/OAuth/DNAs e não acessar o banco runtime real.
