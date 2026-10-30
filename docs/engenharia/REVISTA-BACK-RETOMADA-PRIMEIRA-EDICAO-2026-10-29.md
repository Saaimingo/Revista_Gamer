# REVISTA BACK — Retomada do Codex e foco em primeira edição

**Data:** 2026-10-29  
**Status:** instrução de continuidade para investigação/execução controlada; **não é homologação nem autorização de publicação**.  
**Direção:** concluir uma revista navegável e funcional, não ampliar a fábrica.

## Fonte primária para a retomada
Leia primeiro, **no computador do diretor**, `D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md`. Este documento no GitHub é apenas o roteiro de retomada; **não substitui** o checkpoint local nem comprova por si que os arquivos locais estão presentes e íntegros. Confira também `git status` no clone `D:\Censurado-ollama-test`, o relatório/artefatos locais e o estado do repositório `Saaimingo/Revista_Gamer`. Não sobrescreva trabalho não commitado. Evite reaproveitar cegamente a PR #44, que corresponde à fábrica anterior.

## Evidências relatadas pelos últimos ensaios (confirmar no checkpoint local)
- Captador agendado do ChatGPT grava coletas factuais em `main:coletor/` com checagem de URLs anteriores; é fonte de candidatos, **não** reportagem revisada.
- Clone do Censurado em `D:\Censurado-ollama-test`. Ollama/Qwen local passou no teste de adaptador de inferência; DDGS `websearch` leu páginas públicas, com limitações de mecanismo e extração.
- A ponte SIWC autorizada produziu **uma resposta real** com `gpt-6-luna` via OAuth/Responses API, recebendo `response.completed`. Checkpoints de duas tentativas antigas permanecem `uncertain` e nunca devem receber retry automático.
- Testes focados de UTF-8, controle `reasoning_effort`, carregamento de 19 arquivos dos três pacotes de persona e prévia local passaram. O fluxo `run.py` com nós `draft` e `review` via SIWC **simulado** passou, com checkpoints e prevenção de duplicação, mas **não houve pipeline editorial integrado real com Luna**.
- Censurado foi selecionado como **base experimental**. Umbruch inspira composição de personas; Machine Herald inspira entrega de artigo, fontes e proveniência. Não há decisão de instalar/juntar três sistemas integrais. O visual final do Bloco 03 ainda não foi integrado ao pipeline.

## Meta do ciclo de entrega
Alcançar **uma primeira edição piloto da Revista Back aberta no navegador**: conteúdo original pesquisado e revisado, personas oficiais Carranca/Beto/Nina, identidade visual previamente aprovada, leitura funcional no computador e celular, aprovação humana obrigatória. Sem deploy/publicação pública até autorização específica da Direção.

## Ordem de trabalho
1. **Continuidade e segurança:** ler checkpoint local e artefatos, identificar mudanças não commitadas, propor/produzir backup versionado seguro em branch separada, respeitando licenças MIT/avisos e **sem armazenar OAuth, tokens, logs sensíveis ou textos editoriais privados em Git público**. Verificar o estado antes de alterar.
2. **Mapa de impedimentos de entrega:** identificar precisamente o mínimo entre pipeline existente e edição navegável. Nada de nova auditoria de três projetos ou arquitetura ampla. Reaproveitar ao máximo o que já funciona.
3. **Ensaio de fluxo real delimitado:** planejar uma execução de notícia real de `coletor/` → jornalista com DNA oficial → revisão → saída salva, pela ponte SIWC e `gpt-6-luna`. **Antes de qualquer chamada real**, apresentar quantidade máxima de invocações, orçamento e pedir autorização. Nenhum fallback para modelos mais caros ou API paga; uma chamada de IA ativa por vez, salvo até dois jornalistas quando autorizado. Não considerar a saída real aprovada só porque o mock passou.
4. **Leitor visual:** integrar artigo aprovado à experiência visual aprovada pelo Bloco 03, sem substituir a identidade. Tela do celular dedicada ao conteúdo, menu discreto, modos folhear/rolar configuráveis, leitura contínua ou duas páginas quando pertinente; testar navegador real em desktop e viewport móvel. Imagens somente com uso editorial autorizado e fonte registrada; placeholders explícitos quando necessário.
5. **Primeira edição piloto:** reunir material suficiente para Carranca, Beto e Nina, testar cadeia e visualizar a edição inteira. Publicação externa, redes sociais, patrocínios, áudio e novidades ficam fora do primeiro gate, salvo requisito já indispensável no material aprovado.

