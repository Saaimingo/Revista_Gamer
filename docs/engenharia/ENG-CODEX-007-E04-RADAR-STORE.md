# ENG-CODEX-007 — E04: armazenamento isolado do Radar

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E04
- **Versão:** v0.1
- **Status:** implementado e validado localmente; revisão da PR de implementação pendente
- **Data de atualização:** 2026-10-25 13:55 America/Sao_Paulo
- **Autorização:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), execução contínua E01–E19
- **Dependências:** contratos `ResearchRequest`/`ResearchPacket` e contratos de agentes da E02; papéis E03; branch de implementação baseada na ponta da PR #26

## Resultado

Foi adicionado `motor_editorial/radar_store.py`, um armazenamento SQLite do Radar com arquivo de destino explícito, versão própria (`PRAGMA user_version=1`) e tabelas no namespace `radar_*`. A resolução do caminho bloqueia o `motor_editorial/runtime/motor.sqlite3`. A inicialização valida a estrutura v1 e recusa misturar tabelas de outra aplicação. A fila de tarefas continua no `AgentQueue`/`TaskDispatcher` existente; o Radar não cria um segundo ledger de execução.

O schema guarda fontes, documentos observados, eventos de observação, entidades e aliases, tópicos e relações, alegações e relações com fontes, eventos da alegação, solicitações e pacotes de pesquisa, candidatos de pauta e eventos de mudança de faixa. As relações usam chaves estrangeiras e `foreign_key_check` passou nas fixtures.

### Regras de integridade aplicadas

- Fonte inicia com política de acesso `unreviewed` e direitos `unknown`; URLs precisam ser HTTPS, sem usuário/senha e sem parâmetros de credencial conhecidos.
- Documento guarda metadados, hashes SHA-256, links de referência e no máximo um resumo curto. Texto de resumo só é aceito com `short_excerpt` e direitos marcados como `authorized`; por padrão, a retenção é `metadata_only`.
- Eventos de observação preservam hash anterior/atual, tipo, horário e diff JSON. Atualização e exclusão de eventos são bloqueadas por triggers append-only.
- `epistemic_status` da alegação descreve a natureza da atribuição (incluindo `attributed_rumor`). Estado posterior do conteúdo fica em evento separado (`confirmed`, `partially_confirmed`, `contradicted`, `withdrawn`); registrar confirmação não reescreve a classificação epistemológica nem o histórico.
- Relações de origem guardam `origin_group_id`. Dez republicações podem apontar para um grupo de origem, sem serem contadas automaticamente como dez origens independentes.
- Solicitações e pacotes reutilizam os contratos versionados da E02, preservam versão/hash e validam idempotência da solicitação. O banco não executa a pesquisa.
- Candidatos da carteira usam as faixas `principal`, `reserva`, `monitoramento` e `descartada`; eventos de faixa são append-only. A política de quantidade dinâmica 10+10 permanece na E12.

### Migração e recuperação

A migração v0→v1 coberta aqui importa somente o fixture isolado `radar_sources_v0`, aplica defaults conservadores, valida os registros e roda dentro de uma transação SQLite. Tabelas alheias ao fixture são recusadas. O helper de backup usa a API de backup do SQLite e restaura para um arquivo novo. Os testes cobrem backup antes da migração, restauração da cópia original e rollback transacional quando a fixture tem URL inválida. Nenhum banco de runtime foi migrado ou aberto.

## Arquivos entregues

- `motor_editorial/radar_store.py` — schema, validação, migração fixture, backup/restauração e operações de leitura/gravação.
- `motor_editorial/tests/test_radar_store.py` — nove testes offline com bancos temporários.
- `docs/engenharia/ENG-CODEX-007-E04-RADAR-STORE.md` — este relatório.
- `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md` — evidências persistentes e retomada.
- `docs/engenharia/README.md` — índice e status da sequência.

## Validação executada

Ambiente: CPython 3.11.9 do `.venv` do repositório, Windows. Todos os bancos de teste foram criados em diretórios temporários.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_store -v` → **9/9 OK**, 1,686 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **124/124 OK**, 73,891 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` e `git diff --cached --check` → sem erro após remover linha vazia final.
- Verificados schema versionado separado, bloqueio do caminho runtime antes de abrir, FK, migração v0 isolada, recusa de tabelas externas, backup/restauração, rollback, hashes/diffs append-only, status de rumor e evolução, grupos de origem, idempotência e hash de pesquisa, carteira e histórico de faixa.
- `motor_editorial.db.SCHEMA_VERSION` continua `5`; `RADAR_SCHEMA_VERSION=1` no arquivo separado.

## Limites e riscos conhecidos

Esta unidade não consulta URLs, não coleta feeds, não agenda tarefas e não chama modelo, SIWC/Plus ou API paga. Conectores públicos e limites de rede pertencem à E05; coleta incremental à E06; registro rico de produtores/idiomas à E07; política de origem/evolução às E08; carteira quantitativa à E12. A migração validada é uma fixture sintética, não uma autorização nem um plano para migrar o SQLite runtime. Direitos e acesso começam conservadores e precisam de evidência antes de retenção editorial.

Não houve publicação, deploy, merge ou alteração de DNA. `published=false`.

## Commit e próximo passo

- Implementação e testes: `509a882` (`feat: add isolated ENG-CODEX-007 Radar store`), enviado à branch `codex/eng-codex-007-factory-radar`.
- PR draft de implementação: [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), sem merge.
- Próxima unidade: **E05 — conectores públicos permitidos e guardas de segurança**, sem habilitar coleta proibida, serviço pago ou operação contínua.
