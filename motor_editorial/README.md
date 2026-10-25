# Motor Editorial v0.2 + etapa de engenharia CODEX-003

O núcleo editorial v0.2 continua local e offline para testar fluxos independentes e compor uma edição com várias matérias. A etapa CODEX-003 acrescenta fila SQLite, dispatcher, agenda por intervalos e executores substituíveis. Requer Python 3.11 ou superior. O núcleo usa a biblioteca padrão; SIWC é opcional e usa a dependência OIDC indicada em `requirements-siwc.txt`.

Todos os jogos, fontes, acontecimentos e ativos das fixtures são fictícios. A execução editorial simulada não consulta notícias nem chama modelos. Uma tarefa SIWC separada e explicitamente iniciada pode fazer uma única prova técnica não editorial após consentimento OAuth. Não há rota ou comando de publicação.

## Executar no Windows 11

Na raiz do repositório, com Python 3.11 instalado:

```powershell
py -3.11 -m motor_editorial init
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial status
py -3.11 -m motor_editorial web
```

A primeira execução multipauta cria três pautas independentes: Orbit Racers chega à checagem de mídia; Garden of Echoes fica bloqueada pela segunda revisão; Clockwork Harbor registra uma falha transitória de apuração. A segunda execução retoma somente as etapas pendentes, sem repetir importação ou etapas concluídas. A edição permanece bloqueada até uma pessoa excluir explicitamente a pauta reprovada, com responsável, motivo e confirmação exata:

```powershell
py -3.11 -m motor_editorial exclude <edition_id> <story_id>
```

Depois da exclusão humana, a prévia interna reúne as duas matérias elegíveis na ordem persistida. Para revisar e registrar aprovação somente interna:

```powershell
py -3.11 -m motor_editorial approve <edition_id>
```

`status` mostra execuções, estados das pautas, composição e associações ordenadas. Para retomar uma pauta isolada, use os identificadores exibidos por `status`:

```powershell
py -3.11 -m motor_editorial run-story <run_id> <story_id>
```

O painel local abre em `http://127.0.0.1:8765/`. Ele oferece execução em lote, retomada individual de falha transitória, detalhes de fontes e revisão, direitos por matéria, exclusão humana auditada e prévia multipauta. Antes de servir uma prévia, revalida a composição e os direitos; se algo mudar após uma aprovação, invalida essa aprovação, atualiza a prévia e aguarda nova confirmação humana. Não existe publicação.

## Compatibilidade v0.1

`demo-v1` executa a fixture original de uma pauta e mantém as garantias cobertas pelos 11 testes da v0.1, inclusive a rejeição anterior à gravação quando a fixture contém mais de uma pauta selecionável. A nova fixture está em `fixtures/demo-multipauta.json`; a antiga permanece em `fixtures/demo.json`.

O SQLite usa o esquema v5. A abertura de bancos v1–v4 aplica migrações aditivas; os testes incluem a migração v3→v5 com preservação de registros e restauração de backup, além da inclusão das colunas de lease em v4. Faça e confira um backup antes de atualizar um banco local: o projeto não instala nem agenda backups automáticos. Bancos com versão posterior à suportada são recusados antes de qualquer alteração no arquivo.

## Dados e diretório

Por padrão, `motor_editorial/runtime/` guarda `motor.sqlite3` e artefatos locais e é ignorado pelo Git. Para usar uma pasta isolada:

```powershell
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-demo-v02" init
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-demo-v02" demo
```

Os IDs de pautas, itens e edições incluem o identificador da execução para evitar colisão entre execuções independentes. Tentativas de etapa, revisões, fontes, direitos, decisões de exclusão e aprovações ficam no SQLite com trilha de auditoria.

## Testes

```powershell
py -3.11 -m unittest discover -s motor_editorial/tests -v
```

Os testes usam diretórios temporários. Cobrem os contratos do Motor v0.2, migrações SQLite, isolamento e retomada, idempotência, concorrência/leases/fencing, revisão editorial vigente, fontes/citações, direitos por matéria, confirmação humana, rotas locais e ausência de publicação. Os ensaios ENG-CODEX-006 usam executores e clientes de fixture; não fazem chamadas SIWC.

## Orquestração durável — CODEX-003

As tarefas de agentes ficam no mesmo SQLite da aplicação, em tabelas separadas do fluxo editorial v0.2. O registro preserva payload, idempotency key, tentativas, lease, estado, resultado estruturado e `profile_id` + versão + hash. Eventos não copiam prompts, tokens, códigos OAuth ou corpo integral do provedor.

Prove a cadeia sintética (pesquisador → redator → revisão reprovada → correção → revisão aprovada):

```powershell
py -3.11 -m motor_editorial agents demo-chain
py -3.11 -m motor_editorial agents list
```

