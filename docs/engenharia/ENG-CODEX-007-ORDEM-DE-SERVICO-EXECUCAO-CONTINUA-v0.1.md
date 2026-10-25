# ENG-CODEX-007 — Ordem de serviço contínua e sequência de execução E01–E19

**Direção:** instrução expressa em 25/10/2026 — implementar arquitetura de agentes, regimento funcional, Radar geral, perfis de pesquisas sob demanda e integração à esteira; depois executar testes isolados e integrados dos três jornalistas. **Modalidade:** ordem de execução técnica contínua e incrementada, dentro dos limites deste contrato, sem microaprovações de rotina. **Estado inicial:** ENTREGUE PARA CODEX; nenhuma tarefa deste novo roteiro está marcada como executada pelo fundador.

**Documentos normativos desta ordem (branch de documentação):**
- `docs/operacao/REGIMENTO-INTERNO-FABRICA-EDITORIAL-v0.1.md`
- `docs/engenharia/ENG-CODEX-007-CATALOGO-E-DNA-FUNCIONAL-DOS-AGENTES-v0.1.md`
- `docs/engenharia/ENG-CODEX-007-RADAR-FONTES-RUMORES-E-PESQUISA-v0.1.md`
- Esta ordem, sempre ligada à Issue de engenharia e a commits, sem confiar na memória de chats.

## 0. Primeiro: ler o que já foi entregue e verificar HEADs

Não reescrever motor, OAuth/SIWC, persona ou layout:
- Motor Editorial v0.2 integrado em `main` pelo PR #6.
- Orquestração/SIWC PR #8 e Luna Max/editorial PR #10; prova histórica em 19/10 com `gpt-6-luna`, `reasoning.effort=max` via OAuth, **seis inferências reais** para *perfil neutro*, experimento de capa incompleto; não constitui prova da fábrica real com três jornalistas.
- PR #18 contém fundamentos de layout/acervo; PR #24 (B1 sobre main), #25 (B2/B3 sobre B1), #26 (C0–D2 sobre B2/B3) contêm reconciliação offline, `factory-demo`, `AgentQueue`, `TaskDispatcher`, revisões, direitos, StoryPackage/LayoutPlan/prévia/gate simulado; testes reportados pelo Codex **95/95**, fluxo normal **15/15** e revise **18/18**, ambos `published=false`. Esses números não devem ser convertidos em prova de IA real.
- PRs #13/#14 de Carranca, #19 de Beto/Nina, #27 de continuidade. Handoff documental dos três: `docs/personagens/ENTREGA-TRIO-PERSONAS-BLOCO02-2026-10-24.md` na branch PR #19. IDs canônicos `ranzinza`, `beto-cartucho`, `nina-prisma`. DNAs criativamente fechados, matrizes T01–T16 **não executadas**.
- Issue #20 de memória editorial: D0–D2 são planejamento, banco runtime local v4 foi apenas inspecionado; schema código v5. **Não migrar runtime real nem ativar memória sem requisitos/gate próprios.**
- Issue #28 registra dois testes de persona (isolado e integrado) e discussões subsequentes; esta ordem atualiza a prioridade: **primeiro construir o circuito completo de papéis/radar**, depois persona isolada, depois persona integrada.

Se a estação Codex local exibir `19/19` de uma missão anterior, **reconciliar ID/branch/commit com GitHub antes de marcar como entregue**. O último baseline verificável aqui é o handoff A0–D2 na PR #26, HEAD `4de16640e67bd16c61468955e96e4ffa850d4cab`; “19/19” foi mencionado pelo diretor, mas não é substituto de evidência/HEAD. Não repetir testes históricos salvo regressão necessária.

**Estratégia de branches:** partir do HEAD de engenharia candidato que contém PR #24→#25→#26, confirmado atual antes de cada fase. Abrir branch de trabalho e PR draft específicos ENG-CODEX-007 **sem merge na `main`**. A documentação de direção está em branch independente; consumir arquivos pelo ref explícito até revisada/mesclada futuramente, sem exigir merger na main. Resolver conflitos de origem com método verificável, manter PRs e hashes antigos intactos; `mergeable=true` é condição de Git, não aceite funcional.

