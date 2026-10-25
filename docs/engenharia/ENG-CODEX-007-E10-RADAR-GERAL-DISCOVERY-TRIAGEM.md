# ENG-CODEX-007 — E10: Radar geral, DiscoveryBatch e fila de triagem

**Setor responsável:** Engenharia e Codex
**Identificador:** ENG-CODEX-007-E10
**Versão:** v0.1
**Status:** validado localmente
**Data:** 2026-10-25
**Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), ordem E01–E19 da direção na PR [#29](https://github.com/Saaimingo/Revista_Gamer/pull/29), Radar E04–E09 e contratos E02/E03.

## Critério e limite da unidade

E10 deve ligar o Radar geral incremental a um `DiscoveryBatch` validado pelo papel `triage_analyst@1.0.0`, aplicar uma política de novidade/threshold configurável, preservar pesos de prioridade auditáveis e evitar nova tarefa de IA quando o polling não encontrar mudança. Uma edição material de fonte deve gerar item candidato à triagem. Republicações e grupos de origem de alegação não podem multiplicar itens nem perder a proveniência.

Esta unidade entrega o candidato como item do batch e a tarefa de triagem na fila. Como o executor segue `triage.pending`, o lote **não despacha IA**, não emite `TriageDecision`, não grava promoção em `radar_candidates` e não escolhe a carteira editorial. A integração de papéis/executores ao dispatcher está na E13; a prova de modelo autorizado está na E17.

## Implementação

- `RadarGeneralService` recebe perfis `SourceProfile` já validados, chama o `IncrementalRadarService` existente e lê eventos/documentos/linhagens no `RadarStore` existente. Não cria coletor paralelo, fila paralela ou segundo dispatcher.
- O serviço considera apenas `first_seen` e mudanças materiais observadas (`title_changed`, `body_changed`, `corrected`, `removed`, `url_changed`, `origin_linked`). Snapshot duplicado, repetição e resposta HTTP `304 not_modified` não geram item.
- `RadarTriagePolicy` expõe `relevance_threshold` e `priority_weights` por tipo de `ObservationEvent`. O padrão técnico é threshold `0.50`, com pesos `first_seen=0.65`, `title_changed=0.85`, `body_changed=0.90`, `corrected=1.00`, `removed=0.35`, `url_changed=0.40` e `origin_linked=0.55`. Os valores, versão e score são incluídos em cada item para auditoria e podem ser substituídos pela configuração.
- O score usa somente o tipo determinístico do evento. Não mede interesse editorial, qualidade de fonte, confirmação ou confiança no conteúdo, e não soma frequência/viralidade. Esse score é um filtro técnico de fila, não uma decisão da direção sobre pauta.
- O serviço agrupa novidades por vínculo de republicação e, quando houver vínculo, por `claim_id + origin_group_id`. Um grupo já existente não recebe uma nova triagem só por ganhar uma republicação; alteração material em documento existente ainda pode gerar um único item para reavaliação.
- `diff` contém eventos/hash de alteração, IDs de documentos, snapshots, fontes e relações de proveniência. Quando existe alegação, preserva `epistemic_status` e relações `origin`/`republished`; `attributed_rumor` permanece explícito e não é promovido a conteúdo confirmado. O texto integral do artigo não vai para a tarefa.
- Cada batch não vazio produz uma única tarefa `agent.role.triage_analyst` com `AgentTaskEnvelope`, hash do perfil/entrada, snapshots e chave idempotente. O contrato do catálogo é validado antes de gravar na mesma `AgentQueue`; o gate humano do papel continua exigido e o executor fica `triage.pending`.
- Batch vazio, sem novidade acima do threshold, não escreve tarefa. O polling determinístico pode consultar o conector configurado, mas este código não despacha executor/LLM.

## Evidências de validação

Ambiente: Windows, CPython 3.11.9, SQLite temporário, fontes/feeds `.invalid`, relógio, resolver e transporte simulados.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_triage -v` — **4/4 OK**, 6,929 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **166/166 OK**, 129,768 s, serial.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.
- Os quatro testes demonstram: uma novidade gera batch/tarefa contratual pendente; um `304` posterior não cria outra tarefa nem inicia executor; threshold e pesos configuráveis são refletidos na evidência; uma republicação recém-adicionada a grupo conhecido não duplica; uma edição material do rumor cria um item, mantendo três fontes, relações de origem/republicação e status atribuído.

Código e testes: commit `949ac16` (`feat: queue Radar discoveries for triage`). A suíte integral foi executada após esse commit. Não foi feita chamada a fonte pública, LLM, SIWC/Plus, API paga ou banco runtime; não foi iniciado worker/dispatcher; sem publicação, deploy, merge ou alteração nos DNAs dos jornalistas. `published=false`.

## Continuação

Próxima unidade autorizada: **E11 — ResearchService sob demanda**, com perfis compartilhados, cache-first, escopo e retorno ligado à pauta. Antes de E13, as tarefas E10 permanecem pendentes na fila e não são processadas automaticamente.
