# ENG-CODEX-011 — checkpoint da prova real da fábrica

**Atualizado:** 2026-10-26, após seleção editorial e correção do pré-despacho do jornalista
**Issue de execução:** [#41](https://github.com/Saaimingo/Revista_Gamer/issues/41)
**Branch de implementação:** `codex/eng-codex-011-live-factory`, iniciada sobre `codex/eng-codex-010-factory-fictional-e2e@fcb1a3c785834edb3abf8eca74b517727ba8abf9`
**Status:** em andamento; Radar/triagem e investigação reais concluídos; editor real selecionou Proton 11.0-2e e Ranzinza. A tarefa de redação foi bloqueada antes de SIWC por alteração do DNA durante validação. Correção validada; ainda sem chamada do jornalista, matéria, revisão ou prévia.

## Estado remoto e autorização

- Issue #41 está aberta e sem comentários adicionais; o corpo integral é a ordem vigente desta missão.
- PR #40 continua aberta, draft, sem reviews e sem merge; base `codex/eng-codex-008-siwc-validation`, head `fcb1a3c785834edb3abf8eca74b517727ba8abf9`.
- PR #38 continua aberta, draft, sem reviews e sem merge; head `5a592151d9a837d204037c5f8d64186c0dc122ca`. Seus três ensaios de redação já concluídos não serão repetidos.
- PR #34 continua aberta, draft, sem reviews e sem merge; head `8d43a6c855807b2229a8e1eb620a31c6bb6e28e2`.
- Issue #33 segue aberta. O checkpoint H05 de `8d43a6c` registra somente a ponte offline parcial; nenhum StoryDraft H05 real nem handoff de pesquisa complementar foi executado.
- Issue #35 mantém a decisão `INDEX_ONLY` somente para ENG-008/H05 e histórico anterior. Issue #41 autoriza escopo público novo apenas para ENG-011, com política e limites explícitos.
- A Direção informou 76% de franquia disponível e autorizou SIWC/Plus para esta execução; este percentual é observação humana, não saldo SIWC nem conversão de tokens. Sem APIs pagas, novo login, publicação, deploy ou merge.
- `motor_editorial siwc status` confirmou credencial SIWC local existente e escopo `chatgpt.tokens.use.direct`. A primeira execução real, registrada abaixo, usou o catálogo e uma triagem; nenhuma autenticação nova ocorreu.

## Prova concluída até aqui

- Estado inicial do Git foi verificado limpo, na branch ENG-010, com upstream confirmado; `origin` foi atualizado com `git fetch origin`.
- AGENTS.md, Bíblia, README, Decisões, Status geral, README de Engenharia, contrato de entregas, protocolo de handoff, README do Motor e referências online das Issues #33/#35/#37/#41 e PRs #34/#36/#38/#40 foram consultados.
- Branch nova criada sem tocar nas branches/PRs anteriores.
- ENG-010 demonstrou somente pipeline determinístico sintético e preview não aberto; não será apresentado como execução ENG-011.
- ENG-009 publicou três originais para revisão humana; seus testes não serão reexecutados.

## Unidades ENG-011

- **U0 — Estado e limites:** concluída; evidências acima.
- **U1 — Integração mínima:** concluída e validada em testes focados. Reutiliza a única `AgentQueue`/`TaskDispatcher`, Radar, `ResearchService`, `ResearchResultRouter`, catálogo SIWC e layout/renderer existentes; mediação sem correspondência textual exata, com testes de Unicode, pontuação, paráfrase, ambiguidade e segurança.
- **U2 — Radar real:** parcial. Três requisições únicas foram feitas a `api.github.com`; duas retornaram HTTP 200 e uma ficou `blocked` sem status HTTP nem diagnóstico persistido. O agente de triagem concluiu uma chamada real e classificou os grupos Proton e SDL como `monitoramento`. O adaptador inicialmente não vinculou IDs de eventos às candidatas e parou antes do editor; a correção está pronta e a continuação reutiliza a saída existente. Orçamento: até 4 requisições totais, 8/dia, paralelismo 1 e sem retry.
- **U3 — Redação e pesquisa:** investigador e editor concluíram chamadas reais; resposta do investigador foi recuperada sem repetição. Editor selecionou Proton 11.0-2e e Ranzinza. A primeira preparação do jornalista foi bloqueada pelo hash do DNA após remoção técnica da quebra de linha final, antes de SIWC. Correção e reabertura sem chamada externa prévia estão implementadas; redação e ciclo complementar seguem pendentes.
- **U4 — Checagem, revisão e versões:** pendente. Chamadas reais de fact-check e revisão; redator real cria uma revisão separada somente quando necessário; status final humano permanece pendente.
- **U5 — Imagem e prévia:** pendente. Usar imagem original ou ativo com licença compatível; gerar prévia determinística e servi-la apenas em loopback HTTP; confirmar visualmente texto e imagem no navegador.
- **U6 — Evidência final:** pendente. Uso/latência por papel, relatório curto, arquivos privados integrais com hashes, checkpoint, commits/push e prova visual. Não declarar E2E se qualquer critério estiver bloqueado.

## Próximo passo exato

Após registrar a correção do hash de DNA, executar `& '.\.venv\Scripts\python.exe' -m motor_editorial.eng_codex_011 resume --image-path 'C:\Users\saimi\.codex\generated_images\01a17625-b527-7482-9736-47bee96d96c6\exec-e12dc452-f0bd-4992-8f49-c1ea7db2cc10.png'`. A retomada reutiliza Radar, triagem, investigador e editor; reabre a tarefa de redação somente porque a tentativa anterior não iniciou chamada externa. Uma requisição pública permanece reservada ao pedido do jornalista pelo Motor. Parar em `429`, chamada ambígua, falta de direitos ou orçamento insuficiente; não repetir resposta SIWC durável.

## Atualização técnica — 2026-10-26, antes da primeira execução real

- Revalidação live: Issue #41 aberta e sem comentários novos; PR #40 e PR #38 abertas/draft, sem review/merge; PRs #36 e #34 abertas/draft, sem review/merge. Issue #33 continua aberta e H05 não foi executada; Issue #35 restringe apenas H05/ENG-008 ao índice local e não revoga a autorização nova, limitada a ENG-011, da Issue #41.
- Branch atual `codex/eng-codex-011-live-factory`, base `fcb1a3c785834edb3abf8eca74b517727ba8abf9`, sem upstream configurado; código ainda não foi commitado nem enviado. Nenhuma chamada de descoberta externa ou inferência editorial ENG-011 foi feita até este registro.
- DNA aprovado conferido diretamente nas refs remotas: 19 arquivos entre Ranzinza, Beto e Nina; 19/19 SHA-256 coincidem com o manifesto. Corrigido no runner um SHA copiado incorretamente para uma amostra da Nina. Todos os arquivos permanecem inalterados e source-locked.
- As regressões ENG-011/integrações focadas passaram: CPython 3.11 no `.venv`, `python -m unittest motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_research_mediation_011 motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_layout motor_editorial.tests.test_factory_role_draft_bridge -q` — 62/62 OK. O primeiro ensaio com Python global teve um erro ambiental por falta de `tzdata`; a dependência `tzdata>=2025.2` já está satisfeita no `.venv`, e a execução repetida nesse ambiente passou.
- `py_compile`, ajuda CLI `run --image-path` e `git diff --check` passaram. Teste local do carregador de imagem confirmou cópia byte idêntica: PNG 1536×1024, 2.564.202 bytes, SHA-256 `6cccc5e4d0d5c3e291d7d68ed851f6777d467af80deb10cabeb370c38355b5bf`; geração ImageGen original fica apenas no armazenamento privado, com uso limitado a `internal_preview`.
- O jornalista receberá o identificador e a procedência da pauta, mas não o excerto do changelog obtido na varredura inicial; a lacuna está explicitada para que formule o pedido complementar em linguagem natural. O Motor aceitará somente a rota confiável para o repositório/tag escolhido e entregará o resultado ao mesmo papel/matéria. Assim o retorno deve acrescentar a evidência detalhada que faltava, em vez de repetir o pacote inicial.
- Uma confirmação do teste focado via Python global não é evidência de produto: o resultado válido é a repetição 62/62 no `.venv`. Franquia observada pela Direção continua 76%; ainda sem uso de tokens editoriais medido. Nenhuma API paga, login, conta, publicação, deploy ou merge.

## Atualização técnica — após a primeira execução real, 2026-10-26

- Run privado `eng-codex-011-20261026T152226Z-0256b6a1c34d`; branch `codex/eng-codex-011-live-factory`. O catálogo listou 7 modelos e confirmou `gpt-6-luna`; uma inferência real de `triage_analyst` foi concluída, `role_schema_valid`, sem retry: tarefa `radar-triage-08092fe3306e823a5930d1afb2e20eeb`, resposta SHA-256 `63afb32fdc703de1628e8ae6cdd109ddf988f37dab32dc2db4a0cfb8806009a8`.
- A triagem consumiu 6.974 tokens de entrada, 1.022 de saída (481 de raciocínio dentro da saída), 7.996 totais, latência 21.188 ms; modelo `gpt-6-luna`, esforço `high`. Recibo integral permanece privado em `agent-usage/...attempt-001.json`. Catálogo é consulta de capacidade sem tokens editoriais. Até aqui: 1 inferência, 7.996 tokens medidos, nenhuma chamada de jornalista.
- Radar consultou três endpoints em série. Proton e SDL retornaram 21.914 e 101.758 bytes; a consulta de Godot foi `blocked`, sem `http_status`, bytes ou motivo no evento persistido, e não será repetida. A triagem encontrou registros recentes de Proton 11.0-2e (09/10/2026) e SDL 3.4.18 (02/10/2026), mas classificou os grupos como `monitoramento` porque ainda faltava conferir as notas: [Proton 11.0-2e](https://github.com/ValveSoftware/Proton/releases/tag/proton-11.0-2e) e [SDL 3.4.18](https://github.com/libsdl-org/SDL/releases/tag/release-3.4.18). Isso é resultado editorial real, não falha do modelo.
- Bloqueio técnico identificado: a resposta válida citou event IDs e os lotes tinham candidatas vinculadas a esses eventos; o adaptador comparava somente `item_id` e ainda excluía `monitoramento` antes do editor. Corrigido o vínculo por interseção de referências confiáveis, a reconstrução das candidatas a partir do banco Radar privado e o encaminhamento de `monitoramento` ao editor real. O contrato informa ao editor que esse estado não é aprovação automática.
- Retomada valida o task/response/hash/uso persistidos e não refaz catálogo, scan ou triagem. Duas fontes tiveram resultado, uma falhou; a quarta requisição total fica reservada ao detalhe da pauta escolhida. O conteúdo do artigo ainda não existe. Imagem original gerada pelo ImageGen está privada; nenhum dado editorial ou mídia foi enviado ao GitHub.
- Regressões depois da correção inicial: CPython 3.11 do `.venv`, foco de Mediação/Radar/roles/layout/ponte mais `test_eng_codex_011_runner` — 65/65 OK. `py_compile`, ajuda CLI `resume --image-path` e `git diff --check` passaram. Commit `af6c907` foi enviado antes da segunda retomada.

## Atualização técnica — recuperação do investigador, 2026-10-26

- Segunda retomada do mesmo run `eng-codex-011-20261026T152226Z-0256b6a1c34d` reutilizou triagem e pesquisa persistidas. O investigador fez uma única chamada SIWC: `gpt-6-luna`, esforço `high`, 7.501 tokens de entrada, 1.036 de saída (222 de raciocínio), 8.537 totais, 20.390 ms. Resposta SHA-256 `9ef1d777e09497bd77d32c9606d16866291b75f76d2ee3d401d9ffea41ef74a4`; recibo privado em `agent-usage/e011-0256b6a1c34d-evidence-investigator-live-dossier.attempt-001.json`.
- O JSON passou schema e referências de evidência. A montagem de `AgentResultEnvelope` rejeitou `claim_id` descritivos por espaços; isso bloqueou a fila depois da resposta completa. Nenhuma chamada do editor/jornalista e nenhuma quarta requisição pública foram feitas nessa tentativa.
- Criada canonicalização determinística de identificadores sem alterar a resposta bruta nem o rótulo original, e recuperação restrita a uma tarefa bloqueada com o código `siwc_result_envelope_invalid`, tentativa única, solicitação externa iniciada e hash da resposta idêntico ao artefato. O ledger grava `external_output_recovered`; o contador de tentativas permanece 1.
- Exercício isolado em cópia temporária do run real recuperou 10 claims, confirmou task `succeeded` e preservou o hash real da resposta; não tocou o ledger ativo nem chamou rede/SIWC. Regressões focadas no `.venv`: 119/119 OK, abrangendo contratos, executor SIWC, fila/orquestração, runner ENG-011, mediação, Radar, layout e ponte.
- O código e este checkpoint estão em validação para novo commit/push. Próximo passo: executar o comando `resume --image-path` acima; nenhum catálogo, scan, triagem ou chamada do investigador será repetido. Pendentes: decisão real do editor, uma redação por persona aprovada, pesquisa complementar solicitada pelo jornalista, fact-check, revisão editorial, versões integrais, prévia loopback HTTP e verificação visual no navegador.

## Atualização técnica — seleção editorial e falha prévia do jornalista, 2026-10-26

- Terceira retomada do mesmo run reutilizou o investigador recuperado e fez uma chamada real ao `assignment_editor`: `gpt-6-luna`, `high`, 11.342 tokens de entrada, 615 de saída (221 de raciocínio), 11.957 totais, 13.453 ms; resposta SHA-256 `38068152d212d30a12bd601d6a2e2e2e52e5acb5046a1a0beec55d4c57c7c4da`. Escolheu a pauta `Proton 11.0-2e` e `ranzinza` (Carranca), alinhada à linha de tecnologia.
- O dispatcher bloqueou a tarefa `persona_writer` com `agent_contract_invalid` antes de qualquer chamada externa (`external_request_started=false`, sem resposta ou tokens). Reprodução local com o payload persistido identificou a causa: `prepare_invocation` aplicava `.strip()` ao DNA carregado e, em seguida, comparava esse texto alterado ao hash original. O pacote Ranzinza tem 86.813 caracteres; hash integral aprovado `d1470b7e004c49e80ffd0c7fa2f732ae66ab3acfd8fdef852b7438fea86ad05a`.
- A validação agora preserva os bytes/texto do DNA e só verifica tipo, conteúdo não vazio e tamanho; a quebra de linha terminal não é removida. Uma reabertura de fila só aceita `agent.role.persona_writer`, bloqueio `agent_contract_invalid`, tentativa 1, `max_attempts=1`, sem resposta e `external_request_started=0`; mantém a tentativa anterior auditada e autoriza uma tentativa corrigida. Nenhuma chamada foi repetida.
- Exercício isolado em cópia temporária reutilizou as 10 alegações do investigador e a decisão do editor, confirmou hash do DNA, preparou o mesmo payload do jornalista e reabriu a fila com zero chamada de provedor. Regressões focadas no `.venv`: 121/121 OK; `py_compile` passou.
- Próxima ação após commit/push: executar `resume --image-path` uma vez para o rascunho original. Esperados: uma chamada real do Carranca/Ranzinza; somente se ela solicitar pesquisa em linguagem natural, uma requisição pública final via Radar/Motor. Restam pendentes pesquisa complementar, fact-check, revisão editorial, eventual revisão pelo redator, arquivos integrais e prévia aberta no navegador.

## Atualização técnica — retomada e fonte Radar já registrada, 2026-10-26

- Quarta retomada reutilizou investigador/editor e confirmou DNA/payload, mas encontrou `RadarStoreError` ao registrar novamente a fonte de detalhes `github-api-proton-detail`, que havia sido registrada antes da tentativa de redação. A fila parou ainda antes do despacho SIWC; não há nova inferência, recibo de uso nem requisição pública. O pedido de escritor permanece na tentativa 1 com `external_request_started=false`.
- Corrigido `_register_source` para reutilizar a fonte somente quando ID, URL oficial, estado de acesso/direitos e metadados de autorização coincidirem; rota divergente continua bloqueada. O checkpoint agora reconhece esse bloqueio exato após `persona_load` e retoma sem repetir papéis. Regressões focalizadas de runner/conectores/Radar: 41/41 OK; `py_compile` passou.
- Exercício isolado em cópia temporária confirmou retomada do checkpoint, uma única linha da fonte de Proton após registro repetido, reuso dos resultados do investigador/editor, DNA íntegro, reabertura da tarefa do redator e zero chamada pública/SIWC.
- Próximo passo: registrar este ajuste e executar `resume --image-path` novamente. O resume reutiliza as fontes, Radar, triagem, investigador e editor, então reabre apenas a tarefa bloqueada pré-SIWC do jornalista. A primeira chamada real de redação ainda está pendente; a pesquisa pública complementar continua dentro do saldo 3/4.

## Limites permanentes

`published=false`; gate de aprovação humana final pendente. Sem texto integral de artigo público de terceiros no repositório, sem segredos/logs sensíveis no GitHub, sem alterações de DNA, sem repetição das baterias ENG-008/009/010, sem merge, deploy ou publicação.
