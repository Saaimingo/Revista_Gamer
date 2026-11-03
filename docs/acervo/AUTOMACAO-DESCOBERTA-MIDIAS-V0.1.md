# Descoberta e ingestão autorizada de mídia editorial — estudo v0.1

- **Setor responsável:** Bloco 05 — Acervo Editorial
- **Identificador:** ACERVO-AUTOMACAO-001
- **Versão:** 0.1
- **Status:** proposta / pesquisa e arquitetura conceitual (NÃO implementada)
- **Data:** 2026-10-25
- **Aprovador:** direção, pendente; implementação futura Codex com missão específica
- **Dependências:** `MAPA-FONTES-IMPRENSA-V0.1.md`, `FICHA-MIDIA-MODELO.md`, `AGENTS.md`, governança e limites do Motor Editorial
- **Exclusões:** sem criar contas, adquirir serviços, compartilhar credenciais, ativar coleta real, baixar acervos, driblar autenticação/antibot, publicar ou conectar a produção.

## Descoberta x acesso x licença x publicação

São **quatro gates separados**:
1. Detectar anúncio/asset candidato (metadados: título, URL, data, publisher, ID do jogo);
2. Poder acessar legalmente o portal/API/arquivo (público, conta de imprensa aprovada, contrato, feed autorizado);
3. Comprovar direitos para modalidade específica (web editorial; capa; PDF; redes; corte e diagramação; composição; animação/IA; vídeo embutido);
4. Liberar após revisões de embargo, qualidade, crédito, precisão e aprovação editorial humana.

Nenhum `200 OK` HTTP, CDN acessível, token válido, scraping possível ou banco de imagens estabelece o gate 3.

## Fontes de descoberta programática verificadas documentalmente

| Mecanismo | URL/documentação | Uso potencial | Restrição / estado de validação |
|---|---|---|---|
| Games Press RSS de manchetes | https://www.gamespress.com/News/RSS | Identificar candidatos / links para publishers | FAQ: feed para referência pessoal; **proibido republicar o feed**; uso por pipeline automatizado interno ainda requer checar termos/obter concordância quando necessário. Não assumir autorização para redistribuir feeds/dados. Não testado. |
| Games Press Combo RSS | https://www.gamespress.com/Files/ComboRSS | Novidades de assets | Idem; evitar downloads sistemáticos. Não testado. |
| Games Press alertas por e-mail | https://www.gamespress.com/nl/FAQ---Use-of-Assets | Digest de PR | Apenas entrega autorizada ao destinatário; processar caixa própria com permissão; não publicar texto/arquivos automaticamente. |
| EA Press Release RSS | https://news.ea.com/media-resources/rss-feeds/default.aspx | Headlines/releases EA | Existe feed anunciado; endpoint XML específico ainda não extraído/testado. |
| Steamworks ISteamNews/GetNewsForApp v2 | https://partner.steamgames.com/doc/webapi/ISteamNews | Notícia oficial por Steam AppID | Endpoint público documentado; **GetNewsForAppAuthed exige chave do publisher** e não deve ser usado sem titularidade. Não confundir notícias com direito de arte da Steam. |
| IGDB API / Twitch | https://api-docs.igdb.com/ | Resolver nome/aliases/IDs de jogos, empresas, datas e imagens como metadados | OAuth app Twitch; parceria comercial declarada, atribuição; **não presume direito de publicar capa/foto contida**. Licenciamento/atribuição comercial a verificar antes de produção. |
| n8n RSS Feed Trigger | https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.rssfeedreadtrigger/ | Orquestração eventual de RSS autorizado | Software conector, não licença ou fonte. Sem deploy/teste nesta rodada. |
| Miniflux RSS API | https://miniflux.app/docs/api.html | Assinar feeds com histórico, leitura por API e deduplicação | Software, não fonte/direito. Credenciais protegidas; não testar até ordem. |

**Ferramentas do ecossistema indie:** presskit() https://www.dopresskit.com/ e presskit.gg https://presskit.gg/ permitem que estúdios publiquem press kits. Não representam APIs globais de consumo de kits.

**Plugins/MCPs:** pesquisa no diretório de plugins ChatGPT por `games press media assets video game press release newsroom RSS API` não identificou plugin especializado/instalável claramente correspondente. **Isso não demonstra inexistência de MCP de terceiros.** Não foi localizado nem validado endpoint oficial público de API do Games Press para ingestão editorial nesta rodada; canal de contato para negociar permissão: mail@gamespress.com (publicado no FAQ). Um MCP, caso venha a existir, é camada de integração: não altera termos da origem, autenticação nem licença.

## Fluxo candidato para avaliação do Codex (não autorizado a executar)

