# ENG-CODEX-007 — E07: pessoas, projetos, aliases, entrevistas e idiomas

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E07
- **Versão:** v0.1
- **Status:** implementação concluída; validação integral em execução
- **Data:** 2026-10-25
- **Autorização:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), sequência contínua E01–E19
- **Dependências:** Radar isolado E04, conectores públicos com política E05 e coleta incremental E06

## Resultado

O `RadarStore` registra pessoas e projetos públicos com documento-fonte permitido, aliases por idioma e contexto profissional para desambiguar homônimos. Registros de pessoa não aceitam campos livres em `metadata`; contexto profissional, alias e título de cargo recusam e-mail e telefone. Etiquetas de idioma compatíveis com o perfil BCP 47 simplificado são armazenadas com capitalização canônica.

`radar_entity_roles` preserva cada atribuição como evidência append-only, ligada à pessoa, cargo, organização/projeto, intervalo temporal, documento e tipo de evidência. Citação/byline de entrevista exige uma entrevista registrada para a mesma pessoa e documento. Um press release exige fonte oficial e vínculo explícito `press_release_from` com a organização emissora. Os registros mantêm contextos distintos e permitem cargos anteriores e atuais sem sobrescrever o histórico.

`radar_interviews` registra apenas a pessoa entrevistada, documento original e idioma. `radar_interview_variants` aponta para original ou variante anterior e classifica tradução, transcrição ou republicação. Nenhum texto, citação, áudio ou transcrição de entrevista é copiado ao Radar.

## Migração isolada

O schema próprio do Radar avançou de v2 para v3. A migração reconstrói apenas `radar_entities`, preserva os IDs, aliases e relações existentes, acrescenta documento/contexto de identidade e troca a chave única para permitir homônimos somente com contexto profissional distinto. Tabelas de cargos, entrevistas e variantes ganham índices e bloqueios append-only. A verificação de FKs ocorre antes do commit: uma referência órfã de fixture faz rollback completo e conserva `user_version=2`.

O `motor_editorial.db.SCHEMA_VERSION` continua 5. O SQLite runtime não foi aberto nem migrado; todos os arquivos usados nos testes são temporários.

## Arquivos entregues

- `motor_editorial/radar_store.py` — schema v3, migração e operações de identidade, cargos, entrevistas e variantes.
- `motor_editorial/tests/test_radar_entities.py` — aliases japoneses/romanizados, projeto multilíngue, homônimos, privacidade, histórico profissional, proveniência e tradução.
- `motor_editorial/tests/test_radar_store.py` — migração v1/v2→v3, preservação de links legados, rejeição do SQLite runtime e rollback de FKs órfãs.
- `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md` e `docs/engenharia/README.md` — andamento e índice da unidade.

## Validação

Ambiente: CPython 3.11.9, `.venv`, Windows; fixtures e caminhos temporários; domínios `.invalid` sem consulta de rede.

- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -p 'test_radar*.py' -v` → **32/32 OK**, 4,563 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` → exit 0; Git emitiu apenas avisos de conversão LF→CRLF para arquivos editados.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → execução integral final pendente.

Sem consulta a fontes públicas, inferência, SIWC/Plus, API paga, credenciais, banco runtime, scheduler, publicação, deploy ou merge; `published=false`.

## Commit e próximo passo

O commit e push serão registrados após a conclusão da suíte integral e sincronização do relatório/checkpoint. PR draft [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30) permanece aberta e sem merge. Próxima unidade após validação: **E08 — ledger de alegações, rumores, origem e evolução/contradições**.
