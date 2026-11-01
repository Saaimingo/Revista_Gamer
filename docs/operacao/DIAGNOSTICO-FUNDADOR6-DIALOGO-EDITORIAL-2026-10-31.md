# Revista Back — Diagnostico do Fundador 6 sobre dialogo jornalista/revisor

**Estado:** ANALISE TECNICA INDEPENDENTE + PROPOSTAS EM DEBATE. NAO APROVADO PARA IMPLEMENTACAO.
**Data:** 31/10/2026, conversa Fundador 6.
**Origem:** leitura direta, somente de leitura, do codigo remoto da factory `Saaimingo/revista-back-factory`, branch `codex/revista-back-factory-v0.1.4-20261030`, HEAD `312dbd2`, confrontada com o retorno da auditoria Codex e orientacoes verbais da Direcao.
**Escopo:** fluxo de passagem de contexto, identidade editorial, revisao, pesquisa complementar e lacunas dos testes. Nenhum codigo/prompt/config/DNA modificado. Nenhum modelo executado.

## Decisoes da Direcao a preservar

1. **Nao reduzir rigor** do revisor. Bloquear quando afirmacao carecer de sustentacao. O pedido e melhorar compreensao, explicacoes e dialogo, nao facilitar aprovacao.
2. Revisor deve formular perguntas especificas e esclarecer sua duvida. Jornalista deve poder responder, justificar, contestar fundamentadamente ou solicitar pesquisa.
3. DNAs de Arlindo Carranca, Beto Cartucho e Nina Prisma permanecem aprovados e inalterados. Investigar se falta uma instrucao de **atuacao da persona** no uso operacional do Luna; nao pressupor que a causa foi provada.
4. Revista de games/hardware pode ter voz, criatividade e ironia da persona sem inventar dados ou alegar testes fisicos. Nao obrigar humor artificial.
5. Debater e aprovar contrato antes de encomendar alteracao ao Codex.

## Achados verificaveis no codigo remoto

### F1 — Reescrita sem texto anterior no prompt enviado
- `automation/pipeline/src/flow.py`, funcao `article_run`: ao receber revisao, o codigo guarda `context["draft"]` e monta um novo prompt a partir de `respin["prompt_path"]`.
- O prompt de reescrita ativo foi identificado na auditoria como `factory-config/prompts/respin.md`: insere persona, pauta, encaminhamento, evidencias, pesquisa complementar e notas, **mas nao contem placeholder `{draft}`**, embora instrua preservar partes corretas.
- `automation/pipeline/src/render.py` substitui somente os placeholders efetivamente presentes. Portanto, o prompt de reescrita nao inclui automaticamente a versao precedente, apesar de o codigo mante-la no contexto.
- **Impacto:** pode levar a reescritas menos precisas e perda de trechos bons. Nao afirmar que isso causou comprovadamente um erro especifico do run System76.

### F2 — Canal unilateral em vez de dialogo
- Revisor responde JSON com `action`, `corrections`, `observacoes`, `research_questions`, `research_urls`.
- Jornalista responde uma nova materia (`title`, `standfirst`, `body`, `sources`; no primeiro draft, `image_needs`); **nao ha resposta estruturada do jornalista a perguntas individuais**, campo de justificativa/discordancia ou registro de negociacao editorial.
- `_factory_verdict` em `flow.py` prioriza `corrections` e transforma a lista em texto de `notes`; perguntas e URLs de `research` seguem para ferramenta de busca, mas **nao sao entregues como perguntas identificadas ao jornalista**, por um contrato de conversa. O jornalista recebe evidencia agregada da pesquisa complementar.
- `automation/pipeline/src/adapter_siwc.py`, `ResponsesAdapter.complete`, envia requisicao de inferencia separada com um `input` textual e `store: False`, sem historico de dialogo automaticamente encadeado. O estado conversacional deve ser reconstituido explicitamente no prompt.
- **Impacto:** existe sequencia de avaliacao/reescrita, nao intercambio de argumentos verificaveis.

