# ENG-CODEX-007 — E05: conectores de leitura pública

- **Setor responsável:** Engenharia e Codex
- **Identificador:** ENG-CODEX-007-E05
- **Versão:** v0.1
- **Status:** implementado e validado localmente; revisão da PR de implementação pendente
- **Data de atualização:** 2026-10-25 14:13 America/Sao_Paulo
- **Autorização:** Issue [#28](https://github.com/Saaimingo/Revista_Gamer/issues/28), execução contínua E01–E19
- **Dependências:** `SourceProfile` de conectores E05 e armazenamento isolado E04; sem ativação de scheduler

## Resultado

Foi adicionado `motor_editorial/radar_connectors.py` com perfis explícitos de leitura RSS/Atom, API JSON pública e páginas HTML públicas; serviço de consulta de uma chamada; transporte HTTP(S); controle de política; e extração limitada a metadados. A chamada é sempre explícita: não há polling automático nem conexão ao scheduler.

O perfil fica bloqueado por padrão. Para buscar, exige `access_policy=allowed`, data de revisão dos termos, política/snapshot robots aprovado por host e operação específica na allowlist. Um perfil ausente ou incompleto não resolve DNS e não abre conexão. Os snapshots robots são configuração de entrada: este conector não busca `robots.txt` automaticamente nem decide se termos/licença autorizam operação. A próxima etapa de ensaio real precisa verificar cada origem permitida antes de configurar o perfil.

### Limites de rede e conteúdo

- Produção aceita somente HTTPS na porta 443, valida certificados com o contexto TLS padrão e conecta ao IP público validado depois de DNS. O IP fica pinado naquela requisição; todos os endereços retornados precisam ser globais. Proxy de ambiente, login, credencial, cookie e método diferente de GET não são usados.
- Host é comparado a uma allowlist exata por perfil. Cada redirect é revalidado quanto a esquema, host, IP e regras robots; hosts permitidos em outro domínio exigem snapshot robots próprio e passam pelo limitador daquela origem. `ETag`/`Last-Modified` condicionais não são encaminhados a outra origem.
- HTTP sem TLS só pode ser ligado explicitamente em modo de teste e para IP literal loopback. Não há exceção para HTTP público.
- Timeout é configurável entre 0,1 e 30 segundos; corpo entre 1 byte e 5 MB; redirects entre zero e cinco. Resposta excedente é descartada. `Retry-After`, backoff exponencial limitado, intervalo mínimo por origem, limite de falhas e suspensão evitam repetição ilimitada.
- Query params comuns de credencial/assinatura, userinfo, fragmentos e credenciais reconhecidas em textos são recusados. Respostas 401/403 suspendem a fonte; 404/410 registram link removido; 429 aplica cooldown de origem; 5xx e erros transitórios recebem retry limitado.
- `FetchResult` não expõe o corpo HTTP bruto. RSS/Atom retorna título, link seguro, ID e data; HTML retorna título, canonical same-host e links HTTPS de referência; API JSON retorna uma projeção de campos metadata (`id`, `title`, `name`, versão, data, estado, etc.) e omite `description`, `body`, `content`, artigo, HTML e outros campos de conteúdo. DTD e entidades XML são bloqueadas.

O estado de suspensão, backoff e quota é volátil em memória dentro de `RadarConnectorService`; não há worker ou processo agendado. E09/E06 precisam persistir/recuperar esses estados antes de qualquer operação contínua.

## Arquivos entregues

- `motor_editorial/radar_connectors.py` — `SourceProfile`, `RadarConnectorService`, transporte com IP pinado, limitador por origem, políticas e parsers de metadados.
- `motor_editorial/tests/test_radar_connectors.py` — 12 testes focados, sem consulta a hosts públicos.
- `docs/engenharia/ENG-CODEX-007-E05-CONETORES-LEITURA-PUBLICA.md` — este relatório.
- `docs/engenharia/ENG-CODEX-007-CHECKPOINT.md` — evidências persistentes e próxima unidade.
- `docs/engenharia/README.md` — índice e estado da sequência.

## Validação executada

Ambiente: CPython 3.11.9 do `.venv`, Windows.

- `& '.\.venv\Scripts\python.exe' -m unittest motor_editorial.tests.test_radar_connectors -v` → **12/12 OK**, 0,531 s.
- `& '.\.venv\Scripts\python.exe' -m unittest discover -s motor_editorial/tests -q` → **136/136 OK**, 88,750 s.
- `& '.\.venv\Scripts\python.exe' -m compileall -q motor_editorial` → exit 0.
- `git diff --check` e `git diff --cached --check` → passaram.
- Testes cobrem bloqueio por ausência de perfil/termos/operação/robots; caminhos robots proibidos antes de DNS/fetch; redirects e DNS rebinding; limites por host em redirects cruzados; TLS configurado e transporte HTTP apenas no servidor loopback de teste; 200, 304, 403, 404/410, 429, 500; `Retry-After`, backoff, suspensão, timeout e tamanho; ETag condicional; RSS/Atom, API JSON e HTML sem corpo bruto; URLs com credenciais e links hostis.
- Transportes e DNS públicos foram simulados. Um único teste executou HTTP contra `127.0.0.1` para provar o transporte limitado. Nenhuma origem pública foi consultada.

## Limites e riscos conhecidos

Não houve cadastro ou revisão real de fonte, consulta pública, login, credencial, API paga, SIWC/Plus, scheduler, publicação, deploy ou merge. `robots_rules_by_host` precisa receber snapshot verificado por alguém autorizado; sua presença não é prova automática de termos, direito autoral ou licença. Suspensão/backoff não persistem a reinício. E16 fará a primeira validação controlada de origens concretas; bloqueio de uma origem não bloqueia o restante offline.

Não houve alteração de DNA; `published=false`.

## Commit e próximo passo

- Código e testes: `313baeeb1384354189c49a2a3ec206dc8a428ae1` (`feat: add policy-gated Radar connectors`), enviado à branch `codex/eng-codex-007-factory-radar`.
- PR draft de implementação: [#30](https://github.com/Saaimingo/Revista_Gamer/pull/30), sem merge.
- Próxima unidade: **E06 — coleta incremental, cache, ETag/diff e deduplicação conservadora**.
