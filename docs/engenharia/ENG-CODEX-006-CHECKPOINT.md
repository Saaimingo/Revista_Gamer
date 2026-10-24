# ENG-CODEX-006 — checkpoint de continuidade

Atualizado: 2026-10-24 00:06 America/Sao_Paulo
Unidade: **A4 — aceite técnico preparatório, em andamento**
Última unidade concluída: **A3 — C-005-3**

## Estado confirmado

- Issue #23 aberta: [ENG-CODEX-006](https://github.com/Saaimingo/Revista_Gamer/issues/23). A diretriz de execução contínua é o comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359). Escopo restrito a execução offline/simulada/local; sem SIWC/Plus, API paga, terceiros reais, publicação, deploy, despesas ou merge na `main`.
- Branch ativa `codex/eng-codex-005-offline-layout`, HEAD `efdc47811000a8a6183bde14d525d30a8dc6106e`, igual ao upstream da branch antes dos registros A4 desta retomada. A0 (`f2f7ba3`), A1 (`bc5aecb`), A2 (`bf2e9e3`) e A3 (`efdc478`) estão commitados e enviados. PR #18 aberta, sem merge; parecer original [6306223656](https://github.com/Saaimingo/Revista_Gamer/pull/18#issuecomment-6306223656) solicita C-005-1/2/3 antes do aceite.
- PR #8 aberta, `mergeable=false`, head `962dcd4753414d506990913238f12a6a946bcffe`; PR #10 aberta, head `37027897d8d0c1b733e2bfb87acecb7b7822d760`, empilhada sobre #8. Nenhuma está mesclada. O fetch atualiza `origin/main` para `ce8f6a7b65c2050d5da851491c9c89835f82c3a2`; a branch local `main` permanece em `d9fbb6e` (32 commits atrás). A PR #18 reporta `mergeable=true`, mas sua API ainda retorna base SHA `b44daf1`; a diferença de snapshot deve ser conferida de novo em B0. Não atualizar o checkout `main` nem mesclar PRs implicitamente.
- O backup obrigatório não existe neste checkout; foi lido via GitHub na `main` remota (`ce8f6a7`). `docs/governanca/STATUS-GERAL.md` tem data-base 2026-10-19; para status operacional prevalecem Issue/PRs atuais e refs remotas verificadas.
- Issue #17 permanece aberta. Issue #20 permanece aberta e a memória editorial continua fora desta implementação; D0–D2 desta missão são somente levantamento/mapa e handoff.
- O checkpoint de ENG-CODEX-006 está nesta branch e preserva o histórico A0–A4. `git status --short --branch` mostrou os dois documentos A4 modificados e `?? .venv/`; manter `.venv/` fora do stage.

## Trabalho e validação

