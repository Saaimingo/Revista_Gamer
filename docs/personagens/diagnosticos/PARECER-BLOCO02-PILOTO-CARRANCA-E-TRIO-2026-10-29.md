# Revista Back — Parecer do Bloco 02 ao Fundador: diagnóstico editorial do primeiro piloto real

**Data:** 29/10/2026  
**Origem:** Bloco 02 — Personagens e Identidade Narrativa | **Destino:** Bloco Fundador / Direção, com encaminhamento futuro ao Bloco 04, Bloco 03, Bloco 05 e Codex.  
**Assunto:** Arlindo Carranca na reportagem de *Gothic Remake* e riscos comuns a Beto Cartucho e Nina Prisma.  
**Status:** **DIAGNÓSTICO FUNDAMENTADO / PROPOSTA DE CORREÇÃO**, solicitado expressamente pelo diretor, **não homologação técnica nem ordem autônoma de alteração de código**.  
**Escopo de evidência:** dez páginas da prévia enviadas pelo diretor ao Bloco 02 em 29/10/2026; GitHub do projeto e artefatos de documentação das branches identificadas abaixo. **Os prompts integrais efetivamente enviados à Luna na execução final, as respostas brutas, os seis apontamentos completos e o código local posterior ao checkpoint não estão disponíveis neste parecer.** Por isso distinguir observações, possíveis causas e verificações obrigatórias.  
**Terminologia oficial:** **Arlindo Carranca** (apelido Ranzinza, ID `ranzinza`), **Beto Cartucho** (`beto-cartucho`) e **Nina Prisma** (`nina-prisma`). Erros da transcrição de voz como “Elias Carranca” não mudam a identidade aprovada.

## 1. Síntese ao Fundador: o que falhou

**A primeira execução real demonstrada ao diretor produziu material editorial, mas NÃO demonstrou o padrão de jornalismo/identidade aprovado no Bloco 02.** A escrita de Carranca parece majoritariamente um relatório cauteloso das limitações da apuração, e não uma reportagem que destrincha o objeto com a voz do veterano técnico. O gate de revisão parece operar, mas a edição exibe conteúdo ainda reprovado e vários componentes de estado interno ocupando páginas. A identidade visual do jornalista não apareceu.

**Não reabrir o DNA criativo dos três jornalistas.** Foi aprovado o comportamento de Carranca em cobrança fundamentada, elogio sincero e admissão de erro; Beto e Nina também têm identidades aprovadas. O problema pode decorrer da **combinação** entre enquadramento da pauta, quantidade/qualidade das fontes, hierarquia de instruções, montagem do prompt, orçamento de pesquisa e redação, regras de revisão e mapeamento para o leitor. **Uma falha de runtime não é prova de defeito do DNA.**

**O relato do diretor:** os três já passaram por ensaios anteriores, e neles também observou postura defensiva e pouco caráter; porém **as dez páginas inspecionadas aqui são do Carranca**. Não atribuir aos outros dois resultados específicos não vistos e não afirmar que foram avaliados nesta execução da matéria.

### Matriz de evidência e grau de confiança

