# ENG-CODEX-008 — checkpoint de execução

**Atualizado:** 2026-10-25 21:39 -03:00
**Issue de execução:** [#33](https://github.com/Saaimingo/Revista_Gamer/issues/33)
**Ordem documental:** [PR #32](https://github.com/Saaimingo/Revista_Gamer/pull/32)
**PR de implementação:** [#34](https://github.com/Saaimingo/Revista_Gamer/pull/34), draft, aberta, sem merge.

## Estado atual

- **H00:** concluída — estado remoto, base, fontes de persona, documentos obrigatórios, arquitetura e baseline conferidos.
- **H01:** concluída — executor SIWC genérico, validação de papel/modelo/esforço/schema e retenção integral da resposta.
- **H02:** concluída — testes offline de segurança, incerteza, lease, replay, fronteiras de evidência e falhas do provedor.
- **H03:** concluída no gate técnico com ressalva do harness de entrada — catálogo e uma inferência real de `assignment_editor` concluíram; resposta integral privada, completa e válida pelo schema.
- **Próxima ação:** H04 — rever os commits/decisões de identidade ao vivo, preparar fixtures de persona em JSON UTF-8 validado e iniciar os cenários autorizados de Carranca, Beto e Nina.
- **Branch:** `codex/eng-codex-008-siwc-validation`, criada diretamente de `codex/eng-codex-007-factory-radar@cd71022ef3b3d60fa4c97beb6db5583a03856102`.
- **Commits H00:** `b8e2dde` (checkpoint inicial), `05d3c8f` (vínculo à PR #34); ambos enviados para `origin/codex/eng-codex-008-siwc-validation`.
- **Commits H01/H02:** `60c4c0f` (executor por papel, retenção SIWC e regressões offline) e `7256db1` (checkpoint); ambos enviados para `origin/codex/eng-codex-008-siwc-validation`.
- **Comentários H00:** [Issue #33](https://github.com/Saaimingo/Revista_Gamer/issues/33#issuecomment-6405340231) · [PR #34](https://github.com/Saaimingo/Revista_Gamer/pull/34#issuecomment-6405340777).
- **Comentários H01/H02:** [Issue #33](https://github.com/Saaimingo/Revista_Gamer/issues/33#issuecomment-6405551977) · [PR #34](https://github.com/Saaimingo/Revista_Gamer/pull/34#issuecomment-6405552335).
- **Commit/checkpoint H03:** `b0b0441`; relatório com a mesma evidência: [Issue #33](https://github.com/Saaimingo/Revista_Gamer/issues/33#issuecomment-6405668375) · [PR #34](https://github.com/Saaimingo/Revista_Gamer/pull/34#issuecomment-6405668626).
- **Baseline:** sem alterações de código antes desta branch; suíte serial `198/198 OK` em CPython 3.11.9, 134,945 s.
- **Chamadas SIWC/Plus nesta missão:** 1 consulta real a `/v1/models`, 1 refresh suportado da credencial existente e 1 inferência real. Nenhum login ou consentimento novo. As chamadas de teste de H01/H02 foram mockadas.
- **Orçamento informado pelo usuário antes de H03:** 24% da franquia compartilhada com Codex. A inferência H03 reportou 1.611 tokens (628 input, 983 output; 501 de raciocínio), sem medidor de percentual restante na resposta.
- **Saída editorial real:** 1 briefing estruturado de `assignment_editor`, sintético e sem persona; não é `StoryDraft`, não teve avaliação P/J ou parecer humano, e `published=false`.
- **Publicação/merge/deploy:** não realizados; `published=false`.

## Estado remoto verificado

| Referência | Estado observado |
| --- | --- |
| PR #30 / ENG-CODEX-007 | aberta, draft, sem reviews; head `cd71022ef3b3d60fa4c97beb6db5583a03856102`; base `4de16640e67bd16c61468955e96e4ffa850d4cab` |
| PR #32 / contrato 008 | aberta, draft, sem reviews; head `a9aee221f1783d402bbed16ff13f1ea32042dae2`; base no head da #30 |
| PR #34 / implementação 008 | aberta, draft, sem reviews; sincronizada com a branch de execução, base no head da #30; não mesclada |
| Issue #33 / ordem 008 | aberta; inclui adendo obrigatório de preservação integral das saídas textuais |
| PR #13 / Ranzinza | aberta, draft, sem reviews; head `3d651fe1951818767b4a6b935732857f08cb7849` |
| PR #19 / Beto e Nina | aberta, draft, sem reviews; head `21381c0975bef1da048d7887cbdfbd0dd97bed96` |
| PR #27 / diretriz de apuração | aberta, draft, sem reviews; head `d38c5da92ba76739d9234942f7bf0bd087949e5f` |

O repositório GitHub é público. PR #30 e os relatórios históricos E17–E19 não foram editados. A autorização 008 permite pilotos reais controlados na assinatura existente, dentro dos limites da Issue #33; não autoriza API paga, novo consentimento OAuth, mudança de DNA, merge, publicação, deploy, agendamento de produção ou migração do banco runtime.

## Auditoria H00

- **SIWC:** `SIWCClient` usa o endpoint Responses existente, envia `store=false` e `stream=true`, valida modelo/esforço retornados e exige `response.completed`. Queda de transporte ou stream sem conclusão vira `uncertain`, sem replay automático.
- **Lacuna de retenção encontrada no H00 e tratada em H01:** o caminho anterior aparava a resposta, fazia parse do JSON e descartava o texto original. Agora a rota de papel preserva a string integral (inclusive whitespace) em artefato bruto antes do parse/schema; respostas parciais, falhas de JSON e falhas HTTP deixam manifesto com estado e hash.
- **Executor atual:** `SIWCEditorialExecutor` é restrito ao perfil experimental neutro e a `gpt-6-luna/max`; não executa os papéis funcionais nem as personas.
- **Contratos e fila:** `AgentRoleCatalog` resolve papel por `role_id/version/hash`, valida input/schema e hash de persona, separa seções confiáveis de input e evidência não confiável. `TaskDispatcher` prepara esse contexto e valida `AgentResultEnvelope`; filas, leases e ledger permanecem no `AgentQueue`/SQLite existentes.
- **Fábrica:** `SyntheticFactoryExecutor` ainda executa os estágios sintéticos. E18 e E19 da 007 só provaram vínculo/isolamento offline; as 48 entradas seguem sem execução real e não há `StoryDraft` real dessas etapas.
- **Persistência e publicação:** o `Store` mantém artefatos fora dos documentos versionados e a fábrica registra o estado `not_published`; os ensaios 008 devem manter os conteúdos brutos fora do Git público.
- **Fontes de persona:** os hashes SHA-256 do pacote/contrato de carregamento do Ranzinza, contratos de carregamento do Beto e da Nina e diretriz de apuração na fixture E18 coincidem com os bytes dos commits fonte acima. Os comentários do fundador reconhecem as identidades criativas e liberam a preparação de testes técnicos; PRs permanecem independentes, sem merge.

## H01–H02 — ponte genérica e validação offline

- `SIWCAgentRoleExecutor` é registrado no `TaskDispatcher` já existente, exige `AgentRoleCatalog` ativo e usa o `AgentQueue`/ledger recebido; não instancia outro Motor, fila ou dispatcher.
- Resolução role/version/hash e persona hash ocorrem antes do executor. Instruções confiáveis e schema ficam no campo de instruções; input e evidência permanecem como dados separados, com fronteira de confiança explícita.
- Modelo e esforço são parâmetros obrigatórios; o modelo precisa estar no catálogo verificado, o perfil precisa autorizar o executor SIWC e fallback permanece proibido. O resultado exige `store=false`, `stream=true`, evento `response.completed`, modelo/esforço retornados e JSON válido.
- Cada tarefa grava request, resposta bruta e manifesto local com hashes, role/persona, run/story/revision/case, snapshots, refs de evidência, modelo/esforço, uso/latência disponíveis e status. A resposta bruta não entra no resultado SQLite nem em logs; o envelope aponta para o artefato e conserva `input_hash`, `output_hash` e `human_review_required`.
- Validação semântica bloqueia referências a evidência/claims ausentes, claims sem evidência, promoção de rumor apoiado só por fonte rumorosa e fact-check/revisão com `draft_hash` obsoleto. A saída nunca é aprovação humana nem publicação.
- Artefatos dos testes H01/H02 ficaram em diretórios temporários e foram removidos. No fechamento de H01/H02 não havia saída SIWC real; a primeira saída real foi produzida em H03 e permanece fora do Git público, sob ACL local verificada.

## H03 — E17 real controlada, concluída com ressalva do harness de entrada

- ACL observada em `%LOCALAPPDATA%`: `ReadAndExecute` herdado por outro principal; caminho rejeitado. `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-008` foi criado sob o pai privado e conferido com acesso de usuário atual, SYSTEM e Administrators apenas; nenhuma ACL foi alterada.
- Pré-leitura local do CredentialStore sem segredos: credencial e access/refresh tokens presentes, escopo `chatgpt.tokens.use.direct` presente; access token expirado. A `SIWCClient.models()` usou o refresh existente suportado; expiração restante depois: 3599 s. Sem login ou novo consentimento.
- Uma chamada real `GET /v1/models` concluiu em 2875 ms: 9 modelos, 7 listados, `gpt-6-luna` visível. Manifesto de metadados: `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-008\\h03-model-catalog-c3d837d559d049bfbad3ef922507aac8.json`.
- Uma inferência real foi despachada como `assignment_editor` (`role_version=1.0.0`, `role_hash=3b3db550015edd5fcf90aff8aa5ed781429efe9af7cc59e6b76504d9d3eb1810`), `gpt-6-luna/max`, `store=false`, `stream=true`, `response.completed=true`; o dispatcher concluiu `succeeded`, `role_schema_valid`, `human_review_required=true`, `publication_state=not_published`.
- Uso reportado: 628 input, 983 output, 501 raciocínio, 1.611 total; duração 19.828 ms. `temperature` de amostragem não configurada. Texto original integral: 2.147 bytes UTF-8, SHA-256 `0e7f24d4b38d5ac4d194837fadc594871944015983d9ab3fed27fecc4f027f22`; conferido contra o manifesto.
- Índice privado, com links diretos para original, manifesto e entrada: `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-008\\INDICE-LEITURA-INTEGRAL.md`. A resposta encontrou dossier vazio, `needs_more_research=true` e 3 lacunas; não há claims nem evidências no resultado. Sem revisão/correção posterior.
- **Ressalva:** o script de ensaio foi alimentado por pipeline PowerShell→Python, que converteu caracteres portugueses não ASCII da entrada sintética em `?`. O `.request.json` e manifesto preservam exatamente o que foi enviado; `test_only`, `no_external_sources` e `no_real_world_factual_claims` permaneceram intactos. Isso limita a evidência de fidelidade da entrada deste caso; não invalida a conclusão técnica do fluxo SIWC, da resposta completa nem da validação de schema. Nota privada: `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-008\\h03-assignment-editor-20261026-0035z\\h03-operator-note.md`. H04 usará arquivos JSON UTF-8 lidos com `encoding="utf-8"` e validação dos bytes antes de inferir.

## Evidências executadas

| Comando/consulta | Resultado |
| --- | --- |
| `git status --short --branch`, branch/upstream, `git rev-parse HEAD`, `git log -5 --oneline` | árvore inicial limpa; branch e upstream 007 apontavam para `cd71022`; histórico preservado |
| `gh issue view 33 --json body,title,labels,assignees,milestone,url` | Issue aberta; sequência H00–H09 e limites atuais confirmados |
| `gh pr view 30/32/13/19/27` | heads, bases, estados e ausência de reviews confirmados; #30/#32 e fontes seguem draft |
| `gh repo view Saaimingo/Revista_Gamer --json nameWithOwner,visibility,url` | `PUBLIC` |
| `git cat-file -t <commit fonte>` e SHA-256 de sete arquivos via `git show` | commits disponíveis; todos os sete hashes do pacote E18 conferiram |
| `& '.\\.venv\\Scripts\\python.exe' --version` | CPython 3.11.9 |
| `& '.\\.venv\\Scripts\\python.exe' -m unittest discover -s motor_editorial/tests -q` | `Ran 198 tests in 134.945s — OK` |

| `& '.\\.venv\\Scripts\\python.exe' -m unittest motor_editorial.tests.test_agent_contracts motor_editorial.tests.test_agent_role_catalog motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_orchestration motor_editorial.tests.test_agent_workflow motor_editorial.tests.test_editorial motor_editorial.tests.test_factory motor_editorial.tests.test_factory_multipauta -q` | H01/H02: `Ran 109 tests in 79.474s — OK` |
| `& '.\\.venv\\Scripts\\python.exe' -m unittest motor_editorial.tests.test_agent_siwc_executor motor_editorial.tests.test_orchestration.SIWCContractTests.test_editorial_raw_stream_sink_preserves_exact_complete_and_partial_text -q` | Repetição focada: `Ran 13 tests in 6.682s — OK` |
| `& '.\\.venv\\Scripts\\python.exe' -m compileall -q motor_editorial` | exit 0 |
| `git diff --check` e `git diff --cached --check` | exit 0, sem problemas de whitespace |
| Inspeção ACL PowerShell de `%LOCALAPPDATA%`, `%USERPROFILE%\\.codex` e raiz de artefatos H03 recém-criada | `%LOCALAPPDATA%` rejeitado por `ReadAndExecute` de outro principal; raiz H03 privada, owner usuário atual e acessos herdados somente de usuário atual/SYSTEM/Administrators; sem alteração de ACL |
| Pré-leitura local de `CredentialStore.default_path()`/`CredentialStore.load()` | Arquivo presente; `authenticated=true`; `direct_usage_scope=true`; access/refresh token presentes; access token expirado; valores sensíveis nunca impressos; nenhuma rede acessada |
| Uma chamada `SIWCClient.models()` pelo CredentialStore existente | `GET /v1/models`, 1 request em 2875 ms; catálogo 9, listados 7, `gpt-6-luna` visível; refresh suportado concluiu; sem inferência; manifesto privado em `h03-model-catalog-c3d837d559d049bfbad3ef922507aac8.json` |
| Uma execução real via `TaskDispatcher` e `SIWCAgentRoleExecutor` | 1 inferência `assignment_editor`; `succeeded`; `role_schema_valid`; resposta completa 2.147 bytes; SHA-256 conferido; 1.611 tokens; request/response/manifesto/índice preservados no storage privado; ressalva de encoding descrita acima |
| Verificação local do `INDICE-LEITURA-INTEGRAL.md`, resposta e manifesto | três links diretos existentes; resposta UTF-8 de 2.147 bytes; SHA-256 do arquivo e `artifact_sha256` coincidem |

## Gates para H03 — E17 real controlada

1. **Armazenamento:** não usar `%LOCALAPPDATA%` para texto bruto porque foi observada leitura por outro principal. A raiz `%USERPROFILE%\\.codex\\Revista_Gamer\\ensaios-008` já herda a ACL privada de `%USERPROFILE%\\.codex`; verificação final não encontrou outro principal com leitura/escrita. Não alterar permissões.
2. **Conta e catálogo:** concluído — CredentialStore existente renovado pelo caminho suportado, sem login/consentimento novo; uma consulta única mostrou `gpt-6-luna` como listado.
3. **Primeira inferência:** concluída — uma chamada curta `assignment_editor` em `gpt-6-luna/max`, sem fallback, via SIWCClient e dispatcher existentes. O resultado completou e passou schema; por controle de cota, não foram feitas chamadas H03 adicionais.
4. **Parada segura:** 401/403, 429, novo consentimento, modelo/esforço divergente, resposta incompleta/incerta ou orçamento insuficiente interrompem o lote; não repetir chamadas incertas. Se incompleta, marcar `incomplete` e nunca apresentar como texto integral. Nenhuma dessas falhas ocorreu no piloto H03.
5. **Trilhas de aceite:** qualquer texto editorial fica preservado integralmente, com metadados e hash, em storage local privado. Não gravar textos integrais de terceiros, tokens ou PII no Git/Issue/PR. `published=false`; revisão humana e critérios P/J continuam separados e pendentes.
6. **Identidades:** manter commits/hashes fonte fixados para Carranca/Ranzinza, Beto, Nina e diretriz de apuração; não alterar DNA. Não editar os históricos E17–E19 da 007.

## Próximo passo exato

H01/H02 estão implementadas e enviadas (`60c4c0f`, `7256db1`), validadas por 109 testes focados, repetição de 13 testes críticos, `compileall` e `git diff --check`; evidências H01/H02 registradas na Issue #33 e PR #34. H03 concluiu o gate técnico: uma consulta ao catálogo, refresh suportado e uma inferência real concluída, sem login/consentimento novo. A resposta original e metadados estão preservados localmente e indexados; a ressalva de encoding está registrada e orienta o harness H04. Próximo: H04 — rever ao vivo as fontes de DNA e decisões, montar inputs UTF-8 com hash verificado e executar os cenários autorizados isolados de Carranca, Beto e Nina. P/J e avaliação humana continuam pendentes; nada foi publicado.

## H04 — primeira leva privada preparada (2026-10-25 21:52 BRT)

**Estado:** preparação local concluída; zero inferências H04 executadas neste checkpoint. PR #34 permanece aberta/draft e sem reviews; branch sincronizada antes desta atualização. A sessão do runner mantém a fila H04 local pronta e aguardando despacho controlado.

**Fontes e identidade:** os 16 arquivos privados travados para H04 foram revalidados contra os SHA-256 do manifesto fonte. Os textos carregados são os documentos de perfil fixados por commit: Carranca/Ranzinza, pacote consolidado v1.0 em 3d651fe1951818767b4a6b935732857f08cb7849; Beto, GAMER.md v0.2 em 21381c0975bef1da048d7887cbdfbd0dd97bed96; Nina, NINA-PRISMA.md v1.0 no mesmo commit. Os hashes do conteúdo do DNA efetivamente carregado ficam no manifesto privado por tarefa. Nenhuma fonte ou perfil foi alterado.

**Pacotes de evidência:** três fixtures UTF-8 privadas e inteiramente fictícias, uma para cada T13 profundo (CPU para Carranca, jogo de luta para Beto, anatomia de mod para Nina). Cada uma identifica claims, fontes simuladas, métodos/limites e proíbe alegações reais. Inputs, diretório e documentos fonte tiveram SHA-256 verificados antes do despacho. Arquivo de preparação: %USERPROFILE%\.codex\Revista_Gamer\ensaios-008\h04-isolated-batch-20261026\batch-inputs.json.

**Preflight sem rede:** a credencial existente foi lida sem exibir valores sensíveis e contém o escopo de uso direto já autorizado. O catálogo não foi consultado novamente. O lote está preparado no AgentQueue/SQLite privado existente para executar pelo mesmo TaskDispatcher com persona_writer, modelo gpt-6-luna, esforço max, sem fallback, uma chamada por tarefa, retenção de resposta integral, gate humano obrigatório e publication_state=not_published. Nenhuma chamada SIWC ocorreu na preparação.

**Limite de consumo:** o usuário informou 16% da franquia compartilhada antes da primeira leva. Para respeitar o orçamento, executar agora somente os três casos T13, um por persona, em ordem e com checkpoint entre resultados. Os segundos casos de correção permanecem pendentes: Carranca T06, Beto T09 e Nina T08. Não marcar H04 completo até esses casos e as avaliações P/J pendentes serem resolvidos ou registrados como bloqueados por orçamento.

**Hashes dos inputs T13:** Carranca 2cb680650abf0e79cacac5f280f5bcfec2cc96f03248bb59839e6b65cf87cf7f; Beto 6392334eddedadd861d40ca6c936927c35ef5173ef60c123fb911ad71a92ab0b; Nina 8b9b2e0e39eb436ae619d72fdc451de181c2e9e739ceb4793f08efeb6fa20cb1.

**Próximo passo:** despachar apenas Carranca T13. Após cada inferência, verificar estado, resposta completa, schema, hash, consumo, original integral e link no índice privado. Parar o lote em 401/403, 429, novo consentimento, modelo/esforço divergente, saída incerta/incompleta, schema inválido ou orçamento insuficiente; não repetir uma chamada incerta. Não publicar texto bruto no GitHub.

## H04 — Carranca T13 concluído (2026-10-25 21:53 BRT)

**Evidência real SIWC:** tarefa de redação T13 do Carranca/Ranzinza passou pelo TaskDispatcher existente e persona_writer v1.0.0, usando a persona consolidada v1.0 travada no commit 3d651fe1951818767b4a6b935732857f08cb7849. Modelo gpt-6-luna, esforço max, resposta completa, succeeded, role_schema_valid, store=false, stream=true, gate humano requerido e published=false. Duração 51.187 ms. Uso reportado: 4.510 tokens de entrada, 2.743 de saída (1.744 raciocínio), 7.253 total.

**Integridade e acesso ao texto:** original bruto UTF-8 preservado em C:\Users\saimi\.codex\Revista_Gamer\ensaios-008\h04-isolated-batch-20261026\artifacts\siwc-role-responses\69c60794-db84-58a0-bd05-d264ed109ccf.response.json; SHA-256 bb5901344f0187bc0800796bc07c696a288485e75de06d3a89986f3224d4e720, conferido com o manifesto. Índice privado C:\Users\saimi\.codex\Revista_Gamer\ensaios-008\INDICE-LEITURA-INTEGRAL.md agora tem links diretos para render legível integral, resposta bruta, manifesto, request e input UTF-8. Tamanho do render: 3.643 bytes. O relatório P/J desta amostra está em cases\ranzinza\T13\assessment.md, no mesmo diretório privado.

**Avaliação separada, Codex e provisória:** P = 12/14; voz tecnicamente compatível, mas ainda próxima de análise neutra, com ironia/assinatura pouco marcadas. J = 11/12; boa atribuição, separação de alegação e medição, preservação das diferenças metodológicas e conclusão suspensa; cenário de custo/uso ficou parcial. As escalas de aceite da matriz são propostas, não aprovadas. Isso não é revisão humana nem aprovação da direção e não generaliza para a persona.

**Limite do ensaio:** todas as entidades e fontes do caso são fictícias; o teste avalia resposta a um pacote controlado, não apuração de fatos reais. Não houve edição ou revisão textual. Texto bruto permanece privado e não foi copiado para Issue/PR.

**Próximo passo:** após este checkpoint, executar somente Beto T13; confirmar seu hash de resposta, schema, uso reportado e texto integral. Nina T13 continua na mesma primeira leva se o consumo e o orçamento observado permitirem. Casos de correção Carranca T06, Beto T09 e Nina T08 continuam pendentes; nenhuma chamada incerta será repetida.
