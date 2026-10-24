@echo off
setlocal
cd /d "%~dp0"

if not exist "AGENTS.md" (
    echo AGENTS.md nao encontrado na pasta do repositorio.
    pause
    exit /b 1
)
if not exist "docs\engenharia\ENG-CODEX-006-CHECKPOINT.md" (
    echo Checkpoint ENG-CODEX-006 nao encontrado.
    pause
    exit /b 1
)
where codex.cmd >nul 2>nul
if errorlevel 1 (
    echo Codex CLI nao encontrado no PATH. Instale ou ajuste o PATH e tente novamente.
    pause
    exit /b 1
)

codex.cmd -C "%CD%" "Continue the already authorized Revista Gamer ENG-CODEX-006 work from the persisted checkpoint. Before changes, read AGENTS.md and all mandatory documents listed there; verify current git branch, upstream, status, commits, PR #26 and Issue #23 comments/reviews; read docs/engenharia/ENG-CODEX-006-CHECKPOINT.md and Issue #23 comment 6378715359. Recheck live state instead of trusting old notes. Resume with C2 and continue in order through D2 within Issue #23 limits. Validate each unit with real evidence, keep persistent checkpoints and PR evidence, and commit/push regularly. If interrupted, record completed and in-progress units, changes and commits, commands and results, blockers, and next step. Do not merge to main, publish/deploy, use paid APIs or real SIWC/Plus, create accounts, change permissions, buy or contract services. Do not ask for routine technical confirmation. Record editorial, legal, or scope decisions reserved to direction as blockers and continue independent work."