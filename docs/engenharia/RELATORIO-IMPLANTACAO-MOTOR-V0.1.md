# Relatório de implantação — Motor Editorial v0.1

**Status:** implementado e testado localmente; pronto para revisão em Pull Request. Não autorizado para produção ou publicação.

## Entrega

Foi implementado um aplicativo Python local, sem dependências de terceiros, com orquestração determinística, persistência SQLite, arquivos de prévia no disco, CLI e painel HTTP limitado a `127.0.0.1`. O conjunto inclui fixture inteiramente fictícia, máquina de estados, tentativas limitadas, trilha de auditoria, revisão versionada, decisão de direitos e aprovação humana exclusivamente interna.

A primeira chamada de demonstração gera uma falha temporária injetada e fica pronta para retomada. A chamada seguinte termina com uma edição em `awaiting_approval`. O operador pode revisar o HTML e registrar a aprovação interna pelo painel ou pelo CLI. Não há scraping, IA, API externa, automação programada, upload ou rota de publicação.

## Estrutura persistida

O SQLite cobre fontes, itens de entrada, pautas e fontes associadas, pacotes de apuração, revisões de matéria, resultados de revisão, ativos e decisões de mídia, edições e matérias incluídas, tentativas de execução e eventos de auditoria. Restrições de estado e chaves estrangeiras protegem as transições e relações. Arquivos da execução ficam na pasta de dados local, fora do controle de versão.

## Validação

Os testes automatizados cobrem o percurso até a aprovação pendente, deduplicação, duas versões e duas passagens de revisão, bloqueio de mídia pendente, falha recuperável e limite de tentativas, idempotência, persistência após reabrir o banco, transições inválidas, requisito de aprovação da versão atual e rotas do painel em loopback. A aprovação pelo painel é executada em teste contra um servidor local temporário. O painel não foi avaliado visualmente em Windows ou Debian neste ambiente.

Validação executada no ambiente disponível, com Python 3.12.14:

```sh
python3 -m compileall -q motor_editorial
python3 -m unittest discover -s motor_editorial/tests -v
```

Resultado: compilação sem erros e **5 testes aprovados**. Também foi feito um smoke test do CLI (`init`, duas execuções de `demo` e `status`): a primeira execução parou na falha recuperável simulada; a segunda chegou a `awaiting_approval` com 4 itens, 1 duplicata, 1 pauta, 2 revisões, 1 edição, 33 eventos e 10 tentativas. O status repetido preservou esses totais. O workspace de teste foi temporário.

Consulte `motor_editorial/README.md` para executar a aplicação em Windows 11 e Debian 12.

## Limites e próximos adaptadores

O teste exercita o software em Python 3.12 no ambiente disponível; Windows 11 e Debian 12 não foram executados fisicamente nesta validação. A implementação usa apenas recursos da biblioteca padrão e paths portáveis, mas essa portabilidade precisa ser confirmada nos sistemas-alvo.

O painel local não autentica usuários; a confirmação exigida é uma proteção contra ação acidental, não uma barreira contra outra pessoa com acesso à mesma conta local. O SQLite pode ser alterado por acesso direto ao arquivo. Antes de operar em dados reais, definir controle de acesso, política de backup e retenção, além de contratos e testes para cada integração externa. Qualquer coleta real, modelo de IA, mídia de terceiros, agendamento ou publicação requer especificação e autorização separadas.
