# Revista Gamer — Especificação de construção do Motor Editorial v0.1

**Documento:** ENG-MOTOR-001  
**Status:** aprovado para IMPLEMENTAÇÃO DO PROTÓTIPO LOCAL, sujeito a testes; não aprovado para produção/publicação  
**Responsáveis:** chat fundador (arquitetura), Codex (engenharia, implementação e validação), diretor humano (decisões de produto e autorização de operação)  
**Data-base:** 2026-10-15  
**Prioridade:** primeiro sistema executável da Revista Gamer  
**Tipo:** protótipo mecânico vertical, offline, com dados SIMULADOS.

## 0. Finalidade e autoridade

O diretor determinou que a arquitetura dos sistemas ficará a cargo do chat fundador; o Codex atuará como **construtor e verificador técnico**, com autonomia para resolver problemas normais de engenharia, implementar, testar, corrigir e justificar melhorias sem ficar devolvendo escolhas técnicas triviais ao diretor. Se uma exigência for tecnicamente inviável ou criar riscos materiais, o Codex deve explicar a restrição e propor a menor alternativa funcional, documentando o impacto. Alterações de objetivo, orçamento, licenças, segurança, publicação ou direitos exigem novo aval.

**Esta especificação é a ordem arquitetural suficiente para construir v0.1.** Não reabrir o diagnóstico inicial nem pedir ao diretor decisões sobre detalhes de framework, nome de classes, rotas, nomes de tabelas ou biblioteca de testes. Escolher e justificar.

O repositório `Saaimingo/Revista_Gamer` é o livro de regras e o espaço de código compartilhado. Os seis chats do Project são **setores de CONCEPÇÃO**, não agentes de execução. Não há integração automática entre chats. A implementação usará dados fictícios e tarefas simuladas, sem antecipar especificações de conteúdo/personas/mídia de outros blocos.

## 1. Produto a entregar nesta missão

Entregar **UM aplicativo local funcional** denominado **Motor Editorial v0.1**, capaz de:
1. Receber uma pequena coleção de itens de notícia SIMULADOS, com identificação/origem, pelo CLI ou ação de teste local;
2. Normalizar, registrar e desduplicar esses itens;
3. Criar e acompanhar pautas selecionadas;
4. Mover as pautas num fluxo controlado de etapas, com persistência de entradas/saídas e registro auditável;
5. Executar investigação, redação, revisão, correção, verificação de mídia e montagem por **adaptadores simulados determinísticos**, sem IA real;
6. Impedir que falhas, direitos pendentes ou revisão rejeitada avancem indevidamente;
7. Produzir uma **prévia HTML interna claramente marcada "SIMULAÇÃO — NÃO PUBLICAR"** usando texto ficcional, sem conteúdos de terceiros;
8. Oferecer interface/painel local simples para mostrar filas, estados, histórico, prévia e **aprovação HUMANA INTERNA**;
9. Retomar execução interrompida sem duplicar resultados ou corromper registros;
10. Provar esses comportamentos com testes repetíveis e documentados.

Esta edição demonstrativa **não equivale à primeira revista-piloto real**; servirá apenas para validar a mecânica. Não criar site público nem disponibilizar um botão, endpoint ou comando de publicação.

## 2. Tecnologia e ambiente recomendados

- **Python 3.11+**, `sqlite3` com banco local e migrações simples, arquivos no disco para conteúdo/saída, HTML/CSS/JS leve para painel de administração e prévia. Dependências mínimas: biblioteca padrão sempre que prática; bibliotecas leves são permitidas se justificadas, sem custos.
- Deve executar em **Windows 11 para desenvolvimento** e preservar portabilidade para **Debian 12** sem mudanças de arquitetura. Não usar caminhos absolutos de máquina do fundador ou dependências exclusivas de Windows.
- Escopo inicial: **um processo local**, sem workers distribuídos, broker, cluster, Kubernetes, n8n, Airflow, Redis, servidor remoto ou SaaS.
- Painel deve escutar **apenas 127.0.0.1** por padrão; não abrir portas para internet, LAN ou rede pública. Se escolher servidor HTTP, não implementar nenhuma rota para deploy/publicação.
- `runtime/`, `data/`, `*.db`, `*.sqlite*`, saídas e logs com dados operacionais devem ser ignorados pelo Git, exceto fixtures ficcionais expressamente aprovadas; não incluir credenciais/tokens.
- GitHub mantém **código e especificações**. SQLite armazena **estado da execução**. As pastas locais armazenam **arquivos das execuções**. Não usar Issues do GitHub como fila de produção.
- Se houver limitação real de ambiente do Codex Cloud (sem navegador/UI/OS), entregar testes automatizados de painel e instrução de validação local, sem afirmar que o recurso foi testado num sistema onde não foi.

