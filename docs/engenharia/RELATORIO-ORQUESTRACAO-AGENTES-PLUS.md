# Relatório técnico — ENG-CODEX-003 Orquestração e SIWC

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-003-REL
- **Versão do documento:** 1.0
- **Status:** implementação validada localmente; consentimento e inferência SIWC reais pendentes
- **Data:** 2026-10-19
- **Branch:** `codex/motor-editorial-orquestracao-agentes-plus`
- **Base:** `main` em `d9fbb6e`; PR #6 integrado em `794e9fcc20f5944031370bd7ddb93f8b323d9528`
- **PR desta etapa:** [#8 — CODEX-003: orquestração durável e integração SIWC](https://github.com/Saaimingo/Revista_Gamer/pull/8), aberto como draft; sem merge

## Resultado implementado

- Esquema SQLite v4 aditivo com `agent_tasks`, `agent_task_events` e `agent_schedules`.
- Fila com chave idempotente, tentativas limitadas, disponibilidade/backoff, leases, resultado estruturado e estados `queued`, `running`, `retry_wait`, `succeeded`, `failed`, `blocked`, `uncertain` e `cancelled`.
- Recuperação após reinício: lease expirado antes de chamada externa volta à fila; lease expirado depois do início de chamada vira `uncertain`, sem retry automático.
- Dispatcher usa executores registrados por ID e perfil imutável por ID, versão e hash.
- Cadeia simulada de cinco tarefas: pesquisador sintético, rascunho, reprovação, correção e aprovação. Não acessa rede nem usa persona pública.
- Scheduler por intervalo configurável, UTC, políticas `skip`/`run_once`, eventos de auditoria e desativado por padrão.
- SIWC oficial: registro dinâmico de client, loopback `127.0.0.1`, Authorization Code + PKCE S256, validação de state/nonce/JWKS/issuer/audience/expiração, escopo direto obrigatório, refresh serializado e credenciais protegidas.
- Executor Responses limitado à prova técnica `siwc.integration_probe`; não aceita artigo, pesquisa, ferramentas hosted ou tarefa editorial.
- Credential store no Windows usa DPAPI; Linux usa diretório privado e arquivo modo `0600`. Nenhum token, código OAuth, email ou texto integral de inferência é gravado nos logs de eventos.
- Unidade systemd de exemplo para Debian 12; não instalada, habilitada ou executada nesta máquina.

## Elegibilidade e autorização SIWC

Documentação oficial distingue a rota local open source/projeto pessoal, sujeita à elegibilidade do usuário, da hospedagem privada: uso do plano em apps privados está disponível somente a clientes selecionados; apps pagos ou hospedados remotamente precisam solicitar acesso antes de oferecer o produto. O guia remoto SIWC descreve apps open source.

O repositório consultado é público, mas não contém LICENSE. Portanto, visibilidade pública não prova licença open source. Uma prova pessoal local no Windows pode seguir o fluxo SIWC caso a conta seja admitida e o diretor dê consentimento no navegador. Ainda não há evidência de que a conta/app foi admitida, pois o login e a resposta real não foram executados.

**VPS/app privado hospedado: elegibilidade não confirmada.** Não habilitar inferência remota, transferir credenciais ou ativar agenda Plus antes de obter confirmação oficial apropriada. O sistema não usa chave paga nem credencial extraída de sessão privada.

Fontes consultadas em 2026-10-19:

- [SIWC Quickstart](https://developers.openai.com/siwc/quickstart)
- [Registro e login](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Limitações do preview](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Refresh, credenciais e limites do Plus](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [VMs self-hosted](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms)
- [Projetos open source e projetos pessoais locais](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)
- [Sign in with ChatGPT em websites](https://developers.openai.com/siwc/website)

## Validação

Antes das alterações, a branch base passou **22/22 testes herdados** com Python 3.11.9 no Windows 11.

Validação final local:

- **46/46 testes passaram** na suíte completa com Python 3.11.9 e `.venv` contendo `PyJWT 2.15.1` + `cryptography 50.0.2`; os 22 contratos anteriores também passaram.
- `compileall` e `git diff --check` sem erros.
- A cadeia `agents demo-chain` executada via CLI em diretório temporário concluiu cinco tarefas, exibiu rejeição/correção/revisão aprovada e `external_calls: 0`.
- Regressões novas cobrem persistência após reabrir o SQLite, idempotência, disputa de claim entre workers, retry/backoff/limite, recuperação segura/incerta, políticas de agenda, bloqueio de segredo em payload, OAuth callback/state/PKCE/client ID, validação de assinatura/audience/issuer/nonce, refresh token rotativo e stream Responses.
- O fluxo SIWC foi validado com servidor callback local e respostas fixture; a requisição Responses foi inspecionada em teste, sem chamada real ao provedor.
- `siwc status` retornou `authenticated: false` e `direct_usage_scope: false`. Não há consentimento salvo para essa instalação.

Esses testes não provam elegibilidade da conta. A primeira resposta real ainda depende do consentimento do diretor no navegador e da admissão da conta/app pela OpenAI.

## Comandos locais

```powershell
py -3.11 -m unittest discover -s motor_editorial/tests -v
py -3.11 -m motor_editorial agents demo-chain
py -3.11 -m motor_editorial siwc login
py -3.11 -m motor_editorial siwc status
py -3.11 -m motor_editorial siwc models
py -3.11 -m motor_editorial siwc probe
```

O último comando faz uma única inferência sintética e só deve ser executado depois do consentimento. A conta Plus tem limite compartilhado em janela móvel com outros apps SIWC; o app não estima franquia ou horário de reset. `429` bloqueia novas chamadas SIWC até ação do usuário.

## Debian 12 e migração futura para VPS

O exemplo `deploy/systemd/revista-gamer-orchestrator.service.example` utiliza um usuário sem privilégios, `/var/lib/revista-gamer`, `XDG_DATA_HOME` privado, `UMask=0077`, filesystem protegido, sem porta de entrada, polling em SQLite local e `Restart=on-failure`. Instalação, enable, start, credenciais e configuração de agendas ficam para uma etapa operacional autorizada.

Passos que continuam condicionados à elegibilidade remota:

1. Confirmar oficialmente acesso SIWC para a instalação privada/remota; não inferir permissão a partir da rota local.
2. Criar host ID estável exclusivo da VM e aplicar serviço, backups e monitoramento de disco.
3. Completar OAuth de modo local conforme o guia OpenAI e transferir credenciais somente se a elegibilidade e os termos permitirem; manter refresh exclusivamente no host Linux.
4. Não copiar o arquivo DPAPI do Windows. A documentação OpenAI alerta que atribuição/revogação por host ainda não está disponível para sessões transferidas.
5. Confirmar perfis, fontes, limites, política de falhas e agenda específica antes de qualquer tarefa editorial.

## Limitações e pendências

- Login e execução real no Plus: **pendentes da participação do diretor no consentimento do navegador**.
- Elegibilidade da conta e capacidade/modelo específico: só podem ser confirmados pelo fluxo oficial e pela primeira resposta válida.
- Aplicação privada hospedada: **não confirmada**; nenhuma chamada remota autorizada por este relatório.
- Testes Linux/Debian e operação 24 h: não executados nesta máquina; a unidade é configuração de referência.
- Não foi implementado coletor de notícias, gestão de evidências, perfil público aprovado, harness de ferramentas ou publicação.
- O scheduler é intervalar e mantém agendas desativadas por padrão; não é cron e não está em execução contínua nesta entrega.
- Retenção/rotação e backup automatizados do SQLite não estão implementados; planejar antes de volume contínuo.
