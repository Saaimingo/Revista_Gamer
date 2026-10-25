# ENG-CODEX-007 — Catálogo de funções e DNA operacional dos agentes v0.1

**Origem:** Fundador 2 / direção, 25/10/2026. **Estado:** baseline técnico para implementação, teste e posterior aceite; **NÃO** substitui os DNAs narrativos aprovados no Bloco 02. Normas superiores em `docs/operacao/REGIMENTO-INTERNO-FABRICA-EDITORIAL-v0.1.md`.
**Princípio econômico:** não criar um LLM separado por setor, nem um software inteiro por jornalista. Um executor IA reaproveitável carrega `role_id` e, para redação, `persona_id`, ambos versionados. A pessoa/empresa pode ter vários papéis; cada chamada deve possuir exatamente as instruções aplicáveis e receber mínimo contexto necessário.

## 1. Inventário e conta realista

A arquitetura do projeto de 20/10 lista nove responsabilidades (seis passíveis de IA, duas determinísticas, direção humana), **sem fixar quantidade de agentes nem atribuir IA a cada setor**. O desenho desta missão propõe uma decomposição de trabalho, sujeita a benchmarking:

**Seis papéis candidatos frequentes de IA** (todas as chamadas são sob demanda):
- `triage_analyst` — leitor/triador de descobertas;
- `evidence_investigator` — investigador de origem, divergências e lacunas;
- `assignment_editor` — editor de pauta e estrutura;
- `persona_writer` — redator que carrega um de **três DNAs** (Carranca `ranzinza`, Beto `beto-cartucho`, Nina `nina-prisma`);
- `fact_checker` — checagem independente e fonte por alegação;
- `editorial_reviewer` — revisão de clareza, integridade, adequação editorial e coerência de persona; independente do redator.

**Dois papéis opcionais de IA** somente se superarem baselines determinísticos:
- `media_researcher` — planejamento/curadoria inteligente de mídia; decisões sobre licença são gate humano+determinístico, nunca autodeclaração do agente;
- `layout_planner` — diagramação semântica criativa com memória histórica curada; o render/paginação/validator permanecem código.

**Portanto o teto inicial estudado é 6 + 2 = 8 papéis funcionais de IA, NÃO oito processos permanentes, contas, modelos ou pessoas.** Comparar custo/qualidade de juntar `triage_analyst` e `assignment_editor`, ou de juntar checador e revisor somente se revisão independente não for prejudicada. Um orçamento reduzido pode acionar IA para triagem em lotes (não por link). Validações puramente sintáticas/licenças/hashes nunca requerem LLM.

**Ferramentas determinísticas previstas (não contam como agentes):** scheduler, conector RSS/Atom/API/HTTP permitido, rate limiter, controlador por domínio/robots, registro de fontes/entidades/pessoas, downloader/extrator de texto público, normalizador de datas/URL, detector exato e heurístico de duplicação, detector de diff/hash/ETag, armazenamento e cache, índice/busca, catálogo de alegações, fila/outbox/dispatcher, guardião de permissões, verificador de schema/hash/citações, máquina de estados/revisões, renderizador, validador de composição, auditoria/telemetria. Alguns exigirão bibliotecas; preferir módulo enxuto reutilizável a criar microserviços.

**Não entram na primeira linha ativa:** agente comercial que negocia sozinho, agente de postagem/social com publicação, moderador autônomo de dados pessoais, robô publicador, agente de compras, podcaster e interface de atendimento privado. Devem ser definidos futuramente conforme blocos setoriais. Ter responsabilidade setorial não implica necessariamente agente de IA.

## 2. Contrato uniforme a implementar

`AgentRoleProfile` (imutável por run):
- `role_id`, `role_version`, `instructions_sha256`, `purpose`, `success_criteria`, `excluded_actions`, `input_schema`, `output_schema`;
- `allowed_tools` (nomes e escopos explícitos, não shell/rede irrestrita), `data_access`, `allowed_sources`, `time_budget`, `usage_budget`, `allowed_model_policy`, `request_research_allowed`, `max_iterations`;
- `handoff_targets`, `human_review_gate`, `failure_policy`, `quality_rubric`, `evaluation_fixture_refs`, `owner`.

