# ENG-CODEX-009 — checkpoint operacional

**Setor:** Engenharia e Codex
**Identificador:** ENG-CODEX-009
**Versão:** v1.0
**Status técnico:** implementado e validado por testes automatizados; avaliação editorial humana e verificação factual independente pendentes.
**Atualizado:** 2026-10-26
**Dependências:** Issue #37, Issue #35 (decisão index-only), Issue #33/PR #34 (H05), PR documental #36, `docs/operacao/CONTRATO-ENTREGAS.md`.
**Aprovador:** Direção, para escopo e execução.

## Objetivo e limites

Executar uma matéria investigativa completa por jornalista usando o DNA aprovado e o pacote local de evidências; medir consumo/tempo por pessoa; preservar JSON original, texto integral e revisões em arquivos separados; validar a ponte opcional com a fábrica.

Foram feitas três chamadas SIWC reais, uma por pessoa, após ordem explícita da Direção e relato de 95% de franquia durante a chamada de Carranca. Não foram repetidos os seis casos reais H04. Não houve API paga, pesquisa externa, publicação, merge ou deploy. A rodada B do protocolo longitudinal não foi executada.

## Estado vivo revalidado

- Branch: `codex/eng-codex-009-evidence-metering`; upstream: `origin/codex/eng-codex-009-evidence-metering`; HEAD validado antes deste checkpoint: `21ec16d663341f0cf1750c0520b5e4393a1679a3`; worktree limpo antes das alterações deste documento. A ref remota correspondia ao mesmo SHA.
- Base técnica: `codex/eng-codex-008-siwc-validation`, SHA `8d43a6c855807b2229a8e1eb620a31c6bb6e28e2`.
- Issue #37 estava aberta, sem comentários na checagem inicial; a rodada e seus limites foram registrados depois em [comentário de status](https://github.com/Saaimingo/Revista_Gamer/issues/37#issuecomment-6416201161). PR #36 está aberta/draft, com zero reviews, na branch documental `fundador2/eng-codex-009-dossies-editoriais-2026-10-25`. O texto e comentário anteriores diziam aguardar ordem e franquia; a ordem posterior da Direção para continuar e o relato de 95% substituíram essa espera.
- PR #38 está aberta/draft, sem reviews, da branch `codex/eng-codex-009-evidence-metering` para a base documental `fundador2/eng-codex-009-dossies-editoriais-2026-10-25`, para que o diff técnico não duplique os documentos já cobertos pela #36.
- Issue #33 segue aberta e PR #34 segue aberta/draft, sem reviews. A H05 da 008 avançou offline e depende da ponte/revisão conforme os estados registrados em #35.
- Decisão viva de Issue #35, comentário `6406250653`: pedidos ambíguos ou sem mapeamento determinístico ficam em hold; somente `read:radar_index` com `ResearchService(provider=None)` pode executar sem rede. Não existe autorização para pesquisa em fontes públicas ao vivo.
- A observação mais recente de franquia é 95% durante a chamada de Carranca. Não foi observada franquia posterior às três chamadas; tokens não são convertidos em percentagem nem em custo Plus.

## Referências aprovadas e pacotes

- Carranca / `ranzinza` v1.0: DNA aprovado do Bloco 02 no commit `3d651fe1951818767b4a6b935732857f08cb7849`, 4 documentos; snapshot integral de 66.315 caracteres; hash `1f66f0ffbf323823e908cedcc7002aac6551fb5f28d3b309d29602ea94f70191`.
- Beto Cartucho v0.2 e Nina Prisma v1.0: DNA aprovado do Bloco 02 no commit `21381c0975bef1da048d7887cbdfbd0dd97bed96`, 5 documentos por persona; snapshots de 35.229 e 25.245 caracteres. Hashes: Beto `de815e0827b4fae5c30d1ec9e4aecac829b3298474c6fd737d2b4c67cfd5fc67`; Nina `6b60f719de00a91503a411d4e146d41c31ccfe1fa4055177091eb3a0b878e4bc`.
- Os arquivos-fonte e os hashes dos DNAs foram preservados; exemplos editoriais não foram usados como instruções. O limite para carregar DNA foi aumentado a 80.000 caracteres para não truncar Carranca.
- Pacotes locais: `motor_editorial/evidence_packages/eng_codex_009/`; Carranca 12 candidatas/11 notas, Beto 14/12, Nina 11/10. São notas curatoriais e URLs, não corpos de fonte lidos pelo Motor. O índice Radar local não contém tabelas `radar_*`.

