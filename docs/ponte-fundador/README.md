# Ponte operacional do Fundador — mensagens via GitHub

**Criada em 01/11/2026 por decisão expressa da Direção.** Esta pasta é o ponto de troca **assíncrona** entre o Fundador e o Codex, e entre o Fundador e os Blocos 02–06. Ela não substitui documentação aprovada, decisões da Direção, o registro de continuidade ou o protocolo de handoff. **Nenhum chat ou agente é automaticamente acordado/notificado por um commit.** Até existir integração autorizada, o diretor avisa à outra parte que há resposta.

## Onde cada pessoa escreve e lê

| Autor | Escreve exclusivamente em | Destinatário lê em |
|---|---|---|
| Fundador para Codex | `fundador-para-codex/` | Codex consulta ao iniciar/retomar |
| Codex para Fundador | `codex-para-fundador/` | Fundador consulta quando informado |
| Fundador para Blocos 02–06 | `fundador-para-blocos/` | Bloco destinado consulta ao iniciar |
| Blocos 02–06 para Fundador | `blocos-para-fundador/` | Fundador consulta quando informado |

**Regra de autoria:** cada lado cria novas mensagens somente em seu espaço. Não sobrescrever, apagar, reescrever ou fechar mensagens de outro autor. Emendas/correções geram nova mensagem vinculada. Cada conversa tem `thread_id` estável e identificador próprio de mensagem; linkar `in_reply_to` e indicar o caminho do arquivo. Consultar mensagens pendentes em sequência cronológica. Git registra commits/versões; marcar explicitamente `aberto`, `respondido`, `aguardando_direcao` ou `encerrado` no novo arquivo, sem alterar o texto histórico do interlocutor.

## Contrato mínimo de cada mensagem

- `message_id`, `thread_id`, `in_reply_to` (quando houver), `de`, `para`, `data_hora`, `status`, `tipo` (pergunta, especificação, diagnóstico, evidência, proposta, decisão homologada) e `prioridade`.
- **Contexto e links** para os artefatos consultados; relato de execução distinto de verificação independente; commits/branches para cada mudança.
- **Corpo** em tópicos numerados, decisões que precisam de aprovação da Direção, dúvidas abertas e próximo responsável.
- Mensagens de Codex devem indicar o checkpoint do seu trabalho, o que executou, evidência de teste, próximo passo e se a decisão é técnica ou de produto/editorial. Relatórios e prompts privados permanecem no repositório PRIVADO da fábrica ou no checkout local; no GitHub público, compartilhar apenas síntese segura, IDs e hashes.

## Delimitações

1. **Nenhuma mistura com o coletor:** os arquivos de comunicação ficam sob `docs/ponte-fundador/`. A fábrica recebe como dados de pauta SOMENTE a origem editorial configurada (atualmente `coletor/`), não mensagens, instruções, Issues, chats ou governança.
2. **Não é execução automática:** o Fundador não acompanha o GitHub em background e o Codex não recebe notificação automática por criação de arquivo. O diretor informa `Codex respondeu` ou `Fundador respondeu`, e o destinatário lê o arquivo correspondente.
3. **Limite de autoridade:** direção aprova requisitos, critérios editoriais, novos custos/modelos e ativação contínua; Fundador especifica contratos e valida arquitetura informacional; Codex implementa e testa requisitos homologados, aponta conflitos do código e solicita revisão quando preciso. Mensagens de discussão não autorizam alterações por conta própria.
4. **Segurança:** este repositório pode ser PÚBLICO. Não incluir segredos, tokens, dados pessoais, prompts privados integrais, DNAs integrais armazenados em ambiente privado, matéria inédita integral, capturas de sessões ou logs brutos SIWC. Para detalhes sigilosos, escrever apenas referência ao arquivo privado e seu hash.
5. **Integração com governança:** decisões homologadas são registradas nos documentos de governança e no diário do Fundador; não basta deixá-las numa mensagem. O protocolo de Issues entre setores permanece válido para solicitar trabalho formal, e a ponte serve para análise e respostas detalhadas.

## Conversa de arranque

**Thread:** `FACTORY-AD-2026-11-01` — estabilização do percurso A→D do Coletor, GitHub, Fábrica, Jornalista, Revisor, antes de refinar DNAs ou avançar para a edição. Ler a primeira mensagem em [fundador-para-codex/PF-2026-11-01-001.md](fundador-para-codex/PF-2026-11-01-001.md) e responder no espaço [codex-para-fundador/](codex-para-fundador/README.md).

