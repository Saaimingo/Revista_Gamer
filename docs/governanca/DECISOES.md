# Registro de decisões e hipóteses

Atualizado: **2026-10-19**. Este registro resume decisões relatadas em conversa; antes de tratar arquivos derivados como especificação congelada, submetê-los à direção para aprovação.

## Diretrizes consolidadas com o fundador

- **D-001** Revista gratuita, foco predominante em games, mais hardware, informática e nostalgia.
- **D-002** Publicidade contratada e afiliados são fontes pretendidas de receita; anúncios visivelmente identificados e totalmente separados do editorial, inclusive nos acervos.
- **D-003** Redação majoritariamente feita por IA, com diretor humano aprovando edição e custos; não fingir autoria humana nem teste que não ocorreu.
- **D-004** Personagens jornalistas têm identidade reconhecível e estável ao longo das edições; voz digital futuramente, se viável.
- **D-005** Jornalismo baseado em fontes profissionais + experiências da comunidade, com rigor, contexto e atribuição; não copiar conteúdo.
- **D-006** Experiência tipo revista física com folhas frente/verso; navegação de folhear e modo simples opcional; acessível e leve.
- **D-007** Tema gráfico de cada edição pode variar conforme o destaque, preservando identidade central.
- **D-008** Acervo de mídias organizado por titular/empresa, obra e ativo, com ficha de permissões por item e catálogo pesquisável.
- **D-009** Canal permanente de sugestões; divulgação nas redes; publicações antigas permanecem acessíveis.
- **D-010** Este repositório será central de documentos e comunicação assíncrona entre blocos; não há sincronização automática entre chats.
- **D-011** O diretor fixa a visão e limites; o chat fundador responde pela arquitetura; o Codex é engenheiro construtor, autorizado a resolver escolhas técnicas usuais e obrigado a sinalizar inviabilidade/riscos materiais. Não devolver escolhas triviais ao diretor.
- **D-012** Autorizada a **construção do Motor Editorial v0.1 exclusivamente como protótipo local**, com fluxos simulados, testes e aprovação humana interna. NÃO estão autorizados deploy público, coleta agendada real, IA de produção, compra de serviços nem a primeira edição real. Contrato: `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md`. Ordem: `docs/engenharia/ORDEM-CODEX-001-CONSTRUIR-MOTOR-V0.1.md`.
- **D-013** Motor Editorial v0.1 **validado como protótipo local** com evidências no Windows 11/Python 3.11.9 e Linux/Python 3.12.14, revisão arquitetural favorável e [PR #3](https://github.com/Saaimingo/Revista_Gamer/pull/3) integrado à `main` no commit `525ae351d1e7375821435efeb1e012955785f69d`. Essa integração é somente baseline de código e não autoriza operação real, dados privados em repositório público, coleta programada, serviços pagos, publicação nem v0.2 sem nova missão.
- **D-014** A documentação final do aceite da v0.1 foi integrada pelo [PR #4](https://github.com/Saaimingo/Revista_Gamer/pull/4). **Nova ordem CODEX-002 autorizada** para IMPLEMENTAÇÃO do Motor Editorial v0.2 multipauta **somente offline, simulado e local**. Contratos: `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.2-MULTIPAUTA.md` e `docs/engenharia/ORDEM-CODEX-002-MOTOR-MULTIPAUTA.md`. A execução depende de iniciar sessão Codex; nenhum merge, API real, coleta externa ou publicação foi autorizado.

- **D-015** Ao término das rodadas de discussão entre diretor e Chat Fundador, registrar na **pasta do setor correspondente** um parecer de integração com acertos, críticas, sugestões, pendências, decisões realmente ratificadas e próximas ações. Enquanto a discussão estiver em aberto, usar a marca **PROVISÓRIO**. Vincular o parecer no README do bloco para consulta posterior. Isso **não notifica automaticamente outros chats**, não implica autorização de produção/Codex e não transforma opiniões técnicas em decisões da direção. Protocolo: `docs/operacao/PROTOCOLO-HANDOFF.md`.

- **D-016** **Premissa de integração dos agentes para fases futuras:** priorizar a utilização de mecanismos **oficiais e autorizados** de execução programática compatíveis com a **assinatura ChatGPT Plus/Codex já existente do diretor**, antes de propor API cobrada à parte ou infraestrutura paga. Compete ao Codex, sob especificação e autorização próprias, investigar a elegibilidade real, formas suportadas de autenticação, execução não interativa, quotas, limites, regras de uso e continuidade de acesso; implementar e comprovar em testes a ativação do executor correto e o carregamento da identidade versionada de cada cronista. **Não presumir que o Plus equivale a créditos de API, permite toda modalidade de automação ou sustenta produção contínua.** Na ausência de acesso oficial adequado, ou ao atingir limites, registrar o impedimento e **pausar com segurança, sem cobrança, bypass de quotas, aproveitamento de sessão privada ou migração financeira automática**. A orquestração do Motor é requisito antes da operação dos agentes reais; esta decisão **não autoriza ligar agentes, agendamento, gastos, publicação ou ampliar o escopo da v0.2**. Referência: `docs/engenharia/ANALISE-PROVISORIA-FUNDADOR-ORQUESTRACAO-N8N-2026-10-17.md`.

- **D-017** **Aceite técnico e integração do Motor Editorial v0.2:** após revisão do commit `81ee9fd` e das regressões de elegibilidade editorial C1, o chat fundador recebeu delegação da direção para concluir as decisões técnicas do protótipo simulado; a entrega da CODEX-002 foi integrada à `main` pelo [PR #6](https://github.com/Saaimingo/Revista_Gamer/pull/6), merge commit `794e9fcc20f5944031370bd7ddb93f8b323d9528`. O Codex reportou **22/22 testes no Windows 11**; o fundador verificou o código e os testes por inspeção, não reexecutou a suíte. **A delegação cobre aceites técnicos normais de protótipos autorizados, não amplia autonomamente o escopo para despesas, credenciais, integração de serviços reais, publicação, produção ou mudança de fase sem autorização.** A v0.2 permanece offline e simulada. Antes de conectar agentes reais, detalhar e validar o mecanismo de despacho, as interfaces autorizadas da conta Plus/Codex (D-016), a invalidação coerente do estado da pauta quando revisão muda e os limites de custo/execução.

- **D-018 — Agentes operacionais, memória histórica e inteligência de composição:** a direção esclareceu em 20/10/2026 que os **Blocos 02–06 são temporários para concepção**, não executores da linha de montagem. A execução futura pertence a agentes/funções sob controle do Motor Editorial e a módulos determinísticos. O diagramador deverá ter acesso a **índice local de referências históricas de diagramação** e receber reportagem e ativos autorizados para propor uma composição adaptada à identidade visual e aos leitores atuais; **não copiar páginas históricas nem publicar imagens sem autorização de direitos**. Para evitar refazer o motor, foi autorizada **somente a Fase 0 offline de contratos, índice mínimo, agente simulado, layout/validador determinístico e testes**, via [Issue #17](https://github.com/Saaimingo/Revista_Gamer/issues/17) e [especificação arquitetural](../engenharia/ARQUITETURA-AGENTES-ACERVO-VISUAL-E-COMPOSICAO-2026-10-20.md). Isso **não autoriza** inferência SIWC, uso real de acervo editorial, serviços pagos, publicação, implantação remota ou merge dos PRs pendentes. A [Issue #15](https://github.com/Saaimingo/Revista_Gamer/issues/15) continua a trilha de design para unir visual dos mocks e leitor v0.3.

## Hipóteses de trabalho, não decisões irrevogáveis

- **H-001** Primeira edição: aproximadamente 10 folhas/20 faces, contando capa e contracapa; volume poderá mudar.
- **H-002** Periodicidade inicial: em torno de três semanas, sujeita à medição de capacidade.
- **H-003** Operação piloto com 3 funções de IA (editor-pesquisador, redator, revisor) e até 3 personas (Ranzinza, Gamer, Historiador); validar custo e qualidade.
- **H-004** Usar Luna/Codex com plano Plus inicialmente; acesso autônomo em nuvem/limites precisam ser testados. Sem contratar API por padrão.
- **H-005** Possível PDF colecionável e wallpapers próprios/licenciados.
- **H-006** Repositório central primeiro; repositórios separados para software podem ser criados depois.

## Decisões pendentes

Nome comercial/domínio/marca, identidade visual final, personagens definitivos e nomes, cadência depois de teste, permissões reais por publisher/ativo, orçamento com gastos adicionais, serviços de nuvem, habilitação de automações e publicação pública.

## Como mudar uma decisão

Abrir Issue com referência `D-NNN`, proposta, motivo, impacto e setores afetados. Aprovação humana registrada em PR/Issue; atualizar este arquivo e quaisquer contratos relevantes no mesmo conjunto de mudanças. Não substituir decisões silenciosamente.
