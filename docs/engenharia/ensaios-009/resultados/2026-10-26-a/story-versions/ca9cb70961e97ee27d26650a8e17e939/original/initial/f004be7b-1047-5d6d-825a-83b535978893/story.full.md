# REFramework em Requiem: a infraestrutura criativa ainda não é garantia de compatibilidade

As notas curatoriais descrevem uma ferramenta de scripting e uma rede crescente de possibilidades, mas também registram relatos de incompatibilidade que não permitem concluir nem que o suporte falhou para todos nem que os problemas foram corrigidos. Os materiais de origem não foram obtidos para verificação independente.

## Uma ferramenta não é a mesma coisa que um mod

O primeiro cuidado é separar camadas que costumam aparecer juntas quando se fala de mods. Segundo a nota curatorial N01, o projeto REFramework, associado ao autor praydog, se apresenta como uma ferramenta open source para jogos RE Engine. A nota descreve recursos de scripting em Lua, plugins e utilidades como ajustes de câmera e campo de visão, além de suporte a VR em títulos indicados pelo projeto. A própria lista do README, conforme resumida pela curadoria, inclui Resident Evil Requiem. Isso é uma declaração de suporte do projeto — não um resultado de teste independente nem uma promessa de compatibilidade em toda configuração.

Essa descrição aponta para uma função diferente da de um pacote que altera apenas a aparência ou de um mod que modifica regras e sistemas do jogo. O framework é uma camada de infraestrutura: pode oferecer meios para que outros projetos funcionem, mas não é, por isso só, prova de que cada projeto dependente esteja atualizado, seja estável ou mude determinada mecânica. Um script é uma peça executada por meio dos recursos de scripting; um preset visual, por sua vez, descreve uma configuração ou alteração voltada à apresentação. Um mod de regras promete mexer no funcionamento do jogo. Essas categorias podem se sobrepor na prática, mas as notas não detalham pacotes concretos o bastante para classificar exemplos específicos de cada tipo.

A nota N07 descreve o REFramework na lista de destaques do Nexus como infraestrutura com API Lua, e menciona outros projetos, incluindo um mod de inventário e _ScriptCore. N08, uma curadoria jornalística de terceiro, também o caracteriza como base para outros mods. As duas descrições apoiam a interpretação de que a importância potencial da ferramenta vai além de uma mudança cosmética: ela pode ampliar o que outros criadores conseguem construir. Mas não demonstram que todos os mods dependam dela. A nota não validada N11, aliás, alerta que relações de dependência, versões e licenças de outros projetos ainda precisam ser confirmadas.

## Suporte declarado, relatos de falha e versões que não se encaixam automaticamente

A diferença entre suporte listado e funcionamento comprovado aparece nos relatos comunitários resumidos no dossiê. N03 identifica um reporte de 13 de março de 2026: a pessoa autora relata crash ao iniciar Requiem v1.1.2.0 com REFramework nightly v1.5.9.1, indicando também um hash de build; sem o componente, o problema teria desaparecido naquele sistema. Isso descreve uma combinação e um relato individual. Não estabelece que o framework cause crashes em geral, nem que o problema continue presente hoje.

N05 registra outro relato, de 1º de março, em ambiente descrito como Windows 10, RTX 5090 e nightly v1.5.9.1. A pessoa relata conflitos envolvendo DLSS Frame Generation e componentes de hook, com comportamento diferente quando o Steam Overlay estava ativo. A nota ressalva que distinguir uma causa suspeita de uma causa demonstrada exigiria mais evidência. O contraste entre as configurações também importa: não se pode transformar uma lista de variáveis — sistema operacional, GPU, overlay e componentes concorrentes — em uma explicação causal sem confirmação.

Já N04 resume um reporte de 27 de março, posterior a uma atualização do jogo, sobre crash associado a essa atualização. A issue aparece como “closed as not planned”, mas o resumo não fornece a versão exata do jogo, uma confirmação posterior de funcionamento, nem a explicação completa do encerramento. Encerramento administrativo não equivale, por si, a correção. Tampouco é possível atribuir o problema a todos os usuários com base nesse único relato.

Há, portanto, duas classes de informação que não devem ser misturadas: a listagem de suporte do projeto em N01 e experiências relatadas sob condições particulares em N03, N04 e N05. Elas não se anulam. O suporte declarado pode coexistir com regressões, limitações de versão ou conflitos em certas configurações. Como os corpos das fontes não foram obtidos, não é possível aqui confirmar os detalhes dos relatos, verificar comentários posteriores ou estabelecer o estado atual das issues.

## O que mudou com patches e nightlies continua em aberto

Para responder se os problemas foram resolvidos, seria necessário alinhar, no mínimo, a versão do jogo, a build do framework, a data do reporte e as condições do sistema. As notas disponíveis não oferecem essa linha do tempo completa. N02 observa que a página de releases pode exibir uma versão estável antiga enquanto builds nightly mais recentes aparecem em outro lugar. Por isso, tomar a primeira release visível como “a versão válida para Requiem” seria uma conclusão precipitada.

Também não há nos materiais fornecidos um changelog comparado, patch por patch, que explique o que mudou no jogo, no framework ou nas nightlies entre os relatos de março. A existência de uma build mais nova não prova que ela corrigiu um problema específico; e uma issue fechada não substitui a descrição da mudança, uma reprodução posterior ou relatos de confirmação. A evidência reunida permite identificar perguntas e combinações que merecem investigação, não declarar um histórico de correções.

