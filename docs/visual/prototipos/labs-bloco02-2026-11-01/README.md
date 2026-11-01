# Revista Back — laboratório de efeitos, originais transferidos do Bloco 02

**Origem:** a Direção realizou, sem intenção, no Chat Bloco 02 uma série de testes de UX/identidade que pertencem ao **Bloco 03**. A transferência foi solicitada pelo diretor em 01/11/2026.  
**Status:** protótipos experimentais, **não aprovados como código de produção**. Nenhum merge/deploy autorizado.  
**Documento de contexto e decisões:** [Handoff integral, com linha do tempo, comparações, falhas e 13 verificações propostas](../../analises-fundador/HANDOFF-DIRECAO-BLOCO02-PARA-BLOCO03-INTERACOES-IMERSIVAS-2026-11-01.md).  
**Issue de destino:** [#50](https://github.com/Saaimingo/Revista_Gamer/issues/50). **Investigação pré-existente da biblioteca/híbrido:** [PR #46](https://github.com/Saaimingo/Revista_Gamer/pull/46).

## Arquivos HTML ORIGINAIS do ensaio

1. [**Revista_Back_Laboratorio_A_vs_B.html**](Revista_Back_Laboratorio_A_vs_B.html) — comparação lado a lado entre (A) câmera lenta sobre a imagem e (B) simulação de folhear, três cenas. **Avaliação do diretor:** os movimentos **aproximar/afastar** foram aprovados como conceito; folhear pareceu falso, e zoom de componente apenas deslocando a foto foi **reprovado**.
2. [**Revista_Back_Laboratorio_Integrado_Folhear_Zoom.html**](Revista_Back_Laboratorio_Integrado_Folhear_Zoom.html) — laboratório integrado com gesto de canto, capa/câmera, placa-mãe demonstrativa e zoom contextual. **Avaliação:** melhorou, **zoom de componente agradou**; aproximar/afastar agradaram; folhear **ainda não aprovado**, artificial. A ferramenta de validação visual automatizada não concluiu todas as verificações na época.
   
**Verificação da transferência:** ambos os arquivos foram preservados nesta branch como HTML textual, com imagens incorporadas (`data:image`) e JavaScript. A leitura dos dois blobs foi confirmada via GitHub após arquivar; **isso não equivale a rodar novamente a suíte de testes no navegador ou homologar compatibilidade no aparelho físico**.

**Abrir:** baixe o arquivo HTML bruto pelo GitHub e abra em Chrome/Edge. A prévia GitHub normal pode exibir o código, e não executar o HTML. Os arquivos são autônomos e não devem acessar serviço externo para reproduzir os efeitos.

## O que permanece somente no histórico da conversa

- Três **pranchas ilustrativas A/B/C** (conceitos de capa cinematográfica, folhear e imagem técnica). Eram imagens estáticas, não HTML de movimento.
- Uma demonstração **interativa dentro do chat**: efeito de folha em faixas curvas e zoom vetorial por CPU/VRM/M.2/PCIe/RAM. O código visual rodou naquele ambiente, **não foi exportado como terceiro HTML aqui**. Sua avaliação foi documentada no handoff.

**Não substituir silenciosamente os originais por outro código**: as versões acima são peças de comparação, inclusive com limitações que a direção já apontou. O Bloco 03 continua responsável por novos ensaios e pela identidade do leitor, usando a v0.3 como base e comparando motores prontos (StPageFlip etc.) antes de nova tentativa artesanal.

## Regras de continuidade

- **Aprovado em conceito:** imagem vai para perto e para longe suavemente, preservando original.
- **Quase ideal/ganhou aceitação conceitual:** zoom contextual dentro da foto técnica, sem painel lateral.
- **Reprovado ainda:** folhear. Próxima prova: *puxar canto inferior direito, dobra diagonal, sombra, verso real, soltura reversível*, sem interface externa.
- **Novo requisito explicitado:** dupla 02–03, 04–05 como composição editorial (mapa/diagrama atravessando o par), e possibilidade de visualizar dupla no celular em paisagem sem sacrificar texto.
- **Preservar:** modo Folhear/Contínua, menu discreto e acessibilidade da v0.3; não trabalhar em DNA/esteira/Redação por conta deste pacote.

**Somente revisão humana da Direção pode declarar essa interface aprovada.**