## Aceite e evidência
- Evidenciar arquivos/paths e hashes relevantes, URLs válidas e o que o agente efetivamente leu.
- Distinguir teste simulado, chamada real de modelo, reportagem factual e prévia visual efetiva.
- Preview deve abrir no navegador real, ser navegável, exibir identidade visual e não publicar automaticamente.
- Proteger chamadas SIWC por checkpoints e estado incerto; sem retries automáticos.
- Reporte curto: estado, impedimento real, prova obtida, próximo passo. Não declarar primeira edição pronta com arquivos Markdown isolados.

## Limites
Não alterar `main`, não mexer no antigo PR #44, não usar API paga, não publicar, não refazer fábrica, não executar inferência real sem orçamento/consentimento explícito; proteger o trabalho acumulado no clone. Projetos externos: `hec-ovi/censurado-web-brain`, `osmancakir/umbruchai-news-desk`, `the-machine-herald/machineherald.io`. Sem necessidade demonstrada de instalar os três.

**Atenção:** esta branch foi criada apenas para disponibilizar esta orientação ao Codex. O primeiro dever do Codex é verificar o checkpoint local e reconciliar os estados antes de codificar.

## Progresso local desta retomada

**Verificado em 29/10/2026.** O clone original `C:\Users\saimi\Revista_Gamer` continua na branch `codex/eng-codex-012-architecture-contracts`, limpo em `4130ac4`; a PR #44 não foi alterada. O trabalho novo está no worktree isolado `C:\Users\saimi\Revista_Gamer-primeira-edicao`, na branch desta orientação.

- **Backup do Censurado:** `docs/engenharia/backups/censurado-source-diff-20261029/` guarda patch de código de 23 arquivos, manifesto de hashes e licença MIT do upstream `hec-ovi/censurado-web-brain`. Base de origem: `a087e918515f5d01aa21f1b0d70c73b9ece725cc`; SHA-256 do patch: `1a5d23df284406016d3b9763b51fa12f4be58a94a27faece17b1679db45e2cf0`. `git apply --check --reverse` passou no clone fonte; o patch contém 23 arquivos e 3.783 inserções/2.090 remoções. A varredura de padrões de credenciais encontrou zero ocorrências; nenhum caminho `local-tests/` está no patch. A licença MIT e o manifesto foram preservados. O clone original permanece intacto.
- **Leitor visual local:** `docs/visual/prototipos/revista-back-leitor-piloto/` contém uma edição navegável em HTML autocontido, com capa, expediente, sumário, abertura da pauta, resumo captado, fontes, gate editorial e contracapa. O menu hambúrguer é o único acesso às opções em todos os formatos; nele ficam Folhear/Contínua, ajustes tipográficos, tela cheia e sumário. No celular o menu ocupa a tela; em rolagem, a faixa superior evita que o botão cubra o texto. A capa usa ilustração original gerada para esta prévia, sem imagem extraída dos ZIPs do Bloco 03.
- **Direção visual do Bloco 03:** comparados os três ZIPs em Downloads. `Revista_BACK_B03_Mobile_Imersivo_2026-10-27.zip` orienta a interação imersiva no celular; `Revista_BACK_Bloco03_Cinco_Modelos_Editorais.zip` registra a regra de capa (BACK destacado, arte central, chamadas secundárias laterais e chamada principal abaixo), mas seu próprio README classifica o pacote como proposta; `Revista_Gamer_Bloco03_v03.zip` é exploratório. Nenhuma arte de referência foi copiada para a branch.
- **Matriz responsiva:** inspeção visual no Edge via CDP em 390×844, 768×1024, 1024×768, 1366×768 e 1440×900. Todos os cinco viewports mantiveram o hambúrguer, não apresentaram rolagem horizontal e não geraram exceções de runtime. 768×1024 apresenta uma página; 1024×768, 1366×768 e 1440×900 apresentam duas páginas lado a lado. No mobile foram inspecionados capa, abertura da pauta, menu aberto e rolagem contínua. A inspeção é de viewport de navegador, não de aparelhos físicos.
- **Conteúdo escolhido:** `coletor/2026-10-29-1840.md`, pauta de Gothic Remake captada da Gematsu. A página mantém o resumo como pauta e inclui um comunicado oficial da THQ Nordic, localizado e aberto nesta retomada. A classificação “Jogos eletrônicos” é reaproveitada da seção do Captador como etapa local sem inferência; o artigo de Carranca, a apuração independente, revisão factual e aprovação seguem pendentes.
- **Persona de Carranca:** o manifesto local `persona_sources_manifest.json` identifica o pacote `ranzinza` com sete arquivos, origem `3d651fe1951818767b4a6b935732857f08cb7849`; os próprios DNAs confirmam Arlindo Carranca (“Ranzinza”). Beto tem seis arquivos e Nina seis, da origem `21381c0975bef1da048d7887cbdfbd0dd97bed96`. Os pacotes fonte não foram copiados ao backup público.
- **SIWC e autorização:** runpack privado fora do Git preparado com notícia existente do Captador, pesquisa complementar DDGS, ata curada, prompt de Carranca e configuração validados offline. A sequência tem somente duas chamadas GPT-6 Luna via OAuth/SIWC (`draft` e `review`/gate), sem retry, respin, imagem ou publicação; uma resposta `uncertain` encerra a execução. Nenhuma chamada foi feita. O prompt montado tem 133.486 caracteres: estimativa aproximada de 33.372–44.496 tokens de entrada e 700–1.500 de saída (total aproximado de 34.100–46.000 tokens), usando uma faixa de 4–3 caracteres/token e saída planejada; não equivale a créditos, custo nem medição do SIWC. A Direção deve autorizar antes de executar. Beto e Nina ficam para autorizações posteriores.
- **Direitos de imagem:** a prévia usa ilustração original gerada e identificada como não oficial; nenhuma arte dos ZIPs ou do jogo foi copiada. A permissão de uso editorial de artes oficiais da THQ Nordic continua sem comprovação; o kit de imprensa não foi baixado. A publicação externa permanece bloqueada até licença/consentimento das imagens e aprovação humana.
- **Evidência:** `docs/visual/prototipos/revista-back-leitor-piloto/design-qa.md` registra as comparações visuais, os tamanhos de viewport e as correções responsivas. A prévia demonstra o fluxo editorial e a pauta integrada; não demonstra uma reportagem de Carranca. Nesta retomada, a configuração de duas etapas e a montagem dos contextos de persona foram validadas sem rede e sem provedor; contagem aproximada baseada nos prompts renderizados. Os testes e a única chamada curta real descritos na seção de checkpoint são evidência do trabalho anterior, não da reportagem integrada. Não foi executada suíte de testes nem inferência real.

