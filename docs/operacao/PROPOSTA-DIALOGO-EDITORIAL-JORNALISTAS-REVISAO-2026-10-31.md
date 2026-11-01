# Revista Back - Proposta em debate sobre dialogo editorial

Data: 31/10/2026
Origem: Direcao e Fundador 6
Estado: EM DEBATE. NAO IMPLEMENTAR sem nova autorizacao do diretor.
Destinatarios para consulta futura: Codex, Bloco 04 (Redacao) e Fundador.

## Orientacao central da Direcao

O revisor deve manter integralmente o rigor factual. Afirmacoes sem fundamento, inconsistentes ou sem sustentacao devem continuar bloqueadas quando necessario. Nao se pretende flexibilizar a aprovacao, mas sim tornar a comunicacao explicativa e colaborativa.

Diante de precos divergentes ou de uma passagem incompreendida, o revisor deve apontar precisamente a duvida e perguntar ao jornalista se as diferencas podem vir de versoes, modelos, configuracoes, fontes ou datas diferentes. Nao presumir automaticamente que houve erro. O jornalista deve responder com pesquisa e evidencias, ou declarar claramente o que ainda nao foi confirmado. Se a justificativa for insuficiente, o revisor pode manter a negativa fundamentada.

No caso System76, noticia de anuncio e avaliacao de produto sao generos diferentes. A ausencia de benchmark independente de um produto ainda nao lancado nao deve ser confundida com prova de falsidade. O texto deve distinguir alegacoes comerciais de testes efetivamente realizados e delimitar o que nao foi apurado. Outras duvidas sobre precos e configuracoes permanecem sujeitas a verificacao.

## Interpretacao dos jornalistas

Os DNAs aprovados de Arlindo Carranca, Beto Cartucho e Nina Prisma nao devem ser alterados sem deliberacao. A direcao quer examinar a hipotese de que falte uma instrucao operacional para que o modelo interprete efetivamente a personalidade do jornalista durante redacao, revisoes, dialogos, contrapontos e escolhas de enfoque. Os prompts atuais ja incluem a persona e pedem preserva-la; por isso ainda nao se provou que essa seja a causa do comportamento observado.

O tom pode ser criativo e descontraido quando apropriado ao personagem e a uma revista de games/hardware, sem inventar fatos, testes, fontes ou experiencias.

## Proximo passo

Debater com a direcao, por etapas, um protocolo bidirecional de perguntas, respostas, contestacoes fundamentadas, uso de evidencias, limites de ciclos e escalonamento humano. Diferenciar bloqueio por evidencia insuficiente de bloqueio por limite operacional. Nenhuma mudanca de prompt, DNA, codigo ou gasto de inferencia autorizada neste registro.

## Hipotese em debate: memoria temporaria por reportagem

**Origem:** nova ideia apresentada pelo diretor durante a investigacao de dialogo jornalista/revisor. **Estado:** hipotese de arquitetura, nao aprovada nem implementada.

Cada materia pode receber uma pequena memoria propria, associada a `story_id` e `run_id`, com versao do texto, perguntas identificadas, respostas argumentadas, links e hashes de evidencias, pontos resolvidos ou pendentes, conclusoes provisórias e eventual escalonamento humano. Jornalista e revisor receberiam apenas o trecho relevante dessa memoria em cada chamada Luna, sem inserir todo o historico no prompt.

O armazenamento atual da factory ja possui SQLite para a fila e candidatos, checkpoints locais DBOS por run e arquivo privado append-only para versoes aprovadas; estes mecanismos **nao constituem, por si, a memoria conversacional editorial proposta**. Investigar como acrescenta-la sem criar outra fabrica ou perder a durabilidade e a idempotencia atuais.

Ao encerrar uma materia, discutir tres destinos distintos: (a) arquivar no historico privado as fontes, fatos confirmados, divergencias, justificativas de aceite e conhecimento reutilizavel, com proveniencia e data; (b) manter pendencias e versoes necessarias para auditoria, recurso ou retomada; (c) reduzir ou eliminar detalhes transitorios do dialogo somente apos politica explicita de retencao e descarte. Nao transferir conjecturas para a base de fatos nem descartar registros ainda necessarios para recuperacao.

A memoria deve ser limitada por topico/pauta, resumida quando necessario e capaz de evitar repeticao de perguntas ja respondidas. Toda resposta deve distinguir alegacao do fabricante, fonte lida, hipotese e fato verificado. Limites de dialogo, orcamento e tempo continuam a ser deliberados com a direcao.

## Devolutiva da auditoria Codex recebida pelo Fundador (31/10/2026)

**Fonte:** relatorio tecnico privado de viabilidade fornecido pela Direcao nesta conversa; nao foi republicado neste repositorio. **Status:** auditoria somente de leitura concluida; nenhuma implementacao aprovada, nenhuma alteracao de prompts/DNAs/codigo ou inferencia executada nesta etapa. Conclusoes sobre runtime local sao relato da auditoria; as limitacoes de `flow.py` e do contrato de respin tambem foram confrontadas pelo Fundador com o codigo remoto.

- **Viabilidade:** o Censurado operacional comporta memoria editorial estruturada por materia sem nova fabrica. Recomendada a alternativa B: artefato privado versionado por `story_id` e `candidate_revision_sha256`, dentro do `run_id` existente, usando checkpoints DBOS, journal SIWC e mecanismos atuais de proveniencia.
- **Lacunas:** nao existe dialogo com questoes identificadas e respostas por item; a reescrita nao injeta explicitamente o draft anterior; o ultimo pedido de pesquisa pode ficar sem atendimento quando terminam os dois passes de reescrita; `blocked` nao distingue impasse editorial de limite operacional; nao ha politica configurada de expurgo da memoria e artefatos.
- **Identidade:** o Luna recebe perfil dinamico do backend, mas o texto exato recebido no run historico nao foi preservado; atuacao de persona requer verificacao/testes antes de atribuir culpa ao DNA. Os DNAs aprovados permanecem intocados.
- **Revisao de interpretacao do System76:** segundo a nova inspecao detalhada do Codex, o parecer nao mandou inventar ou apresentar benchmark inexistente: pediu que, se nao houver benchmark independente, a noticia registre sua ausencia e nao seja tratada como analise de desempenho. O impasse principal persistente foi a relacao entre precos e configuracoes. A redacao anterior do Fundador que atribuiu ao revisor exigencia categorica de benchmark foi excessiva e deve ser revista nesta deliberacao.
- **Estado da execucao:** a auditoria reporta que o Docker estava ativo, mas sem worker factory rodando; o run System76 historico ficou bloqueado por limite de reescrita, com outras pautas ainda pendentes e nao processadas. Nenhuma alteracao foi feita.
- **Pontos que so a Direcao pode definir:** criterios por genero de reportagem, estados de incerteza, dialogo e limites de turnos, escalonamento humano, retencao/expurgo e eventual incorporacao do dossie do Captador. Implementacao separada depende de autorizacao expressa.
