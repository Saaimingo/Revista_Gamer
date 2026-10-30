# REVISTA BACK | ORDEM CONSOLIDADA DO FUNDADOR: FÁBRICA AUTÔNOMA, PARECERES 02/03 E VPS

**Origem:** Direção da Revista Back e coordenação do Bloco Fundador, conversa de 29/10/2026.
**Destino:** Codex como ENGENHEIRO de software; Blocos 02/03/04/05 para leitura cruzada.
**Natureza:** handoff integral de visão, decisões, lacunas, prioridades e aceite. NÃO é relatório de que o código já existe. É ordem para diagnóstico, preservação e IMPLEMENTAÇÃO LOCAL segura nas etapas especificadas; não autoriza novas inferências reais SIWC, publicação, gastos, mudança de DNA, merge em main, registro de contas ou deploy de VPS.
**Referências normativas:** os pareceres originais dos Blocos 02 e 03 integram esta ordem por referência, integralmente, não apenas pelos resumos abaixo. Leia o texto completo de ambos ANTES de modificar código. Em conflito de interpretação, prevalecem decisões expressas do diretor; não substituir documentos das áreas por opinião da engenharia.

## 0. LEITURA OBRIGATÓRIA E CONTEXTO

**Bloco 02 — relatório COMPLETO com 12 achados e fontes:**
https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/continuidade-checkpoint-2026-10-24/docs/personagens/diagnosticos/PARECER-BLOCO02-PILOTO-CARRANCA-E-TRIO-2026-10-29.md
Handoff: https://github.com/Saaimingo/Revista_Gamer/issues/49

**Bloco 03 — relatório COMPLETO com análise das 6 telas/10 faces e contratos B03-G01…G08 e B03-I01…I06:**
https://github.com/Saaimingo/Revista_Gamer/blob/main/docs/visual/ESPECIFICACAO-CORRETIVA-IDENTIDADE-LEITOR-BACK-2026-10-29.md
Handoff: https://github.com/Saaimingo/Revista_Gamer/issues/48

**Checkpoint do Codex na branch experimental (histórico parcial e anterior às chamadas reais):**
docs/engenharia/REVISTA-BACK-RETOMADA-PRIMEIRA-EDICAO-2026-10-29.md

**Checkpoint LOCAL do clone Censurado:**
D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md

**Worktree experimental do leitor e backups, conforme checkpoint:**
C:\Users\saimi\Revista_Gamer-primeira-edicao
Branch: codex/revista-back-primeira-edicao-20261029
Leitor: docs/visual/prototipos/revista-back-leitor-piloto/index.html
Design QA: docs/visual/prototipos/revista-back-leitor-piloto/design-qa.md

**Fontes históricas adicionais:** decisões D-011 e D-018; Issue #15; leitor v0.3; ZIPs aprovados do Bloco 03 na máquina local; PRs #13, #14, #19 e #27 com identidades e amostras; issue #42, PR #44 são histórico de fábrica anterior, NÃO ordem para recriá-la ou alterá-la.
**PRs, documentos e arquivos originais devem ser preservados**, com SHA, branch e data. Não presumir que os ZIPs ou artefatos locais estejam disponíveis no GitHub ou que arquivos privados sejam publicáveis.

## 1. A DECISÃO CENTRAL DA DIREÇÃO: ENGENHEIRO ≠ AGENTES OPERACIONAIS

O Codex é exclusivamente o **engenheiro/codificador** que constrói, integra, testa e conserta a fábrica. Ele NÃO será o operador diário que transporta notícias entre setores, chama um agente por vez, reapresenta textos para revisão ou inicia a montagem. Sua franquia de Codex NÃO deve sustentar a operação editorial normal.

