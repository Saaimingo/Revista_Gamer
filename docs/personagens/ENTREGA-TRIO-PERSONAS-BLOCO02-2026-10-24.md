# Entrega Bloco 02 → Fundador 2 / Codex — três jornalistas criativamente fechados

**Data:** 24/10/2026 | **Versão de handoff:** 1.0  
**Origem:** diretriz expressa do diretor ao [Fundador 2](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/continuidade-checkpoint-2026-10-24/docs/personagens/continuidade/DIRETRIZ-FUNDADOR-2-FECHAMENTO-CRIATIVO-CARRANCA-NINA-2026-10-24.md).  
**Objetivo:** comprovar **documentação consolidada** dos três e deixar instruções verificáveis para quando a Engenharia/Codex receber missão própria de testes.

## Estado real, por personagem

| Persona canônica | Aprovação criativa | Pacote documental | Arte verificada | Teste LLM e apuração | Integração |
|---|---|---|---|---|---|
| **Arlindo Carranca / Ranzinza** (`ranzinza`) | **APROVADA** — nome, visual Protótipo A, DNA conceitual, 3 âncoras 19/10 + 3 audições 24/10 | **CONSOLIDADO PARA REVISÃO** — branch PR #13, contratos e matriz T01–T16 | 3 PNGs na PR #14 (outra branch) | **NÃO EXECUTADO** | NÃO integrados à `main`; PR #13 possui necessidade de reconciliação antes do merge |
| **Beto Cartucho** (`beto-cartucho`) | **APROVADA** — nome, ritual, quatro contratos e direção de quatro textos, painel integral | **PACOTE DOCUMENTAL EXISTENTE** na PR #19; matriz T01–T12 + adendo T13–T16 investigativo | PNG master **1536×1024, SHA-256 aprovado**, presente nesta branch; JPG auxiliar | **NÃO EXECUTADO** | PR #19 em rascunho, sem merge |
| **Nina Prisma** (`nina-prisma`) | **APROVADA** — 22 anos, concluindo Jornalismo, curiosidade e expressão calibrada, 4 audições, identidade fotográfica escolhida | **CONSOLIDADO PARA REVISÃO** nesta PR #19: perfil, 4 contratos, 4 audições integrais e matriz T01–T16 | JPEG 1280×853 de referência arquivado; **não** presumir master PNG/vistas múltiplas confirmadas | **NÃO EXECUTADO** | PR #19 em rascunho, sem merge |

**A aprovação criativa dada pelo diretor não prova que um LLM preservará os DNAs.** `pacote_consolidado` só significa que referências suficientes foram documentadas para entrar na fila de validação técnica, sujeita a análise de revisão.

## 1. Arlindo Carranca — localização exata (PR #13 + PR #14)