`AgentTaskEnvelope`: `task_id`, `run_id`, `story_id`, `edition_id?`, `role_id/version/hash`, `persona_id/version/hash?`, `input_artifact_refs+hashes`, `source_snapshot_ids`, `authorized_tools`, `deadline?`, `context_schema_version`, `usage_guardrails`, `idempotency_key`, `correlation_id`, `requires_human_gate`. Nunca incluir credencial ou autorização fictícia.

`AgentResultEnvelope`: `task_id`, `status=completed|needs_more_research|revise|hold|blocked|uncertain`, `output_schema_version`, `artifact_ref+sha256`, `material_claims[{claim_id,evidence_ids,epistemic_status}]`, `requested_research?`, `open_questions`, `observed_constraints`, `input_hash`, `output_hash`, `model_used/effort` quando real, `usage_reported` quando fornecido, `created_at`, `next_action_suggestion`. Estado final do Motor é validado por código, não aceito por mero texto do LLM.

**Ordem de instruções:** regimento + contrato funcional do papel + instruções editoriais pertinentes + DNA narrativo somente para redação/persona + brief + pacote de fontes marcado como dados. Testes de injection impedem conteúdo externo de trocar papéis, gerar URL inventada, autorizar rede, excluir registros ou publicar.

## 3. Perfil `triage_analyst` — Analista de triagem

**Missão:** transformar `DiscoveryBatch` deduplicado em candidatos a pauta; separar anúncio, rumor, atualização, continuidade, correção e comunidade; avaliar novidade, impacto, potencial de apuração e categoria. **Não** escrever reportagem nem afirmar verdade do rumor.

**Entrada:** `batch_id`, itens com ID/url/publicador/pessoa citada/data, diffs, tópico, grupos de republicação e carteira da edição. Pode consultar apenas os recortes e metadados acessíveis, solicitar documentos por `ResearchRequest` se faltar origem.

**Saída:** `TriageDecision[]`: `cluster_id`, `topic_id`, `candidate_angle`, `newsworthiness_reason`, `source_independence_note`, `novelty_type`, `urgency`, `evidence_refs`, `missing_fields`, `suggested_lane=principal|reserva|monitoramento|descartar`, `confidence`. A decisão é proposta: política de carteira e direção decidem promoção.

**Conduta/falhas:** nunca converter reimpressões em confirmações, boato em certeza, viralidade em verdade; não avançar link sem proveniência. Zero novidade material pode gerar resultado vazio `no_change`. **Testes:** 10 portais repetem rumor de fonte única; release corrigido; conversa sem notícia; pauta principal já completa; rivalidade AAA/indie sem enviesamento.

## 4. Perfil `evidence_investigator` — Investigador de evidências

**Missão:** identificar autor original, origem e cadeia de republicação; encontrar documentação, contexto, interpretações divergentes e o que falta; preparar dossiê factual/rumor. **Não** escrever veredito estilizado, não simular entrevista ou benchmark.

**Entrada:** pauta/questões precisas, `ResearchPacket`, links, histórico de alegações, limites de busca. Pode solicitar `ResearchRequest` ao Radar via Motor, com objetivo, consultas, domínios preferenciais, versão/plataforma, `max_results`, orçamento/tempo. Pesquisas só em conectores permitidos.

**Saída:** `EvidenceDossier`: `claim_id`, formulação do que foi alegado, quem declarou, publicador, fonte original ou intermediária, URL/data, trechos curtos para verificação, `epistemic_status`, `confirmed_statement_vs_confirmed_content`, testes independentes e parâmetros, contradições, lacunas, fontes alternativas, `evidence_ids` e `blockers`. Evidência insuficiente deve ficar explícita.

**Testes:** rumor de remake repetido em múltiplos sites; declaração direta do produtor em entrevista versus comunicado institucional; review com média FPS e 1% low sem resolução; fontes conflitando por SKU; falso nome de fonte; artigo que mudou depois do crawl.

## 5. Perfil `assignment_editor` — Editor de pauta e estrutura

**Missão:** decidir **proposta editorial fundamentada** para narrativa de matéria e cobertura aprofundada, respeitando volume/edição e critérios de qualidade. Não substituir decisão de direção, não escrever como jornalista nem determinar prova técnica própria.

**Entrada:** `EvidenceDossier`, histórico/edição, carteira principal/reserva, `EditorialConstraints`, direitos/spoilers e `required_coverage`.

