# Relatório de implantação — Motor Editorial v0.1

**Status:** implementação v0.1 validada tecnicamente no Windows 11 nativo e revalidada em 16/10/2026. O PR #3 foi integrado pelo proprietário do repositório em 17/10/2026 00:45:16 UTC (16/10/2026 21:45:16 BRT), no merge commit `525ae351d1e7375821435efeb1e012955785f69d`. A integração do código não autoriza operação editorial de produção ou publicação.

## Entrega

Foi implementado um aplicativo Python local, sem dependências de terceiros, com orquestração determinística, persistência SQLite, arquivos de prévia no disco, CLI e painel HTTP limitado a `127.0.0.1`. O conjunto inclui fixture inteiramente fictícia, máquina de estados, tentativas limitadas, trilha de auditoria, revisão versionada, decisão de direitos e aprovação humana exclusivamente interna. Após as correções da revisão do Pull Request, o SQLite usa o esquema v2 e migra automaticamente o esquema v1, preservando as decisões de mídia existentes como obrigatórias por padrão.

A primeira chamada de demonstração gera uma falha temporária injetada e fica pronta para retomada. A chamada seguinte termina com uma edição em `awaiting_approval`. O operador pode revisar o HTML e registrar a aprovação interna pelo painel ou pelo CLI. A v0.1 rejeita fixtures com mais de uma pauta selecionável antes de criar dados; uma segunda reprovação editorial encerra a execução em `failed_intervention`, com evento auditável. Não há scraping, IA, API externa, automação programada, upload ou rota de publicação.

## Estrutura persistida

O SQLite cobre fontes, itens de entrada, pautas e fontes associadas, pacotes de apuração, revisões de matéria, resultados de revisão, ativos e decisões de mídia, edições e matérias incluídas, tentativas de execução e eventos de auditoria. Restrições de estado e chaves estrangeiras protegem as transições e relações. Arquivos da execução ficam na pasta de dados local, fora do controle de versão.

## Validação nativa — Windows 11

