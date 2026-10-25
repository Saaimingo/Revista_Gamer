# Bloco 06 — proposta provisória de operação de redes sociais, contas e integração

**Data:** 25/10/2026  
**Origem:** discussão direta do diretor com Bloco 06 — Comercial, Monetização e Divulgação  
**Status:** **PROVISÓRIO — submetido à avaliação do Chat Fundador e da direção**  
**Natureza:** análise de requisitos e caminhos técnicos; **não é ordem ao Codex**, não aprova publicação, contratação, gastos, criação de contas, instalação de apps nem mudança de fases do Motor Editorial.

## 1. Pergunta concreta do diretor e resposta

**Pergunta:** o ChatGPT/Codex está autenticado com o e-mail pessoal do diretor; a revista terá e-mail e perfis próprios. É necessário usar o mesmo e-mail para que o Codex publique e responda no Instagram/Facebook?

**Resposta:** **não**. São **identidades independentes**. O login OpenAI/Codex autentica a ferramenta e o acesso ao modelo; a autorização Meta ou de um serviço de publicação autenticado é concedida **separadamente** pelo detentor autorizado dos ativos sociais. O operador executa com permissões delegadas (OAuth, acesso a páginas/contas e/ou integração conectada), não por exigir coincidência entre os e-mails.

**Distinção obrigatória:** plugins existem nas interfaces compatíveis de ChatGPT e Codex, mas **a existência de um plugin nesta conversa NÃO comprova que um Codex CLI local nem um worker não interativo terão acesso programático à mesma conexão**. O diretório de plugins pode ser usado em tarefas compatíveis do Codex (Fontes → Usar plugins); uma integração local/contínua deve ser testada especificamente pelo Codex e pode exigir API oficial da Meta ou um serviço autorizado com interface suportada. **Não tomar credenciais da sessão pessoal ChatGPT/Meta nem reproduzir cookies de navegador.**

Fontes oficiais OpenAI:
- https://help.openai.com/en/articles/20001256-plugins-in-chatgpt
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan
- https://help.openai.com/en/articles/20001494-connecting-and-managing-app-accounts-in-chatgpt
- https://developers.openai.com/resources/docs-mcp

## 2. Ativos de identidade e propriedade — ainda não criar

Sequência conceitual:
1. **Nome comercial**: decidir após pesquisa de anterioridade/aceite do diretor. Não congelar marca apenas por mockup.
2. **E-mail institucional**: caixa dedicada da revista, distinta do e-mail pessoal da OpenAI; autenticação multifator, recuperação e titularidade sob controle da direção. Pode usar provedor gratuito inicialmente, caso a direção aprove; domínio personalizado apenas se houver decisão/necessidade/orçamento.
3. **Instagram**: perfil oficial da marca, preferencialmente conta **profissional** (empresa/criador, conforme a combinação de recursos pretendida).
4. **Facebook**: **Página** oficial da revista administrada por pessoa com autorização legítima na Meta; não criar falso perfil pessoal em nome de uma entidade/IA para contornar regras.
5. **Meta Business Suite / portfólio empresarial**: vincular a Página e a conta de Instagram, atribuir administradores elegíveis e papéis mínimos, habilitar recuperação e controles de segurança. A vinculação oferece caminho único de gestão quando suportada.
6. **Integração técnica**: somente após titularidade e permissões, conectar app/plugin autorizado ao ativo correto, independentemente do login OpenAI/Codex.

Registrar em documentação apenas **IDs públicos, identificadores técnicos não secretos, permissões requeridas, titularidade e estados**. **Não** registrar senhas, códigos de recuperação, access tokens, refresh tokens ou chaves em GitHub, Issues, logs ou prompts. Guardar segredos em mecanismo adequado sob controle da direção, com política de revogação.

## 3. Dois caminhos de implementação — comparação a validar

### Caminho A — execução supervisionada / menor custo e risco
- Usar Meta Business Suite para elaborar, agendar e gerenciar posts nas contas conectadas, com operador humano inicialmente.
- Opcionalmente avaliar plugins de publicação/gestão conectáveis na superfície suportada do ChatGPT/Codex. A pesquisa do diretório indicou **Metricool** (posts/agendamento/análise) e **Windsor.ai** (publicar e responder em plataformas suportadas após autorização); **não foram instalados/conectados nesta missão**. Examinar planos, cotas, acesso programático, direitos de dados, confirmações por ação e disponibilidade na superfície usada.
- Benefício: testar a rotina social e os formatos de postagem antes de investir em integração automática própria.
- Limite: **não comprova operação autônoma do Motor Editorial via plugin na CLI local** e não pressupõe agendamento sem intervenção humana.

