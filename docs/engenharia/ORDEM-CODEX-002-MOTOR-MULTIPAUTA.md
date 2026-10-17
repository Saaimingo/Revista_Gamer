# Ordem de Serviço CODEX-002 — Implementar Motor Editorial v0.2 multipauta

**Status:** AUTORIZADA PARA CONSTRUÇÃO E TESTE DO PROTÓTIPO OFFLINE; **não para merge, deploy, IA real ou publicação**.  
**Baseline:** `main` atual, após PR #3 (código v0.1) e PR #4 (relatório de aceite).
**Contrato principal:** `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md`.

## Missão do construtor

Você, Codex, deverá **IMPLEMENTAR**, e não apenas redesenhar, a segunda etapa da fábrica editorial da Revista Gamer. A v0.1 aceita uma pauta por edição; a v0.2 deve administrar pautas independentes, falhas por pauta, versões e permissões próprias, e compor uma edição contendo múltiplas matérias finalizadas.

Leia integralmente a especificação v0.2, `AGENTS.md`, Bíblia, decisões, README e relatório v0.1. O chat fundador fixou a arquitetura. Você tem autonomia técnica para escolher estruturas internas, migração, interfaces simples, refatorações mínimas e testes sem devolver decisões de baixo nível.

## Trabalho executável

1. Confirme a `main` atualizada e abra **uma nova branch `codex/motor-editorial-v0.2-multipauta`**, sem reutilizar a branch de aceite v0.1.
2. Implemente identidade/persistência independentes por pauta, múltiplas fontes/revisões e limites de tentativa por pauta.
3. Refatore executores fixos da fixture para suportar ao menos três pautas, inclusive uma com bloqueio editorial e outra com falha técnica recuperável.
4. Implemente composição real de **várias matérias elegíveis** numa edição única; bloquear conclusão enquanto houver membro obrigatório pendente; permitir exclusão apenas humana auditável.
5. Atualize CLI, painel e prévia interna multipauta sem criar site final e mantendo loopback.
6. Prove migração de SQLite v2 para novo esquema, idempotência, retomadas e ausência de publicação.
7. Mantenha testes v0.1 e acrescente cobertura para os critérios v0.2. Execute e corrija a suíte; documente os resultados REAIS, sem inventar execução no Windows quando estiver em Linux.
8. Envie código, testes, fixtures e relatório numa PR nova, aberta para revisão arquitetural, **sem merge automático**.

## Segurança/limites

Não usar fontes reais, API, modelos de IA, rede externa, agendamento, login público, mídia de terceiros, publicidade, arquivo de edição real ou publicação. Não cobrar serviços. Nenhuma decisão dos blocos de concepção é inventada ou alterada. Sem alteração na `main` pelo Codex.

**Aceite:** seguir integralmente os critérios da especificação v0.2; entregar demo mostrando no mínimo três pautas independentes, uma pendente que não paralisa as demais, e edição com duas reportagens revisadas e rastreáveis. Encerrar com link do PR, testes/ambiente e limitações.

Caso a implementação encontre impeditivo real, explique-o com evidência, proponha a menor solução segura e prossiga até onde o escopo permitir.
