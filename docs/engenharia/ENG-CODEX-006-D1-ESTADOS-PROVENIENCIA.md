# ENG-CODEX-006 — D1: estados e proveniência da memória editorial

- **Setor responsável:** Engenharia e Codex
- **Identificador do artefato:** ENG-CODEX-006-D1
- **Versão:** v0.1
- **Status:** em_revisao
- **Data de atualização:** 2026-10-24 18:13 America/Sao_Paulo
- **Dependências:** Issue [#23](https://github.com/Saaimingo/Revista_Gamer/issues/23), comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359); Issue [#20](https://github.com/Saaimingo/Revista_Gamer/issues/20), decisão [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182); [mapa D0](ENG-CODEX-006-D0-MAPA-SCHEMA-MEMORIA.md)
- **Aprovador:** Direção; revisão e aceite pendentes.

## Objetivo e limite

Registrar, como proposta documental, como uma futura memória editorial deve distinguir trabalho em andamento, revisão, aprovação interna ainda inédita e publicação externa comprovada; preservar correções e retiradas; e levar a proveniência junto com qualquer recuperação. D1 também descreve um ensaio fictício matéria→DLC que não publica conteúdo.

Este documento não aprova nomes finais de estados, tabelas, campos, política de acesso ou prova legal de publicação. Não altera o SQLite, não migra o runtime v4, não implementa memória, skills, agentes ou conexões sociais e não faz chamadas externas. A Issue #20 continua aberta; a PR #21 continua uma proposta em rascunho.

## Estados e fatos que não devem ser confundidos

A decisão [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182) pede estados independentes e explícitos. A tabela abaixo organiza o significado esperado; codificação e taxonomia continuam para validação da direção.

| Conceito proposto | Evidência exigida | Uso interno | Declaração pública permitida |
| --- | --- | --- | --- |
| Rascunho (`draft`) | Revisão de artigo identificada; ainda sem aprovação final. | Trabalho editorial, com sinalização de rascunho e acesso restrito. Não entra como memória editorial aprovada. | Nenhuma alegação de revisão, aprovação ou publicação. |
| Revisado (`reviewed`) | Resultado de revisão ligado à revisão exata do artigo e ao hash correspondente. | Consulta apenas para revisão, auditoria ou continuidade interna permitida. Revisão não equivale à aprovação final. | Não declarar aprovado ou publicado. |
| Aprovado internamente (`approved_internally`) | Ator e instante da aprovação interna vinculados à revisão/hash aprovados. | Pode fundamentar uma pauta futura interna se o resultado da consulta continuar rotulado como inédito. | Não chamar de publicado nem revelar detalhes antes de autorização específica. |
| Publicado (`published`) | Evento externo confirmado, com canal, identificador/link confirmado e vínculo à revisão/hash efetivamente publicada. | Pode constar como publicação anterior depois que a prova for registrada e validada. | Só então pode ser descrito como publicado; aprovação, preview, HTML, agenda, URL planejada ou tentativa de envio não bastam. |

`draft`, `reviewed`, `approved_internally` e `published` são rótulos conceituais requeridos pela decisão, não enumeração aprovada. “Inédito” é uma condição pública que precisa acompanhar o estado interno aprovado, mesmo que seja armazenada em campo próprio, evento ou resultado derivado. A forma de persistir esse eixo ainda não foi decidida.

## Prova de publicação e proveniência da consulta

Uma recuperação futura deve devolver o contexto junto com o conteúdo, para que nenhum consumidor precise adivinhar o que o texto significa. O conjunto mínimo proposto é:

- identidade estável da matéria e da revisão recuperada;
- autor/persona, versão do DNA e hash do perfil associados àquela autoria;
- hash do conteúdo recuperado e edição, quando houver;
- fontes associadas, seus identificadores e datas relevantes; `published_at` de uma fonte é a data da fonte, não a data de publicação da Revista Gamer;
- resultado e instante da revisão, ator/instante da aprovação interna e status editorial;
- status público separado, explícito como inédito/não confirmado até existir prova externa;
- cadeia de correções, substituições e retiradas, com motivo, ator/instante e ligação entre as revisões;
- escopo de acesso autorizado e indicação de que a recuperação é para preparação interna;
- recibo externo, se existente, que identifique o canal, referência confirmada, instante e hash/revisão publicados.

A ausência de recibo significa que o sistema não pode afirmar `published`; uma falha ou resposta ambígua de envio também não muda essa classificação. O mecanismo exato para validar recibos, retenção e força probatória fica para especificação própria e decisão competente.

## Correção, substituição e retirada

Estas ações devem preservar a cadeia histórica; não devem apagar nem reescrever a revisão anterior.

| Ação | Tratamento conceitual | Consequência para recuperação |
| --- | --- | --- |
| Correção | Criar nova revisão com novo hash, registrar a relação com a revisão corrigida e repetir os gates editoriais aplicáveis. | Exibir a revisão vigente e apontar a anterior como corrigida; uma prova de publicação antiga permanece ligada ao hash antigo. |
| Substituição | Relacionar a matéria ou versão anterior à sucessora, com motivo e instante. | Consultas normais priorizam a sucessora e preservam a predecessora para auditoria e para entender a continuidade. |
| Retirada | Registrar uma decisão explícita, ator, instante e motivo; conservar o histórico. | Impedir que a matéria retirada apareça como referência atual/publicável; retorná-la apenas em contextos autorizados de auditoria ou retificação, com aviso. |

Os termos `corrected`, `superseded` e `withdrawn` são possibilidades de estado/evento citadas pela direção; não se escolhe aqui se serão colunas, eventos ou relações. Uma correção posterior exige reavaliação e aprovação da nova revisão; publicação da versão corrigida precisa de evidência externa ligada ao novo hash.

## Acesso e fronteira de publicação

- Conteúdo `approved_internally` pode ser consultado por funções editoriais autorizadas para preparar pauta futura, desde que resultado, contexto e citações o marquem como **inédito**.
- Rascunhos, revisões reprovadas e material retirado não entram na recuperação editorial normal. Uso para auditoria ou retificação deve ser explícito, restrito e sinalizado.
- Preview, StoryPackage, LayoutPlan, gate simulado e aprovação interna permanecem artefatos internos. Nenhum deles pode alimentar saída pública como evidência de publicação.
- O D0 constatou que o schema v5 não apresenta camada de autorização por usuário/persona nem recibo de publicação. O runtime local permanece v4 e foi consultado somente em leitura. O desenho de papéis, acesso, retenção e base legal depende de decisão e especificação futuras.
- Não duplicar fisicamente uma matéria por cronista: autoria e posições devem apontar para registros/revisões e versões de persona, mantendo a identidade editorial separada do perfil executor do job.

## Ensaio offline matéria→DLC

Fixture futura, somente sintética e local:

1. Registrar uma matéria fictícia sobre o lançamento de um jogo, com fontes sintéticas, revisão/hash e autoria de uma persona fictícia versionada.
2. Registrar aprovação interna da revisão 1, mas nenhum recibo externo. A busca interna para uma pauta sobre DLC retorna o contexto com estado **aprovado internamente, inédito** e suas fontes/datas.
3. Preparar uma matéria derivada sobre o DLC, mantendo relação de continuidade com a matéria anterior sem copiá-la como um segundo exemplar de autoria. A saída da fixture informa que a referência anterior não foi publicada e não contém chamada pública que afirme o contrário.
4. Simular a correção da matéria inicial: criar revisão 2 com novo hash, manter a revisão 1 e suas relações, reexecutar revisão/aprovação da revisão 2 e confirmar que resultados antigos não são associados automaticamente ao novo hash.
5. Apenas em uma variante completamente fictícia de teste, anexar ao artigo a confirmação externa simulada para a revisão exata. A consulta pode então classificar aquela revisão como publicada. A variante não acessa plataforma, conta ou serviço real.
6. Se não houver confirmação, se o envio falhar ou se o recibo não identificar a revisão, a classificação continua inédita/não confirmada. Se houver retirada, a consulta normal deixa de oferecer a matéria como memória vigente e mantém a trilha para auditoria autorizada.

## Critérios propostos para a missão futura

- Distinguir revisão, aprovação interna e publicação externa por evidências separadas; nenhuma etapa interna ou URL planejada libera `published`.
- Permitir recuperação interna da matéria aprovada e inédita sem apresentá-la como conteúdo já publicado.
- Vincular cada resultado de revisão, aprovação e recibo à identidade e hash exatos da revisão pertinente.
- Preservar as revisões anteriores e explicar correção, substituição ou retirada sem apagar a proveniência.
- Retornar fontes/datas, edição, autoria/persona + versão do DNA e escopo de acesso no resultado recuperado.
- Manter rascunhos/reprovados/retirados fora da recuperação editorial comum; permitir exceção somente com finalidade e sinalização de auditoria/retificação.
- Provar a continuidade fictícia matéria→DLC e o bloqueio de alegação pública de publicação em fixture offline, sem SIWC/Plus, API paga, redes, contas ou publicação real.
- Manter uma única matéria com vínculos de autoria/posição, sem cloná-la por persona.

## Decisões e riscos reservados

Continuam pendentes da direção e de missão própria: nomes finais dos estados; modelo relacional para persona e versão de DNA, jogo/franquia/tema e recibo externo; padrão de comprovação aceito para cada canal; política de papéis e acesso ao inédito; retenção e base legal; escopo de uso de rascunho/rejeitado/retirado para retificação; e revisão das fontes/direitos de conteúdo real. Esses pontos não impedem fechar o mapa documental D1, mas impedem transformar esta proposta em schema ou código aprovado.

Riscos conhecidos: exposição acidental de matéria inédita; atribuição de uma publicação ao hash errado após correção; confusão entre datas das fontes e data da revista; perda da relação entre sucessora e texto original; excesso de retenção ou acesso sem justificativa; e interpretação de uma falha/aceite ambíguo de plataforma como publicação efetiva.

## Evidência e limitações desta unidade

- Referência de autoridade reconsultada: Issue #20, comentário [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182). Ele confirma o princípio de recuperar internamente matéria aprovada ainda inédita, exige estados separados e proveniência, define publicação apenas após evento externo confirmado e deixa a implementação para uma missão posterior.
- Base técnica: [relatório D0](ENG-CODEX-006-D0-MAPA-SCHEMA-MEMORIA.md), que mapeia schema v5/17 tabelas e a diferença do runtime v4 sem consultar linhas de conteúdo ou executar migração.
- Validação desta unidade: revisão documental contra a decisão citada e D0; `git diff --cached --check` passou para o relatório e checkpoint staged. Nenhum teste de produto, migração ou integração foi executado para D1, porque o escopo desta unidade é somente documental.
- Sem mudança de schema/código, chamada de rede, API paga, SIWC/Plus real, conta, publicação ou deploy.

## Próximo passo

D2: produzir apenas o mapa de migração mínima e os critérios de aceite para missão posterior, incluindo dependência de migrar o runtime v4→v5 antes de uma futura extensão; listar custos/riscos conhecidos, checkpoint final e resumo na Issue #23. Continuar sem codificar memória, skills ou integração social.