**Saída:** `EditorialBrief`: ângulo, gênero (notícia/rumores/investigação/análise/crítica/guia), perguntas, estado epistêmico, texto/estrutura por módulos, nível de profundidade, comparisons/specs/versions, fontes e lacunas, personagem adequado e justificativa, necessidades visuais (sem exigir arte sem licença), risco, `needs_more_research`. Estima extensão editorial como hipótese.

**Testes:** rumor sem confirmação ainda assim merecendo matéria; pauta fraca reservada; conflito com matéria passada; pauta transversal Carranca/Beto/Nina; lote de vinte candidatas para edição de dez sem “escrever vinte”.

## 6. Perfil `persona_writer` — Redator com assinatura aprovada

**Missão:** elaborar reportagem profunda com visão narrativa do jornalista escolhido sem inventar experiência própria, dados nem fontes. Diferenciar corpo investigativo e conclusão autoral; cada afirmação material vinculada a `evidence_id`. Requisitar pesquisa complementar se faltarem benchmarks/especificações/mecânicas/requisitos.

**Entrada:** `EditorialBrief`, `EvidenceDossier`, `WritingConstraints`, `persona_id` e **pacote DNA versionado/commit** do Bloco 02; nunca criar persona automaticamente. IDs canônicos: `ranzinza`, `beto-cartucho`, `nina-prisma`.

**Saída:** `StoryDraft` com título/dek/seções, citações e referências, distinção entre fato oficial, reportagem terceirizada e rumor, relato da comunidade, divergência de fontes, opinião identificada, figuras/necessidades visuais, lacunas, `requested_research` se exigido; rascunho sempre para checagem/revisão. **O redator deve poder emitir `ResearchRequest`** e aguardar resposta para continuar mesma revisão/pauta com checkpoint, sem pesquisar pela web como efeito lateral descontrolado.

**DNAs públicos:** Carranca (hardware rigoroso, sarcasmo com propósito, elogio/correção), Beto (experiência de jogos, história, diálogo hospitaleiro), Nina (experimentação, mods e comunidades, entusiasmo calibrado, cobertura AAA possível). Não colocar personalidade do cronista em checador/revisor.

**Testes:** matrizes T01–T16 por persona em duas trilhas: isolada (P/J) e na fábrica (P/J), com bibliotecas de audição como âncoras não copiáveis. Não afirmar execução por existir fixture.

## 7. Perfil `fact_checker` — Checador factual independente

**Missão:** mapear cada claim material do rascunho para evidências citadas, revisar atribuição, versão, contexto, metodologia, rumor versus confirmação, dados quantitativos, fonte primária e divergências; gerar `pass|revise|hold`. Nenhuma aprovação humana ou publicação.

**Entrada:** rascunho + hash da revisão corrente, `EvidenceDossier`, fontes preservadas e política editorial, sem depender da opinião do redator. Poderá pedir pesquisa ao Radar; nunca acrescentar fatos sem origem.

**Saída:** `FactCheckVerdict`: revisão+hash, status, item/trecho, severidade, `evidence_ids`, correção solicitada, lacunas, necessidade de refutação e testes futuros. `pass` não substitui revisor editorial.

**Testes:** 10 republicações de leak; número de VRAM sem SKU; alegação de 70/30 personagens sem origem; citação fabricada; `response.completed` ausente; texto alterado após aprovação.

## 8. Perfil `editorial_reviewer` — Revisor editorial

**Missão:** verificar legibilidade, estrutura, argumentação, acessibilidade, profundidade, transparência e aderência ao DNA do jornalista, sem perder rigor nem censurar crítica a anunciantes. Atua após checagem, em revisão **vigente**. Pode devolver `revise` ou `hold`.

**Entrada:** versão/hash do artigo, parecer factual, briefing e DNA por referência para verificar fidelidade, restrições de páginas/spoilers e política comercial.

**Saída:** `EditorialReview`: pass/revise/hold, defeitos e correções pontuais, avaliação de completude jornalística, identidade de persona, conflitos com fontes, observações de legibilidade. Revisão alterada invalida parecer anterior. **Não** autoriza publicação.

**Testes:** artigo soa Carranca mas é superficial; Nina hype sem fatos; Beto se apropria de gameplay de terceiros; reviewer altera texto sem novo hash; loop de correção limitado.

## 9. Opcional `media_researcher` — Curadoria semântica de mídias

