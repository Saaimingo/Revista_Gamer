# ORDEM AO CODEX — Corrigir e comprovar a cadeia real do Coletor ao Revisor; implementar diálogo e memória editorial

**Emitida pela Direção da Revista Back / Fundador 6, em 31/10/2026.**
**Estado:** implementação autorizada pelo diretor nesta conversa, subordinada aos gates de proveniência e testes descritos abaixo.
**Prioridade:** ALTA. Não reconstruir a fábrica. Não criar motor paralelo. Não publicar edição.
**Repositório da fábrica:** `Saaimingo/revista-back-factory`, branch operacional de referência `codex/revista-back-factory-v0.1.4-20261030`, HEAD observado `312dbd2cecb65a3f01400118d1a5d4d2a79c4177`. Verificar checkout/dirty state e preservar mudanças não commitadas antes de editar.
**Fonte atual:** `Saaimingo/Revista_Gamer`, `main`, `coletor/`. O futuro repositório operacional exclusivo da revista será configurável, mas não deve ser criado ou migrado por inferência.

## 0. Por que esta ordem foi emitida

O coletor passou a entregar não apenas notícias, mas também radar e dossiês `revista-back.coletor.v1` completos com afirmações classificadas, linhas do tempo, fontes, divergências e lacunas. O diretor exige provar o caminho **A coletor → B GitHub → C fábrica/pesquisa/jornalista → D revisor** usando o dado realmente depositado, NÃO um conteúdo escrito pelo Codex nem fixture como falsa evidência de ponta a ponta. Etapas E e seguintes da revista permanecem fora do escopo.

Foi igualmente AUTORIZADO implementar, na factory atual, comunicação colaborativa jornalista/revisor e memória pequena e privada por reportagem, mantendo rigor factual integral. Antes da edição, usar a evidência já recebida; depois implantar em etapas verificáveis.

### Referências a ler antes de modificar

- `docs/engenharia/MISSAO-CODEX-VERIFICAR-VIABILIDADE-DIALOGO-MEMORIA-EDITORIAL-2026-10-31.md`.
- `docs/operacao/DIAGNOSTICO-FUNDADOR6-DIALOGO-EDITORIAL-2026-10-31.md`.
- `docs/operacao/PROPOSTA-DIALOGO-EDITORIAL-JORNALISTAS-REVISAO-2026-10-31.md`.
- Relatório privado local de viabilidade de 31/10/2026, já entregue ao diretor: consultar de forma privada sem enviá-lo para este repositório público.
- Arquivos da fábrica real: `automation/pipeline/src/collector.py`, `factory_queue.py`, `factory_worker.py`, `flow.py`, `context.py`, `render.py`, `adapter_siwc.py`, `call_journal.py`, `archive.py`, `automation/pipeline/tests/test_factory.py` e CONFIG/PROMPTS PRIVADOS montados em `factory-config/` (não copiar conteúdo integral em relatórios públicos).

## 1. Gate obrigatório: provar a origem real antes de afirmar ponta a ponta

1. A fábrica existente possui `GitHubCollectorSource` configurado para `Saaimingo/Revista_Gamer:main:coletor/`, com listagem GitHub API, download raw e validação do SHA de blob; `FactoryQueue` persiste snapshot, candidato, `story_id`, `candidate_revision_sha256` e `run_id`. Exibir comprovante para cada salto.
2. Na auditoria de consulta do Fundador, o arquivo real `coletor/2026-10-31-1840.md` tem blob Git SHA **`01101850f5e099aed0058690d08f03f37bdfdf53`**, nove notícias novas, doze itens de radar e três dossiês JSON `revista-back.coletor.v1`. Os três `linked_news_urls` do JSON coincidem exatamente com as respectivas notícias (TUXEDO Nano Pro Gen15, Pikmin Day, interfaces Steam Deck). O parser atual extrai somente a parte plana das notícias; não associa os dossiês.
3. **DIVERGÊNCIA DE PROVENIÊNCIA QUE NÃO PODE SER OMITIDA:** recalculando a candidata `System76 anuncia Thelio Prime compacto com Ryzen 9000 e opção de GPU dedicada` a partir do arquivo atualmente presente em `main`, `coletor/2026-10-30-0800.md` (arquivo com apenas um commit identificado, `ae1e3e19e69164e36ed8ab380be1690f4d007853`), segundo o algoritmo `parse_collector_markdown`, o Fundador obteve `story_id=story-5fa6ee7b30046e5f4ecf20f4`, `candidate_revision_sha256=92210fe12f8b4998204b9491172f113d31236ee0158635da78af8ebe72f6a013`, `run_id=rb-e3de5eda5607f7750a720475`. **Mas o run histórico relatado é `rb-05a34e3a8ddc9ff622e862e6`.** Reproduzir o cálculo usando diretamente o parser real, conferir `capture_path`, `capture_blob_sha`, `source_url_normalized`, `story_id`, `candidate_revision_sha256` e o run artefact. Verificar possibilidade de candidato injetado manualmente, mudança de normalização/algoritmo, outro documento, outro ramo ou erro no diagnóstico. Se a origem não puder ser demonstrada, classificar o teste System76 como **execução real de inferência sem proveniência GitHub ponta a ponta comprovada**, nunca como teste completo. Registrar conclusão e evidências.
4. NÃO modificar a fila para fazer o ID antigo coincidir; não inventar histórico. Não apagar estados ou resetar identificadores.