1. **Monitoramento condicionado a autorização:** feeds oficiais e APIs documentadas do catálogo. Usar horários e limites por fonte definidos futuramente, HTTP ETag/Last-Modified quando suportados. Não inventar endpoints, nem inferir permissão de crawl de ser indexável.
2. **Normalização:** identificador único `source_id + external_id/url`, timestamp de primeira publicação, URL canônica, hash de metadados, empresa detentora, jogo, territórios, idioma, tags e possíveis duplicatas. Preservar original e link; sem reproduzir release integral automaticamente.
3. **Correlação:** resolver jogo e publisher efetivo, deduplicar posts replicados por Xbox/PlayStation/Games Press, reconhecer quando publisher diferente detém material.
4. **Busca de asset:** consultar *apenas* páginas de mídia com acesso permitido. Preferir manifestos, API oficial, feeds, links de ZIP fornecidos na página, armazenamento de URLs e thumbnails autorizadas; não acessar pastas privadas, endpoints não documentados, tokens ocultos, cookies alheios, contornar CAPTCHA, usar contas falsas nem descarregar acervo inteiro.
5. **Gate de direitos:** `PENDENTE` por padrão; registrar prova (URL da política, data, trecho aplicável, licença, titular, créditos, restrições e embargo). Categorização: `editorial_web`, `capa_revista`, `pdf`, `redes`, `recorte`, `composicao`, `ia_derivada`, `embed`. Uma permissão de reprodução sem modificação não autoriza geração de arte derivada.
6. **Ingestão sob demanda:** apenas arquivo necessário à matéria e explicitamente permitido. Verificar malware/ZIP, hashes, MIME real, espaço, retenção, redimensionamento permitido, backups e retirada/revogação. Guardar mídia fora do Git e chaves fora do repositório.
7. **Handoff editorial:** oferecer ao jornalista/Codex fontes e assets com status; apenas mídias aptas à modalidade pretendida seguem ao layout; embargo até data e hora aplicáveis; antes de publicar revisão humana.
8. **Auditoria:** provenance, tentativas de acesso, arquivos associados, decisões e revisões; bloquear automaticamente em 403/401, mudança de política, crédito incerto ou revogação. Não tentar renovar/burlar acesso sem permissão.

## Exemplo operacional: novo anúncio de Santa Monica Studio

- Alerta de fonte oficial (PlayStation Blog / SIE, ou PlayStation Press Center mediante conta aprovada).
- Indexação da notícia, vínculo ao estúdio, publicação no ecossistema PlayStation e localização do material de imprensa da **obra específica**.
- Primeiro resultado possível: `press_page_url`, `asset_candidates` e `rights=PENDENTE`. Se conta aprovada oferecer download individual e termos claros, registrar evidência e avaliar web/capa/edição.
- Texto investigativo de terceiros é atribuição do Bloco 04, não do Bloco 05. Sem automatizar publicação nem afirmar que a produtora tenha liberado artes editáveis.

## Gate Games Press (achado prioritário)

FAQ https://www.gamespress.com/nl/FAQ---Use-of-Assets informa RSS e digest, mas exige que o RSS não seja republicado; não recomenda downloads automáticos em massa; os termos https://www.gamespress.com/pt/Site/TermsAndConditions?popup=True proíbem extração massiva automatizada sem consentimento prévio. **A automação certa aqui é descoberta/triagem, não espelhamento.** Antes de criar um coletor robusto, confirmar por escrito limites/tipos permitidos de acesso programático. Games Press Pro não deve ser presumido como licença de scraping irrestrito.

## Critérios de aceite propostos para piloto futuro

- Verificar com fonte autorizada 3 casos: grande publisher, estúdio Sony e indie; usar dados simulados se não houver autorização real.
- Diferenciar `descoberto`, `acessivel`, `licenca_documentada`, `apto_modalidade`, `publicado`.
- Sistema recusa publicação quando `PENDENTE`; deduplica anúncio repetido; preserva crédito e link; respeita embargo; usa conta autorizada sem salvar senha no Git; teste de revogação e erros 403/429.
- Usar no máximo os recursos já aprovados; nenhum serviço pago por inferência.

## Fontes e limitações

- https://www.gamespress.com/nl/FAQ---Use-of-Assets
- https://www.gamespress.com/pt/Site/TermsAndConditions?popup=True
- https://partner.steamgames.com/doc/webapi/ISteamNews
- https://api-docs.igdb.com/
- https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.rssfeedreadtrigger/
- https://miniflux.app/docs/api.html
- https://regulations.cdprojektred.com/en/press_regulations
- https://www.bandainamcoent.com/press-center

**Sem implementação / sem testes de rede por agente:** apenas pesquisa pública documental em 2026-10-25. É necessário acesso de imprensa real e validação jurídica/editorial antes de qualquer uso concreto.