## 3. Arquitetura lógica: núcleo orquestrador + executores substituíveis

### Componentes obrigatórios

**A. Entrada/normalização:** importa fixtures, atribui identificador de fonte e título, canoniza identificadores de origem/URL quando existirem, gera chave determinística para duplicatas. A entrada do primeiro teste é totalmente fictícia.

**B. Máquina de estados:** única responsável por transições válidas, dependências e bloqueios. Agentes/adaptadores **nunca escrevem diretamente "etapa concluída" para pular o controle**.

**C. Executor de etapas:** cada etapa recebe contexto versionado, devolve resultado estruturado com status, artefatos e problemas. Implementação inicial usa adaptadores locais previsíveis; interfaces permitirão troca por pesquisa real e modelos de IA futuramente SEM reescrever o orquestrador. Não há exigência de chamadas LLM agora.

**D. Persistência e auditoria:** banco SQLite transacional + arquivos locais com referências. Histórico append-only de transições e execuções; revisões de texto imutáveis/versionadas. Controle de idempotência e recuperação.

**E. Política de mídia:** utiliza registro fictício de ativos com `permitido`, `pendente` ou `bloqueado` para uso editorial de prévia. Nunca converte `pendente` em `permitido` por inferência. Placeholder interno é permitido, desde que identificado e sem utilizar o ativo problemático.

**F. Montador de prévia:** converte saída simulada revisada num arquivo HTML estático **interno**, com sinalização explícita de simulação, identificação da matéria, lista de fontes e status dos ativos. Sem incorporar anúncios, links afiliados ou mídias externas no protótipo.

**G. Painel/CLI:** consulta filas, detalhes de matéria/edição, registros de erros, histórico e aprovações. Deve permitir reiniciar a simulação e repetir teste sem criar cópias acidentais.

### Interfaces de entrada e saída

Definir contratos claros, documentados e testados, ao menos para:
- `SourceItem`: id, identificador/URL-origem opcional, título, data, conteúdo resumido, hash de normalização, estado de deduplicação;
- `Story/Pauta`: id estável, pergunta editorial, vínculos com fontes, etapa atual, status e timestamps;
- `ResearchPackage`: id da pauta, fontes e referências, notas de apuração, afirmações simuladas e dúvidas;
- `ArticleRevision`: id da pauta, nº de versão, conteúdo, fontes associadas, autor-função, data e status de revisão;
- `ReviewResult`: revisão examinada, aprovada/reprovada, lista objetiva de problemas e destino da devolução;
- `MediaAssetDecision`: id do ativo, modalidade de uso, status da permissão, prova/referência e ação (usar, bloquear, placeholder);
- `Edition`: id estável, itens incluídos, versão, status de composição, prévia, aprovação interna;
- `ExecutionAttempt`: id, idempotency_key, tarefa/etapa, início/fim, resultado/falha, nº tentativas;
- `AuditEvent`: data, entidade, ação, responsável (sistema/adaptador/diretor), origem, antes/depois e referência a artefato.

Nomenclatura interna e schema ficam a critério do Codex, desde que os contratos sejam documentados, persistentes e cubram esses conceitos. Chave estrangeira e integridade referencial são obrigatórias no SQLite.

## 4. Fluxo funcional obrigatório v0.1

`entrada -> normalização/deduplicação -> triagem -> apuração -> redação (v1) -> revisão -> [correção (v2) -> nova revisão] -> direitos de mídia -> prévia -> aprovação humana interna -> arquivamento interno`

Estados negativos são de primeira classe:
- `duplicata`: o item já entrou; não gerar duas pautas;
- `bloqueado_por_revisao`: corrigir versão e revalidar; não prosseguir automaticamente;
- `bloqueado_por_direitos`: ativo impedido de uso, a pauta pode prosseguir com placeholder SOMENTE se a regra permitir; registrar motivo;
- `falha_tecnica_recuperavel`: retry limitado + rastreado;
- `falha_exige_intervencao`: limite excedido; nenhum loop infinito;
- `aguardando_aprovacao_humana`: sem passagem automática para `aprovado_internamente`.

