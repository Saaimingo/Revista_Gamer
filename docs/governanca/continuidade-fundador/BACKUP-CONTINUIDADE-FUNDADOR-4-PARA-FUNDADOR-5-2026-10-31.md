# REVISTA BACK — PASSAGEM FORMAL: FUNDADOR 4 → FUNDADOR 5

**Data:** 31/10/2026 (Brasil)  
**Origem:** memória oficial do Fundador 4 e conferência pontual de repositórios pelo Fundador 5.  
**Status:** transição assumida; **nenhuma nova inferência, automação, publicação, código editorial, deploy ou alteração de prompt foi autorizada por este documento**.

> **Ponto de retomada:** o coletor entregou em 31/10 às 18h40 a primeira coleta com dossiês de inteligência editorial (`revista-back.coletor.v1`), mas a branch remota da fábrica **ainda não demonstra ingestão desses dossiês**. A próxima missão conhecida do Codex é adaptar o parser e os contextos de redação/revisão para consumir integralmente esses dossiês, com compatibilidade anterior, testes técnicos normais e sem rodar o backlog. Em paralelo, o primeiro teste real com Luna foi tecnicamente bem-sucedido, mas **editorialmente bloqueado**, e o mandato/prompt efetivo do revisor ainda precisa de auditoria. Não confundir um pedido do diretor ao Codex com entrega concluída.

## 1. Documentos de leitura obrigatória

1. [Memória cronológica do Fundador 4](REGISTRO-FUNDADOR-4-2026-10-31.md), incluindo as seções recentes sobre dossiês e revisor.
2. [Protocolo permanente de memória](PROTOCOLO-MEMORIA-CONTINUA.md).
3. [Backup Fundador 1 → 2](../BACKUP-CONTINUIDADE-FUNDADOR-2026-10-23.md) e [Fundador 2 → 3](../BACKUP-CONTINUIDADE-FUNDADOR-2-PARA-FUNDADOR-3-2026-10-27.md).
4. [Bíblia](../BIBLIA-DO-PROJETO.md), [Decisões](../DECISOES.md), [Status](../STATUS-GERAL.md), [handoff setorial](../../operacao/PROTOCOLO-HANDOFF.md), [AGENTS](../../../AGENTS.md). **Atenção:** DECISOES/STATUS contêm retratos antigos e não substituem decisões mais recentes e documentação da factory.

## 2. Estrutura operacional e responsabilidade

