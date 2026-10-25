# ENG-CODEX-007 — E17: piloto real SIWC/Plus bloqueado

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E17
- **Versão:** v0.1
- **Status:** bloqueado por limite explícito de escopo
- **Data de atualização:** 2026-10-25 19:59 America/Sao_Paulo
- **Dependências:** ordem E01–E19 na Issue #28; E16 concluída
- **Aprovador:** limite atual explicitado diretamente pelo usuário

## Motivo do bloqueio

A instrução vigente do usuário proíbe usar SIWC/Plus real nesta missão. Portanto, a E17 não fará login, atualização/autenticação, consulta `status/models`, probe, inferência nem teste de conta/modelo. A franquia estar disponível em 100% não revoga essa fronteira.

Este estado é `BLOCKED_BY_SCOPE`, não falha técnica, cota esgotada ou falta de credencial. Não consultei nem acessei credenciais persistidas; não houve chamadas reais, consumo, custo ou saída de modelo (**0**).

## Evidências e fronteiras

- A E17 requer piloto real apenas quando o acesso e a franquia estiverem autorizados e elegíveis; a ordem também manda continuar as partes offline se a etapa online for bloqueada.
- A orientação atual é mais restrita: nenhum SIWC/Plus real. Ela prevalece sobre o caminho condicional descrito na ordem anterior.
- Nenhum fallback para API paga, chave nova, outra conta ou sessão privada foi usado.
- Nenhuma agenda, coleta contínua, publicação, deploy ou migração de banco foi ativada.

## Continuação independente

As E18 e E19 seguem em modo offline com fixtures, transporte e avaliador determinísticos. Saídas reais de jornalista/modelo ficam `not_executed`; a revisão humana de direção e qualquer conclusão sobre fidelidade de DNA ou qualidade editorial permanecem pendentes. Mocks validam contratos e bloqueios, não qualidade de uma inferência real.

## Próxima unidade

E18 — preparar e executar a matriz isolada em modo offline, preservando os DNAs aprovados sem edição. PR #30 permanece draft/aberta, sem merge; `published=false`.