## Implementação

- `motor_editorial/usage_meter.py`: recibo por jornalista/papel/tarefa com modelo, effort, tokens de entrada/saída/raciocínio/total, cache, chamadas, latência, bytes de contexto, status e fonte da medição. Custo faturado e quota ficam indisponíveis sem evidência própria.
- `motor_editorial/story_version_archive.py`: preserva resposta JSON bruta, render integral, manifesto e SHA-256; originais e revisões ficam em caminhos/IDs separados. Os originais desta rodada estão sob `original/initial/`; não há revisões porque ainda não houve avaliação humana.
- `motor_editorial/agent_siwc.py` e `motor_editorial/eng_codex_009.py`: recibo mesmo para estados incertos, snapshot do DNA, no máximo uma chamada por jornalista e sem replay de tarefas iniciadas/concluídas.
- `motor_editorial/research_mediation.py`: converte apenas sugestões determinísticas e tipadas no escopo local aprovado; sugestões sem par question/purpose mapeável ficam em hold.
- Ponte opcional da fábrica reusa `AgentQueue`/`TaskDispatcher`, produz apenas rascunho e conserva revisão humana/fact-check/publicação desligados. O fluxo sintético padrão continua intacto.
- A raiz privada é `%USERPROFILE%\.codex\Revista_Gamer\ensaios-009`; respostas e artigos integrais não foram adicionados ao GitHub. O índice privado `INDICE-LEITURA-INTEGRAL-ENG-CODEX-009.md` reúne links aos originais, hashes e métricas. A gravação do índice foi feita em UTF-8 e validada sem caracteres de substituição; hashes de render e JSON foram conferidos contra os manifestos.

## Execuções reais da ENG-CODEX-009

| Jornalista | Estado | Tokens entrada / saída / raciocínio / total | Latência | Contexto | Texto | Validação / pesquisa / fábrica |
|---|---|---:|---:|---:|---:|---|
| Carranca | `uncertain` no ledger após exceção local de pós-processamento; resposta do provedor concluída | 20.534 / 5.793 / 2.324 / 26.327 | 106.969 ms | 85.258 B | 1.974 palavras | Schema e refs revalidados offline; pesquisa em hold; fábrica não executada por estado incerto |
| Beto | `succeeded_needs_research` | 12.949 / 7.153 / 2.979 / 20.102 | 130.625 ms | 53.372 B | 2.562 palavras | `role_schema_valid`; sugestão de pesquisa em hold; fábrica `held_pending_research_or_review` |
| Nina | `succeeded_needs_research` | 10.071 / 4.312 / 1.471 / 14.383 | 81.391 ms | 40.966 B | 1.726 palavras | `role_schema_valid`; sugestão de pesquisa em hold; fábrica `held_pending_research_or_review` |

**Totais observados:** 60.812 tokens e 318.985 ms de latência acumulada, em três chamadas, sem retry. Estes números medem só os recibos SIWC disponíveis, não a quota da interface ou preço da assinatura.

