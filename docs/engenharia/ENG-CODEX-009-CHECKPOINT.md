# ENG-CODEX-009 — checkpoint operacional

**Atualizado:** 2026-10-26, 01:07 (horário informado pela Direção; America/Sao_Paulo)
**Fase:** pausada antes da primeira inferência real, a pedido da Direção devido ao horário. Retomada solicitada para a manhã seguinte.
**Missão:** Issue #37, segunda bateria investigativa de Carranca, Beto e Nina.

## Estado vivo conferido

- Repositório `Saaimingo/Revista_Gamer`; branch local `codex/eng-codex-009-evidence-metering`; HEAD-base `eaad07c358d96155f2052864b506c2902c56acaf`. A branch local estava rastreando por engano `origin/fundador2/eng-codex-009-dossies-editoriais-2026-10-25`; refs remotas foram verificadas e a PR documental #36 permanece aberta/draft, sem reviews, nesse commit. O código deste checkpoint deve ser enviado à branch Codex dedicada.
- Issue #37 aberta. A ordem expressa posterior da Direção nesta conversa autoriza iniciar os ensaios em 26/10; não se aplica o bloqueio temporal anterior do comentário da PR #36.
- Issue #33 e PR #34 seguem abertas; PR #34 draft, sem reviews. Seis casos reais H04 já estavam concluídos (Carranca T13/T06, Beto T13/T09, Nina T13/T08). **Nenhum deles foi repetido.** H05 segue sem aceite real; os novos testes cobrem somente integração offline.
- Issue #35 permite mediação automática e determinística apenas para `read:radar_index`, com `provider=None`; não autoriza HTTP, API, rede ou busca externa. A cópia local verificada em `motor_editorial/runtime/motor.sqlite3` existe, mas não contém tabelas `radar_*`; não há corpus local consultável nesta sessão.
- Saldo de franquia mais recente: **76% informado pela Direção às 01:07**. Isso é anotação independente de tokens; percentual posterior à execução está `not_available` até nova observação. Não converter tokens em percentual ou custo Plus.

## DNAs e dossiês travados

- Carranca / `ranzinza` v1.0: refs aprovadas Bloco 02, commit `3d651fe1951818767b4a6b935732857f08cb7849`, quatro documentos do DNA integral.
- Beto Cartucho v0.2 e Nina Prisma v1.0: refs aprovadas Bloco 02, commit `21381c0975bef1da048d7887cbdfbd0dd97bed96`, cinco documentos por personagem.
- Snapshot privado conferido: Carranca 66.315 caracteres, Beto 35.229, Nina 25.245; hash do composto confere com o manifesto de cada persona. Os arquivos fonte permanecem byte-a-byte nos commits aprovados; exemplos editoriais não entram no prompt. O limite do catálogo para DNA foi elevado a 80.000 caracteres para não truncar Carranca.
- Pacotes regenerados em `motor_editorial/evidence_packages/eng_codex_009/`: Carranca 12 candidatas/11 notas elegíveis; Beto 14/12; Nina 11/10. São notas curatoriais e URLs; corpos das fontes não foram obtidos e direitos não foram revalidados. Logo, os resultados podem ser avaliados como raciocínio sobre o dossiê, mas não como apuração independente nem publicação pronta.

## Implementação preparada

- `usage_meter.py` registra uso por jornalista/papel/tarefa, modelo/effort, input/output/reasoning/total, cache, chamadas, latência, tamanho de contexto, status e origem da medição; custo faturado e quota de interface ficam `null` quando indisponíveis.
- `StoryVersionArchive` preserva saída bruta e texto legível integral, manifests e SHA-256; originais e revisões têm diretórios/IDs distintos. Revisão só será criada após avaliação humana, sem sobrescrever original.
- `agent_siwc.py` captura recibo de uso mesmo em validações malsucedidas/estados incertos. O runner permite no máximo uma chamada por jornalista e não repete tarefas iniciadas ou concluídas.
- `research_mediation.py` converte solicitações tipadas para escopo local aprovado; a ponte opcional da fábrica reutiliza a mesma `AgentQueue`/`TaskDispatcher`, cria somente rascunho, exige revisão humana e mantém fact-check/publicação desligados.
- `eng_codex_009.py` prepara snapshots/dossiês em `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-009`; prepara uma chamada por jornalista; não imprime o texto. ACL privada verificada para a conta do projeto, `SYSTEM` e Administradores.

