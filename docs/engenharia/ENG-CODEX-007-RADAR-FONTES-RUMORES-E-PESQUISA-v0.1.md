# ENG-CODEX-007 — Radar de descobertas e pesquisa especializada sob demanda v0.1

**Origem:** direção, 25/10/2026 | **Fronteira:** arquitetura e requisitos de implementação para o Codex; não é coletor operando. **Reaproveitar** Python, SQLite, `AgentQueue`/`TaskDispatcher`, status, idempotência e auditoria existentes; não inventar microserviços sem medição de necessidade.
**Objetivo:** descobrir notícias e rumores de games/hardware/comunidade a baixo custo, manter histórico por assunto/alegação e permitir investigação complementar pedida por qualquer especialista. A coleta principal é **software determinístico**, não uma chamada do Luna por URL.

## 1. Arquitetura lógica

Um **ResearchService compartilhado** oferece duas políticas:
- **Radar geral incremental:** scheduler por horários configuráveis (intenção inicial: três rodadas diárias; permitir quatro a seis se fonte/limite/custo justificarem). Processa fontes cadastradas, registra novidades/diferenças e só enfileira avaliação semântica se houver novidade relevante. *Coletar não significa produzir pauta*.
- **Pesquisa sob demanda:** aceita `ResearchRequest` formal emitido por investigador, editor, redator, checador, curador; exige motivo/lacuna, `story_id`, `parent_task_id`, perfil de pesquisa, orçamento de consultas e política de fonte; consulta cache/índice primeiro, depois conectores autorizados, entrega `ResearchPacket` com procedência ou falha explícita.

Ambas usam a mesma **fonte de verdade local**: Catálogo de Fontes, Pessoas/Projetos, Documentos Capturados, Alegações, Tópicos, Ligações de republicação e Histórico de Mudanças, com controle de acesso e origens. “Robô do Carranca/Beto/Nina” significa **perfil determinístico especializado sobre um mesmo serviço**, NÃO três instâncias de scraping e NÃO agentes IA separados por padrão.

## 2. Camadas de obtenção — da mais barata à mais custosa

1. RSS/Atom, feeds de changelog, releases oficiais e páginas que declaram atualização; cadastro com URLs oficiais, domínio, ETag/Last-Modified quando suportado, intervalo mínimo e regras do provedor.
2. APIs públicas/documentadas para metadados e busca, com autenticação/cota se elegível e expressamente autorizada; não contratar/ativar serviços pagos automaticamente. Para fóruns e redes sociais, preferir APIs/feeds legítimos e respeitar restrições dos provedores.
3. HTML público permitido via HTTP, com extração delimitada e politeness (robots/termos/políticas de acesso conforme aplicáveis, `Retry-After`, backoff, limitação de concorrência por origem). Não burlar login/captcha/bloqueio, não acessar perfis privados, dados de usuário ou grupos fechados.
4. Consultas específicas de pesquisa/sistemas de busca licenciados se existirem interfaces permitidas; **não presumir que SIWC por si só oferece web search, hosted MCP ou browsing**. A documentação oficial do preview varia por ferramenta e conta; conferir catálogo e escopos no ato da implementação.
5. IA: somente triagem/investigação de **pacotes de evidência já obtidos** e decisões que código não pode justificar. Não usar chamadas Luna por cada URL; agrupar em lotes por assunto/fonte.

**Importante:** `robots.txt` e termos do serviço são sinais de política/acesso, não licença para republicação. Link/crédito não autorizam copiar integralmente textos, imagens, vídeos ou transcrições; armazenar excertos mínimos necessários, metadados e, onde permitido, cache privado temporário. Informação de pessoas só quando publicamente ligada ao projeto profissional, evitando coleta de dados pessoais. Suportar remoção/revogação e retenção curta conforme política.

## 3. Catálogo de fontes (`SourceRegistry`)

`source_id`, `name`, `publisher`, `type=developer_official|company_official|journalism|independent_testing|community|primary_interview|creator_blog|api|feed`, `root_url`, `feed_url?`, `terms_checked_at?`, `access_policy`, `license_status`, `allowed_operations`, `contact?`, `language`, `region`, `topic_tags`, `trust_notes`, `expected_update_rate`, `min_poll_interval`, `last_polled_at`, `last_success_at`, `failure_budget`, `domain_rate_limit`, `quota_units`, `disabled_reason`.

