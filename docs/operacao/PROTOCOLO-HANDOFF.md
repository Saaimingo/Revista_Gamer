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

## Exemplo realista

Codex precisa da tolerância do Ranzinza a evidências conflitantes. Cria Issue destinada a Personagens com link para `docs/personagens/RANZINZA.md`. Setor Personagens elabora proposta e registra mudança. Direção aprova. Engenharia lê versão aprovada e implementa/testa. Issue é fechada com links e decisão.
