# Revista Gamer — Bloco 03 · Estrutura Vazia v0.3 revisada

**Estado: LABORATÓRIO EXPERIMENTAL / NÃO APROVADO.** Não é publicação, identidade visual congelada, leitor de produção ou ordem ao Codex.

## Para o fundador abrir e testar

1. Baixar/clonar o repositório: https://github.com/Saaimingo/Revista_Gamer
2. Abrir localmente o arquivo **docs/visual/prototipos/estrutura-vazia-v03-revisada/index.html** no Chrome, Edge ou Firefox.
3. Alternar os botões **Folhear** e **Contínua**, no cabeçalho. No modo Folhear, use Próxima/Anterior ou as setas do teclado.
4. Abrir **Preferências de leitura** e ativar **Matéria extensa**, **Fonte 150%** e, opcionalmente, espaçamento ampliado.
5. Em 1024×768 (janela de notebook), chegar à última face. Inspecionar se todo o texto pode ser lido e se a **contracapa aparece sozinha**, inclusive após expansão. Repetir num celular.
6. Abrir **Sumário** para verificar posições e navegar; redimensionar a janela ou girar o aparelho, observando a recomposição.

**O HTML é autocontido:** não usa bibliotecas, fontes, fotografias ou APIs remotas. Basta abrir o arquivo; não há necessidade de servidor ou conta. O arquivo também pode ser visualizado e baixado isoladamente pelo GitHub.

## Correções incorporadas após o parecer do fundador

**F1 — Integridade da reportagem:** a distribuição mede a capacidade da face renderizada, segmenta parágrafos extensos em trechos contínuos, preserva figuras com legendas, citações e tabelas como componentes e evita esconder módulos grandes (com rolagem acessível na própria área quando necessário).

**F2 — Livro com capa e contracapa externas:** a montagem inclui um verso editorial neutro quando a expansão gera contagem ímpar; assim mantém coerência frente/verso e contracapa isolada. Atualiza numeração e navegação.

**Conforto no celular:** preferências recolhíveis, topo mais compacto, leitura em coluna única e eliminação da barra flutuante que poderia sobrepor texto no modo Contínua.

**Apresentação no desktop:** escala da capa isolada ligeiramente ampliada, ainda sujeita à escolha do diretor.

## Entregas deste diretório

- **index.html:** protótipo interativo real e executável no navegador.
- **LEIA-ME.md:** este roteiro e limites.
- **resultado-testes.json:** resultados reportados no pacote v0.3 revisado e checagens adicionais.
- **tests/test_integridade.py:** script opcional e reproduzível com Playwright para verificar F1/F2, texto e modo contínuo.

## O que os testes dizem e o que NÃO dizem

O pacote original registrou ensaios em **1440×960, 1024×768, 800×1100, 390×844, 360×740 e 320×700**, no cenário de matéria extensa com 150% de fonte, sem detectar blocos de texto ocultos, perda de texto, erros JavaScript ou contracapa emparelhada nos casos exercitados. Checagens adicionais foram executadas para 1024×768 e 390×844 com o código local idêntico ao publicado.

Não houve homologação em aparelhos físicos, acessibilidade completa com leitor de tela, desempenho em dispositivos fracos ou paginação com reportagens reais. A preservação de posição de leitura utiliza âncoras aproximadas. **O resultado é uma prova de conceito de casca editorial, não o produto final.**

## Escopo e responsabilidades

- **Bloco 03:** layout, modos de leitura, espaços, ergonomia e transições.
- **Bloco 02:** personagens/assinaturas e representação autorizada.
- **Bloco 04:** texto editorial e verificação de conteúdo.
- **Bloco 05:** seleção e direitos de imagens e mídias.
- **Bloco 06:** publicidade, afiliação e divulgação.
- **Diretor + fundador:** validação conceitual e autorização de próximos passos.

**Parecer de origem:** [Parecer provisório do fundador sobre v0.3](../../analises-fundador/PARECER-PROVISORIO-2026-10-19-ESTRUTURA-VAZIA-V03.md).

## Sobre as prévias PNG e o ZIP

O pacote de referência local **Revista_Gamer_Bloco03_v03_revisada.zip** também contém quatro imagens PNG de capturas e documentos de origem. **O HTML e os materiais textuais de avaliação estão agora no GitHub; o ZIP e os PNGs binários não foram enviados neste registro.** Não declarar esses binários publicados. O fundador já pode baixar/clonar este repositório e reproduzir a visualização abrindo index.html.

**Próxima etapa:** avaliação com o diretor e fundador, sem aprovação antecipada de marca, tipografia, número de faces, interface final ou execução por engenharia.