- Carranca: tarefa `0cc6663c-2df8-563c-926a-d087b87ec2be`; bruto SHA `48e3b5a16b034406358803fd62713f6eeb0cfd6d8e2879e574eba2be5f0a0445`; render SHA `cc8a6bec0ef134651049d5adced0a2f8c91abacf69c4026dbe112aff47a15e70`.
- Beto: tarefa `d6bf9d8e-3bd7-59c3-bc9d-91aff746ac16`; bruto SHA `f936a3a4cb341f5d447ae400aa89f6d6cf353d5c462e8bcbc264a7a868269a96`; render SHA `c42b31b48f662a8a7bc0b0b30ccb09f2a34620803e7d273e8fa5786acf662ea3`.
- Nina: tarefa `f004be7b-1047-5d6d-825a-83b535978893`; bruto SHA `afd5ef25f5146fde5bfc34c8ac706f8fdb7401aa58146fafd3b1c90b16b558c1`; render SHA `6f9a7c4a338ff169e657043e45c749b73de8765bea07652540f222136aa2acc7`.
- Carranca ficou `uncertain` porque o pós-processamento rejeitou `/` no `story_id` depois da resposta completa. O defeito foi reproduzido offline e corrigido: o caminho é derivado por hash e não deve proibir identificador namespaced. A matéria foi recuperada do JSON já existente e arquivada; ledger incerto preservado e chamada não repetida. O status `json_object` capturado na hora foi separado da revalidação offline de schema de papel e referências, ambas aprovadas.
- Beto e Nina concluíram uma chamada cada. Ambos solicitaram pesquisa que não pôde ser mapeada de forma determinística; a mediação respondeu `hold_unmapped_suggestions`, nenhuma consulta local ou externa foi executada e os drafts não foram liberados pela ponte da fábrica.

## Factualidade e avaliação humana

Esta rodada permite avaliar como cada persona raciocina sobre os dossiês disponíveis, a voz e a temperatura narrativa. Não representa apuração independente: corpos de fontes não foram obtidos, direitos não foram revalidados e nenhum fact-check humano foi feito. Avaliação P/T/J/F está pendente para leitura humana integral. Nenhum texto foi publicado. Expansão para fontes externas requer decisão de escopo e autorização próprias; manter `read:radar_index` como limite atual.

## Validação executada

- Suíte focalizada da instrumentação, mediação, runner, H05 e ponte da fábrica: **42 testes OK**.
- Regressões após o registro de franquia: **24 testes OK**.
- Regressões após corrigir o identificador namespaced: **9 testes OK**.
- Regressões após corrigir o resumo de schema final: **10 testes OK**.
- Suíte ampliada dos módulos de contratos, catálogo, fábrica, multipauta, orquestração e workflow: **99 testes OK** em 90,565 s usando ` .venv/Scripts/python.exe ` (CPython 3.11.9). Uma execução anterior com Python global terminou com 5 erros e 1 skip, inclusive por falta de `tzdata` para `America/Sao_Paulo`; a mesma suíte no ambiente do projeto passou.
- `python -m compileall -q motor_editorial` — OK. `git diff --check` — OK.

## Persistência e próxima ação

Commits enviados para `origin/codex/eng-codex-009-evidence-metering`: `2b09b5c` (preparação da bateria), `f189b20` (checkpoint da manhã), `f8a222e` (pausa), `e6fccf2` (identificador namespaced no arquivo) e `21ec16d` (estado final de schema), `12f7b0a` (checkpoint das três execuções) e `22f05dc` (link da PR draft). PR #38 mantém a implementação e o checkpoint em draft; não foi mesclada. O branch e seus checkpoints são versionados em commits regulares e enviados ao upstream dedicado.

1. Revisar a PR #38 técnica, baseada na branch documental do Fundador 2; manter sem merge.
2. Fazer leitura humana dos três originais pelo índice privado e registrar P/T/J/F em artefato separado, sem modificar DNA ou original.
3. Tratar fact-check, direitos e eventual expansão da pesquisa como pendências de escopo/editoriais. Não fazer nova chamada, não repetir Carranca e não executar pesquisa além do índice local sem nova decisão explícita.
4. Revalidar GitHub/Git e registrar um novo checkpoint antes de qualquer etapa futura.

**Sem merge, publicação ou deploy.**