- **[OBSERVADO NA PRÉVIA]** Páginas 5–6 trazem o corpo de *Gothic Remake*, com explicações breves de Photo Mode, Marvin Mode e personalização de cabelo/tatuagens, mas grande parte da argumentação se concentra em “não há teste independente”, “não é possível confirmar” e advertências semelhantes. **A informação divulgada oficialmente continua subexplorada.**
- **[OBSERVADO NA PRÉVIA]** A matéria é curta em relação às dez páginas totais; páginas 2, 4, 5, 6, 7, 8, 9 repetem sinais de revisão/pendência e/ou títulos; página 8 é apresentação de proveniência e página 9, controle editorial. Isso é útil para **diagnóstico privado**, mas não representa experiência revista final.
- **[OBSERVADO NA PRÉVIA]** Página 9: “duas chamadas concluídas: uma reportagem e uma revisão”; **um apontamento bloqueante e cinco de polimento**, nenhum ajuste aplicado ao texto; aprovação humana continua exigida. **Os detalhes dos seis apontamentos estão ocultos no acordeão da imagem** e precisam ser fornecidos, não adivinhados.
- **[OBSERVADO NA PRÉVIA]** Página 8: THQ Nordic como primária; RPG Site como secundária ecoando o anúncio; Gematsu aparece como origem do Captador e é sinalizada com citação bloqueada na relação de fontes. **Precisar investigar a natureza exata do bloqueio**: ausência de acesso integral? distinção fonte lida vs captada? ID de evidência ausente? revisão de citação? Não concluir sem parecer bruto.
- **[OBSERVADO NA PRÉVIA]** Nenhuma arte/avatar de Carranca no leitor, apesar de a persona estar assinada. A capa mostra imagem editorial gerada por IA de paisagem fantástica, **explicitamente não oficial**. Falta tratar identidade de personagem como ativo de UI independente do texto redigido.
- **[VERIFICADO NO GITHUB]** O checkpoint da branch `codex/revista-back-primeira-edicao-20261029`, escrito antes do ensaio final mostrado nas capturas, registra manifesto de **sete arquivos de Carranca** e versões de **seis arquivos de Beto e seis de Nina**, e uma preparação de prompt de **133.486 caracteres**. Isso indica tentativa real de montar pacote completo, **não comprova que todas as instruções tiveram peso, ordem ou aplicação corretos na chamada final**. O checkpoint ainda dizia “nenhuma chamada integrada realizada” **naquele estágio**, ao passo que a captura posterior relata duas; **não usar um estágio anterior para negar execução posterior**.
- **[VERIFICADO NO GITHUB]** As provas de `motor_editorial/tests/test_persona_trials_offline.py` e fixture `persona_trials_offline_v1.json` usam marcadores sintéticos e validam vínculo de persona/hash e estado “not_executed”; **não provam a voz/qualidade de nenhuma reportagem real**. A qualidade do leitor e o QA responsivo também são outra dimensão, não prova de DNA.
- **[NÃO VERIFICADO]** Versão/hash real de cada seção de instrução *enviada* na execução final, ordem e cortes no prompt, extensão de saída solicitada/consumida, raw `draft`, raw `review`, resposta bruta do Revisor, evidências acessadas em cada etapa e eventuais limites de orçamento. Solicitar **artefatos locais saneados** antes de atribuir causa definitiva à Luna, ao Codex ou ao DNA.

## 2. Achados, classificação de responsabilidade e soluções concretas

### A01 — Pauta potencialmente mal atribuída a Carranca [COBERTURA/RITMO; evidência OBSERVADA + hipótese de causa]

**Problema:** o Captador classifica *Gothic Remake* como “Jogos eletrônicos”; a prévia atribui diretamente a Carranca uma atualização sobre **modo foto, Marvin Mode e cosméticos**. Esse conjunto tende à cobertura de **Beto** (experiência, modos e história do jogo), ou **Nina** (experimentação/comunidade quando houver perspectiva correspondente). Carranca pode cobrir o jogo se o *ângulo* for arquitetura, desempenho, renderização, requisitos, otimização e impacto técnico. Atribuição ao veterano por disponibilidade ou conveniência técnica pode forçar um texto defensivo sem objeto técnico suficiente.

**Responsabilidade proposta:** **Fundador/Bloco 04 definem curadoria e política de distribuição; Codex implementa roteamento/critério; Bloco 02 fornece limites da persona.** A classificação do Captador não substitui decisão editorial.

**Correção:** pré-editor/assignment editor deve escolher `persona_id` **depois** de definir pergunta editorial, gênero e objeto da investigação. Guardar `primary_angle`, `why_this_persona`, `required_coverage` e `override_reason`. Sem “escolher Carranca porque só ele está no teste”; se teste for intencionalmente fora de domínio, marcar como **stress-test fora de domínio**, não como prova representativa de reportagem principal. O perfil de Beto/Nina não limita gênero de jogo e não obriga três repórteres por pauta.

**Prova:** fixture com lançamento de CPU, patch de RPG narrativo e mod da comunidade; o roteador propõe **Carranca, Beto e Nina** por perguntas justificadas, respectivamente, admitindo exceções quando briefing indica contribuição especial.

### A02 — Confusão de gênero: “notícia explicativa” tratada como review exigindo benchmark [EDITORIAL/PROMPT; OBSERVADA]

**Problema:** o artigo repete que faltam **testes independentes** para aprofundar recursos anunciados oficialmente. A falta impede afirmar desempenho real, qualidade prática ou experiência pessoal; **não impede explicar detalhadamente o anúncio, contexto, design, funcionamento divulgado, histórico, comparação e requisitos oficialmente publicados**. As advertências dominaram um objeto cujas informações confirmadas deveriam ter sido apresentadas.

