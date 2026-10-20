# Arquivo de protótipos do Bloco 03

**Data:** 2026-10-17 | **Versão:** 0.1 | **Estado:** PROPOSTA — NÃO APROVADO.  
**Objetivo:** guardar **dois mocks de oito faces cada** para debate com diretor e Bloco Fundador, não para publicar uma edição.

- [Estudo comparativo, decisões e riscos](../estudos/ESTUDO-COMPARATIVO-DOIS-MOCKS-TEMATICOS-2026-10-17.md)
- [Mock A — Terror / Resident Evil: 8 faces](mock-a-terror/README.md)
- [Mock B — GTA VI / tema colorido: 8 faces](mock-b-gta/README.md)

## Referências visuais recebidas em 20/10/2026

Foi preparado um pacote local com **dois conjuntos de oito PNGs**, identificados nas próprias imagens como Mock 03 e Mock 04: [abrir o inventário e manifesto](referencias-chatgpt-2026-10-20/README.md). Ambos representam Resident Evil 9 / Requiem; não são o par documentado Mock A (terror) e Mock B (GTA VI), e não devem ser misturados nessas pastas.

**Estado: cópia local em branch de revisão; não enviada ao GitHub.** As imagens contêm marcas e elementos reconhecíveis de franquia. A decisão do Bloco 05 sobre exposição no repositório público continua pendente; hashes confirmam integridade da cópia, não licença. O pacote não é identidade aprovada nem material editorial/publicitário.

## Exemplo integrado do Chat Fundador — 20/10/2026

**[Abrir pasta e instruções da demonstração integrada](demonstracao-integrada-fundador-2026-10-20/README.md)** · **[HTML navegável](demonstracao-integrada-fundador-2026-10-20/index.html)**

Por solicitação expressa da direção, o fundador combinou **a arquitetura das capas dos dois mocks A/B** — marca grande centrada em cima, arte editorial dominante, chamadas laterais, patrocínio inferior apenas se houver — com a composição de miolo e controles do novo Estudo Visual 01. São **duas temáticas selecionáveis, oito faces por tema, e publicidade fictícia alternável**. Artes SVG próprias; não há PNGs dos jogos, matéria factual nem publicação. **Exemplo estético**, não substitui paginação dinâmica da v0.3. Antes de aprovação, Bloco 03 deve verificar funcionamento em navegador/dispositivos e discutir o design com a direção.

## Localização esperada dos 16 PNGs

Dentro de cada pasta, subdiretório `png/`, nomenclatura idêntica: `pagina-01.png` (capa), `pagina-02.png` a `pagina-07.png` (miolo), `pagina-08.png` (contracapa). Arquivos extras de apoio: `visao-geral.jpg` de cada mock e `manifesto.json` com dimensões, fontes locais e SHA-256.

**Estado de transferência:** os **documentos de texto foram registrados no GitHub**, mas **os 16 PNGs ainda não foram transferidos para ele nesta sessão**, por limitação do conector para arquivos binários originados localmente. A direção recebeu um pacote ZIP com as 16 imagens em suas pastas finais. Até que sejam enviados e validados por acesso direto, os links para PNGs não devem ser tratados como disponíveis no repositório.

## Uso restrito / riscos

Os nomes de revista, fotos, caricaturas, nomes comerciais, QR codes, perfis, avaliações, preços, cronologias e especificações técnicas apresentados são **ilustrações sintéticas e fictícias**, não matéria apurada, testes, patrocínios ou campanhas. A presença de franquias e marcas reconhecíveis **não significa licença**. Solicitar avaliação do Bloco 05 antes de divulgação externa. Arquivar não implica aprovação. A estrutura final, a edição real e os efeitos interativos ainda precisam ser debatidos e testados.

## Se for transferir os arquivos manualmente

1. Extrair o ZIP preservando a árvore de pastas.
2. No clone local do repositório, copiar a pasta `docs/visual/prototipos/` do pacote para a pasta homônima no projeto, mantendo os 16 PNGs, as duas visões gerais e o manifesto.
3. Conferir o total de 8 PNGs por mock e verificar suas dimensões e hashes do manifesto; então realizar commit apropriado na área do Bloco 03.
4. Reavaliar o tratamento de direitos por se tratar de repositório **público**. Marcar os arquivos como referenciais/não publicados.

## Laboratório navegável v0.3 revisado — 20/10/2026

**Novo: protótipo HTML realmente disponível no GitHub, marcado como experimental/não aprovado.**

- [Abrir/baixar o HTML executável](estrutura-vazia-v03-revisada/index.html)
- [Instruções e roteiro para o fundador](estrutura-vazia-v03-revisada/LEIA-ME.md)
- [Resultados estruturados dos ensaios](estrutura-vazia-v03-revisada/resultado-testes.json)
- [Teste opcional em Playwright/Python](estrutura-vazia-v03-revisada/tests/test_integridade.py)
- [Parecer provisório de origem](../analises-fundador/PARECER-PROVISORIO-2026-10-19-ESTRUTURA-VAZIA-V03.md)

Este laboratório é **distinto** dos 16 PNGs dos mocks A/B acima. O fundador pode clonar/baixar o repositório e abrir localmente `index.html`, sem API, servidor ou conteúdo editorial real. A entrega não autoriza publicação, nome, identidade definitiva ou implementação pelo Codex. O pacote ZIP v0.3 revisado e suas capturas PNG originais ainda não foram enviados ao repositório; os documentos acima têm estado de transferência verificado.

## Estrutura Vazia v0.3 consolidada — 20/10/2026

**[Pasta da entrega e instruções para o fundador](estrutura-vazia-v03-consolidada/README.md)**.

Esta versão continua a anterior e foi publicada para validar as observações B03-R1/R2/R3 do parecer de 20/10, incluindo o painel de preferências ao cruzar 560px, relatório de faces únicas versus visitas, comparação de texto no Folhear e Contínua, componente grande rolável ao teclado, e espaço publicitário inexistente sem anunciante.

- [Protótipo real (HTML)](estrutura-vazia-v03-consolidada/index.html)
- [Relatório das verificações](estrutura-vazia-v03-consolidada/resultado-testes.json)
- [Script de teste reproduzível](estrutura-vazia-v03-consolidada/tests/test_integridade.py)

**Condição:** experimento; testes de aparelho físico, leitor de tela, desempenho e conteúdos editoriais reais continuam pendentes. Não confundir com os 16 PNGs dos dois mocks A/B, que permanecem fora do GitHub.
