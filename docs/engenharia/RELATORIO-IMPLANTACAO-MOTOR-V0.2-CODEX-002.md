# Relatório de implantação local — Motor Editorial v0.2 / CODEX-002

**Estado:** implementação concluída na branch `codex/motor-editorial-v0.2-multipauta`; [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) aberto para revisão arquitetural. Não integrado à `main`.

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
| `python -m unittest discover -s motor_editorial/tests -v` | 17/17 passaram |
| Contratos da v0.1 | Os 11 testes originais seguem presentes e passaram |
| Regressões v0.2 | 6 testes: isolamento/retomada; composição ordenada e exclusão; direitos e invalidação da prévia; IDs independentes e guarda de exclusão; concorrência/idempotência; migração v2 |
| `git diff --check` | Passou; apenas aviso do Git sobre normalização LF/CRLF de `motor_editorial/README.md` no Windows |
| Painel no Chrome | HTTP 200, layout visível, execução em lote e ação de retomada individual acionadas no loopback |

### Demonstração observada

1. Primeira execução pelo painel persistiu as três pautas. Orbit Racers concluiu revisão e checagem de mídia; Garden of Echoes ficou `blocked_by_review` com intervenção editorial; Clockwork Harbor ficou `recoverable_failure` na apuração. A edição permaneceu aguardando os bloqueios.
2. A retomada individual de Clockwork Harbor pelo painel produziu a segunda tentativa de apuração e levou a pauta à checagem de mídia. A pauta bloqueada continuou independente e a edição não foi liberada prematuramente.
3. Em testes automatizados isolados, a exclusão com ator, motivo e frase exata manteve a pauta bloqueada no histórico e liberou prévia com as outras duas matérias em ordem. Os testes também confirmam que a revogação de permissão remove a arte da prévia e exige nova ação de aprovação.

A demonstração local permanece aguardando uma decisão humana real sobre Garden of Echoes. Nenhuma aprovação foi registrada no banco temporário do painel, e a prévia multipauta não foi desbloqueada nessa sessão. Os atores usados para percorrer exclusão/aprovação aparecem somente nos testes temporários.

## Arquivos alterados

- `motor_editorial/db.py`, `domain.py`, `workflow.py`, `render.py`, `web.py`, `cli.py`.
- `motor_editorial/fixtures/demo-multipauta.json` e `motor_editorial/tests/test_workflow.py`.
- `motor_editorial/README.md`, `docs/engenharia/README.md` e este relatório.

## Limites e pendências

- É um protótipo offline com fixtures fictícias. A checagem demonstra gates técnicos; não comprova direitos de ativos reais, apuração jornalística ou qualidade editorial de produção.
- A aprovação é interna e local. Não há autenticação de usuário, serviço externo, IA, ingestão real, rota de publicação ou operação de produção.
- Revisão arquitetural do [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) é a próxima etapa. Não houve merge nem publicação.
