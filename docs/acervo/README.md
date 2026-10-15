# Setor: acervo **editorial** e direitos

Status: arquitetura conceitual. Nenhuma licença concreta está aprovada apenas por constar neste documento.

## Organização

Arquivo lógico por titular -> franquia/produto -> mídia. Ex.: `Capcom/Resident_Evil/<jogo>/`; fabricantes de GPU por marca/produto. Cada fonte possui política geral versionada; **cada ativo**, mesmo de press kit, possui ficha própria e evidência do direito de utilização.

Um índice central pesquisável (inicialmente metadados/SQLite) poupa o Luna de abrir dezenas de pastas. Vídeos externos permitidos como embed podem ser apenas referenciados, sem download. Mídia binária licenciada pertence a armazenamento dedicado com backup, não necessariamente a este Git público.

## Modelo da ficha

Ver [modelo de ativo](FICHA-MIDIA-MODELO.md). Origem, titular, URL, tipo de material, modalidades de uso permitidas/vedadas, derivações, crédito, data da revisão, restrições de marketing, status e referência à autorização.

## Critérios

- Uso jornalístico, PDF, redes, animação, download colecionável e publicidade são **modalidades diferentes**.
- Publicidade não utiliza, nem consulta automaticamente, acervo editorial. Anunciante fornece suas peças e direitos em ambiente comercial segregado.
- Imagem de jogo não é domínio público por estar na internet; gerador de IA não autoriza derivação protegida.
- Se autorização/limite é desconhecido: `PENDENTE`, não `LIBERADO`. Nunca presumir licença ampla.
- Antes de publicar, validar cada mídia contra modalidade efetivamente usada.

## Recursos a catalogar futuramente

Press rooms de fabricantes/publishers, capturas válidas para reportagem, arte original e links de vídeo oficial. Links e leis de referência não substituem avaliação jurídica para usos concretos.
