# Revista Gamer — Estrutura Vazia v0.3 revisada

**Bloco 03 — Identidade Visual e Experiência de Leitura**  
**Data da publicação do laboratório:** 20/10/2026  
**Status:** PROTÓTIPO / SOB AVALIAÇÃO DO DIRETOR E FUNDADOR — NÃO APROVADO.

Este diretório contém **um protótipo navegável de verdade**, com texto meramente demonstrativo, slots vazios de imagens e publicidade e dois modos de leitura: **Folhear** e **Contínua**.

## Abrir imediatamente

**[index.html — abrir/baixar o laboratório](index.html)**. É um arquivo HTML autocontido; baixe-o e abra no navegador para executar os controles. O GitHub pode mostrar o código-fonte em vez de executar o HTML: nesse caso use **Download raw file** ou clone o repositório.

## O que o fundador pode conferir

**F1:** 1024×768, opção **Matéria extensa**, fonte **150%**, percorrer toda reportagem. A correção busca não esconder texto nem quebrar figuras e legendas.

**F2:** verificar que capa e contracapa ficam isoladas mesmo quando a contagem dinâmica exigiria um verso adicional.

**Ergonomia:** experimentar no celular os controles recolhíveis, leitura em coluna única, alteração de fonte, sumário e mudança entre Folhear/Contínua.

**Insumos de auditoria:**

- [LEIA-ME.md — instruções completas, limitações e histórico de mudanças](LEIA-ME.md)
- [resultado-testes.json — verificações registradas](resultado-testes.json)
- [tests/test_integridade.py — teste automatizado opcional de F1/F2 e coerência de texto](tests/test_integridade.py)
- [Parecer do fundador que motivou a revisão](../../analises-fundador/PARECER-PROVISORIO-2026-10-19-ESTRUTURA-VAZIA-V03.md)

## Execução do teste opcional

No terminal, a partir da pasta deste diretório:

1. Instalar Playwright: **python -m pip install playwright**
2. Instalar o navegador de teste: **python -m playwright install chromium**
3. Executar: **python tests/test_integridade.py**

Este teste é de apoio e não garante acessibilidade, desempenho ou comportamento em todos os dispositivos. O protótipo foi preparado sem imagens oficiais, fatos jornalísticos ou anunciantes. As capturas PNG e o ZIP originais da v0.3 revisada não acompanham este diretório no GitHub; não alegar upload dos binários.

**Próxima ação:** fundador e diretor revisarem o HTML e os resultados. Não acionar Codex nem tratar a estrutura como aprovada por inferência.
