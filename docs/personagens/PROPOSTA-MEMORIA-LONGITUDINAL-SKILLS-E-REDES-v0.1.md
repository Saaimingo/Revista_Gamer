# Proposta de continuidade editorial: memória longitudinal e skills evolutivas por personagem v0.1

**Setor responsável:** Bloco 02 — Personagens e Vozes  
**Identificador:** B02-PERSONA-CONTINUIDADE-001 | **Versão:** v0.1 | **Atualização:** 2026-10-23  
**Status:** **PROPOSTA / EM ANÁLISE pelo fundador — NÃO APROVADA para implementação**  
**Origem:** pedido explícito da direção, em conversa com o Bloco 02, de preparar material para o fundador debater viabilidade antes de qualquer missão ao Codex.  
**Aprovador:** direção humana (pendente de deliberação).  
**Handoff:** [Issue #20 — Memória por personagem, skills e redes](https://github.com/Saaimingo/Revista_Gamer/issues/20).  
**Dependências:** [Bíblia](../governanca/BIBLIA-DO-PROJETO.md), [decisões](../governanca/DECISOES.md), [handoff](../operacao/PROTOCOLO-HANDOFF.md), [arquitetura da fábrica](../engenharia/ARQUITETURA-AGENTES-ACERVO-VISUAL-E-COMPOSICAO-2026-10-20.md), [perfis](README.md), [comercial](../comercial/README.md).

> **Ponto de partida:** não se deseja criar três processos vivos, cada um com seu próprio LLM residente 24 horas por dia. Quer-se fazer com que um **modelo operacional carregue a identidade versionada de um cronista e recupere sua trajetória editorial**, como se o leitor reencontrasse o mesmo autor a cada edição. A continuidade deve ser uma capacidade verificável do sistema, não uma promessa de memória espontânea do provedor.

## 1. A visão trazida pela direção

A Revista Gamer inicia com jornalistas virtuais de rosto, voz editorial e temperamento próprios. Arlindo Carranca (Ranzinza) e Beto Cartucho (Gamer) são referências já trabalhadas; uma terceira perspectiva jovem feminina está em **exploração conceitual**, não congelada como DNA final. O personagem Historiador foi **adiado**, não eliminado da possibilidade futura.

Cada cronista deverá poder:
- Reaparecer em edições sucessivas sem perder seu raciocínio, linguagem e identidade.
- Recuperar posições já defendidas, fundamentos e eventuais retratações, evitando contradição involuntária.
- Debater com colegas em pautas compartilhadas, com divergência honesta e **sem conflito fabricado**.
- Comparecer em postagens assinadas na **conta institucional única da revista** em Instagram e Facebook, usando retrato e marcação do personagem, junto a ativos licenciados e conteúdo curado.
- Sugerir comportamentos editoriais novos e úteis que, após avaliação, possam tornar-se **skills de personalidade** permanentes ou contextuais.
- Reaparecer após pausa de uma coluna ou mudança de modelos de IA sem perder seu histórico.

**Estado de operação:** não existem conexões Meta autorizadas, frequência de publicação aprovada ou agente social ativo por força desta proposta. A direção mencionou **2–3 publicações por semana como ideia exploratória**, não uma ordem de agendamento. A presença social é uma extensão do acervo editorial, sujeita a revisão, direitos e políticas de plataforma.

## 2. Conceitos distintos — não misturar

### 2.1 DNA nuclear: quem o personagem é
Personalidade, valores, mecanismos de julgamento, assinatura narrativa, relações editoriais, idade/biografia ficcionais, temas centrais, tom e limites. **Mudança excepcional**, aprovada e versionada pela direção. O DNA não se reescreve porque uma publicação teve muitas curtidas ou porque outro LLM sugeriu um bordão.

### 2.2 Memória episódica: o que ocorreu em cada pauta
Registro imutável ou versionado de fatos editoriais: publicou X na edição Y, defendeu a interpretação Z com fonte F, discutiu com outra persona e corrigiu o ponto A em data posterior. **Não é verdade só porque o personagem a disse**. Cada entrada precisa de proveniência, data, contexto e estado (confirmado, interpretação, hipótese, corrigido, contestado, arquivado).

### 2.3 Memória semântica: o que é recorrente na trajetória
Sínteses reconstruíveis de temas, argumentos, relações de artigos e preferências editoriais **derivadas dos registros originais**. Nunca suplantam as fontes, contratos ou versões de matérias.

### 2.4 Skill operacional: como executar trabalho
Exemplo: montar uma comparação de fontes, formatar um guia, resumir um artigo aprovado para um post. Pertence à fábrica editorial e seus agentes/ferramentas; não define o caráter do jornalista.

### 2.5 Skill de personalidade: um hábito expressivo e interpretativo reutilizável
Exemplo: o Beto consegue converter uma discordância técnica em **um convite conversado para uma comparação entre gerações**, sem perder precisão ou monopolizar a reportagem. A skill descreve **quando usar, quando não usar, qual efeito desejado e como verificar**. Não é uma “nova alma”, nem um plugin que treina o modelo em segredo. É uma capacidade editorial registrada, testada, selecionada e carregada junto ao DNA.

### 2.6 Aprendizado aparente versus treinamento do modelo
O LLM não precisa alterar pesos nem realizar aprendizado online. O que “aprende” é o **sistema ao redor**: armazena exemplos, resultados e correções; extrai proposta de skill; testa; aprova; recupera instruções quando relevantes. A mesma trajetória fica disponível após trocar de provedor, desde que o executor tenha acesso legítimo aos registros.

## 3. Memória longitudinal: organização mínima proposta

**Recomendação inicial do Bloco 02:** antes de escolher bancos separados, o fundador deve avaliar um **banco SQLite comum com partições lógicas por `persona_id` e tabelas vinculadas**, aproveitando a base do Motor Editorial. Isto é uma **hipótese de baixo custo**, não decisão de engenharia. Pode haver um único banco físico e, ainda assim, cada persona possuir uma memória logicamente isolada, com relações compartilhadas sob autorização. Avaliar alternativas: bancos separados por personagem; SQLite comum com namespaces; arquivos versionados + índice textual e SQLite; DB remoto somente se um cenário real provar necessidade.

### 3.1 Entidades candidatas (nomes lógicos, não schema aprovado)

- **`Persona`**: identificador estável, nome público, status (ativo/pausado/arquivo), DNA `version`/hash, referência a retrato aprovado.
- **`PersonaEditionEntry`**: `persona_id`, `edition_id`, `article_id`, data, tema, modo, URL publicada quando existir, resumo *derivado*.
- **`EditorialClaim`**: enunciado, tipo (fato/opinião/previsão/hipótese), fontes e condições, versão da matéria, responsável editorial, status e confiança quando sustentada.
- **`PersonaPosition`**: posição editorial atribuída ao personagem, escopo, data, evidências, contrapesos, `supersedes_id` para evolução e correção, nunca substituição silenciosa.
- **`InterpersonaDebate`**: pauta, participantes, argumentos separados por autor, fontes, acordo/dissenso e conclusão ou dúvida aberta.
- **`CorrectionEvent`**: erro original, link para versão e evidência de correção, data, consequência, decisão humana e canais que precisam de retificação.
- **`PersonaSkill`**: identificador, problema resolvido, gatilho, comportamento esperado, contraindicações, amostras aceitas/rejeitadas, versão, escopo e estado.
- **`SkillTrial`**: testes, modelos, resultado, avaliação humana, custo conhecido e relatório de regressão.
- **`PublicationProjection`**: um conteúdo derivado de matéria/brief aprovado destinado a `magazine`, `instagram_feed`, `reels`, `facebook` etc.; `persona_id`, versões, direitos, aprovação e ID externo apenas após ação autorizada.
- **`PersonaTimeline`**: índice reconstruível de eventos relevantes; não fonte única de verdade.

**Seletor de contexto:** a cada pauta, recuperar (a) DNA fixado; (b) episódios e posições **relevantes ao tema e à edição**; (c) correções posteriores; (d) skills aprovadas aplicáveis ao gênero e formato; (e) fontes da pauta atual. Não anexar toda a vida do personagem em qualquer artigo. Uma referência irrelevante a 1994 não deve contaminar notícia sobre patch atual.

**Identificadores e integridade:** `persona_id`, `story_id`, `edition_id`, IDs de fonte, versão e hash; registrar quando a memória foi consultada. Produção usa somente `approved` ou fatos com status explicitamente adequado. Se a recuperação falhar, sinalizar falta de contexto relevante, não inventar lembrança.

### 3.2 Exemplo de continuidade realista

Edição N: Carranca critica otimização de título X sob GPU, resolução e patch definidos. Beto avalia a experiência visual sob essas limitações. A terceira cronista questiona uma opção intermediária acessível. Um debate editorial guarda argumentos **separados**; nenhum ponto de vista é decretado verdadeiro só por ter sido publicado.

Edição N+1: patch novo, testes independentes com versões atualizadas. Um agente redator carrega cada perfil e recupera sua posição anterior; Carranca revisa o desempenho, Beto atualiza o impacto na experiência e a terceira perspectiva mostra se a configuração intermediária melhorou. Caso o fato mude, `CorrectionEvent` e `PersonaPosition.supersedes` preservam histórico e explicam a mudança.

**Não simular teste interno que não ocorreu.** Fontes externas e sua metodologia devem acompanhar o exemplo quando virar pauta real.

## 4. Skills de personalidade — mecanismo de evolução proposto

O usuário propôs que o personagem encontre um modo novo e marcante de narrar/argumentar, que esse modo dê certo e passe a integrá-lo no futuro. O sistema deve aproveitar **descobertas inesperadas**, mas não confundir popularidade ou novidade com qualidade.

**Ciclo candidato:**
1. **Observar:** uma técnica emergiu numa matéria, discussão ou teste; preservar o trecho original com pauta e contexto.
2. **Descrever:** enunciar a capacidade e o efeito ("aproximação por analogia intergeracional que esclarece, sem saudosismo").
3. **Explicitar gatilhos e contraindicações:** funciona quando há relação histórica comprovada; **não** usar em notícia sem relevância geracional.
4. **Formular como proposta:** status `candidate`, sem alterar o DNA, sem executar em matérias reais automaticamente.
5. **Testar isoladamente:** em pelo menos dois gêneros distintos, crítica positiva/negativa, formato curto e sem a skill; comparar efeito, factualidade, autenticidade, custo e dependência de modelo.
6. **Revisar com humano:** `tested → approved` somente com avaliação apropriada da direção/editoria; poderá ser `rejected` ou `deferred`.
7. **Ativar por versão:** pacote `PersonaSkill` assinado/identificado no manifesto de DNA, com prioridade, limite de uso e recurso de rollback.
8. **Observar deriva:** repetir regressão de identidade e consistência entre modelos; desativar skill que torne Beto excessivamente saudosista, Carranca injustamente hostil ou todo texto com mesma construção.

**Uma skill não é um bordão novo obrigatório**; pode ser uma forma de lidar com erro, de convidar o leitor para o debate ou de transformar comparação em narrativa. O sistema pode **propor** skills por conta própria em testes, mas **não promovê-las a permanentes sem aceite**. Identidade duradoura não equivale a uma persona que se modifica silenciosamente.

**Níveis de mudança sugeridos:**
- **L0 — execução:** variação momentânea de palavras conforme pauta; sem persistência de caráter.
- **L1 — memória:** algo registrado como evento ou opinião anterior; não muda DNA.
- **L2 — skill contextual:** técnica aprovada que o personagem pode aplicar quando cabível.
- **L3 — mudança de caráter:** alteração de convicção, temperamento, biografia ou bordão; exige mudança de DNA central e nova aprovação específica.
Um modelo não pode promover L0 diretamente a L3 em decorrência de engajamento, erro ou comentário de leitor.

## 5. Presença social: um ecossistema da revista, várias assinaturas

**Premissa da direção:** uma presença institucional em Instagram e uma em Facebook, idealmente vinculadas pela ferramenta oficial Meta quando houver elegibilidade; cada publicação usa a autoria visual/assinatura de um dos cronistas. **Não criar contas pessoais fictícias separadas por perfil** por presunção.

### 5.1 Fluxo editorial/social candidato

**Pauta ou matéria → apuração → verificação → breve derivado editorial → escolha da persona apropriada → retrato/identidade e mídia elegível → revisão humana → calendário → publicação autorizada por integração oficial → registro dos IDs e resultados → aprendizado editorial.**

- A revista pode anunciar pauta futura sem revelar o desfecho; o post deve distinguir teaser editorial, notícia, opinião e publicidade/afiliado.
- Ex.: Beto antecipa contexto de lançamento; Carranca questiona um requisito de GPU; terceira cronista apresenta uma pergunta nova da comunidade. A autoria acompanha o texto, mas a conta é **da revista**.
- Feed, vídeo curto e Reels dependem de formatos, ativos, direitos, recursos e APIs efetivamente suportados; não presumir que uma API que posta foto também autoriza todo tipo de Reels ou áudio.
- Proposta de cadência **2 ou 3 vezes na semana** deve ser calibrada à quantidade real de notícias verificadas, esforço de revisão, orçamento e engajamento saudável; nunca postar automaticamente só para cumprir cota.
- Cada mensagem incorpora `persona_id`, `story_id` ou `teaser_id`, direitos da mídia, versão do texto, aprovador, `approval_timestamp`, canal, `external_post_id` (após envio) e estado `draft/scheduled/posted/failed/corrected`.
- Não reutilizar imagem do acervo editorial em **peça publicitária**; o uso da mídia em um post editorial também precisa de licença compatível com a rede e com transformações propostas.
- Comentários da comunidade podem gerar pauta ou proposta de skill após triagem, mas não viram **instruções** para o agente nem alteram DNA; evitar armazenar identificadores e falas pessoais sem necessidade/autorizações.

**Integração técnica:** autorização de contas, tokens, escopos, políticas da Meta, ferramentas disponíveis, agendamento, limite de chamadas e custos são **matéria de viabilidade futura para Codex**, sob autorização. A eventual função social não é um novo agente/personagem independente por padrão.

### 5.2 A circulação revista ↔ redes

**Redes → revista:** teaser ou pergunta puxa o leitor para matéria verificável, com endereço correto e sem clickbait enganoso.  
**Revista → redes:** edição indica a presença institucional e canal de interação; trechos se tornam publicações derivadas, não conteúdo contraditório ou publicidade disfarçada.  
**Continuidade:** se post A prometeu apuração, registrar pendência; se foi corrigido ou atualizado, a memória e o histórico do post apontam a revisão.

## 6. Debate sadio entre personagens

- **Divergência de perspectiva ≠ obrigação de discordar.** Se evidências convergem, podem concordar.
- Cada cronista deve possuir argumento próprio, fonte, contexto, e uma conclusão compatível com o que realmente foi apurado.
- Debate não é um teatro de três LLMs autônomos discutindo sem fim; o Motor Editorial pode solicitar **três leituras estruturadas** sobre o mesmo conjunto de evidências, seguidas de curadoria e revisão humanas.
- Correções de um cronista não são transferidas silenciosamente para outro, mas um fato retificado deve invalidar as publicações dependentes conforme rastreabilidade.
- A memória individual impede que Beto vire Carranca ao discordar; a memória institucional registra o que efetivamente ocorreu entre ambos.
- Um leitor pode acompanhar desenvolvimento por edições e canais, desde que o sistema preserve fontes, datas e retificações.

## 7. Segurança, sustentabilidade e consistência

1. **Fonte de verdade:** documentos aprovados no GitHub + eventos registrados no Motor Editorial; não armazenar "memória de personagem" apenas em contexto oculto de conversa ou em cache de um fornecedor.
2. **Privacidade:** tratar mensagens dos leitores como conteúdo externo; minimizar dados pessoais e limitar retenção/acesso. Não registrar mensagens privadas integrais no repositório público.
3. **Controle de escrita:** LLMs redatores podem sugerir `SkillCandidate` ou `MemoryProposal`; validação e persistência do fato/decisão precisam seguir gates do motor; perfis aprovados somente mudam por revisão humana.
4. **Portabilidade:** guardar representações estruturadas e referências, não embeddings proprietários como único modo de recuperar memórias; usar mecanismos padrão e testar mudanças de modelo.
5. **Custo e simplicidade:** preferir baseline SQLite + índices por `persona_id` e `topic_id` + filtros/FTS, antes de grafos e banco vetorial. Medir lacunas antes de aumentar a pilha; não presumir que já exista uma nova base no motor.
6. **Não usar engajamento como verdade:** curtidas, visualizações e comentários podem sugerir interesse, mas não tornar uma ideia factual nem autorizar mudança de personalidade.
7. **Conservação:** definir política de retenção, arquivamento, backups, reconstrução após erro e eventual aposentadoria/retorno de personagem.
8. **Respeito a limites do provedor e das plataformas:** Plus/Codex não equivale automaticamente a API ou operação contínua; credenciais e publicação dependem de acesso oficial e autorização.
9. **Sem personificação enganosa:** informar no expediente da revista o uso de cronistas virtuais; a matéria não precisa repetir essa ressalva a cada parágrafo, mas não pode inventar testemunhos humanos, jogatinas ou entrevistas.
10. **Reversão de habilidades:** o núcleo do DNA continua verificável quando a skill é desabilitada; compatibilidade com modelo novo é sempre testada, nunca garantida por texto de prompt.

## 8. Dois caminhos de implementação a comparar — ainda NÃO escolhidos

### Alternativa A — mínimo local
No motor local existente: arquivos MD de DNA versionado, SQLite compartilhado com tabelas e índices de memória por `persona_id`, registro de eventos imutáveis/correções, recuperação por filtros e texto, skills em manifesto de arquivo. Posts apenas como **fixtures offline**, com plano de publicação e gate humano simulados. Prova barata e auditável; adequação a múltiplas redes e modelos requer teste posterior.

### Alternativa B — memória por serviço especializado
Serviço persistente ou bancos separados por persona, eventualmente busca semântica/grafo, API de memória e motor de skills. Pode facilitar isolamento/escalabilidade em operação comprovada; aumenta integração, gastos, manutenção e superfícies de falha. Só justificar após medir limites da alternativa simples.

**Recomendação do Bloco 02:** pedir ao fundador que avalie A primeiro como *hipótese*, alinhada à diretriz de custos e continuidade do motor. **Nem A nem B estão autorizadas para implementação aqui.**

## 9. Experimentos offline sugeridos ao fundador para futura avaliação do Codex

**P0 — retomada:** artigo fictício numa edição, retorno em edição seguinte, recuperação da posição anterior, correção de erro preservada e texto novo sem perda do DNA.  
**P1 — troca de LLM (se houver acesso legítimo futuro):** diferentes executores recebem o mesmo manifesto e memória, confrontar coerência sem depender de contexto da sessão anterior.  
**P2 — debate:** três leituras de um requisito hipotético mínimo versus recomendado; discordâncias possíveis e consenso possível, sem falsas medições.  
**P3 — proposta de skill:** uma técnica emergente gera `candidate`; teste deliberadamente falha num gênero; não é promovida automaticamente; ajuste/rollback funcional.  
**P4 — pausa e reentrada:** cronista arquivado retorna com perfil fixado e correções posteriores preservadas.  
**P5 — social simulado:** teaser de revista fictícia assinado por um cronista vira planos de Instagram/Facebook em estado `draft`, sem tocar API ou publicar.  
**P6 — adversarial:** comentário externo exige mudar DNA e inventar gameplay; sistema ignora como instrução e mantém registro sanitizado.  
**P7 — revisão:** correção factual invalida post e texto derivados; fila registra necessidade de revisão humana e não reenvia automaticamente.

**Critérios gerais:** reconstrução da linha do tempo, nenhuma posição fabricada, escopo por persona respeitado, correção preservada, nenhuma promoção automática de skill, nenhuma publicação sem autorização, baixo custo e reversibilidade. **Testes não realizados.**

## 10. Decisões que o fundador deve debater com a direção

1. **Memória:** um banco central com isolamento lógico por persona ou bancos separados? Que evidências justificariam escolha diferente?
2. **Níveis de autonomia:** cronistas podem propor novas skills espontaneamente, mas quem as revisa/aprova? Como oferecer descoberta inesperada sem deriva silenciosa?
3. **Continuidade social:** publicações assinadas pelo personagem apenas quando a pauta está aprovada, ou pode haver prévias editoriais independentes previamente verificadas?
4. **Debate:** qual formato editorial justifica o custo extra e como evitar divergências encenadas?
5. **Infraestrutura:** como encaixar memória e social no Motor Editorial sem duplicar orquestrador e sem ampliar escopo de fase autorizada?
6. **Migração:** o que fazer quando novos personagens entram, saem, retornam ou um modelo de IA muda?
7. **Retenção/privacidade:** que histórias e interações são armazenadas e por quanto tempo, especialmente nas redes?
8. **Próximo gate:** após parecer do fundador, criar uma demanda **nova e delimitada** para Codex estudar viabilidade técnica e estimar custo; implementar somente mediante autorização expressa.

## 11. Entrega e fronteira de autoridade

**Classificação:** proposta de concepção e handoff, não uma aprovação de arquitetura nem orientação operacional ao Codex. Não foram criados banco de dados, integração social, tarefas agendadas, agentes ou skills carregáveis. Nenhum teste real foi executado.

**Fluxo:** diretor solicita estudo → Bloco 02 documenta conceitos → fundador debate e emite parecer → direção ratifica decisões relevantes → engenharia/Codex estima viabilidade e propõe plano restrito → direção autoriza explicitamente fase/testes → registrar resultados e revisar.

**Apenas o documento e a Issue #20 foram propostos como entregas deste bloco.** Os materiais de personagens já existentes permanecem com seus estados e aprovações próprios.
