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
