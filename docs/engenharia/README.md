# Setor: engenharia e Codex

Status: **primeira implementação LOCAL autorizada (Motor v0.1); não há pipeline executável pronto nem autorização para implantação pública**.

## Ordem técnica vigente

- [Especificação Motor Editorial v0.1](ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md) — arquitetura e critérios de aceite.
- [Ordem Codex 001: construir](ORDEM-CODEX-001-CONSTRUIR-MOTOR-V0.1.md) — executar código e testes, preparar PR, sem publicação.

Este trabalho não ativa os blocos conceituais e não autoriza integrações reais de IA/notícias.

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
