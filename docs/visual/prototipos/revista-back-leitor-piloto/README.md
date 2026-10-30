# Leitor piloto local da Revista Back

Abra `http://127.0.0.1:8765/` enquanto o servidor local estiver ativo. Para iniciar outro servidor, entre nesta pasta e execute:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

O protótipo é um HTML autocontido, sem dependências para instalar. Ele não publica nem envia dados para outro serviço.

## Experiência responsiva

- O mesmo botão hambúrguer fica disponível em celular, tablet, notebook e desktop. Ele é o único acesso aos modos de leitura, controles de texto e sumário; a barra do site fica recolhida.
- O menu reúne `Folhear` e `Contínua`, tamanho da fonte, espaçamento, tema, tela cheia e navegação da edição. No celular, abre a tela inteira. Na rolagem contínua, a faixa superior reserva espaço para o hambúrguer e evita que o texto passe por baixo dele.
- A leitura em páginas mostra uma página nas telas estreitas e duas páginas lado a lado nas telas largas. O modo contínuo adapta as páginas e o texto à largura disponível.
- A implementação foi capturada no Edge em 390×844 (celular), 768×1024 (tablet em pé), 1024×768 (tablet deitado), 1366×768 (notebook) e 1440×900 (desktop). Não houve rolagem horizontal nesses viewports.
- A edição reúne capa, expediente, sumário, abertura da pauta, resumo recebido, fontes, gate de aprovação e contracapa.

## Referências visuais e artes

- A decisão de leitura imersiva no celular e o padrão do menu foram comparados com `Revista_BACK_B03_Mobile_Imersivo_2026-10-27.zip`.
- A regra de capa foi consultada em `Revista_BACK_Bloco03_Cinco_Modelos_Editorais.zip`: `BACK` em destaque no topo, arte cinematográfica ao centro, chamadas secundárias nas laterais e chamada principal mais abaixo. Aquele pacote se identifica como proposta; não é tratado como aprovação integral da identidade.
- `Revista_Gamer_Bloco03_v03.zip` se identifica como laboratório exploratório, não como identidade aprovada.
- Nenhuma imagem dos três ZIPs foi copiada para esta implementação. A ilustração original em `assets/gothic-mining-valley-editorial-illustration.png` foi gerada para o protótipo e identificada como arte editorial gerada por IA; ela não representa o jogo nem é captura oficial.

## Conteúdo e situação editorial

A pauta vem de `coletor/2026-10-29-1840.md`, atribuída pelo Captador à Gematsu. A classificação local reutiliza a seção do Captador sem inferência adicional. O texto apresentado continua sendo o resumo da coleta, não uma reportagem de Arlindo Carranca. Um comunicado oficial da THQ Nordic foi aberto nesta retomada e aparece como fonte complementar, com sua origem promocional indicada.

A matéria completa, pesquisa complementar de Carranca, revisão factual, aprovação humana e conteúdo de Beto Cartucho e Nina Prisma ainda não foram integrados. O estado da edição permanece como prévia privada, com gate humano visível. Não houve inferência SIWC, publicação ou deploy nesta prévia.

## Atualizar a pauta por uma reportagem aprovada

O objeto `edition` em `index.html` contém o conteúdo da edição. Quando houver reportagem revisada, preencher `edition.story.article.body` ou `edition.story.article.blocks`, registrar somente as fontes efetivamente consultadas e manter o gate de aprovação humana antes de qualquer publicação.