O sistema em produção utilizará agentes de função, com seus próprios papéis, DNAs, instruções e contextos: triagem, curadoria/editor de pauta, investigador/pesquisa, jornalistas Carranca/Beto/Nina, checagem factual/revisor, setor de imagens/direitos e, em etapa POSTERIOR separada, editor de edição/diagramador/montador. Esses agentes podem usar o adaptador de inferência autorizado (atualmente GPT-6 Luna por OAuth/SIWC quando elegível, e adaptadores futuros configuráveis) sem fingir que o modelo se transformou numa sessão Codex. **Codex constrói; a fábrica executa.**

A Direção quer apertar PLAY e ver a execução independente, sem precisar supervisionar a passagem de cada setor. Um agente desperta apenas quando há tarefa, entrega resultado e cessa a inferência; o próximo é acionado automaticamente. Não usar agentes permanentemente ocupados por ociosidade. O motor persistente e determinístico controla filas, estado, transições e recuperação; a IA faz decisões semânticas, pesquisa e redação. Modelo pequeno como LFM3/d1 foi SOMENTE hipótese discutida, **não decisão**, e NÃO deve ser instalado como novo orquestrador.

**Problema a diagnosticar na implementação atual:** provas isoladas e demonstrações conduzidas manualmente pelo Codex NÃO mostram que existe o fluxo automático de começo ao fim. Identificar precisamente quais transições, gatilhos e filas já estão implementados no Censurado/DBOS e quais ainda são manuais. Não construir segundo motor por reflexo.

## 2. CICLO A: CAPTAÇÃO → MATÉRIAS APROVADAS → ACERVO (NÃO MONTAGEM)

### 2.1 Entrada atual
Captador agendado do ChatGPT pesquisa e grava no repositório Saaimingo/Revista_Gamer, branch main, diretório coletor/, atualmente às **08h00 e 18h40**, America/Sao_Paulo. Os arquivos confirmados das duas datas 28 e 29/10 dão evidência real de coleta, persistência e conferência contra URLs anteriores. O captador agora também possui instruções de radar de continuidade, rumors, confirmação/desmentido, até 12 pautas em aberto; conferir implementação nas rodadas seguintes, NÃO presumir recurso validado só por existir no prompt da tarefa. A tarefa agendada não implica execução local no computador nem dispara automaticamente o DBOS.

**Contrato da campainha:** um monitor de entrada detecta arquivo novo sem depender do Codex. Alternativas a avaliar: polling incremental/reconciliação de GitHub (primeira fase local, mesmo se PC esteve desligado), ou eventos GitHub Actions/webhook para VPS. Não inferir que GitHub liga PC desligado; tarefa nova fica pendente até retorno do ambiente local. Usar caminho, SHA/commit, batch_id e chave de idempotência para não reprocessar uma coleta/mesma pauta por engano. Se houver polling, evitar rate limits e duplicação mesmo com arquivos antigos. Identificar alterações em relatórios de rumor sem confundir mesma notícia com atualização substantiva.

### 2.2 Sequência em cascata
1. Monitor detecta rodada nova, persiste evento, cria batch e acorda orquestrador/DBOS.
2. Triagem avalia novos registros, histórico/rumores, relevância, duplicidade semântica, pertinência e propostas de pauta. Sem obrigatoriedade de uma matéria por notícia.
3. Curadoria/editor de pauta define ângulo, gênero, prioridade, profundidade esperada, jornalista adequado, razões de roteamento e perguntas de apuração. A triagem do captador é apenas ponto de partida.
4. Pesquisador/investigador obtém fontes complementares, documentos oficiais, histórico, comparações e comunidade quando pertinente e legalmente acessível. Dossiê por alegação/pergunta; registrar fonte original, data, acesso e limites. O jornalista pode solicitar PESQUISA ADICIONAL DURANTE a escrita, e a devolução precisa retornar à **mesma matéria, mesma identidade e mesmo estado da tarefa**, com novas evidências. Se revisor apontar lacuna factual, permitir complementação antes de correção. Sem inventar benchmarks, testes próprios, conteúdo de fontes não lidas, nem burlar login/paywall/termos.
5. Jornalista redige corpo real, completo, com voz e profundidade apropriadas; devolve campos estruturados de fontes usadas, claims, gênero, necessidades de imagem/arte, módulos visuais possíveis, detalhes a conferir e lacunas pontuais. Não confundir conteúdo da reportagem com controles operacionais.
6. Revisor/checador verifica afirmações, fontes citadas, integridade, profundidade editorial, voz e adequação à pauta; devolve ACEITO, CORRIGIR ou BLOQUEIO com achados objetivos. Correções retornam AUTOMATICAMENTE ao mesmo jornalista; a fábrica gere as transições, não Codex.
7. Matéria aprovada editorialmente entra em **acervo/carteira de matérias aprovadas**, versionada, com texto, fontes, metadados, autor/persona, imagem requerida, créditos, status de direitos e histórico. Isto conclui o CICLO DE PRODUÇÃO DE MATÉRIA. **NÃO acionar montagem de edição automaticamente.** Artigo aprovado pelo revisor ≠ edição aprovada/publicável pelo diretor.
8. A fila continua com pautas pertinentes para Carranca, Beto, Nina conforme curadoria e capacidade; não forçar um número por jornalista a cada coleta nem geração sem notícia válida. A quantidade de matérias e de dias necessários para completar a grade SERÁ DEFINIDA DEPOIS pela Direção, não pelo Codex.