## Validação desta etapa

- `python -m unittest motor_editorial.tests.test_evidence_packages motor_editorial.tests.test_research_mediation motor_editorial.tests.test_usage_meter motor_editorial.tests.test_h05_integration motor_editorial.tests.test_eng_codex_009_runner motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_factory_role_draft_bridge -q` — **42 testes OK**.
- `python -m unittest motor_editorial.tests.test_eng_codex_009_runner motor_editorial.tests.test_h05_integration motor_editorial.tests.test_usage_meter motor_editorial.tests.test_evidence_packages motor_editorial.tests.test_research_mediation -q` — **24 testes OK**, após incluir o registro atualizado de 76% informado.
- `python -m compileall -q motor_editorial` — OK. `git diff --check` — exit 0.
- Uma validação ampliada de 99 testes terminou com **5 erros e 1 skip**; pelo menos um erro foi causado pela ausência da dependência `tzdata` necessária para `ZoneInfo("America/Sao_Paulo")` no Python global usado (`CPython 3.11.9`). Não houve instalação de dependências. As suítes focalizadas acima passaram.
- `python -m motor_editorial.eng_codex_009 prepare --franchise-percent-reported 76` — OK. Registrou o saldo como relato do usuário, os três hashes de DNA e zero repetição H04. Nenhuma inferência SIWC foi feita até este checkpoint.

## Pausa noturna

Às 01:07, a Direção pediu para concluir o checkpoint e deixar os ensaios para a manhã. Portanto, nenhuma matéria de teste foi iniciada, nenhuma chamada real SIWC foi feita, nenhum texto editorial novo foi gerado e não houve consumo SIWC registrado nesta missão. O último percentual (76%) é anterior à execução e permanece apenas como relato do usuário.

## Persistência

- Implementação, pacotes e checkpoint foram commitados em `2b09b5c` (`feat(eng): prepare codex 009 journalist trials`) e enviados para `origin/codex/eng-codex-009-evidence-metering`.
- A limpeza do whitespace final e a atualização da pausa ficaram no commit `f189b20` (`docs(eng): persist codex 009 morning handoff`), também enviado à branch dedicada. `git diff --cached --check` passou após a limpeza. Nenhuma execução real ocorreu.

## Limites e próxima ação

1. Na retomada pela manhã, revalidar branch/upstream/status, refs remotas, Issues #37/#35/#33, PRs #36/#34, comentários/reviews e franquia informada pela Direção. Não confiar em valores antigos sem nova observação.
2. Confirmar que a branch dedicada contém este checkpoint e a instrumentação antes de iniciar qualquer inferência. Com franquia suficiente, iniciar Carranca primeiro: `python -m motor_editorial.eng_codex_009 run eng-codex-009-carranca`, uma chamada SIWC, `gpt-6-luna/max`, `max_calls=1`, usando DNA e pacote congelados.
3. Preservar original integral/recibo e registrar métricas; se a chamada falhar ou ficar incerta, não reenviar. Examinar eventual solicitação de pesquisa; com o Radar sem tabelas locais, não executar pesquisa externa. Não tratar o texto como factualidade independentemente verificada. O adaptador da fábrica só recebe saída concluída e mantém `awaiting_human_review`.
4. Após checkpoint de Carranca, continuar Beto e Nina em chamadas individuais dentro do saldo então autorizado. Não editar DNAs aprovados, não gerar revisão sem parecer humano, não publicar, não fazer merge ou deploy.
