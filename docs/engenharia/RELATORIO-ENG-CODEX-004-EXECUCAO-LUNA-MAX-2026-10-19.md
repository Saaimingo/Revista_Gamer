# Relatório técnico — ENG-CODEX-004: execução local SIWC Luna Max

- **Issue:** [#9 — Gate SIWC Luna Max e benchmark editorial por matéria](https://github.com/Saaimingo/Revista_Gamer/issues/9)
- **Data:** 2026-10-19
- **Status:** gate Luna Max comprovado; uma amostra técnica real de 578 palavras no tipo cover, abaixo da meta e não pronta como capa; benchmark por categoria incompleto
- **Branch:** `codex/eng-codex-004-luna-max`, separada e baseada no head do PR #8
- **Base:** `962dcd4` (`codex/motor-editorial-orquestracao-agentes-plus`, correção C-001 do PR #8)
- **PR #8:** aberto para revisão, sem merge
- **PR desta entrega:** [#10 — ENG-CODEX-004](https://github.com/Saaimingo/Revista_Gamer/pull/10), aberto separadamente, com base no PR #8 e sem merge

## Resultado

O catálogo da conta autenticada via Sign in with ChatGPT (SIWC) listou o slug `gpt-6-luna`. O Motor Editorial passou a exigir modelo e esforço explícitos, consultar o catálogo, não fazer fallback e validar o modelo e o esforço retornados no objeto concluído do Responses API.

Depois do gate, foi executado um ensaio editorial local, com pacote preparado a partir de seis fontes públicas e seis chamadas sequenciais: análise de fontes, estrutura, redação, checagem factual, revisão e correção. Todas retornaram `gpt-6-luna` e `reasoning.effort=max`. A saída ficou em `awaiting_human_review`, com `human_review_required=true` e `publication_state=not_published`.

O ensaio demonstra execução real de ponta a ponta em uma amostra técnica no tipo `cover`. As 578 palavras ficam abaixo da meta de 900–1.200, o revisor devolveu `revise` e o fluxo histórico não revisou editorialmente o texto corrigido. Portanto, a amostra não é uma capa concluída nem matéria pronta. Ela também não demonstra aprovação editorial, média estável de consumo ou viabilidade de um ciclo completo da revista.

## Gate SIWC

Documentação oficial consultada:

- [SIWC — modelos e inferência](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference): catálogo por `GET /v1/models` e inferência pelo endpoint público `/v1/responses`.
- [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna): slug `gpt-6-luna` e valores aceitos para `reasoning.effort`, incluindo `max`.
- [Limitações do preview SIWC](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations): `max_output_tokens` não é suportado.
- [Fast mode](https://developers.openai.com/api/docs/guides/fast-mode): o parâmetro de serviço Fast é uma modalidade da API com preço pay-as-you-go.

Uma única prova sintética mínima concluiu antes de qualquer inferência editorial:

- tarefa `54eb1e02-ba49-454f-bd47-2cf0b2cfe097`, estado `succeeded`;
- modelo solicitado e retornado: `gpt-6-luna`;
- esforço solicitado e retornado: `max`;
- endpoint: `/v1/responses`, com `store=false` e `stream=true`;
- duração medida: 2.516 ms;
- usage reportado: 102 tokens de entrada, 36 de saída (18 de raciocínio), 138 no total;
- resposta sintética validada como `status=ok`; nenhum dado editorial foi enviado.

**Fast não foi usado nem validado no SIWC.** O modo Fast exibido no Codex interativo não comprova que exista opção equivalente no SIWC. A modalidade Fast documentada para a API é paga e foi excluída desta execução.

## Amostra real e instrumentação

O pacote [`ENG-CODEX-004-RTX5090-PACOTE-FONTES.json`](evidencias/ENG-CODEX-004-RTX5090-PACOTE-FONTES.json) registra seis URLs, publicador, data, tipo, confiança de fonte, resumo de evidência e data de consulta. A pista de vídeo fornecida na Issue não foi usada como evidência: a página não ficou disponível na consulta. Nenhuma entrevista, teste de hardware ou benchmark próprio foi realizado.

Execução `461f354e-abcb-42f7-bb29-dfa2530d15f8`, em Windows 11 local, com o perfil interno `internal-controlled-editorial-experiment@1.0.0` (SHA-256 `e076e792fb1e204f86e5a21ed4787884eaf19f2b2cb656b81bfa9e5dc43e9397`). As seis tarefas SQLite concluíram com uma tentativa cada. O artefato integral e o banco permanecem no diretório privado `%LOCALAPPDATA%\RevistaGamer\Codex004-Editorial`; a amostra e as métricas sanitizadas estão versionadas em `evidencias/`.

Cada etapa da execução histórica fez uma chamada de inferência Responses com `store=false` e streaming. Houve também sete consultas de catálogo: uma verificação inicial e uma antes de cada etapa. A duração dessas consultas históricas não foi instrumentada; os tempos abaixo são das inferências e a duração total é a parede do processo. O código corrigido no PR #10 faz uma única consulta preflight por execução, compartilha o conjunto validado entre os estágios e mede duração e timestamps de `GET /models` para ensaios futuros.

| Etapa | Duração (s) | Entrada | Saída | Raciocínio | Total |
|---|---:|---:|---:|---:|---:|
| Análise de fontes | 39,922 | 1.342 | 1.919 | 903 | 3.261 |
| Estrutura | 17,610 | 2.127 | 777 | 195 | 2.904 |
| Redação | 52,328 | 2.668 | 2.427 | 767 | 5.095 |
| Checagem factual | 166,407 | 2.977 | 8.216 | 4.989 | 11.193 |
| Revisão | 39,859 | 6.149 | 1.906 | 1.552 | 8.055 |
| Correção | 48,579 | 6.463 | 2.348 | 1.217 | 8.811 |
| **Total** | **364,705** | **21.726** | **17.593** | **9.623** | **39.319** |

A parede total do pipeline foi 370,407 s (6 min 10 s), entre `20:10:48.688` e `20:16:59.101 UTC`. Os tokens são o usage informado pelo provedor, não uma estimativa de porcentagem da franquia Plus. O tempo de pesquisa e preparação das fontes não foi medido.

Os 9.623 tokens de raciocínio são um detalhamento de `output_tokens` (17.593), não uma parcela adicional a somar. Os 39.319 tokens totais permanecem o total informado pelo provedor. A pesquisa histórica não teve cronômetro; o CLI agora separa a validação local do pacote e aceita `--source-collection-duration-ms` para registrar a coleta manual de fontes em execuções futuras. Valor ausente permanece `null`, sem estimativa.

O rascunho final contém 578 palavras, abaixo da meta interna de 900–1.200 para capa. O revisor devolveu `revise` com três achados; a etapa de correção ajustou o texto, mas deixou pendências factuais. O resultado continua sujeito à leitura e decisão humana. A [amostra técnica em formato cover](evidencias/AMOSTRA-CAPA-RTX5090-CODEX-004.md) conserva o texto produzido, a identidade versionada e as referências clicáveis; ela não é tratada como capa pronta nem como média.

## Leitura das evidências jornalísticas

As páginas oficiais consultadas confirmam especificações publicadas da RTX 5090 e da RTX PRO 6000 Blackwell, mas não confirmam nas páginas examinadas que ambas usem o mesmo die GB202 nem que tenha ocorrido redirecionamento de chips. A reportagem de 10 de outubro sobre a interrupção foi apresentada como rumor não verificado; a cobertura consultada rastreia a alegação a fontes de vazamento. A notícia posterior sobre Jeff Fisher é indireta e atribuída a relatos de terceiros, sem transcrição ou comunicado escrito da NVIDIA localizado neste pacote. Escassez e listagens de varejo não provam a causa nem a interrupção da produção.

Fontes principais: [NVIDIA RTX 5090](https://www.nvidia.com/en-us/geforce/graphics-cards/50-series/rtx-5090/), [NVIDIA RTX PRO 6000](https://www.nvidia.com/en-us/products/workstations/professional-desktop-gpus/rtx-pro-6000/), [Tom’s Hardware, 10 out.](https://www.tomshardware.com/pc-components/gpus/nvidia-reportedly-halts-geforce-rtx-5090-production-in-favor-of-ai-data-center-and-professional-gpus-impending-supply-drought-expected-to-drive-up-prices-rtx-5080-24gb-rumored-as-new-gaming-flagship), [Hardware Busters, 10 out.](https://hwbusters.com/news/rtx-5090-reportedly-loses-its-gb202-supply-as-nvidia-steers-the-die-to-rtx-pro-cards/), [Tom’s Hardware, 17 out.](https://www.tomshardware.com/pc-components/gpus/nvidia-reportedly-insists-the-rtx-5090-isnt-dead-despite-severe-shortages-and-removed-listings-at-multiple-retailers-flagship-gpu-is-missing-from-nvidias-store-and-commands-usd8-500-on-amazon) e [TechRadar, 17 out.](https://www.techradar.com/computing/gpu/are-we-seeing-the-first-signs-of-nvidia-abandoning-pc-gamers-as-the-rtx-5090-seemingly-disappears-from-shelves-im-getting-more-worried-about-geforce-gpus).

## Projeção exploratória para 4 matérias grandes + 6 pequenas

A simulação da Issue representa dez matérias (uma capa, três grandes e seis pequenas). A execução histórica da v1.0.0 usou seis etapas por matéria, o equivalente a 60 chamadas. Na v1.2.0, o fluxo usa cinco chamadas quando a revisão inicial não pede correção (pass ou hold) e oito quando responde revise; dez matérias implicariam 50–80 chamadas conforme os resultados. Apenas a amostra histórica foi medida; não há amostras long/brief nem médias por categoria.

Para tornar a incerteza visível sem fingir que existe uma média, a tabela abaixo aplica fatores de sensibilidade explícitos ao custo total observado desta amostra técnica cover (39.319 tokens) para cada uma das dez matérias. Os fatores de 0,5×, 1× e 2× são extrapolações ilustrativas, não resultados medidos, média de matérias prontas, quota disponível ou distribuição estatística.

| Cenário de sensibilidade | Hipótese por matéria | Tokens para 10 matérias | Chamadas de inferência |
|---|---:|---:|---:|
| Otimista | 0,5 × a amostra técnica observada por matéria | 196.595 | 50–80 |
| Central de referência | 1 × a amostra técnica observada por matéria | 393.190 | 50–80 |
| Conservador | 2 × a amostra técnica observada por matéria | 786.380 | 50–80 |

Esses valores não são previsão de consumo do Plus nem cenário de capacidade: misturam tamanhos diferentes usando uma amostra técnica como unidade e não incluem chamadas de catálogo, uso pessoal, revisão humana ou tempo de pesquisa. A franquia restante e a data de renovação não são expostas pelas respostas SIWC observadas; não há base para converter tokens em percentual ou declarar que o calendário hipotético de 21 dias de produção mais quatro de fechamento cabe no plano. Não fiz novas chamadas para amostras grande e pequena depois dos 39.319 tokens da amostra.

## Alterações de engenharia

- `siwc probe` agora exige `--model` e `--reasoning-effort`; o executor valida catálogo, resposta do modelo e esforço retornados, sem seleção automática nem fallback.
- `editorial run --packet ... [--run-id ...] [--source-collection-duration-ms ...]` encadeia checkpoints SQLite versionados e retomáveis. A v1.2.0 usa revisão inicial, correção somente após `revise`, checagem factual final e revisão do texto corrigido; `hold` bloqueia sem correção. A revisão vigente carrega SHA-256 do headline, dek, corpo e IDs de fonte; alteração de texto invalida a revisão. Há uma rodada automática de correção; novo `revise` ou `hold` exige decisão humana.
- O executor editorial aceita apenas o modelo/esforço explicitamente aprovados para o experimento, valida pacote HTTPS, IDs de fontes, citações e saídas estruturadas, e fixa revisão humana e não publicação.
- A identidade usada na amostra real foi `internal-controlled-editorial-experiment@1.0.0`. A revisão `1.1.0` anterior à Issue #11 passou apenas por testes. A `1.2.0` acrescenta revisão vigente por hash e guardas de contexto/saída; foi validada somente em testes offline, sem nova inferência real.
- O preview SIWC documenta que `max_output_tokens` não é aceito. As faixas de palavras são metas no prompt e validações locais; não limitam com rigor o tamanho gerado no provedor.

## Correções da Issue #11: C-002 a C-004

**C-002: revisão vigente:** a saída distingue `execution_status=completed` de `editorial_status`. `hold` para antes da correção; `revise` inicia uma rodada, checagem final e revisão do texto corrigido. Cada revisão registra hash da revisão alvo. A mudança de texto invalida esse hash; um segundo pedido de revisão termina em `blocked_human_decision`. `pass` deixa `awaiting_human_approval`; não aprova editorialmente nem publica.

**C-003: amostra e medição:** a execução histórica de seis etapas, 578 palavras e status `revise` está classificada como amostra técnica, abaixo da meta e fora de qualquer média de capa pronta. A v1.0.0 e suas métricas originais foram preservadas; v1.1.0 e v1.2.0 não foram testadas em inferência real. O prompt atual consolida achados factuais e limita detalhes; o contexto de redação usa trechos de evidência atribuídos em vez de repetir o pacote integral, e contextos de checagem/revisão mantêm evidências. Uma consulta de catálogo por execução é cronometrada; preparação do pacote e coleta manual ficam medidas em campos separados. Metas de palavras não autorizam preencher com texto sem fonte.

**C-004: integridade editorial:** a amostra Markdown recebeu nota explícita de normalização para os caracteres substitutos do cabeçalho e separadores das fontes; seu corpo e suas afirmações não foram reescritos. O teste verifica UTF-8 estrito, citações no conjunto S1–S6 e a preservação do mesmo conjunto no pacote/lista de fontes.

As correções C-002 a C-004 e seus testes nesta entrega são offline. Não houve nova chamada SIWC nem alteração dos JSONs históricos de métricas ou do pacote de fontes.

## Autenticação privada hospedada e operação futura

O login e a resposta sintética demonstram que esta conta/cliente local obteve autorização e completou chamadas SIWC em 2026-10-19. Isso não comprova elegibilidade de uma aplicação privada hospedada. O repositório é público, mas não contém arquivo `LICENSE`; visibilidade pública, sem licença, não confirma enquadramento open source. A [documentação SIWC](https://developers.openai.com/siwc/quickstart) restringe o uso do plano por apps privados a clientes selecionados e o [guia de VMs self-hosted](https://developers.openai.com/siwc/token-sharing-open-source/self-hosted-vms) descreve apps open source. A elegibilidade desta aplicação privada permanece **não confirmada**; não transferir a sessão Windows nem ativar inferência remota antes de confirmação oficial apropriada.

A arquitetura continua preparada para uma futura execução contínua em Debian 12 independente do Windows: worker único sob systemd, usuário sem privilégios, SQLite em disco local dentro de `/var/lib/revista-gamer`, diretório de dados privado, sem porta de entrada e reinício em falha, conforme o [exemplo da unidade systemd](../../deploy/systemd/revista-gamer-orchestrator.service.example). Para migrar a uma VPS: validar primeiro elegibilidade SIWC remota; instalar Python/venv e diretórios com permissões restritas; autenticar novamente no próprio host se permitido; preservar SQLite e backups em disco local; configurar monitoramento, relógio e restauração; manter agendas desativadas até decisão operacional separada. Não copiar DPAPI do Windows. A unidade não foi instalada, habilitada ou testada em Debian/VPS nesta entrega.

## Segurança e limites

Não foi usada API paga, `OPENAI_API_KEY`, cookie, token extraído de sessão privada ou credencial de navegador. Nenhum gasto de API foi feito. O login SIWC foi consentido pelo diretor; credenciais existentes permaneceram no armazenamento local protegido. A execução usou `store=false`, não acessou conversas do ChatGPT, não publicou e não ativou agendas.

## Validação automatizada

- `py -3.11 -m unittest discover -s motor_editorial/tests -v`: **69 aprovados; 1 ignorado por ausência de PyJWT[crypto] (70 executados)** em Windows 11, Python 3.11.9.
- `py -3.11 -m compileall -q motor_editorial`: passou.
- `git diff --check`: passou; apenas avisos informativos do Git sobre normalização LF/CRLF nos arquivos alterados.
- A cadeia simulada continua coberta por teste sem rede; a retomada do ensaio usa checkpoints/idempotência e não repete as seis chamadas concluídas.
- Os testes novos cobrem exigência de esforço/modelo, validação da resposta, bloqueio de fallback, limites de listas, citações, checkpoints, identidade do perfil e retomada sem repetir etapas concluídas.