- **Revista Back** é a marca operacional; repositório principal de governança e coleta: [Saaimingo/Revista_Gamer](https://github.com/Saaimingo/Revista_Gamer), **público**, branch `main`.
- **Factory Censurado adaptada**: [Saaimingo/revista-back-factory](https://github.com/Saaimingo/revista-back-factory), **privado**, branch `codex/revista-back-factory-v0.1.4-20261030`. HEAD **verificado em 31/10**: `312dbd2cecb65a3f01400118d1a5d4d2a79c4177`. O histórico original do Censurado e a licença MIT estão preservados.
- O Codex é o **engenheiro que desenvolve e integra software**; jornalistas, revisor e outros papéis são agentes configurados e invocados pela factory. Não usar Codex como operador manual cotidiano da redação.
- Três jornalistas cadastrados segundo execução relatada: `ranzinza` (Arlindo Carranca), `beto-cartucho` (Beto Cartucho), `nina-prisma` (Nina Prisma). DNAs e âncoras aprovados pelo Bloco 02, sem improvisar identidades.
- Docker Compose com perfil `factory`; backend `publish`, SQLite/DBOS, fila serial, pesquisa web, gate de revisão e arquivamento privado após aceite. **Operação 24/7 e migração VPS não estão validadas**. Farol é outro projeto, não o painel desta revista.

## 3. Provas reais e limites

- SIWC/OpenAI: login oficial `authenticated:true`, `plan_usage_scope:true`; catálogo mostrou `gpt-6-luna` e outros. A ponte Windows/Docker foi corrigida no commit da factory `312dbd2`. Não presumir elegibilidade de futura VPS comercial apenas do sucesso local.
- Primeiro teste real com `gpt-6-luna` e `reasoning_effort=max`, **9 inferências reais**, sem fallback/retry, um item processado: hardware System76/Thelio Prime. `run_id=rb-05a34e3a8ddc9ff622e862e6`, `story_id=story-5fa6ee7b30046e5f4ecf20f4`. Três versões do Carranca e três avaliações do revisor; **resultado final `blocked`**, sem matéria aprovada/publicada. Fila relatada após teste: **1 bloqueada e 38 pendentes**. Não repetir chamada por conta deste resumo.
- Investigação do revisor registrada na memória do Fundador 4: revisor/gate e loop de até 3 avaliações vêm da arquitetura Censurado adaptada pelo Codex; **o prompt de produção em `factory-config/` é local/privado e não foi lido pelo Fundador**. A revisão real pode depender de instruções diferentes das do código público. Não atribuir causa sem comparar drafts, reviews, pesquisa e prompt ativo; discutir mandato e critérios com a direção.
- A matéria System76 teve dúvida de preços e versões diferentes do produto; misturar gerações é hipótese a investigar, não causa confirmada. Ausência de benchmarks num produto não lançado não deve, por si, ser confundida com falha de apuração numa reportagem de anúncio.

## 4. Coletor: última entrega e contrato a integrar

- Coleta confirmada no [arquivo de 18h40](https://github.com/Saaimingo/Revista_Gamer/blob/main/coletor/2026-10-31-1840.md), commit `f974166458fc907037c2583ec24a48ebb92bfce1`, blob `01101850f5e099aed0058690d08f03f37bdfdf53`.
- **9 notícias**, **12 pautas acompanhadas** e **3 dossiês**; JSON `revista-back.coletor.v1` parseado pelo Fundador 4: 11 referências de fontes, 10 alegações estruturadas, 6 perguntas em aberto, vínculo por `linked_news_urls`.
- Diretriz do diretor: **extrair o máximo de contexto público relevante** no coletor, com fontes rastreáveis, antecedentes, divergências, evolução e lacunas, **sem limites arbitrários de profundidade**; não redigir matéria no coletor. O jornalista interpreta e escreve, pesquisa adicional somente quando precisa; o revisor verifica. Não criar nova esteira nem piloto editorial paralelo.
- **Dependência:** Codex deve interpretar o JSON dos dossiês e ligá-los às notícias, preservando boletins antigos, antirrepetição, proveniência e todos os campos úteis para jornalista/revisor. Este pedido foi formulado na conversa, mas **não se comprovou commit posterior na factory remota**.

## 5. Visão da direção e prioridades

1. **Concluir e homologar revista/fábrica** antes de expandir. Revista digital é o produto central; redes sociais (Facebook/Instagram) devem atrair leitores e são prioridade próxima à revista.
2. **Painel de comando próprio da Revista Back**, não do Farol: acompanhar cada etapa e intervir conversando com jornalistas, revisor, diagramador, montagem, imagens e acervo; permitir orientar, pausar e retomar, com auditabilidade. Não implementado nem completamente especificado.
3. Podcast inicialmente em áudio, depois audiovisual com personagens, YouTube e portal ampliado são **possibilidades futuras**, sem compromisso de execução/custos agora. Expansão depende da sustentabilidade da revista.
4. Visual/folheação e identidade definitiva pertencem ao Bloco 03. Demonstrações recentes do Codex não atenderam ao padrão visual aprovado; não confundir leitor piloto com homologação de layout.
5. Acervo de imprensa, autorizações de imagem e separação entre editorial e publicidade seguem obrigatórios; nenhuma publicação/deploy resulta automaticamente de aprovação de revisão.

## 6. Riscos e ações seguintes sem autorização implícita

- **Codex:** confirmar se já recebeu/executou a instrução de ingestão de dossiês; revisar commit e testes antes de declarar a integração concluída.
- **Direção/Fundador 5:** continuar discussão e eventual auditoria read-only dos artefatos System76 e **prompt ativo do revisor**; definir critérios de correção e direito de justificativa entre jornalista/revisor. Não reconstruir sem diagnóstico.
- **Operação:** testar recuperação real após reinício, gastos/limites SIWC, transição VPS e eventual watchdog **quando autorizados**. Não iniciar `--watch` com backlog por dedução.
- **Governança:** atualizar memória continuamente após cada deliberação/resultado do Codex, com prova de gravação no GitHub. Preservar backups anteriores e manter o próximo Fundador preparado. **Não depositar segredos ou textos editoriais privados no repo público**.

## 7. Checagem realizada na transição

Em 31/10/2026, Fundador 5 verificou por integração GitHub:
- Repo público `Saaimingo/Revista_Gamer`, `main` anteriormente em `295806387a4a66420f159cc81690194f8e1825b4`.
- Repo privado `Saaimingo/revista-back-factory`, HEAD `312dbd2cecb65a3f01400118d1a5d4d2a79c4177`.
- Pasta `docs/governanca/continuidade-fundador/` e conteúdo da memória do Fundador 4.
- Coleta estruturada `2026-10-31-1840.md`; **nenhum arquivo de execução local privado foi acessado** nesta transição.

**Orientação ao Fundador 5:** assuma o processo pelo ponto concreto mais recente. A passagem de bastão não liga a fábrica, não concede acesso ilimitado ao Luna e não altera o status `blocked` da pauta.
