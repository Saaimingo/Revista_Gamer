# Análise provisória do Fundador — Despacho por eventos e orquestração editorial
**Data:** 2026-10-17  
**Status:** PROVISÓRIO — estudo arquitetural, NÃO é especificação aprovada nem ordem de implementação.  
**Área:** Engenharia / Motor Editorial.  
**Origem:** discussão do diretor com o chat fundador sobre o n8n e o acionamento automático dos agentes.

## 1. Problema apresentado pelo diretor
O sistema precisa funcionar como fábrica editorial: uma coleta agendada (hipótese: três vezes ao dia em horários configuráveis) cria insumos; ao completar cada etapa, um mecanismo central deve acionar a função adequada (triagem, apuração, cronista/redator, revisor, correção etc.), sem operador chamar cada IA manualmente. O diretor usa o n8n como referência de orquestração e quer evitar reinventar mecanismos consolidados; **não solicitou instalar o n8n nem reconstruir o Motor existente**.

Esse mecanismo é requisito funcional para a operação futura, mas NÃO se confunde com a máquina de estados já implementada.

## 2. Base verificada no projeto (2026-10-17)
- v0.1 na `main`: executor por etapas simuladas, SQLite, máquina de estados, auditoria, retry e retomada, bloqueios, aprovação humana interna.
- v0.2 no PR #6 (aberto, não integrado no momento da consulta): proposta/implementação de múltiplas pautas e edição; ainda com adaptadores determinísticos simulados.
- O contrato `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md` PROÍBE integrar LLMs, notícias externas, agendamento, agentes e filas operacionais de produção nesta etapa.
- Portanto **não existe hoje, validado, um mecanismo operacional que acorde agentes de IA de verdade nem uma agenda de coleta três vezes ao dia**. Os contratos prevêem futura substituição de adaptadores e evolução de orquestração, mas falta especificação operacional específica para esse acionamento.
- Preservar exigência de aprovação humana, versões atuais, fontes, evidências e direitos; nenhuma publicação/ativação real está autorizada.

## 3. Estudo de referência — como o n8n resolve conceitos equivalentes
Pesquisa na documentação oficial do n8n:
- **Schedule Trigger:** dispara workflows em horários/intervalos configuráveis e com timezone; contempla política de execução perdida conforme configuração: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/
- **Execute Sub-workflow:** chama fluxos menores, passando entradas; pode aguardar conclusão ou seguir sem aguardar: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.executeworkflow/
- **Wait:** persiste execução pausada em banco e retoma quando condição ocorre, incluindo evento externo: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/
- **Error workflows:** capturam falhas e iniciam tratamento/alerta: https://docs.n8n.io/flow-logic/error-handling/
- **Queue mode:** instância principal recebe triggers, broker Redis enfileira identificadores de execução e workers consomem/registram resultados; para maior escala; usa componentes extras e não é automaticamente adequado ao nosso protótipo SQLite de processo único: https://docs.n8n.io/hosting/scaling/queue-mode/

**Distinção crítica:** estudar/adotar conceitos comprovados não equivale a copiar código ou criar um clone do n8n. Avaliar explicitamente usar ferramenta pronta versus componente local mínimo, com critérios de custo, confiabilidade, manutenção e direitos/licenciamento.

## 4. Proposta de arquitetura enxuta para debate, não implementação
1. **Agendador / entrada de eventos:** relógio para coletas autorizadas e eventos internos `pauta_criada`, `apuracao_concluida`, `revisao_reprovada`, `correcao_entregue`, `revisao_aprovada`, `direitos_pendentes` etc.; registrar hora prevista e fuso.
2. **Caixa de tarefas persistente:** cada trabalho autorizado contém ID único, tipo, pauta/edição, versão, prioridade, contexto referenciado, requisitos, status, tentativas, horários e chave de idempotência; em um processo local, SQLite pode servir de fila durável inicial, desde que retirada/claim sejam atômicos.
3. **Despachante:** consulta tarefas elegíveis e dependências; reserva tarefa com bloqueio/lease; seleciona adaptador de execução autorizado para a função, sem confundir persona de cronista com processo.
4. **Executor/adaptadores:** invoca modelo/serviço APENAS quando houver autorização, credencial, limite e conector compatível; recebe saída estruturada versionada; não concede a si mesmo aprovação de etapa.
5. **Motor de estados:** valida resposta, fontes, revisão vigente, direitos e transição; persiste resultado e próximo evento/transição de forma consistente; tarefa e outbox/evento devem sobreviver a quedas sem perder acionamento nem duplicar operação editorial.
6. **Falhas:** timeout, retentativas finitas, atraso progressivo, recuperação de reserva expirada, bloqueio por intervenção, alarmes/visibilidade no painel; tarefa com erro não paralisa outras pautas.
7. **Gates humanos:** reprovada volta à correção com problemas identificados; ao corrigir, cria nova versão e exige NOVA revisão; publicação e aprovação interna humana continuam separadas de automação.
8. **Custos e limites:** limite por período, custo por chamada/tarefa, sem assumir que ChatGPT Plus fornece acesso programático; métricas e circuito de pausa antes de exceder cotas.
9. **Operação:** evento já persistido pode despertar dispatcher por notificação local ou ser verificado periodicamente; não é necessário um processo LLM continuamente ativo. Definir comportamento com máquina desligada, relógio atrasado e execução perdida.

## 5. Testes de aceite futuros sugeridos
- Três horários de coleta configuráveis disparam jobs distintos no fuso selecionado; horários perdidos têm regra explícita.
- Um evento de conclusão de pesquisa gera, de modo atômico e idempotente, apenas a tarefa seguinte; dois despachantes simultâneos não processam o mesmo job sem controle.
- Duas pautas independentes avançam sem uma pauta bloqueada travar o lote.
- Revisor devolve ao redator e registra justificativa; revisão vigente não aprovada nunca avança nem volta ao estado aprovado por recomposição.
- Reiniciar processo em qualquer etapa não apaga nem executa duas vezes efeitos confirmados.
- Credencial ausente, cota excedida, modelo indisponível, mídia revogada e tentativa excedida bloqueiam ou adiam corretamente; não aprovam nem publicam.
- Execuções/trilhas são rastreáveis no painel com responsável, horário, entradas/saídas, versões, custos e incidentes.
- Nenhum disparo real começa sem autorização específica do diretor para a etapa e para conexões externas.

## 6. Fronteiras e encaminhamento
- **Agora:** concluir, revisar e integrar o PR #6 somente após corrigir o bloqueio editorial identificado; este documento não altera o PR nem ordena o Codex.
- **Depois da v0.2:** discutir arquitetura e fazer avaliação comparativa curta entre (a) n8n como orquestrador externo, (b) despacho local com SQLite/agendador Python e (c) outra ferramenta madura leve se houver justificativa. Decidir por evidências, não por moda.
- **Só com aprovação posterior:** converter proposta em especificação e testes de engenharia; definir a menor prova de conceito. Não ativar coleta real, LLMs, serviço pago, publicação, nem denominar automaticamente v0.3.
- **Decisão pendente:** confirmar arquitetura exata, agendamento, política de coletas perdidas, executor de IA e limites.

**Síntese do debate:** o diretor considera o acionamento automático encadeado uma capacidade essencial para a fábrica editorial. O fundador concorda com a necessidade e recomenda reutilizar o núcleo existente, estudando a mecânica do n8n como referência antes de escolher implementações.