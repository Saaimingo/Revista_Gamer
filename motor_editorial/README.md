# Motor Editorial v0.1

Aplicativo local e offline para exercitar o fluxo editorial da Revista Gamer com dados totalmente fictícios. A v0.1 usa Python 3.11 ou superior e somente a biblioteca padrão: SQLite para estado, arquivos locais para prévias e uma interface HTML servida em `127.0.0.1`.

O motor não coleta notícias, não chama modelos de IA, não acessa serviços externos e não contém função de publicação. Os nomes de jogos, veículos, fontes e ativos da fixture são inventados para teste.

## Executar

Abra um terminal na pasta raiz do repositório. Não é necessário instalar pacotes com `pip`.

No Windows 11 com Python 3.11+:

```powershell
py -3.11 -m motor_editorial init
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial status
py -3.11 -m motor_editorial web
```

No Debian 12 com Python 3.11+:

```sh
python3 -m motor_editorial init
python3 -m motor_editorial demo
python3 -m motor_editorial demo
python3 -m motor_editorial status
python3 -m motor_editorial web
```

A primeira execução de `demo` registra uma falha transitória fictícia na apuração e termina em `recoverable_failure`. Execute o mesmo comando novamente para retomar; o resultado esperado é `awaiting_approval`, com uma prévia interna e uma única edição. Abrir `web` mostra o painel em `http://127.0.0.1:8765/`. Para escolher outra porta local, use `web --port 8766`.

O painel permite consultar os itens e estados, abrir o histórico de uma pauta, revisar as duas versões e a prévia, e executar ou retomar a fixture. A aprovação interna só é aceita depois da prévia, com o nome do responsável e a frase de confirmação explícita. O CLI também aceita aprovação interativa:

```sh
python3 -m motor_editorial approve edition-demo-motor-v0.1
```

No PowerShell, substitua `python3` por `py -3.11`. Aprovar apenas registra uma decisão interna; nenhum conteúdo é enviado ou publicado.

Por padrão, o banco `motor.sqlite3` e os arquivos de execução ficam em `motor_editorial/runtime/`, ignorado pelo Git. Para repetir desde o início, passe uma nova pasta a `--data-dir`, por exemplo:

```sh
python3 -m motor_editorial --data-dir /tmp/revista-gamer-demo init
python3 -m motor_editorial --data-dir /tmp/revista-gamer-demo demo
```

Em PowerShell, use `--data-dir "$env:TEMP\revista-gamer-demo"`.

## Testar

Na raiz do repositório:

```sh
python3 -m unittest discover -s motor_editorial/tests -v
```

No Windows, use `py -3.11` no lugar de `python3`. Os testes usam bancos e arquivos temporários, verificam a simulação sem sockets de rede e iniciam o painel apenas em loopback para validar suas rotas e a aprovação interna.

## Modelo de dados e fluxo

O banco local registra fontes e itens normalizados, pauta e vínculos, pacote de apuração, versões de matéria, resultados de revisão, ativos e decisões de direitos, edição e composição, tentativas de execução e eventos de auditoria. As chaves estrangeiras e restrições SQLite protegem as relações e estados permitidos.

O fluxo de demonstração exercita normalização e deduplicação, triagem, apuração, rascunho, revisão reprovada, nova versão, segunda revisão aprovada, verificação de direitos, montagem da prévia e espera por decisão humana. A revisão encontra uma afirmação fictícia sem fonte; a correção cria uma nova versão. O ativo permitido de teste é desenhado como SVG original incorporado; o ativo pendente nunca é incluído e aparece somente como placeholder. Falhas transitórias têm tentativas contadas e limite finito.

As referências principais de implementação estão nos módulos `db`, `domain`, `workflow`, `render`, `web` e `cli`. A simulação usa adaptadores determinísticos e fixture versionada; não existe mecanismo de publicação.

## Limitações conhecidas

- O painel é local e não tem autenticação de usuário. A confirmação explícita reduz aprovações acidentais, mas não substitui controles de acesso do sistema operacional em um computador compartilhado.
- A v0.1 suporta um operador/processo local e uma fixture de demonstração estável. Ainda não implementa edição concorrente, fila distribuída, agendamento, ingestão real ou backup automatizado.
- O histórico é append-only pelo fluxo do aplicativo; acesso direto ao arquivo SQLite pelo operador pode alterar dados.
- A aprovação grava o estado de aprovação interna no SQLite e mantém a prévia local. Isso não é aprovação de direitos, autorização comercial nem publicação.

Consulte `docs/engenharia/RELATORIO-IMPLANTACAO-MOTOR-V0.1.md` para o resumo de entrega e validação.
