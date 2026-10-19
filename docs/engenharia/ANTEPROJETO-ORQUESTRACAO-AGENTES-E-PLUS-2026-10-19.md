# ANTEPROJETO — Orquestração de agentes e autenticação ChatGPT Plus no Motor Editorial
**Data:** 2026-10-19  
**Responsável pela proposta:** Chat Fundador / Arquitetura  
**Estado:** PROPOSTA EM DEBATE — NÃO É ORDEM DE IMPLEMENTAÇÃO, NÃO DEFINE VERSÃO  
**Base integrada:** Motor Editorial v0.2, PR #6, merge `794e9fcc20f5944031370bd7ddb93f8b323d9528`

## 1. Objetivo do diretor
A fábrica editorial deve disparar por agenda (hipótese: três coletas por dia) e por eventos (tarefa concluída, reprovação, correção, pendência); o **sistema central** escolhe e aciona os executores, nunca um agente dando ordens diretas a outro. O motor entrega contexto à função editorial correta, recebe artefatos rastreáveis, verifica regras e encaminha ou bloqueia a etapa seguinte. Quando não há tarefa, nenhum modelo precisa permanecer ativo. Identidade de cronista precisa ser a identidade *versionada* definida pelo Bloco 02 e aprovada, não um chat genérico.

Prioridade econômica **D-016**: investigar primeiro acesso programático oficial com a conta ChatGPT Plus/Codex que já existe, sem assumir créditos de API ou franquia ilimitada. O diretor delegou o aceite técnico de protótipos, mas não autorização de custos, publicação e produção.

## 2. O que a v0.2 oferece e o que ainda falta
**Pronto na v0.2:** Python local, SQLite, transições e bloqueios por pauta, fluxo multipauta fictício, trilha de auditoria, revisões, prévia interna e gates humanos, migração v2→v3, testes reportados 22/22 pelo Codex e revisão arquitetural.  
**Não implementado:** agenda ativa, fila persistente de tarefas para workers, despacho automático de eventos, credenciais/autenticação do provedor de IA, execução de modelos reais, proveniência factual real, contabilidade de franquias em chamadas externas e recuperação de chamadas remotas interrompidas.  
Não reescrever o núcleo, não usar GitHub como fila editorial, não ligar chats do ChatGPT Project diretamente ao motor.

## 3. Desenho lógico proposto
1. **Agendador:** cadastra horários e fuso; cria eventos/tarefas no SQLite (p.ex., busca autorizada). Persistir último disparo e decidir explicitamente como lidar com horários perdidos durante desligamento. Escolher biblioteca concreta (APScheduler ou agendamento Python simples) após critérios de necessidade.
2. **Caixa durável de tarefas e eventos:** `Task(id, tipo, story_id, edition_id, agente_perfil_id, perfil_versao, estado, tentativas, idempotency_key, created_at, available_at, lease_until, erro)`. Gravar a conclusão de etapa e o evento do próximo trabalho em mesma transação ou usar outbox transacional. Retirada de trabalho atômica e recuperável após queda.
3. **Despachante Python:** observa tarefas prontas, dependências e limites, reserva uma tarefa, consulta o cadastro de executores/perfis e chama apenas o executor designado. O despachante nunca faz julgamento editorial; o motor de estados decide legalidade da transição.
4. **Registro de funções e perfis:** função operacional (pesquisador, redator, revisor, acervo etc.) é separada da persona. Ex.: função `redator` + perfil `gamer`, `ranzinza` ou `historiador`. Cada perfil inclui instruções públicas aprovadas, ficha de linguagem, escopo, restrições, critérios e versão/hash. Os perfis vêm de arquivos/registro local versionado; o executor recebe a versão exata que o fluxo registrou. Não depender da memória de um chat ou de importar suas conversas.
5. **Adaptador de inferência:** contrato `execute(Task, Context, Profile) -> StructuredResult`, independente do provedor, executado sob demanda. Não guardar segredos em Git/log. Conexão oficial via OAuth do ChatGPT é opção prioritária e deve ser provada para este aplicativo; execução offline simulada continua disponível para testes.
6. **Validadores determinísticos e revisor:** receber afirmações, fontes, versões, objeções, correções e resultados estruturados. Revisão sem evidência rastreável não promove matéria. Rejeição origina nova tarefa de correção; após correção é necessária nova revisão vigente, com limite de ciclos e intervenção humana.
7. **Supervisão do diretor:** painel local exibe quem está trabalhando, tarefa, versão de perfil, fontes, erros, consumo, aprovação requerida, tempos e fila. Aprovação humana da edição e publicação seguem distintas; não publicar automaticamente.

## 4. Integração oficial prioritária com o ChatGPT Plus
**Hipótese principal para testar:** OpenAI **Sign in with ChatGPT — ChatGPT plan usage** (SIWC) para clientes de código aberto/local e usuários elegíveis. O usuário autoriza o app no navegador. Se sua conta e este tipo de cliente forem elegíveis, o app recebe tokens OAuth próprios para enviar **requisições elegíveis** à Responses API usando a franquia do plano. A documentação também prevê conexão com Codex app-server por esse token. Essa autorização **não concede acesso às conversas nem à memória** da conta.