### Caminho B — futura integração direta no Motor Editorial
- Adaptador de publicação Meta via **APIs oficiais**: Instagram Platform Content Publishing (conta profissional e escopos suportados) e Facebook Pages API para publicação, leitura/resposta a comentários e insights autorizados.
- Fluxo de autorização pelo proprietário legítimo, permissões mínimas de leitura/escrita, identificação de ativos, renovação/revogação de tokens e verificação de elegibilidade/limites reais.
- Agendamento pelo **orquestrador persistente** do Motor (não por um LLM improvisando timers); fila por destino, reintentos limitados, logs, respostas da API e prevenção de duplicatas. Usar programação nativa da plataforma apenas se suportada no endpoint/formato escolhido; caso contrário publicar no horário pelo adaptador.
- Leitura de comentários por API permitida e processamento em janela (hipótese inicial noturna); webhooks apenas se comprovarem vantagem técnica, permitidos e autorizados.
- Alguns formatos, permissões, revisões de app e verificações empresariais dependem de tipo de login, tipo de conta, produto e modalidade de uso; **não prometer aprovação ou acesso automático**.

Fontes oficiais Meta:
- https://developers.facebook.com/documentation/instagram-platform
- https://developers.facebook.com/documentation/instagram-platform/instagram-api-with-instagram-login
- https://developers.facebook.com/documentation/instagram-platform/content-publishing
- https://developers.facebook.com/documentation/pages-api
- https://developers.facebook.com/documentation/pages-api/posts
- https://creators.facebook.com/tools/meta-business-suite/
- https://www.facebook.com/business/help/609176706604372

**Recomendação técnica do Bloco 06 (ainda não ratificada):** começar com A em modo manual/supervisionado para validar o processo e avaliar B como integração de produção. Nunca usar scraping, automação clandestina de login ou contorno de limites.

## 4. Função social na fábrica, sem agentes por cronista

- **Um papel operacional de Marketing/Relacionamento**, despachado pelo orquestrador; **não** criar agente por personagem nem outro motor editorial.
- O papel recebe pauta/fonte/verificação liberada, objetivo da publicação, conta-alvo, calendário e **profile_id + version/hash do DNA do cronista**. A persona está nos perfis do Bloco 02; o executor LLM é substituível e não pode alterar a identidade.
- Produz post / legenda / arte apta para modalidade de uso **autorizada** / links / marcação de caráter comercial e agenda; revisão/validação humana nas etapas de autonomia ainda não aprovadas.
- Conteúdo em redes não herda automaticamente os direitos de imagens editoriais: a modalidade Instagram/Facebook e transformações precisam constar na autorização correspondente. Publicidade patrocinada ou afiliada segue **acervo comercial separado**.
- A arquitetura social deverá consultar acervo de conhecimento e respostas já dadas, sem criar banco editorial paralelo desnecessário.

## 5. Objetos e estados mínimos para engenharia futura

Especificação de intenção (nomes ilustrativos, **não contrato de implementação aprovado**):

- **SocialAccount**: platform, account/page ID, ownership/status, permissions, connector_kind, scopes/version, último teste de capacidade — sem segredos.
- **SocialPostPlan**: post_id, origem editorial/version/hash, profile_id/version/hash, canal e formato, direitos dos ativos, texto/arte, classificação orgânico/comercial, links e transparência, scheduled_at com fuso, status, revisão/aprovação.
- **SocialPublishReceipt**: post_id local, id remoto, data/hora, resposta sanitizada da plataforma, estado de retry/erro, deduplicação.
- **SocialInteraction**: id da publicação e comentário, mensagem e contexto mínimos, classificação, persona, proposta de resposta, motivo de priorização ou dispensa, status e id da resposta; minimizar retenção de dados de terceiros.
- **SocialCalendar**: janelas, fila, reserva para evento extraordinário, validade temporal do conteúdo e política de reagendamento.