O perfil `internal-validation-chronicler@1.0.0` é somente uma fixture técnica. Ele não representa persona pública nem conteúdo editorial. Falhas recuperáveis aguardam backoff; lease vencido antes de iniciar uma chamada pode ser retomado; lease vencido depois do início de chamada externa vira `uncertain` e não é repetido automaticamente.

O lease tem proprietário interno e geração de fencing persistidos no esquema SQLite v6. A migração adiciona metadados de janelas locais ao `agent_schedules` existente, sem alterar a fila nem abrir o banco runtime nesta entrega. O dispatcher envia heartbeat enquanto o executor síncrono está ativo; apenas o proprietário atual, com lease válido, pode marcar a chamada externa, renovar, concluir ou falhar a tarefa. O token de propriedade não é incluído em eventos nem na representação da tarefa. Se o heartbeat deixa de confirmar ownership, o dispatcher interrompe as mutações finais e reconcilia o estado durável. A renovação não torna seguro repetir uma chamada externa ambígua: nesses casos a tarefa permanece `uncertain`.

Agendas usam intervalo em segundos e política de atraso `skip` ou `run_once`. O fuso é guardado como metadado e os instantes são UTC; não há sintaxe cron nesta etapa. Uma agenda nova fica desativada:

```powershell
py -3.11 -m motor_editorial scheduler add exemplo validation.research --executor simulated --interval-seconds 3600 --payload '{"role":"researcher"}'
py -3.11 -m motor_editorial scheduler list
```

O Radar também aceita grupos de **3 a 6 horários locais por dia**, com instantes persistidos em UTC, `skip`/`run_once`, pausa/retomada do grupo e `dry_run=true`. Informe quotas diárias por hostname exato; cada pedido HTTP e cada salto de redirect reserva uma unidade no ledger persistente do Radar. Host sem quota configurada fica bloqueado. No Windows, instale a base IANA usada por `zoneinfo`:

```powershell
py -3.11 -m pip install -r requirements-radar.txt
# Exemplo somente de sintaxe: horários e example.invalid são fixtures, não agenda aprovada.
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler windows-add radar-demo radar.general.scan --times 07:00 13:00 19:00 --domain-quota example.invalid=8 --payload '{"source_ids":["fixture-source"]}'
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler list
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler pause-group radar-demo
```

O configurador sempre cria janelas `enabled=false` e `dry_run=true`; não inicia worker, cron ou coleta real. `resume-group` retoma na próxima janela futura e continua em modo dry-run. O worker vazio consulta a fila existente e não invoca executor/IA. Horários e fontes de operação real dependem de autorização própria e de integração do coletor nas etapas seguintes.

### Radar geral e fila de triagem (ENG-CODEX-007 E10)

`RadarGeneralService` combina perfis `SourceProfile` explicitamente fornecidos com o `IncrementalRadarService` e o `RadarStore` existentes. Só snapshots novos ou mudanças materiais acima do `relevance_threshold` formam `DiscoveryBatch`; `304`, repetição e polling sem mudança não criam tarefa. Grupos de republicação e grupos de origem de alegações viram um item, com documentos, fontes, relações e estado epistêmico preservados.

`RadarTriagePolicy` permite configurar threshold e pesos de prioridade por tipo de evento. O score é um filtro determinístico de fila, não uma avaliação editorial nem sinal de confirmação. Um batch não vazio cria uma tarefa contratual `agent.role.triage_analyst` na mesma `AgentQueue`, com gate humano preservado. O executor desta etapa é `triage.pending`; a tarefa fica enfileirada e não chama modelo nem cria promoção à carteira. A integração de papéis ao dispatcher continua prevista na E13.

### Prova técnica opcional com o plano ChatGPT