## 2. Gate de ingestão completa do coletor

1. Manter o conector GitHub e o parser Markdown legado compatíveis. Acrescentar leitura versionada e validada do JSON embutido em `coletor/*.md` sob `schema_version=revista-back.coletor.v1`; ligar `dossiers[].linked_news_urls` aos registros de notícia por URL normalizada, com hash, captura e `dossier_id`.
2. A pauta do jornalista deve receber resumo, cronologia, afirmações e classificações (confirmada, alegação comercial, contestada, rumor, não verificada, quando disponíveis), fontes oficiais/secundárias, contradições, questões abertas e links, preservando a informação original. O revisor deve receber o mesmo dossiê e a evidência realmente pesquisada.
3. Não misturar radar com notícias inéditas; radar deve ser contexto de acompanhamento, não ingressar automaticamente como nova notícia. Não duplicar pautas ao recuperar múltiplos dossiês, revisões ou links. Dossiês ausentes devem seguir no fluxo antigo sem quebrar a leitura.
4. O coletor **reúne inteligência, não certifica a fonte para a redação**. Diferenciar `collector_reported` de `journalist_source_read`. Preservar validação `_factory_source_provenance`: somente páginas efetivamente lidas/conferidas pela pesquisa da fábrica contam como lidas e potencialmente citáveis. Não converter texto sintético, trecho de busca ou afirmação do coletor em fonte independentemente confirmada.
5. Parser estrito e resiliência a JSON inválido, URLs canônicas, alterações no mesmo arquivo, múltiplos dossiês e links conflitantes. Exigir prova de que os três dossiês do arquivo real acima estão associados às três matérias corretas.
6. Preparar fonte por configuração `owner/repo/branch/path` para um futuro repositório operacional de dados da revista, isolado de documentos de governança. Não criar repositório agora, não puxar textos de chats, diretórios de blocos, issues operacionais ou material do Codex como matéria. Ingestão só do feed editorial permitido.

## 3. Corrigir passagem de contexto e implementar diálogo com rigor

1. Confirmar e corrigir `respin.md` ativo: o redator deve receber o draft anterior com hash, trechos aceitos, questões abertas, observações, evidências e alterações solicitadas. A versão anterior já existe em `context["draft"]`, mas não estava explicitamente inserida pelo template.
2. Criar contrato estruturado por pendência editorial com `issue_id`, alegação/trecho, gravidade, tipo da dúvida (inconsistência, falta de comprovação, atribuição, ambiguidade, forma), fonte associada, **pergunta objetiva do revisor**, resposta/argumento do jornalista e URLs/hashes de evidências, decisão e estado.
3. Permitir ida/volta entre jornalista e revisor **sem exigir reescrita completa somente para esclarecer uma dúvida**. Registrar justificativa e contestação fundamentada; o revisor pode e deve manter negativa em caso sem evidência, jamais flexibilizar o gate factual.
4. Separar afirmação `incorreta/contradita` de `sem confirmação/indisponível`; deixar o jornalista explicar com cautela e atribuição quando adequado ao gênero editorial, ou remover informação não sustentada. Notícia de lançamento não deve ser automaticamente tratada como benchmark independente. Não transformar ausências em fatos, rumores em confirmações, nem testes de fabricante em testes da revista.
5. Preservar DNAs aprovados dos três jornalistas (Carranca, Beto Cartucho e Nina Prisma). Reforçar, em instrução operacional separada, o uso consistente da voz aprovada na argumentação e escrita; não editar DNA, não forçar ironia artificial e não copiar personalidade do revisor sobre o autor.
6. Manter custo/turnos finitos configuráveis e diferenciados: pesquisa, diálogo e reescritas. Quando se esgotarem, registrar causa operacional distinta de `rejeição editorial fundamentada`, sem aprovação automática. Encaminhamento humano deve ser explícito, com todos os pontos em aberto. Não iniciar conversas infinitas.

## 4. Implementar memória editorial compacta por reportagem SEM outro serviço

1. Escolha técnica aprovada: aproveitar `article_run` e criar arquivo privado estruturado, versionado e de atualização idempotente no diretório de `run_id`, associado a `story_id` e `candidate_revision_sha256` (alternativa B da auditoria). Não exigir migração a banco central nem vetor store nesta etapa.
2. Persistir cada issue, pergunta/resposta, decisão, versão/hash do draft, evidência com proveniência, resolvido/pendente e um resumo compacto. O prompt do Luna recebe apenas os pontos relevantes, não todo histórico bruto. Isolar dados de cada matéria e de cada revisão da candidata.
3. Proteger crash/recovery e evitar duplicação de turnos, buscas e chamadas SIWC. Reutilizar DBOS e `DurableCallJournal` existentes, com checkpoint de escrita e testes de retomada.
4. Quando a pauta terminar, produzir um resumo de histórico/editoria privada, com fatos datados e fontes conferidas, incertezas declaradas e referências aos registros auditáveis. **Não apagar os arquivos brutos nem inventar prazo de expurgo sem política da Direção.** A memória temporária ativa pode ser compactada, mas retenção e descarte devem ficar pendentes de deliberação.
5. O resumo histórico não deve contaminar futuras pautas com alegações não confirmadas; qualquer dado reutilizado deve ser revalidado quando necessário.

