# Bloco 05 — Fluxo simples de obtenção de mídias oficiais v0.1

**Identificador:** ACERVO-FLUXO-OFICIAL-001  
**Setor responsável:** Acervo Editorial, Imagens e Direitos de Uso  
**Versão:** 0.1 — 2026-10-25  
**Status:** PROPOSTA, para revisão da direção/fundador; não implementado.  
**Dependências:** `MAPA-FONTES-IMPRENSA-V0.1.md`, `MATRIZ-DIREITOS-EDITORIAIS-V0.1.md`, `FICHA-MIDIA-MODELO.md`.

## Direção criativa esclarecida pela direção em 25/10/2026

**Objetivo principal: descobrir e obter imagens e vídeos OFICIAIS, já fornecidos gratuitamente para imprensa quando disponíveis, SEM MODIFICÁ-LOS, e oferecer esses arquivos para reportagem, capa editorial e navegação da revista conforme as condições de cada fonte.** Recriação por IA e transformação de imagens de jogos NÃO são parte do fluxo normal de acervo. Não gerar imagens enquanto existirem assets oficiais suficientes e apropriados. Diagramação externa ao arquivo pode ser feita pelo Bloco 03, respeitando termos do material.

**Separação:** divulgação de matéria/capa editorial ≠ anúncio publicitário de produto. Acervo editorial não alimenta peças publicitárias, como já consta nas decisões da revista. Não confundir gratuidade do site com licença automática: procurar a licença, sem burocracia inventada nem extrapolar a permissão.

## Fluxo operacional enxuto — requisito conceitual, ainda não implementado

1. **Matéria/lançamento identificado:** registrar título, publisher e estúdio corretos para aquele jogo/território.
2. **Abrir fonte oficial registrada:** press room do publisher ou estúdio, agregador de relações públicas que identifica o remetente, ou media library oficial do jogo.
3. **Ver pacote disponível:** screenshots, key arts, logos, fotos, trailers; anotar acesso público ou cadastro/credenciamento legítimo. **Não criar contas por iniciativa de agente nem compartilhar credenciais.**
4. **Ler condições aplicáveis (uma vez por política/versionamento e excepcionalmente por ativo):** reprodução editorial web, uso em capa da edição, PDF, créditos, embargo, território; não há interesse em modificar o arquivo. Se não houver autorização comprovada para modalidade, marcar `PENDENTE` sem afirmar proibição.
5. **Obter apenas o necessário para a pauta, pela função de download autorizada:** preservar o arquivo intacto, identificação original, crédito, fonte, data, eventual licença e hash; mídias fora do Git. Não baixar automaticamente bibliotecas inteiras.
6. **Oferecer ao editor:** pacote pesquisável de arquivos aptos à modalidade e respectivos créditos, sem obrigar análise jurídica manual em toda utilização de uma política já comprovada e aplicável. Se a mesma arte servir para capa e miolo, registrar os dois usos.

**A automação priorizada é:** (A) detectar lançamentos/novos press releases via feed/API autorizado; (B) resolver o portal de imprensa certo; (C) identificar se há assets e quais exigem credenciamento; (D) obter somente o material que o canal efetivamente permitir por mecanismo oficial; (E) entregar material organizado e etiquetado com condições. **Não há etapa de edição por IA.** Se não houver material adequado, registrar lacuna e buscar outra fonte oficial, não gerar cena fictícia como substituta automática.

## Fontes com caminho de obtenção verificado nesta rodada (25/10/2026)

| Fonte oficial | URL inicial | Passo operacional observado | Acesso / permissão |
|---|---|---|---|
| Square Enix North America Press Hub | https://press.na.square-enix.com/ | Abrir jogo no catálogo; escolher conjunto de screenshots/artwork/logos; `Add set to downloads` | Termos https://press.na.square-enix.com/Site/TermsAndConditions §1(b): licença gratuita, não exclusiva e revogável para membros da imprensa baixarem e reproduzirem mídia relativa ao grupo; respeitar embargo, território, avisos de copyright, avaliações/age-gates aplicáveis. Não foi feito login nem download. |
| Team17 | https://www.team17.com/press-and-creator-hub ; https://www.team17.com/press-kit-archive | Selecionar jogo; `Press Kit` / arquivo de kits | Disponibilização de kit confirmada; direitos específicos e acesso ao ZIP não testados. |
| Focus Entertainment | https://www.focus-entmt.com/en/presskits | Selecionar jogo; `Download` | Disponibilização de kit confirmada; licença do material não verificada individualmente. |
| Rockstar Games — GTA VI | https://www.rockstargames.com/VI/media | Escolher Screenshots / Artwork / Clips / Videos; `Download All` em ZIP ou arquivo individual | Opções oficiais de download constatadas. Condições específicas para capa/reprodução ainda pendentes; download oferecido ≠ licença universal. |
| Bandai Namco Entertainment America | https://www.bandainamcoent.com/press-center | `Register Now` para press room de imagens estáticas; vídeos no canal oficial para embed | Página informa registro e breve aprovação antes do acesso; não realizado. |
| PlayStation Press Center | https://presscenter.playstation.com/ | Cadastro/credenciamento, login, busca por jogo e assets | Página de login/cadastro confirmada, biblioteca autenticada não inspecionada. |
| Games Press (agregador) | https://www.gamespress.com/pt | Localizar jogo/press release; escolher materiais enviados por publisher ou PR e baixar somente os necessários | FAQ https://www.gamespress.com/FAQ---Use-of-Assets: fonte original deve ser atribuída ao publisher ou agência, copyright permanece do contribuinte; recomendável verificar autorização e preservar créditos; download sistemático de todas as imagens gera suspensão; RSS para referência pessoal, não republicação. |

### Demonstração concreta: Square Enix

Página de termos oficial: https://press.na.square-enix.com/Site/TermsAndConditions (termos disponíveis com data 21/10/2019). Para membros da imprensa a licença de materiais é expressa, limitada à criação/distribuição de conteúdo de mídia relacionado à Square Enix, com possibilidade de revogação. Fichas por jogo podem trazer exigências adicionais, inclusive restrições de idade sobre vídeos. Logo: registrar o termo geral e checar apenas a exceção por ativo, ao invés de exigir autorização manual nova para cada screenshot idêntico sob a mesma política.

## Critérios de aceite para um futuro teste do Codex

- Uma matéria de jogo com pacote oficial e uso editorial explicitamente permitido recebe imagens e créditos, com localização simples do arquivo.
- Um jogo com biblioteca dependente de cadastro indica corretamente `PRECISA_CREDENCIAMENTO`, em vez de tentar acessar a conta à força.
- Uma fonte com política já verificada é reutilizável; atualizar se versão/termos mudarem, sem atrito manual para cada arquivo.
- Nenhuma imagem oficial é alterada, recriada por IA, recombinada ou enviada ao acervo comercial.
- Mídias sem comprovação de uso específico recebem `PENDENTE` e indicação do que verificar, não proibição inventada.
- Não disparar aquisição paga, download em massa, extração contra termos, publicação ou automação real sem autorização específica.

## Estado e limites

Apenas pesquisa documental dos portais oficiais, sem baixar nenhum arquivo nem testar credenciamento/autenticação ou feed na prática. **Este documento não autoriza Codex a mudar o sistema, começar monitoramento ou gastar recursos.** Links e políticas precisam ser revisitados antes da utilização pública.