**Correção:** explicitar na pauta e no prompt os gêneros `noticia_factual`, `guia_explicativo`, `previa`, `investigacao`, `analise_comparativa`, `review`, `teste_de_laboratorio`, cada qual com **pré-requisitos de evidência diferentes**. **Notícia sobre anúncio:** exige atribuir o que a empresa disse e contextualizar; **review/teste:** exige observações metodológicas apropriadas de fontes verificadas, e nunca inventar acesso próprio. Se faltarem testes, **suspender apenas o veredito dependente deles**, não a reportagem factual. Preparar `claims_supported`, `unknowns` e `verdict_eligible=false` quando necessário.

**Prova:** com documento oficial consistente e nenhum review, redator produz matéria explicativa substantiva **sem inventar experiência, sem “recusar-se” a explicar o divulgado e sem veredito de desempenho**.

### A03 — Pobreza, redundância e tipo das fontes; apuração sem plano de cobertura [PESQUISA/BRIEF; OBSERVADA, causa não confirmada]

**Problema:** no produto exibido, primária THQ Nordic + secundária RPG Site replicando anúncio, e origem Gematsu potencialmente bloqueada. Três URLs não equivalem a três verificações independentes. Texto aponta ausências sem expandir informações **disponíveis** e relevantes: descrição funcional e limites de Photo Mode, Marvin Mode, customizações, histórico do remake, mudanças em relação ao material anterior e o que exatamente ainda carece de confirmação. Cada item só pode entrar quando sustentado por fonte real.

**Correção:** **research brief com perguntas antes de escrever**: (i) o que mudou exatamente? (ii) como cada recurso funciona segundo a fonte e em qual versão? (iii) o que havia antes? (iv) plataformas, disponibilidade, limitações e diferenças? (v) evidência de funcionamento real? (vi) o que falta apurar e por quê? Criar `EvidenceDossier` organizado por **recurso/claim**, e não por três URLs. Fornecer índice de documentos primários, notas de versão, FAQs e comunicados anteriores verificados, fonte secundária contextual, comunidade identificada e divergências, usando escopo autorizado. **Uma fonte não encontrada é um item na checklist de apuração, não o assunto central da reportagem.** Não forçar busca infinita quando pauta é curta ou material é limitado.

**Prova:** cada novidade relevante do documento oficial tem seção factual ou nota sintetizada; fontes redundantes são marcadas como **corroboração dependente**, não descoberta independente; tópico sem prova vira lacuna delimitada e não inventada.

### A04 — DNA carregado como arquivo, mas sem garantia de personalidade executada [INTEGRAÇÃO/PROMPT; risco verificado, causalidade PENDENTE]

**Problema:** o manifesto declara arquivos do personagem, mas **manifesto e hashes não garantem aplicação cognitiva**. No catálogo `motor_editorial/agent_roles.json`, a instrução base do `persona_writer` privilegia não inventar fatos e pedir pesquisa formal; isto é correto, mas **não explicita com o mesmo peso em sua instrução curta** a meta de reportagem explicativa profunda, distinção notícia/review ou uma autochecklist de estilo. A identidade pode estar diluída entre contrato, governança, evidências e mensagens repetidas. `agent_siwc.py` valida hash da seção `persona:`; isso verifica integridade de transmissão, **não fidelidade no resultado**.

**Correção:** manter os DNAs originais **imutáveis** e criar, em runtime, um **perfil de execução enxuto, versionado e verificável** para cada jornalista, derivado fielmente do pacote aprovado: (a) pergunta cognitiva central; (b) ritmo e temperamento; (c) modo `reportagem` vs `veredito` vs `resposta`; (d) 2–4 comportamentos positivos; (e) proibições de alucinação; (f) âncoras aprovadas apenas como referência, sem reproduzir falas. Fornecer `persona_id/version/hash`, a lista ordenada de seções efetivamente enviadas, e instrução de **escrever informação primeiro, interpretar depois**. Não colar todos os arquivos históricos redundantes como instruções com igual prioridade. Não trocar/encurtar DNA de maneira a perder decisão sem validação setorial.