## 5. Critérios verificáveis de aceitação e sequência de testes

**Fase 0: auditoria/correção de proveniência, sem inferência.**
- Inspecionar System76 e provar ou NÃO provar o elo com o arquivo real do GitHub pelo SHA e IDs. Documentar honestamente a discrepância dos `run_id`.
- Ler o arquivo real `coletor/2026-10-31-1840.md` diretamente da fonte GitHub, com prova de URL, branch, path e blob. Fazer teste de ingestão `poll-only` ou execução offline isolada, sem reprocessar 38 pendências do ambiente.

**Fase 1: ingestão do dossiê e contexto.**
- Teste offline usando bytes de uma coleta **real** do GitHub (não dados inventados). Validar 9 notícias, 12 itens de radar tratados apenas como radar, 3 dossiês e 3 associações corretas.
- Verificar com snapshot de prompt renderizado ou teste de contrato que informações de dossiê efetivamente chegam a `draft` e `review` e que nenhum dado de governança/Blocos/Codex é puxado como pauta. Não expor prompts integrais em relatório público.

**Fase 2: diálogo/memória.**
- Testes offline determinísticos de issue e resposta, draft anterior, objeções de preços e de benchmark em anúncio, recusa justificada de alegação sem fonte, resumo de memória, ausência de contaminação entre pautas, rollback, crash/recovery e journal SIWC.
- Manter as antigas provas de idempotência, proveniência e segurança do gate. Não publicar nem arquivar artigo sem `accept` e validação de fontes.

**Fase 3: demonstração E2E limitada com conteúdo real.**
- Após passar fases anteriores, escolher e documentar **uma** matéria real do GitHub com dossiê (por exemplo TUXEDO, Pikmin ou Steam Deck) como candidato explicitamente isolado. Encaminhar ao fluxo `triage → assignment → queries → evidence → jornalista → revisor` com dados reais de coletor e acesso real às fontes, e no máximo a rodada de revisão autorizada para testar diálogo/memória.
- Fazer isto sem iniciar `factory --watch` em todo o backlog, sem editar 38 pendências, sem duplicar chamada paga e sem publicação. Preparar medição de chamadas/modelo/custo e escopo. Se SIWC estiver fora de condições seguras, relatar bloqueio e não simular um E2E como prova real.
- Entregar uma cadeia verificável de **commit/blob da coleta → snapshot → candidate ID → dossier_id → evidência verificada → prompt recebido pelo jornalista → draft → pergunta/parecer → resposta do jornalista → revisor → estado/memória final**. Se algum elo falhar, assinalar claramente.
- Tratar mocks como testes de código, e produção com Luna real como teste de comportamento; ambos são úteis mas nunca intercambiáveis.

## 6. Segurança, entrega, autonomia e pontos de parada

- Trabalhar no REPOSITÓRIO PRIVADO DA FÁBRICA, preservando branch e arquivos locais de outros trabalhos. Não expor tokens, credenciais, prompts privados, DNAs completos ou material de reportagens ainda inéditas no repositório público. Relatórios com conteúdo interno ou trechos de prompt devem permanecer em destino privado/local; neste repositório editorial público cabem somente status e resumos sem material sigiloso.
- Pode implementar o núcleo incremental e executar testes offline. Não criar novos serviços, motores paralelos, bancos centrais, filas alternativas ou automação de publicação.
- Deliberações editoriais não definidas (limite numérico definitivo de turnos, classificação final de casos sem evidência, prazos de retenção e política de reutilização de histórico) não podem ser escolhidas silenciosamente como norma. Usar defaults conservadores configuráveis se tecnicamente indispensáveis, marcando-os como provisórios e reportando ao Fundador antes de ativação contínua.
- Os limites de inferência real, se executada, devem ser explicitados no relatório; não operar sobre todos os candidatos. Preferir primeiro prova offline com dados REAIS do coletor, depois demonstração limitada e rastreada.
- Entregar: diagnóstico de origem da System76; fluxograma A–D do que de fato funciona; lista de arquivos e commits alterados; testes com contagem/resultados; evidência de uso real de dados GitHub; ligação dos três dossiês; prova de ida/volta e memória; limitações, divergências e próximos passos. **Não dizer "integrado" sem rastreio concreto.**

**Prioridade de execução: P0 rastreabilidade de origem → P1 consumo real dos dossiês → P2 dialogo/memoria e contexto → P3 verificacao E2E real controlada.**