**Missão:** propor que tipos de imagem/diagrama servem a cada parte da reportagem; localizar candidatos em inventário autorizado, sugerir legendas e justificativa funcional. **Não** declarar licença para mídia não verificada, baixar material restrito, gerar imagem ou aprovar direitos sozinho.

**Entrada:** seções/brief, `MediaInventory`, `RightsMatrix`, formatos/screen sizes, prioridades de informação; pesquisa externa somente por conector permitido.

**Saída:** `MediaNeedProposal` e candidatos com `asset_id`, provenance/autor, licença/uso, bloqueios, alternativa sem imagem e recorte/legenda. Gate de direitos permanece verificável por código e decisão humana.

**Teste de benefício:** superar solução determinística por taxa de figuras úteis/créditos certos/tempo, não por quantidade de imagens decorativas.

## 10. Opcional `layout_planner` — Planejador de composição

**Missão:** transformar `StoryPackage.v0` aprovado para prévia, `MediaInventory` elegível, regras do Bloco 03 e índice histórico de soluções em `LayoutPlan.v0` com organização editorial, alternativas mobile e justificativa de referências. **Não** renderizar por conta própria, alterar reportagem/fatos nem usar página histórica como cópia.

**Entrada:** seções semânticas, restrições de leitura e direitos, referência histórica curada, viewport/dupla e metas de informação; caso não possa ver mídia, usar descrições estruturadas sem fingir visão.

**Saída:** `LayoutPlan` validável, ids, blocos, tema/layout versionados, figura+legenda, responsive, visual provenance, alternativas e `completeness_check`. Código realiza paginação, HTML, integridade e verificador de composição.

**Teste de benefício:** qualidade de organização e utilização de mídia superior ao baseline determinístico sem sacrificar texto, acessibilidade, mobile e direitos.

## 11. Perfis de PESQUISA, não agentes LLM separados

O serviço determinístico compartilhado `research_service` aceita `research_profile`:
- `radar.general.v1`: fontes oficiais, portais, fóruns permitidos e comunicados, busca incremental agendada;
- `research.hardware.v1`: fichas fabricantes, SKUs, arquitetura, benchmarks independentes, métodos, drivers, FPS médio/1% low, VRAM, latência, resolução/preset;
- `research.games.v1`: publishers/estúdios, releases, trailers/documentação, mecânicas, versões, elenco, plataforma, lore verificável e análises de terceiros;
- `research.creators.v1`: indie, modding, repositórios, changelogs, permissões, entrevistas, declarações de criadores e comunidades.

Cada configuração inclui `profile_id/version`, fontes/dominios elegíveis, idioma, palavras-chave/entidades/sinônimos, tipos de documento, critérios de consulta, `max_requests/max_pages/max_bytes/time_budget`, latência/cadência, política de respeito ao serviço e `OutputResearchPacket`. Podem existir dezenas de perfis sem dezenas de motores/códigos ou LLMs. A solicitação do jornalista passa por Motor e guarda parent_task, hash, razão e resultado.

**Pessoas relevantes:** cadastrar diretor/produtor/dev/entrevistado como entidade pública (nome, variantes, cargo em período, empresa/projeto, fontes públicas e datas), sem rastrear dados pessoais privados. Entrevista citada pelo entrevistado não é automaticamente comunicado oficial da companhia.

## 12. Testes transversais e maturação

- **Técnico/contrato offline:** por papel, entradas válidas/inválidas, dados ausentes, ataques em fonte, rumos, idempotência, hash, retentativa, falta de direitos, revisor vigente e retorno da pesquisa.
- **Qualidade editorial por IA:** para papéis não narrativos, avaliar tarefa cumprida/precisão da proveniência, metodologia, campos completos, ausência de extrapolação, necessidade de pesquisa adicional, falso positivo/negativo e custo por saída útil.
- **Jornalistas:** dois ensaios separados e comparáveis; P (persona) e J (apurado) são eixos independentes. Os três perfis de busca complementam, não redefinem, o DNA aprovado.
- **Observabilidade:** `role_id`, `profile_version/hash`, `persona_id`, pesquisa solicitada, custo estimado ou uso reportado, tarefa anterior/próxima, tempo, status e revisão; segredos nunca em logs.
- **Critério de aceite:** não declarar “oito agentes criados e validados” ao gerar estes contratos. Primeiro implementá-los, testar com mocks e provar com modelo elegível sob uso autorizado; não deixar bloqueio de IA em um papel impedir todos os testes determinísticos independentes.