## 1. Autonomia OPERACIONAL expressamente concedida nesta missão

O diretor **não estará permanentemente diante do PC** para apertar confirmação a cada teste ou checkpoint. Esta ordem concede, dentro do escopo:

**Pode executar sem consulta individual:** ler/editar código e documentação da branch autorizada; pesquisar documentação técnica pública necessária; criar arquivos/fixtures/schemas locais; instalar/testar dependências de desenvolvimento compatíveis dentro do projeto sem compra; executar e **reexecutar** testes unitários, de integração, smoke **offline** e regressões; usar relógio/redes simuladas e servidor de loopback; corrigir testes/código, rodar linter/type checks, validar CLI; commitar, fazer push na branch, criar/atualizar PR draft, comentar e atualizar Issues, atualizar checkpoint/relatórios, revisar interfaces, avançar automaticamente de E01 para E19 quando pré-condições forem atendidas. Essa é **uma autorização por missão**, não 19 pedidos de aprovação. Não abrir pergunta sobre escolha trivial de algoritmo, nome de classe, commit ou comando de teste.

**Pode preparar, sem ativar silenciosamente:** conector de leitura web pública permitido e perfis de fonte; agendas configuráveis default OFF; integração do executor local SIWC já existente; artefatos editoriais internos em sandbox/ambiente local. Para ensaios **reais controlados, apenas se o ambiente e a conta já estiverem autorizados/elegíveis**, a direção manifesta intenção nesta missão de usar a **franquia Plus já existente** (nenhum desembolso novo), com preflight `status/models`, **sem fallback**, execuções pequenas e observáveis e parada automática ao atingir limite ou falha de elegibilidade. Não estimar cotas do Plus a partir de tokens; manter limites por sessão/tarefa e logs de usage. Não repetir login/probe real automaticamente. A conta pode exigir **consentimento humano oficial para novo OAuth**, que nunca deve ser contornado. Se não houver demonstração de autorização vigente, marcar a parte online como `blocked_needs_consent` e continuar restante offline. **O relatório da etapa real precisa informar se houve ou não consumo real.**

**Precisa de aprovação separada:** qualquer pagamento/crédito/API-key faturável, contratação, mudança do plano do usuário, merge irreversível/produção na `main`, credencial de terceiro ou app comercial, escalonamento de quota via múltiplas contas, mudança no DNA aprovado, download/reprodução de mídia sem direito, postagem, publicação, envio de e-mails/redes, contas sociais, deploy/VPS/daemon externo em produção, três/seis coletas automaticamente ativas em internet real indefinidamente, acesso a material privado, alteração de permissões, execução destrutiva contra banco runtime da máquina do usuário, migração real de v4 para v5, apagamento de histórico ou ações legais/comerciais. Não contornar prompts de segurança/permissão impostos pelas ferramentas/ambiente.

**Regra de não paralisação:** bloqueio de OAuth, limite Plus ou acesso a fonte específica não paralisa testes offline, documentação, ajustes de conector ou outro papel independente. Um único bloqueio global só quando invariantes de segurança/estado estiverem realmente ameaçados; relatar causa reproduzível. Não solicitar permissão dez vezes para a mesma suíte — executá-la quantas vezes precisar dentro da tarefa.

## 2. Protocolo de checkpoint para continuidade após cota/sessão

