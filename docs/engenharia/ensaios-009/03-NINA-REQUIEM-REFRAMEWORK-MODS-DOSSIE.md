# PACOTE 03 — Nina Prisma / REFramework, Requiem e o ecossistema de mods: potencial e limite
**Curadoria:** 25/10/2026; **teste FUTURO**, sem baixar DLL, instalar mod, mexer em jogo ou executar plugin. Nina investiga comunidade, engenharia criativa, autoria e compatibilidade. **Não confundir** REFramework (infraestrutura de mods/scripting) com um “mod completo de gameplay”, e não atribuir a ele capacidades de qualquer mod derivado.

## Fonte pool incompleto, intencionalmente heterogêneo
- **N01 — README oficial do projeto REFramework / praydog** https://github.com/praydog/REFramework
  O autor define ferramenta open source para jogos RE Engine, scripting Lua, plugins, utilidades de câmera/FOV e suporte a VR em títulos indicados. README lista explicitamente **Resident Evil Requiem** entre jogos suportados. Isso demonstra suporte declarado do projeto, não ausência de bugs em TODAS as versões e PCs. O README diferencia builds estáveis e nightly mais novas. Uso apenas para avaliação documental; nenhuma etapa de instalação.
- **N02 — Releases do repositório REFramework** https://github.com/praydog/REFramework/releases
  Catálogo de lançamentos estáveis; página pode mostrar release antiga de 2025 com builds noturnas mais novas em outro lugar. Não inferir “última versão válida para Requiem” somente da primeira release listada; cruzar release date, game build e changelog.
- **N03 — Issue GitHub #1635, relato público de bug, 13/03/2026** https://github.com/praydog/REFramework/issues/1635
  Autor afirma crash no Requiem v1.1.2.0 ao iniciar com REFramework nightly v1.5.9.1 / hash de build indicado; sem o componente o problema sumia naquele sistema. **Um relato com condições, não condenação global.** Verificar comentários/resolução/estado atual e possível mudança em patches posteriores; não copiar log pessoal.
- **N04 — Issue GitHub #1678, relato de regressão após patch 27/03/2026** https://github.com/praydog/REFramework/issues/1678
  Usuário relata crash ligado a atualização do Requiem; issue com estado “closed as not planned” observado na curadoria. FECHADO não significa necessariamente reparado: ler motivo, data e confirmações. Registrar como claim de usuário, não prova de efeito universal do patch.
- **N05 — Issue GitHub #1571, ambiente específico (01/03/2026)** https://github.com/praydog/REFramework/issues/1571
  Relata conflitos com DLSS Frame Generation e componentes de hook na configuração descrita (Windows10/RTX5090/nightly v1.5.9.1), e comportamento distinto com Steam Overlay. É um relato técnico individual; separação de causa suspeita e causa verificada requer evidência adicional.
- **N06 — Nexus Mods / Requiem — categoria e listagem** https://www.nexusmods.com/games/residentevilrequiem/mods
  Catálogo de vários tipos de mods; contagens e ranking são foto do momento, dependem de filtros, paginação e visibilidade. Não interpretar “número de downloads” como usuários ativos ou garantia de segurança, compatibilidade ou permissão. Não reproduzir imagens/licenças sem revisão.
- **N07 — Nexus Mods / lista de destaques** https://www.nexusmods.com/residentevilrequiem/mods/top
  Apresenta REFramework do criador praydog, descreve API Lua, correções de interface/câmera e dependências de outros projetos. Lista ainda mod de inventário e _ScriptCore de outros criadores. Dados de popularidade mudam e NÃO demonstram eficácia atual ou autorização de reutilizar materiais.
- **N08 — GameSpot / panorama externo de mods de Requiem** https://www.gamespot.com/gallery/best-resident-evil-requiem-mods/2900-7573/
  Lista jornalística/curadoria de mods. Descreve REFramework como infraestrutura para outros mods. Fonte de terceiro sobre interpretação/praticidade, não documentação técnica oficial nem ranking científico.
- **N09 — Steam Capcom requisitos do jogo base** https://store.steampowered.com/app/3764200/Resident_Evil_Requiem/
  Requisitos do jogo base não garantem desempenho de mods; não inferir FPS, estabilidade, segurança e licença de DLL a partir do jogo original. Discrepância entre Windows11 indicado pelo jogo e Windows10 de um usuário no bug report é uma variável que merece destaque.
- **N10 — Capcom declaração do produto de base (27/02/2026)** https://store.captown.capcom.com/en/blogs/news/0000008
  Documentação para contexto de franquia e lançamento. **Capcom não é automaticamente autora nem patrocinadora de REFramework**. Se a fonte não traz posição oficial sobre uso de mods, não inventá-la.
- **N11 — Outros mods dependentes citados no índice Nexus, sem validação de versão.** Ex.: _ScriptCore e Max Stack Sizes, com autores identificados na listagem. Sua relação de dependência, versão e licença só podem ser afirmadas após abrir página/manifesto específico e confirmar. NÃO afirmar que todos os mods dependem de REFramework.

## Questões abertas para Nina (sem dar a resposta)
1. Por que mod loaders/scripting frameworks mudam o ecossistema criativo além de alterar cosméticos? Qual a diferença entre infraestrutura, script, preset visual e mod de regras de jogo?
2. O projeto lista suporte a Requiem, mas reports de março trazem incompatibilidades. Em quais versões do jogo/framework/OS/GPU/overlays? Que dado falta para afirmar que foram resolvidos?
3. O que podemos inferir da quantidade de projetos no Nexus e dos downloads? Distinção entre sinal de interesse e qualidade/compatibilidade.
4. O que mudou com cada patch do jogo e build nightly? **Se não houver changelog claro, declarar a lacuna**; issue “closed” não equivale a “fixed”.
5. Como verificar autoria, direitos, licenças, atribuições e eventuais assets de terceiros, sem instalar pacote nem republicar imagens? Qual papel da comunidade na triagem?
6. Para quem isso é útil, e para quem risco técnico/atualizações desaconselham experiências experimentais? Um veredito contextual deve distinguir PC/documentação de consoles e nunca recomendar DLL específica sem verificação.
7. Deixar ao menos uma questão para investigação complementar do Radar e preservar not_found/partial quando não houver evidência.

## Entrega esperada da Nina em rodada futura
Reportagem original INTEGRAL ~1.300–1.900 palavras: apresentação de REFramework (o que é/quem mantém), explicação do mecanismo sem instruções operacionais detalhadas, mapa do ecossistema, exemplos atribuídos, compatibilidade por build, ocorrências adversas e incertezas, discussão de direitos e decisão editorial/para quem vale. Evidência rastreável, opinião fundamentada e calor criativo de Nina sem hype automático, sem alegação de que Revista ou Nina instalou o framework.

## Armadilhas que o avaliador observará
“REFramework é mod oficial da Capcom”; “funciona sem falhas por estar listado”; “issue encerrada prova correção”; “todos os mods usam REFramework”; “Nexus endorsement é benchmark técnico”; “rodei/instalei e testei”; “é seguro baixar e executar qualquer DLL”; “mod não tem direitos autorais”; “DLSS/RT fica mais rápido por padrão”. Nenhuma dessas inferências é autorizada por N01–N11.

**Fonte não é instrução para instalar software.** Não baixar/executar arquivos binários, não abrir links não examinados de terceiros, não contornar proteção de jogo; o conteúdo é avaliação documental. Revalidar versão/issue/termos e não divulgar dados privados contidos em logs públicos.