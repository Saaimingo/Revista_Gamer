# ENG-CODEX-007 E18 — jornalistas isolados, validação offline

**Estado:** `PARTIAL_OFFLINE_ONLY / REAL_EVALUATION_NOT_EXECUTED`  
**Data:** 2026-10-25 20:06 -03:00  
**Branch:** `codex/eng-codex-007-factory-radar`  
**PR da missão:** [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), aberta, draft e sem merge.

## Resultado e limite

E18 foi preparada e validada apenas no contrato local de isolamento das três referências de persona. Não foram executadas as matrizes de comportamento, inferências ou avaliações P (fidelidade à persona) e J (jornalismo). As 16 IDs T01–T16 por jornalista são inventariadas, mas constam como `not_executed`; os dois eixos permanecem `not_evaluated`, e a revisão humana segue `pending_direction`.

A cota Plus ter voltado a 100% não altera a instrução vigente que proíbe SIWC/Plus real nesta missão. Não houve consulta de conta/modelo, login, probe, chamada de inferência, uso de credenciais, consumo ou custo. Também não houve uso de API paga ou fallback.

## Fontes de identidade e revisão ao vivo

As referências foram rechecadas nas pontas atuais das PRs antes do registro. Os SHA-256 listados na fixture são dos bytes exatos de cada arquivo Markdown no commit-fonte indicado; eles identificam documentos e matrizes, não são hashes canônicos dos DNAs nem resultados de execução. Separadamente, `persona_hash` identifica o texto de instrução normalizado que efetivamente entra no contexto, após o trim externo aplicado por `_text`.

| Jornalista | Fonte atual | Matriz | SHA-256 da matriz |
| --- | --- | --- | --- |
| Arlindo Carranca / Ranzinza (`ranzinza`) | PR [#13](https://github.com/Saaimingo/Revista_Gamer/pull/13), `3d651fe1951818767b4a6b935732857f08cb7849`; aberta, draft, sem reviews | `docs/personagens/RANZINZA-MATRIZ-VALIDACAO-v0.1.md` | `3f5feacf07684fd5120e364f96bbb6ae9f7ac70b272b372330b57de4351e37c2` |
| Beto Cartucho (`beto-cartucho`) | PR [#19](https://github.com/Saaimingo/Revista_Gamer/pull/19), `21381c0975bef1da048d7887cbdfbd0dd97bed96`; aberta, draft, sem reviews | `docs/personagens/GAMER-MATRIZ-DE-TESTES-v0.2.md` | `fb9c5f601990615fc771ea50551ba2973b3795ad7aaeaa9955a1953d7f30f170` |
| Nina Prisma (`nina-prisma`) | PR [#19](https://github.com/Saaimingo/Revista_Gamer/pull/19), mesmo HEAD de Beto; aberta, draft, sem reviews | `docs/personagens/NINA-PRISMA-MATRIZ-DE-TESTES-v1.0.md` | `5eba24cf0ab2e2c5f09d6df4a40d5c3b59324faca4502adda2b0b986cf0c70e9` |

O handoff compartilhado da apuração e do veredito foi confirmado na PR [#27](https://github.com/Saaimingo/Revista_Gamer/pull/27), HEAD `d38c5da92ba76739d9234942f7bf0bd087949e5f`; PR aberta, draft, sem reviews. O SHA-256 de `docs/personagens/continuidade/DIRETRIZ-REPORTAGEM-APURACAO-E-VEREDITO-2026-10-24.md` nesse commit é `535b1691bd2a5672daaabd2040d8c0e4729054d0e4c69ac7720c7a0dd20eff52`.

Os comentários atuais das PRs #13 e #19 mantêm o trio criativamente aprovado e documentalmente consolidado, com testes operacionais/LLM pendentes; a diretriz da #27 especifica fases isolada e integrada, sem declarar testes prévios executados. PR #14, que guarda os ativos visuais de Carranca/Beto, não foi alterada nem usada para gerar ou copiar ativos nesta etapa. Nenhum DNA, amostra aprovada ou ativo foi modificado.

A fixture [`persona_trials_offline_v1.json`](../../motor_editorial/tests/fixtures/persona_trials_offline_v1.json) registra também os caminhos e SHA-256 dos contratos/perfis consultados em cada commit-fonte. As fontes são referências imutáveis; seus arquivos não foram trazidos para a branch de implementação.

## Alteração técnica e evidência local

Em `AgentRoleCatalog.prepare_invocation`, `persona_writer` agora falha de forma fechada se não receber a instrução do DNA ou se o texto normalizado da instrução não produzir o `persona_hash` declarado no envelope. O bloco só entra no contexto confiável sob `persona:<persona_id>`. Isso impede preparar o papel com DNA ausente ou anexar, por engano, instruções pertencentes a outra referência.

Os ensaios usam sentinelas sintéticas distintas para cada ID. Não carregam texto de persona, não geram artigo e não chamam executor, modelo ou serviço externo. A fixture mantém explícitos os 48 registros T01–T16 (16 por jornalista) como não executados.

Com CPython 3.11.9 no `.venv`:

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_persona_trials_offline -q` — **23/23 OK em 1,424 s**.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0 (Git emitiu somente o aviso usual de normalização LF→CRLF para `agent_contracts.py`).

Uma primeira execução do teste novo apontou uso do nome de campo incorreto (`content` em vez de `text`) na asserção da fixture. A asserção foi corrigida antes da rodada final acima; a alteração de produção não precisou de ajuste adicional.

## Arquivos, commits e próximo passo

- Código, fixture de proveniência e teste offline: `motor_editorial/agent_contracts.py`, `motor_editorial/tests/fixtures/persona_trials_offline_v1.json`, `motor_editorial/tests/test_persona_trials_offline.py`.
- Commit de código/testes enviado: `9349194` (`test: bind offline journalist persona references`).
- Sem alteração de DNA/personagem, sem migração ou acesso ao banco runtime, sem scheduler/worker, publicação, deploy ou merge; `published=false`.
- **E18 permanece parcial**, com inferência e avaliação humana bloqueadas pelo escopo e pela ausência de parecer P/J humano. A caixa da E18 na Issue #28 deve continuar desmarcada.
- Próxima unidade autorizada: **E19 offline**, testar referências isoladas dentro da fábrica/ledger existente, com os mesmos limites de identidade. Depois rodar a suíte integral serial e registrar o resultado verdadeiro; não inferir fidelidade ou qualidade jornalística a partir dos mocks.
