# Devolutiva do Fundador 6: implementacao local e teste controlado TUXEDO

**Data de registro:** 01/11/2026
**Fonte:** relato tecnico do Codex encaminhado pela Direcao nesta conversa, referente ao trabalho local de 31/10/2026. **Status:** avaliacao preliminar; a implementacao nao esta remotamente disponivel para revisao independente. Nenhum merge ou ativacao continua autorizado por este documento.

## O que o Codex informou ter executado

- Branch **local**, nao publicada no remoto: `codex/collector-dialogue-memory-20261031`, worktree isolado, commits `e3780df19e97995e0b45f4b53ce00de38e3e66ce` (ingestao de dossies) e `c4a3070b9e4d542633074b6a29df1d4cf3fde2f8` (dialogo/memoria).
- Ingestao real declarada de `coletor/2026-10-31-1840.md`, Git blob `01101850f5e099aed0058690d08f03f37bdfdf53`; pautas e dossie TUXEDO associados; amostra isolada passou por `article_run`, jornalista e revisor Luna, com memoria privada e um dialogo.
- `story_id=story-7f3e7cfe86558173ff024b09`, revisao `32aeb2272e68cc7fc1be61db59caf60c6127d35853f4623d99c1b189bb459406`, `run_id=rb-5403393c6859c576e69b0f49`.
- Sete chamadas Luna reais declaradas; testes parciais verdes; sem publicacao, sem arquivo editorial aprovado, sem consumir backlog ou ligar o worker continuo. Teste e2e chamava **diretamente** `article_run`, nao demonstrou despacho normal por worker.
- O revisor permaneceu com duvida sobre especificacao/validacao de memoria anunciada para equipamento ainda nao verificado, solicitou pesquisa adicional e o run terminou `blocked`. Dialogo/memoria tecnicos nao comprovam, por si, acerto de politica editorial.
- Contextos declarados de aproximadamente 380 mil e 319 mil caracteres em chamadas de dialogo e revisao. Necessario medir tokens e eliminar repeticoes antes de ativar em fluxo continuo.
- Suite nao integralmente verde no ambiente de testes, com falhas reproduzidas na base e dependencias de shell/checkout; detalhamento e hashes de artefatos seguem somente no relatorio local privado.

## Correcao independente de proveniencia: System76

**A discordancia dos IDs comunicada anteriormente pelo Fundador foi um erro na nossa reconstrucao manual, nao evidencia de captura sintetica ou codigo diferente.**

- O markdown `coletor/2026-10-30-0800.md` usa `Acesso ao conteúdo integral`, mas o `_ALIASES` de `collector.py` na branch de referencia so reconhece `Acesso ao conteúdo` (e variantes), e nao o termo com `integral`.
- Ao reproduzir o `parse_collector_markdown` com `reported_access_status=""`, a revisao corresponde **exatamente** ao checkpoint historico `8f345fc88c1f9631c0e7cbbe1d53fea947308e4aea466bc5ba3f14cda4e7c92f` e o `run_id` calculado corresponde **exatamente** a `rb-05a34e3a8ddc9ff622e862e6`. O `story_id` tambem coincide `story-5fa6ee7b30046e5f4ecf20f4`.
- Os IDs `92210...` e `rb-e3...` vieram da conferencia anterior do Fundador, que interpretou a chave `Acesso ao conteúdo integral` como se fosse campo reconhecido. **Retirar a suspeita de origem da System76 baseada nesses IDs.**
- Ha, entretanto, uma falha adicional de **perda silenciosa do status de acesso** no parser antigo. Ao adicionar suporte ao nome real do campo, evitar reprocessar como novas revisoes antigas sem decisao/migracao de idempotencia. Verificar tambem se a implementacao local nova ja corrige essa lacuna.

## Avaliacao de maturidade A–D

- A (coletor escreve no GitHub) e B (captura real/associacao de dossie) possuem evidencia na coleta e relato de teste.
- C/D (Luna jornalista → dialogo → revisor) tiveram **execucao real isolada** relatada pelo Codex, com artefatos locais; a integracao do **worker/polling/claim/finish** normal e o comportamento continuo ainda nao estao demonstrados.
- O codigo novo permanece no worktree local e nao pode ser conferido independentemente pelo Fundador via GitHub ate push da branch privada.
- Resultado final `blocked` preserva o gate factual; e necessario deliberar como tratar noticia de anuncio e alegacao de fabricante expressamente atribuida, em oposicao a especificacao/benchmark comprovado. Nao pressionar revisor a aceitar afirmacao sem fonte, nem bloquear automaticamente anuncio por ausencia de teste inexistente.

## Prioridades para proxima devolutiva ao Codex

1. Verificar/corrigir o alias de status de acesso sem duplicar candidatas antigas; registrar em teste com dado real.
2. Reduzir e medir o **contexto** de 380k/319k caracteres: separar fatos/dossie/evidencias relevantes, deduplicar paginas, memorias e perguntas, estabelecer limites de tokens configuraveis e teste de que nao perde fatos essenciais. A memoria curta nao pode causar prompts gigantes em todas as chamadas.
3. Expor com seguranca os dois commits no repositorio **privado** da fabrica em branch revisavel, sem incluir prompt integral privado, checkpoints SIWC, captura pessoal ou segredos. Criar PR para revisao; **nao mergear sem aval da Direcao**.
4. Confirmar testes de retomada/crash e de isolamento entre materias com o novo estado, alem da integracao opt-in do worker com fila e captura real. Nao processar backlog ou ativar `--watch` antes da homologacao.
5. Avaliar editorialmente o caso TUXEDO: quando o fabricante anuncia um valor mas nao existe validacao independente, o revisor deve conferir atribucao e incerteza, separar risco factual de pedido por pesquisa inacessivel e explicar exatamente por que algo permanece bloqueante.
6. Definir politica editorial e limites de dialogo com o diretor antes de ativar autonomamente. Testes verdes de mecanica nao equivalem a qualidade editorial homologada.

**Privacidade:** nao copiar relatorios completos, payloads Luna, prompts privados, materia nao publicada nem dados sensiveis para o repositorio publico. Este e apenas um checkpoint tecnico de alto nivel.