Executada em **16/10/2026 (America/Sao_Paulo)**, no repositório local `Revista_Gamer`, branch `codex/motor-editorial-v0.1`, PR [#3](https://github.com/Saaimingo/Revista_Gamer/pull/3). O registro de eventos do motor usa UTC; por isso os eventos da demonstração aparecem datados de 17/10/2026 UTC.

Ambiente observado: Microsoft Windows 11 Home, versão `10.0.26200`, Windows PowerShell `5.1.26100.9711`, CPython `3.11.9` executado pelo launcher `py -3.11`.

```powershell
py -3.11 -m compileall -q motor_editorial
py -3.11 -m unittest discover -s motor_editorial/tests -v
```

Compilação concluída sem erros e **11/11 testes aprovados**. A primeira execução nativa identificou que a fixture do teste de migração deixava uma conexão SQLite aberta; no Windows, isso impedia a remoção do banco temporário (`WinError 32`). O teste agora fecha explicitamente a conexão após confirmar a fixture v1. A lógica de migração do motor não precisou de alteração.

Durante o smoke test do painel, o `HTTPServer` sequencial deixou clientes HTTP adicionais esperando enquanto o navegador mantinha conexões loopback abertas. O servidor foi substituído pelo `ThreadingHTTPServer` da biblioteca padrão; continua em processo local único, limitado a `127.0.0.1`. Após a correção, os clientes de linha de comando e o navegador responderam normalmente.

Em pasta exclusiva sob `$env:TEMP` (nome `revista-gamer-motor-aceite-20261016-<GUID>`), os comandos abaixo foram executados em processos separados:

```powershell
$dataDir = Join-Path $env:TEMP 'revista-gamer-motor-aceite-<GUID>'
py -3.11 -m motor_editorial --data-dir $dataDir init
py -3.11 -m motor_editorial --data-dir $dataDir demo
py -3.11 -m motor_editorial --data-dir $dataDir demo
py -3.11 -m motor_editorial --data-dir $dataDir status
py -3.11 -m motor_editorial --data-dir $dataDir status
```

`init` criou o banco local. A primeira chamada a `demo` terminou em `recoverable_failure` por falha transitória simulada na apuração: 4 itens, 1 duplicata, 1 pauta, 0 revisões, 0 edições, 10 eventos e 3 tentativas. A segunda chamada retomou a mesma execução e terminou em `awaiting_approval`: 4 itens, 1 duplicata, 1 pauta, 2 revisões, 1 edição, 33 eventos e 10 tentativas. As duas consultas `status` foram idênticas, confirmando persistência entre processos, uma única edição e nenhuma duplicação na retomada.

Na revisão editorial, a versão 1 foi devolvida pela afirmação fictícia sem fonte; a versão 2 foi corrigida e aprovada por uma nova passagem de revisão. Na política de mídia, o ativo fictício autorizado para `editorial_preview` foi incluído; o ativo obrigatório com permissão `pendente` foi substituído por placeholder, sem incorporar seu arquivo. A prévia mostra as fontes fictícias e o estado de direitos.

A aprovação interna foi verificada pela suíte automatizada: exige a versão atualmente revisada e a frase explícita, grava o ator e o evento no SQLite, e o teste da rota de painel registra o estado apenas em banco temporário. **Nenhuma aprovação foi registrada na demonstração aberta desta validação**: ela permanece em `awaiting_approval` para uma decisão humana real.

O painel foi iniciado em `http://127.0.0.1:8765/`, com listener observado em `127.0.0.1:8765`. A inspeção visual no Chrome cobriu painel, detalhe da pauta, as versões 1 e 2, direitos de mídia e prévia interna. A tela exibe a ação de aprovação humana e identifica a simulação como “SIMULAÇÃO — NÃO PUBLICAR”. O GET do painel, do detalhe e da prévia retornou 200; GET e POST para `/publish`, este último com token CSRF válido, retornaram 404. A rota não existe e nenhum conteúdo foi publicado. O painel foi deixado em execução e a aba aberta para conferência local.

### Reexecução de confirmação — 16/10/2026, 22:01 BRT

Revalidado no mesmo commit de código `a9ab17bb5f6106b72707682a77db9c7ee2e05c71`, em Windows 11 Home build 26200 com CPython 3.11.9. `py -3.11 -m compileall -q motor_editorial` passou e `py -3.11 -m unittest discover -s motor_editorial/tests -v` passou **11/11 testes** (5,442 s). A demonstração foi repetida numa pasta temporária isolada: a primeira chamada terminou em `recoverable_failure` (4 itens, 1 duplicata, 1 pauta, 0 revisões, 0 edições, 10 eventos, 3 tentativas); a segunda retomou para `awaiting_approval` (4 itens, 1 duplicata, 1 pauta, 2 revisões, 1 edição, 33 eventos, 10 tentativas). Duas chamadas consecutivas a `status` retornaram o mesmo estado e contagens.

Na inspeção atual do Chrome, o painel, o detalhe da pauta e a prévia responderam em `127.0.0.1:8765`; foram vistos a reprovação da versão 1, a aprovação da versão 2, o ativo permitido e o placeholder para mídia pendente. GET do painel, do detalhe e da prévia retornaram 200; GET e POST para `/publish` retornaram 404. A suíte automatizada valida a confirmação deliberada, a revisão vigente e o registro auditável da aprovação interna. A demonstração desta reexecução ficou em `awaiting_approval`: nenhuma aprovação foi registrada em nome de uma pessoa real.

## Validação anterior — Linux

Na rodada anterior, o código também foi compilado e os 11 testes passaram em Linux x86_64 com Python 3.12.14. A demonstração Linux registrou os mesmos estados e totais descritos no histórico do PR. Essa evidência permanece histórica; esta rodada acrescenta a execução nativa e inspeção visual no Windows 11.

Consulte `motor_editorial/README.md` para reproduzir em Windows 11 e Debian 12.

## Limites e próximos adaptadores

Windows 11 foi executado fisicamente nesta validação; Debian 12 não foi reexecutado nesta rodada. A implementação usa apenas recursos da biblioteca padrão e paths portáveis. A v0.1 aceita uma única pauta por edição; suporte a múltiplas pautas exige implementação e testes do montador correspondente.

O painel local não autentica usuários; a confirmação exigida é uma proteção contra ação acidental, não uma barreira contra outra pessoa com acesso à mesma conta local. O SQLite pode ser alterado por acesso direto ao arquivo. Antes de operar em dados reais, definir controle de acesso, política de backup e retenção, além de contratos e testes para cada integração externa. Qualquer coleta real, modelo de IA, mídia de terceiros, agendamento ou publicação requer especificação e autorização separadas.
