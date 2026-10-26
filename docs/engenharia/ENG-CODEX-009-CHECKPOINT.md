# ENG-CODEX-009 — checkpoint operacional

**Atualizado:** 2026-10-26, após retomada da Direção  
**Fase:** resposta Carranca reconciliada e arquivada; correção técnica validada; próxima execução: Beto.  
**Missão:** Issue #37, segunda bateria investigativa de Carranca, Beto e Nina.

## Estado vivo conferido

- Revalidação na retomada: branch `codex/eng-codex-009-evidence-metering`, HEAD `f8a222e`, upstream `origin/codex/eng-codex-009-evidence-metering`; worktree limpo antes da execução e SHA remoto conferido. PR #36 continua aberta/draft, sem reviews, na branch documental do Fundador 2.
- Issue #37 aberta. A ordem expressa posterior da Direção nesta conversa autoriza iniciar os ensaios em 26/10; não se aplica o bloqueio temporal anterior do comentário da PR #36.
- Issue #33 e PR #34 seguem abertas; PR #34 draft, sem reviews. Seis casos reais H04 já estavam concluídos (Carranca T13/T06, Beto T13/T09, Nina T13/T08). **Nenhum deles foi repetido.** H05 segue sem aceite real; os novos testes cobrem somente integração offline.
- Issue #35 permite mediação automática e determinística apenas para `read:radar_index`, com `provider=None`; não autoriza HTTP, API, rede ou busca externa. A cópia local verificada em `motor_editorial/runtime/motor.sqlite3` existe, mas não contém tabelas `radar_*`; não há corpus local consultável nesta sessão.
- Saldo informado pela Direção: 76% às 01:07 e, depois, 95% durante a chamada Carranca. O percentual posterior à execução continua `not_available`; não converter tokens em percentual ou custo Plus.

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
- `python -m motor_editorial.eng_codex_009 prepare --franchise-percent-reported 76` — OK. Registrou o saldo como relato do usuário, os três hashes de DNA e zero repetição H04.

## Pausa noturna

Às 01:07, a Direção pediu para concluir o checkpoint e deixar os ensaios para a manhã. A pausa terminou quando a Direção disse para continuar. A chamada única de Carranca abaixo é o primeiro ensaio desta missão.

## Retomada e primeira resposta — Carranca

- Foi feita uma chamada real para Carranca (`gpt-6-luna/max`), com uma tentativa no ledger (`attempts=1`, `max_attempts=1`). A resposta do provedor chegou completa: 20.534 tokens de entrada, 5.793 de saída (2.324 de raciocínio), 26.327 total, 106.969 ms, 85.258 bytes de contexto; 1.974 palavras no render.
- SHA-256 do JSON bruto: `48e3b5a16b034406358803fd62713f6eeb0cfd6d8e2879e574eba2be5f0a0445`. SHA-256 do texto legível: `cc8a6bec0ef134651049d5adced0a2f8c91abacf69c4026dbe112aff47a15e70`. Ambos e o recibo estão no armazenamento privado.
- O task ficou `uncertain` após o retorno por uma `ValueError` de pós-processamento. Reprodução offline identificou que `StoryVersionArchive` rejeitava `/` no `story_id`, embora o diretório seja derivado por SHA-256. O schema do papel e as referências de evidência passaram na revalidação offline. Corrigida a validação do identificador e acrescentada regressão; `test_usage_meter`, `test_h05_integration` e `test_eng_codex_009_runner`: **9 testes OK**.
- A resposta não foi reenviada. O JSON bruto original foi reconciliado para `story-versions/.../original/...`; o estado incerto do ledger foi preservado. A mediação da sugestão retornou `hold_unmapped_suggestions` porque a saída não trouxe o par question/purpose válido. Pesquisa não executada; nenhuma chamada externa. O Radar local permanece sem tabelas `radar_*`.
- A resposta não passou pelo adaptador da fábrica porque o task do ledger continua incerto. `fact_check_status=not_run`, direitos pendentes, revisão humana obrigatória e publicação `false`.
- A Direção informou 95% enquanto a chamada ainda estava em execução. Isso foi registrado como observação durante o ensaio; uma observação posterior à chamada continua indisponível.

## Persistência

- Implementação, pacotes e checkpoint foram commitados em `2b09b5c` (`feat(eng): prepare codex 009 journalist trials`) e enviados para `origin/codex/eng-codex-009-evidence-metering`.
- A limpeza do whitespace final e o checkpoint da pausa ficaram nos commits `f189b20` e `f8a222e`, enviados à branch dedicada.

## Limites e próxima ação

1. Commitar e enviar a correção de `StoryVersionArchive` e esta atualização para a branch dedicada; manter a tentativa Carranca `uncertain` e não repetir.
2. Próxima chamada real: `python -m motor_editorial.eng_codex_009 run eng-codex-009-beto`. Uma chamada e uma tentativa; arquivar original, recibo e métricas. Se o task ficar incerto, reconciliar artefatos locais e nunca reenviar a mesma tarefa.
3. Depois do checkpoint Beto, executar Nina individualmente dentro do saldo informado. Não editar DNAs aprovados, não criar revisão sem parecer humano, não publicar, não fazer merge ou deploy.
4. Em todos os textos, distinguir raciocínio sobre notas curatoriais de apuração independente. Limitar pesquisa a `read:radar_index`; sem tabelas locais disponíveis, manter a lacuna explícita e não acionar a fábrica para tarefa incerta ou pendente de pesquisa.