**Prova:** teste A/B com **o mesmo dossiê de fontes** e mesmo modelo/limite, variando apenas método de montagem aprovado, com anotação humana de identidade (Carranca: ironia seca e perguntas técnicas, elogio sem ceticismo compulsório, correção respeitosa; Beto: calor e repertório quando útil; Nina: curiosidade e crítica equilibrada). **Não medir caráter pela contagem de bordões**.

### A05 — Prompt/contexto volumoso e saída curta, sem prioridade visível [ENGENHARIA/ORQUESTRAÇÃO; sinal verificado, causa pendente]

**Problema:** o checkpoint do ciclo anterior registra prompt montado de **133.486 caracteres**, estimativa de dezenas de milhares de tokens, para um artigo sobre atualização relativamente breve. Isso é **um sinal de risco**, não medição da chamada real. Em paralelo, o texto visto é curto e repetitivo. É necessário auditar **relação entre tamanho da entrada, requisitos de cobertura, max_output_tokens/saída real, truncamento, ordem do prompt, instruções conflitantes e orçamento de pesquisa**.

**Correção:** empregar contexto hierarquizado `governance_core → role_policy → persona_core → editorial_brief → evidence_by_claim → output_contract`; referências maiores recuperáveis com hashes, não despejo irrestrito. Identificar e remover avisos duplicados na parte destinada à escrita. Registrar contagem real de tokens de entrada/saída se o conector reportar, quantidade de texto confiável e não confiável, orçamento para seções, resultado de truncamento e comprimento entregue. Não aumentar custo automaticamente; priorizar densidade e qualidade do contexto. Estabelecer limite de extensão por gênero e profundidade **ajustável pelo diretor**, não teto rígido de uma nota para reportagem de múltiplas páginas.

**Prova:** mesmo pacote factual gera texto mais substancial, com cobertura de cada ponto; métricas mostram ausência de corte e não duplicação de regras, sem elevar custo desnecessariamente.

### A06 — Incerteza correta virou linguagem defensiva repetitiva [ESTILO/GATE; OBSERVADA]

**Problema:** existem várias versões do mesmo aviso: publicação oficial, confirmação do anúncio, ausência de teste próprio/independente, necessidade de não extrapolar. A postura ética foi convertida em **refrão de autocontenção**, anulando ritmo e personalidade.

**Correção:** política de **incerteza localizada e proporcional**:
1. atribuir afirmações oficiais junto ao respectivo fato (“segundo a publicadora”);
2. uma seção curta **“O que ainda precisa ser verificado”** apenas quando material;
3. não repetir a mesma ressalva em cada parágrafo nem exibir internamente `no_test` no corpo;
4. o jornalista explica primeiro o que é conhecido; quando não há prova de qualidade, evita recomendação/nota em vez de repetir “não sabemos”;
5. um subeditor de estilo identifica redundância **sem apagar limites epistêmicos**.

**Prova:** cada alegação material continua verificável; avisos repetidos são eliminados; não surgem afirmações alheias às fontes.

### A07 — Critério de revisão concentra-se em bloqueio, sem ciclo de correção da matéria [REDATOR/REVISOR/ORQUESTRAÇÃO; OBSERVADA na saída]

**Problema:** as capturas relatam **seis achados (1 bloqueante, 5 polimentos)** e “nenhuma correção foi aplicada”, com duas chamadas apenas: rascunho + revisão. O bloqueio de publicação **funciona** e deve ser mantido. Mas falta **circuito de correção supervisionado**, de modo que uma matéria reprovada não seja confundida com produto editorial entregue.

**Correção:** ao receber `revise`/`hold`:
- armazenar `review_verdict` com hash da revisão, severidade, trechos, `evidence_ids`, texto de correção sugerida e indicação **corrigível com fontes existentes vs exige nova pesquisa**;
- retornar **uma revisão controlada** ao mesmo jornalista com feedback estruturado, versão do DNA e evidências preservadas; se depender de fatos, pesquisa via Motor antes de reescrever;
- refazer checagem factual e revisão editorial **para cada novo hash**; manter gate humano final e bloqueio de publicação; cap de tentativas e de custo aprovado **antes** de chamar o provedor;
- quando não houver nova chamada autorizada, **guardar como pendente**, mas não promover o rascunho reprovado à aparência de matéria completa.

**Prova:** um erro de atribuição de fonte introduz status `revise`; ciclo de correção substitui a citação ou remove claim, registra revisão e volta ao Revisor; `hold` não vira publicação e o texto anterior permanece auditável.