### 2.3 Ciclo de revisão, decidido pelo diretor (3 pares máximos)
- Passagem 1: jornalista escreve (J1), revisor avalia (R1). Se aceitar, acervo.
- Se rejeitar: o MESMO jornalista recebe feedback e evidência, corrige (J2), revisor avalia nova versão (R2). Se aceitar, acervo.
- Se rejeitar de novo: última correção do mesmo jornalista (J3), terceira avaliação (R3). Se aceitar, acervo.
- Se houver terceira rejeição, **BLOQUEAR** matéria, preservar todas as versões, pendências e histórico, permitir intervenção humana; nenhuma quarta tentativa automática.
- Solicitação de pesquisa complementar é um subfluxo rastreado, NÃO uma reescrita artificial só para contar tentativa. Contar rodadas por versão revista. Revisor deve avaliar cada novo hash; nenhuma avaliação de versão antiga autoriza a nova.
- **Retries técnicos** não são **rodadas editoriais**. Chamada SIWC com resultado uncertain, falha de rede ou falta de checkpoint NÃO pode ser repetida automaticamente. Os checkpoints precisam assegurar execução no máximo uma vez enquanto o estado externo é incerto; efeitos idempotentes. Guardar consumos por papel e por rodada.
- Caso do Gothic: J1 e R1 já aconteceram em inferências reais (respectivamente 21.968+717 e 22.383+424 tokens), com parecer de 1 bloqueio e 5 polimentos; o artigo está pendente e preservado. Não refazer nem fingir que o texto foi aprovado. Continuar J2/R2/J3/R3 SOMENTE após nova autorização explícita para uso SIWC, conforme normas de produto e credenciais válidas. O diretor deseja teste do **ciclo completo**, não interrupção artificial a cada passo, mas é necessário combinar previamente escopo/limites e autorização para a execução real.

### 2.4 Imagens e direitos, parte da cadeia editorial
Jornalistas/pesquisadores devem INDICAR quando precisam de imagens e quais: captura oficial, vista de hardware, material promocional, retrato da persona, imagem de contexto, comparação, zoom, créditos e páginas/press kits candidatos. O sistema precisa produzir solicitações estruturadas ao acervo de imagens/Bloco 05, sem esperar que o diretor descubra depois os buracos. O setor de mídias verifica procedência, licença/uso editorial permitido, disponibilidade, créditos e restrições, tenta fontes oficiais legítimas e registra pendências. Se a imagem exigir login/autorização ou direito não comprovado, **não contornar**; sinalizar que o diretor poderá intervir posteriormente. Uma matéria pode ser aprovada editorialmente com pendência de mídia explícita para seleção visual posterior, desde que nenhuma imagem irregular seja publicada. **Nunca regenerar retratos oficiais dos cronistas**; carregar PNG aprovado por referência/ID/hash e respeitar o nível de disponibilidade de cada branch.