Manter em branch `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md`, criado em E01 e atualizado a cada unidade concluída **e a cada bloqueio**. Mesmo que a sessão acabe abruptamente, o último checkpoint commitado é base de retomada. Estrutura obrigatória:
- data/hora/fuso; nome da missão; última unidade concluída (E##_status) e próxima unidade exata;
- branch, upstream, HEAD local/remoto, base e dependências, status PR (draft/merge);
- `git status`, arquivos alterados e commits, hash de contratos relevantes;
- comandos de testes e contagens, ambiente e resultados **observados** vs apenas históricos/documentais;
- estado de SIWC (somente autêntico/indisponível, **sem credenciais**), chamadas reais/custos quando medidos, fontes/quotas, agenda ativa ou não;
- bloqueios, decisões pendentes do diretor (somente as realmente materiais), próxima ação executável independente;
- `published=false`, confirmação de nenhum gasto/API paga, migração e deploy quando aplicável.

**Cada unidade E##:** 1) verificação de git e dependências; 2) implementar/testar; 3) verificar `git diff --check`, smoke e testes adequados; 4) commit/push incluindo relatório; 5) comentário curto na Issue/PR com HEAD/testes/próxima; 6) iniciar E##+1 sem esperar resposta do diretor. Se a janela de contexto ou franquia terminar, deixar comando seguro e explícito de retomada, sem prometer trabalho assíncrono inexistente. Não reexecutar trabalho comprovado, exceto regressão necessária.

## 3. Linha de montagem E01–E19 — ordem autoritativa

Todas as unidades possuem **critérios de pronto**. Dentro de uma unidade, Codex decide subtarefas sem nova ordem. Se um marco depender de rede/modelo indisponível, entregar todos artefatos offline e deixar bloco online com status próprio; seguir subetapas independentes.

### E01 — Baseline e plano de integração (sem escrita destrutiva)
Inspecionar `main`, PRs #8/#10/#18/#24/#25/#26, #13/#14/#19/#27 e código/testes atuais; conferir HEADs, detectar alterações posteriores, relatório de status por componente, mapear `AgentQueue`, `TaskDispatcher`, SIWC, `factory.py`, layout e histórico SQLite sem tocar runtime real. Abrir PR draft de implementação. Criar checkpoint E01. **Aceite:** mapa de dependências concretas e suíte baseline executada na branch de trabalho ou impedimento especificado.

### E02 — Contratos versionados e regimento operacional no runtime
Implementar schemas validáveis (`AgentRoleProfile`, `AgentTaskEnvelope`, `AgentResultEnvelope`, `ResearchRequest/Packet`), hash/versão e catálogo configurável; integrar regras de regimento ao carregamento sem duplicar DNA. Evitar quebrar os envelopes/contratos A4 existentes; adaptar apenas o necessário. **Aceite:** fixtures e testes para papel errado, versão/hash divergente, escopo de ferramenta insuficiente, prompt injection e resposta malformada.

### E03 — Registro de funções e testes iniciais dos DNAs funcionais
Registrar `triage_analyst`, `evidence_investigator`, `assignment_editor`, `persona_writer`, `fact_checker`, `editorial_reviewer`; opcional `media_researcher`, `layout_planner` como perfis desligados para prova de valor. Nenhum LLM permanente. **Aceite:** cada papel tem instrução/entrada/saída/proibição/testes versionados e resolve `role_id` sem confundir com persona.

### E04 — Esquema de Radar e armazenamento em SQLite ISOLADO
Criar `SourceRegistry`, `ObservedDocument`, `ObservationEvent`, `EntityRegistry`, `ClaimLedger`, `ResearchRequest/Packet`, carteira de pautas. Preferir namespace/banco de teste separado, migração incremental com backup/rollback em fixture; sem tocar banco runtime v4 existente. **Aceite:** integridade de chaves, versões, fonte original e histórico de diffs, migração reproduzível de fixture.

### E05 — Conectores econômicos de obtenção (offline first)
Implementar interface de conector para RSS/Atom, API permitida e HTTP HTML público; validação de URLs e redirects, timeouts, TLS, robots/termos/config de permissão, rate limit por origem, backoff, `Retry-After`; sem bypass, credencial privada, descarga massiva ou site pago. **Aceite:** mocks HTTP/fixtures mostram sucesso, 304, 403, 429, 5xx, link removido, suspensão segura, SSRF bloqueada.

### E06 — Coleta incremental, cache e deduplicação
ETag/`Last-Modified`, URL canônica sem apagar parâmetros significativos, hash exato e mudanças de trecho, grupos de republicação conservadores, cache entre perfis, histórico de eventos. **Aceite:** título/body editado cria evento novo e não duplica pauta; cópia igual não consome LLM; dois autores independentes não são fundidos sem evidência.

### E07 — Pessoas, projetos, aliases, entrevistas e idiomas
Registrar produtores/diretores/devs públicos, cargos com intervalo, entidades e variações de nome/idioma, fontes originais e ligações; priorizar informação profissional, sem coletar dados pessoais privados. **Aceite:** produtor citado em entrevista ≠ press release de companhia; nome japonês/romanizado; homônimos; cargo antigo e nova função; original x tradução.

### E08 — Ledger de alegações e rumores
Implementar estados epistêmicos, fonte original/intermediário, origem independente, declarações pessoais e oficiais, fontes que se contradizem, histórico de atualização. Estado da **declaração** separado da comprovação do **conteúdo**. **Aceite:** 10 sites repetindo rumor de uma pessoa não se tornam 10 confirmações; rumor atribuível é preservado sem afirmar confirmação; mudança/correção mantém história.

### E09 — Agendamento e política de coleta ajustável
Implementar configurador de 3 janelas locais/dia com 4–6 opcionais, UTC internamente, atraso `skip/run_once`, dedupe por run, quota por domínio, pausa e dry-run; **default OFF**. **Aceite:** relógio simulado executa horas, quedas e retomada sem duplicação, sem chamada de IA por polling vazio.

### E10 — Radar geral e triagem em lotes
Entregar `DiscoveryBatch` para fila de triagem; política de novidade e relevance threshold configurável, sem LLM obrigatório no caminho sem novidade; pesos de prioridade controláveis e auditáveis. **Aceite:** batch sem alteração não desperta IA; fonte editada gera candidato; grupo de rumor não duplica e informa proveniência.

### E11 — Pesquisa sob demanda com perfis compartilhados
Perfis `radar.general.v1`, `research.hardware.v1`, `research.games.v1`, `research.creators.v1`; `ResearchRequest` versionado, cache-first, limite/escopo, resposta `found|partial|not_found|blocked|rate_limited`, ligação a `story_id`/revisão. Nenhum robô duplicado por jornalista. **Aceite:** Carranca requisita testes de GPU 1440p e método; Beto requisita mudanças de mecânicas; Nina pede changelog/licenças de mod; todos reutilizam índice e respeitam limites; sem resultado não gera invenção.

### E12 — Carteira 10 principais + 10 reservas e continuidade
Gerir candidatas por tópico/edição, atualizações, prioridade e reserva, sem redigir automaticamente todas; mudança de estado em rumor ou fonte importante reativa avaliação, não apaga história. Trocas que afetem membro de edição têm autorização auditável. **Aceite:** 20 candidatos sem 20 reportagens; 10 principais + 10 reservas sem duplicar tópico; pauta bloqueada não bloqueia outras.

### E13 — Integração dos papéis ao dispatcher existente
Adapter/registry de papel e `ResearchRequest` → tarefas duráveis → dependências/retomada → resultados, não criar segundo orquestrador. Separar funções determinísticas dos LLMs; agendamento do Radar acorda coleta, mas não liga produção por conta própria. **Aceite:** fluxo sintético múltiplos papéis, solicitação complementar e retorno ao artigo correto; retries seguros, idempotência, owner/lease/heartbeat e teste de restart.

### E14 — Handoff editorial com evidências e revisões
Conectar `EvidenceDossier` → `EditorialBrief` → `StoryDraft` → `FactCheckVerdict` → `EditorialReview`; manter até duas funções de revisão distintas para avaliação, com opção de compará-las no custo. Revisão e correção ligadas ao hash; `hold` bloqueante; necessidades visuais → direitos/StoryPackage/LayoutPlan/preview existentes. **Aceite:** uma reportagem de rumor atribuída, um caso de hardware e um caso de jogo/mod em fluxo offline; ataque de fonte bloqueado; texto corrigido exige nova revisão; `published=false`.

### E15 — Ensaio integrado offline multipauta e regressões
Combinar Radar+pesquisa com fábrica candidata, fonte/editores/redatores/revisores e layout; fazer teste **E2E com mais de uma pauta** no novo caminho (não só multipauta legado v0.2). Verificar status das 95 regressões anteriores após mudança, reparando apenas regressões comprovadas; documentar novo total observado. **Aceite:** 2–3 pautas, uma bloqueada/uma corrigida/outra aprovada para prévia interna, replay de restart, sem coletas reais, sem SIWC real e sem publicar.

### E16 — Integração externa mínima de fontes públicas permitidas (controlada)
Depois dos mocks, selecionar poucas fontes comprovadamente abertas/permitidas, uma execução **manual** de leitura sem custo, sem chave nova, respeitando robots/termos/rate limits; salvar metadados/URL/hashes e resultado sanitizado. **Aceite:** relatório do que foi de fato consultado, limitações/403/429 e nenhum conteúdo licenciado republicado. Se não elegível, `blocked_external_access` e continuar.

### E17 — Piloto mínimo de papel IA real via SIWC Plus local
Reusar OAuth/credenciais **já autorizadas e válidas**, consultar `status/models` sem desperdiçar probe, confirmar `gpt-6-luna` e `reasoning.effort=max` ou reportar bloqueio sem fallback. Uma execução pequena, observável, com fontes/fixtures controladas, papéis editoriais e gates seguros, usando a franquia existente **somente se elegibilidade e limites vigentes permitirem**; não criar API key paga, nem login remoto. `store=false`, `stream=true`, verificar `response.completed`, `429` e stream incompleto. **Aceite:** input/outputs e status reais distinguidos de mocks, chamadas/uso/tempo registrados sem segredo, `published=false`. Não forçar número alto de chamadas; primeiro medir. Sem consentimento exigido/sem quota, entrega bloqueada com prova e continua tarefas offline.

### E18 — Testes isolados de cada jornalista (eixos P/J)
Ler HEADs e DNAs aprovados de Carranca/Beto/Nina; sem refazer amostras. Executar pilotos em temas novos fora da fábrica, **no Luna Max real somente quando autorizado/disponível**, comparar fidelidade P e qualidade jornalística J, independentes, avaliadores/revisão humana da direção em amostra representativa; ampliar gradualmente T01–T16 por persona conforme evidência/capacidade, preservando registros de `not_executed` para casos não corridos. **Aceite:** resultados por persona, falhas/limites, inputs/outputs/hashes, sem “aprovado” por causa apenas do estilo. Em bloqueio de cota, concluir documentação/testes mock sem fingir execução real.

### E19 — Testes dos jornalistas DENTRO da fábrica + handoff
Repetir pautas controladas de E18 na esteira com mesma versão DNA/fontes, comparar P/J, verificar não mistura de personas na revisão/diagramação, pesquisa complementar por cada perfil, rastreio de rumos e leitura acessível. Rodar regressões finais, `compileall`, checks de integridade, relatório de cobertura/consumo e **parecer final com pronto/bloqueado/pedidos objetivos** por camada. Manter código em PR draft, sem merge/publicar; encaminhar revisão ao Fundador 2; registrar o que ainda falta para edição piloto real, operação de coleta contínua, memória, leitor visual e elegibilidade VPS.

## 4. Critérios de conclusão GLOBAL e veracidade do relatório

**Entregue:** código versionado em branch e PR, arquivos/contratos, fixtures, testes reproduzíveis, manual local de execução e configuração, checklist de origem/direitos, logs sanitizados, exemplos de dossiê/rumor, checkpoint E19 e relatório de lacunas. A fábrica deve ser capaz de fazer testes offline de descoberta→triagem→investigação→redação→checagem→revisão→direitos/layout→prévia com múltiplas pautas e pesquisa sob demanda, reutilizando o motor existente. O caminho SIWC real tem aceites próprios, não é implicitamente liberado para produção pela entrega.

**Não declarar:** que há robô fazendo 3–6 coletas reais agendadas, que cinquenta fontes reais já estão homologadas, que modelos passam em T01–T16 sem executá-los, que a conta Plus sustenta produção mensal, que direito de ativos foi confirmado, que memória v0.1 foi implantada ou que a `main` integra PRs antigas — sem evidências reais.

**Ao terminar:** resumo por E01–E19 (`done|blocked|partial`), commits, branch, PR, teste observado, chamadas reais, decisões necessárias **somente de gate material**, próximos riscos e recomendações para Blocos 03–06. A prioridade do diretor é **seguir a sequência continuamente**, mas não sacrificar integridade: bloqueios genuínos são registrados e contornados por etapas independentes, nunca por bypass ou fabricação de progresso.
