# ENG-CODEX-007 — E16: leitura pública controlada

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E16
- **Versão:** v0.1
- **Status:** validado localmente; uma leitura pública manual concluída
- **Data de atualização:** 2026-10-25 19:57 America/Sao_Paulo
- **Dependências:** conector público E05; política de origem E09; ordem contínua E01–E19 na Issue #28
- **Aprovador:** autorização de execução já registrada na Issue #28; sem decisão de republicação de conteúdo

## Objetivo e exclusões

Executar manualmente uma única leitura de metadados em uma API pública, sem autenticação, chave nova, custo, polling ou scheduler. A resposta integral não foi salva nem reproduzida. O conector guardou apenas a projeção de metadados permitidos, a URL e o SHA-256 do corpo recebido.

Este ensaio comprova uma chamada pública controlada do conector. Não comprova licença para republicar notas de versão, acesso contínuo, homologação de outras origens ou operação agendada.

## Origem e política conferidas

- **Origem:** API REST pública do repositório `godotengine/godot`, identificada pela documentação oficial do Godot como seu repositório de código-fonte: https://docs.godotengine.org/en/4.4/contributing/development/compiling/getting_source.html
- **Endpoint consultado:** `GET https://api.github.com/repos/godotengine/godot/releases/latest`.
- **Documentação do endpoint:** a documentação oficial da API declara que releases publicados são públicos e que o endpoint pode ser usado sem autenticação quando a solicitação é por recurso público: https://docs.github.com/en/rest/releases/releases#get-the-latest-release
- **Termos:** a API está sujeita aos Termos de Serviço do GitHub, seção H; os termos proíbem abuso e excesso de frequência, e não foi usado nem compartilhado token: https://docs.github.com/en/site-policy/github-terms/github-terms-of-service#h-api-terms
- **Robots:** `GET https://api.github.com/robots.txt` respondeu **404** em 2026-10-25 19:56:26 -03:00. O RFC 9309 classifica respostas HTTP 4xx como indisponibilidade do arquivo robots e permite ao crawler acessar recursos do servidor. O perfil normalizou esse resultado para uma regra equivalente a `User-agent: *` / `Allow: /`; essa linha é uma representação local da semântica do 404, não conteúdo retornado pelo servidor: https://www.rfc-editor.org/rfc/rfc9309#section-2.3.1.3
- O `robots.txt` de `github.com` recomenda usar a API em vez de rastrear as páginas HTML. A solicitação de conteúdo foi somente ao host separado `api.github.com`: https://github.com/robots.txt
- **Limite:** a documentação informa 60 solicitações REST por hora para acesso não autenticado a dados públicos. O perfil exige intervalo mínimo de 3.600 segundos e foi executado uma vez, sem retry. A resposta do endpoint de dados não expôs cabeçalhos de quota na interface segura do transporte; portanto, não se afirma saldo pós-consulta. A resposta 404 do `robots.txt`, anterior à leitura, mostrava `limit=60`, `remaining=56`, `used=4`; esse registro é do preflight e não é atribuído à resposta do endpoint de releases: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api

## Execução e resultado observado

O perfil `SourceProfile` usado pelo `RadarConnectorService` foi restrito a `api.github.com`, operação `api_metadata_read`, HTTPS, timeout de 15 s, corpo máximo de 1.000.000 bytes, zero redirects, uma falha permitida e intervalo mínimo de 3.600 s. Não foi fornecido cabeçalho Authorization nem token. Foi feita uma única chamada ao conector, usando `PinnedHTTPTransport`, validação DNS/IP pública e TLS padrão.

Resultado real observado em **2026-10-25 19:57:08 -03:00**:

| Campo | Resultado |
|---|---|
| Estado do conector | `observed` |
| HTTP | `200` |
| Content-Type | `application/json` |
| Redirects | `0` |
| ETag | `W/"fde8c980e3f83daefb57aa66a228594725493bc737e73060a3a78187e0eea226"` |
| Last-Modified | `Sat, 22 Aug 2026 14:27:33 GMT` |
| Metadados projetados | `id=372486926`; `name=4.7.2-stable`; `published_at=2026-08-18T16:12:28Z`; `updated_at=2026-08-22T14:27:33Z`; `url=https://api.github.com/repos/godotengine/godot/releases/372486926` |
| SHA-256 do corpo recebido | `a3ada3c2c833631fcdd9221c4a86807886c95c994bbfc89abd87f1f369d0baad` |

Não houve resposta 403 ou 429. O parser `project_public_api_metadata` descartou campos de conteúdo, como `body` e assets; o corpo bruto não foi impresso, gravado em arquivo, incluído em Git ou republicado.

## Validação, limites e pendências

- A política de acesso foi conferida nas fontes oficiais acima; robots do host `api.github.com` retornou 404; a API pública respondeu 200.
- Em CPython 3.11.9, `& '.\\.venv\\Scripts\\python.exe' -m unittest motor_editorial.tests.test_radar_connectors -q` passou com **13/13 testes em 0,701 s**; `compileall -q motor_editorial` e `git diff --check` terminaram com exit 0. Os testes são locais e usam transporte/fixtures de teste.
- O resultado sanitizado contém metadados públicos e hash; a hash não substitui licença nem autentica a autoria do conteúdo.
- Foi uma execução manual, sem scheduler, repetição, credencial, modelo, SIWC/Plus, API faturada, banco runtime ou publicação. `published=false`.
- O transporte atual não expõe `X-RateLimit-*` no conjunto de cabeçalhos seguros; não há saldo da quota após o GET. Próximas coletas precisam de novo preflight e de limite persistido por domínio; este ensaio não habilita polling recorrente.
- Direitos para reprodução de texto/ativos permanecem fora do escopo e não foram presumidos.

## Próxima unidade

E17 permanece bloqueada para chamadas SIWC/Plus reais pela instrução atual do usuário, mesmo com franquia disponível. A sequência continua com documentação e testes offline E18/E19, sem simular resultados como inferências reais.
