# ENG-CODEX-009 — Banco de FONTES CANDIDATAS do Radar e regras de classificação
**Fundador 2 / 25/10/2026.** Esta é a primeira semente editorial documentada, NÃO uma allowlist pronta para scraper nem autorização de busca externa H05. A governança interna e o regimento da ENG-CODEX-007 prevalecem; Issue #35 autorizou SOMENTE consulta automática index-only nesta fase.

## Princípio
Fonte importante não significa verdade. A "autoridade" é sempre relativa ao **tipo de claim**: AMD é fonte primária para ficha anunciada, mas não para concluir comparação independente de FPS; review de site é fonte primária para o TESTE QUE ESSE SITE EXECUTOU, não para alegar que a revista o executou; postagem isolada é fonte primária do relato de usuário, não de que o defeito existe universalmente; declaração de produtor é fonte primária para O QUE ELE DISSE, não para o fato material afirmado. Rastrear cadeias e grupos de origem. Dez republicações da mesma notícia não são dez confirmações independentes.

## Catálogo inicial por classe — domínio, uso e gate
**A. Fabricantes, publishers e produtores de mods (primários para seus próprios anúncios/documentos)**
1. AMD especificações RX9050 8GB — https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9050.html — specs declaradas, disponibilidade/marketing separados; revisão/versionamento necessário.
2. AMD specs RX9050 4GB — https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9050-4gb.html — não confundir SKU com 8GB.
3. AMD press-room RI — https://ir.amd.com/news-events/press-releases/detail/1253/amd-introduces-new-radeon-graphics-cards-and-ryzen-threadripper-processors-at-computex-2025 — datas, preços sugeridos histórica e parceiros.
4. AMD developer / GPUOpen — https://gpuopen.com/learn/ — documentação técnica/método de renderização de fabricante, não benchmark neutro.
5. ASRock press-room — https://www.asrock.com/news/index.us.asp?iD=5827 — anúncio do SKU AIB, clocks e produto.
6. PowerColor press-room — https://www.powercolor.com/news-detail90.htm — anúncio produto e regiões; conferir disponibilidade e página antes de polling.
7. Sapphire product/news — https://www.sapphirenation.net/rx-9050-release — clocks e SKU; não atribuir modelos custom à referência.
8. Capcom IR — https://www.capcom.co.jp/ir/english/news/html/e250609.html — anúncio de jogo; PRESS RELEASE não é review.
9. Capcom Town / lançamento — https://store.captown.capcom.com/en/blogs/news/0000008 — comprovação de publicação.
10. Capcom IR vendas — https://www.capcom.co.jp/ir/english/news/html/e260316.html — indicador declarado; data e base são cruciais.
11. Steam página oficial da obra — https://store.steampowered.com/app/3764200/Resident_Evil_Requiem/ — descrição/requisitos oficiais, tags e avaliação agregada como META separado.
12. Praydog / código e README REFramework — https://github.com/praydog/REFramework — autoria, ferramentas, jogos declaradamente suportados.
13. Praydog / versões REFramework — https://github.com/praydog/REFramework/releases — releases e changelog; branch nightly pode ser diferente, revalidar.

**B. Testes independentes e avaliações especializadas (primário para medição/opinião do autor que testou, secundário para fatos de terceiros)**
14. TechSpot/Hardware Unboxed RX9050 — https://www.techspot.com/review/3162-amd-radeon-rx-9050-8gb/ — comparação de 10 jogos, método/presets, GPUs/SKU.
15. Tom's Hardware RX9060XT review — https://www.tomshardware.com/pc-components/gpus/amd-radeon-rx-9060-xt-16gb-review — laboratório próprio sobre 9060XT, não 9050.
16. Tom's Hardware notícia RX9050→GDM — https://www.tomshardware.com/pc-components/gpus/amds-new-radeon-rx-9050-is-roughly-30-percent-slower-than-the-rtx-5050-in-games-early-testing-shows-the-cheapest-8gb-rdna-4-gpu-comfortably-handles-1080p-gaming-but-doesnt-impress — republica medições japonesas GDM; seguir fonte original antes de atribuir resultados.
17. PC Gamer campanha Requiem — https://www.pcgamer.com/games/resident-evil/resident-evil-requiem-review/ — opinião crítica + hardware de teste declarado.
18. GameSpot review Requiem — https://www.gamespot.com/reviews/resident-evil-requiem-review-two-headed-mutant/1900-6418464/ — crítica da costura entre modos.
19. TechRadar review Requiem — https://www.techradar.com/gaming/resident-evil-requiem-review — contraponto ritmo/segundo ato; spoilers controlados.
20. PC Gamer performance Requiem — https://www.pcgamer.com/hardware/resident-evil-requiem-pc-performance-analysis-great-visuals-and-decent-frame-rates-all-round-though-path-tracings-an-obvious-frame-rate-killer/ — versões/presets/RTX diferentes da G11.
21. DSOGaming benchmark Requiem — https://www.dsogaming.com/pc-performance-analyses/resident-evil-requiem-pc-performance-analysis/ — raster específico e metodologia detalhada.
22. Digital Foundry performance — https://www.youtube.com/watch?v=QwGzu2Tdl-Q — canal oficial/vídeo, conferir conteúdo antes de extrair números.
23. PCWorld RX9050 — https://www.pcworld.com/article/3200962/amd-reveals-the-radeon-rx-9050-and-4gb-graphics-cards-are-back.html — jornalismo sobre lançamento/OEM/preços históricos, sem benchmark próprio relatado nesta peça.
24. GameSpot panorama de mods — https://www.gamespot.com/gallery/best-resident-evil-requiem-mods/2900-7573/ — curadoria/opinião, não garantia técnica.