Estados ilustrativos: `rascunho → checado → aguardando_aprovacao → agendado → publicando → publicado`; `falhou/revisar/cancelado` com trilha auditável. **Nunca publicar apenas porque o LLM finalizou a redação.**

## 6. Cronograma de implantação proposto — marcos sem datas inventadas

**Marco 0 — Agora: decisão conceitual (sem custo/contas).** Fundador avalia esta proposta com Comercial, Visual, Engenharia, Acervo e Redação. Confirmar o que cada bloco fornece e qual superfície Codex realmente será utilizada.

**Marco 1 — Identidade e ativos (depende de decisão de marca).** Diretor autoriza, quando pertinente, criação do e-mail institucional, Página Facebook e Instagram profissional; configura controle e recuperação. Nenhum compromisso com fornecedores pagos.

**Marco 2 — MVP manual.** Com contas autorizadas e identidades finais, testar textos/arte e agendamento supervisado no Business Suite. Inicialmente **duas publicações por semana** (segunda e quarta foram exemplo, **não** calendário aprovado); espaço para notícias excepcionais.

**Marco 3 — Prova técnica de integração.** Codex verifica na instalação/conta efetiva: acesso de plugins no Codex suportado versus CLI/runner local, API oficial Meta, permissões por ação, publicação e captura de recibo, comentários, limites, custos, falha segura. Ensaiar mocks OFFLINE antes de testes reais específicos autorizados.

**Marco 4 — Piloto supervisionado na conta real (somente com autorização expressa).** Publicar posts reais aprovados e conferir resultado, erros e métricas básicas; depois responder a alguns comentários pertinentes, sem promessa de responder todos. Desligar automaticamente publicação em falhas de autorização.

**Marco 5 — Autonomia gradual.** Ampliar agendamento e lote de respostas apenas após medir qualidade, custo, taxa de falhas e capacidade da plataforma. A frequência semanal e campanhas pagas continuam decisões comerciais posteriores.

## 7. Interfaces setoriais e aceites

**Fundador**: ratificar arquitetura, papel do marketing no orquestrador, limites de aprovação e decisão do caminho A/B.

**Engenharia/Codex**: descobrir capabilities efetivas de plugins no cliente local; comparar integração manual/plugin/API; propor contrato técnico e testes com mocks; não ativar conectores reais por inferência.

**Bloco 02**: fornecer referências dos três DNAs estáveis e exemplos de vozes; Comercial **não** recria perfil jornalístico.

**Bloco 03**: templates visuais de social, escala da marca, variantes mobile, identificação de publicidade.

**Bloco 04**: conteúdo factual e reuso editorial verificável, aprovação contextual de respostas informativas.

**Bloco 05**: adequação de permissão de imagens por plataforma e categoria editorial/comercial.

**Bloco 06**: calendário, critérios de seleção de conteúdos, distribuição, acompanhamento de audiência, regras comerciais e métricas; contratos de patrocínio e controle financeiro são frentes **distintas e futuras**.

**Critérios antes de liberar uma publicação automática:** conta/destino inequívocos; credencial delegada autorizada e testada; texto com perfil versionado; fontes verificadas; direitos específicos da mídia; identificação comercial adequada; consentimento da direção para operação, logging, deduplicação, reversão e ausência de gasto imprevisto.

## 8. Pendências para aprovação

1. Nome final e identidade pública da revista — bloqueador **somente** para criação definitiva dos ativos, não para projeto offline.
2. Escolha/aceite de plataforma para MVP e do executor real da fábrica (plugin no Codex suportado? Codex CLI? aplicativo separado?).
3. Tipo de conta Meta, permissão por operação e resultado de autenticação concreta, sem instruir captura de tokens em chat.
4. Regras de publicação real e escalonamento de respostas que serão fixadas após testes.
5. Custos/limitações de cada integração, condições de apps terceiros, privacidade e governança.
6. Handoff formal aos setores e autorização separada do Codex antes de implementar.

**Conclusão:** *não existe impedimento estrutural porque o e-mail OpenAI é pessoal*. A incógnita real é a compatibilidade de execução entre plugin, Codex local e orquestrador, somada à autorização de acesso da Meta. Projeto deve separar identidade, credenciais, agentes e canal de publicação.