### A08 — Etapas internas vazam para as páginas de leitura [DIAGRAMAÇÃO/PRODUTO; OBSERVADA]

**Problema:** edição de 10 páginas tem extensas páginas de expediente, “primeira reportagem em revisão”, provenance, parecer do Revisor e alertas repetidos. A própria reportagem visível ocupa cerca de **duas páginas curtas**; páginas 5, 6 e 7 repetem título, assinatura/status e aviso. A chamada de capa parece uma **reportagem**, porém a página administrativa descreve uma **prévia bloqueada**. A culpa não é de Carranca e os metadados são úteis à fábrica.

**Correção:** **dois modos de renderização:**
- `editorial_debug_preview`: mostra proveniência, etapa, apontamentos do Revisor, trilha auditável e gate, **fora da área principal da revista** em painel/aba administrativa;
- `reader_preview`/edição revista: capa, sumário, reportagem completa, boxes, imagens pertinentes, assinatura e retrato, créditos/sumário; **quando não aprovada, watermark discreto “prévia privada” sem repetir alerta em toda página**, sem publicar;
- título completo no início e cabeçalho de continuação discreto, não o mesmo título gigante a cada página;
- a paginação é **derivada do volume editorial real**, não preenchimento de páginas administrativas para chegar a dez;
- o leitor deve manter imersão móvel e menu já definidos pelo Bloco 03; soluções novas passam pela autoridade do Bloco 03.

**Prova:** prévia privada mantém bloqueio e controles consultáveis, mas a área principal não substitui conteúdo por metadados; páginas de matéria se expandem conforme o texto e as figuras autorizadas.

### A09 — Identidade visual aprovada não aparece na montagem [ATIVOS/UI; OBSERVADA + existência verificada]