**Próxima sequência:** após autorização explícita, executar uma única prévia de Carranca com no máximo as duas chamadas listadas, guardar os checkpoints e entregar o artigo para aprovação humana. Integrar o artigo aprovado na abertura já existente do leitor; depois avançar com Beto e Nina nos mesmos componentes, mediante autorização para as respectivas inferências. Pesquisa DDGS e demais ajustes locais podem seguir sem franquia. Não publicar nem fazer deploy.


## Atualização de continuidade da Direção após o piloto real — 29/10/2026

**LEITURA PRIORITÁRIA PARA A PRÓXIMA SESSÃO CODEX**: [ORDEM CONSOLIDADA — autonomia, Blocos 02/03, acervo e preparação da VPS](DIRECAO-INTEGRADA-FABRICA-AUTONOMA-BLOCOS02-03-VPS-2026-10-29.md). Essa ordem incorpora integralmente por referência os pareceres [Bloco 02, Issue #49](https://github.com/Saaimingo/Revista_Gamer/issues/49) e [Bloco 03, Issue #48](https://github.com/Saaimingo/Revista_Gamer/issues/48); o Codex deve ler os relatórios completos originais, não apenas esse índice.

**IMPORTANTE: este checkpoint contém histórico de ANTES das inferências reais.** A seção anterior que diz que nenhuma reportagem integrada ocorreu e que duas chamadas estão pendentes não descreve o estado mais recente. Conforme relatório posterior do Codex trazido pelo diretor, **duas chamadas reais SIWC GPT-6 Luna foram executadas para Carranca** (draft 21.968 entrada/717 saída; review 22.383 entrada/424 saída; 44.351 entrada e 1.141 saída no total). Reportagem Gothic Remake e parecer de 1 bloqueio + 5 polimentos foram integrados à prévia local; conteúdo continua **PENDENTE DE CORREÇÃO**, não aprovado. Não executar J1/R1 novamente. Essas cifras são tokens reportados, NÃO medição do saldo Plus.

**DESLIGAMENTO INESPERADO:** o diretor desligou o PC antes de o Codex escrever o checkpoint pós-chamadas e informou que o HTML atualizado estava apenas no disco local, sem commit. Ao retomar, a PRIMEIRA AÇÃO deve ser conferir estado real dos worktrees, arquivo de checkpoint, HTML, checkpoints SIWC privados e git status; fazer backup antes de qualquer alteração. NÃO afirmar que a versão do HTML após as duas inferências foi salva no GitHub. NÃO copiar credenciais/tokens/respostas privadas para commits.

**DECISÕES NOVAS:** o Codex é engenheiro, NÃO operador contínuo; a fábrica deve partir da detecção da coleta 08h00/18h40 e trabalhar autonomamente até a matéria aprovada no acervo, via orquestrador/DBOS e agentes por papéis. Ciclo por matéria J1/R1, se necessário J2/R2, se necessário J3/R3, após terceira rejeição bloqueio. Pesquisas complementares e necessidades de imagem são solicitadas e retornam ao mesmo fluxo. Só depois, em ciclo SEPARADO, grade/edição/diagramador/montagem. Requisitos de observabilidade para central do diretor, MAS **não implementar o painel ainda**. Testes locais em novembro e portabilidade preparada para VPS 24/7 em dezembro, contratação/deploy somente autorizados futuramente; horários adicionais de coleta são mera hipótese. Não trocar modelos nem iniciar nova chamada SIWC real por causa desta documentação.

**Handoff obrigatório duplo:** atualizar depois de verificação local este checkpoint no GitHub E o arquivo no PC `D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md`, preservando backup, hashes e histórico de divergências. Não é possível sincronizar automaticamente o arquivo Windows a partir deste commit GitHub.


## Continuidade consolidada após desligamento — 2026-10-30

**Release de continuidade:** RB-FABRICA-P1-2026-10-30. Esta atualização substitui o estado operacional histórico acima e preserva o conteúdo anterior como registro.

### Recuperação confirmada

- Worktree do leitor em C:\Users\saimi\Revista_Gamer-primeira-edicao, branch codex/revista-back-primeira-edicao-20261029, HEAD 7456bb934aff4bbfa5580f9dfae6f3f1e8aeef82. O tip remoto antes desta atualização era 4fea7bb41cd456b6be6029a33954a9dc46a5a26a. O único arquivo local modificado continua sendo docs/visual/prototipos/revista-back-leitor-piloto/index.html, SHA-256 F6B6A31AB008BBEDC745E7DEEF198D20B272B9395E183753D9F54785CE71D19F; não foi commitado nem enviado.
- Clone local do Censurado permanece em main, HEAD a087e918515f5d01aa21f1b0d70c73b9ece725cc, com alterações locais preservadas. Backup privado pré-implementação conferido por hash: 362 arquivos, zero divergências; hash de SHA256SUMS.txt 28DA6D8069EF8C45293AF8D6221FA9C77919F66AA9F859E00CADAD4DAFDE8D9A.
- J1/R1 continuam preservados e inalterados fora do Git: draft.txt 52F1ABCBAA38FD71D58645B8050C70506F3CF4DBADDBDDF21C9FE1E58DD052DE; draft.json 8D363FDDDAE7AC084ED8651183FE6D9C38E98C6912D128EB2F4426A0F6A3FD62; review.txt E6B1306A1EF0729583E3FCFA519FA61D8E41E69A7E3D320099818574817921F7; review.json 0FAF227786DCA52F2F89519ABFF064D09825318CEF34FC451F848C2FE304733F. As duas chamadas SIWC reportaram completed/attempt=1; não foram repetidas. Uso reportado: J1 21.968/717 e R1 22.383/424 tokens; isso não mede saldo de assinatura.

### Implementação local

No clone do Censurado foi preparada uma lane local para detecção read-only do Captador, verificação de Git blob e ETag, fila SQLite idempotente, worker serial com lock, triagem, encaminhamento limitado ao roster permitido, pesquisa com proveniência de páginas lidas, correções J1/R1 → J2/R2 → J3/R3 e acervo privado append-only após aceite explícito da revisão. A factory não chama o publicador; imagens e montagem de edição continuam separadas. O contrato, schema e comando run.py factory foram atualizados apenas no clone local, ainda sem commit/PR.
- Hashes SHA-256 locais: collector.py CE3AE0420B7D8200B48F583A003C6D430D3409134E7AC9B1F85E402276601652; factory_queue.py B5C99647E4CDBEE4F67C4DB64CA0C72D8001E6BD7964489433425BEEA2E2E0FC; archive.py 99A442B7C5A0B344F0D69E6EFEC5D7988CE7241747BE851F2E2D2A9B0AE6D440; factory_worker.py 4961C4F4E7199FE0B5A68F1E5AA5BE1ACB96CD61ECC252B48E2F5B55BD527E59; flow.py 05007716C8289DCFAA371ECB86BFAABBE3C4C94624E9BA1AC16ACE764AC32BD6; config.py F5D82F690072D2B066302B30A4CAF4D5FABBDABD3B35816E3407BCAAD438731E.
- A configuração local de factory usa API local e rejeita adaptadores SIWC nos nós dessa lane. Ela não foi executada: nenhum novo poll do Captador, pesquisa web real, chamada de modelo, publicação ou deploy ocorreu nesta retomada. Os handles seed ranzinza/gamer-x ainda precisam ser verificados no backend; a variável de token local não estava disponível para confirmar o roster.

### Testes e gates remanescentes

- 10 testes focados da nova lane passaram, incluindo workflow DBOS simulado com pesquisa complementar, correção, aceite e arquivamento sem publicar. A seleção offline do pipeline/source_images sem tópicos e sem o teste de timeout sensível ao host terminou com exit code 0. git diff --check passou.
- A suíte ampla ainda registra duas falhas no ambiente disponível: o teste de tópicos não encontra pydantic; test_batch_contains_a_hung_article_and_continues excede seu limite de quatro segundos para ambas as pautas, reproduzido com Python 3.11 e com o .venv Python 3.14. Nenhuma dependência foi instalada e a lane antiga não foi alterada.
- Transições ainda manuais: confirmar roster/credencial e endpoint local; iniciar o worker ou configurar agendamento supervisionado; decidir pautas bloqueadas/incertas; revisão visual humana; escolher e montar edição; aprovar direitos de imagem; autorizar qualquer publicação/deploy. Nenhum agendamento está ativo.

O checkpoint local D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md também foi atualizado com esta release e preserva cópia prévia local. Este documento público registra apenas hashes/metadados; reportagem e parecer continuam privados.

## Continuidade de autonomia da factory — 2026-10-30 (v0.1.2)

**Estado:** ensaio integrado passou em simulação; a factory não está homologada. Nenhuma inferência real, publicação, montagem, deploy ou alteração no leitor HTML ocorreu nesta etapa.

### Estado preservado

- Clone local Censurado: main, HEAD a087e918515f5d01aa21f1b0d70c73b9ece725cc, alterações locais sem commit. Snapshot code-only RB-FACTORY-P1-v0.1.2-20261030: 46 arquivos, SHA-256 ca996dbd9756abc9e0c494cc919b6791366dca3a52f448e21aa5d202b4d88800; SNAPSHOT.json SHA-256 0811ea4e15a9fa488967faa162a48b1372ee09d5007270e158fde84df5b7e590. v0.1.1 e o checkpoint anterior foram preservados localmente.
- Worktree do leitor: branch codex/revista-back-primeira-edicao-20261029 em 8a7992a64a9256465af0432c7d9b70c2c0cfb7ef, igual ao upstream. O HTML local atualizado permanece como única modificação, SHA-256 F6B6A31AB008BBEDC745E7DEEF198D20B272B9395E183753D9F54785CE71D19F.
- Checkpoint local atualizado: SHA-256 9C30F35E1C773D21E9FD46883C291E83951FD118354CDBB6652A3810DA0AEF67. Cópia anterior local: REVISTA-BACK-CHECKPOINT.md.pre-autonomy-20261030, SHA-256 5FC535BC0E9EDA69D92CF475C5366C34BDE5E27F5A89BFC43C01AF9C70FDE289.

### Autenticação e cadastro

A variável NEWSROOM_OPERATOR_TOKEN foi verificada contra o mecanismo oficial, não presumida por uso em teste legado: bootstrap.sh do Censurado a provisiona como Bearer oficial e a stack atual a encaminha ao executor existente. GET /authors exige Bearer válido e não exige escopo de escrita naquela rota. O backend real estava indisponível; a factory não criou token nem serviço novo. A configuração de produção mantém o nome oficial, enquanto o ensaio usou REVISTA_BACK_SIMULATED_BEARER somente contra GET /authors em servidor loopback. Credenciais OAuth locais foram verificadas apenas por existência/metadados; nenhum conteúdo foi lido ou usado.

O roster de teste foi claramente marcado como simulado e utilizou os handles oficiais ranzinza, beto-cartucho e nina-prisma, encontrados no manifesto local. gamer-x não está no manifesto e não foi usado. Registro online e disponibilidade de agentes reais continuam não verificados.

### Ensaio integrado

Comando único: python local-tests/revista-back-factory/demo_autonomy.py.

- Fonte real somente leitura: Saaimingo/Revista_Gamer@main:coletor/2026-10-30-0800.md, Git blob SHA 29d1765245c6f1b4f26f61d9f55aeba879e119a1, 9 candidatas.
- Um processo poll-only gravou 9 tarefas pendentes. Um processo novo executou o worker existente em modo drain-once e consumiu a fila autonomamente: 1 item foi ao acervo de simulação, 2 foram bloqueados e 6 descartados na triagem simulada.
- A pauta de mods foi encaminhada a nina-prisma, pediu pesquisa complementar, voltou à mesma jornalista, recebeu correção e aceite simulado. A pauta de hardware recebeu três revisões sem aceite e bloqueou em R3. A pauta de jogo com beto-cartucho recebeu rejeição explícita e bloqueou em R1.
- Responses API local simulada: 27 chamadas, exclusivamente gpt-6-luna/max; 27 checkpoints completados uma única vez, attempt=1. OAuth real não foi lido, e não houve fallback. Pesquisa usou CLI fake sem acesso externo; respostas e evidências sintéticas foram rotuladas e usaram simulated.invalid.
- Cadastro simulado: 9 leituras GET /authors, zero escritas; NEWSROOM_OPERATOR_TOKEN não foi encaminhado ao teste.
- Acervo exclusivamente de simulação: article SHA-256 8279e2d30434df797694bad51181f9951f2d54ba0919081cec121295c128132b; packet SHA-256 a164c9f24d3fff032c06be7696badfb781790a9f2ef36e81b46da5ced1bd336f; publication_ready=false e aprovação humana pendente. image_needs foi preservado com direitos pendentes.
- Novo processo repetiu a detecção; adicionou zero tarefas e preservou os estados finais/ETag. Nenhuma montagem ou publicação foi chamada.
- Manifesto local da simulação, sem conteúdo editorial remoto: SHA-256 d02a1c46365157aeda2e1c65807c0ff4254210d767d82390be1b43d966e0790d.

### Alterações e testes

A lane passou a aceitar uma captura Markdown explicitamente indicada, após verificar caminho e Git blob SHA. O worker existente recebeu --drain-once para executar poll e drenar uma fila finita; --watch continua sendo a opção contínua. A configuração permite o adaptador SIWC existente somente com gpt-6-luna, checkpoints duráveis e sem retry automático de chamada incerta. O prompt da reportagem registra image_needs com direitos pendentes. A factory não chama o publicador.

- automation/pipeline/tests/test_factory.py: 13 passed.
- local-tests/oauth-siwc/test_responses_adapter.py: 21 passed.
- local-tests/oauth-siwc/test_pipeline_siwc_integration.py: 1 passed.
- git diff --check: passou.
- Pydantic 2.14.2, pydantic-settings 2.16.2 e pytest 9.2.0 foram instalados somente no .venv; o teste focado de tópicos passou.
- O teste antigo test_batch_contains_a_hung_article_and_continues continua falhando no limite de 4 s. A causa isolada é inicialização fria do subprocesso Python/DBOS (~7,3 s) mesmo quando as chamadas simuladas somam ~0,44 s. O limite e a fábrica antiga não foram modificados.
- As primeiras iterações do mock falharam por um pressuposto do parser de teste sobre a ordem das chaves JSON e por encerramento CTRL_BREAK instável no Windows; o parser foi generalizado e o ensaio final usa --drain-once. Resultado final acima passou.

### VPS e próximos gates

O Compose atual reinicia o executor de horários, mas não executa a nova factory. Antes da VPS, adicionar o worker na mesma stack Censurado com política de reinício, dependência do publish saudável e armazenamento persistente para fila, acervo e DBOS runs. Não foi alterado Compose nem feito deploy. A fila usa IDs estáveis e retoma primeiro tarefas running; o re-poll sem duplicidade foi demonstrado localmente.

A homologação ainda depende de backend e cadastro reais disponíveis, uma autorização futura para inferência real gpt-6-luna, validação editorial com serviços/agentes reais e configuração futura do worker na mesma stack VPS. Aprovação humana, direitos de imagem, montagem e publicação continuam gates separados.


## Hash final do checkpoint local — 2026-10-30

Após corrigir a codificação do trecho acrescentado, o checkpoint local REVISTA-BACK-CHECKPOINT.md ficou em UTF-8, SHA-256 FC3A2358D021452A794797B4BFAD431471A7926EB998DD7B13280A783EF787B3. A cópia anterior foi preservada como REVISTA-BACK-CHECKPOINT.md.pre-autonomy-20261030, SHA-256 5FC535BC0E9EDA69D92CF475C5366C34BDE5E27F5A89BFC43C01AF9C70FDE289. Nenhum texto privado de reportagem ou parecer foi acrescentado a este registro remoto.


## Configuração final gpt-6-luna e snapshot v0.1.3 — 2026-10-30

A configuração persistente da nova factory foi alinhada ao adaptador OAuth/SIWC existente, exclusivamente gpt-6-luna/max e sem fallback. Nenhum worker foi iniciado, token lido ou inferência real executada. O backend real continua indisponível e o cadastro online das personas não foi verificado.

O ensaio mock foi repetido após o alinhamento: a coleta real main:coletor/2026-10-30-0800.md permaneceu no blob SHA 29d1765245c6f1b4f26f61d9f55aeba879e119a1; 9 tarefas, 1 arquivada somente no acervo de simulação, 2 bloqueadas, 6 descartadas; 27 Responses simuladas gpt-6-luna/max; re-poll adicionou 0. O status continua passed_simulation_only. Hash do manifesto local final: 8fbfaf4c39c832c452cc6ce2ae393e4c4120b0bb47d127abfc7f9e56155cfaca. Hash do artigo simulado: 8279e2d30434df797694bad51181f9951f2d54ba0919081cec121295c128132b; packet final: d7a96ba1cd20345557c4f645053daabd3326bc0fbdae6a669ff520a7c3ec3a59.

Snapshot code-only final RB-FACTORY-P1-v0.1.3-20261030: 46 arquivos, SHA-256 8dabd229848cdc790ca5deb24b4ca139e19e1bbbb509650d76de8cac95590166; manifesto SHA-256 dbe3b3ec7479a04a2ec8d479bb6010a28b1b5f0c825b8efbfc63b7f31ebb3e95. v0.1.2 permanece preservado.

Checkpoint local atual REVISTA-BACK-CHECKPOINT.md: SHA-256 18856F150364952D1BD87C4499B6AE15E1033BFE02FC6BB74E0035B29FCE8FE7. Versão local imediatamente anterior preservada como REVISTA-BACK-CHECKPOINT.md.pre-v0.1.3-20261030, SHA-256 FC3A2358D021452A794797B4BFAD431471A7926EB998DD7B13280A783EF787B3. Nenhum texto privado de reportagem ou parecer foi incluído.

## Infraestrutura real e branch isolada da factory - v0.1.4 - 2026-10-30

### Preservacao e versionamento

- O snapshot local v0.1.3 permaneceu inalterado: `RB-FACTORY-P1-v0.1.3-20261030.zip`, SHA-256 `8dabd229848cdc790ca5deb24b4ca139e19e1bbbb509650d76de8cac95590166`; manifesto SHA-256 `dbe3b3ec7479a04a2ec8d479bb6010a28b1b5f0c825b8efbfc63b7f31ebb3e95`.
- A lane foi commitada localmente em `D:/Censurado-ollama-test`, branch `codex/revista-back-factory-v0.1.4-20261030`, commit `48515ed30476e0d4338ae8b02a5f69840ca5ceaa`, filho da base `a087e918515f5d01aa21f1b0d70c73b9ece725cc`. Sao 28 arquivos de codigo/config-exemplo/contrato/testes; LICENSE segue igual a base.
- O commit exclui `local-tests/`, checkpoints, bancos, prompts privados, credenciais e textos editoriais. O checkpoint local anterior (SHA-256 `18856f150364952d1bd87c4499b6ae15e1033bfe02fc6bb74e0035b29fce8fe7`) foi preservado como copia local `.pre-v0.1.4-20261030`. Checkpoint local atualizado: SHA-256 `acc09a7cbda6454b2be5ecb435b062d65468381b7c5b188daa2d5aeea10fae11`.
- Envio do codigo ao remoto Censurado e criacao da branch pelo conector GitHub foram negados por HTTP 403; a credencial `Saaimingo` nao tem permissao de escrita em `hec-ovi/censurado-web-brain`, e a integracao retornou `Resource not accessible by integration`. Nao foi criada referencia remota, PR ou fork. `main` local/remoto nao mudou. A branch e o commit seguem preservados localmente aguardando acesso de escrita.

### Worker na stack existente

- Foi preparado o servico Compose `factory` no perfil opt-in `factory`, usando o executor/image existentes. Executa `run.py factory --watch`, reinicia com `unless-stopped`, espera `init-perms` e health do `publish`, e persiste fila, runs DBOS e acervo em `./data`. Configuracao e prompts ficam em `FACTORY_CONFIG_DIR` montado read-only e ignorado pelo Git.
- A configuracao-exemplo seleciona somente OAuth/SIWC `gpt-6-luna/max`, sem fallback. O armazenamento OAuth POSIX usa `XDG_DATA_HOME=/data/factory-oauth`, com modos 0700/0600. Credencial Windows DPAPI nao foi lida nem copiada para Linux; login OAuth oficial no runtime de destino continua necessario.
- `.env.example` documenta `COMPOSE_PROFILES=factory`; esta preparacao nao foi ativada nem implantada.

### Bloqueios reais observados

- Sem listener ou health check em `127.0.0.1:8082` e `:8080`. O checkout irmao `censurado-web-backend`, `.env`, `keys.json` e `factory-config/factory.config.json` estao ausentes. O engine Docker nao esta ativo (named pipe Linux engine ausente).
- O codigo/config original confirma `8082` como backend `publish` construido do sibling `censurado-web-backend`; `8080` e o llama.cpp configurado no pipeline antigo. Nenhum `llama-server` executavel/processo foi encontrado. `ollama.exe` nao foi usado como substituto.
- `NEWSROOM_OPERATOR_TOKEN` nao existe em env process/user/machine nem `.env`. O codigo oficial o provisiona pelo `bootstrap.sh`, que roda rotacao de chave; nao foi executado. Sem servidor e credencial Bearer, nao foi chamado `GET /authors`. Cadastro/disponibilidade reais de `ranzinza`, `beto-cartucho` e `nina-prisma` permanecem nao verificados; `gamer-x` nao foi inventado.
- O arquivo local OAuth DPAPI existe; apenas existencia/metadados foram vistos. Nenhuma inferencia real GPT-6 Luna ou outra chamada externa foi feita. A factory ainda nao esta homologada para agentes reais.

### Verificacao e continuidade

- Teste focado combinado: 53 passed (Compose, factory, adaptador API e SIWC/Responses simulados). Tudo offline/mock; Compose nao foi executado porque Docker Engine esta inativo.
- Hashes: `factory.config.example.json` `9968f5d535bc7250b0e3119ed339291241390e769687d227d0ebe409e85c300c`; `docker-compose.yml` `c9ed94ef0212040f7cae67c3a83cdbadd661cf5731c44fb411de04d1daac32f7`; `automation/executor/Dockerfile` `805bd6876c94e18bf1c4c75a55bf4ec984009e8be4f9dd4d296973f53e36ace9`; `factory_worker.py` `80ff7234a8bc907ccde33c690b7fa3f7bed04366aac8ec9e64d4760195e60c37`; `factory_queue.py` `f7d627533ffd95a0805a96d60d27efef6f36cfb361d0561c58ee7f5a262a4967`; `siwc_auth.py` `be3e8a78d48a1b04cb6351018c0972a3368d8a6c072adf5afaff429290f1a0e6`; `call_journal.py` `c9b6e19c3476a298f935bb59a1ebfce9b67922da5a4d074db9f4d0f5113d50ba`.
- Worktree do leitor segue na branch `codex/revista-back-primeira-edicao-20261029`. O unico arquivo local nao commitado continua `docs/visual/prototipos/revista-back-leitor-piloto/index.html`, SHA-256 `F6B6A31AB008BBEDC745E7DEEF198D20B272B9395E183753D9F54785CE71D19F`. Esta atualizacao altera somente este checkpoint; o HTML permanece preservado.
- Checkpoint remoto antes desta atualizacao: branch em `946fb013cda46576eeba7979fb51b6e4becd68dc`, checkpoint blob `88204019a4a2d9d7ad2e99af7748147454ccb862`. Este addendum preserva a versao anterior pelo historico Git; nenhuma reportagem ou parecer privado foi incluido.
