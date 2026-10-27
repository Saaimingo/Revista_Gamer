# ENG-CODEX-012 — ORDEM EXPRESSA DA DIREÇÃO AO CODEX
## Auditoria de PRs e arquitetura existente; corrigir o piloto real; decidir se Radar/bots agregam valor ou devem ceder a pesquisa direta dos agentes

**Data:** 27/10/2026  
**Status:** ORDEM DA DIREÇÃO PARA A PRÓXIMA RETOMADA, com preservação integral da execução pausada.  
**Escopo:** `Saaimingo/Revista_Gamer`, PR #44, Issue #42, PR #43 normativa.  
**Origem:** revisão independente do fundador registrada na [Issue #42, comentário 6432841694](https://github.com/Saaimingo/Revista_Gamer/issues/42#issuecomment-6432841694) e pedido explícito da Direção.  
**Este documento NÃO é um checkpoint de código já executado. É uma ordem operacional.** Diagnósticos de leitura estática ≠ testes executados; suspeitas ≠ erros provados.

> **Mensagem da Direção, sem margem para interpretação:** A fábrica não pode continuar eternamente travando em contratos, vírgulas, arquivos antigos, schemas ou recibos enquanto consome franquia e não entrega uma reportagem pronta. Audite TODO o contexto relevante e as PRs antes de retomar. Se o modelo de Radar/bots, criado para economizar buscas/tokens, estiver custando mais tempo e retrabalho do que entrega, apresente claramente uma alternativa mais simples em que os AGENTES façam a pesquisa na internet mediante ferramentas permitidas, com fontes reais e rastreabilidade. Não proteger a arquitetura atual por apego ao código já escrito. O sucesso é uma reportagem jornalística verdadeira, checada e visível no navegador, não o número de testes ou módulos.

## 0. ORDEM DE LEITURA E REGRA DE AUTORIDADE — faça primeiro

Ler, na sequência:
1. Este documento integralmente e o comentário da auditoria independente na Issue #42.
2. `docs/engenharia/ENG-CODEX-012-CHECKLIST-RETOMADA-MANHA.md`; `ENG-CODEX-012-CHECKPOINT.md`; `ENG-CODEX-012-MATRIZ-RASTREABILIDADE.md`, usando HEAD **atual**, não SHA histórico como suposta versão corrente.
3. As três especificações normativas **na PR #43** (arquitetura-mestra, matriz de falhas/aceite e contratos de integração); consultar pelo SHA real da PR, porque os arquivos não estão automaticamente presentes na branch #44.
4. `AGENTS.md`, decisões aprovadas e contratos/DNAs aprovados pelos setores **nas versões corretas**. Propostas e textos antigos não viram decisões por aparecerem no README.
5. O código e os testes de execução no HEAD da PR #44, e o **ledger/artefatos privados do run pausado em leitura somente** antes de qualquer escrita ou chamada.

**Precedência:** instrução específica recente da Direção e autorizações explícitas > contrato normativo vigente/decisão setorial aprovada com SHA > código vigente/estado real do ledger > documentos históricos. Em conflito: relatar, não inferir aprovação. Não redefinir DNA/persona, não converter mock em fato, não inserir custos nem ferramentas web por suposição.

### Cuidado com o checkout local
Esta ordem foi adicionada diretamente à branch remota da PR #44 **enquanto a execução estava pausada**. O Codex informou que possui alteração local ainda não validada em `motor_editorial/eng_codex_011.py`. **Antes de atualizar a branch local, fazer `git status`, preservar patch/diff local sem perda e sincronizar com segurança. Nunca `git reset --hard`, sobrescrita forçada, `pull --rebase` sobre worktree suja, nem descartar artefatos privados.** Não repetir `run`.

## 1. AUDITORIA DAS PRs: o passado pode estar contaminando o presente

**Inventário remoto observado em 27/10/2026:** 27 PRs, **23 abertas, 4 integradas** (até revisão posterior); não presumir que uma PR aberta entrou em outra. Revalidar contagem e bases ao vivo quando assumir. Classificar cada PR em planilha/matriz curta: número, finalidade, base/head e SHA, status aprovado/rascunho/histórico, código compartilhado/duplicado, se é ancestral real do HEAD #44, o que falta migrar e ação exata (nenhuma/consultar/importar pontualmente/encerrar como superseded/revisão humana). **Não fazer merge automático de PRs antigas nem fechar sem autorização da Direção.**

**Inventário das PRs verificadas:**
- **#3, #4, #6, #45 — integradas à main.** Base histórica núcleo v0.1/v0.2 e comercial; não reaplicar.
- **Engenharia histórica/empilhada:** #8, #10, #18, #24, #25, #26, #30, #34, #38, #40, #44. As ancestrais da trilha principal são herdadas em #44, mas **#38 é uma bifurcação divergente**, portanto a equivalência de medição/editorial precisa ser provada por diff/owner, sem merge em bloco. A branch ENG-011 é ancestral direto da #44; seus commits não constituem PR numerada nesse inventário.
- **Documentação e ordens de engenharia paralelas:** #29, #32, #36 e **#43**. #43 contém os três contratos normativos, mas segue **branch paralela**; não pressupor seus Markdown no checkout #44.
- **Bloco 02/personagens:** #13 (Carranca), #14 (assets), #19 (Beto), #21 (memória/skills NÃO aprovada), #27 (continuidade/Nina). Verificar manifestações/DNA e hashes reais antes de usar; não adotar propostas sem autorização.
- **Outros setores:** #16 (mocks de referência, não arte final liberada), #31 (fontes/acervo/direitos), #46 (Bloco 03 avaliando flipbooks; NÃO é requisito de alterar a fábrica nesta missão).

**Fatos de comparação de branches:** #44 está 22 commits à frente de `codex/eng-codex-011-live-factory` e não atrás; #44 vs `main` diverge (168 commits à frente, 6 atrás no instante auditado). Os últimos 6 da `main` observados são documentais/comerciais, não motivo para mesclar indiscriminadamente. #43 não é ancestral de #44; #38 diverge. Usar `git merge-base`, comparação de commits e hashes de arquivos para provar a linhagem; não interpretar "arquivo semelhante" como integração completa.

**Detectado: arquivos que contam uma história desatualizada.** `docs/governanca/STATUS-GERAL.md` descreve o estágio inicial, `docs/personagens/README.md` ainda declara personagens como pendentes/codinomes, `docs/engenharia/README.md` destaca ENG-007, `README.md`/Bíblia v0.1/`DECISOES.md` são históricos de 15–19/10. **NÃO apagar nem atualizar a história cegamente**; rotular claramente “histórico/superado”, criar um índice curto de estado operacional vigente, com links versionados, depois de confirmar decisões com a Direção. Remover apenas do fluxo decisório atual a autoridade indevida desses textos antigos.

**Pergunta obrigatória:** quais funções foram implementadas 2–3 vezes, em classes/runners diferentes, e que parte da arquitetura do Radar e de recuperação existe só para atender ao piloto ENG-011? Verificar responsabilidades de `workflow.py` (protótipo), `factory.py` (fábrica/simulação), `orchestration.py` (fila e ledger), `agent_siwc.py` (transporte/executor), `research_service.py` (pesquisa), `eng_codex_011.py` (harness real, ~3.310 linhas). Classificar código produtivo vs fixture/demo/harness vs histórico. Exigir **uma só responsabilidade canônica por gravação, estado, contrato e orçamento**, sem iniciar uma reescrita paralela.

## 2. BLOQUEIOS REAIS A CORRIGIR PRIMEIRO — antes de nova inferência

**P0-A — recibo gravado duas vezes (confirmado no piloto e no código remoto):** `agent_siwc.py::persist_response` grava usage receipt de task/attempt. `eng_codex_011.py::_task_output` chama `AgentUsageArtifactStore.write` de novo com conteúdo diferente, provocando `ValueError` pela regra correta de imutabilidade. Reutilizar e verificar recibo existente, nunca sobrescrever. Métricas de análise posterior em artefato derivado distinto, se necessário. Fazer teste de crash após persistência e replay com **0 novas chamadas SIWC**.

**P0-B — checkpoint parado em `triage_agent/call_started`** apesar de o ledger registrar task `succeeded`. `Checkpoint.resume_after_triage` exige `succeeded` no último evento e hoje rejeita a fronteira real. Somente aceitar `call_started` se tarefa, bytes, manifest, receipt, tentativa=1, modelo/esforço e hashes forem verificados na raiz do MESMO run; registrar reconciliação idempotente.

**P0-C — saída derivada pode estar ausente:** o caminho de `resume` em `eng_codex_011.py` lê `structured-outputs/<triage-task>.json` antes de reconstruí-la. O erro ocorreu antes da escrita deste arquivo. Regenerar derivado só da resposta SIWC concluída e autenticada por hashes, **sem inventar resultado nem repetir triagem**. Cobrir esse caso com regressão específica. Os P0-A/B/C formam **UM defeito operacional integrado**; correções isoladas sem teste do conjunto não bastam.

**P1-D — nova claim após provider (defeito lógico de leitura estática, ainda NÃO provado por regressão):** `research_service.py::execute` lê mapa `claim_rows` antes de `provider.search`. Em seguida calcula `available_claim_kinds` usando esse snapshot antigo depois que provider possivelmente gravou uma nova claim. Pode deixar evidência nova em `missing_evidence` e produzir `partial` falso. Testar provider fake que **persiste claim inédita do tipo exigido com source/document/lineage válidos**; se reproduzir, atualizar leitura pós-retrieval e validar novamente. Não chamar web/agent para depurar isso.

**P1-E — divergência potencial de modelo no replay:** `agent_siwc.py::_finalize_output` aceita modelo igual ou versão com sufixo do slug, enquanto `eng_codex_011.py::_load_succeeded_role_output` exige modelo exato. Harmonizar políticas para não rejeitar um resultado já aceito. É hipótese, **não bloqueio real comprovado**.

**P1-F — fragmentação de recovery por incidente:** há vários `resume_after_*` no harness ENG-011. Antes de adicionar mais um remendo específico por erro, avaliar se um contrato geral de tarefa concluída + artefatos imutáveis resolve casos de recovery no owner compartilhado. Evitar refatoração de meses antes de avançar no run atual.

**IMPORTANTE:** A auditoria independente viu o GitHub remoto, **não o patch local pendente**; os diagnósticos acima precisam ser reconciliados com `git diff` local, não sobrescrever mudança válida. Auditar o patch antes de editar.

## 3. RETOMAR A MESMA EXECUÇÃO REAL, SEM VOLTAR À ESTACA ZERO

**Run ID:** `eng-codex-012-20261027T025920Z-e207b61f01c5`  
**Raiz:** `%USERPROFILE%\.codex\Revista_Gamer\eng-codex-012-live-factory`  
**Resposta triagem SHA-256:** `f9b66c4bc9efd2fe2fa8f7e5917b72bb376687a0a4c7297add2e65abaa5d94ce`  
**Recibo triagem SHA-256:** `0a23b5433b2827dab0d67d5ecd044b58980bb0ba2181ac6d0ef31a5e78ce1ec0`  
**Modelo autorizado:** `gpt-6-luna` / `max`; não trocar sem autorização.  
**Pesquisa no piloto:** 3 de 4 tentativas de fonte usadas; Proton/SDL HTTP 200; Godot bloqueado; **no máximo 1 consulta pública restante** dentro da autorização, sem retry. Catálogo/modelo já comprovado; NÃO repetir GET desnecessário. Triagem real `triage_analyst` já concluída: 10.775 tokens, tentativa 1, 10 candidatos, armazenada; NÃO repeti-la.

**Sequência mandatória:**
1. Fazer `git status`, conferir alterações locais e diferenças remotas, guardar patch e verificar no privado apenas leitura até comprovar integridade. Não clonar root histórico para simular run novo.
2. Corrigir P0-A/B/C e testar crash/recovery com fixtures locais específicas. Testar P1-D. Fazer commit/push do código e checkpoint em #44, preservando PR draft.
3. Executar **`resume` na MESMA raiz/run/ledger**, e verificar na prática que houve 0 nova chamada de triagem, 0 novo scan e 0 novo catálogo. Não usar `run` se `resume` bloquear. Registrar falha e estado exato, sem repetir efeitos externos incertos.
4. Prosseguir com **investigador real → editor real → jornalista/persona aprovado → pesquisa complementar realmente necessária → mesmo jornalista → fact-check real → revisor real → correção limitada e rechecagem → prévia HTML com texto e imagem interna aberta e examinada no navegador**. Não forçar pauta que não tem base factual; a triagem inicial marcou Proton/SDL como monitoramento sem changelog. Chegando a `no_story_yet` ou `hold` legítimo, registrar decisão editorial correta, não chamar isso de bug.
5. Medir por etapa: id/run/task, modelo/esforço efetivos, tokens, tempo, rede pública efetiva, cache/hits, status, documentos e claims utilizáveis, hashes das versões, onde houve espera/hold e por quê. Marcar prova real ≠ replay ≠ fake.
6. U08 (preview real de navegador) e U09 (isolamento de duas pautas com uma bloqueada) não podem ser aprovadas por teste de fixture. Permanece `published=false`, revisão e autorização humana pendentes. Sem merge, deploy, publicação, API paga, nova autorização implícita ou fonte/destino não liberados.

## 4. A QUESTÃO ESTRATÉGICA DA DIREÇÃO — ROBÔS/RADAR OU AGENTES PESQUISANDO DIRETAMENTE?

**Esta decisão agora é OBRIGATÓRIA como análise técnica honesta, não como justificativa para construir mais componentes.** O Radar com bots determinísticos, ingestão, índice e cache foi proposto para poupar custo das inferências; porém a fábrica está perdendo tempo e ainda não entrega a matéria ponta a ponta. **Economia de tokens não compensa uma linha de produção que não funciona.** Comparar:

**Opção A — Radar/bots atuais:** fontes registradas, ingestão, cache, triagem, indexação, pedido complementar pelo Motor, controle próprio de orçamento. Ganhos esperados: repetibilidade, cache, rastreabilidade e economia em escala. Custos reais: manutenção de scanners/parsers, schema/ledger, debugging, falhas de handoff, fontes limitadas.

**Opção B — agentes pesquisam na web diretamente:** investigador/jornalista recebe ferramentas de busca/navegação **legitimamente disponíveis e expressamente autorizadas**, faz busca real, abre fontes, registra URLs/trechos admissíveis/evidências e devolve achados ao mesmo dossiê versionado; checagem independente permanece. **Não presumir que SIWC tem navegação/browsing nativo!** Verificar se interface efetivamente dispõe de ferramentas e chamadas; se não, documentar adaptador leve possível e restrições de OAuth/Plus/custos, sem habilitar integração não autorizada. Não permitir que o agente invente URL, alegue leitura sem fetch, ignore direitos/robots, navegue em credenciais ou faça buscas ilimitadas.

**Opção C — híbrida enxuta:** discovery/Radar simples e fontes cadastradas como sinais, mas **investigação real via ferramenta web sob demanda do agente**, sem o complexo circuito de bots para cada pergunta; indexar/cachear apenas o que comprovadamente reduz trabalho e não impõe gargalos. Um fallback seguro evita impedir a reportagem só porque parser de um source falhou.

**Faça uma tabela concreta com:** complexidade de código e de operação, gargalos reais de A, capacidade de pesquisar games/hardware/mods além dos três repos GitHub, cobertura de fonte, custo de manutenção, tempo perdido com falhas, tempo de produção por pauta útil, tokens e chamadas por reportagem completa, qualidade/rastreabilidade das evidências, direitos, privacidade, possibilidade de auditoria, segurança e plano de migração/reversão. **Use dados realmente registrados** de ENG-011/012; onde faltam dados, escreva “não medido”, não invente números nem empate artificial.

**Critério de decisão:** se a cadeia A continuar bloqueando por integração/limitação de fonte e B ou C for viável, apresente recomendação por **simplicidade, reportagem concluída, qualidade de prova e custo TOTAL**, não apenas tokens. Se o Radar provar valor, mantê-lo como discovery/caching, **não como obrigação que impeça trabalho editorial útil**. A mudança arquitetural total precisa de **proposta e aprovação expressa da Direção**; não desativar bots, alterar provedor, expandir internet ou consumir consultas extras por conta própria.

**Prova comparável:** primeiro análise no papel e nos registros reais existentes; depois, se já houver autorização de rede suficiente, demonstrar um teste mínimo controlado com MESMA pauta e MESMOS critérios. O orçamento registrado de **1 consulta pública restante não autoriza duas arquiteturas consumirem novas buscas**. Sem autorização extra, deixar ensaio B/C pendente com desenho claro, enquanto recupera e usa o trabalho já pago na execução A.

## 5. DEFINIÇÃO DE PRONTO E ENTREGAS — não passar o dia remendando

**Entregar, em ordem, sem alongar a missão indefinidamente:**
- **Relatório curto de auditoria por PR** com mapa de ancestralidade, status atual, duplicaçõ​es e arquivos de autoridade ultrapassados. Separar “comprovado”, “provável” e “histórico”; nenhuma PR ou DNA alterada só por estar aberta.
- **Correção do run pausado, com teste integrado de recuperação** que garanta tarefa succeeded, mesmo receipt, mesmo hash, `attempts=1`, 0 rede/0 SIWC extra; log de `resume` real, ou bloqueio exato se algo verdadeiramente irrecuperável.
- **Relatório editorial ponta a ponta real** contendo saída completa quando as evidências permitirem, ou gate factual/humano justificado quando não permitirem; distinguir falha técnica de falta de fatos. Meta prática: reportagem pronta para avaliação humana em prévia local, sem publicação. Nenhum resultado de mock substitui isso.
- **Parecer de A/B/C (Radar vs web direta vs híbrido)** com recomendação justificável e os limites das ferramentas de agentes. Apresentar proposta à Direção antes de desligar o Radar.
- Atualizar `CHECKPOINT`, `MATRIZ-RASTREABILIDADE`, checklist e PR #44 com SHA, testes, tokens, chamadas, bloqueios e próximo comando exato. Se a franquia terminar, pausa limpa com zero retentativa e estado preservado.

**Ordem final:** não abrir mais uma arquitetura paralela, não gastar sessões em novas fixtures genéricas, não “concluir” com testes offline, não acrescentar 20 novos contratos enquanto o mesmo receipt quebra a cadeia. Use regressões pequenas para consertar BUGS CONCRETOS; então **execute os agentes reais e veja a reportagem percorrer a esteira**. O sistema deve ser mais simples e confiável na saída desta missão; se não for, recomende remover seus gargalos.

**Lembrete:** esta diretiva não executa automaticamente ferramenta, não libera limite extra da pesquisa do piloto e não substitui aprovações humanas de custo, marca, direitos ou publicação.
