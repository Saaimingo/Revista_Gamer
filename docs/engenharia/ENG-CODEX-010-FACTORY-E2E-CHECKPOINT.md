# ENG-CODEX-010 — fábrica fictícia ponta a ponta com imagem

**Status:** implementado, validado localmente e enviado para revisão em PR draft; sem merge.
**Data:** 26/10/2026.
**Branch:** `codex/eng-codex-010-factory-fictional-e2e`.
**Base:** `codex/eng-codex-008-siwc-validation` em `8d43a6c855807b2229a8e1eb620a31c6bb6e28e2`.
**PR draft:** [#40 — Prévia local com imagem sintética na fábrica](https://github.com/Saaimingo/Revista_Gamer/pull/40), base `codex/eng-codex-008-siwc-validation`.
**Direção:** pedido do diretor para criar uma pauta fictícia ilustrada e testar a fábrica até o último gate.

## Objetivo e limites

Provar uma reportagem fictícia desde a organização das fontes até o HTML interno ilustrado, passando por revisão e correção, checagens finais, inventário de mídia, pacote e layout. A fixture usa perfis neutros sintéticos; não executa DNAs de Carranca, Beto ou Nina nem chama um modelo real.

Não houve chamada SIWC/Plus, API paga, acesso à rede, pesquisa externa, publicação, implantação, merge ou envio de matéria real. `simulated_approved_internally` é somente o resultado do executor de teste; o relatório mantém `published=false`.

## Implementação

- Novo caso `motor_editorial/fixtures/factory-fictional-image-e2e.json`: mod e jogo imaginários, fontes `example.invalid`, correção deliberada e perfis neutros.
- Novo PNG original `motor_editorial/fixtures/assets/farol-de-papel-ficticio.png`: 1536 × 1024, 2.424.094 bytes, SHA-256 `84c5a7dc179f091c1854e7b305fa860c3a216b7006bbcb8b986d204713e530ae`.
- `MediaInventory.v0` agora representa a imagem como `synthetic_generated`, com hash/dimensões, `rights_status=synthetic_fixture`, licença de fixture própria e `permitted_modes=[internal_preview]`. O carregador rejeita caminho absoluto, travessia para fora das fixtures, formato que não seja PNG, cabeçalho/CRC inválido e dimensões fora dos limites locais.
- O renderizador inclui `<img>` apenas para caminhos content-addressed locais `assets/<sha256>.png`. A validação compara ativo, caminho, alt text, atributos e ausência de URL externa. A persistência confere novamente hash e dimensões dos bytes copiados.
- O placeholder textual antigo segue como caminho padrão para fixtures existentes.

## Execução e evidências

Ambiente: CPython 3.11.9 no Windows. Todos os 18 estágios concluíram com `succeeded`, usando uma `AgentQueue`, um `TaskDispatcher` e o ledger compartilhado. O fluxo `revise` criou revisão 2 e executou `correction`, `final_fact_check` e `final_review` antes de StoryPackage, direitos, composição, render, persistência e gate.

Comando CLI executado em diretório privado local:

```powershell
.\.venv\Scripts\python.exe -m motor_editorial --data-dir "$env:USERPROFILE\.codex\Revista_Gamer\eng-codex-010-factory-image-e2e" factory-demo --fixture motor_editorial\fixtures\factory-fictional-image-e2e.json --run-id codex-010-factory-image-e2e --review-flow revise
```

Resultado observado: exit 0; `simulated_approved_internally`; 18 tarefas; revisão 2; composição `PASS`, 23 verificações sem falhas; 0 chamadas de rede, SIWC ou API paga; `published=false`. O PNG de saída tem o mesmo SHA-256 e os mesmos 2.424.094 bytes do ativo de fixture. O HTML final contém artigo corrigido, alt text, legenda e `<img src="assets/<sha256>.png">` local.

Artefatos privados locais:

- Relatório: `%USERPROFILE%\.codex\Revista_Gamer\eng-codex-010-factory-image-e2e\artifacts\factory-demo\codex-010-factory-image-e2e\factory-demo-report.json`.
- Prévia interna: `%USERPROFILE%\.codex\Revista_Gamer\eng-codex-010-factory-image-e2e\artifacts\factory-demo\codex-010-factory-image-e2e\internal-preview-e1343ae9c1bc9d08.html`, SHA-256 `e1343ae9c1bc9d08b3144de74f5d3dcc5be0b36458c5955738d424387fc0a3f4`.
- Ativo materializado: `%USERPROFILE%\.codex\Revista_Gamer\eng-codex-010-factory-image-e2e\artifacts\factory-demo\codex-010-factory-image-e2e\assets\84c5a7dc179f091c1854e7b305fa860c3a216b7006bbcb8b986d204713e530ae.png`.

Validação executada:

- `python -m unittest motor_editorial.tests.test_factory motor_editorial.tests.test_layout -q` — 26/26 OK em 24,179 s.
- `python -m unittest discover -s motor_editorial\tests -q` — 218/218 OK em 118,494 s.
- `python -m compileall -q motor_editorial` — exit 0.
- `git diff --check` — exit 0.
- O browser bloqueou a navegação `file://` pela política de URL. Não tentei contornar essa barreira; o HTML e o ativo foram conferidos diretamente no disco, e as verificações automatizadas passaram. Portanto, não há prova de inspeção visual de navegador/dispositivo nesta entrega.

## Estado e próximo passo

Commits principais da branch:

- `1f48458219e7881fd936f7547d833b85a0099c57` — implementação, fixture, imagem e validação.
- `ac6793ef75e2c3d483314b10338ec91bc5493f09` — checkpoint sem trailing whitespace.

A atualização do checkpoint com a URL da PR foi registrada no commit seguinte. A branch foi enviada ao `origin` e está limpa; PR #40 está aberta como draft. Próximo passo: revisão humana do PR. Não houve merge; nenhum trabalho adicional é necessário antes dessa revisão.
