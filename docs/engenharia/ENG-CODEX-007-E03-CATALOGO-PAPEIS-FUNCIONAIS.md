# ENG-CODEX-007 — E03: catálogo de papéis funcionais

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E03
- **Versão:** v0.1
- **Status:** validado localmente; aguarda revisão na PR de implementação
- **Data de atualização:** 2026-10-25 13:42 America/Sao_Paulo
- **Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28); contratos E02 em [ENG-CODEX-007-E02](ENG-CODEX-007-E02-CONTRATOS-VERSIONADOS.md); especificação de funções na [PR #29](https://github.com/Saaimingo/Revista_Gamer/pull/29).
- **Aprovador:** direção, pela ordem contínua da Issue #28; revisão do código ainda pendente.

## Resultado

O catálogo versionado contém os seis papéis frequentes habilitados para uso contratual e os dois papéis opcionais registrados, porém desligados. Cada perfil define instruções com SHA-256, schema de entrada/saída, ferramentas e escopos, dados/fontes acessíveis, limites, handoffs, proibições, gate humano, política de falhas, rubrica e fixture de avaliação.

| `role_id` | Função | Estado no catálogo |
| --- | --- | --- |
| `triage_analyst` | Triagem de novidades e propostas de pauta | Habilitado |
| `evidence_investigator` | Dossiê de evidências e lacunas | Habilitado |
| `assignment_editor` | Proposta de ângulo e estrutura | Habilitado |
| `persona_writer` | Redação usando referência externa de persona | Habilitado |
| `fact_checker` | Checagem independente da revisão/hash vigente | Habilitado |
| `editorial_reviewer` | Revisão editorial sem autorização de publicação | Habilitado |
| `media_researcher` | Sugestões de mídia a partir de acervo autorizado | Desligado; opcional |
| `layout_planner` | Proposta de composição para validador/renderizador determinístico | Desligado; opcional |

Os dois perfis opcionais podem ser inspecionados explicitamente (`allow_disabled=True`), mas a resolução usada pela tarefa e pelo despachante recusa perfis desligados. Ferramentas de pesquisa expostas aos papéis são somente solicitações formais ao Motor; os perfis não recebem shell nem acesso HTTP direto. `persona_writer` exige `persona_id`, versão e hash separados. Nenhum DNA, conteúdo ou imagem de Carranca, Beto ou Nina foi copiado, alterado ou usado como fixture.

## Arquivos entregues

- `motor_editorial/agent_roles.json`: catálogo local configurável, com seis papéis ativos e a lista explícita `disabled_role_ids` para os opcionais.
- `motor_editorial/agent_contracts.py`: loader do catálogo embarcado, lista de papéis ativos e bloqueio de despacho para papel desligado.
- `motor_editorial/tests/fixtures/agent_role_fixtures_v1.json`: exemplos sintéticos versionados de entrada/saída para os oito papéis.
- `motor_editorial/tests/test_agent_role_catalog.py`: testes de catálogo, hash/schema, fixtures, ferramentas e escopos, bloqueio dos opcionais e separação de referência de persona.
- `docs/engenharia/README.md`: índice atualizado para ENG-CODEX-007 e checkpoint.

## Evidência executada

Ambiente: Windows, `.venv`, CPython 3.11.9.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_agent_contracts -v` → **20/20 OK**, 1,159 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **115/115 OK**, 65,036 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- Carregamento do catálogo embarcado → 8 perfis; 6 habilitados e 2 desligados.
- `git diff --check` → passou.

São testes de contrato e fixture local. Não houve chamada a LLM, SIWC/Plus, API paga, fonte externa ou uso de mídia real. `published=false`.

## Limites e próxima unidade

“Habilitado” significa que o perfil pode ser aceito pelo catálogo e usado por uma tarefa autorizada; não significa que há sessão LLM persistente, executor de produção ou papel validado por inferência real. Os resultados das fixtures são sintéticos e não avaliam a qualidade de um modelo.

**Próxima unidade:** E04 — schema isolado do Radar e armazenamento SQLite de fontes, documentos, observações, entidades, alegações, pesquisas e carteira; o banco runtime existente continuará fora do escopo.
