# Missao Codex — Verificar viabilidade de dialogo editorial e memoria por materia na fabrica Censurado

**Emissor:** Direcao da Revista Back / Bloco Fundador 6
**Data de referencia:** 31/10/2026
**Tipo:** AUDITORIA DE VIABILIDADE, SOMENTE LEITURA, SEM IMPLEMENTACAO
**Estado:** autorizada apenas a investigacao documental/tecnica; qualquer implementacao depende de nova deliberacao da Direcao.
**Prioridade:** entender o que a fabrica REAL utilizada ja suporta e quanto seria preciso adaptar, sem construir outra esteira.

## 1. Fontes e base de comparacao

- Fabrica operacional: repositorio PRIVADO `Saaimingo/revista-back-factory`, branch `codex/revista-back-factory-v0.1.4-20261030`, ponto de referencia `312dbd2cecb65a3f01400118d1a5d4d2a79c4177`. Se o checkout real divergir, informar os dois commits e qual corresponde ao runtime.
- Repositorio editorial: `Saaimingo/Revista_Gamer`, branch `main`.
- Deliberacao inicial da Direcao: `docs/operacao/PROPOSTA-DIALOGO-EDITORIAL-JORNALISTAS-REVISAO-2026-10-31.md`.
- Investigacao independente do Fundador: `docs/operacao/DIAGNOSTICO-FUNDADOR6-DIALOGO-EDITORIAL-2026-10-31.md`.
- Auditoria privada anterior do run System76, se disponivel em arquivo local autorizado. Nao republicar prompts integrais nem dados privados no repositorio publico.
- Distinguir rigorosamente a fabrica Censurado em uso do legado `motor_editorial` no repositorio Revista_Gamer, do pipeline Censurado generico e das configuracoes privadas efetivamente montadas em runtime.

## 2. Visao de produto a verificar, nao a implementar

A Direcao deseja uma equipe editorial que **dialogue** entre turnos do Luna, em vez de apenas receber reprova e reescreve. Rigor factual inalterado: bloquear o que nao tem fundamento. Flexibilizar comunicacao para entendimento, jamais afrouxar aceite.

Um revisor deve poder perguntar, por exemplo, se tres precos representam SKU, geracao, configuracao ou data diferentes; o jornalista pode investigar, justificar, contestar respeitosamente uma exigencia impraticavel ou admitir lacuna verificavel. Uma noticia sobre produto nao lancado nao deve ser tratada como benchmark realizado; promessas comerciais precisam ser atribuidas, nunca assumidas como teste. O revisor pode manter bloqueio fundamentado.

Os DNAs de Arlindo Carranca, Beto Cartucho e Nina Prisma sao aprovados e NAO devem ser alterados. Avaliar se falta instrucao operacional de interpretacao consistente da persona ao redigir, investigar e responder a revisoes, sem reduzir criatividade ou transformar ironia em fato.

A memoria proposta e pequena, isolada por `story_id` e revisao/`run_id`, com versao anterior, questoes especificas, pergunta, resposta, evidencia, decisao, resumo dos pontos resolvidos/pendentes. A inferencia recebe somente contexto relevante; banco persistente guarda o resto. Apos encerramento, reter fatos e evidencias reutilizaveis em historico privado; diferenciar logs de auditoria de detalhes transitorios, com politica de retencao deliberada.

## 3. Perguntas tecnicas obrigatorias

### A. Base real e origem
1. Qual o caminho de execucao REAL em producao/teste (entrypoint, node graph, arquivos de config montados, prompts efetivos, modelos, adaptador, fila, checkpoints, acervo)? Indicar caminhos/linhas/commits/hashes, sem colar instrucoes privadas.
2. O que ja existe, o que e apenas legado/desconectado, o que esta local sem commit, e o que e codigo sem teste real? Nao contar recursos de outro motor como ja existentes na factory.

### B. Identidade dos jornalistas
3. Quais campos de persona chegam ao Luna em draft, review e respin? O que vem do backend dinamico, o que vem de arquivo de prompt, o que efetivamente sabemos e o que nao conseguimos comprovar sobre o run?
4. Ha orientacao ativa para o agente **agir como o jornalista** durante pesquisa, contraponto e revisao, alem de reproduzir voz no artigo? Ate onde bastaria ajuste de instrucoes, sem reescrever DNA?
5. Como verificar fidelidade e criatividade das tres personas sem revelar/copiar seus DNAs ou exigir chamadas pagas nesta auditoria?

### C. Dialogo estruturado e revisao
6. Conferir a suspeita de que `respin.md` nao recebe a materia anterior (`{draft}`) apesar de o workflow mante-la em contexto. Confirmar o caminho preciso e seus impactos.
7. Como o review devolve observacoes, correcoes, perguntas e URLs? O jornalista pode atualmente responder justificando cada item, contra-argumentar e pedir esclarecimento SEM reescrever tudo? Que informacao se perde em `_factory_verdict`, `notes` e na remontagem de prompt?
8. Como introduzir dialogo de perguntas e respostas com identificadores por pendencia, severidade, evidencia, status e historico limitado, sem repetir discussao e sem reaprovar alegacoes sem fundamento?
9. Que diferenca existe entre erro demonstravel, ambiguidade/incompreensao, lacuna pesquisavel, sugestao de estilo e bloqueio real? Como definir sem deixar o modelo alterar a politica editorial?

