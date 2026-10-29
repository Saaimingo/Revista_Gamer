# REVISTA BACK — Retomada do Codex e foco em primeira edição

**Data:** 2026-10-29  
**Status:** instrução de continuidade para investigação/execução controlada; **não é homologação nem autorização de publicação**.  
**Direção:** concluir uma revista navegável e funcional, não ampliar a fábrica.

## Fonte primária para a retomada
Leia primeiro, **no computador do diretor**, `D:\Censurado-ollama-test\local-tests\REVISTA-BACK-CHECKPOINT.md`. Este documento no GitHub é apenas o roteiro de retomada; **não substitui** o checkpoint local nem comprova por si que os arquivos locais estão presentes e íntegros. Confira também `git status` no clone `D:\Censurado-ollama-test`, o relatório/artefatos locais e o estado do repositório `Saaimingo/Revista_Gamer`. Não sobrescreva trabalho não commitado. Evite reaproveitar cegamente a PR #44, que corresponde à fábrica anterior.

## Evidências relatadas pelos últimos ensaios (confirmar no checkpoint local)
- Captador agendado do ChatGPT grava coletas factuais em `main:coletor/` com checagem de URLs anteriores; é fonte de candidatos, **não** reportagem revisada.
- Clone do Censurado em `D:\Censurado-ollama-test`. Ollama/Qwen local passou no teste de adaptador de inferência; DDGS `websearch` leu páginas públicas, com limitações de mecanismo e extração.
- A ponte SIWC autorizada produziu **uma resposta real** com `gpt-6-luna` via OAuth/Responses API, recebendo `response.completed`. Checkpoints de duas tentativas antigas permanecem `uncertain` e nunca devem receber retry automático.
- Testes focados de UTF-8, controle `reasoning_effort`, carregamento de 19 arquivos dos três pacotes de persona e prévia local passaram. O fluxo `run.py` com nós `draft` e `review` via SIWC **simulado** passou, com checkpoints e prevenção de duplicação, mas **não houve pipeline editorial integrado real com Luna**.
- Censurado foi selecionado como **base experimental**. Umbruch inspira composição de personas; Machine Herald inspira entrega de artigo, fontes e proveniência. Não há decisão de instalar/juntar três sistemas integrais. O visual final do Bloco 03 ainda não foi integrado ao pipeline.

## Meta do ciclo de entrega
Alcançar **uma primeira edição piloto da Revista Back aberta no navegador**: conteúdo original pesquisado e revisado, personas oficiais Carranca/Beto/Nina, identidade visual previamente aprovada, leitura funcional no computador e celular, aprovação humana obrigatória. Sem deploy/publicação pública até autorização específica da Direção.

## Ordem de trabalho
1. **Continuidade e segurança:** ler checkpoint local e artefatos, identificar mudanças não commitadas, propor/produzir backup versionado seguro em branch separada, respeitando licenças MIT/avisos e **sem armazenar OAuth, tokens, logs sensíveis ou textos editoriais privados em Git público**. Verificar o estado antes de alterar.
2. **Mapa de impedimentos de entrega:** identificar precisamente o mínimo entre pipeline existente e edição navegável. Nada de nova auditoria de três projetos ou arquitetura ampla. Reaproveitar ao máximo o que já funciona.
3. **Ensaio de fluxo real delimitado:** planejar uma execução de notícia real de `coletor/` → jornalista com DNA oficial → revisão → saída salva, pela ponte SIWC e `gpt-6-luna`. **Antes de qualquer chamada real**, apresentar quantidade máxima de invocações, orçamento e pedir autorização. Nenhum fallback para modelos mais caros ou API paga; uma chamada de IA ativa por vez, salvo até dois jornalistas quando autorizado. Não considerar a saída real aprovada só porque o mock passou.
4. **Leitor visual:** integrar artigo aprovado à experiência visual aprovada pelo Bloco 03, sem substituir a identidade. Tela do celular dedicada ao conteúdo, menu discreto, modos folhear/rolar configuráveis, leitura contínua ou duas páginas quando pertinente; testar navegador real em desktop e viewport móvel. Imagens somente com uso editorial autorizado e fonte registrada; placeholders explícitos quando necessário.
5. **Primeira edição piloto:** reunir material suficiente para Carranca, Beto e Nina, testar cadeia e visualizar a edição inteira. Publicação externa, redes sociais, patrocínios, áudio e novidades ficam fora do primeiro gate, salvo requisito já indispensável no material aprovado.

## Aceite e evidência
- Evidenciar arquivos/paths e hashes relevantes, URLs válidas e o que o agente efetivamente leu.
- Distinguir teste simulado, chamada real de modelo, reportagem factual e prévia visual efetiva.
- Preview deve abrir no navegador real, ser navegável, exibir identidade visual e não publicar automaticamente.
- Proteger chamadas SIWC por checkpoints e estado incerto; sem retries automáticos.
- Reporte curto: estado, impedimento real, prova obtida, próximo passo. Não declarar primeira edição pronta com arquivos Markdown isolados.

## Limites
Não alterar `main`, não mexer no antigo PR #44, não usar API paga, não publicar, não refazer fábrica, não executar inferência real sem orçamento/consentimento explícito; proteger o trabalho acumulado no clone. Projetos externos: `hec-ovi/censurado-web-brain`, `osmancakir/umbruchai-news-desk`, `the-machine-herald/machineherald.io`. Sem necessidade demonstrada de instalar os três.

**Atenção:** esta branch foi criada apenas para disponibilizar esta orientação ao Codex. O primeiro dever do Codex é verificar o checkpoint local e reconciliar os estados antes de codificar.