- A0 concluído: conferidos estado de branches locais, PRs #18/#8/#10, issue #23, parecer original do Fundador na PR #18, Issues #17/#20 e backup remoto indicado pela diretriz. Checkpoint inicial commitado (`f2f7ba3`) e enviado à branch da PR #18.
- A1 concluído: `validate_layout_plan()` agora exige `sequence` inteiro positivo e único. `validate_plan()` verifica ordem dos `block_id`s e sequência 1-based contra `StoryPackage.payload.sections`; check emitido: `editorial_order_and_sequence`. O novo teste prova que nem a reordenação com sequências consistentes nem a troca isolada dos números passa após re-hash.
- A2 concluído: construção e validação usam `profile_sha256()` canônico; o check `source_role_identities_match_story_package` compara exatamente os papéis editor, redator/persona e revisor com os IDs, versões e hashes derivados do StoryPackage. Hash genérico da identidade com metadado adicional não é aceito como substituto do hash de perfil.
- A3 concluído: `MediaInventory.v0` agora reconhece apenas `authorized`, `pending`, `blocked` e `not_applicable_synthetic_placeholder` para `license.status`. O gate de composição permite prévia somente para placeholder sintético coerente ou mídia editorial autorizada com `internal_preview`; conflitos de status e modos faltantes falham antes do render. O slot de publicidade também exige licença autorizada e modo de prévia, mantendo a separação editorial/comercial.
- A4 em andamento: testes já foram executados no HEAD atual; relatório e checkpoint estão sendo atualizados. Faltam `git diff --check` sobre os documentos atuais, commit/push e comentário de evidências na PR #18.
- Comandos locais de inventário: `git status --short --branch`; `git branch -avv`; `git merge-base HEAD origin/main`; `git rev-parse HEAD origin/codex/eng-codex-005-offline-layout origin/main main`.
- A0: nenhum teste executado (inventário apenas).
- A1 baseline: `.\.venv\Scripts\python.exe -m unittest motor_editorial.tests.test_layout.LayoutContractTests.test_rehashed_plan_must_preserve_story_order_and_sequence -v` falhou como esperado em dois casos adulterados, ambos indevidamente `PASS` no código original.
- A1 após correção: o mesmo teste focado passou (1 teste); `.\.venv\Scripts\python.exe -m unittest motor_editorial.tests.test_layout -q` passou (10 testes em 5,734 s); `git diff --check` passou.
- A2 baseline: os dois testes focados falharam como esperado; divergências de `profile_id`, versão, hash e papel ausente nos planos re-hasheados passavam antes, totalizando 11 subfalhas. Hash construído por `sha256_json(identity)` divergia do hash canônico quando havia campo extra.
- A2 após correção: `...test_plan_role_identity_hashes_use_the_canonical_profile_rule -v` passou; `...test_rehashed_plan_rejects_missing_or_divergent_source_role_identities -v` passou (10 subcasos); suíte de layout passou (12 testes em 9,253 s); `git diff --check` passou.
- A3 baseline: os testes específicos falharam no defeito previsto (ativo com `license.status=pending`, `rights_status=authorized` e `internal_preview` indevidamente passou) e aceitaram texto arbitrário em `license.status`.
- A3 após correção: `...test_license_and_rights_status_must_match_the_preview_mode -v` passou (3 casos); `...test_unknown_license_status_is_not_accepted_by_the_contract -v` passou; módulo layout passou (14 testes em 3,642 s); `git diff --check` passou.
- Arquivos A1 alterados: `motor_editorial/layout/contracts.py`, `motor_editorial/layout/engine.py`, `motor_editorial/tests/test_layout.py`. A2: `motor_editorial/layout/engine.py`, `motor_editorial/tests/test_layout.py`. A3: `motor_editorial/layout/contracts.py`, `motor_editorial/layout/engine.py`, `motor_editorial/tests/test_layout.py` (A3 commitada em `efdc478`). `.venv/` continua não rastreada e deve permanecer fora do stage.

### A4 — resultados executados nesta retomada

- Versão: `& '.\.venv\Scripts\python.exe' --version` → Python 3.11.9.
- Focado: `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_layout -v` → 14 testes em 2,965 s, OK.
- Suíte completa: `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → 36 testes em 24,806 s, OK. A suíte anteriormente interrompida foi executada até o fim neste HEAD.
- CLI: `& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\rg-eng-codex-006-a4-7aef31f3e2584251928d4a6dc0c6654d" layout-demo` → `awaiting_approval`; `reportagem-duas-imagens`, `comparativo-consoles-spread`, `mapa-panoramico-spread` PASS; 22 checks por cenário (66/66), `network_calls=0`, `siwc_calls=0`, `paid_api_calls=0`, `published=false`. Diretório temporário local preservado em `C:\Users\saimi\AppData\Local\Temp\rg-eng-codex-006-a4-7aef31f3e2584251928d4a6dc0c6654d`.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → passou.
- `git diff --check origin/main...HEAD` → passou antes da edição dos documentos A4. Repetir `git diff --check` sobre as alterações atuais antes do commit.
- Limite: `awaiting_approval` é prévia interna pendente de revisão humana; não foi feita inspeção visual em navegador e não representa aceite do Fundador ou publicação.

## Próxima ação exata

Fechar A4: conferir os diffs de `docs/engenharia/RELATORIO-ENG-CODEX-005-FASE0-OFFLINE.md` e deste checkpoint, executar `git diff --check`, commitá-los explicitamente sem `.venv/`, fazer push para `codex/eng-codex-005-offline-layout` e comentar na PR #18 com commits, 14/14 focados, 36/36 completos, 3/3 cenários × 22 checks, compileall e limites. Reconsultar a PR após push. Em seguida, iniciar B0 em branch própria baseada no `origin/main` verificado; não fazer merge na `main`.

## Retomada segura

Antes de qualquer edição: `git status --short --branch`; confirmar branch e HEAD; manter `.venv/` fora do stage. Se interrompido, ler este arquivo, comparar o HEAD/PR com o estado remoto atual e continuar A4; não repetir A0–A3 nem assumir que testes antigos foram executados neste HEAD.
