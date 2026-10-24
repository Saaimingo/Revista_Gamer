# ENG-CODEX-006 — checkpoint de continuidade

Atualizado: 2026-10-23 23:51 America/Sao_Paulo
Unidade: **A1 — C-005-1, em andamento**
Última unidade concluída: **A0 — inventário**

## Estado confirmado

- Issue #23 aberta: [ENG-CODEX-006](https://github.com/Saaimingo/Revista_Gamer/issues/23). A diretriz de execução contínua é o comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359). Escopo restrito a execução offline/simulada/local; sem SIWC/Plus, API paga, terceiros reais, publicação, deploy, despesas ou merge na `main`.
- Branch ativa `codex/eng-codex-005-offline-layout`; o HEAD original era `55eda8cd2c4006c66a4cc50c021aa4532a111d76`; checkpoint A0 foi commitado como `f2f7ba3` e enviado com sucesso. PR #18 aberta, base `main`, sem merge, `mergeable=true`; parecer original [6306223656](https://github.com/Saaimingo/Revista_Gamer/pull/18#issuecomment-6306223656) pede C-005-1/2/3 antes do aceite.
- PR #8 aberta, `mergeable=false`; head local `962dcd4`, base `main`. PR #10 aberta, head local `3702789`, base empilhada na branch da #8; `mergeable=true`. Não mesclar nenhuma PR.
- `main` remoto verificado via GitHub API em `ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; o `origin/main` local ainda está em `b44daf115bc33bfb5e4f3bb24b866fc43efd724d`. O commit novo é o backup de continuidade do Fundador. Li `docs/governanca/BACKUP-CONTINUIDADE-FUNDADOR-2026-10-23.md` no `main` remoto; o arquivo ainda não existe neste checkout/branch. Não atualizar ou mesclar `main` implicitamente.
- Issue #17 permanece aberta. Issue #20 permanece aberta e a memória editorial continua fora desta implementação; D0–D2 desta missão são somente levantamento/mapa e handoff.
- Não há checkpoint anterior de ENG-CODEX-006. `git status --short --branch` mostrou apenas `?? .venv/`; preservar e não incluir esse diretório em commits.
- `docs/governanca/STATUS-GERAL.md` tem data-base 2026-10-19 e não reflete as Issues recentes; para esta missão prevalecem o estado vivo do GitHub e a Issue #23.

## Trabalho e validação

- A0 concluído: conferidos estado de branches locais, PRs #18/#8/#10, issue #23, parecer original do Fundador na PR #18, Issues #17/#20 e backup remoto indicado pela diretriz. Checkpoint inicial commitado (`f2f7ba3`) e enviado à branch da PR #18.
- A1 em andamento: `StoryPackage.payload.sections` mantém a ordem editorial e `plan_layout()` grava `sequence` 1-based; `validate_layout_plan()` atualmente só valida IDs únicos, e `validate_plan()` compara IDs como conjuntos. A regra permite reordenar blocos ou adulterar `sequence` sem falha se o envelope for re-hasheado. Ainda sem correção.
- Comandos locais de inventário: `git status --short --branch`; `git branch -avv`; `git merge-base HEAD origin/main`; `git rev-parse HEAD origin/codex/eng-codex-005-offline-layout origin/main main`.
- Testes nesta unidade: não aplicáveis/não executados; nenhuma alteração de código foi feita ainda.
- Arquivos alterados no checkpoint A0: `docs/engenharia/ENG-CODEX-006-CHECKPOINT.md`. Commit `f2f7ba3`; push para `origin/codex/eng-codex-005-offline-layout` concluído.

## Próxima ação exata

Em `motor_editorial/layout/contracts.py`, exigir `sequence` inteiro positivo e único. Em `motor_editorial/layout/engine.py::validate_plan()`, comparar ordem de `block_id`s e sequências 1-based com `StoryPackage.payload.sections`. Em `motor_editorial/tests/test_layout.py`, re-hashear separadamente um plano reordenado e outro com sequência trocada, e confirmar FAIL do check sem invalidar o envelope. Encerrar A1 quando a regressão reproduzir o defeito no baseline e passar com a correção, com teste focado e `git diff --check` limpos.

## Retomada segura

Antes de qualquer edição: `git status --short --branch`; confirmar branch e HEAD; manter `.venv/` fora do stage. Se interrompido, ler este arquivo, comparar o HEAD/PR com o estado remoto atual e continuar da próxima ação acima; não repetir A0 nem assumir que testes antigos foram executados neste HEAD.
