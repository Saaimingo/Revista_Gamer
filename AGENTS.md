# Instruções operacionais para Codex e outros agentes

Este repositório é a **fonte de verdade do projeto**, não um sistema de execução da revista. Os chats do ChatGPT Project não compartilham estado operacional em tempo real.

## Ao começar qualquer tarefa

1. Ler a **`docs/governanca/BIBLIA-DO-PROJETO.md`**, `README.md`, `docs/governanca/DECISOES.md`, `docs/governanca/STATUS-GERAL.md` e o README do setor.
2. Consultar GitHub Issues abertas vinculadas ao setor e quaisquer alterações recentes pertinentes.
3. Identificar entregável, responsável, status e referências aprovadas.
4. Se houver requisito não decidido, abrir Issue seguindo `docs/operacao/PROTOCOLO-HANDOFF.md`; não preencher lacuna criativa/jurídica por conta própria.
5. Trabalhar na sua área em branch/PR quando houver alterações substanciais. Não mudar documentos aprovados por outro setor sem solicitação e revisão.
6. Documentar evidências, testes, dependências, limitações e URLs dos arquivos entregues.

## Autoridade e status

`proposta` -> `em_revisao` -> `aprovado` -> `implementado` -> `validado`. `bloqueado` quando falta decisão ou acesso. Apenas **aprovado** é requisito para implementação. `implementado` NÃO significa `validado`.

A direção do projeto decide sobre nome comercial, marca, publicações e mudanças significativas de escopo. Um agente **não publica, não compra serviços, não contrata, não envia comunicações a terceiros, não cria contas, não muda permissões e não liga automações de produção** sem aprovação específica.

## Paredes de separação

- Editorial: pesquisa, fontes, checagem, texto e acervo com direitos verificados.
- Comercial: peças e licenças fornecidas por anunciantes, afiliados e campanhas.
- É proibido puxar imagem de jogo do acervo editorial para publicidade. A revisão editorial não é substituída por objetivo de monetização.
- Personas públicas são perfis de escrita persistentes, não credenciais humanas ou experimentos autônomos. Nunca alegar teste de produto ou jogo que não ocorreu.
- Não assumir que conteúdo de imprensa ou vídeo oficial tem uso comercial/derivativo autorizado. Uso sem prova fica pendente.
- Não adicionar chaves de API, tokens, dados pessoais sensíveis, mídia binária não autorizada ou logs com segredos.
- Não usar limites do Plus como garantia de acesso à API ou execução desassistida: medir e validar.

## Padrão de entrega

Veja `docs/operacao/CONTRATO-ENTREGAS.md`. Toda entrega deve apontar arquivos alterados, status, versões/fontes, validação, riscos e pendências. Pedidos a outros setores devem virar Issue. Não prometer que um chat notifica outro automaticamente.

## Regra permanente de continuidade do Fundador (direção, 31/10/2026)

O chat Fundador deve manter a memória operacional atualizada **após cada decisão, avaliação de Codex, devolutiva setorial, mudança de rumo, teste ou bloqueio** em `docs/governanca/continuidade-fundador/`, seguindo [o protocolo específico](docs/governanca/continuidade-fundador/PROTOCOLO-MEMORIA-CONTINUA.md). O índice fica em [README](docs/governanca/continuidade-fundador/README.md) e os backups históricos permanecem em `docs/governanca/`. Registrar status e fontes; não confundir relato com prova independente, testes simulados com reais, aprovação interna com publicação. Ao suceder um Fundador, ler essa memória antes de recomendar novas ações. Não declarar commit inexistente; nenhuma memória autoriza automaticamente trabalho ou gastos.
