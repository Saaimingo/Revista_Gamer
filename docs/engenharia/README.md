# Setor: engenharia e Codex

Status: **Motor Editorial v0.2 implementado e validado localmente no Windows 11; PR #6 aberto para revisão arquitetural, sem merge.**

## Primeiro marco técnico concluído

- [Especificação Motor Editorial v0.1](ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md) — contrato e critérios cumpridos no protótipo.
- [Ordem Codex 001](ORDEM-CODEX-001-CONSTRUIR-MOTOR-V0.1.md) — concluída no [PR #3](https://github.com/Saaimingo/Revista_Gamer/pull/3), integrado à `main` em `525ae351d1e7375821435efeb1e012955785f69d`.
- [Código do Motor](../../motor_editorial/README.md), [relatório](RELATORIO-IMPLANTACAO-MOTOR-V0.1.md) — simulação offline, 11 testes aprovados em Windows 11/Python 3.11.9 e Linux/Python 3.12.14 segundo evidências registradas pelo Codex.
- Não são permitidos publicação, coleta real, API paga, produção editorial automatizada ou execução pública nesta fase.

Este marco não ativa os blocos conceituais e não autoriza integrações reais de IA/notícias.

## Segunda missao de engenharia - implementacao CODEX-002

- [Especificação ENG-MOTOR-002](ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md): multipauta, fluxos independentes, montagem de uma edição com matérias múltiplas e salvaguardas herdadas.
- [Ordem do construtor CODEX-002](ORDEM-CODEX-002-MOTOR-MULTIPAUTA.md) e [Issue #5](https://github.com/Saaimingo/Revista_Gamer/issues/5).
- **Status: implementação e testes concluídos; [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6) aberto para revisão arquitetural.** O protótipo continua offline e sem publicação.

## Estudo arquitetural em debate

- [Análise provisória do fundador — orquestração orientada a eventos e referência n8n](ANALISE-PROVISORIA-FUNDADOR-ORQUESTRACAO-N8N-2026-10-17.md). **Não autoriza implementação, ativação de agentes reais, agendamento ou mudança na v0.2.**

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