## 3. CICLO B SEPARADO: ACERVO → GRADE → DIAGRAMAÇÃO → REVISTA

Somente quando Direção/editores definirem grade, quantidade e distribuição de matérias, selecionar artigos do acervo; editor de edição planeja ordem, capa, editorias e extensão; setor de imagens prepara assets permitidos; diagramador/montador compõe no sistema visual oficial B03-01 a B03-05; inspeção real em navegador; aprovação humana de edição; publicação SOMENTE após autorização explícita. Não publicar em função de cron automático do Captador. Não usar páginas vazias ou documentação de processos para completar uma quantidade artificial de faces.

O sistema de reportagem é contínuo, com acervo acumulativo. A periodicidade alvo de revista NÃO equivale a produzir edição em toda coleta. A seleção/quantidade da grade são decisões FUTURAS. Não inventar número definitivo de páginas ou artigos.

## 4. B02 | PERSONAGENS E JORNALISMO: 12 ACHADOS, TODOS OBRIGATÓRIOS

Os 12 achados originais devem ser lidos NA ÍNTEGRA no parecer do Bloco 02. Síntese executiva fiel, com responsabilidade e direção de correção:

- **A01, atribuição da pauta/persona:** Gothic Photo Mode/Marvin Mode/cosméticos tende a BETO, não Carranca sem ângulo técnico justificado; curadoria define primary_angle, why_this_persona, gênero e possibilidade de override, nunca roteamento por conveniência de teste.
- **A02, gênero mal reconhecido:** notícia factual/guia explicativo/prévia/investigação/análise/review/teste possuem padrões probatórios distintos; ausência de teste impede veredito de gameplay/desempenho, NÃO explicação detalhada de anúncio oficial.
- **A03, pesquisa superficial e fontes dependentes:** THQ Nordic + RPG Site ecoando mesmo anúncio não é investigação plural; dossier por claims/perguntas, fontes primárias, história anterior e outras evidências quando existirem; não preencher lacunas com invenção.
- **A04, DNA transmitido não equivale a DNA incorporado:** sete arquivos/hashes de Carranca validam integridade, não voz. Derivar perfil de execução enxuto com precedência, modo reportagem/veredito/resposta, sem reescrever o DNA criativamente aprovado, e validar fidelidade qualitativa.
- **A05, contexto excessivo versus texto curto:** checkpoint estimou prompt preparatório de 133.486 caracteres; verificar prompt realmente ENVIADO, repetições de políticas, cortes, limites de saída, 44.351 tokens de entrada/1.141 de saída nas chamadas reais, e orçamento por seção. Compactar hierarquicamente sem perder instruções essenciais nem elevar consumo automaticamente.
- **A06, incerteza repetida virou texto defensivo:** atribuir afirmações onde necessário, localizar ressalvas relevantes, evitar refrões de 'não testamos'; o jornalista deve destrinchar o objeto e contextualizá-lo, sem falsificar experiência.
- **A07, revisão sem retorno:** implementar J1/R1 → J2/R2 → J3/R3 com severidade, trechos, claim_id, evidence_id, draft_hash, nova checagem e gates; preservar originais/versões e bloqueio por terceira reprovação.
- **A08, bastidores na revista:** separar editorial_debug privado de reader_preview limpo; proveniência/parecer/status no histórico administrativo, não ocupando a capa e miolo; título completo só abertura, cabeçalho discreto nas continuações; prévia privada sinalizada sem alertas repetidos.
- **A09, avatar ausente:** retrato aprovado Carranca Protótipo A, referenciado no PR #14, precisa ser resolvido como UI asset pela montagem (persona_visual_ref/asset_id, hash, fonte, crédito), não inventado pelo redator; verificar assets do trio nas PRs respectivas.
- **A10, confusão entre captura e citação:** Gematsu originou pauta mas não foi lida como prova nessa execução; separar discovery_source, fulltext_accessed, evidence_consumed, cited_by_writer, approved_by_review. Não citar como fonte consultada algo que não foi aberto.
- **A11, gate não exige profundidade:** briefing deve pedir required_topics, topic_evidence_refs, comparison_targets, proposed_visuals, open_questions, genre, expected_depth; só aceitar cobertura factual suficiente ou escopo reduzido declarado. Notícia não é relatório de ressalvas.
- **A12, testes de hash não são provas de qualidade:** avaliar dois eixos independentes P=persona e J=jornalismo para Carranca, Beto e Nina (T01–T16 quando aplicável); não contar bordão como fidelidade, não declarar trio homologado a partir de tests mocks.