Não basta exibir nomes de etapas: implementar **regras reais de transição**, armazenar resultados e recusar transição ilegal com erro explicativo. Nenhuma etapa que use revisão deve considerar aprovada uma **versão antiga** depois de correção. Alteração material requer revisão da nova versão.

A prévia interna e seu status não são publicação. A aprovação interna requer ação deliberada do diretor no painel/CLI e histórico auditável; nenhuma rotina de background aprova automaticamente. Nenhum botão/rota de "publicar" deve existir em v0.1.

## 5. Fixtures e cenários determinísticos

Criar uma franquia/jogo **inteiramente fictícios**, sem reproduzir personagens, nomes, logotipos, screenshots ou outros ativos protegidos. O conteúdo e as imagens devem ser placeholders originais neutros marcados como teste.

Testar, com fixtures explícitas:
1. Dois itens de notícia idênticos ou com mesma identidade de origem, resultando em **um item/pauta elegível**;
2. Triagem seleciona o item pertinente, descarta o irrelevante;
3. Pacote de investigação com referências a fontes fictícias;
4. Primeira versão da reportagem contendo afirmação simuladamente sem referência;
5. Revisão reprova com razão específica e devolve à correção;
6. Versão nova corrigida, aprovada por **outra passagem de revisão**;
7. Um ativo `pendente` é impedido de entrar na prévia; placeholder identificado o substitui; um ativo `permitido` de teste pode ser usado;
8. Uma falha técnica transitória interrompe etapa; retomada registra nova tentativa e não duplica efeitos;
9. Solicitação de transição inválida (pular revisão, aprovar antes da prévia) é recusada;
10. Após prévia aprovada para revisão humana, sistema aguarda intervenção explícita;
11. Diretor aprova **apenas internamente**, e o evento fica registrado no histórico;
12. Reiniciar aplicação mantém estado e informações coerentes.

Conjuntos de entrada, resultados esperados e comandos de teste documentados.

## 6. Experiência da interface mínima

Painel local funcional, não protótipo estático:
- visão geral do número de itens por estado;
- lista de pautas/edições, identificadores e etapa;
- detalhes de história com fontes, versões de texto, relatório de revisão e eventos;
- indicação de bloqueios/direitos e de falhas recuperáveis;
- abertura da prévia HTML interna;
- comando de aprovação **interna** com confirmação explícita;
- mecanismo controlado para executar/reiniciar os fixtures de demonstração;
- mensagens de erro compreensíveis, navegação básica por teclado e legibilidade sem animações obrigatórias.

O visual é neutro e provisório: NÃO antecipar o design do Bloco 03 nem a revista final. A versão 0.1 não precisa ter páginas com frente/verso real; precisa apenas demonstrar a entrega de um pacote de edição e uma prévia. Evitar dependências do browser/rede externa.

CLI de apoio deve permitir migrar/abrir banco, importar fixtures, rodar pipeline, consultar status e testar retomadas. Não exigir CLI e painel tenham controles redundantes sofisticados; apenas tornar a validação reprodutível.

## 7. Integridade, privacidade e limites de execução

- Banco e gravação de arquivos devem preservar consistência: nenhuma transição fica aprovada sem persistir seu resultado; operações repetidas idempotentes.
- Registrar falhas técnicas sem segredos, motivos de bloqueio e vínculos a artefatos.
- Retry configurável e finito; não repetir fases já confirmadas depois de reiniciar, salvo comando explícito de novo teste.
- Não ativar relógio de 3 coletas/dia nesta versão, nem web scraping, chamadas de IA, imagem remota, credenciais, conexão a redes sociais, armazenamento em nuvem ou automatização de publicação.
- Não consumir quotas de modelos de IA para etapas internas da simulação. O Codex pode consumir sua franquia de desenvolvimento para escrever/testar o código, mas o programa resultante deve funcionar totalmente OFFLINE.
- Não depender da leitura de chats ChatGPT para funcionamento.
- Não confundir `aprovado_para_uso_editorial` com autorização de publicidade. Acervo comercial é separado e fica para etapa posterior.
- Prever separação funcional e testes que impeçam acesso cruzado entre material editorial e publicitário quando o módulo comercial for construído.

