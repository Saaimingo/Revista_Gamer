# ENG-CODEX-012 — Checkpoint de arquitetura e contratos

**Atualizado:** 2026-10-26
**Issue:** [#42](https://github.com/Saaimingo/Revista_Gamer/issues/42)
**Documentação normativa:** [PR #43](https://github.com/Saaimingo/Revista_Gamer/pull/43), os três documentos foram lidos integralmente antes de qualquer mudança.
**Branch:** `codex/eng-codex-012-architecture-contracts`, derivada de `codex/eng-codex-011-live-factory@27c6703`.
**Status:** em andamento. U00 concluída; U01 diagnóstico concluído, implementação ainda não iniciada. Nenhuma chamada SIWC/Plus ou pesquisa pública nesta missão.

## Limites ativos

- ENG-011 usou as quatro requisições públicas autorizadas. Nenhuma pesquisa pública adicional está autorizada por esta missão; não repetir pesquisa nem resposta SIWC arquivada.
- Preservar todos os DNAs aprovados e os artefatos privados integrais; não copiar matéria integral ou resposta privada ao repositório.
- Sem API paga, publicação, merge ou deploy. Aprovação humana final continua pendente.
- ENG-012 U10 (piloto público real novo) permanece bloqueada até autorização específica posterior; continuar unidades offline e usar registros existentes.

## Feito nesta retomada

- Revalidado live branch/upstream/status/commits: branch ENG-011 limpa e sincronizada em `27c6703`; consultadas Issue #41 e comentário de handoff, que confirmam Issue aberta, limite 4/4 esgotado e ENG-011 não homologada.
- Lidos os documentos locais obrigatórios e os três contratos ENG-012 da PR #43 antes de alteração arquitetural.
- Auditado o `research-flow.json` e o `ledger/radar.sqlite3` privados em modo read-only. Resposta detalhada Proton: HTTP 200, 2.120 bytes, hash `8400dc8314939d00f3e0346df6ee15a3dbcc33b34773df48b0fd7cf719efc988`; documento Radar `3fa4064bb5d46d9e07a384806ca51735`; pacote `56610495-0ee9-4403-bbfd-70d61643ac64`, `blocked`, sem document/claim refs.
- **Causa raiz localizada sem nova consulta:** depois de persistir o documento e `statement_by` em `radar_document_entities`, `GitHubReleaseResearchProvider.search` consulta `RadarStore.get_row("radar_topics", "topic_id", topic_id)`. A allowlist de `get_row` omite essa tabela, embora `list_rows` a permita. A chamada lança `RadarStoreError` antes de criar tópico/claim. O estado parcial no SQLite confirma exatamente esse ponto da sequência. `ResearchService.execute` esconde a etapa/código sob resultado bloqueado e constraint genérica; a exceção original não foi registrada.
- Branch ENG-012 criada; nenhuma outra alteração foi feita ainda.
- Matriz módulo a módulo e por unidade está em `docs/engenharia/ENG-CODEX-012-MATRIZ-RASTREABILIDADE.md`.

## Validação e resultados

- Sem testes nesta unidade; U00 é inventário e leitura forense somente.
- Consultas SQLite feitas com URI `mode=ro`. Nenhum registro, fonte ou pacote foi modificado.
- Nenhuma chamada externa foi realizada durante a auditoria.

## Em andamento

- **U01:** corrigir a allowlist de `RadarStore.get_row` no owner do contrato, acrescentar regressão que exercite lookup e falha/retomada sem HTTP; desenhar recibo de etapa/error para que o `ResearchService` preserve falha técnica sanitizada em logs auditáveis sem expô-la ao texto editorial. Inspecionar transações e recuperação da sequência de ingestão antes de alterar o desenho.

## Próximo passo

1. Ler os testes existentes de `RadarStore` e `ResearchService` relativos a tabelas permitidas, provider, exceções e persistência.
2. Escrever regressão determinística que reproduza a falta de allowlist e documente o estado já persistido (cópia/fixture de contrato; nenhuma consulta de rede ou chamada de agente).
3. Corrigir o contrato no módulo proprietário; adicionar erro/receipt versionado ao resultado da pesquisa e cobertura para a causa observada.
4. Validar com testes focados e `git diff --check`; atualizar este checkpoint com comando e resultado antes do commit/push U01.

## Critérios ainda abertos

Contratos gerais U02, recuperação confiável U03, arquitetura Radar offline U04, handoffs U05–U07, preview real em navegador U08, isolamento multipauta U09 e nova homologação U10 (bloqueada por autorização de pesquisa esgotada). A missão não está concluída enquanto algum critério obrigatório permanecer aberto.
