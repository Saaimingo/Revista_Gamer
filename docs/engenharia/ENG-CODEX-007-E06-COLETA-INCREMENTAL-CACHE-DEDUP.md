# ENG-CODEX-007 — E06: coleta incremental, cache e deduplicação conservadora

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E06
- **Versão:** v0.1
- **Status:** implementado e validado localmente; revisão da PR de implementação pendente
- **Data de atualização:** 2026-10-25
- **Autorização:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), execução contínua E01–E19
- **Dependências:** conectores E05 e armazenamento isolado E04; não ativa scheduler, fila de IA ou coleta real

## Resultado

`motor_editorial/radar_incremental.py` conecta `RadarConnectorService` ao `RadarStore` já existente. O caminho é determinístico: consulta ETag/Last-Modified, salva o estado atual do cache, registra cada tentativa de fetch e insere/atualiza documentos e eventos de observação. O serviço não inicia agentes, não chama LLM e não cria uma fila ou dispatcher adicional. `requires_triage` é apenas um resultado para unidades posteriores; E10 decide como encaminhar novidades.

O cache usa `(source_id, request_url)` como chave, sem identidade de jornalista ou perfil de consumidor. Perfis separados que consultam a mesma fonte e URL reutilizam os mesmos validadores. Respostas `304` preservam a representação atual, registram `FetchEvent` e não produzem documento duplicado nem indicação de triagem.

## Hashes, alterações e retenção

- O parser RSS/Atom calcula SHA-256 dos campos extraídos de título e conteúdo disponível no feed e do corpo completo do feed recebido. Para texto de corpo, também calcula hashes de segmentos normalizados; nenhum corpo, descrição ou trecho do artigo é incluído em `FetchResult` ou persistido.
- O documento atual mantém os hashes, título, autoria pública, origem declarada, status e hashes de segmentos. `ObservationEvent` registra `first_seen`, `title_changed`, `body_changed` ou `repeated`, com hashes anteriores/atuais e diff sem texto do corpo. Eventos permanecem append-only.
- Um mesmo `source_id` + URL canônica mantém um único `document_id`. Mudança de título ou de conteúdo normalizado produz evento novo e indica triagem; uma observação equivalente é `repeated` e não pede triagem.
- Para HTML e API JSON, os conectores mantêm a política metadata-only do E05; se não houver campo de corpo permitido, o fingerprint usa somente os metadados disponíveis. O ensaio E06 exercita RSS/Atom em fixtures.

## URLs e grupos de republicação

A normalização de URL reduz host a minúsculas, usa `/` para caminho vazio e remove fragmento. Preserva query string inteira, incluindo nomes, valores, duplicatas e ordem: o sistema não supõe que `utm_*` ou outros parâmetros sejam dispensáveis. Parâmetros de credencial são recusados.

Um documento só entra em grupo de republicação com evidência explícita: URL de origem declarada em RSS/Atom, ou corpo idêntico de pelo menos 80 caracteres com título e autoria normalizados iguais. O grupo mantém documentos e bylines separados. Autores diferentes não são mesclados por título ou semelhança; com origem declarada, podem pertencer ao mesmo grupo de cópia, sem fundir seus registros.

## Banco e migração

O schema isolado do Radar avançou de v1 para v2 por migração aditiva: hashes de corpo/segmentos e URL de origem no documento; `radar_fetch_cache`; histórico append-only `radar_fetch_events`; e grupos/membros de republicação com evidência. A migração v1→v2 e a criação v0→v1→v2 foram exercitadas apenas em arquivos SQLite temporários. `motor_editorial.db.SCHEMA_VERSION` permanece 5, e o caminho runtime continua recusado pelo `RadarStore`.

## Arquivos entregues

- `motor_editorial/radar_incremental.py` — coleta incremental determinística, cache condicional, normalização segura, eventos e grupos conservadores.
- `motor_editorial/radar_connectors.py` — fingerprints de payload/campos RSS e exposição de hashes sem corpo bruto.
- `motor_editorial/radar_store.py` — schema v2, migração, cache, fetch history e upsert atômico de observações.
- `motor_editorial/tests/test_radar_incremental.py` — fixtures que exercitam URLs com parâmetros, 200→304, edição, repetição e cópias/autorias.
- `motor_editorial/tests/test_radar_connectors.py` e `motor_editorial/tests/test_radar_store.py` — regressões de hash, migração v1→v2 e append-only.
- `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md` e `docs/engenharia/README.md` — estado e índice.

## Validação executada

Ambiente: CPython 3.11.9 em `.venv`, Windows.

- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental -q` → **27/27 OK**, 6,216 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **142/142 OK**, 161,422 s na execução integral final.
- `git diff --check` e `git diff --cached --check` → sem erro antes do commit de código.

Uma execução integral intermediária apresentou falha transitória no teste preexistente `test_multipauta_concurrent_and_successive_calls_are_serialized_and_idempotent` (apenas um dos dois resultados antes do timeout e pasta temporária ocupada). O teste isolado passou **1/1** em 13,961 s; a execução integral seguinte passou **142/142**. A causa da ocorrência intermediária não foi estabelecida; não houve alteração no workflow nem no teste de concorrência.

Todos os transportes e DNS foram simulados; não houve consulta a fonte pública, LLM, SIWC/Plus, API paga, autenticação, banco runtime, scheduler, publicação, deploy ou merge. `published=false`.

## Commit e próximo passo

- Código e testes: `eddc0e904b0a220f24651209a4e4da2d27153423` (`feat: add incremental Radar collection and dedupe`), enviado à branch de implementação.
- PR draft [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30) permanece aberta, sem merge, sobre a base `4de16640e67bd16c61468955e96e4ffa850d4cab`.
- Próxima unidade: **E07 — cadastro de pessoas, projetos, aliases, entrevistas e idiomas**, limitada a informação profissional pública e fixtures locais nesta fase.
