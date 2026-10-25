# Setor: engenharia e Codex

Status: **Motor Editorial v0.2 integrado à `main`; PRs #8, #10 e #18 continuam abertas e não mescladas; ENG-CODEX-007 E01–E14 validadas na branch `codex/eng-codex-007-factory-radar`, PR draft #30 sem merge; E15 está em andamento. ENG-CODEX-006 permanece registrado abaixo como trilha histórica.**

## Arquitetura operacional dos futuros agentes — 20/10/2026

**Diretriz da direção:** os Blocos 02–06 são **chats de concepção**, não workers. Os operadores futuros serão **agentes e módulos identificados, executados sob demanda pelo orquestrador**, com entradas e saídas versionadas. O diagramador terá **memória histórica privada e indexada** de soluções editoriais e produzirá `LayoutPlan`; o motor determinístico comporá/validará páginas sobre o leitor v0.3 e a identidade visual do Bloco 03.

- [Especificação arquitetural: papéis, contratos, acervo histórico e diagramador](ARQUITETURA-AGENTES-ACERVO-VISUAL-E-COMPOSICAO-2026-10-20.md).
- [Issue #17 — missão ENG-CODEX-005, Fase 0 offline](https://github.com/Saaimingo/Revista_Gamer/issues/17): começar interfaces, índice local, simulação de diagramador e testes, **sem SIWC, sem mídia histórica pública e sem merge automático**.
- [Issue #15 — composição visual e leitor integrados](https://github.com/Saaimingo/Revista_Gamer/issues/15): frente estética/UX separada, mas coordenada.
- **Baseline real:** v0.2 integrada à `main` via [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6); orquestração e fluxo editorial avançados continuam respectivamente em [PR #8](https://github.com/Saaimingo/Revista_Gamer/pull/8) e [PR #10](https://github.com/Saaimingo/Revista_Gamer/pull/10), não na `main`.

## Primeiro marco técnico concluído

- [Especificação Motor Editorial v0.1](ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md) — contrato e critérios cumpridos no protótipo.
- [Ordem Codex 001](ORDEM-CODEX-001-CONSTRUIR-MOTOR-V0.1.md) — concluída no [PR #3](https://github.com/Saaimingo/Revista_Gamer/pull/3), integrado à `main` em `525ae351d1e7375821435efeb1e012955785f69d`.
- [Código do Motor](../../motor_editorial/README.md), [relatório](RELATORIO-IMPLANTACAO-MOTOR-V0.1.md) — simulação offline, 11 testes aprovados em Windows 11/Python 3.11.9 e Linux/Python 3.12.14 segundo evidências registradas pelo Codex.
- Não são permitidos publicação, coleta real, API paga, produção editorial automatizada ou execução pública nesta fase.

Este marco não ativa os blocos conceituais e não autoriza integrações reais de IA/notícias.

## Segunda missao de engenharia - implementacao CODEX-002

- [Especificação ENG-MOTOR-002](ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md): multipauta, fluxos independentes, montagem de uma edição com matérias múltiplas e salvaguardas herdadas.
- [Ordem do construtor CODEX-002](ORDEM-CODEX-002-MOTOR-MULTIPAUTA.md) e [Issue #5](https://github.com/Saaimingo/Revista_Gamer/issues/5).
- **Status: implementação e testes concluídos; [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) integrado à `main`.** O protótipo continua offline e sem publicação.

## Terceira missão — CODEX-003: orquestração e SIWC

- [Especificação aprovada ENG-CODEX-003](ESPECIFICACAO-CODEX-003-ORQUESTRACAO-PLUS.md): fila SQLite, dispatcher, executores, perfis versionados, retomada, agenda desativada por padrão e prova local SIWC de uma tarefa sintética.
- [Relatório técnico ENG-CODEX-003](RELATORIO-ORQUESTRACAO-AGENTES-PLUS.md): implementação, evidências de teste, status de autenticação real, elegibilidade remota e migração futura para Debian 12.
- **PR #8 aberta e sem merge**, head `962dcd4`; a comparação original com a `main` via PR continua baseada no SHA `d9fbb6e`. A PR de revisão B1 [#24](https://github.com/Saaimingo/Revista_Gamer/pull/24), em rascunho, integra o head preservado da #8 à `origin/main@ce8f6a7`; seu conflito documental foi resolvido e a branch original não foi reescrita. [CODEX-003: orquestração durável e integração SIWC](https://github.com/Saaimingo/Revista_Gamer/pull/8).
- **PR #10 aberta e empilhada sobre #8**, head `3702789`; mantém a dependência de #8 e não está integrada à `main`. A branch B2 `codex/eng-codex-006-pipeline-reconcile` reconcilia esse head sobre B1 para revisão; a branch #10 original permanece intacta.
- [Unidade systemd de exemplo](../../deploy/systemd/revista-gamer-orchestrator.service.example): preparar operação contínua futura; não instalada nem habilitada.
- [Anteprojeto de 2026-10-19](ANTEPROJETO-ORQUESTRACAO-AGENTES-E-PLUS-2026-10-19.md) permanece como registro da proposta e dos pontos debatidos; foi sucedido, para este escopo, pela especificação aprovada acima.

O código da PR #8 inclui o adaptador SIWC, mas **esta missão ENG-CODEX-006 executa somente testes offline com executores simulados**; nenhuma chamada SIWC/Plus, agendamento, hospedagem ou publicação é feita ou habilitada. A reconciliação fica isolada em branch/PR e não integra automaticamente a `main`.

## Estudo arquitetural em debate

- [Análise provisória do fundador — orquestração orientada a eventos e referência n8n](ANALISE-PROVISORIA-FUNDADOR-ORQUESTRACAO-N8N-2026-10-17.md). **Não autoriza ativação de agentes reais, agendamento, custos ou mudança na v0.2.**
- [Anteprojeto da próxima etapa — orquestração de agentes e integração oficial com Plus](ANTEPROJETO-ORQUESTRACAO-AGENTES-E-PLUS-2026-10-19.md). O escopo CODEX-003 sucedeu este anteprojeto; sua inclusão preserva a trilha histórica, sem ativar operação real.

## Quarta missão — ENG-CODEX-004: Luna Max e experimento editorial controlado

- Ordem executada a partir da [Issue #9](https://github.com/Saaimingo/Revista_Gamer/issues/9), em branch separada baseada no head do PR #8.
- O catálogo autenticado SIWC listou `gpt-6-luna`; uma inferência sintética com `reasoning.effort=max` concluiu e retornou modelo/esforço compatíveis. O gate foi liberado.
- Uma amostra real de capa percorreu seis etapas SIWC; ficou aguardando revisão humana e não foi publicada. Métricas, pacote de fontes e rascunho estão no [relatório ENG-CODEX-004](RELATORIO-ENG-CODEX-004-EXECUCAO-LUNA-MAX-2026-10-19.md) e em `evidencias/`.
- **[PR #10](https://github.com/Saaimingo/Revista_Gamer/pull/10) aberto para revisão**, separado e sem merge; sua base é a branch do PR #8. O PR #8 também continua aberto e sem merge.
- A elegibilidade SIWC de app privado hospedado/VPS continua não confirmada. Nenhuma agenda, serviço Debian/VPS ou publicação foi ativada.

## Evolução futura

O protótipo possui estados, validações, tentativas limitadas, fila técnica, trilha de eventos e aprovação humana interna. Permanecem pendentes perfis públicos aprovados, fluxo editorial real, coleta/fonte autorizada, controle de acesso e backup. Agendas vêm desativadas; não ativar produção sem nova decisão e autorização.

Três funções operacionais candidatas: editor-pesquisador, redator que recebe perfil público de persona, revisor independente. O número definitivo depende de testes. Persona ≠ processo. Não multiplique modelos por personagem.

## Contratos de integração

Consumir somente especificações `aprovado`; anexar referências de versão/commit na execução. Solicitar faltas pelo [protocolo](../operacao/PROTOCOLO-HANDOFF.md). Validação de direitos de ativos e posição de publicidade são controles de software, não julgamentos livres de LLM. Nenhuma etapa publicada sem aprovação explícita.

## Custo e autonomia

Antes de automatizar, verificar oficialmente a elegibilidade de chamadas programáticas, os limites compartilhados do plano e a necessidade de API separada; SIWC só pode ser usado dentro da autorização aplicável e com consentimento. Medir por tarefa, tempo, iterações e consumo, mantendo margem de segurança. O acesso a apps privados hospedados permanece não confirmado e deve ser verificado antes de qualquer proposta de VPS. GitHub Actions e nuvem só após validar custos, autenticação e permissões. Não supor acesso à conta ChatGPT por runner em nuvem.

## Tecnologia e testes

Priorizar mecanismos simples, logs, estados recuperáveis e conteúdo estático otimizado. Leitor deve conseguir navegar em máquina modesta e sem efeitos. Restringir dependências e evitar baixar mídias sem licença. Segredos em secret manager, nunca neste repositório.

## Primeiro experimento proposto

Uma pauta real -> investigação com fonte -> texto com persona -> revisão -> entrega para diretor, sem publicação automática e com medição da franquia. Somente depois projetar a produção de edição completa.

## Entrega ENG-CODEX-005 — Fase 0 offline (2026-10-24)

- [Relatório técnico da Fase 0](RELATORIO-ENG-CODEX-005-FASE0-OFFLINE.md), vinculado à [Issue #17](https://github.com/Saaimingo/Revista_Gamer/issues/17). A4 corrige ordem/sequence, linhagem de identidades e consistência de direitos antes da prévia; validação foi sintética e offline.
- Código e testes permanecem na branch fonte `codex/eng-codex-005-offline-layout`, head `ab7d11f`, e na [PR #18](https://github.com/Saaimingo/Revista_Gamer/pull/18), aberta e sem merge. A integração com B1–B3 está somente na branch C0 `codex/eng-codex-006-e2e-experiment`; isso não altera a PR nem declara as etapas integradas à `main`.
- A4 usa artefatos versionados e render/validação determinísticos. A composição C0 documenta a ponte para o pipeline editorial e mantém a aprovação humana pós-prévia como gate separado; o leitor v0.3/identidade do Bloco 03 continua dependência futura da Issue #15.

## ENG-CODEX-007 — fábrica editorial e Radar (2026-10-25)

**Estado atual:** E01–E14 validadas localmente em branch/PR draft de implementação, sem merge. E15 é a unidade em andamento. PR #29 continua sendo somente pacote documental; os papéis registrados não são sessões LLM permanentes nem agentes avaliados por inferência real.

- [E01 — baseline e plano de integração](ENG-CODEX-007-E01-BASELINE-PLANO-INTEGRACAO.md).
- [E02 — contratos versionados e carregamento do regimento](ENG-CODEX-007-E02-CONTRATOS-VERSIONADOS.md).
- [E03 — catálogo de papéis funcionais](ENG-CODEX-007-E03-CATALOGO-PAPEIS-FUNCIONAIS.md): seis perfis habilitados, dois opcionais desligados e fixtures sintéticas.
- [E04 — armazenamento isolado do Radar](ENG-CODEX-007-E04-RADAR-STORE.md): schema separado `radar_*`, alegações versionadas, evidências imutáveis e migração coberta por fixture/backup/rollback.
- [E05 — conectores de leitura pública](ENG-CODEX-007-E05-CONETORES-LEITURA-PUBLICA.md): RSS/Atom, API JSON pública, HTML metadata-only, robots explícito e proteções TLS/SSRF/redirect/limite.
- [E06 — coleta incremental, cache e deduplicação](ENG-CODEX-007-E06-COLETA-INCREMENTAL-CACHE-DEDUP.md): cache ETag/Last-Modified por fonte+URL, hashes/diffs append-only, migração isolada do Radar para v2 e grupos de republicação com evidência.
- [E07 — pessoas, projetos, aliases, entrevistas e idiomas](ENG-CODEX-007-E07-PESSOAS-ALIAS-ENTREVISTAS-IDIOMAS.md): proveniência pública, homônimos contextualizados, histórico de funções, distinção entrevista/press release e linhagem de traduções; Radar schema v3, 147/147 testes integrais.
- [E08 — ledger de alegações, rumores e histórico](ENG-CODEX-007-E08-LEDGER-ORIGEM-STATUS-HISTORICO.md): estados epistemológicos separados do conteúdo, fontes-base/republicações/grupos independentes, declarações atribuídas, correções e contradições append-only; Radar schema v4, 148/148 testes integrais.
- [E09 — agendamento e política de coleta](ENG-CODEX-007-E09-AGENDAMENTO-POLITICA-COLETA.md): 3–6 janelas locais/dia no scheduler e fila existentes, UTC persistido, `skip`/`run_once`, pausa de grupo, `dry_run=true`, migrações aditivas de fixtures e quotas persistentes por hostname; Radar schema v5.
- [E10 — Radar geral, DiscoveryBatch e fila de triagem](ENG-CODEX-007-E10-RADAR-GERAL-DISCOVERY-TRIAGEM.md): novidade incremental e prioridade determinística configurável, agrupamento de republicações/rumores com proveniência e tarefa `triage_analyst` versionada na mesma fila, sem despacho LLM; suíte integral 166/166.
- [E11 — pesquisa sob demanda com perfis compartilhados](ENG-CODEX-007-E11-PESQUISA-SOB-DEMANDA.md): `ResearchService` cache-first sobre o mesmo índice de documentos/entidades/tópicos/alegações, request v1.1 ligado à revisão, budgets, escopos e packet persistente; suíte integral 176/176.
- [E12 — carteira dinâmica 10 + 10](ENG-CODEX-007-E12-CARTEIRA-DINAMICA-10-10.md): seleção determinística por prioridade fornecida, sem gerar reportagens; reavaliação por evento material, proteção auditável de membros e migração Radar v6→v7; suíte integral 185/185.
- [E13 — dispatcher, dependências e pesquisa retomável](ENG-CODEX-007-E13-DISPATCHER-DEPENDENCIAS-PESQUISA-RETOMADA.md): dependências persistentes no ledger existente, rotas determinísticas registradas, pesquisa cache-first e handoff idempotente de retorno ao artigo; suite integral 192/192.
- [E14 — handoffs editoriais, direitos e prévia](ENG-CODEX-007-E14-HANDOFFS-EDITORIAIS-DIREITOS-PREVIA.md): cinco artefatos tipados e presos por hash à revisão, papéis resolvidos no catálogo, rumores atribuídos e casos hardware/jogo-mod em fixtures, gate de direitos e prévia interna; suite integral 194/194.
- [Checkpoint ENG-CODEX-007](ENG-CODEX-007-CHECKPOINT.md), [Issue #28](https://github.com/Saaimingo/Revista_Gamer/issues/28) e [PR draft #30](https://github.com/Saaimingo/Revista_Gamer/pull/30).
