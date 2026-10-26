# ENG-CODEX-008 — checkpoint de execução

**Atualizado:** 2026-10-25 21:29 -03:00
**Issue de execução:** [#33](https://github.com/Saaimingo/Revista_Gamer/issues/33)
**Ordem documental:** [PR #32](https://github.com/Saaimingo/Revista_Gamer/pull/32)
**PR de implementação:** [#34](https://github.com/Saaimingo/Revista_Gamer/pull/34), draft, aberta, sem merge.

## Estado atual

- **H00:** concluída — estado remoto, base, fontes de persona, documentos obrigatórios, arquitetura e baseline conferidos.
- **H01:** concluída — executor SIWC genérico, validação de papel/modelo/esforço/schema e retenção integral da resposta.
- **H02:** concluída — testes offline de segurança, incerteza, lease, replay, fronteiras de evidência e falhas do provedor.
- **Próxima unidade:** H03 — preflight da conta existente, consulta única ao catálogo se necessária e uma primeira inferência real curta.
- **Branch:** `codex/eng-codex-008-siwc-validation`, criada diretamente de `codex/eng-codex-007-factory-radar@cd71022ef3b3d60fa4c97beb6db5583a03856102`.
- **Commits H00:** `b8e2dde` (checkpoint inicial), `05d3c8f` (vínculo à PR #34); ambos enviados para `origin/codex/eng-codex-008-siwc-validation`.
- **Commit H01/H02:** `60c4c0f` — executor por papel, retenção SIWC e regressões offline; pronto para push junto deste checkpoint.
- **Comentários H00:** [Issue #33](https://github.com/Saaimingo/Revista_Gamer/issues/33#issuecomment-6405340231) · [PR #34](https://github.com/Saaimingo/Revista_Gamer/pull/34#issuecomment-6405340777).
- **Baseline:** sem alterações de código antes desta branch; suíte serial `198/198 OK` em CPython 3.11.9, 134,945 s.
- **Chamadas SIWC/Plus nesta missão:** 0. Nenhum login, refresh, catálogo ou inferência foi iniciado; todas as chamadas de teste foram mockadas.
- **Orçamento informado pelo usuário:** 24% da franquia Codex/Plus, compartilhada com esta execução segundo a confirmação do usuário; consumo SIWC ainda não foi medido. H03 começa com uma chamada curta e verifica o resultado antes de qualquer expansão.
- **Saída editorial real:** 0; nenhum texto ou caso foi fabricado.
- **Publicação/merge/deploy:** não realizados; `published=false`.

## Estado remoto verificado

| Referência | Estado observado |
| --- | --- |
| PR #30 / ENG-CODEX-007 | aberta, draft, sem reviews; head `cd71022ef3b3d60fa4c97beb6db5583a03856102`; base `4de16640e67bd16c61468955e96e4ffa850d4cab` |
| PR #32 / contrato 008 | aberta, draft, sem reviews; head `a9aee221f1783d402bbed16ff13f1ea32042dae2`; base no head da #30 |
| PR #34 / implementação 008 | aberta, draft, sem reviews; base no head da #30; não mesclada |
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
- Artefatos dos testes ficaram em diretórios temporários de teste, removidos ao final. Ainda não existe saída real SIWC. O armazenamento real será escolhido fora do Git público e terá ACL verificada antes de H03.

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

## Gates para H03 — E17 real controlada

1. **Armazenamento:** inspecionar a ACL herdada em `%LOCALAPPDATA%` e em `%LOCALAPPDATA%\\Revista_Gamer\\ensaios-008`; criar a pasta apenas se a ACL já for privada. Não alterar permissões. Se houver leitura por usuários não autorizados, não armazenar nem chamar o SIWC e registrar o bloqueio enquanto se conclui trabalho offline independente.
2. **Conta e catálogo:** usar somente o CredentialStore já existente; não iniciar login, relogin, consentimento novo ou refresh fora do caminho suportado. Não exibir identidade, token ou segredo. Consultar o catálogo no máximo uma vez se o modelo não estiver verificado por evidência vigente; bloquear se acesso/modelo não estiver elegível.
3. **Primeira inferência:** explicitar `gpt-6-luna` e `max`, sem fallback, executar uma chamada curta pelo SIWCClient existente e pelo mesmo dispatcher/fila. Salvar request, resposta bruta integral e manifesto fora do Git público antes do parse/schema. O usuário reportou 24% de orçamento compartilhado; medir o uso disponível na resposta e fazer no máximo duas chamadas adicionais no lote H03 apenas se a primeira concluir e qualidade/orçamento comportarem.
4. **Parada segura:** parar em 401/403, 429, novo consentimento, modelo/esforço divergente, resposta incompleta/incerta ou orçamento insuficiente; não repetir chamadas incertas. Se a resposta for incompleta, marcá-la `incomplete`; nunca apresentar como texto integral.
5. **Trilhas de aceite:** qualquer texto editorial fica preservado integralmente, com metadados e hash, em storage local privado. Não gravar textos integrais de terceiros, tokens ou PII no Git/Issue/PR. `published=false`; revisão humana e critérios P/J continuam separados e pendentes.
6. **Identidades:** manter commits/hashes fonte fixados para Carranca/Ranzinza, Beto, Nina e diretriz de apuração; não alterar DNA. Não editar os históricos E17–E19 da 007.

## Próximo passo exato

H01/H02 estão implementadas no commit local `60c4c0f` e validadas por 109 testes focados, repetição de 13 testes críticos, `compileall` e `git diff --check`. Próximo: commitar este checkpoint, enviar os dois commits para a branch e registrar evidências nos comentários da Issue #33 e PR #34. Em seguida, executar o preflight ACL local de H03; nenhuma chamada SIWC real foi feita até agora.
