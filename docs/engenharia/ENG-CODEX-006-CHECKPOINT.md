# ENG-CODEX-006 — checkpoint de continuidade

Atualizado: 2026-10-23 23:49 America/Sao_Paulo
Unidade: **A0 — inventário concluído**
Próxima unidade: **A1 — C-005-1, ordem editorial e `sequence`**

## Estado confirmado

- Issue #23 aberta: [ENG-CODEX-006](https://github.com/Saaimingo/Revista_Gamer/issues/23). A diretriz de execução contínua é o comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359). Escopo restrito a execução offline/simulada/local; sem SIWC/Plus, API paga, terceiros reais, publicação, deploy, despesas ou merge na `main`.
- Branch ativa `codex/eng-codex-005-offline-layout`; HEAD local/remoto observado `55eda8cd2c4006c66a4cc50c021aa4532a111d76`. PR #18 aberta, base `main`, sem merge, `mergeable=true`; parecer original [6378715359?](https://github.com/Saaimingo/Revista_Gamer/pull/18#issuecomment-6306223656) pede C-005-1/2/3 antes do aceite.
- PR #8 aberta, `mergeable=false`; head local `962dcd4`, base `main`. PR #10 aberta, head local `3702789`, base empilhada na branch da #8; `mergeable=true`. Não mesclar nenhuma PR.
- `main` remoto verificado via GitHub API em `ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; o `origin/main` local ainda está em `b44daf115bc33bfb5e4f3bb24b866fc43efd724d`. O commit novo é o backup de continuidade do Fundador. Li `docs/governanca/BACKUP-CONTINUIDADE-FUNDADOR-2026-10-23.md` no `main` remoto; o arquivo ainda não existe neste checkout/branch. Não atualizar ou mesclar `main` implicitamente.
- Issue #17 permanece aberta. Issue #20 permanece aberta e a memória editorial continua fora desta implementação; D0–D2 desta missão são somente levantamento/mapa e handoff.
- Não há checkpoint anterior de ENG-CODEX-006. `git status --short --branch` mostrou apenas `?? .venv/`; preservar e não incluir esse diretório em commits.
- `docs/governanca/STATUS-GERAL.md` tem data-base 2026-10-19 e não reflete as Issues recentes; para esta missão prevalecem o estado vivo do GitHub e a Issue #23.

## Trabalho e validação

- A0: conferidos estado de branches locais, PRs #18/#8/#10, issue #23, parecer original do Fundador na PR #18, Issues #17/#20 e backup remoto indicado pela diretriz.
- Comandos locais de inventário: `git status --short --branch`; `git branch -avv`; `git merge-base HEAD origin/main`; `git rev-parse HEAD origin/codex/eng-codex-005-offline-layout origin/main main`.
- Testes nesta unidade: não aplicáveis/não executados; nenhuma alteração de código foi feita ainda.
- Arquivos alterados nesta unidade: este checkpoint. Commit e push do checkpoint inicial ainda pendentes.

## Próxima ação exata

Inspecionar `motor_editorial/layout/contracts.py`, `motor_editorial/layout/engine.py` e os testes de layout para localizar como `StoryPackage.v0` ordena blocos e como `validate_plan()` valida `LayoutPlan.v0`; reproduzir o caso adulterado com hashes recalculados. Encerrar A1 somente com validação da ordem editorial e teste negativo que re-hasheie o plano adulterado.

## Retomada segura

Antes de qualquer edição: `git status --short --branch`; confirmar branch e HEAD; manter `.venv/` fora do stage. Se interrompido, ler este arquivo, comparar o HEAD/PR com o estado remoto atual e continuar da próxima ação acima; não repetir A0 nem assumir que testes antigos foram executados neste HEAD.