Não cadastrar genericamente “todo o Reddit/YouTube/X/etc. liberado”: o conector exige contrato específico por serviço, escopos e condições atuais. Sites com restrição ficam como **descoberta de links externos sem download automatizado**, ou requerem credencial/aceite próprio.

**Categorias iniciais propostas:** jogos AAA, mods/indies/criadores, hardware PCs/consoles, empresas/plataformas, recepção crítica, entrevistas/documentos oficiais e comunidade. Habilitar fontes em lotes pequenos, medindo retorno e qualidade antes de crescer para centenas/milhares.

## 4. Registro de pessoas, produtos e assuntos (`EntityRegistry`)

`entity_id`, `type=game|franchise|product|component|company|studio|person_public_professional|mod_project|platform`, nome canônico, nomes anteriores/alternativos, grafias/localização (por exemplo japonês/romanização), `aliases`, relações com títulos e projetos, função/cargo **com data**, `source_refs`, estado/versão, datas de validade, `editorial_interest`. Não supor cargo atual sem data.

Pesquisa por produtor/diretor/roteirista/desenvolvedor usa o nome público e seus aliases combinados ao projeto/empresa, preservando quem foi entrevistado e o publicador da entrevista. Declaração pessoal de produtor não vira automaticamente comunicado institucional da empresa. Entrevista em outro idioma preserva título/idioma/URL originais, identifica tradução e incertezas. Remover homônimos e falsos positivos antes de consolidar.

## 5. Registro de documentos e observações

`ObservedDocument`: `document_id`, `canonical_url`, `resolved_url`, `source_id`, `publisher`, `byline?`, `language`, `published_at?`, `modified_at?`, `fetched_at`, `etag?`, `last_modified?`, `content_sha256`, `normalized_sha256`, `title`, `summary_snippet`, `outbound_primary_refs`, `topic/entity_refs`, `access_policy`, `rights_status`, `content_retention`, `fetch_status`, `retry_after?`. Chaves: normalização URL conservadora; não eliminar parâmetros que mudam versão/material; URLs redirecionadas são auditadas.
`ObservationEvent`: nova publicação, mesmo documento repetido, título alterado, corpo alterado, correção, exclusão, mudança de URL, novo link de origem, erro ou remoção; registrar **diferença** e versionamento, não criar pauta duplicada.

Dedupe níveis: URL/exato por hash → variantes/canônicos → similaridade de título/trecho → cluster semântico apenas quando seguro, com referência individual preservada. **Cuidado:** dois sites independentes podem publicar notícias parecidas; não destruir proveniência numa deduplicação agressiva. Em dúvidas, preservar dois registros relacionados.

## 6. Alegações e rumores (`ClaimLedger`)

`claim_id`, `topic_id`, `statement`, `epistemic_status`, `asserted_by_entity_id?`, `reported_by_source_id`, `earliest_traceable_source_id?`, `first_seen_at`, `statement_date?`, `published_at`, `url`, `confidence_in_attribution`, `confidence_in_content?`, `evidence_refs`, `republished_by[]`, `independent_origin_groups[]`, `disputed_by[]`, `superseded_by?`, `new_information_since`, `editorial_review_status`.

**Estado da alegação NÃO pode ser confundido com verdade do conteúdo:**
- `official_statement`: organização fez a afirmação documentada; conteúdo técnico ainda pode exigir medição;
- `named_person_statement`: pessoa identificada declarou; verificar cargo/data e se fala pessoal ou corporativa;
- `independent_measurement`: medição de terceiro com método/versão;
- `community_report`: testemunho limitado sem generalização;
- `attributed_rumor`: portal/informante atribuído e sem confirmação;
- `unverified_or_disputed`: origem/valor incerto ou contraditório;
- `editorial_interpretation`: inferência separada do fato.

`confirmed`, `partially_confirmed`, `contradicted`, `withdrawn` são **eventos posteriores com fonte/razão**, nunca classificação inferida apenas da contagem de artigos. Exemplo conceitual: portal B cita Y sobre suposta mudança 70/30 de personagens; fonte original de Y não rastreada => rumor de origem incerta, não “Capcom confirmou 70%”. Posterior entrevista de produtor explicando mudança de título => declaração pessoal com fonte primária se comprovada; não reescrever o passado como se rumor nunca existiu.

