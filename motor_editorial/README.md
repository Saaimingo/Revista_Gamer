# Motor Editorial v0.2

Aplicativo local e offline para testar fluxos editoriais independentes e a composição de uma edição com várias matérias. Usa Python 3.11 ou superior e somente a biblioteca padrão: SQLite para estado, arquivos locais para prévias e painel HTML servido exclusivamente em `127.0.0.1`.

Todos os jogos, fontes, acontecimentos e ativos das fixtures são fictícios. O motor não consulta notícias, não chama modelos de IA, não acessa serviços externos e não oferece rota ou comando de publicação.

## Executar no Windows 11

Na raiz do repositório, com Python 3.11 instalado:

```powershell
py -3.11 -m motor_editorial init
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial demo
py -3.11 -m motor_editorial status
py -3.11 -m motor_editorial web
```

A primeira execução multipauta cria três pautas independentes: Orbit Racers chega à checagem de mídia; Garden of Echoes fica bloqueada pela segunda revisão; Clockwork Harbor registra uma falha transitória de apuração. A segunda execução retoma somente as etapas pendentes, sem repetir importação ou etapas concluídas. A edição permanece bloqueada até uma pessoa excluir explicitamente a pauta reprovada, com responsável, motivo e confirmação exata:

```powershell
py -3.11 -m motor_editorial exclude <edition_id> <story_id>
```

Depois da exclusão humana, a prévia interna reúne as duas matérias elegíveis na ordem persistida. Para revisar e registrar aprovação somente interna:

```powershell
py -3.11 -m motor_editorial approve <edition_id>
```

`status` mostra execuções, estados das pautas, composição e associações ordenadas. Para retomar uma pauta isolada, use os identificadores exibidos por `status`:

```powershell
py -3.11 -m motor_editorial run-story <run_id> <story_id>
```

O painel local abre em `http://127.0.0.1:8765/`. Ele oferece execução em lote, retomada individual de falha transitória, detalhes de fontes e revisão, direitos por matéria, exclusão humana auditada e prévia multipauta. Não existe publicação.

## Compatibilidade v0.1

`demo-v1` executa a fixture original de uma pauta e mantém as garantias cobertas pelos 11 testes da v0.1, inclusive a rejeição anterior à gravação quando a fixture contém mais de uma pauta selecionável. A nova fixture está em `fixtures/demo-multipauta.json`; a antiga permanece em `fixtures/demo.json`.

O SQLite usa o esquema v3. A abertura de bancos v1/v2 aplica migrações aditivas e mantém os registros e associações existentes.

## Dados e diretório

Por padrão, `motor_editorial/runtime/` guarda `motor.sqlite3` e artefatos locais e é ignorado pelo Git. Para usar uma pasta isolada:

```powershell
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-demo-v02" init
py -3.11 -m motor_editorial --data-dir "$env:TEMP\revista-gamer-demo-v02" demo
```

Os IDs de pautas, itens e edições incluem o identificador da execução para evitar colisão entre execuções independentes. Tentativas de etapa, revisões, fontes, direitos, decisões de exclusão e aprovações ficam no SQLite com trilha de auditoria.

## Testes

```powershell
py -3.11 -m unittest discover -s motor_editorial/tests -v
```

Os testes usam diretórios temporários. Cobrem os 11 contratos herdados da v0.1, isolamento e retomada, idempotência sob chamadas concorrentes, migração v2, ordem da edição, revisão vigente, direitos por matéria, confirmação humana, rotas locais e ausência de publicação.