O acesso oficial é via Sign in with ChatGPT (SIWC), autorização explícita no navegador e escopo de uso do plano. Não use nem configure `OPENAI_API_KEY`. Para instalar a dependência OIDC opcional em ambiente isolado:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-siwc.txt
.\.venv\Scripts\python.exe -m motor_editorial siwc login
.\.venv\Scripts\python.exe -m motor_editorial siwc status
.\.venv\Scripts\python.exe -m motor_editorial siwc models
.\.venv\Scripts\python.exe -m motor_editorial siwc probe --model gpt-6-luna --reasoning-effort max
```

`siwc login` mostra o endereço oficial e aguarda o callback apenas em `127.0.0.1`; o usuário precisa entrar no ChatGPT e consentir. A prova chama somente o catálogo de modelos e uma inferência não editorial do Responses API, em stream com `store=false`. O acesso depende da elegibilidade da conta/app e da franquia compartilhada do plano; `429` pausa chamadas e não presume horário de reset. As credenciais ficam no Windows DPAPI, fora do repositório. A autenticação não dá acesso a conversas nem memória do ChatGPT.

O executor de prova técnica rejeita qualquer tarefa que não seja `siwc.integration_probe`. O executor editorial da ENG-CODEX-004 é separado e aceita somente as oito etapas limitadas de `editorial.stage`, com `gpt-6-luna`, `reasoning.effort=max`, uma tentativa por tarefa e checkpoints SQLite. Ele não pesquisa a web, não cria persona pública e sempre termina em revisão humana; não existe rota de publicação. A v1.2.0 faz uma consulta ao catálogo por execução e compartilha o resultado entre as etapas. As chamadas editoriais usam Responses com `store=false` e streaming. O preview não aceita `max_output_tokens`, então as metas de palavras são instruções e validações locais, não um limite rígido de geração. A agenda Plus continua desativada. Ativação recorrente depende de decisão operacional separada, frase explícita no comando e `MOTOR_EDITORIAL_ALLOW_PLUS_SCHEDULING=1` no processo worker.

### Experimento local ENG-CODEX-004

Prepare e revise manualmente um pacote de evidências antes de executar. O comando usa o SIWC já autenticado, verifica que Luna está no catálogo da conta, e guarda o artefato no diretório privado selecionado:

```powershell
.\.venv\Scripts\python.exe -m motor_editorial --data-dir "$env:LOCALAPPDATA\RevistaGamer\Codex004-Editorial" editorial run --packet docs\engenharia\evidencias\ENG-CODEX-004-RTX5090-PACOTE-FONTES.json
```

Passe `--run-id <UUID>` para retomar a mesma cadeia. Etapas concluídas são reutilizadas pelo idempotency key; chamada externa ambígua não é repetida automaticamente. O artefato `artifacts/codex004/<run-id>.json` contém checkpoints, versão/hash do perfil, modelo/esforço efetivos, tempos e usage retornado. O ensaio não autoriza publicação nem elimina a revisão editorial humana.

## Debian 12 e VPS futura

`deploy/systemd/revista-gamer-orchestrator.service.example` prepara um worker único, sem porta de entrada, com dados em `/var/lib/revista-gamer`, reinício por falha e diretório restrito. O exemplo não foi instalado nem habilitado. Configure usuário de serviço, venv e diretórios conforme o relatório antes de operar. Agendas permanecem desativadas por padrão.

Não copie a credencial Windows DPAPI para Linux. Para VM, use um host ID estável e próprio e mantenha a elegibilidade remota por confirmar. O repositório é público, porém não tem arquivo LICENSE; isso não prova status open source. Apps privados hospedados são elegíveis somente quando selecionados/aprovados pela OpenAI. Consulte a [especificação CODEX-003](../docs/engenharia/ESPECIFICACAO-CODEX-003-ORQUESTRACAO-PLUS.md) e o [relatório técnico](../docs/engenharia/RELATORIO-ORQUESTRACAO-AGENTES-PLUS.md).

## Fase 0 — diagramador offline (Issue #17)

A demonstração da Fase 0 usa somente matérias, referências e direitos sintéticos. Ela deriva necessidades visuais, consulta um índice SQLite local de metadados, gera um plano versionado e bloqueia a prévia quando direitos, hashes, referências ou integridade falham. Os cenários cobrem reportagem com imagens pequenas, comparativo e mapa panorâmico.

```powershell
.\.venv\Scripts\python.exe -m motor_editorial --data-dir "$env:TEMP\revista-gamer-layout-demo" layout-demo
```

Relatórios, planos, validações e prévias ficam em `artifacts/layout-demo/` sob o diretório de dados selecionado. Os placeholders não são as imagens de contexto do Bloco 03. A prévia é interna, não há rede, SIWC ou API paga, e a demonstração termina aguardando revisão humana.

Código e relatório estão na [PR #18](https://github.com/Saaimingo/Revista_Gamer/pull/18), aberta e sem merge. A cadeia C0–C5 é experimental e não integra a `main`.

## Esteira sintética fim a fim — ENG-CODEX-006

`factory-demo` percorre fonte/organização, brief editorial, rascunho, checagem, revisão vigente, inventário de direitos sintético, `StoryPackage.v0`, índice/layout, validação determinística, prévia interna e um gate de aprovação explicitamente simulado. Todas as tarefas passam por uma única `AgentQueue`/`TaskDispatcher` e pelo ledger `agent_tasks`/`agent_task_events`; não chama o runner legado `layout-demo`.

```powershell
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-factory-demo" factory-demo
```

A fixture `fixtures/factory-demo.json` contém duas fontes fictícias sob `example.invalid` e perfis neutros versionados; nada é buscado na rede. O relatório e a prévia HTML ficam em `artifacts/factory-demo/<run_id>/`; evidências e hashes do C1 estão no [relatório técnico](../docs/engenharia/ENG-CODEX-006-C1-RELATORIO.md). `simulated_approved_internally` registra somente o resultado do teste: não altera uma edição real, não é aceite da direção e sempre mantém `published=false`. Use o mesmo `--run-id` para retomar as mesmas tarefas idempotentes.