Duas URLs reproduzindo o mesmo vazador **são uma linhagem de rumor**, não múltiplas confirmações. Teste de rumor bem citado não se torna “verdade”. Manter casos sem prova: o agente pode redigir “circula rumor atribuído a ... ainda não confirmado” se interesse editorial e risco forem avaliados e diretor aprovar.

## 7. Contrato `ResearchRequest.v0`

Entrada proposta:
`request_id`, `parent_task_id`, `story_id`, `requester_role_id`, `requester_persona_id?`, `research_profile_id/version`, `question`, `queries[]`, `entity_ids[]`, `required_evidence_kinds[]`, `preferred_source_ids/domains[]`, `languages[]`, `time_window`, `versions/configurations`, `known_evidence_ids[]`, `exclusions`, `max_sources/max_requests/max_bytes/max_duration`, `reason`, `allowed_scope`, `idempotency_key`, `human_gate_if_sensitive`.
`ResearchPacket.v0`: `request_id`, `status=found|partial|not_found|blocked|rate_limited`, `document_refs`, `claim_refs`, `source_lineage`, `new_material_since`, `relevant_excerpts_short`, `missing_evidence`, `constraints/retry_at`, `retrieval_log_ref`, `content_hash` e `fetched_at`.

**Regra central:** O redator pede “benchmarks GPU 1440p, VRAM, 1% low, drivers/versões” ou “mecânicas/remake, entrevistas, origem de rumor”, o Motor registra pedido e aciona o mesmo ResearchService com perfil adequado. O pacote volta ao **mesmo** `story_id` e revisão, com versionamento e nova checagem; o redator não cria thread autônoma fora do ledger. Sem achado = explicitamente `not_found`, nunca inventar resultados. Cada pedido tem orçamento e profundidade para evitar loop infinito de pesquisa.

## 8. Perfilagem de consulta, sem três programas separados

- `radar.general.v1`: varredura agendada multi-setor, fontes oficiais/comunidades/portais permitidos; usa data de modificação, diffs e palavras-chave.
- `research.hardware.v1`: SKU, arquitetura, memória/cache, barramentos, VRAM, APIs gráficas, raster/RT, FSR/DLSS, preset, FPS médio/1% low, método, drivers, consumo/temperatura, preço/data; retorna tabelas de parâmetros sem fingir teste próprio.
- `research.games.v1`: título e aliases, editora, equipe, entrevistas, franquias, comparativos entre versões, lore explicitamente sustentada, elenco/mecânicas, plataformas, patch notes, reviews e rumores.
- `research.creators.v1`: mods/indies, repositórios e releases, changelogs, licenças, autores, entrevistas públicas, requisitos, compatibilidade, comunidades, divergências/bugs.

Perfis não são fronteiras exclusivas de pauta: Carranca pode pedir game research, Nina pode pedir hardware, Beto pode pedir mods. O serviço seleciona por **pergunta**, não pela idade ou personalidade do jornalista.

## 9. Carteira editorial principal + reservas

**Objetivo inicial de planejamento:** uma edição com dez matérias (capa + nove), outra dez candidatas como reserva para reposição dinâmica; é alvo provisório e ajustável, não limite de descoberta. O Radar continua coletando após 10 ou 20; registra atualizações sem iniciar vinte reportagens completas. Candidatas têm `topic_id`, `story_id?`, `queue_lane=principal|reserva|monitoramento|descartada`, `reason`, `depth_available`, `evidence_risk`, `last_material_change`, `priority`, `source_packet`, `human_override`, histórico de promoção e da edição.

Código controla contagem, duplicação, limites e atualização de estados. IA pode **sugerir** prioridade e promoção; troca de membro da edição exige regra de direção/aprovação auditada, evitando remover automaticamente matéria já aprovada. Fontes rasas não bloqueiam todas as pautas: reserva sobe mediante critérios autorizados, sem descartar história.

## 10. Scheduler, budgets e proteção operacional