Responsabilidades: Bloco 02 define identidade e voz (sem mudança por conta própria); Bloco 04 orienta gênero/curadoria/profundidade/pesquisa/revisão; Bloco 05 direitos; Bloco 03 layout; Codex integra e comprova entrada→saída. Não atribuir culpa específica ao modelo sem examinar prompts reais, evidências, raw outputs e parecer completo. **Preservar as amostras e os DNAs aprovados**, inclusive o que já foi decidido sobre Nina e Beto.

## 5. B03 | CONTRATO VISUAL OBRIGATÓRIO, SEM REABRIR DECISÕES

Leitura integral obrigatória de B03-G01…G08, B03-I01…I06, análise tela a tela, prioridades P0/P1/P2 e critérios de aceite na especificação do Bloco 03. A avaliação do diretor foi: a prévia HTML é vitória técnica, mas **não representa a identidade aprovada**. Não considerar 'design QA passed' aprovação artístico-editorial.

Problema técnico concreto no leitor piloto: variável CSS --sheet-w:min(43vw,505px), além de palco central limitado. A revista aparece como pequeno livro dentro de moldura no desktop e não ocupa toda a tela útil. O hambúrguer aparece fora da face. A revista do Bloco 03 deve ocupar o viewport, não simplesmente caber nele.

- Capa isolada, marca BACK grande no alto, composição cinematográfica dominante de ponta a ponta, chamadas laterais e manchete inferior; sem área de patrocinador quando não houver publicidade real. Contracapa isolada full viewport com fechamento digno.
- Mobile: uma face ocupa integralmente área útil da tela; nenhum cabeçalho externo reduz espaço editorial. Desktop/tablet largo: dupla ocupa aproximadamente 50% esquerda/50% direita de área útil, dobra discreta; quando zoom/tela não permitirem legibilidade, uma face. TV também segue a regra, sem linhas de texto exageradas.
- Hambúrguer **DENTRO/OVERLAY** da face; Folhear/Contínua, fonte, espaçamento, sumário, tema etc. SOMENTE no menu, fechado por padrão. Folhear com swipe/tap/teclado, modo contínuo com scroll vertical, âncora e preferência persistidas entre modo/rotação/zoom. Sem barra externa e sem contador operacional à vista.
- A pauta Gothic usa OBRIGATORIAMENTE **B03-03 Grande Reportagem**, e os demais templates B03-01 nota, B03-02 radar, B03-04 técnica, B03-05 visual/comunidade. Texto real como HTML selecionável, fluido, não PNG de texto. Tipografia, capitulares, módulos de apoio, imagens com legenda quando permitidas, variações de ritmo e densidade. Nada de 'cartões de status' dominando a identidade.
- Páginas 2–3 (editorial/sumário), 4–5 (abertura/primeiro texto), 6–7 (continuação/fontes), 8–9 (bastidores) e 10 (contracapa) precisam de correção específica conforme o Bloco 03: paginação reequilibrada, sem meia folha vazia por falha, sem repetição de título, referências acessíveis sem consumir edição, sem inventar filler.
- Responsividade, acessibilidade, foco/ESC, 150% de fonte, preservação de figuras e textos, sem sumiço, duplicação nem rolagem horizontal. Comparação REAL de antes/depois com screenshots/bounding boxes nas resoluções 360×740, 390×844, 768×1024, 1024×768, 1366×768, 1440×900, 1920×1080, se viável 3840×2160; dois gates independentes: funcionalidade e ACEITE VISUAL HUMANO.
- Preservar leitor v0.3 e protótipos aprovados, backup/rollback. Não adotar outra biblioteca flipbook sem comparar contratos e obter decisão. Bloco 03 **não pediu** correção do jornalismo; separar setores.

