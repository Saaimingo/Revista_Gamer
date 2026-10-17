# Protocolo de handoff e comunicação entre blocos

A comunicação é **assíncrona via GitHub**. Abrir uma Issue NÃO acorda um chat nem notifica outro modelo automaticamente. O usuário ou uma automação futura, explicitamente autorizada, leva o trabalho ao bloco responsável. Cada bloco consulta suas pendências ao iniciar sessão.

## Pedir uma definição, arte, especificação ou correção

1. Criar GitHub Issue via template `Solicitação entre setores`.
2. Título: `[SETOR-ORIGEM -> SETOR-DESTINO] pedido objetivo`.
3. Descrever contexto, decisão necessária, arquivos/URLs atuais, impacto, critério de aceite e prioridade.
4. Indicar status `aberto`, `em_analise`, `bloqueado`, `resolvido` ou `cancelado` no corpo/atualizações. Sem labels, usar busca textual; labels podem ser criadas futuramente.
5. O destino responde na Issue e entrega seu documento via branch/PR quando aplicável.
6. Quem pediu **verifica** o resultado; fecha a Issue com link para documentação aprovada.
7. Se houver alteração global, direção atualiza `DECISOES.md` e `STATUS-GERAL.md`.

## Sem conflitos de edição

- Cada setor edita preferencialmente sua pasta. Mudanças no escopo de outro setor viram solicitação/PR.
- Especificação `proposta` não autoriza Codex a implementar como regra permanente.
- Conteúdo `aprovado` é requisito estável; atualização exige rastreio de mudanças e aprovação.
- Nunca armazenar segredos, arquivos comerciais confidenciais ou documentação com dados pessoais em Issue pública. Repositório pode estar público.
- Um bloco que não consegue acessar GitHub solicita ao diretor que medie uma entrega. **Não** alegar que escreveu ou leu o repositório sem ferramenta/artefato verificável.

## Parecer do fundador em cada pasta setorial — rotina permanente

**Decisão de fluxo:** conversas relevantes entre diretor e Chat Fundador devem produzir, ao encerrar cada rodada de discussão, um **parecer de integração arquivado na pasta do setor correspondente**. Assim o próximo chat-setor pode consultar a avaliação do fundador sem depender da memória de conversas separadas.

**Pasta-padrão:** `docs/<setor>/analises-fundador/`. Para o Bloco 03: `docs/visual/analises-fundador/`; Bloco 02: `docs/personagens/analises-fundador/`; Bloco 04: `docs/redacao/analises-fundador/`; Bloco 05: `docs/acervo/analises-fundador/`; Bloco 06: `docs/comercial/analises-fundador/`. Não mover arquivos de autoria do setor nem substituir contratos aprovados por pareceres.

**Ao final de cada conversa de avaliação:**
1. Fundador resume **o que foi apresentado e verificado** (com links para arquivos/commits, datas e versões), **o que funcionou**, **o que merece revisão** e **o que ainda falta decidir**.
2. Marcar separadamente cada afirmação como `observação`, `sugestão`, `pedido explícito do diretor`, `decisão ratificada` ou `pendência`. Usar **PROVISÓRIO** para discussões ainda em andamento e **PARECER FINAL DA RODADA** quando a direção encerrar aquela avaliação; final da rodada não equivale à aprovação do produto/identidade.
3. Registrar documento Markdown na pasta do setor, criar/atualizar link no README setorial e indicar **as próximas ações propostas ao bloco**, sem acionar o Codex nem lançar novos trabalhos por inferência.
4. Quando a observação tiver impacto em outro setor, registrar referência cruzada ou Issue de handoff; só alterar `docs/governanca/DECISOES.md` se houver autorização/decisão explícita do diretor.
5. Antes de encerrar a resposta ao diretor, informar o **link exato** para o parecer no GitHub e se ele é parcial ou final.

**Ao retomar qualquer chat-setor:** consultar o seu README, a pasta `analises-fundador/` e as Issues relevantes. O parecer é memória operacional consultável, não comunicação automática: o chat não recebe notificações em tempo real. Se o arquivo não estiver acessível ou não tiver sido gravado, declarar essa limitação e solicitar o link/consulta, sem fingir leitura.

**Prevalência:** decisões explícitas do diretor e contratos setoriais aprovados têm prioridade sobre comentários do fundador. Um parecer pode discordar tecnicamente de uma proposta e explicitar o motivo, mas não congelar marcas, personagens, layout ou publicação sem a decisão competente.

## Exemplo realista

Codex precisa da tolerância do Ranzinza a evidências conflitantes. Cria Issue destinada a Personagens com link para `docs/personagens/RANZINZA.md`. Setor Personagens elabora proposta e registra mudança. Direção aprova. Engenharia lê versão aprovada e implementa/testa. Issue é fechada com links e decisão.
