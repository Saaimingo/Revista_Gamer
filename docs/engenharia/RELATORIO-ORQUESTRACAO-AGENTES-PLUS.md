# Relatório técnico — ENG-CODEX-003 Orquestração e SIWC

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-003-REL
- **Versão do documento:** 1.1
- **Status:** implementação, prova SIWC local histórica e correção C-001 com validação offline; elegibilidade de hospedagem privada/remota não confirmada
- **Data:** 2026-10-19
- **Branch:** `codex/motor-editorial-orquestracao-agentes-plus`
- **Base:** `main` em `d9fbb6e`; PR #6 integrado em `794e9fcc20f5944031370bd7ddb93f8b323d9528`
- **PR desta etapa:** [#8 — CODEX-003: orquestração durável e integração SIWC](https://github.com/Saaimingo/Revista_Gamer/pull/8), aberto; sem merge

## Resultado implementado

- Esquema SQLite v5 aditivo com `agent_tasks`, `agent_task_events`, `agent_schedules` e migração v4 para a propriedade de lease.
- Fila com chave idempotente, tentativas limitadas, disponibilidade/backoff, leases, resultado estruturado e estados `queued`, `running`, `retry_wait`, `succeeded`, `failed`, `blocked`, `uncertain` e `cancelled`.
- Recuperação após reinício: lease expirado antes de chamada externa volta à fila; lease expirado depois do início de chamada vira `uncertain`, sem retry automático.
- Dispatcher usa executores registrados por ID e perfil imutável por ID, versão e hash.
- Cadeia simulada de cinco tarefas: pesquisador sintético, rascunho, reprovação, correção e aprovação. Não acessa rede nem usa persona pública.
- Scheduler por intervalo configurável, UTC, políticas `skip`/`run_once`, eventos de auditoria e desativado por padrão.
- SIWC oficial: registro dinâmico de client, loopback `127.0.0.1`, Authorization Code + PKCE S256, validação de state/nonce/JWKS/issuer/audience/expiração, escopo direto obrigatório, refresh serializado e credenciais protegidas.
- Executor Responses limitado à prova técnica `siwc.integration_probe`; não aceita artigo, pesquisa, ferramentas hosted ou tarefa editorial.
- Credential store no Windows usa DPAPI; Linux usa diretório privado e arquivo modo `0600`. Nenhum token, código OAuth, email ou texto integral de inferência é gravado nos logs de eventos.
- Unidade systemd de exemplo para Debian 12; não instalada, habilitada ou executada nesta máquina.

## Correção C-001 da Issue #11 — lease com ownership e fencing

**Causa:** o lease inicial de 120 segundos não cobria a inferência `fact_check` observada em 166,407 segundos. Um segundo worker podia recuperar a tarefa ainda ativa; as operações `complete`, `fail` e `mark_external_started` verificavam apenas `state='running'`, sem provar quem era o proprietário.

**Correção no PR #8:** o esquema v5 persiste `lease_owner` (UUID interno, não exposto em eventos/representação) e `lease_generation`. Cada claim incrementa a geração. `renew_lease`, marcação de chamada externa, conclusão e falha verificam estado, token, geração e validade temporal dentro de transações SQLite `BEGIN IMMEDIATE`. O dispatcher mantém heartbeat durante a execução síncrona, usando timestamps de microssegundos para não perder renovações de leases curtos. Um proprietário antigo não consegue alterar uma tarefa recuperada. Leases vencidos sem chamada externa podem ser retomados; após início externo, a recuperação é `uncertain` e nunca faz replay automático.

**Prova offline:** testes determinísticos com relógio controlado cobrem renovação para além do TTL enquanto um segundo worker tenta claim, conclusão íntegra por A, recuperação retomável antes de chamada externa, estado `uncertain` após chamada externa sem resultado, fencing do proprietário antigo, migração v4→v5 e token ausente de eventos/representação. Um teste concorrente mantém um executor simulado ativo além do TTL enquanto o heartbeat renova a posse. Esses testes não fazem chamadas SIWC.

**Resultado desta correção em Windows:** a suíte completa `motor_editorial/tests` passou **50/50** em Python 3.11. `compileall` terminou sem erro e `git diff --check` não encontrou problemas. A prova SIWC real descrita acima é histórica e não foi repetida; os testes SIWC desta suíte usam respostas/servidores de fixture.

## Elegibilidade e autorização SIWC

Documentação oficial distingue a rota local open source/projeto pessoal, sujeita à elegibilidade do usuário, da hospedagem privada: uso do plano em apps privados está disponível somente a clientes selecionados; apps pagos ou hospedados remotamente precisam solicitar acesso antes de oferecer o produto. O guia remoto SIWC descreve apps open source.

O repositório consultado é público, mas não contém LICENSE. Portanto, visibilidade pública não prova licença open source. A prova local abaixo confirma elegibilidade da conta e deste cliente/host para uma chamada sintética na data do teste. Ela não comprova elegibilidade de uma aplicação privada hospedada.

Nas duas primeiras tentativas, o callback local recebeu o retorno após consentimento, mas a validação do ID token encerrou com `ImmatureSignatureError`. Nenhuma credencial foi salva e nenhuma inferência foi feita. A consulta NTP (`time.windows.com`) mediu o Windows 30,44 segundos atrasado. O W32Time foi configurado para esse peer com autorização administrativa, mas `w32tm /resync` não obteve dados; a ferramenta `stripchart` pôde medir o peer e a diferença. Uma correção pontual de +30,438 segundos foi aplicada, após autorização, e a medição seguinte indicou desvio de 1,8 ms. O serviço ainda não confirmou sincronização automática. Como o cliente W32Time usa UDP 123 como porta de origem e o `stripchart` usa porta efêmera, o caminho de rede do serviço pode estar bloqueado; isso é uma hipótese, não confirmação. Consulte [ferramentas e comportamento do W32Time](https://learn.microsoft.com/en-us/windows-server/networking/windows-time-service/windows-time-service-tools-and-settings?tabs=config) e [diagnóstico de ausência de dados de hora](https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/error-message-run-w32tm-resync-no-time-data-available).

Na terceira tentativa, o login SIWC validou a identidade, persistiu a credencial protegida via DPAPI e concedeu `chatgpt.tokens.use.direct` mais `offline_access`. `siwc status` confirmou `authenticated: true`; `siwc models` listou os modelos disponíveis para a conta, incluindo `gpt-6.1-sol`. Em 2026-10-19, um único `siwc probe` real no Windows concluiu tarefa `dc23604e-f9c7-4faa-b837-8a4f5077105f` no estado `succeeded`, por `/v1/responses`, com `store:false` e streaming até `response.completed`. Modelo: `gpt-6.1-sol`; resposta sintética `status=ok`; `response_id=resp_0dfb847baed3c398016ad66e932f5487d2a32f6af4f36f4129`; SHA-256 da resposta: `09eb1a2b6d7bc88d1a00c9a46e68ac502fa6e8bb112ff54ac913da80a025e340`; uso reportado pelo provedor: 102 tokens de entrada, 16 de saída, 118 no total. Essa prova confirma o uso local para esta conta/host no momento do teste; não exercitou conteúdo editorial e não confirma a elegibilidade de aplicação privada/VPS.

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
- Duas tentativas iniciais falharam na validação temporal OIDC. Depois da correção pontual do relógio, `siwc status` confirmou login e escopo direto; `siwc models` confirmou modelos disponíveis; a chamada Responses real do probe concluiu com `succeeded` e JSON sintético validado.

Os testes automatizados não provam elegibilidade por si sós; a prova real acima confirma que a conta/cliente local recebeu escopo e concluiu uma resposta em 2026-10-19. O relógio local foi alinhado por correção pontual, mas a sincronização recorrente ainda não foi comprovada.

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

- Login e execução real no Plus: **validados para uma tarefa técnica sintética local**; não cobre tarefa editorial, operação contínua, outras contas ou hospedagem remota.
- Elegibilidade da conta nesta execução local e disponibilidade do modelo: confirmadas pelo fluxo oficial, catálogo e resposta válida em 2026-10-19; podem mudar por conta, host, modelo ou política.
- Aplicação privada hospedada: **não confirmada**; nenhuma chamada remota autorizada por este relatório.
- Testes Linux/Debian e operação 24 h: não executados nesta máquina; a unidade é configuração de referência. No Windows, a sincronização automática W32Time ainda não foi confirmada.
- Não foi implementado coletor de notícias, gestão de evidências, perfil público aprovado, harness de ferramentas ou publicação.
- O scheduler é intervalar e mantém agendas desativadas por padrão; não é cron e não está em execução contínua nesta entrega.
- Retenção/rotação e backup automatizados do SQLite não estão implementados; planejar antes de volume contínuo.
