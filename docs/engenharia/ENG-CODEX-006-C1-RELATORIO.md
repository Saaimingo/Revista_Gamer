# ENG-CODEX-006 — C1: fluxo feliz sintético

Data: 2026-10-24
Status: **C1 concluída em branch experimental; C2 ainda pendente**.
Branch: `codex/eng-codex-006-e2e-experiment`
PR: [#26](https://github.com/Saaimingo/Revista_Gamer/pull/26), draft, sem merge.

## Execução reproduzível

Ambiente: CPython 3.11.9. Fixture: `motor_editorial/fixtures/factory-demo.json`; dados/relatório/HTML do comando ficaram em `%TEMP%`, fora do repositório.

```powershell
& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\revista-gamer-factory-demo-c1-20261024" factory-demo --run-id codex-006-c1-cli-proof
```

Saída observada: `simulated_approved_internally`; 15/15 tarefas `succeeded`; CompositionValidation `PASS`, 22 checks; prévia interna presente; `published=false`, `network_calls=0`, `siwc_calls=0`, `paid_api_calls=0`.

## Contratos e evidências

A sequência percorrida foi `source_analysis` → `outline` → `draft` → `fact_check` → `review` → inventário de direitos sintético → `StoryPackage.v0` → necessidades/referências → `LayoutPlan.v0` → validação → render → validação do HTML → persistência da prévia → gate humano de fixture. A aprovação foi explicitamente simulada; não foi gravada como decisão humana real do Motor.

Uma única construção de `TaskDispatcher` serviu as etapas de agente e determinísticas. O teste verifica `TaskDispatcher.call_count == 1`, que os eventos/tarefas estão em `agent_tasks`/`agent_task_events` e que `execution_attempts` continua em zero nesta cadeia. O runner legado `layout-demo` não é chamado pela esteira.

| Artefato | SHA-256 |
| --- | --- |
| Artigo B2 e revisão vigente | `5e214c149bcbb84c81997ca91ac352785efeb5e3dc925c696a275ea45eb232b6` |
| Envelope `StoryPackage.v0` | `163b86a9e117c07cfb36e46696a5cfb17d9d9bf0a9f274df25599993feafe444` |
| Revisão `StoryPackage` | `b4291679bc6b2c2cf54488b0d7da3b0e9cacfa1ce73405180c0706e2c9609fdf` |
| `MediaInventory.v0` | `4b63cfe7635f28e7bc1872af269cbb16cf1910357608c86e0c43cf8590d64054` |
| Índice sintético de referências | `0fba255d3580d66767daadf83a060e64da1785c297974805e41aaa42094cf181` |
| `LayoutPlan.v0` | `8c4887f125bb8379ed29eed5464233e6664ce846d06384eff390b73dd52f933f` |
| `CompositionValidation.v0` após render | `51a7abb27685c42aed89a25ba95e1f1ba23f2989bc9d782bcf5aa3ec6c7f7405` |
| HTML da prévia interna | `30ab0b2c3249ef7aeccdbfc01f76749cf0708bcf0ddacb4711203037a3ebf4b5` |

Os perfis de conteúdo A4 são neutros e versionados: editor `synthetic-editor@0.1.0` (hash `d2e027cb72bd5187ef0a9c94823ab843182eb8307e414100ac09a3b79241441c`), persona fictícia `neutral-fictional-writer@0.1.0` (hash `f42e0887781c28331198b9bdf45b60d53da608d3fcc3afc9c67757f83a615e03`) e revisor `synthetic-reviewer@0.1.0` (hash `6c51aa4f56cf6b98ff69fd313d2da813dd8d2b48c14ccd16998f3f3ae3ec83e5`). O hash B2 do perfil executor fica separado no ledger. A ponte preserva o hash da revisão B2 e calcula um novo hash A4; o `review_kind=synthetic_contract_bridge` não representa aprovação humana.

## Validação

- `motor_editorial.tests.test_factory -q`: 2/2 OK em 3,394 s. Cobre a cadeia, um dispatcher, retomada idempotente, hashes/perfis e a interface CLI.
- `motor_editorial.tests.test_factory -q` em tentativa anterior expôs `WinError 32` ao limpar SQLite aberto pelo próprio teste. O teste passou a fechar a conexão com `contextlib.closing`; a repetição passou.
- Primeira execução da suíte completa: 88/89 passaram; `test_dispatcher_heartbeat_keeps_long_executor_owned_past_ttl` retornou `queued` em vez de `succeeded`. Rodada isolada do teste: 1/1 OK em 8,251 s. Suíte completa serial subsequente: 89/89 OK em 52,495 s. A causa da oscilação inicial não foi isolada, então ela permanece registrada como observação de timing.
- `python -m compileall -q motor_editorial` passou; `git diff --check` passou após as alterações de código e `git diff --cached --check` passou após incluir os documentos finais, antes do commit.

## Limites e próximo passo

O ensaio usa somente nomes, textos, fontes `example.invalid`, perfis e placeholders fictícios. O gate `simulated_approved_internally` é dado de fixture; não é aceite da direção, não altera uma edição real e não publica. Não houve rede, SIWC/Plus, API paga, custo ou deploy.

C1 cobre somente o caminho feliz sem correção automática. C2 deve forçar `revise`, criar novo hash de artigo e executar nova checagem/revisão, comprovando que StoryPackage, plano, prévia e qualquer decisão anterior não passam como atuais.