Fontes oficiais consultadas em 2026-10-19:
- https://developers.openai.com/siwc/quickstart
- https://developers.openai.com/siwc/token-sharing-open-source
- https://developers.openai.com/siwc/token-sharing-open-source/sign-in
- https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference
- https://developers.openai.com/siwc/token-sharing-open-source/codex-app-server
- https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations
- https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan

**Contrato específico desta integração no preview:** `store: false`, `stream: true` em requisições HTTP Responses; enviar o contexto pertinente a cada execução, sem assumir conversas persistidas do lado servidor. O catálogo de modelos é por conta e deve ser consultado; entitlement exige prova em requisição real. Ferramentas hospedadas (por exemplo File Search e hosted MCP), image generation e alguns parâmetros da Responses API não estão disponíveis nessa modalidade, conforme documentação atual. Pesquisa externa e verificação de fontes terão de respeitar essas restrições e autorizadores independentes.

**Não presumir acesso automático:** checar elegibilidade do aplicativo local e da conta, aprovação e escopos concedidos, limites e exigências se o produto mudar para serviço remoto/comercial. Um repositório publicamente visível não demonstra por si só enquadramento de licenciamento/open source. Nenhum procedimento de autenticação deve tentar extrair cookies ou tokens de sessão privados do ChatGPT.

**Alternativa oficial a avaliar:** execução programática de Codex (`codex exec`, SDK, app-server), se o caso exigir ambiente de ferramentas/agent harness e se a autenticação/saldo permitirem o uso. Não confundir o Codex como engenheiro que desenvolve o sistema com o agente editorial que escreve uma reportagem. Preferir interface de inferência limitada para os cronistas caso dê conta dos requisitos, com ferramentas explicitamente controladas.

**Falha/limite:** falta de autorização, modelo indisponível, token revogado, quota atingida, erro ou stream incompleto resultam em tarefa pendente/pausada, com auditoria e retomada segura. **Sem troca automática para API faturável, compra de créditos, bypass de limite ou autorização de publicação.** Preferências de consentimento e credenciais ficam em armazenamento local protegido, nunca no Git.

## 5. Seqüência proposta de validação, sem definir versão de antemão
**Marco A — Núcleo do despachante offline:** coletas e eventos fictícios geram tarefas; três funções simuladas se encadeiam; revisor reprova, redator corrige e revisor reavalia; testes de retomada, deduplicação e isolamento por pauta. Nenhuma chamada real ainda.

**Marco B — Primeiro executor real autorizado e custeado pela franquia, se elegível:** consentimento SIWC local, seleção de modelo disponível, uma tarefa não pública com perfil fictício versionado, resultado estruturado e auditoria; medir consumo/limite. Se não elegível, registrar impedimento, sem substituição onerosa tácita.

**Marco C — Encadeamento híbrido controlado:** alternar executor real e simulado no mesmo fluxo, sem duplicar processo, manter versão do cronista e reprovar material sem evidências. **Antes de permitir revisão real mutar revisões:** corrigir/coordenar estado da pauta quando revisão corrente perde aprovação, incluindo capacidade de correção/retomada, questão de robustez observada ao final da CODEX-002.

**Marco D — Fluxo editorial interno real (somente com aprovação posterior):** fonte e pesquisa externas explicitamente autorizadas, critérios factuais definidos pelo Bloco 04, perfis definitivos do Bloco 02, mídia licenciada pelo Bloco 05, revisão auditada e entrega à diretoria. Não publicar.

## 6. Pontos abertos para discussão com o diretor
- Confirmar o objetivo de operar **primeiro na máquina local**, mantendo portabilidade para Debian/VPS posterior. Em servidor remoto, exigir nova avaliação de SIWC, segurança, autenticação e elegibilidade do aplicativo.
- Definir horários de coleta, tratamento de desligamento/atraso e limites de simultaneidade; não assumir que toda coleta gera pauta.
- Definir perfis iniciais com o Bloco 02 e padrão de evidências com Bloco 04, sem editar decisões desses blocos.
- Comprovar requisitos do modelo para pesquisa: acesso autorizado a fontes, modo de busca suportado, data da fonte, citação e checagem independente.
- Determinar limites de consumo e condições de pausa e de intervenção do diretor.

## 7. Governança
Este arquivo é uma **análise preliminar** para elaborar com o diretor a próxima etapa; não é CODEX-003, ordem de implementação, autorização de login/ativação, gasto, coleta pública/real nem publicação. A v0.2 integrada é a baseline. Depois das discussões, criar especificação aprovada e ordem precisa para execução por Codex. Não extrapolar capacidades de SIWC nem tratar Plus como plano garantido de automação ilimitada.