**Problema:** não se vê foto/avatar aprovado do Carranca, embora os **três PNGs do Protótipo A** estejam versionados na [PR #14](https://github.com/Saaimingo/Revista_Gamer/pull/14), **branch separada**. O repositório da prévia não incorporou automaticamente essa mídia e não se pode exigir que o redator textual cole uma imagem no artigo.

**Correção:** contrato de UI `persona_visual_ref` ou `asset_id` com `persona_id`, arquivo/hash, licença/status, tipos (avatar, retrato, referência), tamanho/alt e destino de exibição (assinatura, coluna, expediente). Pipeline de **montagem** e Bloco 05 resolvem assets de origem aprovada, sem regenerar rosto e sem se apropriar de qualquer arte externa. Validar se PR #14 foi disponibilizada ao worktree local da edição; **não efetuar merge por inferência**.

**Prova:** avatar do Carranca aparece na assinatura/abertura onde previsto; bate checksum do PNG aprovado; Beto e Nina também têm referências corretas com seu grau de preservação original. A imagem artística fictícia de Gothic **não substitui** a foto da persona nem uma captura oficial do jogo.

### A10 — Checagem de fontes confunde “origem do Captador” com “fonte citável de reportagem” [PROVENIÊNCIA/QA; OBSERVADA + causa pendente]

**Problema:** página 8 descreve a Gematsu como origem da pauta, **não usada como evidência**, enquanto página 7 ainda lista Gematsu entre fontes e página 8 diz que o Revisor **bloqueou citá-la**. Isso é inconsistência entre `captured_from`, `actually_read`, `used_as_evidence`, `cited_in_article` e `approved_for_publication`. Não concluir se foi erro de modelo ou transformação de dados sem examinar registros.

**Correção:** estados e campos distintos `discovery_source`, `fulltext_accessed`, `evidence_claim_ids`, `evidence_consumed_by_writer`, `cited_by_writer`, `review_approval`. A seção “Fontes consultadas” deve conter fontes realmente abertas e usadas na apuração, com anotação sobre dependência entre fontes. A origem da pauta fica na trilha interna e, quando útil, pode ser creditada como **origem**, nunca promovida automaticamente a “verificação independente”. O Revisor dá erro objetivo com `claim_id`, `source_id` e revisão afetada.

**Prova:** fixture com um agregador coletado mas **não consultado** na escrita; ele não aparece como fonte da matéria nem gera contradição com a página de proveniência. Fonte lida e citada tem prova de consulta real.

### A11 — Faltou exigência explícita de “destrinchar o objeto” no gate comum [REDACÃO/ESPECIFICAÇÃO; comprovado no contraste dos artefatos]

**Problema:** o Bloco 02 documentou antes [duas dimensões narrativas](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/continuidade-checkpoint-2026-10-24/docs/personagens/continuidade/DIRETRIZ-REPORTAGEM-APURACAO-E-VEREDITO-2026-10-24.md): **reportagem factual profunda e conclusão pessoal**. Entretanto, a especificação curta do `persona_writer` atual está centralizada em rastreabilidade, não em uma **cobertura estruturada de especificações, novidades, diferenças, imagens e contexto**. É possível “passar no schema” com texto curto, prudente e incompleto.

**Correção:** o Bloco 04/Fundador cria critério transversal de **completude por pauta**: `required_topics`, `topic_evidence_refs`, `comparison_targets`, `proposed_visuals`, `open_questions`, `genre`, `expected_depth`. O redator precisa cobrir ou justificar a ausência de cada tópico. Se não há material, brief retorna pesquisa ou **escopo editorial reduzido explicitamente**, nunca texto “especial completo” sem substância. Bloco 02 assegura que os três possam investigar com vozes distintas; Codex homologa no Motor.

**Prova:** para CPU, partes e benchmarks com método; para jogo de luta, elenco/mecânicas/história e novidades; para mod, dependências/autoria/mudanças/limites. Em todos: opinião só depois/com base no que foi explicado.

### A12 — Testes de contrato/hash foram confundidos com provas de qualidade [VALIDAÇÃO/STATUS; verificado em documentação]

**Problema:** fixture E18 “offline_contract_binding_only” usa `OFFLINE_BINDING_SENTINEL`, garante consistência de referências e declara `not_executed` para T01–T16. Testes de schema, executor e responsividade são importantes, mas **não provam personalidade reconhecível nem reportagem aprofundada**. O diretor já percebeu problemas de tom nos poucos ensaios anteriores; estes resultados precisam virar avaliações formais do trio e não ficar como “agentes prontos”.

**Correção:** instituir **dois eixos obrigatórios e independentes**:
- `P — PERSONA`: Carranca deve ser crítico justo, irônico sem agressividade, técnico sem jargão vazio e capaz de elogiar/corrigir; Beto anfitrião adulto com entusiasmo e repertório útil; Nina investigadora curiosa e emocionalmente equilibrada;
- `J — JORNALISMO`: apresentação de partes/mecânicas, novidade, comparação, atribuição, metodologia, fontes, lacunas e conclusão proporcional.

Usar [matriz Carranca T01–T16](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/ranzinza-dna-editorial-v01/docs/personagens/RANZINZA-MATRIZ-VALIDACAO-v0.1.md), [matriz Beto T01–T16](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/gamer-dna-v02/docs/personagens/GAMER-MATRIZ-DE-TESTES-v0.2.md) e [matriz Nina T01–T16](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/gamer-dna-v02/docs/personagens/NINA-PRISMA-MATRIZ-DE-TESTES-v1.0.md). Não repetir texto de audição como saída do teste; usar evidência nova e fontes controladas. **Se P passa mas J falha, resultado é falha editorial; e vice-versa.** Nenhum critério de pontuação/homologação foi aprovado aqui.

## 3. Enquadramento justo das responsabilidades

**Bloco 02 (este parecer):** cabe a nós **identidade, modos narrativos e exemplos**, já documentados e criativamente aprovados. Falha nossa de handoff possível: não demonstramos por teste real a diferença entre tom de opinião e jornalismo descritivo; os contratos existem mas a integração funcional ainda precisa provar essa diferença. A correção proposta **não muda a pessoa**: dá regras de aplicação por gênero e passa prova em P/J.

**Bloco Fundador:** responsável por traduzir o requisito de profundidade do diretor em política transversal, decidir qualidade mínima, aprovar prioridades, encaminhar implementação e cobrar evidência por etapa. Não declarar resultado qualitativo homologado por haver arquivo ou hash.

**Bloco 04 / Curadoria:** responsável por gênero da matéria, planejamento de perguntas, cobertura mínima, atribuição, classificação de fontes, redação e revisão, inclusive quando não há testes independentes. Pauta sobre anúncio não é benchmark.

**Codex/Engenharia:** responsável por comprovar o que foi **efetivamente executado**: fonte coletada → evidência → brief → persona/version/hash → prompt enviado → resposta bruta → achados → revisão corrigida → layout. Possível falha **de integração** ao dar ênfase excessiva a não inventar, sem checklist de profundidade; **não está comprovado um bug exato de código nem que o Codex deixou de carregar o DNA**. Manter trilha de artefatos, contexto hierarquizado, prompts eficientes, idempotência e gates de custo/segurança.

**Bloco 03 / Layout:** reserva área e comportamento do leitor para matéria e retrato, separa painel operacional da revista e evita múltiplas páginas de status. Não lhe cabe “corrigir” o jornalismo inventando texto.

**Bloco 05 / Mídias:** estabelece origem, créditos/licença, identidade visual original e uso editorial de fotos, artes e diagramas. Protege PNGs mestres e não promove ilustrações geradas como captura real.

**Modelo (GPT-6 Luna no teste):** o resultado observado é aquém do esperado, mas **não é válido atribuir a falha ao modelo isoladamente** sem prompt bruto, brief e evidências. Mesmo com modelo forte, briefing pobre ou regras conflitantes produzem texto fraco; comparar controladamente.

## 4. Plano de reparo recomendado ao Fundador (para transformar em missão do Codex)

**P0 — Diagnóstico reproduzível, sem nova chamada LLM**
1. Exportar para área **privada** os registros saneados da execução de 29/10: `persona_sources_manifest`, versões/hashes, prompt final das duas etapas, ordem de seções, ID de modelo/esforço, limites e tokens quando medidos, `draft` integral, `review` integral com **1 bloqueio + 5 polimentos**, `evidence_packet` por fonte e status de consulta, matéria que foi renderizada, e controle de aprovação. **Sem OAuth, tokens, dados privados ou publicação em Issue.**
2. Reconstruir cadeia de proveniência de Gematsu/THQ Nordic/RPG Site e verificar motivo exato do bloqueio. Documentar qual etapa promoveu a citação.
3. Confirmar o corpo, modo e `persona_id=ranzinza` efetivamente recebidos pela inferência; comparar a prompt enviada com a versão aprovada, sem exigir copiar 19 arquivos inteiros.
4. Verificar `genre`, `reason_for_assignment` e tópicos previstos. Conferir se 133.486 caracteres eram da preparação ou da chamada real, se houve corte e qual foi o limite de resposta.

**P1 — Correções de contrato e fluxo, inicialmente OFFLINE**
5. Governança/Bloco 04 define gêneros e checklist `required_coverage`; Engenharia valida o pré-editor/roteamento por pauta; não mudar DNA.
6. Curar a etapa de pesquisa por **pergunta editorial/claim** e gerar dossier com fontes oficiais, independentes, comunidade e status. Definir protocolo de retorno à pesquisa e como suspender só o veredito sem matar a notícia.
7. Compactar e hierarquizar instruções de persona mantendo proveniência e hash; exigir modos `reportagem/veredito/resposta`, cobertura do objeto, e restrições factuais **sem redundância defensiva**.
8. Revisão devolve `findings` acionáveis por claim/hash; pipeline suporta uma correção estruturada e nova checagem quando houver autorização, sem replay de efeito externo ou SIWC incerto.
9. UI separa `reader_preview` e `editorial_debug`, com retrato/assinatura do jornalista a partir de assets approved-by-ID, sem mesclar branch por conta própria.

**P2 — Prova operacional controlada, somente com autorização da direção**
10. Executar **pauta real curta e pauta profunda** para cada persona, com pacote verificável e gênero apropriado; primeiro offline com fixtures, depois LLM real se autorizado, sem retry automático e com orçamento máximo antecipado.
11. Registrar **dois pareceres diferentes P e J** por saída, cada um com exemplos concretos e falhas bloqueantes; manter seções e número de páginas flexíveis. Para Carranca, incluir elogio justo e correção; Beto, explicação de mecânicas/personagens e opinião; Nina, investigação de mod/indie e limite de evidência.
12. Somente após **aprovação humana** e evidência de melhora refletir a matéria no leitor, mantendo restrições de direitos, fontes e governança.

### Critérios objetivos de aceite propostos (a ratificar)

- **Zero** inventos de benchmark/gameplay/entrevista/URL/claim e **zero** citações sem origem auditável; falha bloqueia independentemente do estilo.
- **Todos os tópicos essenciais do briefing** devem ter explicação factual sustentada ou lacuna explicitamente justificada; ausência de análise independente impede **veredito específico**, não notícia explicativa.
- `persona_id/version/hash` reproduzíveis; saídas reconhecíveis **sem exigir bordão**; uma persona não absorve estilo das demais.
- Revisor lista **todos** os problemas com severidade, hash, evidência e correção; `revise/hold` preserva bloqueio e não aparece como artigo final liberado.
- Captador, fontes lidas, fontes citadas e fontes aprovadas **não se confundem**; uma mesma incerteza não vira refrão textual.
- Prévia da revista reserva sua área majoritariamente para **conteúdo jornalístico**, com imagens informativas autorizadas e assinatura visual correta; avisos operacionais permanecem acessíveis em interface de edição.
- Avaliação P/J e testes de regressão documentados; qualquer percentagem/cota deve vir de **medição real do provedor**, não estimativa por caracteres.

## 5. Referências primárias de consulta

1. [Checkpoint do Codex para retomada da primeira edição, 29/10](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/engenharia/REVISTA-BACK-RETOMADA-PRIMEIRA-EDICAO-2026-10-29.md).
2. [Coleta 29/10 18h40, pauta *Gothic Remake*](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/coletor/2026-10-29-1840.md).
3. [Leitor piloto e documentação](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/README.md) e [QA visual](https://github.com/Saaimingo/Revista_Gamer/blob/codex/revista-back-primeira-edicao-20261029/docs/visual/prototipos/revista-back-leitor-piloto/design-qa.md). **A branch exibe checkpoint anterior ao ensaio das capturas; não deve ser confundida com o resultado final local.**
4. [Catálogo de papéis (persona_writer/assignment_editor/reviewer)](https://github.com/Saaimingo/Revista_Gamer/blob/codex/eng-codex-011-live-factory/motor_editorial/agent_roles.json).
5. [Execução SIWC, montagem de instruções e verificação do hash de persona](https://github.com/Saaimingo/Revista_Gamer/blob/codex/eng-codex-011-live-factory/motor_editorial/agent_siwc.py).
6. [Teste E18 de vinculação, sem prova real de estilo](https://github.com/Saaimingo/Revista_Gamer/blob/codex/eng-codex-011-live-factory/motor_editorial/tests/test_persona_trials_offline.py) e [fixture com `not_executed`](https://github.com/Saaimingo/Revista_Gamer/blob/codex/eng-codex-011-live-factory/motor_editorial/tests/fixtures/persona_trials_offline_v1.json).
7. [Pacote canônico Arlindo Carranca, PR #13](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/ranzinza-dna-editorial-v01/docs/personagens/RANZINZA-PACOTE-OPERACIONAL-CONSOLIDADO-v1.0.md); [PNGs originais, PR #14](https://github.com/Saaimingo/Revista_Gamer/pull/14).
8. [Pacote do trio e testes Beto/Nina, PR #19](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/gamer-dna-v02/docs/personagens/ENTREGA-TRIO-PERSONAS-BLOCO02-2026-10-24.md) e [diretriz de reportagem profunda, PR #27](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/continuidade-checkpoint-2026-10-24/docs/personagens/continuidade/DIRETRIZ-REPORTAGEM-APURACAO-E-VEREDITO-2026-10-24.md).

## 6. Pedido formal ao Fundador

**Transformar este diagnóstico em especificação para o Codex**, com subtarefas de apuração, atribuição de pauta, compactação de persona, avaliação P/J, ciclo controlado de revisão, estado de fontes e integração dos retratos ao leitor. **Não** pedir ao Bloco 02 para “reescrever Carranca”, nem afirmar falha específica de código sem logs.

**Prioridade sugerida:** P0 (obter evidências/identificar causa) **antes** de P1 (mudanças sem novo LLM), **antes** de P2 (ensaio real autorizado). Tratar o piloto como **reprovado editorialmente/útil tecnicamente**, preservando o bloqueio de publicação como acerto de segurança. Não executar chamadas reais, merge ou deploy com base apenas neste parecer.

**Encerramento:** os três jornalistas continuam **CRIATIVAMENTE APROVADOS**. O que está sob teste é a **fidelidade da implementação e da investigação**. Este parecer solicita correção do sistema, não mudança involuntária da personalidade.
