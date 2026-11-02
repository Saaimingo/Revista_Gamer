# Revista Back — Integração do Pesquisador de Inteligência Editorial (Coletor → Fábrica)

**Data:** 02/11/2026. **Origem:** comunicado do Agente de Coleta e Inteligência Editorial, encaminhado pela Direção ao Fundador e Codex. **Estado:** evolução de atribuições do Coletor aprovada pela Direção; novas instruções da automação comunicadas, integração ampliada NÃO homologada. **Responsáveis:** Coletor pela pesquisa, Redação pelo método, Codex pela ingestão e testes, Fundador pela conferência dos contratos.

## 1. Separação de responsabilidades

- **Coletor:** investiga notícias, rumores, anúncios, jogos, mods/comunidades e equipamentos; reúne cronologias, documentos, comparações, fontes, divergências, lacunas, resultados publicados de benchmarks e dossiês. **Não** escreve a reportagem final.
- **Jornalista:** interpreta o conjunto documental e produz narrativa fiel à persona e ao tipo de matéria; não precisa repetir mecanicamente toda pesquisa, mas pode buscar complemento relevante quando faltar fundamento.
- **Revisor:** aplica a D-019 e seu esclarecimento: exige atribuição, evidência proporcional à afirmação, atenção às contradições materiais e não bloqueia anúncio só porque não existem benchmarks independentes disponíveis.
- **Codex:** adapta **a ingestão existente**, sem criar esteira paralela, sem alterar indevidamente o esquema v1 e sem publicar o material do ensaio.

## 2. Capacidades relatadas e formato atual

O Coletor relata rodadas agendadas às 08h00 e 18h40 (America/Sao_Paulo), até três novas notícias por categoria (hardware, jogos, mods/comunidades), radar de até 12 pautas, histórico antirrepetição, investigação e dossiês. Esse limite de triagem **não limita o número de fontes úteis** de um dossiê, mas também não obriga buscar indiscriminadamente todos os testes/variáveis.

Destino de captura: `Saaimingo/Revista_Gamer:main:coletor/AAAA-MM-DD-HHMM.md`. O horário no nome é o slot agendado, não prova do instante de execução. O Markdown mantém seções tradicionais e `## Dados estruturados para a fábrica`, com bloco JSON `revista-back.coletor.v1`. Estrutura principal: `schema_version`, `run`, `dossiers`. Campos de dossiê existentes: `dossier_id`, `topic_id`, `event_id`, `headline`, `category`, `linked_news_urls`, `linked_radar_topic`, `editorial_relevance`, `context`, `sources`, `claims`, `timeline`, `contradictions`, `unknowns` e `next_watch`.

**Conferência direta pelo Fundador em 02/11:** o relatório `coletor/2026-11-02-0800.md` tem 8 itens de notícia (2 hardware, 3 jogos, 3 mods), radar com 12 pautas e 4 dossiês no único JSON v1 sintaticamente válido. Todos os 4 `linked_news_urls` têm correspondência textual exata com 1 item de notícia. Foram identificados enums `FATO_CONFIRMADO`, `RUMOR_NAO_CONFIRMADO`, `ALEGACAO_COMERCIAL`, `NAO_VERIFICADO` no arquivo; `CONTESTADO` é previsto pelo comunicado, mas NÃO foi observado nessa amostra. `sources[].source_type`: `PRIMARY`/`SECONDARY`; `sources[].access`: `FULL`/`PARTIAL`/`UNAVAILABLE`. **Defeito semântico comprovado:** fonte `nagoshi-s4`, campo `published_at="2026-03-2026"`, sintaxe JSON válida e data inválida.

## 3. Evidências de desempenho e comparativos, SEM obrigação laboratorial universal

O Coletor acrescentará em cada dossiê **quando a pauta justificar**, no Markdown, a subseção `Evidências de desempenho e comparativos`, reportando:
- fonte e autor do benchmark, identificando medições de fabricante, desenvolvedor, comunidade e veículos independentes;
- equipamentos comparados, resultados e condições **que estejam disponíveis e sejam relevantes para a conclusão**;
- divergências conhecidas, data e links originais; ou ausência de testes verificáveis **no escopo da busca**, quando for o caso.

Aplica-se a hardware, jogos/franquias/DLCs, mods/comunidades, monitores/TVs e periféricos conforme o assunto. Dados como FPS médio, 1% low, frametime, consumo, resolução, firmware ou drivers são **opcionais e pertinentes**, nunca uma lista de requisitos universais para toda notícia.

