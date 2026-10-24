# ENG-CODEX-006 — checkpoint de continuidade

Atualizado: 2026-10-23 23:56 America/Sao_Paulo
Unidade: **A3 — C-005-3, em andamento**
Última unidade concluída: **A2 — C-005-2**

## Estado confirmado

- Issue #23 aberta: [ENG-CODEX-006](https://github.com/Saaimingo/Revista_Gamer/issues/23). A diretriz de execução contínua é o comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359). Escopo restrito a execução offline/simulada/local; sem SIWC/Plus, API paga, terceiros reais, publicação, deploy, despesas ou merge na `main`.
- Branch ativa `codex/eng-codex-005-offline-layout`; A0 (`f2f7ba3`) e A1 (`bc5aecb`) commitados e enviados. A2 foi editada sobre `bc5aecb` e precisa de commit/push. PR #18 aberta, base `main`, sem merge; parecer original [6306223656](https://github.com/Saaimingo/Revista_Gamer/pull/18#issuecomment-6306223656) pede C-005-1/2/3 antes do aceite.
- PR #8 aberta, `mergeable=false`; head local `962dcd4`, base `main`. PR #10 aberta, head local `3702789`, base empilhada na branch da #8; `mergeable=true`. Não mesclar nenhuma PR.
- `main` remoto verificado via GitHub API em `ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; o `origin/main` local ainda está em `b44daf115bc33bfb5e4f3bb24b866fc43efd724d`. O commit novo é o backup de continuidade do Fundador. Li `docs/governanca/BACKUP-CONTINUIDADE-FUNDADOR-2026-10-23.md` no `main` remoto; o arquivo ainda não existe neste checkout/branch. Não atualizar ou mesclar `main` implicitamente.
- Issue #17 permanece aberta. Issue #20 permanece aberta e a memória editorial continua fora desta implementação; D0–D2 desta missão são somente levantamento/mapa e handoff.
- Não há checkpoint anterior de ENG-CODEX-006. `git status --short --branch` mostrou apenas `?? .venv/`; preservar e não incluir esse diretório em commits.
- `docs/governanca/STATUS-GERAL.md` tem data-base 2026-10-19 e não reflete as Issues recentes; para esta missão prevalecem o estado vivo do GitHub e a Issue #23.

## Trabalho e validação

- A0 concluído: conferidos estado de branches locais, PRs #18/#8/#10, issue #23, parecer original do Fundador na PR #18, Issues #17/#20 e backup remoto indicado pela diretriz. Checkpoint inicial commitado (`f2f7ba3`) e enviado à branch da PR #18.
- A1 concluído: `validate_layout_plan()` agora exige `sequence` inteiro positivo e único. `validate_plan()` verifica ordem dos `block_id`s e sequência 1-based contra `StoryPackage.payload.sections`; check emitido: `editorial_order_and_sequence`. O novo teste prova que nem a reordenação com sequências consistentes nem a troca isolada dos números passa após re-hash.
- A2 concluído: construção e validação usam `profile_sha256()` canônico; o check `source_role_identities_match_story_package` compara exatamente os papéis editor, redator/persona e revisor com os IDs, versões e hashes derivados do StoryPackage. Hash genérico da identidade com metadado adicional não é aceito como substituto do hash de perfil.
- A3 em andamento: inspecionar status de licença, `rights_status`, modos permitidos e usos existentes nas fixtures antes de restringir o contrato; impedir conflito e manter apenas os cenários sintéticos autorizados.
- Comandos locais de inventário: `git status --short --branch`; `git branch -avv`; `git merge-base HEAD origin/main`; `git rev-parse HEAD origin/codex/eng-codex-005-offline-layout origin/main main`.
- A0: nenhum teste executado (inventário apenas).
- A1 baseline: `.\.venv\Scripts\python.exe -m unittest motor_editorial.tests.test_layout.LayoutContractTests.test_rehashed_plan_must_preserve_story_order_and_sequence -v` falhou como esperado em dois casos adulterados, ambos indevidamente `PASS` no código original.
- A1 após correção: o mesmo teste focado passou (1 teste); `.\.venv\Scripts\python.exe -m unittest motor_editorial.tests.test_layout -q` passou (10 testes em 5,734 s); `git diff --check` passou.
- A2 baseline: os dois testes focados falharam como esperado; divergências de `profile_id`, versão, hash e papel ausente nos planos re-hasheados passavam antes, totalizando 11 subfalhas. Hash construído por `sha256_json(identity)` divergia do hash canônico quando havia campo extra.
- A2 após correção: `...test_plan_role_identity_hashes_use_the_canonical_profile_rule -v` passou; `...test_rehashed_plan_rejects_missing_or_divergent_source_role_identities -v` passou (10 subcasos); suíte de layout passou (12 testes em 9,253 s); `git diff --check` passou.
- Arquivos A1 alterados: `motor_editorial/layout/contracts.py`, `motor_editorial/layout/engine.py`, `motor_editorial/tests/test_layout.py`. Arquivos A2: `motor_editorial/layout/engine.py`, `motor_editorial/tests/test_layout.py` e este checkpoint. A2 ainda sem commit/push; `.venv/` permanece fora do stage.

## Próxima ação exata

Concluir A3 em `motor_editorial/layout/contracts.py::validate_media_inventory()` e `motor_editorial/layout/engine.py::validate_plan()`: mapear os estados permitidos por tipo de mídia, barrar `license.status` pendente/bloqueado quando `rights_status` afirma autorizado, validar coerência do modo `internal_preview` e não adicionar política jurídica além do necessário. Testar casos re-hasheados com os dois campos conflitantes e preservar as fixtures sintéticas válidas.

## Retomada segura

Antes de qualquer edição: `git status --short --branch`; confirmar branch e HEAD; manter `.venv/` fora do stage. Se interrompido, ler este arquivo, comparar o HEAD/PR com o estado remoto atual e continuar A3; não repetir A0–A2 nem assumir que testes antigos foram executados neste HEAD.