Uma checagem adequada precisaria conferir datas, números de versão e changelogs correspondentes, além de verificar se há confirmação reproduzível para cada ambiente citado. Até lá, a formulação responsável é restrita: há suporte listado pelo projeto e há relatos localizados de incompatibilidade; o material não mostra se, quando ou em quais builds esses casos foram solucionados.

## Popularidade não mede qualidade nem segurança

O Nexus Mods aparece nas notas como um catálogo de projetos, não como um teste técnico. N06 descreve uma categoria com vários tipos de mods e ressalta que contagens e rankings variam com filtros, paginação, visibilidade e momento da consulta. A nota não fornece valores numéricos conferíveis; portanto, não há base aqui para afirmar quantos projetos existem, quantos downloads somam ou qual seria a dimensão atual da comunidade.

Mesmo se uma contagem estivesse disponível, downloads não equivaleriam automaticamente a pessoas ativas, uso continuado, compatibilidade ou segurança. Um número alto pode ser um sinal de atenção ou interesse, mas não determina se um pacote funciona com a versão atual do jogo, se é bem mantido ou se tem permissão para reutilizar todos os materiais que inclui. N07 também descreve itens destacados e dependências, mas a curadoria alerta que popularidade não prova eficácia atual nem autorização de reutilização.

A distinção importa porque um ecossistema pode parecer movimentado sem que isso resolva as questões práticas de cada instalação. E o inverso também é possível: pouca visibilidade num catálogo não prova que uma ideia seja ruim. Sem números, critérios de contagem e amostragem comparável, o catálogo serve como pista para localizar projetos, não como ranking científico de qualidade.

## Autoria e direitos exigem exame projeto a projeto

As notas atribuem o REFramework a praydog e resumem o projeto como open source (N01), mas os materiais de origem e os termos aplicáveis não foram revalidados neste trabalho. Essa atribuição não identifica automaticamente autores de mods que usem a ferramenta, nem estabelece a licença ou a procedência de cada elemento incluído em outros pacotes.

A própria N11 indica que projetos citados no catálogo, como _ScriptCore e Max Stack Sizes, precisam de consulta às páginas e aos manifestos específicos para confirmar autoria, dependências, versão e licença. Não se deve generalizar a relação de dependência para todos os mods. Também não há evidência neste dossiê para afirmar que algum projeto violou direitos, recebeu autorização de uma empresa ou foi patrocinado por ela. N10 fornece contexto sobre o produto base e adverte, no resumo, que Capcom não é automaticamente autora nem patrocinadora do REFramework.

Uma apuração sobre direitos deveria verificar, para cada pacote relevante, a página e o manifesto, a licença declarada, as atribuições e a origem de eventuais assets de terceiros. Isso pode começar pela documentação pública e pelo diálogo com criadores, sem instalar os arquivos nem republicar imagens. Relatos da comunidade podem ajudar a localizar problemas e inconsistências, mas precisam ser tratados como pistas contextualizadas, não como consenso ou decisão legal. Não há, nas notas disponíveis, base para resolver essas verificações.

## Veredito: potencial documental, compatibilidade ainda condicional

O que se pode sustentar é um veredito limitado. A documentação resumida apresenta o REFramework como infraestrutura de criação e lista Requiem entre os jogos suportados (N01); as referências a API Lua, plugins e projetos relacionados sugerem por que esse tipo de camada pode ampliar as possibilidades de modificação para além de ajustes cosméticos (N07, N08). Essa é uma oportunidade relevante para criadores e para quem acompanha ferramentas experimentais. Não é, porém, uma avaliação da qualidade de cada mod, nem prova de que a ferramenta funcione sem problemas em toda versão ou configuração.

Para quem pesquisa o ecossistema no PC, a documentação pode ajudar a entender o que existe e quais dependências investigar. Para quem precisa de uma experiência previsível, os relatos de crash e conflito são motivo para cautela até que versões, changelogs e confirmações sejam verificados. Não recomendo aqui uma DLL específica nem uma instalação: o pacote não foi instalado, testado ou executado, e as notas não estabelecem uma combinação segura e atual. Os requisitos do jogo base resumidos em N09 também não demonstram desempenho, estabilidade ou segurança de mods. E o material disponível não permite estender conclusões do PC a consoles.

A conclusão não é que o framework esteja quebrado, nem que a compatibilidade esteja resolvida. É que a promessa de infraestrutura e a experiência concreta precisam ser avaliadas separadamente, com versões e condições identificadas. Neste momento, a evidência curada é suficiente para justificar investigação adicional, mas insuficiente para uma recomendação técnica geral. Além disso, como os corpos das fontes não foram obtidos, todas as descrições acima permanecem atribuições a notas curatoriais, e não verificações independentes das páginas citadas.

## Próxima pergunta para o Radar

A questão complementar é: que registros locais com evidência classificada como declaração oficial tratam do REFramework e do ecossistema de mods de Resident Evil Requiem, e que identificadores, datas e versões permitem conferi-los? O material recebido não contém resultado de consulta ao índice local do Radar. Por isso, não apresento registros adicionais como se tivessem sido encontrados; a lacuna permanece aberta.
