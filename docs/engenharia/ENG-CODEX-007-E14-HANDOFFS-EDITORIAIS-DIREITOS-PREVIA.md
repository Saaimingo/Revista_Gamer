# ENG-CODEX-007 E14 — handoffs editoriais, direitos e prévia

- **Setor responsável:** Engenharia
- **Identificador do artefato:** ENG-CODEX-007-E14
- **Versão:** v0.1
- **Status:** validado localmente na branch de implementação; PR #30 continua draft e sem merge
- **Data de atualização:** 2026-10-25
- **Dependências:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), PR [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), E13 e contratos/layout já existentes
- **Aprovador:** ordem da Direção/Fundador 2 registrada na Issue #28; decisões editoriais finais permanecem humanas

## Objetivo e exclusões

Ligar investigação, proposta editorial, rascunho, checagem e revisão aos contratos existentes de StoryPackage, inventário de direitos, layout e prévia interna. A unidade foi executada inteiramente com papéis determinísticos e fixtures; não constitui avaliação de modelo ou aprovação editorial humana.

Sem chamadas a LLM, SIWC/Plus ou APIs pagas; sem rede, fonte real, banco runtime, mídia real, publicação, deploy ou merge. Os DNAs aprovados não foram modificados. Todo StoryPackage e relatório da fábrica preserva `published=false`.

## Implementação

- `motor_editorial/editorial_handoffs.py` define envelopes `EditorialHandoff.v1` para `EvidenceDossier.v1`, `EditorialBrief.v1`, `StoryDraft.v1`, `FactCheckVerdict.v1` e `EditorialReview.v1`. Validadores conferem hashes de conteúdo, campos, fontes/evidências e linhagem da mesma pauta.
- A fábrica vincula as etapas aos papéis habilitados do catálogo versionado — `evidence_investigator`, `assignment_editor`, `persona_writer`, `fact_checker` e `editorial_reviewer` — resolvendo versão e hash existentes. As saídas permanecem determinísticas e sintéticas; não houve execução desses papéis por modelo.
- Cada handoff fica no resultado durável da tarefa da `AgentQueue` existente e o hash dos handoffs recebidos segue no payload da próxima etapa. Nenhuma fila ou dispatcher paralelo foi introduzido.
- A criação de StoryPackage exige os cinco artefatos, evidências coerentes e checagem/revisão `pass` para o hash atual. `hold`, texto corrigido com pareceres antigos, hashes inconsistentes ou evidência externa ao dossiê bloqueiam a esteira.
- O texto corrigido recebe revisão `r2` e exige novos `FactCheckVerdict` e `EditorialReview`. O parecer final permanece vinculado ao hash r2 e continua exigindo gate humano.
- `EditorialBrief` registra gênero, ângulo, perguntas, lacunas e a separação do gate de direitos. A fábrica então reaproveita os contratos existentes de `MediaInventory`, `StoryPackage`, `LayoutPlan`, validação determinística e prévia HTML. O ativo é um placeholder textual sintético e não possui bytes nem licença presumida.
- Instruções encontradas no texto de uma fonte são marcadas no dossiê como conteúdo não confiável, mantidas como dado e não executadas.

## Casos e evidências

`motor_editorial/fixtures/factory-e14-cases.json` contém três casos fictícios, com URLs `example.invalid` não consultadas:

- **Rumor atribuído:** o dossiê preserva `attributed_rumor`; a checagem admite somente quando a narrativa mantém a atribuição e a ausência de confirmação.
- **Hardware:** o número é tratado como especificação declarada; o texto explicita que não houve medição ou benchmark próprio.
- **Jogo/mod:** o texto atribui a descrição às notas fictícias e declara que não houve instalação ou teste.

Também foram verificados um ataque de instrução dentro de evidência, um `hold` por divergência, um bloqueio de direitos pendentes/negados, tentativas de reutilizar pareceres obsoletos e retomada das tarefas persistidas.

## Validação local

- CPython 3.11.9, `.venv`.
- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_factory -q` → **10/10 OK em 27,855 s**.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **194/194 OK em 125,683 s**.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` → exit 0; apenas avisos de normalização LF/CRLF do Git no Windows.

Os testes usaram somente fixtures e SQLite temporário. A prévia foi renderizada localmente e permaneceu interna. Não foram consultadas fontes públicas, contas, SIWC/Plus, modelos, APIs externas ou serviços pagos. Os contadores do relatório sintético são zero; não representam uma medição de execução de modelo.

## Arquivos entregues

- Commit de implementação/testes: `8dcc1e6` (`feat: add revision-bound editorial handoffs for E14`).
- `motor_editorial/editorial_handoffs.py`
- `motor_editorial/factory.py`
- `motor_editorial/fixtures/factory-e14-cases.json`
- `motor_editorial/tests/test_factory.py`
- `docs/engenharia/ENG-CODEX-007-E14-HANDOFFS-EDITORIAIS-DIREITOS-PREVIA.md`
- README setorial, índice de engenharia e checkpoint ENG-CODEX-007

## Pendências e próximo passo

E14 não decide se rumor merece publicação, não aprova matéria e não habilita persona pública ou execução de modelo. O próximo passo autorizado é **E15**, ensaio integrado offline multipauta com retomada e regressões. E17 continua bloqueada para chamadas SIWC/Plus reais pela restrição vigente; a franquia disponível não altera esse limite.
