# ENG-CODEX-007 — E02: contratos versionados e carregamento do regimento

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E02
- **Versão:** v0.1
- **Status:** validado localmente; aguarda revisão na PR de implementação
- **Data de atualização:** 2026-10-25 13:33 America/Sao_Paulo
- **Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28); pacote documental [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29); fila e despachante de [ENG-CODEX-006 / PR #26](https://github.com/Saaimingo/Revista_Gamer/pull/26), HEAD base `4de16640e67bd16c61468955e96e4ffa850d4cab`.
- **Aprovador:** direção, pela ordem contínua da Issue #28; revisão do código ainda pendente.

## Objetivo e resultado

E02 implementa contratos versionados para perfil funcional, tarefa, resultado e pesquisa. O carregador valida versão, hash, campos, schemas e limites antes de entregar a tarefa ao executor. O contrato funcional fica separado do `AgentProfile` técnico já usado pelo executor; a fila, o ledger SQLite e o `TaskDispatcher` continuam únicos. Referências de persona carregam somente identidade, versão e hash, sem copiar DNA para os perfis de função.

O carregamento monta seções confiáveis em ordem separada — projeção runtime do regimento v0.1, instruções do papel, instruções editoriais opcionais e DNA apenas para `persona_writer`. O brief/input e o `ResearchPacket` ficam em campos distintos, identificados como dados. Conteúdo de fonte não pode alterar papel, ferramentas, gates ou instruções.

## Arquivos e contratos

- `motor_editorial/agent_contracts.py`: schemas versionados `AgentRoleProfile`, `AgentTaskEnvelope`, `AgentResultEnvelope`, `ResearchRequest` e `ResearchPacket`; catálogo configurável JSON com resolução exata de `role_id` + versão + SHA-256; validador JSON Schema local de subconjunto explícito; limites de orçamento, ferramentas e gate humano; hash do input e do packet; barreira de dados não confiáveis; enqueue adapter para a fila existente.
- `motor_editorial/orchestration.py`: `AgentQueue.enqueue()` aceita `task_id` previamente criado (opcional, preservando o padrão atual); `TaskDispatcher` recebe `role_catalog` opcional e, quando configurado, valida role/task/input na fronteira de despacho e resultado antes de concluir a mesma tarefa. A execução tradicional sem catálogo continua compatível.
- `motor_editorial/tests/test_agent_contracts.py`: fixtures válidas e inválidas e integração da nova camada com `AgentQueue`/`TaskDispatcher` existentes.

Proteções cobertas incluem chaves desconhecidas, hash de instruções/perfil divergente, role/versão incompatíveis, hash do input alterado, tool ou escopo fora da concessão do papel, remoção de gate humano requerido, credenciais, hash de `ResearchPacket` incorreto, resultado malformado ou de outra tarefa, output hash divergente e conteúdo hostil mantido em dados não confiáveis.

## Evidência executada

Ambiente: Windows, `.venv`, CPython 3.11.9.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_contracts -v` → **12/12 OK**, 1,417 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **107/107 OK**, 69,575 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` → passou.

O teste de integração enfileira um envelope com identificador fixo no SQLite temporário já utilizado pelo `AgentQueue`, carrega o papel pelo catálogo no `TaskDispatcher`, valida o resultado e conclui essa tarefa. Casos incompatíveis ficam `blocked` antes do executor; resultado malformado não é aceito como conclusão.

## Limites e pendências

- A validação implementa um subconjunto explícito de JSON Schema, não o padrão completo. Perfis E03 devem manter-se nesse subconjunto ou a implementação deve ampliá-lo com testes.
- O hash do artefato é conferido entre `artifact_ref.sha256` e `output_hash`; E02 não abre arquivos referidos para recalcular bytes. Persistência/integração de artefatos será tratada nas unidades posteriores.
- O catálogo ainda não contém os seis papéis; registrá-los e testar suas entradas/saídas é E03. Nenhum DNA Carranca, Beto ou Nina foi copiado ou alterado.
- O regimento runtime é uma projeção compacta, versionada como 0.1 e referenciada ao documento da PR #29; não duplica integralmente o texto normativo.
- `SCHEMA_VERSION` do banco continua v5. Não houve acesso ao SQLite runtime, migração, SIWC/Plus real, API paga, consulta externa, deploy, publicação ou merge. `published=false`.

**Próxima unidade:** E03 — registrar seis papéis funcionais e dois opcionais desligados, com fixtures e testes iniciais, sem criar workers permanentes ou misturar `role_id` com persona.