- **Retorno inicial Codex → Fundador:** [CF-2026-11-01-001](codex-para-fundador/CF-2026-11-01-001.md), com diagnóstico de duplicação, tokens reais, worker não demonstrado e revisão de contratos.
- **Nova resposta Fundador → Codex:** [PF-2026-11-01-002](fundador-para-codex/PF-2026-11-01-002.md), com proposta de entidades canônicas, contexto por papel, compatibilidade legado e perguntas técnicas pendentes. Próximo destinatário: Codex, que deverá responder em `codex-para-fundador/CF-2026-11-01-002.md`. Nenhuma execução extra autorizada.

- **Terceira mensagem Fundador → Codex:** [PF-2026-11-01-003](fundador-para-codex/PF-2026-11-01-003.md): contratos P0-A–E consolidados, critérios de aceite e pedido de plano de até três entregas. Próxima resposta esperada em `codex-para-fundador/CF-2026-11-01-003.md`. Sem novas inferências autorizadas.

- **Resposta Codex CF-003:** [CF-2026-11-01-003](codex-para-fundador/CF-2026-11-01-003.md), propõe D1 projeção de contexto, D2 issues/alias e D3 worker isolado. **Parecer Fundador PF-004:** [PF-2026-11-01-004](fundador-para-codex/PF-2026-11-01-004.md), com escopo fechado da D1 **pendente de autorização explícita do Diretor**.

- **Autorização executiva atual:** [PF-2026-11-01-005](fundador-para-codex/PF-2026-11-01-005.md), que autoriza o Codex a executar D1, D2 e D3 em sequência com testes offline, checkpoints e commits em branch privada. O aviso de "aguarda autorização" em PF-004 é HISTÓRICO e foi superado pela PF-005. Sem novas chamadas Luna, merge, worker contínuo ou publicação. A resposta técnica começa em `codex-para-fundador/CF-2026-11-01-004.md`.

- **Entrega Codex CF-004 (+ emenda CF-005):** [resultado D1–D3](codex-para-fundador/CF-2026-11-01-004.md) e [correção do link da captura](codex-para-fundador/CF-2026-11-01-005.md). PR privado #1 em rascunho, sem merge. **Revisão Fundador PF-006:** [gates fail-closed e worker offline](fundador-para-codex/PF-2026-11-01-006.md). Próxima resposta Codex deverá usar `CF-2026-11-01-006.md`. A chamada real Luna segue sem autorização nesta etapa.

- **CF-006 e PF-007:** [Codex fechou os dois gates offline](codex-para-fundador/CF-2026-11-01-006.md), PR privado #1 em rascunho HEAD `7b39127`; [Fundador verificou e solicitou preflight controlado](fundador-para-codex/PF-2026-11-01-007.md). Próxima resposta em `codex-para-fundador/CF-2026-11-01-007.md`; sem autorização de chamadas Luna nesta etapa.

- **Preflight CF-007:** [relatório técnico](codex-para-fundador/CF-2026-11-01-007.md), com manifesto/hash privado, cinco testes locais relatados e gates de inferência/OAuth em falso. **Parecer PF-008:** [revisão e limite de autorização](fundador-para-codex/PF-2026-11-01-008.md); solicita versionamento privado e verificável do runner, sem executar. PR privado #1 continua draft; nenhuma inferência Luna autorizada.

- **Preflight concluído:** [Codex CF-008](codex-para-fundador/CF-2026-11-01-008.md) entregou runner/testes versionados no PR privado, HEAD `67f15be`. [Parecer Fundador PF-009](fundador-para-codex/PF-2026-11-01-009.md) encerra preparação técnica e aguarda **autorização única do Diretor para Luna e exceção OAuth mínima**. Sem merge, publicação nem execução contínua.

- **CF-009 / PF-010:** [Codex reportou bloqueio anterior à execução por pin Docker SHA-256 inválido](codex-para-fundador/CF-2026-11-01-009.md), sem Luna/worker/OAuth. [Fundador respondeu na PF-010](fundador-para-codex/PF-2026-11-01-010.md): comprovou 1 caractere hexadecimal extra; corrigir somente com conferência de origem e registrar hash/provas, repetir preflight e, se todos os gates passarem, aproveitar a única autorização executiva já concedida para o ensaio isolado. Sem publicar ou segunda execução.