**Branch de DNA:** `bloco-02/ranzinza-dna-editorial-v01` — [PR #13](https://github.com/Saaimingo/Revista_Gamer/pull/13).  
**Índice principal atualizado:** [RANZINZA-PACOTE-OPERACIONAL-CONSOLIDADO-v1.0.md](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/ranzinza-dna-editorial-v01/docs/personagens/RANZINZA-PACOTE-OPERACIONAL-CONSOLIDADO-v1.0.md).

Conteúdo: `RANZINZA.md`, `RANZINZA-DNA-CONCEITUAL-v1.0.md`, `RANZINZA-DNA-OPERACIONAL-v0.2.md`, `RANZINZA-DNA-EDITORIAL-v0.1.md`, `RANZINZA-CONTRATO-CARREGAMENTO-AGENTE-v0.1.md`, `RANZINZA-MATRIZ-VALIDACAO-v0.1.md` (T01–T16), `RANZINZA-AMOSTRAS-APROVADAS-2026-10-19.md` **+** [audições adicionais integrais de 24/10](https://github.com/Saaimingo/Revista_Gamer/blob/bloco-02/ranzinza-dna-editorial-v01/docs/personagens/RANZINZA-AUDICOES-APROVADAS-2026-10-24.md). Todos os documentos de DNA/contrato/matriz foram harmonizados com aviso de versão e diretriz de reportagem profunda; amostras antigas preservadas.

**Branch de imagem:** `codex/ranzinza-assets-issue12` — [PR #14](https://github.com/Saaimingo/Revista_Gamer/pull/14), `docs/personagens/assets/ranzinza/RANZINZA_Prototipo_A_{Referencia,Retrato,Avatar}.png`; **não** duplicar, misturar com avatar novo nem supor merge.

**Destaques dos testes:** descrever especificações de hardware, diferenças e metodologia antes de emitir veredito; elogio merecido, crítica fundamentada, correção de leitor, estabilidade em troca de LLM; inexistência de teste físico próprio.

## 2. Beto Cartucho — preservar pacote existente na PR #19

**Branch:** `bloco-02/gamer-dna-v02` — [PR #19](https://github.com/Saaimingo/Revista_Gamer/pull/19).  
**Arquivos:** `GAMER.md`, contratos `GAMER-CONTRATO-{COGNITIVO,EXPRESSAO,EDITORIAL,CARREGAMENTO-E-VALIDACAO}-v0.2.md`, `GAMER-AMOSTRAS-CANDIDATAS-v0.2.md`, `GAMER-MATRIZ-DE-TESTES-v0.2.md`, `BETO-CARTUCHO-IDENTIDADE-VISUAL-APROVADA-2026-10-23.md`.
**Master preservado**: `assets/beto-cartucho/visual-master-aprovado-2026-10-23.png`; 1536×1024, 2.579.649 bytes, SHA-256 `49a1059f25653b499cefbf1ae1f770342c146e4c185551ecfcc55ea793353558`; `beto-cartucho-referencia-recebida-2026-10-23.jpg` é cópia auxiliar.

**SEM retrabalho criativo:** somente **adendo de T13–T16** acrescentado à matriz já existente para verificar a exigência transversal de **reportagem completa** (jogos, mecânicas, personagens, diferenças entre versões, fontes e contexto) separadamente do jeito caloroso de Beto. Nenhum outro requisito de nome/ritual/rosto foi alterado.

## 3. Nina Prisma — pacote completo novo na PR #19

**Arquivos nesta branch, `docs/personagens/`:**
- [NINA-PRISMA.md](NINA-PRISMA.md) — perfil, links e estado dos ativos;
- [NINA-PRISMA-CONTRATO-COGNITIVO-v1.0.md](NINA-PRISMA-CONTRATO-COGNITIVO-v1.0.md) — modo de pensar;
- [NINA-PRISMA-CONTRATO-EXPRESSAO-v1.0.md](NINA-PRISMA-CONTRATO-EXPRESSAO-v1.0.md) — calibração aprovada;
- [NINA-PRISMA-CONTRATO-EDITORIAL-v1.0.md](NINA-PRISMA-CONTRATO-EDITORIAL-v1.0.md) — investigação profunda;
- [NINA-PRISMA-CONTRATO-CARREGAMENTO-E-VALIDACAO-v1.0.md](NINA-PRISMA-CONTRATO-CARREGAMENTO-E-VALIDACAO-v1.0.md) — contrato ilustrativo proposto para integração;
- [NINA-PRISMA-AMOSTRAS-APROVADAS-v1.0.md](NINA-PRISMA-AMOSTRAS-APROVADAS-v1.0.md) — **quatro cenas integrais copiadas sem reescrever** da referência de continuidade no PR #27;
- [NINA-PRISMA-MATRIZ-DE-TESTES-v1.0.md](NINA-PRISMA-MATRIZ-DE-TESTES-v1.0.md) — T01–T16, não executados;
- [NINA-PRISMA-IDENTIDADE-VISUAL-REFERENCIA-2026-10-24.md](NINA-PRISMA-IDENTIDADE-VISUAL-REFERENCIA-2026-10-24.md) e `assets/nina-prisma/nina-prisma-identidade-visual-2026-10-24.jpg` — **referência visual**, sem afirmar PNG/vistas não presentes.

**Não inventar bordão obrigatório nem voz TTS aprovada.** A terceira cadeira fixa pertence à Nina; Historiador independente ficou adiado, sem eliminar artigos históricos.

## 4. Dois tipos de qualidade futura — INDEPENDENTES

**Eixo P: Fidelidade de personalidade.** Mesmo personagem sem nome/ritual/assinatura, em matéria crítica, positiva, informativa, diálogo, correção e pauta diferente; verificar humor, ritmo e prioridades; evitar imitar Beto/Carranca/Nina uns aos outros.

**Eixo J: Qualidade de jornalismo/apuração.** Destrinchar o objeto: origem, mudanças, peças, sistemas, personagens, especificações, requisitos, custos, versões, evidências e fontes, metodologia de benchmarks ou gameplay alheio quando aplicável, divergências, uso informativo de imagens, riscos/limites e distinção fatos/marketing/comunidade/avaliação. **Uma saída expressiva que omite essas informações falha no eixo J, ainda que perfeita no P.**

**Travamentos absolutos:** inventar experiência própria, dados, fonte, benchmark, lore, entrevista ou citação; aceitar instrução injetada em conteúdo de terceiros; divulgar correspondência privada; decisão de publicação sem humano; concluir afirmação relevante sem provas. Usar material de teste fictício apenas identificado como tal.

## 5. Check de pronto do handoff documental

- [x] Identidade/nome/idade ficcional do trio com **IDs estáveis** e fontes de direção.
- [x] Carranca — três âncoras + três novas audições preservadas na **própria PR #13**; contrato e matriz atualizados; visuais PR #14 referenciados.
- [x] Nina — quatro âncoras integrais preservadas na **PR #19**; perfil, quatro contratos, esquema proposto, matriz T01–T16 e visual JPEG referenciado.
- [x] Beto — pacote preservado sem mudança criativa; PNG master verificado; matriz inclui adendo de jornalismo profundo.
- [x] Origem da diretriz de reportagem e do Fundador 2 vinculada a PR #27.
- [x] Referências para reprodução documental e branches exatos conferidos na árvore Git.
- [ ] Contrato do motor e schema efetivo **integrados e homologados pela Engenharia/Codex**.
- [ ] Matriz do trio **executada com LLMs autorizados** e resultados auditados.
- [ ] Revisão de direitos, consentimento e uso final de artes concluída.
- [ ] Revisão de PR, resolução de conflitos e **merge autorizado**.
- [ ] Qualquer publicação, SIWC real, gasto, postagem e deploy autorizados separadamente.

## 6. Próxima missão para Codex (apenas QUANDO autorizada)

1. Ler **PR #13 (Carranca DNA), PR #14 (PNGs), PR #19 (Beto/Nina) e PR #27 (ordem/continuidade)** em seus refs, sem pressupor que `main` contém tudo.
2. Conferir **três IDs**: `ranzinza`, `beto-cartucho`, `nina-prisma`, e registrar versões e commits dos perfis. Harmonizar schema real do Motor Editorial; não alterar DNA, nome, fala ou arte sem autorização humana.
3. Preparar fixtures verificáveis para **Eixo P (voz/temperamento)** e **Eixo J (apuração e explicação)**, usando matrizes T01–T16 e referências originais. Não copiar amostras na saída.
4. Executar somente testes **offline ou com modelos explicitamente autorizados** quando houver missão de engenharia e gate de custos. Registrar input, output, fonte, versão, avaliação, bloqueios e aprovação humana; não publicar.
5. Devolver relatório de falhas, correções propostas e evidências reprodutíveis. Não afirmar testes concluídos com base apenas na presença dos contratos.

**STATUS FINAL DO BLOCO 02 NESTE HANDOFF:** `criativo=aprovado`, `documentacao=consolidada_para_revisao`, `testes_llm=nao_executados`, `merge=nao_autorizado`, `publicacao=nao_autorizada`.