## 8. Critérios de aceite obrigatórios

A entrega só pode ser chamada **v0.1 implementada** após:
- [ ] Instalação/configuração local documentada e execução reproduzível no Windows, com portabilidade realista para Debian;
- [ ] Um comando/teste com fixtures fictícias demonstra o fluxo completo até `aguardando_aprovacao_humana`;
- [ ] Aprovação humana registrada é necessária para `aprovado_internamente`, sem meio de publicação externa;
- [ ] Desduplicação real (mesma entrada reaplicada não cria registros extras);
- [ ] Reprovação editorial cria revisão nova e volta para nova revisão; não aprova versão desatualizada;
- [ ] Mídia pendente/bloqueada nunca é incorporada à prévia; razões e placeholder rastreáveis;
- [ ] Falha técnica é simulada e retomada sem perda/dobramento indevido do trabalho;
- [ ] Transições inválidas são recusadas por regra e por teste automatizado;
- [ ] Banco persiste entre reinicializações e mantém log audível/consultável;
- [ ] Painel mostra estado real do banco, detalhes, problemas e prévia interna;
- [ ] Nenhuma API externa, LLM, publicação, campanha, upload remoto ou conta necessária;
- [ ] Todos os testes automatizados executados; informar comando, totais, resultado, ambiente e limitações honestamente;
- [ ] `README` técnico de execução e relatório curto de implantação, riscos e próximos adaptadores;
- [ ] Código versionado em branch/PR sem misturar alterações criativas de outros setores.

Critérios não atendidos devem ficar claramente declarados como **pendentes**; não esconder falhas nem mudar o critério unilateralmente.

## 9. Autonomia, ciclos e entrega do Codex

O Codex está **autorizado a CONSTRUIR este protótipo 0.1 e testá-lo**. Deve continuar por conta própria após erros normais, dividir trabalho em commits sensatos, corrigir falhas e rodar testes até obter uma entrega verificável. Sem necessidade de discutir linguagem/classe/rotas com o diretor. Estudar rapidamente documentos atuais antes de modificar código.

**Parar e reportar** se: houver necessidade de custo financeiro/serviço pago, direitos não comprovados, acesso a credenciais, publicação/rede pública, intervenção fora do repositório autorizada, ou exigência impossível sob restrições. Preferir alternativa local mínima e documentar trade-off. Não forçar permissões ou ignorar controles.

Trabalhar numa branch `codex/motor-editorial-v0.1` (ou derivação se já existir) e propor PR; não fazer merge automático. Entrega esperada:
- código-fonte do motor e testes;
- exemplos fictícios, HTML de prévia e instruções de execução;
- resumo da arquitetura implementada (não somente proposta);
- link para PR/commits e relatório de testes e limitações;
- recomendações pontuais de ajuste, como engenheiro que identificou restrições reais.

## 10. O que NÃO é parte da v0.1

Não implementar agentes reais, sincronização com ChatGPT Projects, TTS, personas definitivas, buscadores de notícias, coletas agendadas, acervo real de publishers, PDFs, flipbook definitivo, publicidade, afiliados, CMS completo, autenticação pública, deploy, domínio ou hospedagem externa. Esses são **módulos posteriores**, plugados no núcleo após especificação e aprovação própria. A v0.1 não deve exigir essas partes para funcionar.

**Próximo marco depois da v0.1 (não autorizado nesta ordem):** integrar uma etapa real por vez, começando por coleta controlada ou execução LLM autorizada, com medição de quotas/custos e sem quebrar a persistência ou os controles de revisão.

## 11. Documentos de referência

`docs/governanca/BIBLIA-DO-PROJETO.md`, `AGENTS.md`, `docs/governanca/DECISOES.md`, `docs/engenharia/README.md`, `docs/operacao/CONTRATO-ENTREGAS.md`, `docs/operacao/PROTOCOLO-HANDOFF.md`. Em caso de choque de orientações genéricas de "standby" dos **blocos de concepção**, esta **ordem específica do diretor para CONSTRUÇÃO do Motor 0.1** se aplica apenas ao Codex engenheiro, não aos outros blocos.