**Não exigir benchmark impossível ou reprodução própria da revista.** Uma afirmação de terceiro pode ser relatada com atribuição precisa. Para concluir que CPU A supera CPU B, não converter FPS entre computadores com GPUs substancialmente diferentes em prova isolada de superioridade da CPU. Essa é a diferença material; não investigar todas as combinações de overclock/BIOS hipotéticas.

No **JSON v1 atual**, preservar, sem novos campos obrigatórios: descrição comparativa em `context`, origem em `sources`, resultados/alegações em `claims` com `classification`, `source_ids` e `caveat`, diferenças em `contradictions`, ausências em `unknowns` e seguimento em `next_watch`. **Não** adicionar versão nova de forma unilateral. Os códigos de classificação no comunicado: `FATO_CONFIRMADO`, `RUMOR_NAO_CONFIRMADO`, `ALEGACAO_COMERCIAL`, `NAO_VERIFICADO`, `CONTESTADO`. `FATO_CONFIRMADO` significa que a **afirmação específica** é sustentada por fonte adequada, não que todo desempenho atribuído ao produto foi provado.

## 4. Verificação estática do leitor de fábrica

No PR draft privado `Saaimingo/revista-back-factory` HEAD `921496142e3b002a7a9996cd5bd17dbb8263d8fd`, módulo `automation/pipeline/src/collector.py`:
- Descobre `.md` sob o prefixo `coletor/`, com checagem Git blob e deduplicação de snapshots por caminho/blob; não restringe nome a um único slot.
- Captura entradas por títulos `### <n>. ...`, sem exigir a igualdade literal de `## Hardware para jogos`; cabeçalhos com `(N)` não são impedimento inerente. A captura e o radar devem continuar distintos pelos campos efetivamente presentes.
- `_parse_dossiers` reconhece JSON `revista-back.coletor.v1` e `linked_news_urls`, valida tipos básicos/URLs/IDs de fontes e integridade das referências de claims, mas **não valida** formato/calendário de `published_at` nem enum de `classification`, `source_type` ou `access`.
- O parsing mantém `provenance_class=collector_reported`; **presença no Coletor NÃO é prova de que o jornalista leu a fonte original**. Testes reais anteriores demonstram chegada de dossiê à projeção inicial, mas NÃO comprovam ainda todos os novos comparativos.

Esta é uma inspeção de código e do arquivo, **não** execução independente de teste completo com o relatório de 02/11.

## 5. Critérios mínimos da integração

1. Manter leitura de capturas antigas, múltiplos slots/dias e antirrepetição; preservar IDs/URLs de referência e não duplicar notícias já ingeridas.
2. Ingerir o relatório real de 02/11 em testes isolados, verificando número de candidatas, vínculos de dossiê, captura histórica e warnings.
3. Validar semântica de datas, URLs, enums, referências de IDs e campos opcionais, sem correção silenciosa, sem inutilizar toda a rodada por um `published_at` isolado inválido; definir aviso/quarentena apropriada e manter origem original intacta.
4. Provar offline quais evidências, `source_ids`, classes, ressalvas e lacunas realmente chegam ao jornalista e ao Revisor, sem equiparar fonte relatada à fonte realmente lida.
5. Investigar a pertinência da pesquisa complementar, especialmente os quatro documentos alheios à pauta identificados no ensaio TUXEDO; manter rastreabilidade e filtros de relevância **sem transformar a coleta em laboratório universal**.
6. Não impor tamanho de dossiê por limite arbitrário; controlar orçamentos de contexto e manter informação pertinente recuperável e rastreável. Aceitar perdas seletivas apenas explícitas e justificadas, nunca truncamentos silenciosos de evidência essencial.
7. Documentar módulos, fluxos, contratos, testes e procedimentos seguros de diagnóstico/recuperação conforme D-020.
8. Não considerar completa a evolução de benchmarks antes da primeira coleta real posterior à mudança e da validação compatível da fábrica.
9. Ensaios **com agentes reais** são objetivo futuro de homologação e exigirão autorização executiva específica; esta especificação só autoriza estudos e testes offline dentro das ordens técnicas já aprovadas.

**Status de implantação:** comunicado aprovado como DIREÇÃO; capacidades novas configuradas conforme relato, ainda NÃO comprovadas em execução completa nem homologadas na fábrica. **Sem publicação, alteração de DNA, merge, deploy ou nova inferência Luna por este contrato.**
