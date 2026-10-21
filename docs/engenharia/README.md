# Setor: engenharia e Codex

Status: **Motor Editorial v0.2 integrado à main; PR #8 e PR #10 seguem separados; ENG-CODEX-005 Fase 0 implementada e validada offline, em revisão na [PR #18](https://github.com/Saaimingo/Revista_Gamer/pull/18).**

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

## Estudo arquitetural em debate

- [Análise provisória do fundador — orquestração orientada a eventos e referência n8n](ANALISE-PROVISORIA-FUNDADOR-ORQUESTRACAO-N8N-2026-10-17.md). **Não autoriza implementação, ativação de agentes reais, agendamento ou mudança na v0.2.**

- [Anteprojeto da próxima etapa — orquestração de agentes e integração oficial com Plus](ANTEPROJETO-ORQUESTRACAO-AGENTES-E-PLUS-2026-10-19.md). **EM DISCUSSÃO, não autoriza Codex, ativação de IA, autenticação, custos ou v0.3.**

## Evolução futura

O protótipo já possui estados, validações, tentativas limitadas, trilha de auditoria e aprovação humana interna. Ainda faltam agenda real, filas operacionais de produção, integrações, controle de acesso e backup; só implementar após nova especificação e autorização. Os agentes de IA são chamados sob demanda. Não construir um harness alternativo sem evidência de necessidade.

Três funções operacionais candidatas: editor-pesquisador, redator que recebe perfil público de persona, revisor independente. O número definitivo depende de testes. Persona ≠ processo. Não multiplique modelos por personagem.

## Contratos de integração

Consumir somente especificações `aprovado`; anexar referências de versão/commit na execução. Solicitar faltas pelo [protocolo](../operacao/PROTOCOLO-HANDOFF.md). Validação de direitos de ativos e posição de publicidade são controles de software, não julgamentos livres de LLM. Nenhuma etapa publicada sem aprovação explícita.

## Custo e autonomia

Antes de automatizar: verificar oficialmente limites da assinatura Codex, possibilidade de chamadas programáticas elegíveis e necessidade de API separada. Medir por tarefa, tempo, iterações e esgotamento da franquia; manter margem de segurança. GitHub Actions e nuvem só quando custos, autenticação e permissões forem validados. Não supor acesso à conta do ChatGPT por runner em nuvem.

## Tecnologia e testes

Priorizar mecanismos simples, logs, estados recuperáveis e conteúdo estático otimizado. Leitor deve conseguir navegar em máquina modesta e sem efeitos. Restringir dependências e evitar baixar mídias sem licença. Segredos em secret manager, nunca neste repositório.

## Primeiro experimento proposto

Uma pauta real -> investigação com fonte -> texto com persona -> revisão -> entrega para diretor, sem publicação automática e com medição da franquia. Somente depois projetar a produção de edição completa.

## Entrega ENG-CODEX-005 — Fase 0 offline (2026-10-20)

- [Relatório técnico da Fase 0](RELATORIO-ENG-CODEX-005-FASE0-OFFLINE.md), status em_revisao, vinculado à [Issue #17](https://github.com/Saaimingo/Revista_Gamer/issues/17).
- Código e testes estão em implementação isolada, baseada em main@b44daf1; o Motor reutiliza _execute_step e não duplica o dispatcher das PRs [#8](https://github.com/Saaimingo/Revista_Gamer/pull/8) e [#10](https://github.com/Saaimingo/Revista_Gamer/pull/10).
- Cenários e referências são sintéticos. Fase 0 não usa SIWC, API paga, rede, scans, mídia real ou publicação. A integração visual com o leitor continua na [Issue #15](https://github.com/Saaimingo/Revista_Gamer/issues/15).
- PR independente de revisão [#18](https://github.com/Saaimingo/Revista_Gamer/pull/18) está aberta e sem merge.
