# Revista Back — Registro de continuidade do Fundador 4

**Atualizado em:** 31/10/2026 (Brasil). **Natureza:** registro de direção/continuidade, a ser atualizado após cada novo marco. **Origem:** conversas do Fundador 4, saídas do diretor, relatórios do Codex e verificações pontuais em GitHub. **Não é autorização para execução**.

> **PONTO DE PARADA:** primeira execução real, controlada, de uma pauta na nova fábrica Censurado + GPT-6 Luna concluída tecnicamente; reportagem de Arlindo Carranca **bloqueada pelo reviewer após três avaliações**. O diretor decidiu **não enviar mais prompts ao Codex naquela noite**; debateu necessidade de diagnóstico do diálogo jornalista–revisor, definição de escopo e incertezas. Próximo passo é **auditoria somente de leitura dos artefatos** da execução, sem inferências novas ou retomada automática. O diretor pediu agora a regra permanente de memória do Fundador. Nada foi publicado.

## A. Arquivos anteriores e contexto herdado

- [Backup Fundador 1 → Fundador 2, 23/10](../BACKUP-CONTINUIDADE-FUNDADOR-2026-10-23.md) e [Backup Fundador 2 → Fundador 3, 27/10](../BACKUP-CONTINUIDADE-FUNDADOR-2-PARA-FUNDADOR-3-2026-10-27.md). **Não os substituir**.
- O Fundador 3 herdou a reestruturação da antiga fábrica: manter componentes úteis, reduzir burocracia e substituir mocks por **ensaios reais**, preservando a decisão humana de publicar. A base conceitual das cinco funções era captador, classificador/roteador, jornalistas, revisor e montagem; montagem/identidade visual ainda não estava homologada. Não retornar automaticamente à ENG-CODEX-012 congelada.
- A marca operacional é **Revista Back**, embora o repo público mantenha o nome `Revista_Gamer`. O repositório principal contém governança/setores, **não** é sinônimo do código da nova factory.
- Os jornalistas aprovados são `ranzinza` = Arlindo Carranca (hardware), `beto-cartucho` = Beto Cartucho (games) e `nina-prisma` = Nina Prisma (mods/comunidades e temas amplos). **DNA e visuais não devem ser improvisados**: consultar branches `bloco-02/ranzinza-dna-editorial-v01`, `bloco-02/gamer-dna-v02` e `bloco-02/continuidade-checkpoint-2026-10-24`; documentos antigos da `main` podem estar desatualizados. Persona não é um processo/modelo exclusivo.

## B. Decisão de arquitetura sob o Fundador 4

