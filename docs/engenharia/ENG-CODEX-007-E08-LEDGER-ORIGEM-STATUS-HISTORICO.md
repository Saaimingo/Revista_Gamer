# ENG-CODEX-007 — E08: ledger de alegações, rumores e histórico

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E08
- **Versão:** v0.1
- **Status:** implementado e validado localmente; revisão da PR de implementação pendente
- **Data:** 2026-10-25
- **Autorização:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), sequência contínua E01–E19
- **Dependências:** Radar isolado E04, proveniência E05–E07; nenhuma operação editorial pública

## Resultado

O schema Radar v4 mantém a classificação epistemológica da alegação separada do estado posterior do conteúdo. `radar_claims.epistemic_status` registra, entre outros, declaração oficial, declaração de pessoa identificada, rumor atribuído e conteúdo não verificado; `radar_claim_events` registra confirmação parcial, contradição, retirada e correção com fonte, documento público e razão. Os eventos ficam append-only, e a linha inicial da alegação não pode ser sobrescrita.

`radar_claim_sources` agora armazena `based_on_source_id`. Cada vínculo de origem exige documento público da fonte declarada. `origin` aponta para a fonte rastreável mais antiga (ou a reportadora quando a origem anterior é desconhecida); `independent` abre um grupo novo; `republished` exige uma fonte-base já ligada à mesma alegação e grupo. Assim, dez republicações em uma cadeia permanecem um grupo de origem; uma nova origem é registrada separadamente, sem se tornar confirmação automática do conteúdo.

Declarações `official_statement` e `named_person_statement` exigem entidade declaradora do tipo correspondente e vínculo `statement_by` no documento público. Eventos com transição de conteúdo exigem tipo e status coerentes, além de fonte/documento ligados entre si. Correções e contradições são eventos posteriores: não apagam a classificação nem o texto original.

## Migração isolada

O arquivo independente do Radar avançou de v3 para v4 com migração transacional: adiciona a referência de fonte-base, índice de linhagem e triggers append-only para alegações e vínculos. O banco runtime mantém `motor_editorial.db.SCHEMA_VERSION=5` e não foi aberto ou migrado. A cadeia de migração v1→v4 e arquivos temporários são exercitados pelos testes.

## Arquivos entregues

- `motor_editorial/radar_store.py` — schema v4, migração, validações de alegação, linhagem e eventos.
- `motor_editorial/tests/test_radar_store.py` — dez republicações num grupo, origem independente separada, rumor preservado após contradição/correção, atribuição pessoa/organização, rejeições sem fonte-base/status coerente e imutabilidade.
- `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md` e `docs/engenharia/README.md` — estado e índice da unidade.

## Validação

Ambiente: CPython 3.11.9, `.venv`, Windows; hosts `.invalid`, fixtures sintéticas e SQLite temporário.

- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -p 'test_radar*.py' -v` → **33/33 OK**, 16,507 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` → exit 0; Git emitiu apenas avisos de conversão LF→CRLF.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **148/148 OK**, 163,240 s, após as correções finais.

A primeira tentativa da suíte focada após a edição acusou erro de sintaxe na posição da nova rotina de migração; a estrutura foi corrigida e a repetição passou 33/33. Sem coleta/rede, LLM, SIWC/Plus, API paga, banco runtime, scheduler, publicação, deploy ou merge; `published=false`.

## Commit e próximo passo

- Código/testes e checkpoint parcial: `bf96cfb12fa025577d0a3d48c31ad695434d3a78` (`feat: harden Radar claim provenance and history`), enviado à branch de implementação.
- Relatório final, índice, resultado integral e handoffs Issue #28/PR #30 serão registrados no fechamento documental.
- PR draft [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30) permanece aberta e sem merge. Próxima unidade após E08: **E09 — scheduler configurável, default OFF**.
