# Design QA — leitor piloto da Revista Back

**Data:** 29/10/2026
**Final result:** passed

## Alvos visuais e evidências

- **Referência de celular e menu:** `C:\Users\saimi\Downloads\Revista_BACK_B03_Mobile_Imersivo_2026-10-27.zip`, capturas `mobile-390-menu.png` e `mobile-390-editorial.png`, ambas 390×844 pixels. A interação imersiva móvel é a referência aprovada registrada para esta retomada; a captura editorial serve para a linguagem de página, não para o conteúdo da nova pauta.
- **Referência de capa:** `C:\Users\saimi\Downloads\Revista_BACK_Bloco03_Cinco_Modelos_Editorais.zip`, captura `preview-mobile-capa.png` (390×844). O pacote se identifica como proposta; a regra de composição de capa foi registrada como decisão da Direção. A arte de referência não foi copiada.
- **Referência geral de telas largas:** o mesmo pacote inclui `preview-1440.png`. É uma proposta editorial e uma referência de paleta/composição; seu conteúdo e estado não são equivalentes ao spread atual.
- **Implementação local:** `http://127.0.0.1:8765/`, servida pelo Edge via CDP. A aba foi deixada no desktop, na capa.
- **Capturas da implementação** (`deviceScaleFactor=1`):

  | Viewport CSS | Estado | Captura local |
  | --- | --- | --- |
  | 390×844 | Capa, abertura, menu aberto e rolagem | `%TEMP%\revista-back-final-mobile-cover.png`, `%TEMP%\revista-back-final-mobile-article.png`, `%TEMP%\revista-back-final-mobile-menu.png`, `%TEMP%\revista-back-final-mobile-scroll.png` |
  | 768×1024 | Capa e menu aberto | `%TEMP%\revista-back-final-tablet-portrait-cover.png`, `%TEMP%\revista-back-final-tablet-portrait-menu.png` |
  | 1024×768 | Capa e spread | `%TEMP%\revista-back-final-tablet-landscape-cover.png`, `%TEMP%\revista-back-final-tablet-landscape-spread.png` |
  | 1366×768 | Capa e spread | `%TEMP%\revista-back-final-notebook-cover.png`, `%TEMP%\revista-back-final-notebook-spread.png` |
  | 1440×900 | Capa e spread | `%TEMP%\revista-back-final-desktop-cover.png`, `%TEMP%\revista-back-final-desktop-spread.png` |
- **Comparações lado a lado:** `%TEMP%\revista-back-cover-compare-final.png`, `revista-back-menu-compare-final.png` e `revista-back-article-compare-final.png`. Cada par móvel foi normalizado a 390×844 por imagem, `deviceScaleFactor=1`, sem moldura ou chrome de navegador. Os dois menus estavam abertos; a capa estava na capa; a página de abertura estava no estado de leitura. O conteúdo editorial da referência e o da pauta são diferentes, então a comparação de página avalia hierarquia e composição, não correspondência literal do texto.
- Capturas adicionais de implementação: 768×1024, 1024×768, 1366×768 e 1440×900, todas em `deviceScaleFactor=1`. As imagens de referência e comparações permanecem em Downloads/Temp e não foram incluídas na branch.

## Revisão das superfícies visuais

- **Tipografia:** títulos usam sans serif pesada e contraste de tamanho semelhante à referência. O título de abertura no celular foi aumentado para 26–32px depois da primeira comparação, preservando a quebra legível do título real. Texto auxiliar continua menor e com alto contraste. O seletor de fonte permite ampliar o conteúdo.
- **Espaçamento e ritmo:** capa centrada nas telas de tablet, notebook e desktop; leitura em página única na orientação estreita e spread de duas páginas em telas largas. O menu móvel ocupa a largura total. Em rolagem contínua, a faixa fixa contém somente o botão hambúrguer e separa a área de leitura para que o controle não cubra texto.
- **Cores e tokens:** fundo escuro, texto claro e acentos magenta seguem a referência visual. Os cartões de status e fontes usam fundos escuros e bordas legíveis; o tema claro continua selecionável no menu.
- **Imagens:** arte central é uma ilustração raster original gerada para este piloto, com `alt` e legenda que deixam explícito que não é arte oficial nem captura do jogo. Nenhuma arte dos arquivos Bloco 03 foi reutilizada.
- **Texto e estado editorial:** a capa e a abertura identificam a pauta, atribuem a classificação ao Captador e dizem que o resumo ainda não é reportagem. O gate de aprovação humana e o estado de prévia privada permanecem visíveis.
- **Navegação e responsividade:** hambúrguer presente nas cinco dimensões. Menu aberto, troca para rolagem, controles da edição e leitura em spread foram vistos em capturas reais do navegador. A largura total do documento foi igual à viewport em todas as capturas; não houve overflow horizontal. O CDP não registrou exceções de runtime.

## Histórico das correções P0/P1/P2

1. **Primeira comparação — P2:** havia uma barra permanente de controles e o menu móvel ocupava apenas 90% da tela; páginas internas também ainda estavam claras em relação à identidade escura do Bloco 03. **Correção:** recolhi as opções no único menu hambúrguer global, fiz o drawer móvel ocupar a tela toda e alinhei as páginas internas à paleta escura/magenta. **Pós-correção:** `%TEMP%\revista-back-menu-compare-final.png` e `revista-back-article-compare-final.png`, ambas em 390×844.
2. **Inspeção do modo contínuo — P2:** o hambúrguer fixo encobria palavras no topo durante a rolagem. **Correção:** adicionei uma faixa superior sem outros controles, reservei o espaço no início da leitura e descontei esse espaço ao navegar por âncoras do sumário. **Pós-correção:** `%TEMP%\revista-back-final-mobile-scroll.png`, 390×844; o texto aparece abaixo da faixa sem ficar sob o botão.
3. **Tipografia e menu móvel — P2:** título de abertura pequeno e drawer estreito em 390px. **Correção:** aumentei a escala do título e ampliei o drawer para 100vw. **Pós-correção:** `%TEMP%\revista-back-article-compare-final.png` e `revista-back-final-mobile-menu.png`, 390×844.

## Resultado e limites

Não há achados visuais P0/P1/P2 em aberto na prévia local. A comparação cobre a composição visual da capa, a abertura de pauta, o menu e a rolagem móvel, além da responsividade em cinco viewports.

P3/follow-up: confirmar o comportamento em aparelhos físicos e validar tela cheia com gesto real; concluir a identidade com a Direção usando os materiais de arte licenciados para publicação; substituir a pauta por reportagem completa aprovada; integrar Beto e Nina após a matéria de Carranca. A arte gerada nesta prévia não substitui a seleção editorial de imagens. Esses limites impedem chamar a prévia de edição concluída ou publicável, mas não bloqueiam o aceite visual e responsivo deste protótipo.
