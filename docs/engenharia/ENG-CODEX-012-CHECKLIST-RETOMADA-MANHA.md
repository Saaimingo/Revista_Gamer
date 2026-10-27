# ENG-CODEX-012 — Checklist de retomada da manhã

**Registrado:** 2026-10-27, durante a execução autorizada da ENG-CODEX-012  
**Issue:** [#42](https://github.com/Saaimingo/Revista_Gamer/issues/42)  
**PR:** [#44](https://github.com/Saaimingo/Revista_Gamer/pull/44), draft, sem merge  
**Branch:** `codex/eng-codex-012-architecture-contracts`  
**Commit remoto confirmado antes da execução:** `792e78b` (`feat: prepare bounded ENG-CODEX-012 live pilot`)

## ATENÇÃO — Nova ordem prioritária da Direção (27/10/2026)

**ANTES DE RETOMAR, ler integralmente** [ENG-CODEX-012-ORDEM-DIRECAO-AUDITORIA-PRS-ESTRATEGIA-RADAR-2026-10-27.md](ENG-CODEX-012-ORDEM-DIRECAO-AUDITORIA-PRS-ESTRATEGIA-RADAR-2026-10-27.md) e a [auditoria da Issue #42](https://github.com/Saaimingo/Revista_Gamer/issues/42#issuecomment-6432841694). A Direção quer auditoria de PRs/contratos históricos e decisão baseada em evidências sobre **Radar/bots vs pesquisa web direta pelos agentes vs híbrido**, além da recuperação do run real sem repetir chamadas. A ordem acrescenta análise estratégica **sem alterar o teto público já autorizado**. A branch remota recebeu commits documentais durante a pausa: proteger o patch local de `eng_codex_011.py` e não fazer reset/rebase sobre árvore suja.

## Ordem explícita da Direção

> Retomar e resolver os problemas da linha editorial com agentes reais e pesquisas reais. Não encerrar com validação apenas offline: os bloqueios aparecem quando a fábrica encontra respostas e estados do mundo real. Preservar o trabalho real que já foi concluído; não repetir chamadas ou buscas válidas. Continuar autonomamente dentro das autorizações, registrar consumo por agente e manter revisão humana, sem publicação, merge ou deploy.

## Estado real da execução interrompida

- Run ID: `eng-codex-012-20261027T025920Z-e207b61f01c5`.
- Raiz privada: `%USERPROFILE%\.codex\Revista_Gamer\eng-codex-012-live-factory`.
- O preflight reutilizou o catálogo SIWC consultado uma vez; nenhum GET de catálogo redundante foi feito. A Direção autorizou `gpt-6-luna` com `max`; o executor retornou esses valores de fato.
- O Radar tentou três fontes autorizadas em série: Proton e SDL retornaram HTTP 200; Godot ficou `blocked` sem status HTTP/corpo. Foram registrados 10 candidatos. Não refazer esses requests.
- O agente real `triage_analyst` concluiu uma chamada em `gpt-6-luna`/`max`: 6.586 tokens de entrada, 4.189 de saída, 3.152 tokens de raciocínio (incluídos na saída), 10.775 totais, 77.719 ms, tentativa 1, sem retry. Resposta SHA-256 `f9b66c4bc9efd2fe2fa8f7e5917b72bb376687a0a4c7297add2e65abaa5d94ce`; receipt SHA-256 `0a23b5433b2827dab0d67d5ecd044b58980bb0ba2181ac6d0ef31a5e78ce1ec0`.
- A triagem foi persistida como `succeeded` no ledger; resposta bruta, manifesto, receipt e resultado estão presentes. O payload real recomenda manter Proton 11.0-2e e SDL 3.4.18 em monitoramento porque os dados iniciais não continham os changelogs; o investigador ainda não foi chamado.
- O runner bloqueou imediatamente depois de concluir a triagem. Causa reproduzida no receipt: o executor persistiu o receipt e o runner tentou gravá-lo outra vez com `schema_status`, `research_request_count` e `research_suggestion_count` diferentes. O contrato do receipt bloqueou sobrescrita por divergência, gerando `ValueError`. Esse não é um resultado de agente nem falha da resposta SIWC; é falha real de pós-processamento/recuperação.
- `active-run.json` está `blocked` com `blocker_code=ValueError`. `checkpoint.json` ainda termina em `triage_agent/call_started`, pois o runner falhou antes de registrar `succeeded`. O ledger mostra a tarefa de triagem `succeeded`, `attempts=1`, `external_request_started=1`. Não repetir esta tarefa nem a pesquisa Radar.
- Uso público: três tentativas de fonte registradas dentro do teto total 4; duas respostas HTTP 200 e uma fonte bloqueada antes da resposta. O orçamento deixa no máximo uma request pública de detalhe, sem retry, sem expansão de domínio e sem nova varredura. Franquia “100%” foi informada pela Direção; não é métrica lida pelo SIWC.
- Não ocorreram chamadas de investigador, editor, jornalistas, fact-checker ou revisor nesta tentativa; não há matéria completa nem prévia. Imagem preexistente é somente para prévia interna. A aprovação editorial humana segue pendente.

## Correções de recuperação — estado atualizado em 27/10/2026

O registro inicial de alterações locais sem validação foi supersedido. A correção está no commit local `0081cd4` (`fix: recover persisted triage artifacts idempotently`), preservado antes da sincronização em patch privado SHA-256 `52176563AC509F344075AAFC6C0A8727023BF000F9445F6201971AA98F418C9E`.

- `_task_output` reutiliza o receipt apontado pelo resultado/manifesto, confere o mesmo hash e os campos vinculantes e falha fechado se uma tarefa bem-sucedida não tiver receipt. Não tenta criar uma segunda versão com metadados de etapa diferentes.
- `resume_after_triage` valida primeiro resposta e receipt. A confirmação em checkpoint e `active-run.json` só é gravada depois de o ledger confirmar `succeeded`, tentativa 1, e o loader validar resposta, input, schema, DNA/ref e receipt.
- `_load_succeeded_role_output` reconstrói somente `structured-outputs/<task>.json`, do JSON bruto íntegro, quando o derivado está ausente; não reexecuta SIWC.
- SIWC e recuperação compartilham a mesma regra para aceitar o modelo solicitado ou sua variante versionada, desde que o receipt corresponda ao modelo efetivamente retornado.
- `ResearchService` recarrega claims depois do provider para reconhecer alegações criadas durante a busca; um teste focado reproduziu o defeito e passou após a correção.

Validação local: `test_eng_codex_011_runner` 16/16, `test_research_service` 11/11 e `test_agent_siwc_executor` 23/23; `py_compile` e `git diff --check` passaram. Isso valida os contratos de recuperação em testes offline, não a retomada operacional real. O commit está na branch local com os dois commits documentais remotos integrados por merge normal; enviar à PR #44 continua pendente antes do `resume`.

## Checklist obrigatório para a manhã

### Retomar sem perder nem repetir trabalho real

- [x] Ler este checklist, o checkpoint principal, a Issue #42 e confirmar ao vivo branch, upstream, status, HEAD e estado draft da PR #44.
- [x] Confirmar o limite comunicado pela Direção: 3/4 requests já usados e no máximo um request público restante. Isso não representa uma leitura de saldo Plus; não ampliar a autorização.
- [x] Abrir a raiz privada em modo somente leitura e conferir hashes de request/resposta/receipt da triagem e os três registros de fonte. Não repetir `/models`, os três requests Radar ou a triagem concluída.
- [x] Corrigir a reutilização do receipt no owner comum de artefatos/runner. Preservar o receipt válido imutável criado pelo executor; não gerar um segundo recibo divergente.
- [x] Validar em teste focado que `resume` pode adotar a resposta concluída (`attempts=1`) e reconstituir somente artefatos derivados ausentes. A adoção do ledger real continua pendente abaixo.
- [x] Rodar regressões focadas e registrar que são contratos offline, não prova operacional. Nenhuma chamada SIWC foi usada para depurar fixtures.
- [ ] Commitar e enviar a correção e o checkpoint à branch/PR #44 antes de retomar o fluxo real.

### Continuar a redação real

- [ ] Executar `resume` no mesmo Run ID, raiz, ledger e orçamento, com `gpt-6-luna`/`max`; a fila deve reutilizar a triagem persistida e não fazer scan de novo.
- [ ] Prosseguir com o investigador real usando apenas a evidência pública já recuperada. Encaminhar ao editor a pauta/persona selecionada a partir dos resultados reais, sem título ou matéria fixture.
- [ ] Prosseguir com jornalista/persona aprovado, arquivando texto integral, resposta original, cada versão e hashes em arquivos separados; contabilizar tokens e tempo por papel.
- [ ] Permitir, se o próprio jornalista solicitar e se a solicitação passar no contrato, no máximo uma pesquisa pública complementar em `api.github.com` dentro do único request restante. Sem request extra se não for necessário; sem retry em qualquer estado incerto.
- [ ] Executar checagem factual e revisão reais da versão exata. Se houver correção, retornar ao mesmo jornalista, arquivar nova versão e revalidar hashes; parar diante de pedido extra ou gate humano.
- [ ] Integrar a imagem existente somente na prévia interna. Não alegar licença editorial/comercial para publicação.
- [ ] Abrir a prévia local por HTTP no navegador, verificar visualmente texto e imagem e registrar evidência. Esta etapa ainda não foi feita.
- [ ] Atualizar relatório privado de consumo, checkpoint e PR com cada etapa, resultado real, hashes e bloqueio. Manter `published=false`, sem deploy, merge ou publicação.

## Problemas da linha editorial a resolver/fechar

| Etapa | Problema / risco identificado | Evidência/estado | Ação exigida |
|---|---|---|---|
| Radar → store | HTTP 200 podia terminar em pacote bloqueado por leitura de `radar_topics` omitida na allowlist; erros do provider ficavam genéricos. | Causa reconstruída nos registros ENG-011; correção de contrato e diagnóstico estruturado já na branch. | Confirmar no run real que dois sources ingeridos seguem para investigação; a terceira fonte bloqueada permanece observável e isolada. |
| Recuperação e recibos | Resposta e receipt válidos podiam ser perdidos/colidirem com gravação repetida quando processo falhava após a resposta. | Triagem real concluiu, mas runner bloqueou após o executor gravar receipt. Mudança para reuse está local e sem teste. | Recuperar a resposta existente por hash e retomar sem nova chamada; corrigir idempotência no owner compartilhado. |
| Catálogo/modelo | O catálogo não informa esforço; slug solicitado era ambíguo. | SIWC listou `gpt-6-luna`; chamada real retornou modelo e `max`. | Reutilizar evidência deste piloto; validar modelo/esforço em cada nova resposta, sem fallback. |
| Triagem e roteamento | Testes locais não garantiam que referências e decisão reais resolvessem contra itens atuais. | Chamada real retornou Proton/SDL em monitoramento; os dados não tinham changelog. | Consumir a resposta arquivada, resolver itens e seguir ao investigador, sem repetir triagem. |
| Pesquisa do jornalista | Pedido natural pode não virar request seguro ou retorno ao mesmo jornalista; resultado vazio não pode continuar. | Contratos e rota de correção têm testes locais; retorno real ainda não foi exercitado. | Usar o request real do jornalista, dentro do request público restante, e devolver o packet ao mesmo papel/story/persona; falhar fechado se não for útil. |
| Investigador/editor/jornalista | Respostas reais podem quebrar contratos de IDs, refs, DNA e projeção de dados internos. | Ainda não foram chamados nesta nova execução. | Percorrer os papéis funcionais reais com contexto tipado, DNA aprovado intacto e respostas arquivadas. |
| Fact-check/revisão/correção | Risco de revisar hash diferente, gate removido ou correções sem limite. | Contratos e correção limitada validados offline; revisor não concluiu na ENG-011. | Fazer checagem/revisão reais da versão certa; se pedir correção, nova checagem e revisão; aprovação humana não é automatizada. |
| Imagem/direitos | A imagem atual é original ImageGen para prévia interna; não prova direitos de mídia de terceiros nem autorização para publicação. | Hash existente registrado; prévia/browser ainda sem comprovação ENG-012. | Usar somente como internal preview e deixar uso/publicação pendente da Direção. |
| Preview/browser | HTML/preview determinístico não equivale a prévia aberta com texto e imagem. | U08 não concluída; run interrompeu antes de gerar preview. | Servir em HTTP local e comprovar a apresentação visual no navegador. |
| Multipauta | Pauta bloqueada pode interromper outras ou misturar orçamento/versões. | U09 continua sem prova operacional multipauta. | Homologar isolamento em execução separada segura após recuperar a reportagem; não chamar falha de teste sintético de prova real. |
| Alcance/factualidade | Releases metadata de três repos não sustentam por si uma investigação ampla; changelog não veio nos dados da triagem. | Radar observou Proton 11.0-2e e SDL 3.4.18, sem detalhe de changelog. | Não alegar impacto sem conteúdo/fonte consultada; usar a request complementar autorizada se necessária e dentro do limite. |

## Próximo passo concreto

Depois de confirmar live GitHub e o estado dos artefatos, terminar e validar o patch de reuso do receipt e recuperação de tarefa concluída. Então invocar **`resume` no mesmo Run ID** com `gpt-6-luna`/`max` e orçamento já registrado. Continuar com os agentes reais. Se a próxima etapa falhar depois de começar uma chamada externa, parar e reconciliar o ledger e os artefatos antes de qualquer tentativa subsequente.