- **Rumo:** aproveitar a base Python existente [hec-ovi/censurado-web-brain](https://github.com/hec-ovi/censurado-web-brain) como motor de redação e o backend Go [hec-ovi/censurado-web-backend](https://github.com/hec-ovi/censurado-web-backend) para cadastro/persistência, mantendo as personas próprias. Inspirações conceituais de Umbruch AI News Desk (personas) e Machine Herald (proveniência), sem misturar stacks indiscriminadamente.
- Histórico de ensaios: Qwen 3.5 9B/Ollama não atingiu o nível de apuração esperado (saídas com URLs e detalhes não confiáveis). O alvo aprovado para ensaio real passou a ser **`gpt-6-luna` com `reasoning_effort=max`**, via adaptador SIWC, **sem fallback**. Não tratar uso do plano ChatGPT como API genérica irrestrita.
- Fábrica composta por coleta do GitHub `main:coletor/`, triagem, designação de persona, pesquisa complementar, redação, revisão com até **três avaliações/versões**, fila/journal SQLite/DBOS e **acervo privado só para material aprovado**. Publicação pública e diagramação **não estão liberadas**.
- Optou-se por **integrar a factory como serviço no Compose existente**, sob perfil `factory`, sem subir outro sistema editorial paralelo. Ligar `--watch` com backlog não é ensaio controlado.
- Evidência prévia de simulação (não confundir com homologação): um ensaio offline relatou 9 entradas, 1 aprovado simulado, 2 bloqueados e 6 descartados, 27 chamadas Luna **simuladas**. A primeira matéria real só ocorreu depois das correções OAuth relatadas abaixo.

## C. Preparação local Windows + Docker, 30–31/10

**Ambiente do diretor**, caminhos históricos (não supor acesso futuro ao disco):
- Checkout: `D:\Censurado-ollama-test`. Branch local `codex/revista-back-factory-v0.1.4-20261030`.
- Backend original clonado em `D:\censurado-web-backend`. Arquivo `deploy/Dockerfile.publish` presente.
- Docker Desktop Linux Engine e Docker Compose operacional; Git Bash disponível. `bootstrap.sh` oficial executado; `.env` e `keys.json` privados, não versionados; senha padrão do painel trocada antes da inicialização.
- `docker compose up -d publish`. Serviço `censurado-publish` em `127.0.0.1:8082` (porta interna 8080). `GET /healthz` retornou `HTTP 200 ok`. `GET /authors` autenticado inicialmente retornou `{"authors":[]}`.
- Host networking validado de contêiner temporário: `docker run --rm --network host busybox:1.37 wget -qO- -T 5 http://127.0.0.1:8082/healthz` → `ok`.
- Copiado `automation/pipeline/factory.config.example.json` para `factory-config/factory.config.json` (privado/ignorado no Git). Prompts adicionais foram preparados em `factory-config/prompts/`; nenhum deve ser publicado automaticamente.
- Painel real acessível em `http://127.0.0.1:8082/`. Abas Artigos/Autores/Fontes estavam vazias. O código original oferece API `POST /authors`, embora a interface de lista de autores não apresente criação direta; decisão: **delegar ao Codex a integração completa**, em vez de cadastrar manualmente um a um.
- Codex relatou 83 testes offline/simulados (48 pipeline, 14 Compose, 21 SIWC), persistência de bind mount `/data`, pesquisa web real lendo uma página `nintendo.com` e coleta somente leitura de 6 arquivos/39 leads. Importante: **retomada real do worker DBOS após reinício NÃO foi validada**.
- Codex relatou registro e conferência de SHA-256 dos estilos dos três autores no backend; todos elegíveis no roster, `deleted=false`. Não subir imagens de perfis nem inventar fontes. `GET /sources` permanecia vazio; pesquisa da factory usa `websearch` diretamente. Hashes de estilo relatados:
  - Carranca: `6d39c1cf5284426eec19d6e996de721b26bd1a9b6a57a959e41a0df99793d665`
  - Beto: `ae1ca4223e5d430562b704901dfec7f98d0e194dd364bfb40b9118bf11335274`
  - Nina: `ab744f7bb434f6b00c62a3b453caa6280e45668a5e5e3e13bf20916f8c802805`
- As alterações locais do Codex em `source_images/__init__.py`, `adapter_cli.py`, `batch.py`, `photo_command.py`, `photographs.py`, `machineherald_preview.py` e `local-tests/` foram **preservadas** fora de stage; nunca usar reset/limpeza destrutiva por reflexo.

## D. Repositório próprio e preservação

- Criado sob autorização do diretor: **[Saaimingo/revista-back-factory](https://github.com/Saaimingo/revista-back-factory)**, **PRIVADO**. Não confundir com [Saaimingo/Revista_Gamer](https://github.com/Saaimingo/Revista_Gamer), **PÚBLICO**.
- Branch da fábrica: `codex/revista-back-factory-v0.1.4-20261030`; histórico original e licença MIT preservados; remoto `origin` do criador sem push. Publicado inicialmente o commit `48515ed30476e0d4338ae8b02a5f69840ca5ceaa`, depois `87fe0b667808fa4460254e8cc2ae47244a488ef4` (preparo SIWC), e `312dbd2cecb65a3f01400118d1a5d4d2a79c4177` (recuperação da ponte). **Último commit da factory relatado/checado nesta fase: `312dbd2`**.
- Codex relatou auditoria dos 251 commits/3.211 objetos/1.697 blobs transportados, preservação de `LICENSE` MIT (blob `4be9b65cfb83d54a0cb69167d209ef88c98fbac8`) e ausência de credenciais nos arquivos publicados. Credenciais OAuth, bancos, prompts privados, logs e checkpoint local **não** estão no remoto.
- Snapshot anterior `D:\Revista-Back-factory-snapshots\RB-FACTORY-P1-v0.1.3-20261030.zip` com hash relatado `8DABD229848CDC790CA5DEB24B4CA139E19E1BBBB509650D76DE8CAC95590166`. Checkpoint local do Codex: `D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md`. Não supor sincronização deste documento privado com GitHub.

## E. Preparação e autenticação real SIWC, 30–31/10

1. A primeira versão OAuth tinha três riscos: navegador não encaminhado adequadamente ao Docker, registro do `client_id` persistido tarde demais e nome do agente `Censurado Web Brain`, em vez da aplicação específica. A direção escolheu **Revista Back Factory** como nome da integração.
2. Commit `87fe0b6`: ponte Windows–Linux com navegador e callback local, cliente OAuth/OIDC e PKCE, validações de identidade/escopos, persistência segura por permissões POSIX (JSON protegido por filesystem, **não criptografado**), adaptador `/responses` com `store:false`, `stream:true` e consulta ao catálogo. Codex relatou 25 testes aprovados, 2 POSIX ignorados no Windows.
3. Primeira tentativa real abriu `auth.openai.com` e a aplicação foi reconhecida. E-mail da OpenAI confirmou **permissões de identidade**, inclusive informação sobre plano ChatGPT; isso sozinho não provou tokens Linux nem inferência. Retornou `SIWCError: browser_bridge_unavailable`. Verificação `status` no contêiner: `connected=false`, `plan_usage_authorized=false`, `registration_pending=false`.
4. Commit `312dbd2`: cliente da ponte passa a ignorar proxies de ambiente no tráfego local, recuperar falhas temporárias de rede e respostas 5xx, abrir janela de forma idempotente. Codex relatou 26 testes aprovados, 2 POSIX ignorados, incluindo cliente Docker Linux contra ponte Windows com falhas sintéticas.
5. **Segunda tentativa real bem-sucedida** (diretor executou): `py -3.11 automation\pipeline\windows_siwc_login.py login` → `{"authenticated":true,"plan_usage_scope":true}`. Consulta `catalog` retornou, entre outros, **`gpt-6-luna`**, `gpt-6-sol`, `gpt-6.1-sol`, `gpt-6.1-terra`, `gpt-6-astra`. Existência no catálogo prova acesso enumerável, **não qualidade editorial nem licença universal de uso em qualquer hospedagem**.
6. O procedimento oficial de elegibilidade SIWC para futura operação remota/comercial segue **pendente de verificação específica**. Login local e eventual VPS/comercial não são a mesma autorização; não presumir que Plus/Free equivale a API ilimitada nem que uma VM está aprovada.

## F. PRIMEIRO ENSAIO REAL COM GPT-6 LUNA: 31/10/2026

**Origem dos resultados abaixo:** relatório do Codex transmitido ao Fundador 4; o Fundador não leu ainda os arquivos completos de draft/review. Status: **integração real executada, qualidade editorial NÃO homologada**.

- Configuração: somente `gpt-6-luna`, `reasoning_effort=max`, sem fallback, `attempt=1` em cada chamada. Runtime Linux relatou `connected=true` e `plan_usage_authorized=true`; backend `HTTP 200`.
- `--poll-only` carregou **39 candidatos** na fila sem inferências; comando one-shot (sem `--watch` ou `--drain-once`) processou somente o próximo item na ordem persistida:
  `docker compose --profile factory run --rm --no-deps --entrypoint python3 factory automation/pipeline/run.py factory --config /etc/censurado-factory/factory.config.json`.
- **Pauta:** “System76 anuncia Thelio Prime compacto com Ryzen 9000 e opção de GPU dedicada”.
- `run_id`: `rb-05a34e3a8ddc9ff622e862e6`. `story_id`: `story-5fa6ee7b30046e5f4ecf20f4`.
- **Jornalista:** Arlindo Carranca (`ranzinza`). Triagem: avançar. **Estado final: `blocked`**, pelo reviewer.
- **Nove chamadas REAIS ao GPT-6 Luna, HTTP 200**: triagem, atribuição, planejamento de consulta, três versões de rascunho e três avaliações. **Sem retry automático ou outro modelo.** Pesquisa inicial e uma complementar, com fontes System76 e VideoCardz; divergência de evidência sobre valores.
- Reviewer 1 pediu atribuição rigorosa a VideoCardz/System76, data prevista e ressalvas sobre disponibilidade/preço no Brasil.
- Reviewer 2 pediu verificar qual configuração correspondia a **US$ 1.599** e ausência de review/benchmark independente, acionando pesquisa complementar e nova versão.
- Reviewer 3 manteve divergência sobre **US$ 1.599/US$ 1.589/US$ 1.499**, e exigiu identificar alegação de “jogos em 2K” como **marketing da fabricante**, não teste próprio. Limite das três avaliações atingido; não houve quarta versão.
- Título da última versão **rejeitada**: “Thelio Prime: System76 anuncia desktop de 11 litros, mas não identifica a configuração de US$ 1.599”.
- Fila após teste: **1 bloqueado + 38 pendentes**. **Zero matérias aprovadas, zero publicações, zero montagem de edição.**
- Checkpoints, journal DBOS, evidências e textos privados em `D:\Censurado-ollama-test\data\factory\runs\rb-05a34e3a8ddc9ff622e862e6\`, com arquivos `assignment.txt`, `draft.txt`, `review.txt`, `draft-respin-1.txt`, `review-respin-1.txt`, `draft-respin-2.txt`, `review-respin-2.txt`, `source-evidence.json`. Codex relatou 58 arquivos, hash do conjunto `e168de8f20bf57a4e402c13eaa3b8755f7e9b6ff7fdf2d7d207b31bb47286107` e integridade SQLite `ok`.
- **Restrição:** não retomar/reciclar pauta bloqueada nem iniciar `--watch` sem autorização expressa. Ninguém leu/aprovou a matéria completa durante esta conversa. O primeiro ensaio atestou cadeia técnica, não o padrão de jornalismo.

## G. Debate da direção após o primeiro ensaio — ainda não implementado

A direção comemorou o funcionamento real da esteira, mas criticou a possível fragilidade do **diálogo jornalista ↔ reviewer**. Assuntos debatidos, a serem **investigados, NÃO tratados como correção já aprovada ou implementada**:

1. O jornalista deve poder **justificar, com fontes e delimitação de escopo,** por que a matéria é só sobre um modelo ou compara versões da mesma linha; não misturar gerações ou configurações como se fossem equivalentes.
2. O reviewer deve devolver correções **explicativas e acionáveis**, não só “negado”: afirmar qual trecho é problemático, qual fonte/evidência o contradiz, como pesquisar ou atribuir e o que faltaria para aceitar; distinguir indisponibilidade de provas de afirmação sem fundamento.
3. O jornalista precisa reconhecer quando faltam evidências e **pesquisar novamente**, ou registrar honestamente que não há benchmark porque o produto ainda não foi lançado. Uma **notícia de anúncio** não deve receber automaticamente as mesmas exigências de um **review com testes**.
4. Deve existir espaço para **contestação fundamentada** do jornalista se o reviewer estiver interpretando mal a fonte. Não criar debate infinito; preservar as três avaliações até nova decisão.
5. Uma hipótese levantada pelo Fundador: confusão entre páginas de **modelos/gerações distintos do Thelio Prime** e seus preços. **Não confirmada por leitura dos arquivos do run**. A fonte do valor `US$ 1.589` precisa ser rastreada. Não atribuir erro definitivamente a nenhum agente antes de examinar evidências.

**Estado do pedido de auditoria:** Fundador sugeriu prompt ao Codex para análise **somente de leitura** de drafts/reviews/evidências, sem novas chamadas; o diretor decidiu **adiar** o envio por cansaço e horário de trabalho no dia seguinte. Isso não autoriza disparo automático. Não alterar prompts ou engine até saber se falhou pesquisa, Carranca, reviewer, instrução de revisão ou definição da pauta.

## H. Outros setores e dependências: contexto, não novas aprovações

- **Visual Bloco 03:** o diretor identificou em demonstração do Codex uma identidade diferente dos protótipos aprovados; em especial, menu hambúrguer **fora da área da revista**, ameaçando o uso no celular. Pedir especificação visual precisa e validação por telas no setor; não homologar a demonstração nem mudar projeto visual pelo fato de a factory funcionar.
- **Bloco 05 Acervo:** preferência por kits de imprensa/publishers oficiais e créditos ao titular original, com limites de uso editorial e sem converter conteúdo de imprensa em licença comercial automática. Direitos e imagem só entram na publicação após aprovação própria.
- **Bloco 06 Comercial:** marca Revista Back, Facebook/Instagram institucionais criados e Metricool conectado; verificar status corrente nos registros setoriais antes de afirmar que painel/Inbox/identidade social estão completos. Monetização não deve alterar independência editorial.
- **Captador:** registros de coleta no repo da revista `main:coletor/`; rotina indicada na continuidade do projeto de 08h00 e 18h40 (Brasil) e monitoramento de notícias em evolução/rumores; conferir a tarefa agendada efetiva e não duplicar agendamentos por suposição.
- **Futuro VPS:** ainda não implantada; nenhuma tarefa de deploy ou operação 24/7 foi autorizada pelo ensaio.

## I. Próximas decisões e prioridades (sem autorização implícita)

1. **Primeiro:** abrir/ler integralmente o dossiê da execução real (três drafts, três reviews, evidências) e fazer auditoria de fatos e comunicação. Pode ser delegada ao Codex **após decisão do diretor**, preferencialmente somente leitura e sem novas chamadas. Não declarar legítima nem excessiva a revisão sem ler artefatos.
2. Decidir ajustes de escopo da pauta, formato da devolutiva do reviewer, direito de justificativa e tratamento de incertezas, respeitando DNA original dos personagens. Registrar aprovação antes de mexer no motor.
3. Preparar **um segundo ensaio real com uma pauta aprovada pelo diretor**, quantidade/limite de chamadas definidos, sem `--watch` nem processamento dos 38 pendentes por acidente.
4. Testar retomada real do worker/DBOS após reinício, proteção de dados, provas de uso SIWC na hospedagem pretendida e regras de custo/quota.
5. Tratar **montagem/identidade visual** separadamente com Bloco 03; não confundir produção de draft com publicação de revista.
6. Manter esta memória atualizada **após cada nova decisão, teste ou handoff**, inclusive se o Codex apenas relatar erro. Ao esgotar o chat, escrever backup formal Fundador 4 → Fundador 5.

## J. Quem prevalece e o que NÃO está autorizado

**Hierarquia:** decisão explícita mais recente do diretor → contratos/identidades aprovados do setor → evidência verificada de implementação → esta memória. Divergências exigem checagem, não interpretação silenciosa.

**Não autorizado por este registro:** inferência adicional, reprocessamento da pauta bloqueada, inicio automático/`--watch`, despesa, publicação de qualquer artigo, montagem de edição, fusão de branches, reescrita de DNA, alteração de visual, troca de modelo, uso indiscriminado de imagem ou deploy VPS.

**Nota de confiabilidade:** muitas contagens e hashes operacionais são **relatos do Codex transmitidos à conversa**, não auditoria independente dos arquivos locais. Commits de correção e visibilidade do repo privado foram verificados pontualmente via GitHub. O repositório principal é público e nunca deve receber os textos privados da reportagem, tokens ou registros OAuth.


## K. Diretriz multicanal e painel único de comando — conversa de 31/10/2026

**Origem:** fala direta do diretor ao Fundador 4, após o primeiro ensaio real da factory. **Status:** visão estratégica ratificada pela direção; recursos e fases futuras **não implementados** e sem liberação de engenharia. A formalização técnica do painel ainda será debatida.

### Propósito do painel

O diretor deseja um **painel próprio da operação Revista Back**, independente do projeto Farol. Esse painel deve mostrar o percurso integral de cada pauta/processo e seus estados, evidências, revisões, bloqueios, pendências e agentes responsáveis. Deve permitir **intervenção humana contextual a qualquer momento autorizado**, não somente após um bloqueio, inclusive quando o diretor julgar uma pauta relevante mas incompleta, identificar falta de contexto ou quiser compreender uma divergência.

O conceito abrange conversas/interação com os **jornalistas** (Arlindo Carranca, Beto Cartucho, Nina Prisma), **revisor**, **diagramador/montagem** e futuras funções de **acervo de imagens e vídeos**. O debate aberto inclui se a interação poderá ocorrer também fora de tarefas ativas; **não há decisão final** sobre o mecanismo de chat, controle de estados, limites de pausa ou regras de retomada. Não prometer um painel implementado pelo fato de existir um backend administrativo do Censurado.

**Exemplo ilustrativo:** no ensaio System76, o diretor gostaria de poder abrir o segundo ciclo de revisão, visualizar argumentos/evidências, conversar com jornalista e revisor, delimitar o escopo ou pedir pesquisa adicional **antes** do bloqueio terminal. É uma capacidade pretendida do futuro painel, **não função atualmente comprovada**.

### Prioridades e evolução dos canais

1. **Revista digital:** produto editorial central, prioridade imprescindível e primeira frente de produção.
2. **Redes sociais institucionais (Facebook e Instagram):** prioridade **próxima/imediata**, funcionando como principal vetor de atração de público à revista e apoio futuro à monetização; integrar operação e resultados ao painel quando houver capacidade real. As contas já foram criadas, mas não presumir fluxos/editoria/comercial homologados.
3. **Podcast em áudio:** atrativo **futuro**, não demanda de implementação agora; vozes e formato devem ser discutidos e validados no momento oportuno.
4. **Podcast audiovisual com personagens reconhecíveis:** **evolução posterior** ao áudio, com representações de Beto Cartucho, Arlindo Carranca e Nina Prisma; exige arte/movimento/voz/identidade e direitos consistentes.
5. **YouTube:** frente audiovisual **posterior**, aproveitando o conteúdo audiovisual e a materialização visual dos personagens. Não presumir canal ou produção já disponíveis.
6. **Site/presença web:** ampliação natural do acervo/canais, mas com formato e sequência ainda a precisar de definição. Distinguir **site institucional adicional** da **experiência web de leitura**, necessária para distribuir a revista digital prevista na arquitetura.

**Princípio central:** uma **única operação editorial**, com pesquisa/fatos/memória reaproveitáveis de forma rastreável, pode futuramente alimentar revista, posts sociais, podcasts e vídeo, mas cada canal terá adaptação, direitos, revisão, métricas e aprovação específicos. Não assumir que o mesmo motor, sem adaptação, já produz todos esses formatos. O painel único reduz dispersão e permite visão consolidada de tarefas, resultados e decisões.

**Relação com Farol:** são projetos separados. O painel descrito pertence exclusivamente à Revista Back; o Farol poderá futuramente supervisionar o projeto em nível superior. Não misturar bancos, interface ou governança por antecipação.

### Distinção entre decisão e execução

- **Direção ratificada:** visão de controle centralizado, intervenção contextual, prioritização da revista + redes sociais, expansão gradual posterior para áudio, audiovisual e YouTube.
- **Pendente:** requisitos funcionais detalhados, interface, permissões de intervenção, estados/retomada, integrações com redes, roteiro de expansão e local/forma do site adicional.
- **Não autorizado:** iniciar Codex para construir painel/podcast/YouTube, abrir canais, modificar a fábrica ou criar nova pasta de ideias futuras **neste momento**. O diretor mencionou que pedirá **posteriormente** uma pasta de iniciativas futuras; aguardar solicitação explícita.


## L. Debate sobre enriquecimento do coletor e handoff para a fábrica — 31/10/2026

**Origem:** conversa do diretor com Fundador 4 após ensaio System76. **Status:** hipótese de melhoria e proposta de conversa com Bloco Coletor; **NÃO aprovada implementação**, alteração de prompt ou reprocessamento de pauta.

O diretor sugere conversar diretamente com o responsável pelo captador para investigar **até onde o coletor consegue entregar contexto factual**, em vez de apenas notícia/título/link/resumo; o objetivo é fornecer ao jornalista um dossiê inicial mais útil e reduzir perda de contexto na entrada da fábrica. O coletor já é responsável por antirrepetição e acompanhamento de rumores, anúncios, jogos e desmentidos, conforme trabalho anteriormente autorizado.

**Conferência do Fundador em código e arquivo público nesta rodada:**
- Arquivo [coletor/2026-10-31-0800.md](https://github.com/Saaimingo/Revista_Gamer/blob/main/coletor/2026-10-31-0800.md) reúne **8 notícias novas e radar de 12 pautas**; cada entrada de notícia inclui **resumo factual, URL, data/fonte e indicação de acesso**. Não é apenas lista de links.
- No repo privado [revista-back-factory](https://github.com/Saaimingo/revista-back-factory), branch §codex/revista-back-factory-v0.1.4-20261030§, o parser §automation/pipeline/src/collector.py§ reconhece os campos §title§, §category§, §discovery_source§, §source_url§, §reported_date§, §capture_summary§ e §reported_access_status§, retém §raw_record§ e sinaliza que o resumo **não comprova leitura da fonte pelo jornalista**. **Não há estrutura semântica específica** para versões de produto, fontes primárias/secundárias por alegação, histórico do radar ou divergências, embora o bruto seja preservado.
- O §factory_worker.py§ encaminha o §candidate§ à esteira; o §context.py§ injeta esse contexto em nós da fábrica e executa §websearch§ separado, incluindo §candidate.source_url§ na pesquisa quando configurado. Portanto ampliar o markdown do captador **não assegura**, por si só, que os novos campos sejam consumidos de maneira útil; integração requer compatibilidade de contrato entre os dois lados.
- O ensaio System76 envolveu pesquisa ativa separada e retornos de reviewer; **não há prova de que o bloqueio teve causa no captador**. Ainda é necessária auditoria dos três drafts, reviews e evidências.

**Hipótese a discutir com o Bloco do Coletor:** cada descoberta poderia trazer, dentro de limites de custo, precisão e volume, tipo da pauta, produto/modelo/geração exato, resumo factual com fontes atribuídas, alegações não verificadas, diferenças entre versões, referência a comunicado primário, lacunas, contexto temporal e ligação ao radar. Evitar reproduzir integralmente matéria protegida de terceiros, inventar resultados ou transferir apuração/conclusões jornalísticas ao coletor. Jornalista e reviewer continuam obrigados a conferir o material na fonte quando necessário.

**Próxima ação apenas proposta:** ouvir o Bloco Coletor sobre capacidades reais e limites e, só se o diretor aprovar uma proposta precisa, preparar ajuste conjunto de formato do captador + parser/prompt da fábrica e teste controlado. Não fazer alteração automática nem abrir nova execução do Luna.


## M. Devolutiva detalhada do Bloco Coletor: inteligência editorial prévia — 31/10/2026

**Origem:** texto integral da proposta encaminhado pelo diretor ao Fundador 4, atribuído ao Bloco Coletor. **Status:** **proposta apresentada e analisada** pelo Fundador; **não homologada pelo diretor como contrato final** e **sem implementação autorizada**.

**Proposta setorial:** evoluir de descoberta (manchete, URL, data e resumo) para três camadas: **descoberta, investigação documental seletiva e acompanhamento longitudinal**. Classificar pautas comuns/relevantes/alto impacto para adequar o investimento de pesquisa; gerar dossiês sobre fontes primárias, origem das alegações, cronologia, modelos/versões, fontes independentes, divergências, lacunas, datas e o campo explícito **“O que ainda não sabemos?”**. Adaptar evidências por tema (hardware, games, mods). Manter radar de assuntos, histórico permanente por acontecimento e deduplicação semântica além de URLs. Preservar boletim cronológico existente e acrescentar dossiês para aproximadamente uma ou duas pautas por rodada **como sugestão experimental**, não obrigação validada. Separar redação e apuração final do jornalista, não alegar testes próprios, respeitar conteúdo fechado/direitos e medir custo/benefício.

**Parecer do Fundador 4:** abordagem conceitualmente promissora e compatível com objetivos de apuração verificável. O coletor já entregou 8 notícias novas e radar de 12 assuntos na coleta de 31/10 às 08h, portanto não é correto afirmar que hoje só entrega links. O ganho real viria de **conectar afirmações a evidências rastreáveis**, distinguir divulgação original de repercussão e preservar história dos acontecimentos. Uma classificação de “confiabilidade” precisa referir-se à **alegação e à prova específica**, e não representar nota arbitrária e definitiva para um veículo. Diferentes artigos que repetem o mesmo comunicado **não são fontes independentes**.

**Dependência de engenharia essencial:** o atual adaptador `automation/pipeline/src/collector.py` da factory privada reconhece poucos campos de headline e `capture_summary`; conserva `raw_record`, mas `story_id` tem base em URL normalizada. Enriquecer Markdown por si só não garante consumo semântico; deduplicação por acontecimento precisa de identidade distinta da URL. A factory pesquisa fontes independentemente; por isso, ainda não está demonstrado que a falha System76 tenha surgido no coletor. Dossiês adicionais na pasta monitorada `coletor/` exigiriam cuidado para não virar candidatos duplicados no parser de cabeçalhos `### N. ...` ou serem desperdiçados; definir formato e integração antes de alterar a rotina.

**Proposta de piloto futuro, condicionada à direção:** uma pauta relevante, dossiê com URL de cada afirmação, evidência original/primária ou secundária, identidade exata do produto, antecedentes, fatos confirmados, conflito documentado, lacunas, data e limites de pesquisa. Aferir quantas citações o jornalista aproveita, novas buscas necessárias, correções do revisor, tempo de execução, custo, precisão e falsos vínculos entre assuntos. Preservar boletim atual, regras de anti-repetição e histórico e proibir cópia integral de textos de terceiros em repositório público. **Não executar** nova coleta, inferência, mudança de automação ou contrato por conta desta nota.

**Próxima decisão:** diretor avaliar a proposta em diálogo com Fundador e Bloco Coletor. Formalização de contrato e piloto somente após comando específico.


## Atualização de diretriz — Coletor como pesquisador editorial (31/10/2026)

**Origem:** orientação explícita do diretor ao Fundador 4. **Status:** direção conceitual definida; integração técnica ainda pendente.

O diretor rejeita limitar artificialmente o coletor à descoberta e a pequenos resumos. O coletor deve aproveitar ao máximo sua capacidade de pesquisa documental pública para entregar aos jornalistas **o contexto mais completo, útil e verificável possível**, inclusive fontes primárias e secundárias, antecedentes, cronologia, especificações e gerações de produtos, confirmações, versões conflitantes, evolução de rumores, lacunas e perguntas não resolvidas. O campo "O que ainda falta investigar?" permite ao jornalista avaliar se precisa buscar algo mais. Pesquisa complementar do jornalista deve ser **opcional, motivada por lacunas**, não uma repetição obrigatória do trabalho já feito.

**Divisão:** coletor descobre e investiga documentalmente; jornalista julga as evidências, define enfoque e escreve; revisor verifica rigor e consistência. A profundidade do coletor não o transforma em redator. Não impor arbitrariamente limite de um ou dois dossiês por rodada: dimensionar a pesquisa conforme relevância, recursos e qualidade real. Preservar atribuição às fontes e não reproduzir material protegido integralmente em repositório público.

**Integração:** incumbência do Codex adaptar a fábrica para aceitar, preservar e disponibilizar a totalidade do dossiê relevante aos agentes, sem descartar campos ricos por limitação do parser atual. Manter compatibilidade com o formato antigo e conservar trilha de proveniência. Coordenar especificação da entrega do Bloco Coletor com o contrato de ingestão da fábrica, sem criar processo paralelo de teste ou reconstruir a esteira existente. A ordem de implementação deve ser dada pelo diretor; esta nota não dispara mudança ou inferência.

**Ressalva técnica:** informação reunida não equivale automaticamente a prova correta; jornalista e revisor devem poder conferir alegações na fonte, sobretudo diante de contradições ou alegações de alto impacto. A causa do bloqueio System76 continua sem diagnóstico definitivo.
