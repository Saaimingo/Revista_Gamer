# Revista Back — Política editorial de atribuição, verificação e revisão por tipo de matéria

**Data da decisão:** 02/11/2026. **Origem:** decisão explícita da Direção em conversa com o Fundador 6. **Status:** DIRETRIZ EDITORIAL APROVADA. **Setor responsável:** Redação/Bloco 04. **Implementação na fábrica:** depende de adequação contratual e testes offline; esta diretriz, por si só, não aprova novas chamadas SIWC, publicação nem mudança dos DNAs.

## 1. Regra central da Direção

**Noticiar uma alegação não é afirmar que ela foi provada.** O jornalista pode informar que uma fabricante anunciou determinada capacidade, recurso, vantagem ou resultado, desde que **atribua corretamente a alegação** e deixe claro o que foi e o que não foi verificado. Não é necessário produzir ou localizar um teste independente para simplesmente noticiar um anúncio.

**O Revisor não deve bloquear automaticamente uma notícia porque ainda não há benchmarks ou validação independente publicados.** Deve bloquear ou pedir correção se o texto transforma a alegação em **conclusão comprovada da própria revista**, oculta contradição relevante, atribui incorretamente a informação, alega teste não realizado ou sugere certeza além das evidências.

A regra não significa que mencionar “segundo a fabricante” transfira toda responsabilidade editorial: verificar a origem/autenticidade da declaração, a formulação exata (“até”, “previsto”, “em configuração específica”), o estado do lançamento e os fatos contrários confiáveis já disponíveis. Uma alegação reconhecidamente falsa/enganosa não pode ser reproduzida acríticamente apenas por estar atribuída.

## 2. Produto anunciado, ainda não lançado

- Relatar “a fabricante anuncia/prevê/afirma que [recurso]” ou “segundo a ficha da fabricante, o produto terá/suportará até [capacidade]”, mantendo condições e ressalvas de origem.
- Se ainda não há teste independente disponível **nas fontes efetivamente consultadas**, informar isso em linguagem direta e curta quando relevante. Não escrever como fato que nenhum teste exista em lugar nenhum.
- Não inventar medição, compatibilidade comprovada, velocidade efetiva ou experiência de uso.
- Não exigir laudo, teste impossível ou documentação que talvez ainda não exista para viabilizar notícia factual sobre o anúncio.

## 3. Produto já lançado ou comercializado

- Procurar ficha técnica, documentação e, **quando o texto pretende avaliar desempenho/compatibilidade, ou quando houver evidência material conflitante**, testes ou análises públicas pertinentes.
- Se forem encontrados testes comparáveis, citar fonte, método, condições, limitações e conclusões de forma proporcional. A revista só afirma que algo está empiricamente validado quando a evidência suporta a conclusão.
- Se não forem encontrados, ainda é possível noticiar as alegações da fabricante, com esclarecimento curto e preciso do limite da apuração. **Não afirmar desempenho medido ou ganho comprovado**.
- Se fabricante disser “supera modelo anterior”, informar como alegação da fabricante; se faltarem benchmarks, registrar que **não foram localizados testes independentes nas fontes consultadas que comprovem tal ganho**.

## 4. Adequação do nível de evidência ao gênero editorial

| Tipo de matéria | O que o Revisor deve exigir |
|---|---|
| Notícia de anúncio | Autenticidade e correta atribuição da declaração, status anunciado/lançado, condições/limitações, nenhuma alegação inventada; ausência de benchmark pode ser explicitada sem bloqueio automático. |
| Notícia sobre produto lançado | Idem, e verificar especificações e provas independentes disponíveis quando relevantes; distinguir afirmação comercial de comprovação. |
| Análise / comparação | Argumentos e conclusões sustentados por dados adequados e comparáveis. Não concluir desempenho/custo-benefício com base somente no marketing. |
| Dossiê técnico / investigação | Investigar divergências relevantes, contexto, antecedentes, fontes e documentação; explicitar lacunas irresolúveis. Uma questão realmente impeditiva da tese não pode ser autoencerrada. |

**Regras invariantes:** precisão factual, citação de origem, transparência de incerteza, ausência de testes próprios fictícios, atenção a divergências relevantes e proibição de aprovação por aceite genérico de questões bloqueantes. Evitar pesquisa infinita sem hipótese verificável ou ganhos editoriais.

## 5. Exemplos aprovados de enquadramento (não são fact-check de modelos reais)

> Segundo a fabricante, o equipamento terá suporte a até 128 GB de RAM.

> A empresa afirma que o novo modelo supera a geração anterior. Nas fontes consultadas até o fechamento desta matéria, não encontramos benchmarks independentes que permitam confirmar esse ganho.

