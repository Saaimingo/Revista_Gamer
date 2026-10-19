# Especificação ENG-CODEX-003 — Orquestração durável e prova SIWC

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-003
- **Versão do documento:** 1.0 (não define versão comercial do Motor)
- **Status:** aprovado para implementação no escopo descrito
- **Data:** 2026-10-19
- **Aprovador:** Direção do projeto, por instrução direta nesta sessão
- **Dependências:** Motor Editorial v0.2 integrado pelo PR #6; D-016/D-017; anteprojeto de orquestração de 2026-10-19; contrato de entregas

## Objetivo

Construir uma camada técnica substituível sobre o Motor Editorial v0.2: fila SQLite durável, dispatcher, executores, identidades versionadas, retomada segura, eventos de execução e agendador configurável. Provar primeiro uma cadeia sintética sem rede. Preparar uma única tarefa técnica não editorial para provar, após consentimento, a integração oficial Sign in with ChatGPT (SIWC) com o plano do diretor.

A versão do produto não é atribuída nesta ordem. O código existente continua sendo a baseline v0.2 acrescida desta etapa de engenharia.

## Escopo aprovado

1. Migrar o banco local aditivamente para o esquema v4 e armazenar tarefas, leases, tentativas, resultados estruturados, agendas e eventos sem credenciais.
2. Deduplicar por chave idempotente; permitir retry limitado para erros classificados; retomar lease expirado somente quando nenhuma chamada externa começou; marcar como `uncertain` qualquer chamada externa interrompida sem resultado conclusivo.
3. Despachar por identificador de executor e identidade de perfil. Persistir `profile_id`, versão e SHA-256 em cada tarefa.
4. Executar uma cadeia totalmente simulada de pesquisador, redator, revisão reprovada, correção e nova revisão aprovada, sempre com dados fictícios e zero I/O externo.
5. Criar agenda por intervalo configurável, com `skip` ou `run_once` para atrasos. Agendas novas começam desativadas. Timestamps são UTC; o campo de fuso é metadado, não uma expressão cron.
6. Implementar autenticação OAuth Authorization Code + PKCE oficial, callback somente em loopback, validação OIDC do ID token, escopo de uso direto, rotação serializada de refresh token e armazenamento protegido local.
7. Permitir somente uma tarefa SIWC de integração técnica sintética nesta etapa. A chamada usa `GET /v1/models` para catálogo e `POST /v1/responses` com `store=false` e `stream=true`; nenhuma API key é lida ou criada.
8. Instalar dependência OIDC criptográfica opcional em `requirements-siwc.txt`; a simulação e a suíte padrão continuam funcionando sem a dependência opcional.
9. Documentar execução futura como serviço systemd no Debian 12 sem instalar, habilitar ou ativar o serviço nesta entrega.

## Limites e exclusões

- Nenhuma pauta real, busca de fontes, artigo, identidade pública de cronista ou conteúdo da revista nesta etapa.
- `internal-validation-chronicler@1.0.0` e `internal-siwc-integration-probe@1.0.0` são perfis técnicos fictícios e não são personas aprovadas pelo Bloco 02.
- Nenhuma publicação, automação editorial de produção, agenda Plus ativa, compra, API paga, serviço contratado, leitura de cookies, extração de tokens de sessão ou acesso a conversas do ChatGPT.
- Nenhuma migração de credenciais Windows para Debian/VPS. Tokens DPAPI são vinculados ao usuário/host Windows.
- Não atribuir licença open source ou conceder elegibilidade remota ao projeto por inferência. Não adicionar licença ao repositório nesta etapa.

## Contratos de execução

- Executor: `execute(task, profile, context) -> objeto estruturado`.
- A fila só considera concluída uma inferência SIWC depois do evento `response.completed` e validação determinística do JSON da prova.
- O dispatcher não repete uma chamada ambígua. `429` de limite suspende chamadas; usuário não elegível e escopo/política recusados ficam bloqueados; indisponibilidade `503` pode ter retry limitado.
- Logs persistem estados, códigos e hashes de saída; não registram tokens, authorization codes, URLs de callback, corpo da requisição, texto integral do provedor ou e-mail.
- O modelo da prova precisa constar no catálogo retornado para a conta autenticada. A franquia de uso da assinatura Plus continua sujeita aos limites compartilhados do plano.

## Critérios verificáveis

- A cadeia simulada completa as cinco etapas e demonstra rejeição, correção e reavaliação sem abrir socket.
- A tarefa permanece no SQLite após recriação do `Store`; repetição da chave idempotente não duplica a tarefa.
- Falha recuperável respeita o backoff e o limite; lease vencido antes da chamada é retomado; lease após chamada externa vira `uncertain`.
- Agenda desativada não dispara; política `run_once` dispara uma vez após atraso; `skip` avança sem gerar tarefa.
- OAuth testado por fixtures locais: state, PKCE, `client_id`, audience, issuer, expiração, nonce e escopo; Responses testado por stream fixture, sem rede real.
- Suíte legada e testes novos passam em Windows/Python 3.11.9. Uma resposta real só será declarada após login consentido e evento final validado.

## Elegibilidade SIWC e hospedagem

Fontes oficiais consultadas em 2026-10-19:

- [Sign in with ChatGPT — Quickstart](https://developers.openai.com/siwc/quickstart)
- [Registro e login de clientes open source](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Limitações do fluxo em preview](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Contas, refresh e limites de uso](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [VMs self-hosted](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms)
- [Integração open source e projetos pessoais locais](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)
- [Sign in with ChatGPT em websites](https://developers.openai.com/siwc/website)

O fluxo local de projeto pessoal pode usar a via SIWC, se a conta e a solicitação forem admitidas. Isso não comprova a elegibilidade da conta até o consentimento e a primeira resposta válida.

O repositório GitHub consultado é público, mas não contém arquivo LICENSE. Visibilidade pública sem licença não comprova enquadramento open source. A documentação informa que uso do plano ChatGPT em apps privados é restrito a clientes selecionados; apps pagos ou hospedados remotamente devem solicitar acesso antes de oferecê-lo a usuários. O guia para VM remota descreve especificamente um app open source. Portanto, a elegibilidade de uma instalação privada na VPS está **não confirmada** e a integração remota fica bloqueada até confirmação/aprovação oficial apropriada. A autorização de uma execução local não se estende a uma agenda remota.

## Migração futura para Debian 12/VPS

O código é portável a Python 3.11+ e SQLite. Quando houver autorização operacional e elegibilidade remota confirmada, instalar o serviço em usuário sem privilégios, dados em `/var/lib/revista-gamer`, diretório de credenciais com modo `0700`, arquivo de tokens Linux com modo `0600`, `XDG_DATA_HOME` dentro do diretório privado e uma única instância do worker sobre disco local. A unidade de exemplo limita gravação ao diretório de dados e reinicia falhas do processo.

Para futura sessão SIWC em VM, seguir a orientação oficial: host ID estável e próprio da VM, fluxo OAuth local para a mesma aplicação/conta/workspace e transferência segura somente se permitido. Não copiar o arquivo Windows DPAPI. A documentação oficial informa que atribuição de uso e revogação por host não estão disponíveis para sessões transferidas; essa limitação e a elegibilidade do app privado precisam ser resolvidas antes de ativar chamadas remotas.

## Pendências

- Consentimento do diretor no navegador e resposta de uma única inferência local SIWC.
- Elegibilidade do app em hospedagem privada/remota e critérios formais de acesso para VM.
- Perfis públicos, política de evidências, coleta real, cotas operacionais e ativação de qualquer agenda editorial permanecem fora deste escopo.
