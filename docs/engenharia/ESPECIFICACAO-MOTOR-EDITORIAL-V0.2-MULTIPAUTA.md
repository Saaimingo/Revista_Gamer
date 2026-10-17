# Revista Gamer — Especificação de engenharia ENG-MOTOR-002
## Motor Editorial v0.2 — multipauta e composição de edição

**Status:** ordem técnica de implementação autorizada para protótipo offline, não para produção/publicação.  
**Baseline:** `main`, Motor v0.1 aceito e integrado pelos PRs [#3](https://github.com/Saaimingo/Revista_Gamer/pull/3) e [#4](https://github.com/Saaimingo/Revista_Gamer/pull/4).  
**Responsabilidades:** fundador = arquitetura e critérios; Codex = construção, testes e propostas de correção de inviabilidade; diretor = visão, escopo e aprovação de mudanças materiais.

## 1. Objetivo

Evoluir o Motor Editorial de uma demonstração fixa de **uma pauta por edição** para um sistema local capaz de administrar **várias pautas independentes em diferentes etapas** e compor **uma edição com múltiplas matérias elegíveis**, sem antecipar publicação, IA real ou coleta externa.

O requisito central não é somente aumentar um contador: é provar a **independência operacional por pauta**. Uma pauta com revisão reprovada, falha temporária ou direito de mídia pendente não deve impedir o avanço de outras; ao mesmo tempo, nenhuma edição pode ser marcada como pronta se faltarem entregas obrigatórias.

## 2. Restrições herdadas e não negociáveis

- O projeto continua um **único aplicativo Python local**, com SQLite, arquivos de prévia e painel limitado a `127.0.0.1`, sem dependências pagas nem serviços externos.
- Manter código e dados do teste separáveis; dados inéditos, credenciais e mídias de terceiros não entram no repositório público.
- Não integrar LLMs, APIs, feeds reais, pesquisas externas, relógio de coleta, agentes, redes sociais, publicidade, produção de edição real, hospedagem ou mecanismos de publicação.
- Preservar a máquina de estados, auditoria, limites de retentativa, revisão da **versão atual**, regra de direitos por **modalidade de uso** e confirmação humana da v0.1.
- Preservar capacidade de abrir bancos da v0.1, migrando com segurança caso o esquema mude; não destruir nem reescrever dados operacionais sem trilha.
- Respeitar os demais setores: personas, identidade visual e regras editoriais ainda serão aprovadas em suas áreas. Os templates e textos desta versão são apenas de simulação.

## 3. Comportamentos funcionais obrigatórios

### 3.1 Várias pautas, identidades e pacotes

- Entrada local de pelo menos **três pautas fictícias independentes**, com fontes e mídias simuladas próprias. A fixture antiga da v0.1 deve continuar executável ou possuir modo de compatibilidade explicitamente testado.
- Identificadores estáveis que não colidam entre pautas, entre edições nem entre execuções; revisão, apuração, auditoria, direitos e tentativas ligados à pauta correta.
- Cada pauta possui etapa, status, resultado, bloqueios e histórico próprios. Uma falha em uma pauta **não deve cancelar as demais**.
- O mecanismo de triagem e desduplicação preserva a proveniência; item repetido não origina matéria extra.
- O fluxo de revisão e correção continua real na máquina de estados; a segunda reprovação pode gerar intervenção humana **apenas para aquela pauta**, sem transformar todo o lote em falha terminal.

### 3.2 Execução, falha e retomada

- Executar/retomar uma pauta individual e, quando solicitado, percorrer as pautas disponíveis; política de retry por etapa/pauta com limite finito.
- Salvar transições atomicamente e recuperar após reinicialização; etapas completas não são repetidas por efeito de retomar outra pauta.
- Evitar dependência de sequência fixa `draft-v1/review-v1/correction-v2` em IDs globais da demonstração; abstrair o mínimo para várias pautas mantendo o limite editorial de correções do protótipo.
- Tornar explícito no painel e no CLI qual pauta está pronta, pendente, em falha recuperável, bloqueada para intervenção ou aguardando ação humana.
- Chamadas concorrentes ao painel não podem criar edições duplicadas ou aprovar estados parcialmente escritos. SQLite pode continuar com execução efetivamente serializada; não exige workers paralelos.

### 3.3 Composição da edição

- Uma edição tem **identidade própria**, conjunto ordenado de pautas participantes e status: em preparação, aguardando pendências/intervenção, pronta para aprovação interna, ou aprovada internamente.
- Cada matéria incluída precisa possuir revisão válida da **versão corrente**, decisões de mídia compatíveis com `editorial_preview`, texto e fontes rastreáveis. Arquivo sem permissão jamais é incorporado. Ativo opcional pendente é omitido; obrigatório com placeholder só quando a política da simulação permitir.
- Definir membros da edição explicitamente (na fixture/entrada de teste). O montador não pode ignorar silenciosamente uma pauta incompleta e apresentar a edição como finalizada.
- Pauta bloqueada deve manter a edição em preparação/pendente **sem impedir que outras matérias sejam processadas e inspecionadas**.
- É permitido excluir uma pauta da edição **somente por ação humana explícita e auditada**, preservando a pauta e o motivo; não excluir automaticamente em razão de erro. Pode-se implementar essa ação apenas por CLI se o painel ficar excessivamente complexo, mas ela deve existir e ser testável.
- A prévia HTML deverá reunir várias reportagens em ordem, distinguíveis por título/identificador, fontes, versões e placeholders de mídia. É uma **prévia interna**, não o leitor final com flipbook.
- Se uma matéria aprovada mudar de revisão, ou a permissão de mídia usada na prévia for revogada, a composição/prévia e a autorização humana anterior deverão ser **invalidadas ou revalidadas com segurança**, exigindo nova ação humana quando necessário; nunca continuar usando aprovação antiga.
- Aprovação humana interna somente quando **todos os membros ativos** estão elegíveis e a prévia corresponde ao conteúdo/decisões atuais. Nenhuma aprovação implícita nem publicação externa.

### 3.4 Painel e CLI

- Mostrar fila de pautas com estados independentes, detalhes e problemas por pauta, composição/pendências de uma edição, prévia multipauta e aprovação interna.
- Ações básicas locais para importar/iniciar cenário, executar/retomar, consultar pautas/edições e aprovar quando elegível. A exclusão humana auditada pode ser pelo CLI.
- Interface limpa e funcional, sem antecipar a identidade visual aprovada do Bloco 03; bind apenas loopback, sem autenticação pública, sem novas rotas de publicação.

## 4. Estrutura e migração

- Ajustar esquema SQLite de forma incremental, com versão `user_version` e migração verificável a partir do esquema v2 da v0.1.
- Separar conceitualmente **batch/execução**, **pauta**, **participação na edição** e **edição**. Manter relações consistentes e limites de unicidade no escopo correto.
- Não introduzir registros de auditoria genéricos sem referência a entidade; acompanhar responsável, data e transição.
- Não deixar ações externas ou gravações de arquivo mal-sucedidas serem tratadas como transições concluídas; manter consistência e reparabilidade.

## 5. Fixtures e testes de aceite

Manter os **11 testes da v0.1** passando (adaptados somente quando comportamento foi legitimamente generalizado). Adicionar pelo menos estes cenários:

1. **Três pautas independentes** entram no sistema: uma progride normalmente; outra tem reprovação v2 e intervenção por pauta; terceira sofre falha técnica transitória e depois retoma.
2. Executar as duas pautas saudáveis não fica impedido porque a segunda pauta está bloqueada.
3. A edição permanece **não pronta** enquanto algum membro obrigatório está bloqueado, sem ocultar a matéria problemática.
4. Resolver o bloqueio de uma pauta por caminho controlado ou **excluí-la mediante decisão humana auditável** permite que a edição avance, mas nunca oculta que a exclusão ocorreu.
5. Edição com pelo menos **duas matérias distintas** efetivamente renderizadas em HTML, em ordem definida, com fontes e direitos individualizados.
6. Uma mídia permitida para outra modalidade, ou revogada depois da composição, não aparece como ativo utilizável; prévia e aprovação reavaliadas.
7. Revisão nova invalida aprovação antiga da matéria e impede concluir edição usando revisão desatualizada.
8. Reexecutar/importar o mesmo lote não cria pautas, revisões nem edições duplicadas.
9. Reiniciar processo preserva estados distintos e permite retomar só a pauta falha sem refazer pautas concluídas.
10. A aprovação interna exige ação humana explícita, só sucede quando todos os membros restantes estão aptos; GET/POST `/publish` continuam **404**.
11. Migração de banco v2 existente preserva dados e executa sem corromper a demo anterior.
12. Testar duas chamadas sucessivas ou simultâneas simples ao painel sem duplicar a edição ou enfileirar trabalho inconsistente.

Documentar comandos e executar testes no ambiente disponível. Na validação final, repetir em Windows 11 local como na CODEX-001, sem chamar Linux de Windows. Se não houver Windows na sessão, isso **não bloqueia a construção**, mas deve ser apontado como aceite nativo pendente.

## 6. Definição de pronto

Entrega não é apenas alteração de código: exige **fluxo multipauta executável**, cenário demonstrável com ao menos três pautas, no mínimo duas reportagens na prévia final, bloqueio independente por pauta, composição correta, aprovação deliberada, persistência/migração e testes automatizados observados.

Incluir:
- Código Python + alterações SQLite/painel/CLI/fixtures;
- README do Motor com comandos da v0.2, comportamento da v0.1 e limitações;
- Relatório de implantação/testes da v0.2 no setor de Engenharia;
- Branch **nova, criada a partir da `main` atualizada**; PR para revisão, **sem merge automático**;
- Evidências dos cenários e limitações reais.

## 7. Autonomia e interrupções

O Codex tem autorização para escrever, testar, corrigir, refatorar e migrar o protótipo offline **dentro do escopo desta v0.2**. Não perguntar ao diretor detalhes técnicos triviais. Encontrando restrição relevante, escolher a alternativa segura e mínima, documentar; interromper somente por necessidade de custos, acesso fora do repositório, publicação, direitos incertos, credenciais ou alteração material de escopo.

**Não construir v0.3 nem ligar fontes reais/LLMs nesta ordem.**

Referências: `docs/governanca/BIBLIA-DO-PROJETO.md`, `AGENTS.md`, `docs/governanca/DECISOES.md`, `docs/engenharia/README.md`, `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md`, `docs/engenharia/RELATORIO-IMPLANTACAO-MOTOR-V0.1.md`.