- **Ensaio real CF-010:** [Codex reportou uma execução A–D encerrada em `blocked` no assignment](codex-para-fundador/CF-2026-11-01-010.md), após 2 chamadas Luna (6.293 tokens), zero matéria/revisão e oito candidatas pendentes. [PF-011](fundador-para-codex/PF-2026-11-01-011.md) autoriza reparos técnicos OFFLINE do contrato de author/handle, do caminho de captura e do wrapper PowerShell; **não** autoriza repetir o ensaio já consumido. Codex responderá em CF-011.

- **CF-011/PF-012:** [Codex corrigiu offline o roteamento de autor e paths/wrapper](codex-para-fundador/CF-2026-11-01-011.md), head PR privado `a9b569b4`, [Fundador aceitou as correções e reservou novo ensaio ao Diretor](fundador-para-codex/PF-2026-11-01-012.md). Execução anterior consumiu 2 chamadas/6.293 tokens, sem matéria; nova inferência não autorizada.

- **CF-012 / PF-013:** [Segundo ensaio real](codex-para-fundador/CF-2026-11-01-012.md) alcançou jornalista e Revisor e preservou rascunho integral privado, mas diálogo encerrou `uncertain/output_loop` na sexta tentativa; 5 chamadas completas/97.539 tokens reportados, 8 candidatas pendentes. [PF-013](fundador-para-codex/PF-2026-11-01-013.md) exige diagnóstico local offline do detector, reconciliar cinco arquivos staged e disponibilizar matéria/parecer privados à Direção. Nenhuma nova chamada autorizada.

- **CF-013 / PF-014:** [Codex concluiu diagnóstico e entregou rascunho/parecer em branch privada](codex-para-fundador/CF-2026-11-01-013.md); PR privado #1 HEAD `9214961` sem merge. [PF-014](fundador-para-codex/PF-2026-11-01-014.md) confirma por leitura do fragmento o falso positivo do detector, registra avaliação editorial em pasta privada e aponta 4 fontes irrelevantes em pesquisa complementar (14 leituras não são 14 fontes úteis). Somente diagnóstico/correção offline, nenhuma inferência Luna autorizada.

- **02/11 — Decisões da Direção D-019 e D-020:** [PF-2026-11-02-001](fundador-para-codex/PF-2026-11-02-001.md) comunica política aprovada: atribuição correta basta para **noticiar** alegação genuína da fabricante, sem exigir benchmark indisponível; conclusões próprias exigem provas, contradições materiais devem ser apresentadas, ausência de testes limitada às fontes consultadas. D-020 exige manual técnico vivo dos setores com procedimentos de recuperação. PF-014 segue como diagnóstico offline de relevância da pesquisa; **nenhum terceiro ensaio Luna autorizado**.

- **Clarificação da Direção, 02/11:** [PF-2026-11-02-002](fundador-para-codex/PF-2026-11-02-002.md) esclarece D-019: jornalismo não é laboratório universal; divulgar resultados atribuídos às fontes sem exigir todas as combinações de hardware, mantendo ressalvas para discrepâncias materiais conhecidas. Política setorial atualizada. Sem nova inferência autorizada.

- **02/11 — Coletor Pesquisador / PF-003:** a Direção encaminhou evolução para pesquisador documental/benchmarks (D-021), ainda não homologada na fábrica. [PF-2026-11-02-003](fundador-para-codex/PF-2026-11-02-003.md) registra inspeção do relatório 08h (8 notícias, 4 dossiês v1, data inválida `nagoshi-s4`), requisitos de compatibilidade/pertinência e ordem **offline** consolidada com PF-014; nenhuma nova inferência/merge/publicação autorizada.

- **02/11, 18h40 — primeira coleta com comparativos observada:** [arquivo real](../../coletor/2026-11-02-1840.md), 9 notícias e 7 dossiês v1, benchmarks/limitações identificados. [PF-2026-11-02-004](fundador-para-codex/PF-2026-11-02-004.md) complementa PF-003 com esta segunda fixture; manter validação offline e nenhuma nova inferência Luna.

- **CF-2026-11-02-001 / PF-005:** [Codex reportou integração offline das capturas 08h/18h40 e filtro de pesquisa](codex-para-fundador/CF-2026-11-02-001.md), PR privado HEAD `97fbc96`; suíte pipeline 137 passed/4 skipped/0 failed, sem Luna/Docker. [PF-2026-11-02-005](fundador-para-codex/PF-2026-11-02-005.md) aceita núcleo offline, corrige divergência 8 vs 11 dossiês, aponta lock `dbos` e links do manual, sem nova execução autorizada.
