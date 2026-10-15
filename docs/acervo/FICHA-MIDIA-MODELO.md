# Modelo de ficha individual de mídia

**Exemplo de esquema, não é uma autorização.**

- `asset_id`: identificador único
- `titulo`: descrição curta e precisa
- `titular_direitos`: pessoa/empresa
- `produto_ou_obra`: título/franquia/modelo
- `origem_url`: URL oficial/verificável
- `arquivo_ref`: referência ao armazenamento (sem segredos)
- `tipo`: imagem | vídeo | áudio | embed | ilustração_original
- `fonte_politica`: URL, trecho/regra e versão/data
- `licenca_ou_autorizacao`: documento/link verificável ou `indefinida`
- `uso_web_editorial`: permitido | restrito | não autorizado | pendente
- `uso_pdf`: permitido | restrito | não autorizado | pendente
- `uso_redes`: permitido | restrito | não autorizado | pendente
- `uso_derivado_animacao`: permitido | restrito | não autorizado | pendente
- `uso_wallpaper`: permitido | restrito | não autorizado | pendente
- `credito_exigido`: texto/critérios
- `transformacoes_admitidas`: ações especificadas (não presumidas)
- `data_checagem`: AAAA-MM-DD
- `responsavel_checagem`: setor/pessoa
- `status`: pendente | revisado | bloqueado
- `observacoes`: limites e dúvidas
- `hash`: hash do arquivo se armazenado

**Importante:** acervo comercial e ficha de campanha existem em área própria do setor Comercial; não criar aqui campo permissivo genérico que misture anúncios e uso editorial.
