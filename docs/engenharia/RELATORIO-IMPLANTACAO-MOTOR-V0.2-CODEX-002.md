# Relatório de implantação local — Motor Editorial v0.2 / CODEX-002

**Estado:** implementação e correções pós-revisão concluídas na branch `codex/motor-editorial-v0.2-multipauta`; [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) atualizado e aberto para nova revisão arquitetural. Não integrado à `main`.

**Base:** `main` em `f8f959a6548c0b41f4b594beee682e543a2a475c`.

**Escopo aprovado:** [Issue CODEX-002](https://github.com/Saaimingo/Revista_Gamer/issues/5), [especificação v0.2 multipauta](ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md) e [ordem técnica](ORDEM-CODEX-002-MOTOR-MULTIPAUTA.md).

## Ambiente comprovado

- Windows 11 Home, versão `10.0.26200`, build `26200`, execução nativa em `C:\Users\saimi\Revista_Gamer`.
- Python `3.11.9`, sem dependências externas; SQLite e servidor HTML usam a biblioteca padrão.
- Branch verificada: `codex/motor-editorial-v0.2-multipauta`.
- Painel local respondeu HTTP `200` em `http://127.0.0.1:8765/`, bind restrito ao loopback. A página foi aberta e inspecionada visualmente no Chrome.
- Banco e artefatos da inspeção do painel ficaram em diretório temporário sob `%TEMP%`; nenhum estado de demonstração foi gravado no repositório.

## Implementação

- Adicionada fixture inteiramente fictícia com três pautas independentes, fontes `mock://`, uma duplicata, um item irrelevante, direitos de mídia variados, uma reprovação editorial isolada e uma falha transitória determinística.
- `demo` executa ou retoma o lote v0.2; `run-story` retoma uma única pauta. `demo-v1` preserva a fixture e o fluxo de compatibilidade v0.1.
- Cada execução namespacia IDs de itens, pautas e edição. Tentativas permanecem idempotentes por execução, pauta e etapa; falhas e intervenções de uma pauta não mudam o estado das demais nem encerram o lote.
- Edições mantêm membros, ordem, obrigatoriedade, estado ativo e decisão humana de exclusão com autor, motivo, data e evento auditável. A exclusão não apaga a pauta nem seu histórico.
- A prévia só fica pronta quando as matérias obrigatórias ativas estão elegíveis; reúne fontes, revisão vigente e direitos de mídia por matéria, na ordem persistida. Mudança em revisão, fontes ou direitos renova o fingerprint e exige nova aprovação humana interna.
- SQLite migrado de v2 para v3 por adição de colunas. Bancos v0.1 existentes mantêm a composição legada; associação antiga é marcada como fluxo `legacy_v1`.
- Painel inclui lote, retomada individual, estados por pauta, associações ordenadas, revisão/direitos, exclusão humana explícita e aprovação interna. Rotas `/publish` continuam inexistentes.

## Validação executada no Windows 11

| Verificação | Resultado |
|---|---|
| `python -m compileall -q motor_editorial` | Passou |
| `python -m unittest discover -s motor_editorial/tests -v` | 21/21 passaram no Windows 11 |
| Contratos da v0.1 | Os 11 testes originais seguem presentes e passaram |
| Regressões v0.2 | 10 testes: contratos anteriores, mais isolamento/retomada, composição ordenada e exclusão, direitos, IDs, migração, concorrência/idempotência e quatro regressões pós-review |
| `git diff --check` | Passou |
| Painel após correções | Reiniciado no loopback com banco temporário isolado; HTTP 200 em `http://127.0.0.1:8765/` |

### Resposta à revisão arquitetural mais recente do PR #6

- **B1 — Retomada após aprovação:** `run_multipauta_story()` detecta edição já aprovada e retorna sem recompor nem alterar estado. `run_multipauta_demo()` também preserva o fast path quando o fingerprint continua vigente. A regressão compara estado, responsável, data, fingerprint, contadores e trilha de auditoria antes/depois das duas chamadas.
- **B2 — Serialização lote/pauta:** o head revisado já aplicava `@_serialized_operation` em `run_multipauta_story()` e no lote, compartilhando o mesmo `RLock` do objeto `Motor` usado pelo servidor multithread. A regressão nova pausa o lote durante uma pauta e confirma que a retomada concorrente aguarda a liberação; verifica uma edição, três pautas e somente duas tentativas de apuração para a pauta recuperável. Não foi necessária alteração adicional no lock existente.
- **Direitos após aprovação:** retomada de lote, retomada individual, acesso GET à prévia e nova solicitação de aprovação passam pela revalidação da composição aprovada. Se direito, revisão, fontes, fingerprint ou prévia mudarem, a aprovação anterior é limpa e auditada; quando revisão e membros continuam elegíveis, a prévia é recomposta e a edição volta a aguardar nova aprovação humana. O GET mostra um aviso na prévia atualizada; a ação que detecta a mudança não aprova automaticamente.
- As duas regressões que reproduzi antes da correção falhavam: a retomada rebaixava a edição aprovada e o lote retornava aprovação obsoleta após revogação de mídia. Após as correções, as quatro regressões novas passaram; a regressão concorrente confirmou a serialização já presente.

### Demonstração observada

1. No servidor local reiniciado com código corrigido, duas chamadas CLI à fixture persistiram três pautas. A primeira deixou duas pendências; a segunda retomou Clockwork Harbor e reduziu a edição a um único bloqueio, Garden of Echoes em `blocked_by_review`.
2. A edição permanece aguardando essa decisão humana, sem exclusão ou aprovação fictícia no banco temporário atual. O painel responde HTTP 200 no loopback.
3. Em testes automatizados isolados, a exclusão com ator, motivo e frase exata mantém a pauta bloqueada no histórico e libera prévia com duas matérias em ordem. As novas regressões confirmam a retomada idempotente após aprovação, a serialização lote/pauta e a invalidação/recomposição após revogação de direito de mídia, inclusive ao acessar GET `/editions/{id}/preview`.

A demonstração local permanece aguardando uma decisão humana real sobre Garden of Echoes. Nenhuma aprovação foi registrada no banco temporário do painel, e a prévia multipauta não foi desbloqueada nessa sessão. Os atores usados para percorrer exclusão/aprovação aparecem somente nos testes temporários.

## Arquivos alterados

- `motor_editorial/db.py`, `domain.py`, `workflow.py`, `render.py`, `web.py`, `cli.py`.
- `motor_editorial/fixtures/demo-multipauta.json` e `motor_editorial/tests/test_workflow.py`.
- `motor_editorial/README.md`, `docs/engenharia/README.md` e este relatório.

## Limites e pendências

- É um protótipo offline com fixtures fictícias. A checagem demonstra gates técnicos; não comprova direitos de ativos reais, apuração jornalística ou qualidade editorial de produção.
- A aprovação é interna e local. Não há autenticação de usuário, serviço externo, IA, ingestão real, rota de publicação ou operação de produção.
- Nova revisão arquitetural do [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) é a próxima etapa. Não houve merge, publicação ou início da v0.3.