Se houver divergência relevante entre documentação do fabricante e de fornecedor de componentes, apresentar **ambos os documentos com atribuição clara**, deixando explícito o que difere e que a divergência **não prova automaticamente incompatibilidade**. Não transformar falta de teste em desculpa para omitir contradição material.

## 6. Critérios operacionais para o Revisor

1. **Qual é exatamente a afirmação?** Declaração atribuída, fato documental verificável ou conclusão independente da revista?
2. **A atribuição é correta?** Fonte autêntica, condições (inclusive “até”, SKU, versão, status e data) preservadas?
3. **Qual prova é proporcional à alegação?** Para a declaração “a fabricante anuncia”, bastam sua declaração verificável e contexto fiel; para “supera em X%”, exigir medição válida e comparável, ou reescrever como alegação de marketing.
4. **Há contradição material?** Apresentar com contexto, investigar quando possível, não forçar veredito inexistente.
5. **A pesquisa esgotou fontes relevantes proporcionais ao formato?** Ausência nas fontes consultadas é uma informação de escopo, não um fato universal.
6. **Qual ação editorial?** `accept` apenas se as afirmações estiverem corretamente enquadradas e sem bloqueios pendentes; `correct` para redação/atribuição indevida; `research` para dúvida **material e potencialmente resolúvel**; `blocked` para afirmação essencial sem suporte ou contradição não tratada. Não exigir teste ainda não disponível como condição universal para notícia de anúncio.

## 7. Aplicação ao ensaio TUXEDO

A matéria privada do ensaio `rb-5403393c6859c576e69b0f49` continua **rascunho NÃO APROVADO**, com questões do Revisor e estado técnico `uncertain`. Esta política **não retroage** a um aceite, não altera o histórico nem autoriza publicar ou executar inferências.

O título deve distinguir DDR5 da ficha TUXEDO e LPDDR5X da ficha Intel, se ambas sustentadas pelos documentos consultados. A ausência de testes e de lista de módulos deve ser **atribuída ao conjunto realmente consultado**, não tratada como inexistência universal. Contexto de geração anterior pode ser sugerido, mas a falta de benchmark público não impede, sozinha, uma notícia de anúncio factual.

## 8. Responsabilidade de documentação e implementação

- **Direção:** decidiu o princípio. Não precisa arbitrar cada caso ou selecionar manualmente cada documento.
- **Redação/Bloco 04:** manter a política, os gêneros editoriais e critérios aplicáveis claros.
- **Fundador:** transformar a decisão em contrato verificável para a fábrica e acompanhar qualidade/segurança.
- **Codex:** quando instruído, adequar roteamento/revisão e testes offline, com critérios auditáveis; **não** enfraquecer fail-closed, reescrever DNA sem decisão, nem executar novo teste Luna sem autorização expressa.

## 9. Esclarecimento adicional da Direção: jornalismo informativo, não laboratório universal

A Direção explicitou que o rigor NÃO significa explorar exaustivamente cada variável hipotética antes de publicar uma notícia ou comparação. A Revista Back informa o que os dados públicos efetivamente sustentam, cita a origem e **não promete que um resultado vale para toda configuração, ajuste ou cenário possível**.

- Um benchmark público relevante permite informar: “Nos testes publicados pelo veículo X, o processador A ficou à frente do B”. **Não** exige que a revista reproduza hardware, teste todas as memórias/BIOS, antecipe overclock ou investigue todas as combinações imagináveis.
- Condições de teste como GPU, resolução ou potência devem ser mencionadas **quando são conhecidas e mudam materialmente o sentido da comparação**, não como checklist universal obrigatório. Exemplo: se uma medição usa RTX 5090 e outra RTX 5070, não apresentá-las como prova isolada de superioridade entre processadores; pode-se noticiar o resultado como comparação dos dois conjuntos, deixando a diferença clara.
- Testes e números apresentados por um veículo idôneo podem ser relatados com atribuição e contexto suficiente, sem transformar sua notícia em auditoria laboratorial do estudo. Uma conclusão universal da própria revista exige suporte maior que o relato de uma medição específica.
- O Revisor procura **erro material real**, não exceções meramente possíveis. Não deve prolongar pesquisas indefinidamente, bloquear por variáveis hipotéticas ou exigir detalhe irrelevante ao que foi afirmado. Se uma comparação fundamentalmente inadequada sustenta a manchete, corrigir a manchete/conclusão, não exigir que o jornalista cubra o universo de configurações.
- O Coletor entrega fontes úteis e benchmarks encontrados; ausência de estudos é registrada com escopo. Não há meta de documentação exaustiva, apenas boa informação fundamentada e compreensível para o leitor.

**Princípio editorial reafirmado:** a técnica serve à informação; não aprisiona a notícia. Este esclarecimento complementa a D-019 e preserva atribuição, precisão e transparência. Não muda a autorização de operação ou o estado de matérias já ensaiadas.
