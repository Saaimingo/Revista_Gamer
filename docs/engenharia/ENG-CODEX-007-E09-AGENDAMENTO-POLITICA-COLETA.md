# ENG-CODEX-007 — E09: agendamento e política de coleta ajustável

**Setor responsável:** Engenharia e Codex
**Identificador:** ENG-CODEX-007-E09
**Versão:** v0.1
**Status:** validado localmente
**Data de atualização:** 2026-10-25
**Dependências:** [Issue #28](https://github.com/Saaimingo/Revista_Gamer/issues/28), [ordem E01–E19 da direção](https://github.com/Saaimingo/Revista_Gamer/blob/fundador2/eng-codex-007-regimento-radar-agentes-2026-10-25/docs/engenharia/ENG-CODEX-007-ORDEM-DE-SERVICO-EXECUCAO-CONTINUA-v0.1.md), E04–E08 do Radar.
**Aprovador:** direção, por autorização contínua da Issue #28; esta validação não aprova operação real.

## Objetivo e limites

Adicionar janelas diárias locais configuráveis para o Radar, com horário interno em UTC, recuperação previsível de atrasos, quotas persistentes por domínio, pausa/retomada e execução simulada. A implementação estende o `AgentQueue` e o `TaskDispatcher` existentes. As novas agendas são criadas desligadas e com `dry_run=true`.

Não foram escolhidos horários operacionais nem cadastradas fontes. E09 não inicia worker, cron, coleta externa, inferência, SIWC/Plus, serviço contínuo ou publicação. A ligação da tarefa de coleta ao `DiscoveryBatch` pertence à E10.

## Implementação

- O schema do Motor passa de v5 a v6 com campos aditivos em `agent_schedules`: grupo, tipo `daily_window`, horário local, tolerância de atraso, quotas serializadas e `dry_run`. Testes migraram fixtures v5→v6 e v3/v4→v6 preservando linhas. Nenhum banco runtime foi aberto ou migrado.
- `AgentQueue.create_daily_window_set()` aceita 3 a 6 horários `HH:MM`, fuso IANA, política `skip|run_once`, tolerância configurável de 0 a 86400 segundos e quotas positivas por hostname. IDs dos horários são estáveis dentro do grupo; uma transação cria todas as janelas ou nenhuma.
- Cada grupo usa as tabelas `agent_schedules`, `agent_tasks`, `agent_task_events` e o dispatcher já existentes. A agenda grava o próximo instante em UTC e leva uma fotografia explícita de fuso, horário, quota diária e `dry_run=true` no payload da tarefa.
- `pause-group` desliga o grupo inteiro. `resume-group` agenda cada horário na próxima ocorrência local futura e não repõe janelas passadas durante a pausa. Janelas diárias não podem ser ativadas isoladamente. O `misfire_grace_seconds` padrão é 300; atraso dentro da tolerância agenda normalmente. Fora dela, `skip` avança sem tarefa, enquanto `run_once` produz uma tarefa para cada janela do grupo que venceu durante a indisponibilidade, uma vez por horário, depois avança para a próxima ocorrência futura.
- Em horário local ambíguo no retorno do horário de verão, vale a primeira ocorrência (`fold=0`). Um horário inexistente no avanço do relógio desloca-se pelo intervalo da lacuna. Testes usam `America/New_York` para exercitar esses dois casos e `America/Sao_Paulo` para conversão UTC.
- O schema independente do Radar passa de v4 a v5 com `radar_domain_quota_events`, um ledger append-only. `PersistentDomainQuotaGuard` reserva atomicamente cada tentativa HTTP por hostname, data local e fuso; reservas repetidas com a mesma chave são idempotentes, limites não são excedidos sob concorrência e uma chamada sem quota configurada falha fechada. Quota esgotada devolve `rate_limited` e o próximo reset local. Cada salto de redirect reserva quota do hostname de destino.
- Quota usa hostname normalizado exato, incluindo aliases de subdomínio como entradas separadas; não tenta inferir o domínio registrável/eTLD+1. Os limites são por dia local no fuso escolhido. A agenda não permite desativar `dry_run` nesta unidade.
- O suporte de fuso usa `zoneinfo`. O Python distribuído no Windows não trouxe dados IANA neste ambiente; foi adicionada a dependência de primeira parte `tzdata` em `requirements-radar.txt`, de acordo com a [documentação Python de `zoneinfo`](https://docs.python.org/3.11/library/zoneinfo.html). Foi instalada somente no `.venv` local: versão `2026.5`.

## Como configurar localmente

Exemplo de sintaxe apenas. Horários e `example.invalid` são valores sintéticos, não uma escala aprovada:

```powershell
py -3.11 -m pip install -r requirements-radar.txt
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler windows-add radar-demo radar.general.scan --times 07:00 13:00 19:00 --domain-quota example.invalid=8 --payload '{"source_ids":["fixture-source"]}'
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler list
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-radar-demo" scheduler pause-group radar-demo
```

`windows-add` não ativa agenda. `resume-group` permite retomar o grupo ainda em `dry_run=true`; o worker só é executado por comando explícito e continua usando o dispatcher existente.

## Evidências de validação

Ambiente: Windows, CPython 3.11.9, `tzdata 2026.5`. Todos os casos usaram bancos SQLite em diretórios temporários, horários simulados, hosts `.invalid`, resolver/transporte falsos e nenhuma chamada de IA.

- `python -m unittest discover -s motor_editorial/tests -p 'test_radar*.py' -q` — **40/40 OK**, 20,899 s. Inclui DST, migração v4→v5, reserva concorrente/idempotente, permanência após reinício e bloqueio do transporte ao esgotar quota.
- `python -m unittest discover -s motor_editorial/tests -p 'test_orchestration.py' -q` — **41/41 OK**, 23,108 s. Inclui migração v5→v6, CLI de configuração, grupos e relógio simulado.
- `python -m unittest discover -s motor_editorial/tests -q` — **162/162 OK**, 122,539 s.
- `python -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.
- Os testes da agenda provam três janelas e aceitação de quatro/seis; rejeitam contagem, hora e duplicidade inválidas; verificam default OFF, conversão UTC, payload dry-run/quota, atraso `skip/run_once`, pausa/retomada, dedupe em ticks repetidos, migração de fila v5 e ausência de execução de executor/IA no polling vazio.

Uma execução focada de Radar falhou primeiro porque o teste de idempotência tentou reaproveitar uma chave cuja reserva concorrente não havia vencido a corrida. O teste foi corrigido para reutilizar uma reserva confirmada; a suíte Radar focada e a suíte integral subsequentes passaram. Em uma execução focada de orquestração concorrente, o teste existente de heartbeat atrasou e falhou; passou isolado e também na suíte integral sequencial. Nenhum código de heartbeat foi alterado.

## Arquivos e próximo passo

Código: `motor_editorial/db.py`, `motor_editorial/orchestration.py`, `motor_editorial/orchestration_cli.py`, `motor_editorial/radar_policy.py`, `motor_editorial/radar_store.py`, `motor_editorial/radar_connectors.py`, `requirements-radar.txt`. Regressões: `motor_editorial/tests/test_orchestration.py`, `test_radar_policy.py`, `test_radar_store.py`, `test_radar_connectors.py`. Documentação: `motor_editorial/README.md`, `docs/engenharia/README.md` e este relatório.

E09 está `validado` por evidência local. Nenhuma coleta de fonte pública foi feita. **E10 — Radar geral → DiscoveryBatch → triagem** é a próxima etapa autorizada e deverá ligar a tarefa determinística ao catálogo/ledger Radar, garantindo que somente novidade material resulte em triagem de IA.

`published=false`; sem chamada SIWC/Plus, API paga, banco runtime, scheduler de produção, fonte pública externa, publicação, deploy ou merge.