### D. Pesquisa e encerramento
10. Verificar se o loop `passes < respin.passes` impede executar pesquisa pedida no ultimo review, mesmo com rodadas de pesquisa sobrando. Separar limites de pesquisa, dialogo e reescrita; estimar minimo ajuste seguro.
11. O que deve acontecer quando o dialogo esgota orcamento/turnos ou quando resta divergencia: `blocked` editorial, `needs_human_decision`, `awaiting_research`, `budget_exhausted` etc.? Quais estados ja existem e que mudancas de schema seriam necessarias?
12. Verificar retomada apos falha/reinicio e idempotencia de chamadas SIWC/DBOS, evitando consumo duplicado de creditos.

### E. Memoria temporaria e historico
13. Mapear exatamente SQLite `factory_queue.py`, checkpoints DBOS por run, `call_journal.py`, diretorio de artefatos e `archive.py`: o que pode ser reaproveitado e o que NAO e memoria conversacional.
14. Propor **duas alternativas de minima intrusao** para registrar e recuperar memoria pequena por historia, com identificadores, hashes e versionamento. Avaliar se usar SQLite existente, arquivo local versionado por run ou combinacao, sem outro sistema de orquestracao.
15. Descrever ciclo de vida: inicializacao, cada pergunta/resposta, resumo compacto, encerramento, acervo de fatos com fontes e confianca, isolamento entre materias, privacidade, auditoria, retencao/expurgo e consultas futuras por novas pautas. Nao tratar opiniao/rumor como fato.
16. Como anexar dossies estruturados `revista-back.coletor.v1` da coleta aos agentes reais sem recriar o motor antigo? Tratar isso como dependência/adjacencia, nao como autorizacao de integracao.

### F. Testes e viabilidade
17. Quais testes atuais verificam somente mecanica simulada e quais comprovam contexto real, interlocucao, persona e qualidade? Identificar testes faltantes.
18. Especificar testes offline, deterministas, com exemplos System76: tres precos provocam perguntas; jornalista responde com evidencia ou incerteza; noticia pre-lancamento nao exige benchmark inexistente; afirmacao falsa continua bloqueada; draft anterior e enviado; conversa nao repete pergunta resolvida; limite de custo gera encaminhamento correto; retomada preserva memoria e nao duplica inferencia.
19. Estimar alcance e risco de tres opcoes: (A) prompt apenas; (B) ajuste pequeno de prompts+contratos+passagem de contexto; (C) memoria persistente+dialogo estruturado e estado. Dizer o que exige migracao, efeito em checkpoints ja existentes, testes, custo de tokens/rodadas e risco de regressao.
20. Dar recomendacao tecnica, ordem sugerida de implementacao futura em etapas pequenas e reversiveis, com criterios verificaveis de aceite. Nao implementar.

## 4. Regras de execucao desta missao

- **Somente leitura** do codigo, docs, schemas, testes e artefatos ja existentes. Nao alterar prompts, DNAs, regras, limite de ciclos, banco, workers, branches, commits, repos, configuracoes ou ambiente. Nao abrir PR.
- Nao executar SIWC, Luna, chamadas de inferencia ou testes E2E pagos. Nao reprocessar fila de 38 pautas, nem disparar publicacao, coletor ou pesquisa externa desnecessaria.
- Nao revelar credenciais, tokens, prompts privados integrais, DNA completo ou contexto privado em relatorio publico. Relatorio tecnico detalhado deve ficar apenas em caminho LOCAL PRIVADO ou outro destino privado explicitamente autorizado. **Nao subir esse relatorio ao repositorio publico**, nem em branch temporaria.
- Evidencias: citar arquivo, funcao, trechos/linhas, branch e commit; discriminar achado verificado, hipotese e recomendacao. Se o codigo real nao estiver acessivel, reportar a lacuna em vez de imaginar.
- Nao transformar a investigacao numa construcao paralela nem recomendar trocar de motor sem justificativa e aval da Direcao.

## 5. Formato de retorno ao diretor/Fundador

Entregar em portugues:
1. Sumario executivo curto: o Censurado atual consegue fazer isso? Com que alcance e limites?
2. Matriz de **cada item**: ja existe / parcial / nao existe / sem acesso para confirmar; evidencia; alternativa minima; risco.
3. Diagnostico objetivo das causas no run System76, separando comportamento editorial de limitacao do codigo.
4. Comparacao A/B/C com recomendacao fundamentada de adaptacao incremental.
5. Proposta de testes e criterio de pronto para futura homologacao, SEM executar.
6. Perguntas que somente a Direcao pode decidir; nao escolher politica editorial por conta propria.

**Pare antes de modificar qualquer coisa.** O Fundador e o diretor vao discutir o parecer e emitir ordem de implementacao separada, se aprovarem.
