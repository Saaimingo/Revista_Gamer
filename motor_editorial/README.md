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

O SQLite usa o esquema v3. A abertura de bancos v1/v2 aplica migrações aditivas e mantém os registros e associações existentes.

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

Os testes usam diretórios temporários. Cobrem os 11 contratos herdados da v0.1, isolamento e retomada, idempotência sob chamadas concorrentes, migração v2, ordem da edição, revisão vigente, direitos por matéria, confirmação humana, rotas locais e ausência de publicação.

## Orquestração durável — CODEX-003

As tarefas de agentes ficam no mesmo SQLite da aplicação, em tabelas separadas do fluxo editorial v0.2. O registro preserva payload, idempotency key, tentativas, lease, estado, resultado estruturado e `profile_id` + versão + hash. Eventos não copiam prompts, tokens, códigos OAuth ou corpo integral do provedor.

Prove a cadeia sintética (pesquisador → redator → revisão reprovada → correção → revisão aprovada):

```powershell
py -3.11 -m motor_editorial agents demo-chain
py -3.11 -m motor_editorial agents list
```

O perfil `internal-validation-chronicler@1.0.0` é somente uma fixture técnica. Ele não representa persona pública nem conteúdo editorial. Falhas recuperáveis aguardam backoff; lease vencido antes de iniciar uma chamada pode ser retomado; lease vencido depois do início de chamada externa vira `uncertain` e não é repetido automaticamente.

O lease tem proprietário interno e geração de fencing persistidos no esquema SQLite v5. O dispatcher envia heartbeat enquanto o executor síncrono está ativo; apenas o proprietário atual, com lease válido, pode marcar a chamada externa, renovar, concluir ou falhar a tarefa. O token de propriedade não é incluído em eventos nem na representação da tarefa. Se o heartbeat deixa de confirmar ownership, o dispatcher interrompe as mutações finais e reconcilia o estado durável. A renovação não torna seguro repetir uma chamada externa ambígua: nesses casos a tarefa permanece `uncertain`.

Agendas usam intervalo em segundos e política de atraso `skip` ou `run_once`. O fuso é guardado como metadado e os instantes são UTC; não há sintaxe cron nesta etapa. Uma agenda nova fica desativada:

```powershell
py -3.11 -m motor_editorial scheduler add exemplo validation.research --executor simulated --interval-seconds 3600 --payload '{"role":"researcher"}'
py -3.11 -m motor_editorial scheduler list
```

### Prova técnica opcional com o plano ChatGPT

O acesso oficial é via Sign in with ChatGPT (SIWC), autorização explícita no navegador e escopo de uso do plano. Não use nem configure `OPENAI_API_KEY`. Para instalar a dependência OIDC opcional em ambiente isolado:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-siwc.txt
.\.venv\Scripts\python.exe -m motor_editorial siwc login
.\.venv\Scripts\python.exe -m motor_editorial siwc status
.\.venv\Scripts\python.exe -m motor_editorial siwc models
.\.venv\Scripts\python.exe -m motor_editorial siwc probe
```

`siwc login` mostra o endereço oficial e aguarda o callback apenas em `127.0.0.1`; o usuário precisa entrar no ChatGPT e consentir. A prova chama somente o catálogo de modelos e uma inferência não editorial do Responses API, em stream com `store=false`. O acesso depende da elegibilidade da conta/app e da franquia compartilhada do plano; `429` pausa chamadas e não presume horário de reset. As credenciais ficam no Windows DPAPI, fora do repositório. A autenticação não dá acesso a conversas nem memória do ChatGPT.

O executor SIWC desta etapa rejeita qualquer tarefa que não seja `siwc.integration_probe`. A agenda Plus continua desativada. Ativação recorrente depende de decisão operacional separada, frase explícita no comando e `MOTOR_EDITORIAL_ALLOW_PLUS_SCHEDULING=1` no processo worker.

## Debian 12 e VPS futura

`deploy/systemd/revista-gamer-orchestrator.service.example` prepara um worker único, sem porta de entrada, com dados em `/var/lib/revista-gamer`, reinício por falha e diretório restrito. O exemplo não foi instalado nem habilitado. Configure usuário de serviço, venv e diretórios conforme o relatório antes de operar. Agendas permanecem desativadas por padrão.

Não copie a credencial Windows DPAPI para Linux. Para VM, use um host ID estável e próprio e mantenha a elegibilidade remota por confirmar. O repositório é público, porém não tem arquivo LICENSE; isso não prova status open source. Apps privados hospedados são elegíveis somente quando selecionados/aprovados pela OpenAI. Consulte a [especificação CODEX-003](../docs/engenharia/ESPECIFICACAO-CODEX-003-ORQUESTRACAO-PLUS.md) e o [relatório técnico](../docs/engenharia/RELATORIO-ORQUESTRACAO-AGENTES-PLUS.md).
