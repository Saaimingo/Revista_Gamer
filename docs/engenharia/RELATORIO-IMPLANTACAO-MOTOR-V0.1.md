# Relatório de implantação — Motor Editorial v0.1

**Status:** implementação v0.1 e testes automatizados aprovados no ambiente Linux disponível; aceite nativo e inspeção visual no Windows 11 ainda pendentes. Não autorizado para produção ou publicação.

## Entrega

Foi implementado um aplicativo Python local, sem dependências de terceiros, com orquestração determinística, persistência SQLite, arquivos de prévia no disco, CLI e painel HTTP limitado a `127.0.0.1`. O conjunto inclui fixture inteiramente fictícia, máquina de estados, tentativas limitadas, trilha de auditoria, revisão versionada, decisão de direitos e aprovação humana exclusivamente interna. Após as correções da revisão do Pull Request, o SQLite usa o esquema v2 e migra automaticamente o esquema v1, preservando as decisões de mídia existentes como obrigatórias por padrão.

A primeira chamada de demonstração gera uma falha temporária injetada e fica pronta para retomada. A chamada seguinte termina com uma edição em `awaiting_approval`. O operador pode revisar o HTML e registrar a aprovação interna pelo painel ou pelo CLI. A v0.1 rejeita fixtures com mais de uma pauta selecionável antes de criar dados; uma segunda reprovação editorial encerra a execução em `failed_intervention`, com evento auditável. Não há scraping, IA, API externa, automação programada, upload ou rota de publicação.

## Estrutura persistida

O SQLite cobre fontes, itens de entrada, pautas e fontes associadas, pacotes de apuração, revisões de matéria, resultados de revisão, ativos e decisões de mídia, edições e matérias incluídas, tentativas de execução e eventos de auditoria. Restrições de estado e chaves estrangeiras protegem as transições e relações. Arquivos da execução ficam na pasta de dados local, fora do controle de versão.

## Validação

Os testes automatizados cobrem o percurso até a aprovação pendente, deduplicação, duas versões e duas passagens de revisão, bloqueio de mídia pendente, licença incompatível com a modalidade, mídia opcional pendente, revogação após a prévia e nova confirmação, reprovação da segunda revisão com intervenção auditável, rejeição antecipada de múltiplas pautas, migração de esquema v1, falha recuperável e limite de tentativas, idempotência, persistência após reabrir o banco, transições inválidas, requisito de aprovação da versão atual e rotas do painel em loopback. A aprovação pelo painel é executada em teste contra um servidor local temporário. O painel não foi avaliado visualmente em Windows ou Debian neste ambiente.

Validação executada em 17/10/2026 no ambiente Linux x86_64 disponível (distribuição não identificada), com Python 3.12.14:

```sh
python3 -m compileall -q motor_editorial
python3 -m unittest discover -s motor_editorial/tests -v
```

Resultado: compilação sem erros e **11 testes aprovados**. Em uma pasta temporária isolada, `init` completou; a primeira execução de `demo` terminou em `recoverable_failure` (4 itens, 1 duplicata, 1 pauta, 0 revisões, 0 edições, 10 eventos e 3 tentativas); a segunda retomou e chegou a `awaiting_approval` (4 itens, 1 duplicata, 1 pauta, 2 revisões, 1 edição, 33 eventos e 10 tentativas). Duas consultas consecutivas a `status` foram idênticas e confirmaram a persistência da execução e da edição pendente de aprovação.

O painel foi iniciado na porta padrão e o listener observado estava em `127.0.0.1:8765`. O smoke test HTTP local recebeu resposta 200 no painel, no detalhe da pauta e na prévia; verificou as duas versões, a seção de direitos de mídia, a ação de aprovação interna e o aviso “SIMULAÇÃO — NÃO PUBLICAR”. Uma aprovação foi registrada somente no banco temporário e resultou em `approved_internally`. As rotas de publicação testadas por GET e POST retornaram 404. O diretório temporário foi removido ao fim do teste. Esta verificação cobriu conteúdo e rotas HTTP; não foi uma inspeção visual por navegador.

**Validação nativa ainda pendente:** este ambiente é Linux, não Windows 11. Não havia computador Windows conectado nem executor Windows disponível nesta sessão; portanto, Python, comandos PowerShell/`py`, comportamento de paths no Windows e aparência visual do painel no navegador do Windows não foram validados. A evidência Linux acima não substitui o aceite exigido pelo comentário arquitetural.

Consulte `motor_editorial/README.md` para executar a aplicação em Windows 11 e Debian 12.

## Limites e próximos adaptadores

O teste exercita o software em Python 3.12.14 no ambiente Linux disponível; Windows 11 e Debian 12 não foram executados fisicamente nesta validação. A implementação usa apenas recursos da biblioteca padrão e paths portáveis, mas essa portabilidade precisa ser confirmada nos sistemas-alvo. A v0.1 aceita uma única pauta por edição; suporte a múltiplas pautas exige a implementação e testes do montador correspondente.

O painel local não autentica usuários; a confirmação exigida é uma proteção contra ação acidental, não uma barreira contra outra pessoa com acesso à mesma conta local. O SQLite pode ser alterado por acesso direto ao arquivo. Antes de operar em dados reais, definir controle de acesso, política de backup e retenção, além de contratos e testes para cada integração externa. Qualquer coleta real, modelo de IA, mídia de terceiros, agendamento ou publicação requer especificação e autorização separadas.