### F3 — Limite de pesquisa e limite de reescrita se chocam
- `flow.py` so executa `fetch_followup_evidence` para `research` dentro do `while passes < respin.passes`. A pesquisa e uma etapa separada, mas a continuidade obrigatoriamente consome reescrita e nova revisao.
- Factory exemplo tem `respin.passes=2` e `followup_research.max_rounds=2`. A ultima solicitacao `research` pode terminar bloqueada por esgotamento dos passes, ainda que sobrem rodadas de pesquisa.
- O caso System76 teve tres avaliacoes e terminou bloqueado na ultima solicitacao de pesquisa, conforme auditoria de execucao local do Codex; codigo remoto confirma possibilidade desse caminho.
- **Impacto:** resultado `blocked` agrega situacoes distintas: possivel insuficiencia editorial vs limite operacional consumido. Necessario diferenciar status/encaminhamento.

### F4 — Identidade do jornalista carregada, mas interpretacao nao homologada
- `automation/pipeline/src/context.py`, `_persona`, consulta `/authors` no backend e fornece nome, bio, style, who_i_am, profile_topics e exemplos positivos/negativos quando disponiveis.
- O prompt ativo de producao identifica `{persona}` e exige preservar o DNA. Nao existe, na versao examinada, protocolo detalhado de como o personagem deve **pensar, contra-argumentar e sustentar sua voz** durante revisoes.
- O arquivo publico `docs/personagens/RANZINZA.md` e um perfil historico datado de 19/10 e nao comprova o cadastro real do backend usado em 30/10. O prompt integral da persona efetivamente renderizado nao foi preservado pelo journal SIWC. Nao concluir sobre a qualidade ou versao exata do DNA sem evidencias.
- **Impacto:** diferenciar falha de instrucao operacional de hipotese de DNA desatualizado, com verificacao privada dos campos reais e hashes antes de corrigir.

### F5 — Testes atuais nao cobrem a qualidade do contrato de dialogo
- `automation/pipeline/tests/test_factory.py` usa modelos simulados, prompts sinteticos temporarios e resposta predefinida de revisor/jornalista; verifica estados, chamadas e fontes, mas nao exige `{draft}` no prompt de respin nem pergunta/resposta entre agentes.
- Isso explica por que testes verdes de orquestracao nao demonstram preservacao de contexto e boa colaboracao editorial.

## Proposta inicial PARA DISCUSSAO (nao implementada)

- Separar `parecer factual`, `duvida de interpretacao`, `problema de forma`, `necessidade de pesquisa`, `bloqueio justificado` e `limite operacional atingido`.
- Contrato bidirecional minimo: `issue_id`, trecho/afirmacao, tipo e gravidade, evidencias consultadas, **pergunta objetiva do revisor**; resposta do jornalista vinculada ao `issue_id` com evidencias, justificativa, contraponto ou incerteza declarada; revisor reavalia o **mesmo ponto** antes de decidir.
- Encaminhar a versao anterior do texto e as partes ja aceitas; nao requisitar reescrita inteira quando a alteracao for localizada.
- Preservar DNA, incluindo orientacao de atuacao (perspectiva, voz, capacidade de argumentacao) em camada operacional, sem edicao automatica da identidade aprovada.
- Limitar ciclos, contexto e uso; registrar perguntas ja respondidas para evitar repeticao; encaminhar divergencias insolutas para decisao humana, **sem substituir a checagem factual por conversa**.
- Criar testes offline especificos e reproduziveis com cenario System76: fato inconsistente bloqueia; anuncio sem benchmark independente nao vira avaliacao de desempenho; divergencia de precos provoca pergunta com fontes; jornalista pode responder/contestar com evidencia; responder sem evidencias nao aprova; reescrita inclui versao anterior; limite tecnico gera status diferente de falha editorial. So executar quando autorizado.

## Ponto de retomada

Debater com a Direcao, em passos curtos, primeiro a estrutura da pergunta do revisor e da resposta do jornalista; depois o regimento de aceite, o limite de dialogo e o modo de atuacao dos tres jornalistas. Nenhuma ordem de implementacao nesta fase.