Arquivos locais mencionados pelo Bloco 03: Revista_BACK_B03_Mobile_Imersivo_2026-10-27.zip (experiência mobile aprovada), Revista_BACK_Bloco03_Cinco_Modelos_Editorais.zip (base em evolução) e histórico v0.3. A presença no Downloads do diretor DEVE SER VERIFICADA NO PC, não presumida na nuvem.

## 6. MONITORAMENTO E CENTRAL DO DIRETOR: CONCEITO, NÃO IMPLEMENTAR AGORA

A Direção não quer operar a fábrica continuamente. Prevê olhar à noite o que aconteceu de manhã e à tarde e, opcionalmente, intervir em QUALQUER setor: triagem, curadoria, investigação, Carranca, Beto, Nina, revisor, mídia/direitos, edição, montagem. Quer consultar o histórico completo, ver estado/artefatos/rascunhos, investigar erros, conversar com o agente responsável no contexto da tarefa, orientar, pausar/parar novas ações, mandar retomar e aprovar quando pertinente. O painel futuro é uma **central de direção editorial e conversação com agentes**, NÃO só indicadores e botões; não o desenhar nem implementar agora, pois o diretor vai amadurecer o conceito.

Consequência obrigatória para o backend DESDE JÁ: gravar trilha persistente/auditável de eventos (entrada, início/fim/setor, decisões e motivos, prompts/config versionados, versão/hash da matéria, fontes/uso e direitos, solicitações de imagem, execução/custos, revisões, bloqueios, pausas/intervenções, estado atual, histórico e timestamps) com acesso controlado. Não criar um 'dashboard fake' e não armazenar segredos, dados excessivos ou textos brutos em repo público. Deve ser possível pausar enfileiramento/novas chamadas com segurança, sem prometer cancelar no meio uma chamada já aceita pelo provedor.

## 7. FASES DE HOSPEDAGEM: LOCAL EM NOVEMBRO; VPS EM DEZEMBRO

**Intenção declarada da Direção:** contratar VPS mensal até dezembro de 2026, idealmente até meados de dezembro; tudo que hoje está no PC (exceto o que for explicitamente local) deve poder migrar para a nuvem e operar 24h/7. Isso é **meta de planejamento**, não VPS já comprada nem autorização para contratar/deploy. Não implementar dependências Windows-only no núcleo; separar filesystem/config, armazenamento de estado, processo worker, logs, URLs, scheduler, webhooks e secrets.

**Novembro, fase local provisória:** provar o conceito completo coleta→detecção→triagem→curadoria→pesquisa→jornalista↔revisor→acervo, incluindo desligar/religar PC com retomada de coletas perdidas e sem chamadas duplicadas. Para a primeira prova, monitor local pode consultar GitHub periodicamente e recuperar backlog; usar DBOS existente como candidato principal a workflow/fila, confirmar API real/capacidades usadas. Isso precisa funcionar por PLAY, sem intervenção do Codex entre estágios. Salvar checkpoints locais e públicos sem misturar credenciais.

**Dezembro, migração VPS:** a mesma cadeia funciona 24/7 sem PC ligado, sem diretor presente nem sessão Codex aberta. Escolher VPS somente com medição de RAM/CPU/disco/I/O, limites e custos; deploy autorizado depois. Usar gatilho de commit no GitHub/Actions/webhook ou outro comprovado e seguro, com reconciliação/polling de segurança, fila persistente e processo de recuperação. Limites de taxa, observabilidade, alarme de bloqueio e retenção. Não presumir que workflow local, credenciais DPAPI do Windows ou autenticação OAuth/SIWC sejam portáveis para Linux/VPS: **fazer teste explícito de elegibilidade e autenticação SIWC em ambiente servidor permitido**, armazenamento seguro distinto, refresh/token lifecycle e conformidade. Não transportar credenciais protegidas por DPAPI nem fazer bypass de OAuth. Se SIWC não for permitido/funcional na VPS, apresentar contingência autorizada sem inventar API gratuita. NÃO acionar provedor faturável sem autorização.

