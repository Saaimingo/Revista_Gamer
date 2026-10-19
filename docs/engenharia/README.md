# Setor: engenharia e Codex

Status: **Motor Editorial v0.2 integrado à `main` pelo PR #6; etapa CODEX-003 aprovada para implementação nesta branch.**

## Primeiro marco técnico concluído

- [Especificação Motor Editorial v0.1](ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md) — contrato e critérios cumpridos no protótipo.
- [Ordem Codex 001](ORDEM-CODEX-001-CONSTRUIR-MOTOR-V0.1.md) — concluída no [PR #3](https://github.com/Saaimingo/Revista_Gamer/pull/3), integrado à `main` em `525ae351d1e7375821435efeb1e012955785f69d`.
- [Código do Motor](../../motor_editorial/README.md), [relatório](RELATORIO-IMPLANTACAO-MOTOR-V0.1.md) — simulação offline, 11 testes aprovados em Windows 11/Python 3.11.9 e Linux/Python 3.12.14 segundo evidências registradas pelo Codex.
- Não são permitidos publicação, coleta real, API paga, produção editorial automatizada ou execução pública nesta fase.

Este marco não ativa os blocos conceituais e não autoriza integrações reais de IA/notícias.

## Segunda missao de engenharia - implementacao CODEX-002

- [Especificação ENG-MOTOR-002](ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md): multipauta, fluxos independentes, montagem de uma edição com matérias múltiplas e salvaguardas herdadas.
- [Ordem do construtor CODEX-002](ORDEM-CODEX-002-MOTOR-MULTIPAUTA.md) e [Issue #5](https://github.com/Saaimingo/Revista_Gamer/issues/5).
- **Implementação e testes concluídos; [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) integrado à `main`.** O núcleo editorial v0.2 continua offline e sem publicação.

## Terceira missão — CODEX-003: orquestração e SIWC

- [Especificação aprovada ENG-CODEX-003](ESPECIFICACAO-CODEX-003-ORQUESTRACAO-PLUS.md): fila SQLite, dispatcher, executores, perfis versionados, retomada, agenda desativada por padrão e prova local SIWC de uma tarefa sintética.
- [Relatório técnico ENG-CODEX-003](RELATORIO-ORQUESTRACAO-AGENTES-PLUS.md): implementação, evidências de teste, status de autenticação real, elegibilidade remota e migração futura para Debian 12.
- **PR #8 aberto para revisão (OPEN, não draft)**, sem merge: [CODEX-003: orquestração durável e integração SIWC](https://github.com/Saaimingo/Revista_Gamer/pull/8).
- [Unidade systemd de exemplo](../../deploy/systemd/revista-gamer-orchestrator.service.example): preparar operação contínua futura; não instalada nem habilitada.
- [Anteprojeto de 2026-10-19](ANTEPROJETO-ORQUESTRACAO-AGENTES-E-PLUS-2026-10-19.md) permanece como registro da proposta e dos pontos debatidos; foi sucedido, para este escopo, pela especificação aprovada acima.

O trabalho fica isolado em branch/PR. Somente a prova técnica SIWC local pode chamar o provedor, após consentimento do diretor. Agenda Plus, conteúdo editorial real, hospedagem remota e publicação não são ativados por esta etapa.

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

O fluxo oficial SIWC permite chamadas elegíveis com consentimento, sujeitas a limites compartilhados do plano. O acesso a apps privados hospedados permanece não confirmado; a elegibilidade precisa ser confirmada com a OpenAI antes da VPS. Não supor acesso à conta do ChatGPT por runner em nuvem.

## Tecnologia e testes

Priorizar mecanismos simples, logs, estados recuperáveis e conteúdo estático otimizado. Leitor deve conseguir navegar em máquina modesta e sem efeitos. Restringir dependências e evitar baixar mídias sem licença. Segredos em secret manager, nunca neste repositório.

## Primeiro experimento proposto

Uma pauta real -> investigação com fonte -> texto com persona -> revisão -> entrega para diretor, sem publicação automática e com medição da franquia. Somente depois projetar a produção de edição completa.
