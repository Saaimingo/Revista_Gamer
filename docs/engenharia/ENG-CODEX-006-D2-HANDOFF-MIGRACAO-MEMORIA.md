# ENG-CODEX-006 — D2: handoff de migração mínima da memória editorial

- **Setor responsável:** Engenharia e Codex
- **Identificador do artefato:** ENG-CODEX-006-D2
- **Versão:** v0.1
- **Status:** em_revisao
- **Data de atualização:** 2026-10-24 18:16 America/Sao_Paulo
- **Dependências:** Issue [#23](https://github.com/Saaimingo/Revista_Gamer/issues/23), comentário [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359); Issue [#20](https://github.com/Saaimingo/Revista_Gamer/issues/20), decisão [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182); [D0](ENG-CODEX-006-D0-MAPA-SCHEMA-MEMORIA.md); [D1](ENG-CODEX-006-D1-ESTADOS-PROVENIENCIA.md)
- **Aprovador:** Direção; revisão e missão própria pendentes.

## Objetivo e limites

Entregar apenas o mapa de migração mínima e critérios de aceite para uma futura missão de Memória Editorial, priorizada pela direção antes da primeira matéria real. Esta entrega encerra D0–D2 como documentação para o handoff ao Fundador 2; não inicia a missão futura.

Não executar nem codificar migração, memória, busca de continuidade, skills, agentes ou conexões sociais. Não alterar o banco runtime local. Não inferir autorização de implementação a partir da decisão conceitual da Issue #20 ou da PR #21. O schema físico, nomes finais de estados, política legal/de acesso e tratamento de dados ambíguos continuam para aprovação em missão própria.

## Autoridade e estado real

A decisão da direção [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182) confirma como princípio a recuperação interna de matérias `approved_internally`, inclusive inéditas, quando status e proveniência evitam confusão com publicação efetiva. Ela prioriza memória antes da primeira matéria/edição real e declara que nomes e esquema são proposta a validar, sem autorizar implementação, merge, integração social, agentes novos ou gastos. Skills evolutivas ficam para fase posterior.

A PR [#21](https://github.com/Saaimingo/Revista_Gamer/pull/21) segue aberta em rascunho e se identifica como proposta não aprovada/executável. A Issue #20 segue aberta. Portanto este mapa é recomendação técnica condicionada; cada etapa abaixo precisa de uma ordem/aceite futuro antes de alterar bancos ou código.

## Base observada em D0

- `Store` no código atual cria schema v5 com 17 tabelas e não tem entidade de memória/persona/versão DNA/jogo/franquia/recibo de publicação.
- O arquivo local ignorado `motor_editorial/runtime/motor.sqlite3` foi consultado apenas em `mode=ro`: `PRAGMA user_version=4`, 17 tabelas e ausência de `agent_tasks.lease_owner` e `agent_tasks.lease_generation`. Nenhuma linha de conteúdo foi consultada; nenhuma migração foi executada.
- O v5 contém matérias, revisões, fontes, relações matéria-fonte, revisões editoriais, edições e eventos de auditoria. `article_revisions.author_role` não fornece uma identidade persona/versionada; `published_at` em `source_items` é data da fonte; aprovação interna não é prova de publicação externa.
- O runtime v4 precisa primeiro atravessar a migração já existente v4→v5 numa cópia controlada antes de qualquer futura migração de memória baseada no schema atual. Isso é dependência de sequência, não autorização para migrar agora.

Referência detalhada: [relatório D0](ENG-CODEX-006-D0-MAPA-SCHEMA-MEMORIA.md). Estados, proveniência, correções e cenário matéria→DLC: [relatório D1](ENG-CODEX-006-D1-ESTADOS-PROVENIENCIA.md).

## Mapa mínimo proposto para missão futura

O desenho abaixo descreve as informações que precisam existir e suas relações; não determina tabelas, colunas nem enumerações definitivas.

| Necessidade lógica | Relação mínima esperada | Regra de integridade |
| --- | --- | --- |
| Autoria recorrente | Revisão/atribuição editorial → persona estável + versão/hash do DNA. | Não deduzir persona de `author_role` nem duplicar a mesma matéria por persona. Identidade do autor não é `agent_tasks.profile_id` do executor. |
| Obra e continuidade | Matéria → jogo/franquia/tópico estável; matéria sucessora pode referenciar predecessora. | Não converter automaticamente `topic_key` em ID de jogo/franquia nem fundir matérias que só parecem relacionadas. |
| Evidência editorial | Matéria/revisão → fontes e itens com identificadores/datas; relação a afirmações pode ser avaliada. | Preservar relações existentes e datas da fonte; qualquer vínculo novo deve apontar a revisão relevante e fonte verificável. |
| Estado interno | Revisão/hash → resultado de revisão e aprovação interna (ator/instante), mantendo público/inédito separado. | `reviewed` e `approved_internally` não significam `published`; aprovação de uma revisão não aprova automaticamente a seguinte. |
| Publicação externa | Recibo → canal, referência externa confirmada, instante e revisão/hash publicado. | Só evidência externa confirmada autoriza `published`; preview, HTML, agenda, URL planejada, tentativa ou retorno ambíguo não contam. |
| Histórico | Correção, substituição e retirada → revisão/registro anterior e sucessor, motivo e ator/instante quando disponível. | Acrescentar a trilha; não apagar nem reescrever conteúdo ou recibos antigos. |
| Recuperação e acesso | Consulta → conteúdo + proveniência completa + status público + escopo autorizado. | Material aprovado e inédito pode aparecer apenas na preparação interna autorizada, com rótulo de inédito; rascunho/reprovado/retirado não entra na memória comum. |

### Sequência de migração a avaliar

1. **Pré-requisito v4→v5:** em futura missão autorizada, copiar o banco v4 e verificar hash/backup; executar a migração existente somente na cópia; comparar versão, integridade referencial e registros antes/depois. Testar restauração do backup sem sobrescrever o original. A execução no arquivo `motor_editorial/runtime/motor.sqlite3` fica fora desta ordem.
2. **Contrato da memória:** antes de criar DDL, aprovar a taxonomia, vínculos persona/DNA, jogo/franquia, evento externo, acesso, retenção e regra para dados legados ambíguos. A falta de qualquer decisão jurídica/de acesso fica como bloqueio de implementação, não é preenchida por padrão técnico.
3. **Migração futura v5→v6 (apenas hipótese de versão):** desenhar uma migração transacional, aditiva e reversível em cópia; acrescentar somente os vínculos/eventos mínimos aprovados, manter FKs para a matéria e revisão exatas e incrementar `user_version` após sucesso. A numeração v6 é ilustrativa, não aprovada.
4. **Backfill conservador:** manter todas as revisões, fontes, edições e auditoria; criar vínculos só quando os dados antigos identificarem a relação sem ambiguidade. `author_role` não vira `persona_id` por inferência. `topic_key` não vira jogo/franquia normalizados por inferência. Um status de artigo `approved` não gera recibo de publicação. Registros sem prova continuam não publicados/não confirmados, ou ficam pendentes para classificação explícita conforme o contrato aprovado.
5. **Validação e rollback:** rodar `foreign_key_check`, checar unicidade/contagens e amostras de cadeias de revisão em fixture; simular falha no meio da transação e restauração integral do backup. Uma versão futura de banco deve ser recusada sem mutação. Nenhum passo pode remover ou sobrescrever dados históricos.

## Critérios de aceite para a missão futura

Todos são requisitos propostos para uma ordem própria; nenhum foi executado por D2:

- A direção aprova a taxonomia, os campos/vínculos essenciais, o acesso ao inédito, retenção/base legal e o que conta como prova externa para cada canal; PR #21 deixa de ser a única fonte conceitual ou é substituída por decisão formal.
- Migração de fixture v4→v5 e depois da versão de memória aprovada preserva registros, chaves, relações e hashes; `foreign_key_check` fica limpo; rollback restaura bytes/hash do backup; falha e versão futura não deixam mutação parcial.
- Backfill nunca marca conteúdo como `published` sem recibo confirmado ligado à revisão/hash exatos; um recibo com hash errado ou ausente é rejeitado.
- Dados legados ambíguos não recebem persona, jogo/franquia, aprovação ou publicação por inferência; a classificação pendente é explícita e auditável.
- Consulta recupera matéria `approved_internally` ainda inédita para preparação interna e sempre retorna status/proveniência/escopo de acesso; nenhum caminho de preview ou resposta pública a descreve como já publicada.
- Rascunhos e revisões reprovadas ficam fora da consulta comum, com exceções apenas para auditoria/retificação controladas e sinalizadas.
- Correção cria novo hash/revisão e exige nova revisão/aprovação; substituição e retirada preservam a cadeia; recibos antigos permanecem associados ao conteúdo exato que foi publicado.
- Fixture offline demonstra continuidade matéria→DLC, isolamento de autoria/persona, ausência de duplicação física e nenhuma publicação/integração externa. Regressões, suíte completa, `compileall` e `git diff --check` são reportados com ambiente e contagens executadas.
- A execução é somente local/simulada, sem SIWC/Plus real, API paga, contas, permissões, rede social, terceiros, publicação, deploy ou compra de serviço.

## Custos, dependências e riscos conhecidos

- **Custo monetário conhecido:** nenhum serviço pago ou API foi proposto; a missão futura deve permanecer local até nova decisão. Não há estimativa de armazenamento, backup ou horas de revisão de migração, porque volume/retenção ainda não foram decididos.
- **Custo técnico esperado:** novas relações/índices e recibos aumentam o SQLite, as cópias de segurança, a validação e a manutenção de compatibilidade. Recuperação por texto/índices pode ser avaliada antes de qualquer serviço de busca vetorial; esta ordem não solicita nem assume serviço externo.
- **Dependência de dados:** o runtime local está um schema atrás do DDL atual. Será necessário backup/restauração testados e migração v4→v5 em cópia antes da futura extensão, sem escrever no arquivo existente nesta ordem.
- **Risco editorial:** conteúdo aprovado mas inédito pode vazar em chamada, resumo público ou contexto de outro canal se o estado e o acesso não acompanharem o conteúdo.
- **Risco de proveniência:** atribuir recibo a revisão incorreta, tratar aprovação como publicação, confundir data da fonte com data da revista, associar persona pelo texto livre ou unir jogos/franquias indevidamente.
- **Risco jurídico/privacidade:** retenção, base legal, direitos de fontes/trechos e escopo de acesso ao material inédito precisam de validação competente antes da implementação. Não classificar esse risco por conta própria.
- **Risco operacional:** reescrita de revisões antigas ou migração parcial pode destruir trilhas de correção e tornar impossível explicar qual versão foi revista ou publicada. A estratégia futura exige fixture, backup, transação, rollback e rejeição sem mutação de schemas desconhecidos.

## Bloqueios de decisão e escopo

Não bloqueiam este handoff documental, mas bloqueiam implementação futura até decisão explícita:

1. enumeração e semântica dos estados e eventos;
2. modelo de persona/DNA e autoria de posições;
3. normalização de jogo/franquia/tópico e regra para continuidade;
4. prova suficiente de publicação externa por canal e registro de correção/retirada pública;
5. papéis autorizados, uso de matéria inédita, retenção e base legal;
6. tratamento/revisão manual de registros legados sem identidade, publicação ou vínculo inequívocos.

Skills evolutivas, publicação em redes, conexões Meta e novos agentes/serviços permanecem fora da missão ENG-CODEX-006, conforme Issues #20 e #23.

## Validação e encerramento de D2

- Evidências consultadas: Issue #23 e diretriz [6378715359](https://github.com/Saaimingo/Revista_Gamer/issues/23#issuecomment-6378715359); decisão [6376215182](https://github.com/Saaimingo/Revista_Gamer/issues/20#issuecomment-6376215182); PR #21; relatórios D0 e D1; confirmação local, somente leitura, de runtime v4 e schema temporário v5.
- Esta unidade é documental. Nenhum teste de produto, migração, backfill, rollback ou execução real foi realizado. `git diff --cached --check` passou para o relatório e checkpoint staged.
- Não há mudança de código/schema nem alteração do runtime, chamada de rede, API paga, SIWC/Plus real, conta, publicação, deploy ou merge.
- D0, D1 e D2 são entregas documentais em revisão; o gate de aceite do Fundador 2 continua pendente. Esta missão termina com o handoff técnico, sem iniciar a implantação futura.