**Cadência futura:** manter hoje capturas 08h00 e 18h40. A Direção levantou COMO HIPÓTESE adicionar meio-dia e madrugada (por causa de fusos asiáticos), mas NÃO aprovou quatro execuções diárias; não alterar automação de coleta agora. Cadência deve ser configurável e separada da lógica editorial, com custo/latência por rodada medidos. Captador pode já funcionar na nuvem por agendamento do ChatGPT; a fábrica nova não deve duplicar captadores sem necessidade.

## 8. ARQUITETURA MÍNIMA E CRITÉRIOS DE 'NÃO REFAZER FÁBRICA'

Censurado permanece BASE EXPERIMENTAL, DBOS como principal candidato a motor de workflow porque o clone já o usa; adapter SIWC já obteve response.completed real isolado e mock integrado. Persona modular inspirada em Umbruch e saída/artigo/referências/proveniência inspiradas em Machine Herald são adaptações existentes, não motivo para instalar três stacks inteiras. Abordagem 'menos código e mais agentes' significa usar código mínimo/robusto para tarefas determinísticas e agentes com instrução/contratos para trabalho cognitivo, e NÃO entregar ao LLM a responsabilidade de idempotência, segurança, persistência ou exatidão dos eventos.

Separar explicitamente: detector de coleta / fila persistente / máquina de estados e gates / dispatch de papéis LLM / acesso autorizado a fontes / revisor e correção / acervo e direitos / composição da edição. Usar IDs estáveis e estados por batch, story, revisão, referência e asset; recuperar após crash em fronteiras seguras; callbacks de estágio; logs para futura central; supervisão humana excepcional, não operação manual. Não confundir ação do Codex construindo a ponte com solução operacional permanente.

## 9. PROVAS DE ACEITAÇÃO ORDENADAS (SEM RECURSO CARO PRIMEIRO)

**P0 — retomada segura:** antes de qualquer alteração, ler checkpoint local e ambos pareceres completos; inventariar e conservar mudanças ainda não commitadas do worktree da primeira edição (HTML após duas chamadas SIWC pode estar SOMENTE LOCAL). O computador foi desligado inesperadamente pelo diretor antes de novo checkpoint: **não afirmar que o último estado está salvo no GitHub**. Verificar real git status, arquivos locais, SHA, logs e checkpoint; salvar snapshot/backup seguro antes de editar. Preservar J1/R1 reais, artigo original e parecer; não vazar dados nem fazer replay. Atualizar documentação GitHub E o checkpoint local para dupla continuidade. Reconhecer que este documento no GitHub não altera automaticamente o disco D:/C:/ da máquina do diretor.

**P1 — rastreabilidade e fluxo offline:** identificar no Censurado/DBOS lacunas de cascata; implementar monitor local e workflow/fila únicos e mínimos. Testar chegada de arquivo novo, triagem/curadoria, roteamento motivado, pesquisa complementar devolvida ao MESMO jornalista, request de imagens, J1/R1→J2/R2→J3/R3 (com mocks), bloqueio na terceira rejeição, aprovação em R1/R2/R3, persistência em acervo e backlog após desligar/reiniciar. Codex só inicia o sistema e inspeciona; sem comando manual a cada setor. Idempotência por batch/story/hashes, estados uncertain preservados.

**P2 — editorial offline e qualidade:** diagnóstico de prompts reais, fontes, gênero e cobertura do Gothic; eliminar repetição de restrições; distinguir descoberta/leitura/citação/aprovação; perfis de execução derivados dos DNAs, sem modificar identidades aprovadas; revisar rubricas P/J e completude. Separar output para leitor versus controle editorial. Verificar imagem/proveniência, asset avatar e solicitações de mídia. Provar por teste de mesmo conteúdo sem texto falso.