**C. Agregadores/comunidade (observação, hipótese, nunca confirmação por contagem)**
25. Metacritic reviews PC Requiem — https://www.metacritic.com/game/resident-evil-requiem/critic-reviews/?platform=pc — índice de terceiros, ler fontes originais.
26. Steam reviews e score — https://partner.steamgames.com/doc/store/reviews — metodologia oficial sobre filtros e origem; datas, aquisição, idioma e atualizações de avaliações.
27. Steam reviews interface API docs — https://partner.steamgames.com/doc/webAPI/IUserReviewsService — não usar key/publisher key privado; acesso sujeito a termos, quotas e configuração.
28. Nexus Mods categoria Requiem — https://www.nexusmods.com/games/residentevilrequiem/mods — uploads de autores + comentários e ranking com filtros, direitos/termos.
29. Nexus Mods policy API — https://help.nexusmods.com/article/114-api-acceptable-use-policy — obrigações de acesso/limites; **não assumir API liberada para produção** por existir documentação.
30. GitHub issues REFramework #1635 — https://github.com/praydog/REFramework/issues/1635 — usuário relata crash build específica; comentários, resoluções, logs sensíveis e versão.
31. GitHub issues REFramework #1678 — https://github.com/praydog/REFramework/issues/1678 — relato após patch, encerramento não é prova de correção.
32. GitHub issues REFramework #1571 — https://github.com/praydog/REFramework/issues/1571 — relato de conflito técnico contextual.
33. Nexus Mods lista da comunidade — https://www.nexusmods.com/residentevilrequiem/mods/top — ordenação, popularidade, autoria e mod dependentes sob amostragem.
34. Reddit — **candidato sem endpoint nem coleta liberada**. Identificar comunidades apropriadas por assunto e seus termos, registrar autoria/horário e amostra; nunca inventar número de comentários ou consenso; não coletar dados pessoais.
35. Fóruns técnicos de fabricantes — **candidatos futuros sujeitos a reconhecimento manual**. Thread individual sempre relato, com driver/OS/presets, sem extrapolar prevalência.

## Pipeline de ingestão proposto (projeto futuro, não ATIVAR agora)
**Descoberta:** candidato editorial → verificação de nome/domínio/afiliado/autor/tipo de mídia e finalidade → terms/robots/API, limites e quotas por host → perfil de conector autorizado (feed/RSS/API/HTML permitido) → cache + ETag/Last Modified → SHA e snapshot/horário/versionamento → derivação de claims com fontes/trechos mínimos e evidência licenciada → agrupamento de republicações por origem → triagem de conflito/rumor/atualização → ResearchPacket com lacunas.

**Campos de cada item (planejar v1, sem migração runtime):** source_id, owner_name, original_url, canonical_url, source_type (manufacturer_release, product_specs, benchmark_original, reprint_of_benchmark, review_opinion, dev_changelog, author_issue, community_report, aggregator), claim_scope, authored_at, observed_at, content_version/hash quando disponível, author, original_creator_id, group_origin_id, based_on_source_id, language, region, game_build/SKU/driver/OS/resolution/preset/API, usage_rights, robots_status, API_terms_status, connector_id, polling cadence, priority, confidence_of_attribution, epistemic_status, allowed_claims, warnings, last_verified, quarantine.

**Ranking:** alta prioridade para documento primário na afirmação que ele controla; resultados independentes experimentais com metodologia clara para medição; fonte conflitante NUNCA é descartada só por contradizer oficial; notícia repercutida não vira confirmação múltipla. Para fóruns, verificação de um relato significa que foi reportado (não que causa/efeito geral foi demonstrado). Não ocultar conflito ou opinião minoritária bem fundamentada.

**Direitos e segurança:** link/citação sucinta e paráfrase própria; nunca republicar artigos, gráficos, benchmarks completos e imagens sem direitos; screenshots do autor de mod dependem de licença. No repositório PÚBLICO, só índice de fonte e resumos próprios. URLs de usuários não viram comandos de ferramentas/LLM, nem permissões; query result sempre dado não confiável. Sem scraping agressivo, burlar paywall ou login pessoal, copiar chaves/tokens de Nexus/GitHub/Steam, nem downloads de binários para teste.

## Decisão da diretoria já vigente (Issue #35)
- H05 **agora**: roteamento automático **somente local** com read:radar_index, ResearchService provider=None, sem exigir microaprovação para consultas legítimas. Dados insuficientes retornam partial/not_found/hold, não “prova”.
- Futuro, APÓS aprovação de políticas por origem: fontes públicas registradas podem ser pesquisadas autonomamente dentro dos limites e termos do conector, sem pedir aprovação por consulta; exceções/custos/escopo novo pedem autorização.
- Este catálogo é apenas **candidatos à validação e expansão**, não concede permissão de rede nem é justificativa para colher todos os links automaticamente.

**Próxima curadoria (antes de operar Radar 24/7):** ampliar a lista para dezenas de provedores especializados cobrindo também launchers, estúdios indies, hardware de referência, pesquisas de acessibilidade, patch trackers e comunidades com atribuição. Começar por fonte individual, avaliar termos e atualização; não inferir que todos os domínios listados são permissivos para robôs.