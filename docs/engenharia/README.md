# Setor: engenharia e Codex

Status: **arquitetura proposta; não há pipeline executável nem autorização para implantação**.

## Primeiro estágio

Implementar futuramente um orquestrador determinístico com agenda, fila, estado, validações, tentativas limitadas, trilha de auditoria e pontos de aprovação humana. Os agentes de IA são chamados sob demanda. Não construir um harness alternativo sem evidência de necessidade.

Três funções operacionais candidatas: editor-pesquisador, redator que recebe perfil público de persona, revisor independente. O número definitivo depende de testes. Persona ≠ processo. Não multiplique modelos por personagem.

## Contratos de integração

Consumir somente especificações `aprovado`; anexar referências de versão/commit na execução. Solicitar faltas pelo [protocolo](../operacao/PROTOCOLO-HANDOFF.md). Validação de direitos de ativos e posição de publicidade são controles de software, não julgamentos livres de LLM. Nenhuma etapa publicada sem aprovação explícita.

## Custo e autonomia

Antes de automatizar: verificar oficialmente limites da assinatura Codex, possibilidade de chamadas programáticas elegíveis e necessidade de API separada. Medir por tarefa, tempo, iterações e esgotamento da franquia; manter margem de segurança. GitHub Actions e nuvem só quando custos, autenticação e permissões forem validados. Não supor acesso à conta do ChatGPT por runner em nuvem.

## Tecnologia e testes

Priorizar mecanismos simples, logs, estados recuperáveis e conteúdo estático otimizado. Leitor deve conseguir navegar em máquina modesta e sem efeitos. Restringir dependências e evitar baixar mídias sem licença. Segredos em secret manager, nunca neste repositório.

## Primeiro experimento proposto

Uma pauta real -> investigação com fonte -> texto com persona -> revisão -> entrega para diretor, sem publicação automática e com medição da franquia. Somente depois projetar a produção de edição completa.