**P3 — leitor visual correto:** implementar contrato B03, comparar com referências aprovadas e imagens do diretor em navegador real, preservando texto HTML e modos. Mostrar ao diretor antes/depois, navegar efetivamente no próprio computador, não declarar aprovação visual sem ratificação. Preferir reparar o leitor existente.

**P4 — integração REAL só mediante autorização:** apresentar orçamento aproximado por chamadas, limites/retries e plano de 3 rodadas; executar só após autorização explícita, manter logs de tokens reportados versus impacto SIWC desconhecido; corrigir matéria real sem repetir J1/R1 já concluídas, e depois expandir Beto/Nina. Não tratar aprovação técnica como aprovação de qualidade. Não publicar.

**P5 — preparação VPS sem deploy:** mapear portabilidade, configs, armazenamento de segredo, restore, serviço/worker, trigger, rede, políticas SIWC e estimativas de recursos; preparar roteiro de migração reversível que não dependa do PC. NÃO contratar VPS/deploy em dezembro por inferência; pedir decisão no momento adequado.

## 10. ENTREGÁVEIS E RESPONSABILIDADE DO CODEX NESTA RETOMADA

1. **Restaurar e preservar** o estado real após desligamento abrupto: verificar fonte local, worktree, clonado, checkpoint e commits; registrar divergências do checkpoint GitHub. A branch experimental permanece separada de main, da fábrica antiga e da PR #44.
2. **Implementar as melhorias locais/offline viáveis** que unem o Censurado ao fluxo automático, começando pelas transições que faltam, em vez de produzir apenas mais uma arquitetura. Não implantar sem plano de rollback.
3. **Criar uma matriz curta requisito → código existente → lacuna → teste** para B02 A01…A12, B03 G/I e fluxo A de cascata, sem reescrever os pareceres como se fossem decisões novas.
4. **Registrar duas cópias de continuidade:** (a) GitHub branch experimental: código/contratos/estado seguro, (b) checkpoint da operação no disco local, principalmente D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md, e o checkpoint do worktree da primeira edição se houver. Documentar links/hash/horário de ambos; NÃO sobrescrever arquivo anterior sem preservar backup/diff e manter versionamento. O diretor desligou inesperadamente o computador; esta providência é PRIORIDADE.
5. **Relatório objetivo e verificável:** o que roda sem Codex, o que ainda requer Codex manualmente, onde estão os dois checkpoints, testes offline que passaram, diferença entre sistema montado e protótipo, autorizações pendentes. NÃO dizer 'fábrica autônoma aprovada' até prova real de gatilho→acervo. Nem 'leitor visual aprovado' até inspeção e ratificação do diretor.

### Regras finais inegociáveis

- **SEM novas inferências SIWC reais ou API paga** por esta ordem. Não repetir respostas uncertain; não mudar para Sol/Terra, nem usar fallback.
- **SEM publicação, deploy, merge em main, alteração do Captador atual ou mudança de DNA** sem ordem específica.
- **SEM implementação antecipada da central de direção**, mas seus requisitos de observabilidade e interrupção segura devem ser preservados.
- **SEM recomeçar do zero** ou montar três fábricas completas; reutilizar componentes comprovados com licenças cumpridas.
- **SEM aceitar aparência ou jornalismo por contagem de testes**; diretor inspeciona obra concreta.
- **A fábrica deve gerar um ACERVO crescente de matérias aprovadas; só depois um ciclo distinto monta edições.**

Esta ordem foi consolidada pela coordenação do Fundador com o material dos Blocos 02/03 e a orientação de Direção. Os links integrais são parte obrigatória do contexto do Codex, para que nenhum dos 12 achados, contratos visuais, decisões de ciclo, direitos de mídia ou intenção de VPS seja descartado por simplificação de resumo.
