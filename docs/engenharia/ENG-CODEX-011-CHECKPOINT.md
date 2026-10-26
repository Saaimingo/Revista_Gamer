# ENG-CODEX-011 — checkpoint da prova real da fábrica

**Atualizado:** 2026-10-26, início da execução
**Issue de execução:** [#41](https://github.com/Saaimingo/Revista_Gamer/issues/41)
**Branch de implementação:** `codex/eng-codex-011-live-factory`, iniciada sobre `codex/eng-codex-010-factory-fictional-e2e@fcb1a3c785834edb3abf8eca74b517727ba8abf9`
**Status:** em andamento; nenhuma chamada editorial ENG-011 feita ainda.

## Estado remoto e autorização

- Issue #41 está aberta e sem comentários adicionais; o corpo integral é a ordem vigente desta missão.
- PR #40 continua aberta, draft, sem reviews e sem merge; base `codex/eng-codex-008-siwc-validation`, head `fcb1a3c785834edb3abf8eca74b517727ba8abf9`.
- PR #38 continua aberta, draft, sem reviews e sem merge; head `5a592151d9a837d204037c5f8d64186c0dc122ca`. Seus três ensaios de redação já concluídos não serão repetidos.
- PR #34 continua aberta, draft, sem reviews e sem merge; head `8d43a6c855807b2229a8e1eb620a31c6bb6e28e2`.
- Issue #33 segue aberta. O checkpoint H05 de `8d43a6c` registra somente a ponte offline parcial; nenhum StoryDraft H05 real nem handoff de pesquisa complementar foi executado.
- Issue #35 mantém a decisão `INDEX_ONLY` somente para ENG-008/H05 e histórico anterior. Issue #41 autoriza escopo público novo apenas para ENG-011, com política e limites explícitos.
- A Direção informou 76% de franquia disponível e autorizou SIWC/Plus para esta execução; este percentual é observação humana, não saldo SIWC nem conversão de tokens. Sem APIs pagas, novo login, publicação, deploy ou merge.
- `motor_editorial siwc status` confirmou credencial SIWC local existente e escopo `chatgpt.tokens.use.direct`. Nenhuma consulta ao catálogo de modelos ou inferência da ENG-011 ocorreu até este checkpoint.

## Prova concluída até aqui

- Estado inicial do Git foi verificado limpo, na branch ENG-010, com upstream confirmado; `origin` foi atualizado com `git fetch origin`.
- AGENTS.md, Bíblia, README, Decisões, Status geral, README de Engenharia, contrato de entregas, protocolo de handoff, README do Motor e referências online das Issues #33/#35/#37/#41 e PRs #34/#36/#38/#40 foram consultados.
- Branch nova criada sem tocar nas branches/PRs anteriores.
- ENG-010 demonstrou somente pipeline determinístico sintético e preview não aberto; não será apresentado como execução ENG-011.
- ENG-009 publicou três originais para revisão humana; seus testes não serão reexecutados.

## Unidades ENG-011

- **U0 — Estado e limites:** concluída; evidências acima.
- **U1 — Integração mínima:** concluída e validada em testes focados. Reutiliza a única `AgentQueue`/`TaskDispatcher`, Radar, `ResearchService`, `ResearchResultRouter`, catálogo SIWC e layout/renderer existentes; mediação sem correspondência textual exata, com testes de Unicode, pontuação, paráfrase, ambiguidade e segurança.
- **U2 — Radar real:** implementação e limites prontos, execução externa pendente. Allowlist `api.github.com`; até 4 requisições totais (3 consultas de lançamentos + 1 detalhe escolhido), 8/dia por domínio, paralelismo 1, sem retry. O preflight anterior registrou robots 404 tratado conforme RFC 9309; nenhuma consulta de notícia desta missão ocorreu ainda.
- **U3 — Redação e pesquisa:** pendente. Triagem, editor, investigação, jornalista e ciclo de pesquisa complementar serão tarefas reais na fila compartilhada. Carregar o DNA aprovado sem alteração e conferir seu SHA-256.
- **U4 — Checagem, revisão e versões:** pendente. Chamadas reais de fact-check e revisão; redator real cria uma revisão separada somente quando necessário; status final humano permanece pendente.
- **U5 — Imagem e prévia:** pendente. Usar imagem original ou ativo com licença compatível; gerar prévia determinística e servi-la apenas em loopback HTTP; confirmar visualmente texto e imagem no navegador.
- **U6 — Evidência final:** pendente. Uso/latência por papel, relatório curto, arquivos privados integrais com hashes, checkpoint, commits/push e prova visual. Não declarar E2E se qualquer critério estiver bloqueado.

## Próximo passo exato

Concluir a revisão local do runner e confirmar todos os hashes dos DNAs aprovados. Rodar apenas as regressões focadas; fazer commit e push do código/checkpoint sem textos ou imagens da reportagem. Em seguida executar uma única vez `& '.\.venv\Scripts\python.exe' -m motor_editorial.eng_codex_011 run --image-path <caminho-privado-da-imagem>`: catálogo SIWC uma vez, chamadas editoriais sequenciais e Radar limitado ao orçamento acima. Parar em `429`, chamada ambígua, falta de direitos ou orçamento insuficiente; não repetir tarefas com resposta durável.

## Atualização técnica — 2026-10-26, antes da primeira execução real

- Revalidação live: Issue #41 aberta e sem comentários novos; PR #40 e PR #38 abertas/draft, sem review/merge; PRs #36 e #34 abertas/draft, sem review/merge. Issue #33 continua aberta e H05 não foi executada; Issue #35 restringe apenas H05/ENG-008 ao índice local e não revoga a autorização nova, limitada a ENG-011, da Issue #41.
- Branch atual `codex/eng-codex-011-live-factory`, base `fcb1a3c785834edb3abf8eca74b517727ba8abf9`, sem upstream configurado; código ainda não foi commitado nem enviado. Nenhuma chamada de descoberta externa ou inferência editorial ENG-011 foi feita até este registro.
- DNA aprovado conferido diretamente nas refs remotas: 19 arquivos entre Ranzinza, Beto e Nina; 19/19 SHA-256 coincidem com o manifesto. Corrigido no runner um SHA copiado incorretamente para uma amostra da Nina. Todos os arquivos permanecem inalterados e source-locked.
- As regressões ENG-011/integrações focadas passaram: CPython 3.11 no `.venv`, `python -m unittest motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_research_mediation_011 motor_editorial.tests.test_radar_connectors motor_editorial.tests.test_radar_incremental motor_editorial.tests.test_layout motor_editorial.tests.test_factory_role_draft_bridge -q` — 62/62 OK. O primeiro ensaio com Python global teve um erro ambiental por falta de `tzdata`; a dependência `tzdata>=2025.2` já está satisfeita no `.venv`, e a execução repetida nesse ambiente passou.
- `py_compile`, ajuda CLI `run --image-path` e `git diff --check` passaram. Teste local do carregador de imagem confirmou cópia byte idêntica: PNG 1536×1024, 2.564.202 bytes, SHA-256 `6cccc5e4d0d5c3e291d7d68ed851f6777d467af80deb10cabeb370c38355b5bf`; geração ImageGen original fica apenas no armazenamento privado, com uso limitado a `internal_preview`.
- O jornalista receberá o identificador e a procedência da pauta, mas não o excerto do changelog obtido na varredura inicial; a lacuna está explicitada para que formule o pedido complementar em linguagem natural. O Motor aceitará somente a rota confiável para o repositório/tag escolhido e entregará o resultado ao mesmo papel/matéria. Assim o retorno deve acrescentar a evidência detalhada que faltava, em vez de repetir o pacote inicial.
- Uma confirmação do teste focado via Python global não é evidência de produto: o resultado válido é a repetição 62/62 no `.venv`. Franquia observada pela Direção continua 76%; ainda sem uso de tokens editoriais medido. Nenhuma API paga, login, conta, publicação, deploy ou merge.

## Limites permanentes

`published=false`; gate de aprovação humana final pendente. Sem texto integral de artigo público de terceiros no repositório, sem segredos/logs sensíveis no GitHub, sem alterações de DNA, sem repetição das baterias ENG-008/009/010, sem merge, deploy ou publicação.