- **Default OFF**, horários configuráveis no fuso `America/Sao_Paulo`; interna UTC; comportamento `skip` ou `run_once` para janela perdida. Início real das três coletas depende de aceite de operação de rede e fontes.
- 3/dia como hipótese inicial; 4–6/dia somente depois de medição de benefício versus custo/limites. Preferir varredura leve em todas as categorias + rotas mais profundas alternadas, em vez de “hardware só de manhã” que perderia notícia.
- Isolar processo local, fila durável, rate limit por domínio e por API, tempos máximos, `Retry-After`, concorrência baixa, backoff, circuit breaker, quotas por origem e teto global. Dados externos podem conter instruções maliciosas: nunca executar scripts baixados, nem entrar em rede privada/localhost por URL externa (proteção SSRF/redirect/DNS), não aceitar `file://`, credenciais, hosts internos, portas arbitrárias ou URLs de callback.
- Determinar política de user agent, privacidade, limpeza de cache, espaço em disco, backups de metadados e trilha de remoção; não baixar imagens/vídeos em massa; indexar links e direitos.
- **Não habilitar cobrança.** APIs com chave de uso/política especial exigem consentimento e credenciais específicas, armazenadas fora do Git. A operação usa fontes públicas permitidas primeiro.
- Falta de acesso (401/403), limites (429), link removido, falta de timestamp, mudança da página, interrupção/timeout ou web inacessível gera registro/falha restrita, sem contornar bloqueios.
- Web externa é trabalho de coleta; LLM SIWC só sob prova atual de elegibilidade, escopo e uso permitido, com `store=false`, `stream=true`, regras de preview e stop ao limite; não pressupor ferramenta hosted de busca.

## 11. Testes obrigatórios antes de ligar coletas externas

**Offline fixtures com rede simulada/loopback (exemplos mínimos):**
R01 três horários no mesmo dia/fuso; R02 4–6 horários configuráveis e DST/local; R03 queda/restart e janela perdida `skip/run_once`; R04 ETag 304 sem novo documento; R05 notícia editada gera `ObservationEvent`, não pauta duplicada; R06 dez portais copiam rumor de Y, apenas um grupo de origem; R07 declaração de produtor e release da empresa são distintos; R08 URL e alias de Code: Veronica/X vinculam mesmo tópico, sem presumir fatos de exemplo; R09 status de rumor confirmado/contradito por nova fonte sem apagar história; R10 pessoa homônima/cargo antigo; R11 tradução com proveniência original; R12 pergunta do Carranca por benchmark 1440p retorna método e lacunas; R13 jornalista sem evidência recebe `not_found`; R14 cache compartilhado entre três perfis; R15 URL bloqueada/SSRF/redirect; R16 403/429/`Retry-After`, timeouts/retry finito; R17 site proíbe coleta = nenhuma tentativa alternativa; R18 artigos/ativos de terceiros não são republicados; R19 carteira 10+10 sem redigir 20 matérias; R20 duas pautas solicitam pesquisa concorrente e fila resolve idempotência, cancelamento, escopo e versionamento; R21 falha em uma pesquisa não trava outra; R22 solicitação de pesquisa reabre somente a revisão vigente.

**Teste vivo limitado de conectores** (somente depois de fixtures, legalidade e configuração sem custo): selecionar poucas fontes oficiais/feed público comprovadamente permitido, executar uma varredura manual controlada, evidenciar URL/timestamp/304 ou novo documento/latência/volume, sem login em fórum fechado e sem guardar artigo integral. Testar frequência em relógio simulado antes de ativar scheduler real. Logs sanitarizados, nenhuma publicação.

**Métricas:** documentos consultados, novos vs repetidos, custo de rede/API e armazenamento, bytes, média de latência, mudanças materiais, origem rastreada, taxa de falso agrupamento, pedidos de pesquisa bem atendidos, sites indisponíveis, cota por conector, proporção encaminhada a agente IA e **custo SIWC por matéria**, quando uso existir. Não proclamar dezenas de milhares de fontes rastreadas sem execução real.

## 12. Fronteira da missão

Executar o projeto do Radar e perfis em branch, com testes offline primeiro e uma validação de conectores de leitura pública autorizada; não ligar daemon/cron 24h real, não abrir acesso privado/credenciais e não fazer publicação. O caminho para produção exige homologação de fontes/permissões, configuração de horários/custos, direitos, segurança da rede e decisão própria da direção. **Entregar o máximo testável localmente sem confundir software pronto com fontes e operação real já autorizadas.**
