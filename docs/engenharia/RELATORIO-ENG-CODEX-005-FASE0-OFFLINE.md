# ENG-CODEX-005 — Fase 0 offline: acervo e diagramador

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-005-FASE0-OFFLINE
- **Versão:** v0.2
- **Status:** em_revisao, [PR #18 aberta para revisão](https://github.com/Saaimingo/Revista_Gamer/pull/18)
- **Atualização:** 2026-10-24
- **Aprovador da missão:** Diretor, que autorizou a Fase 0 na [Issue #17](https://github.com/Saaimingo/Revista_Gamer/issues/17). A aprovação desta implementação continua pendente de revisão.
- **Dependências:** [arquitetura de agentes, acervo visual e composição](ARQUITETURA-AGENTES-ACERVO-VISUAL-E-COMPOSICAO-2026-10-20.md); [Issue #17](https://github.com/Saaimingo/Revista_Gamer/issues/17); [Issue #15](https://github.com/Saaimingo/Revista_Gamer/issues/15); [PR #8](https://github.com/Saaimingo/Revista_Gamer/pull/8); [PR #10](https://github.com/Saaimingo/Revista_Gamer/pull/10).

## Objetivo e exclusões

Implementar uma demonstração offline rastreável que encaixa o diagramador na linha já existente do Motor, recupera três referências funcionais sintéticas por cenário, cria um plano versionado e aceita ou bloqueia a composição por verificações determinísticas.

A entrega não integra o leitor v0.3, não finaliza a identidade visual, não usa as 16 imagens do fluxo separado de mocks, não carrega scans, não chama SIWC, modelos, APIs, serviços ou rede e não publica conteúdo. A composição final da identidade dos mocks com o leitor continua na Issue #15.

## Auditoria de encaixes existentes

A auditoria foi feita sobre main em b44daf1 (D-018), sem usar os heads das PRs como se já estivessem integrados.

~~~mermaid
flowchart LR
  subgraph MAIN["main — Motor v0.2 integrado"]
    A["run_multipauta_demo"] --> B["_execute_step: ingest e triage"]
    B --> C["_run_multipauta_story"]
    C --> D["research → draft → review"]
    D --> E["correction → review v2, se necessário"]
    E --> F["media-rights"]
    F --> G["_compose_multipauta_edition"]
    G --> H["prévia interna → aprovação humana"]
  end
  subgraph PR8["PR #8 — ainda fora da main"]
    Q["AgentQueue"] --> R["TaskDispatcher.dispatch_one"]
    R --> S["Executor substituível"]
    T["scheduler opcional"] --> R
  end
  subgraph PR10["PR #10 — empilhada sobre PR #8"]
    U["pipeline editorial"] --> V["TaskDispatcher de PR #8"]
    V --> W["SIWCEditorialExecutor"]
  end
  subgraph FASE0["Issue #17 — esta entrega"]
    X["Motor.run_layout_demo"] --> Y["ledger existente: _execute_step"]
    Y --> Z["necessidade → busca → plano → validação → prévia interna"]
  end
~~~

- Na main, Motor.run_multipauta_demo já protege ingestão, triagem, etapas por matéria, checagem de direitos, composição, prévia interna e aprovação humana. O mecanismo durável disponível é Motor._execute_step, que persiste tentativas e eventos com chave idempotente.
- A PR #8 adiciona AgentQueue/TaskDispatcher, executores e agendamento opcional, mas permanece aberta e atualmente conflita com main.
- A PR #10 usa a fila/dispatcher da PR #8 e tem como base a branch daquela PR; ela não é uma base independente para a Fase 0.
- **Estratégia:** branch codex/eng-codex-005-offline-layout, baseada em main@b44daf1; usar o ledger de etapas já integrado; não criar segundo dispatcher, não depender de #8/#10 e não modificar ou integrar essas PRs. A demonstração não usa nenhum executor SIWC.

## Contratos JSON versionados e gates

Todos os envelopes contêm artifact_id, schema_version, revision, content_sha256 e payload. O hash é calculado sobre JSON canônico.

| Contrato | Dados e validações principais |
|---|---|
| StoryPackage.v0 | Matéria fictícia com blocos semânticos, fontes da fixture, identidades editor/redator-persona/revisor e revisão sintética vinculada ao hash da revisão atual. |
| MediaInventory.v0 | Origem, crédito, titular, licença, direitos, transformações, modos permitidos, vínculo com bloco e, para ativo real autorizado, SHA-256 e dimensões. Placeholder não pode fingir bytes ou dimensões. |
| LayoutReference.v0 | Metadados pesquisáveis de função, época, dupla, mídia por media_roles, orientação, affordances digitais, referências e limites; propósito, problema, pontos fortes e fonte. A Fase 0 aceita somente descrições sintéticas e metadata_only; rejeita URL, caminho, bytes e scans. |
| LayoutPlan.v0 | Proposta com exatamente três referências verificadas, hashes da matéria/inventário/índice, colocação única dos blocos, dupla quando aplicável, layouts desktop/celular/contínuo, identidades dos papéis e separação editorial/publicidade. |
| CompositionValidation.v0 | Resultado PASS/FAIL com checks legíveis para revisão vigente, hashes, referências, cobertura dos blocos, direitos, linhagem dos ativos, publicidade, legendas, fallback móvel, integridade do HTML e uso interno. |

As personas aparecem apenas como identidade versionada dos dados de entrada; não são workers.

## Índice local e percurso da demonstração

LayoutReferenceIndex cria um SQLite local com os envelopes das referências sintéticas e seus hashes. A busca ranqueia tags explícitas e facetas function:, media:, era:, orientation:, affordance:, publication:, year:, source-page:, position: e limit:; as descrições também retornam época, dupla, orientação, affordances, fontes conhecidas e limites. O protótipo começa com nove registros sem imagem nem referência histórica copiada.

A chamada Motor.run_layout_demo() é serializada pelo lock já usado pelo Motor e executa as etapas com Motor._execute_step:

1. derivar necessidade visual a partir dos blocos semânticos;
2. buscar três referências no índice por tags;
3. propor LayoutPlan.v0 com hash da matéria, inventário, índice e papéis;
4. validar composição e direitos;
5. validar deterministicamente o HTML renderizado;
6. registrar e restaurar a prévia interna local.

As chaves das etapas incluem os hashes que determinam suas entradas. Uma matéria alterada recebe novo hash e novo plano; as etapas concluídas com a mesma entrada são reutilizadas. Uma falha de direitos bloqueia a prévia, deixa o run em failed_intervention e não repete etapas concluídas numa nova execução idêntica.

A execução bem-sucedida termina em awaiting_approval. Esse estado só indica revisão interna pendente; não habilita publicação.

## Cenários exercitados

1. Reportagem fictícia com duas imagens pequenas e legendas vinculadas.
2. Comparativo fictício de consoles, com itens separados nas páginas 2 e 3.
3. Mapa panorâmico fictício em dupla, com continuidade, aviso de orientação horizontal opcional, alternativa legível quando a rotação está bloqueada, rolagem e controle de zoom.

Em duplas, a prévia identifica as páginas 2 e 3 e as coloca lado a lado em viewport desktop. Em tela estreita, os itens podem empilhar; a rotação não é forçada. O mapa mantém rolagem horizontal, zoom e modo Contínua. As imagens são placeholders declarados, sem arquivos de imagem.

## Entrega de engenharia

- [Contratos](../../motor_editorial/layout/contracts.py)
- [Índice SQLite](../../motor_editorial/layout/index.py)
- [Planejador, validador e prévia](../../motor_editorial/layout/engine.py)
- [Percurso integrado ao Motor](../../motor_editorial/layout/pipeline.py)
- [Fixture sintética](../../motor_editorial/layout/fixtures/layout-demo.json)
- [Testes de contratos e integração](../../motor_editorial/tests/test_layout.py)
- [Comando e operação local](../../motor_editorial/README.md)

Comando PowerShell:

~~~powershell
.\.venv\Scripts\python.exe -m motor_editorial --data-dir "$env:TEMP\revista-gamer-layout-demo" layout-demo
~~~

Os relatórios, planos, validações, prévias HTML e banco do índice são gravados na pasta de dados local, sob artifacts/layout-demo/. Não são mídia de produção nem artefatos para publicação.

## Validação registrada

Ambiente: Windows, CPython 3.11.9 em .venv.

- python -m unittest motor_editorial.tests.test_layout -v — **9 testes aprovados**.
- python -m unittest discover -s motor_editorial/tests -q — **31 testes aprovados**, sem falhas.
- python -m compileall -q motor_editorial — passou.
- git diff --check — passou.
- Execução pelo CLI em diretório temporário isolado — **3/3 cenários PASS**, cada qual com 3 referências e 20 checks PASS; network_calls=0, siwc_calls=0, paid_api_calls=0 e published=false.

A validação automatizada inspeciona conteúdo, legendas, páginas 2–3, controles responsivos, fallback móvel, zoom, overflow e ausência de chamadas externas. **Não foi feita inspeção visual final em navegador.** O HTML é um mock técnico de Fase 0, não a integração gráfica aprovada do produto.

## Retomada ENG-CODEX-006 — aceite A4 (2026-10-24)

Validação executada no Windows neste HEAD, com o ambiente existente `\.venv\Scripts\python.exe`:

- `& '.\.venv\Scripts\python.exe' --version` — Python **3.11.9**.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_layout -v` — **14 testes aprovados** em 2,965 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` — **36 testes aprovados** em 24,806 s. Esta execução completa conclui a validação que havia sido interrompida antes da retomada.
- `& '.\.venv\Scripts\python.exe' -m motor_editorial --data-dir "$env:TEMP\rg-eng-codex-006-a4-7aef31f3e2584251928d4a6dc0c6654d" layout-demo` — **3/3 cenários PASS**, 22/22 checks por cenário, zero checks com falha; `status=awaiting_approval`, `network_calls=0`, `siwc_calls=0`, `paid_api_calls=0`, `published=false`. O diretório temporário foi `C:\Users\saimi\AppData\Local\Temp\rg-eng-codex-006-a4-7aef31f3e2584251928d4a6dc0c6654d`. Os três cenários terminam `not_published`.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` — passou.
- `git diff --check origin/main...HEAD` — passou antes da atualização deste relatório; `git diff --check` será repetido sobre os documentos atualizados antes do commit.

As correções C-005-1/2/3 estão no HEAD `efdc478` (e no upstream da branch) e os testes atuais exercitam ordem/`sequence`, linhagem canônica das identidades e coerência entre licença/direitos. `awaiting_approval` significa que a prévia interna aguarda revisão humana; não indica aceite do Fundador, integração visual no leitor v0.3 nem publicação. Não houve inspeção visual em navegador.

## Limites e pendências

- A biblioteca contém somente metadados sintéticos; aquisição, armazenamento privado e autorização de referências reais exigem decisões e controle de direitos posteriores.
- A interface preparada para ativos autorizados exige hash, dimensões, licença, crédito e vínculo editorial; nenhum ativo real foi incluído nesta execução.
- A revisão da implementação está pendente na [PR #18](https://github.com/Saaimingo/Revista_Gamer/pull/18); não fazer merge automático.
- PR #8, PR #10, PR #13, PR #14 e PR #16 não foram alteradas nem mescladas nesta execução. Issue #15 permanece separada e não é concluída por este trabalho.
