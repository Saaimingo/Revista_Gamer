# ENG-CODEX-007 — E11: ResearchService sob demanda

**Setor responsável:** Engenharia e Codex
**Identificador:** ENG-CODEX-007-E11
**Versão:** v0.1
**Status:** implementado e validado localmente
**Data:** 2026-10-25
**Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), ordem E01–E19 da direção na PR [#29](https://github.com/Saaimingo/Revista_Gamer/pull/29), contratos E02, papéis E03 e Radar E04–E10.

## Critério e limite da unidade

E11 entrega uma pesquisa sob demanda compartilhada entre o Radar geral e as funções hardware, jogos e criadores. Cada pedido escolhe um perfil versionado pelo assunto. Carranca, Beto e Nina podem encaminhar perguntas diferentes ao mesmo índice; não há scraper dedicado por jornalista. A resposta fica vinculada ao `story_id` e à revisão exata da pauta.

O serviço consulta primeiro o Radar local. Uma busca externa somente pode ser tentada por um adaptador explicitamente injetado, com o escopo `read:registered_public_sources`, perfil compatível, fontes restantes no orçamento e evidência ainda pendente. Nenhum adaptador externo é configurado por padrão nesta unidade. O acoplamento ao `TaskDispatcher` permanece na E13; coleta de fontes públicas permanece na E16.

## Implementação

- `ResearchService` usa o `RadarStore` compartilhado para pesquisar documentos, nomes e aliases de entidades, tópicos, vínculos de entidades/documentos e alegações com histórico. O ranqueamento é determinístico e usa a pergunta, consultas, configuração/versão informada e foco do perfil. Filtros de idioma, fonte, domínio, período, exclusões e evidências já conhecidas são aplicados ao mesmo índice.
- Quatro perfis registrados — `radar.general.v1`, `research.hardware.v1`, `research.games.v1` e `research.creators.v1` — declaram versão, foco e escopos. O perfil não é inferido da persona: uma mesma persona pode pedir qualquer eixo compatível com a pauta.
- `ResearchRequest` v1.1 adiciona `story_revision_id`; a versão 1.0 continua parseável para compatibilidade, mas E11 a bloqueia até o vínculo de revisão existir. O resultado da execução devolve story/revisão e o packet fica ligado ao pedido persistido.
- O Radar avança do schema v5 para v6 por migração aditiva: acrescenta `story_revision_id` nullable aos pedidos anteriores e cria índice por story, revisão e data. A fixture v5 preserva o pedido legado e seu JSON sem revisão.
- `ResearchPacket` persiste versão e hash, documento/alegação, linhagem de fontes, trecho curto, última mudança material registrada, evidência faltante, restrições e `retry_at`. Repetir o mesmo pedido reaproveita o packet; pedido rate-limited só é refeito quando o horário de retry chega.
- Título, resumo ou similaridade textual não provam uma categoria de evidência. `found` só é concedido quando as categorias pedidas aparecem como estados epistemológicos em alegações do ledger ligadas a fontes permitidas. Sem esse vínculo, o serviço retorna `partial` ou `not_found`; política/escopo/orçamento inválido retorna `blocked`.
- Um adaptador precisa devolver IDs já persistidos no Radar, nunca texto livre. O serviço valida fonte/documento, escopo, idioma, período, domínio, exclusões e relação da alegação com a pergunta; também aplica limites de chamadas, bytes, fontes e duração. Saída excedente ou referência rejeitada é descartada. Dados locais já válidos continuam identificados como `partial` quando a extensão externa é bloqueada.

## Evidências de validação

Ambiente: Windows, CPython 3.11.9 (`.venv`), SQLite temporário e provedor falso/injetado nas fixtures.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_research_service -q` — **9/9 OK**.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_research_service motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_radar_store -q` — **38/38 OK**, 14,433 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **176/176 OK**, 128,493 s, execução serial.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — exit 0.
- `git diff --check` e `git diff --cached --check` — exit 0.
- As fixtures cobrem os três eixos, reuso de um único índice, troca de perfil pela pergunta sem vínculo rígido à persona, documentos/tópicos/aliases/alegações/histórico, revisão de pauta, migração Radar v5→v6, packet idempotente, cache/retry, `not_found`, bloqueio por perfil/escopo/data inválidos, referências sem proveniência e os quatro limites do pedido.

Código e testes: commit `3ed30ca` (`feat: add shared Radar research service`), enviado à branch `codex/eng-codex-007-factory-radar`. Testes exclusivamente locais: nenhum site, API, LLM, SIWC/Plus, chave paga ou banco runtime foi usado. O provedor foi uma fixture sem rede. Não houve despacho de agentes, publicação, deploy, merge ou alteração de DNAs. `published=false`.

## Pendências e continuação

E11 não coleta fontes novas e não inicia tarefas no dispatcher. Antes da E13, os executores continuam desacoplados. A coleta externa permitida permanece para E16.

Para a E17, a instrução atual do usuário exclui SIWC/Plus real. O usuário informou que a tela mostrava 10% da franquia disponível e retorno a 100% às 18:12; não houve consumo de franquia nesta unidade. O piloto real E17 deve ficar registrado como `BLOCKED` neste escopo, com validações offline independentes onde couber.

Próxima unidade autorizada: **E12 — carteira dinâmica de 10 pautas principais e 10 reservas**, sem gerar vinte reportagens completas.
