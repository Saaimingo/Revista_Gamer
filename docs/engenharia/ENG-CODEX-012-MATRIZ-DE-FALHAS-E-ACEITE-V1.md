# ENG-CODEX-012 — Matriz operacional de falhas, retomada, testes e aceite
**Direção, 26/10/2026. Vinculado a:** ENG-CODEX-012-ARQUITETURA-MESTRA-FABRICA-V1.md. **Status:** contrato de engenharia e homologação futura; nenhuma implementação é atestada por este arquivo.

## A. Mandamento de recuperação

**A fábrica não pode perder trabalho válido nem gastar o orçamento novamente em consequência de erro interno.** Mas “não pode parar” significa: cada tarefa deve ter uma transição segura para reusar, reparar, pesquisar outra fonte autorizada, repropor pauta, aguardar recurso/decisão ou estacionar a matéria enquanto outras progridem. Não significa atravessar consentimento, direitos, fronteiras de segurança ou inventar evidências.

Para qualquer falha, o Motor deve responder a seis perguntas antes de agir: (1) o efeito externo já pode ter ocorrido? (2) existe resultado bruto durável verificado por hash? (3) o input/política/identidade são os mesmos? (4) existe transformação **semântica-neutra** determinística autorizada e testada? (5) qual orçamento/capacidade ainda é válida? (6) em caso de impossibilidade, qual é a rota editorial segura e o próximo estado?

Toda recuperação registra: error_code preciso; failed_stage; role_id; story_id; story_revision_id; original_task_id; previous_status; exception_type/message redigidos de segredos; external_call_started/confirmed/unknown; source_response_sha256 quando disponível; candidate recovery type; verification evidence; regenerated_task_id se existir; source_task_id/recovery lineage; budget_before/after; final_status. Duas execuções concorrentes jamais reabrem a mesma tarefa e ambas recebem “succeeded”.

Respostas externas duráveis e concluídas são imutáveis. **Não retransmitir conteúdo de usuário/fonte ao modelo** apenas porque deu erro de parsing/contrato. Qualquer replay inseguro termina UNCERTAIN, não em segunda cobrança automática.

## B. Códigos de falha e comportamento por domínio

Formato: condição → resposta correta → ação proibida → prova mínima.

### B1. Coleta, origem e orçamento (RADAR)

**R01. HTTP 200 mas zero documentos:** transportar status HTTP, content-type, parser status, quantidade de itens extraídos e erro tipado. Se corpo permitido foi persistido, reprocessar localmente; senão status “not_recoverable_from_metadata”, aguardando nova autorização de coleta. **Proibido:** marcar evidência encontrada apenas por HTTP 200 ou reconstruir corpo pelos 64 caracteres SHA. **Prova:** teste 200 JSON válido gerando documento e 200 JSON não suportado bloqueado COM motivo.

**R02. HTTP 200, parsing OK, falha ao registrar documento/claim:** gravar fase e chave da falha, verificar se documento/tópico/entidade/claim parcial foi persistido; retomar apenas operações idempotentes com IDs iguais e verificação de hash/proveniência. **Proibido:** repetir HTTP para consertar transação SQLite.

**R03. Corpo não pode ser retido por termos/direitos:** registrar resposta no formato permitido, digest/metadata/código de falha e impossibilidade de replay; só afirmar evidência obtida se há material rastreável suficiente. **Proibido:** guardar artigo inteiro escondido em logs.

**R04. HTTP 304/ETag sem modificação:** atualizar observação, não criar pauta, não chamar triagem nem escritor; não consumir orçamento editorial SIWC. **Prova:** dois scans idênticos sem segunda pauta.

**R05. HTTP 401/403/login/paywall:** bloquear fonte específica com motivo e respetivos limites, sem contorno; usar outra fonte previamente permitida se existir; senão hold_source. **Proibido:** simular login, usar cookies de pessoa ou fonte espelhada para burlar política.

**R06. HTTP 404/410:** marcar fonte/link removido, manter snapshot histórico e invalidar prova atual quando necessário; tentar alternativa autorizada. **Proibido:** apagar citações passadas ou insistir em endpoint removido.

**R07. HTTP 429/Retry-After:** respeitar janela, pausar somente aquele domínio, não consultar outro endpoint do mesmo host para driblar; cache e outras fontes autorizadas podem seguir. **Prova:** quota persistida após reinício.

**R08. Timeout, reset, TLS, DNS, resposta parcial:** deixar status e bytes/digest quando disponíveis; se requisição pode ter atingido o servidor, não fazer retry incerto cego. Aplicar política de reconciliação/backoff. **Proibido:** nova requisição após orçamento total sem autorização.

**R09. URL redireciona para host não permitido, IP privado/reservado, TLS não confiável, token em URL:** bloquear rota e registrar origem; jamais “corrigir” removendo proteção SSRF. **Prova:** testes de URLs hostil e redirecionamento em loopback isolado.

**R10. Robots/termos não verificados ou proíbem coleta:** hold da fonte e registro de política, não de toda edição. **Proibido:** converter falha de permissão em “o site não respondeu”.

**R11. Fonte replicadora:** ligar cadeia de republicações ao primeiro publicador rastreável. **Proibido:** tratar 10 cópias idênticas como 10 confirmações independentes.

**R12. RSS repetido / título corrigido / release atualizado:** dedupe por snapshot/evento; se há alteração material, nova versão ligada ao mesmo documento/assunto, invalidando apenas claims afetados.

**R13. API JSON com formatos alternativos:** parser selecionado por SourceProfile/version, com campos obrigatórios e tolerância a metadados opcionais; schema desconhecido gera parser_unsupported preciso. **Proibido:** aceitar qualquer JSON como alegação oficial.

**R14. Conteúdo com caracteres especiais, emojis, Unicode, barra, aspas, colchetes, HTML:** texto original intacto, escape no renderer e IDs/caminhos próprios. **Proibido:** usar título em path sem higienização ou truncar prosa para caber em slug.

**R15. Fonte sem documentos de notícia relevante:** encerrar scan “no_new_story”, atualizar histórico e permitir novo scan agendado quando autorizado. **Proibido:** colocar notícia fictícia no fluxo real.

**R16. Total de requisições esgotado (ENG-011 4/4):** bloquear novas consultas, não alterar budget retroativamente, mostrar quota por missão/host e preservar dados. **Proibido:** usar browsing manual do Codex como substituto invisível de execução Radar.

**R17. Resposta válida mas sem corpo retido no ENG-011:** investigar metadata real e etapas persistidas, identificar a primeira exceção técnica e formular correção verificável com fixture derivada de **esquema conhecido**, sem alegar replay literal do conteúdo perdido. Nova coleta só com autorização posterior específica.

### B2. Triagem, dossiê, editor e identidade

**E01. Agente cita event_id, mas candidato tem item_id:** resolver por índice tipado de relações batch→event→document→item, validando origem; nunca match parcial por substring. Não chamar triagem novamente.

**E02. Triagem classifica “monitoramento”:** preservar status e encaminhar ao editor como opção condicionada a ângulo e evidência; não descartar automaticamente nem promover como aprovado sem editor.

**E03. Triagem escolhe candidato ausente do lote:** rejeitar seleção específica, manter saída bruta, permitir uma correção estrutural determinística se houver referência equivalente verificável; caso contrário hold/editorial clarification or next batch, sem inventar candidato.

**E04. Sem notícia adequada:** no_story_yet, seguir a operação dos demais setores, não criar pauta sintética.

**E05. Investigador entrega claim_id em frase natural:** preservar frase; gerar claim_id seguro/versionado e persistir mapeamento, sem mudar texto semântico nem pedir nova chamada. Reexecutar validação do mesmo bruto.

**E06. Investigador gera claim sem evidência real:** marcar unverified/open_question, nunca transformá-lo em official_statement por tipo suposto.

**E07. Dossiê contém fonte não realmente obtida:** source_candidate_unread, não classe de prova; editor pode solicitar busca autorizada ou tratar como pendência.

**E08. Editor seleciona pauta/tag errado ou ausente:** validar IDs no lote/dossiê atual, devolver erro tipado; correção só se correspondência unívoca e auditável; caso contrário hold com justificativa, sem criar evento fictício.

**E09. Editor escolhe persona inválida:** rejeitar handoff; preservar resposta; pedir reatribuição apenas se não houver regra segura e sem gastar novamente só para formato mal escrito.

**E10. DNA sofre strip / trim / newline no carregamento:** falha de contrato do Motor, preservar bytes originais, validar SHA sobre arquivo exato; reabrir tarefa pré-SIWC com mesmo perfil e sem alterar prompt por fora. **Reproduzir o defeito real ENG-011.**

**E11. Hash do DNA realmente diverge do manifesto aprovado:** hold bloqueante de identidade; não aceitar “quase igual” e não corrigir arbitrariamente. Necessita verificação de fonte da persona e direção.

**E12. Linguagem de auditoria domina o brief:** editor deve fornecer perguntas e ângulo naturais, e mecanismo separar metadata de fontes/escopo dos parágrafos editoriais; testar original 009 e piloto A/B controlado SEM mudar DNA por palpite.

### B3. Fila, contratos, SIWC e recuperação

**Q01. Duplicidade de fonte já cadastrada no resume:** verificar source_id, endpoint, permissões, políticas, metadados e hashes; reutilizar se tudo consistente, senão hold de conflito. Nunca falhar só por INSERT repetido de mesmo registro. **ENG-011 real.**

**Q02. Política congelada tem tuplas e JSON salvo tem listas:** comparar valores canônicos JSON e campos de autorização completos, preservando snapshot/assinatura; não converter diferença REAL em equivalência falsa. **ENG-011 real.**

**Q03. Agente concluiu, Motor falha depois ao montar AgentResultEnvelope:** recuperar response bytes + SHA + schema de papel; aplicar adaptador determinístico versionado em DERIVADO; marcar external_output_recovered, sem nova chamada. **ENG-011 investigador e revisões.**

**Q04. Agente concluído, tarefa no banco succeeded, runner geral “blocked”:** separar tarefa cognitiva concluída da fase consumidora bloqueada; recuperar no último limite seguro sem reapresentar prompt.

**Q05. Duas tentativas de task registradas mas apenas uma com external_request_started:** relatório deve discriminar attempts de fila de chamadas externas reais; cobrança não inferida pelo contador de tasks.

**Q06. external_request_started=true, resposta incompleta e execução desconhecida:** uncertain, sem retry automático, reconciliar por ID/recibo quando autorizado ou hold; não declarar failed-safe apenas porque não recebeu callback.

**Q07. Reinício de Windows ou queda de energia entre chamada e persistência:** sobreviver com journal/intent e status uncertain, não reenviar até reconciliação; backup e replay de ledger testados.

**Q08. Lease expirou antes de qualquer efeito externo:** recuperar conforme AgentQueue, fencing token e idempotência; só dono vigente muda estado.

**Q09. Lease expirou DEPOIS de efeito externo:** estado uncertain e só reconciliação, não novo worker duplicado.

**Q10. Duas instâncias tentam mesmo task:** exclusão por claim lease, dedupe por idempotency key e fencing; somente uma chamada confirmada, sem perda do resultado.

**Q11. Schema evoluiu e resposta antiga é de versão anterior:** adapter versionado com teste de migração, preservação de originais; nunca impor esquema novo destrutivo ao ledger.

**Q12. Mudança no perfil ou no hash de papel durante execução:** preservar perfil congelado daquela tarefa; uso futuro requer versão nova e compatibilidade explícita, não reconstrução silenciosa de resultados passados.

**Q13. Input bruto inclui prompt injection em notícia/fórum:** como dado não confiável, nunca executar instrução externa, URLs arbitrárias, mudanças de modelo, escopo ou credenciais. Logar tentativa em forma saneada.

**Q14. Falha de JSON estruturado do LLM:** conservar resposta original; se reparo formal determinístico seguro (p.ex. campo derivável de metadado autenticado), reparar e auditar; se semântica ausente/ambígua, hold ou eventual pedido novo limitado e justificado, não “alucinar” preenchimento.

**Q15. ResultEnvelope válido mas downstream espera campo da camada errada:** adaptador tipado e regressão ponta a ponta; não adicionar .get(default) silencioso que esconda ausência de evidência obrigatória.

**Q16. Chamada SIWC autorizada mas cota Plus indisponível:** preservar tasks; aguardar renovação, não migrar a API paga ou outras credenciais arbitrariamente. Métricas devem distinguir disponibilidade SIWC de percentual visto no Codex.

**Q17. Contexto muito grande/histórico de 86.813 caracteres de persona mais dossiê:** não truncar DNA aprovado por conveniência; otimizar demais contextos, selecionar fontes relevantes sem alterar hashes; se limite real inviabiliza, bloquear explicitamente.

**Q18. Uso/latência da resposta anterior preservado:** reportar um recibo por chamada real e não duplicar tokens ao reprocessar output.

**Q19. Erro de filesystem/caminho Windows/Unicode/JSON:** paths internos gerados por IDs estáveis; bloquear path traversal e nomes reservados, suportar separadores/acentos/CRLF; fonte e artigo preservados.

**Q20. Banco de dados parcialmente migrado:** backup e operação transacional, validação de versão antes de DDL, rollback comprovado, nada de alterar runtime pessoal apenas porque testes passaram.

### B4. Pesquisa natural e retorno ao mesmo jornalista

**P01. Pedido tem dois-pontos, barras, aspas, espaço/acentos:** mediator extrai intenção sobre brief + evidência sem igualdade literal; conserva pergunta original, tipa os campos com autorização do Motor.

**P02. Pedido de pesquisa de hardware vem de Nina:** escolher perfil pelo tema e evidências, não exclusivamente pelo personagem.

**P03. Perguntas múltiplas compatíveis:** consolidar dentro do orçamento e contrato versionado; preservar ambas. Perguntas incompatíveis: enfileirar a prioritária e registrar a outra como pendente, não perder silenciosamente.

**P04. Fonte conhecida já está no RadarStore:** index/cache antes de nova requisição; se documentos e claims atendem ao pedido e direitos/época são válidos, não chamar a rede.

**P05. Pedido aponta URL fora da allowlist:** bloquear a URL, não usar scraping manual do Codex como bypass; outro domínio permitido só por política.

**P06. Pesquisa HTTP 200, conteúdo extraído, mas sem claim de status obrigatório:** packet parcial com documentos verificáveis e missing_evidence explícito; editor decide se essa evidência sustenta recorte menor ou se precisa de fonte independente.

**P07. Pesquisa retorna blocked sem docs e sem claims:** NÃO gerar continuação de redator vazia, NÃO gastar SIWC com pergunta insolúvel; trazer reason_code e próximo passo seguro. **Falha histórica ENG-011.**

**P08. Pesquisa retorna not_found:** registrar ausência e opções de outra fonte autorizada, pauta menor ou hold; sem inventar resposta.

**P09. Pesquisa parcial com alegações úteis:** entregar somente material efetivamente verificado e status de lacunas; não declarar conclusão. Possível continuação com redator apenas se editor/criticidade permitirem, e justificativa rastreável.

**P10. Pesquisa traz documento antigo ou versão de outro jogo/projeto:** rejeitar por entidade, tag, data e story_revision_id; não poluir claims vigentes.

**P11. Outra matéria recebe ResearchPacket por engano:** bloquear handoff; exigir igualdade de story_id, story_revision_id, requester_role/persona, parent_task_id e hashes.

**P12. Pesquisa retorna alegação sem fonte de proveniência:** bloquear claim, não atribuir ao publisher por inferência.

**P13. Limite por domínio/mission exaurido:** cache ou outra fonte já aprovada; se nenhuma, hold da solicitação, não derrubar outros artigos.

**P14. Mesmo pedido reenfileirado após restart:** mesma idempotency key → uma execução e um packet; não duplicar custo.

**P15. Packet com dado novo válido chega ao jornalismo:** nova continuação do MESMO artigo, mesma persona, DNA e brief + delta de evidências; texto integral versão N+1 e novo SHA; nunca escrever matéria diferente em substituição silenciosa.

**P16. Falta de evidência central não pode ser suprida:** editor decide reduzir âmbito, trocar pauta ou manter hold; qualquer texto final deve evitar afirmar aquilo que não se verificou.

**P17. Fonte nova contradiz texto anterior:** invalidar veredicto factual da versão afetada, atualizar ClaimLedger e exigir revisão de conteúdo; não manter PASS de hash antigo.

### B5. Editorial, direitos e navegador

**C01. Redator termina com seções mas texto faz afirmação não citada:** fact_checker marca claim/trecho; redator corrige ou retira; não aprovar com “fonte não especificada”.

**C02. Artigo incorpora status internos (curator_notes_only, rights_revalidated=false, protocol, quota):** metadados permanecem de bastidor; texto é refeito por decisão editorial sem reescrever o DNA; evitar burocracia narrativa. **Causa plausível 009, exigindo comparação real.**

**C03. Campo claim_refs inclui radar://document em vez de claim ID:** preservar bruto e citações nas seções; reconhecer equivalência apenas se referência existe e é autorizada; mover representação interna a campo correto com trilha, sem inventar conteúdo. **ENG-011.**

**C04. Versão N passa no fact-check mas N+1 altera fatos:** veredicto vira stale; checagem proporcional à mudança semântica, ligada ao hash N+1. Não copiar “PASS” anterior.

**C05. Revisor editorial pede mudança de estilo:** mensagem clara ao mesmo persona_writer, revisão nova de texto; não criar chamada de investigadora sem necessidade.

**C06. Revisor pede fonte nova:** pesquisa via Motor; não reabrir para reescrever tudo sem novos dados; limites epistêmicos aplicados.

**C07. Duas revisões similares sem novo fundamento:** parar loop, apresentar diagnóstico e revisão humana de qualidade, sem consumir franquia indefinidamente.

**C08. Imagem sem licença válida para web/produção:** procurar ativo alternativo autorizado; não publicar ou declarar experiência ilustrada concluída. Para preview interno, identificar explicitamente o escopo e nunca estendê-lo automaticamente.

**C09. Imagem original gerada é meramente ilustrativa:** identificar como tal, não atribuir screenshot, gameplay ou prova documental.

**C10. Arquivo de imagem existe, mas link no HTML está quebrado:** validar caminho seguro e resposta HTTP efetiva, não apenas hash PNG em disco.

**C11. file:// bloqueado por navegador:** servir HTTP loopback legítimo, retornar URL funcional, testar DOM/viewport e imagem carregada; nunca declarar “visual validado” apenas com testes de bytes. **ENG-010.**

**C12. Browser indisponível ao Codex:** marcar NOT_VISUALLY_VALIDATED e oferecer URL/instrução exata ao diretor; não inventar screenshot/inspeção.

**C13. Layout usa revisão desatualizada:** invalidar composição e rerenderizar versão corrente; velho preview deve ser claramente obsoleto ou inacessível.

**C14. Mobile ilegível ou animação impede leitura:** corrigir CSS/acessibilidade e repetir prova no viewport real; modo sem folhear deve continuar operacional.

**C15. Uma matéria da edição está em hold:** manter demais processáveis, editor pode designar pauta reserva; diretor decide exclusão/alteração de composição quando gatilho humano exigido.

**C16. Gate simulado aprovado e published=false:** nunca confundir com aprovação humana. **ENG-010.**

**C17. Publicação sem aprovação explícita para aquela revisão/canal:** bloquear; mesmo que agentes, imagem e navegador tenham PASS.

**C18. Material editorial é selecionado para anúncio/afiliado:** bloquear separação de acervos e exigir ativo publicitário licenciado, não “aproveitar” screenshot do editorial.

## C. Fluxos narrados de exemplo e recuperação

### C1. Caminho feliz observável (pauta NÃO dada pelo programador)
1. Scheduler autorizado inicia Radar uma única vez com fontes publicamente acessíveis e política previamente ratificada.
2. Conector salva snapshot e extrai candidato com URL humana/ID de documento/evento; resultados oficiais e independentes se distinguem.
3. Triagem real examina lote e devolve classificação e refs; Motor reconcilia IDs.
4. Investigador real cria dossiê com claims e perguntas; Motor normaliza IDs técnicos, verifica fontes e persiste.
5. Editor real escolhe um item elegível e persona apropriada; decisão citável e motivo arquivado.
6. Journalist real recebe DNA intacto, pauta, evidências, pesquisa opcional e contexto editorial natural; escreve original integral.
7. Se pede detalhe externo, Motor tipa intenção, consulta cache e então conector sob política; retorna packet verificável ao mesmo story/revision.
8. Jornalista real integra os dados e entrega revisão integral, ou editor opta por ângulo que não dependa da evidência ausente.
9. Fact-checker REAL confere as alegações da versão; se achados, jornalista REAL corrige; rechecagem apenas do que mudou.
10. Revisor editorial REAL avalia voz, ritmo, utilidade, coerência e não deixa texto burocrático.
11. Acervo propõe mídia elegível; direitos confirmados; layout/composição geram HTML real com imagem.
12. HTTP local abre no Chrome/outro navegador suportado, imagem e texto aparecem, screenshots/resultado visual confirmam versão e mobile/desktop.
13. Tudo permanece como PREVIEW interno aguardando aprovação humana, published=false. Relatório aponta cada evidência e custos.

### C2. Falha na fonte principal sem perder a edição
Conector marca HTTP blocked/parser unsupported com reason_code → fonte recebe hold → Radar consulta índice/alternativa previamente autorizada sem violar quota → triagem só de candidatos válidos → editor pode escolher reserva; se nenhum, sem matéria, com registro de ausência. Outras pautas não param.

### C3. Redator solicita evidência que nunca chega
Pedido natural do jornalista persistido → Motor tenta índice → checa escopo/orçamento → fonte externa falha → packet blocked com causa → Router NÃO gera continuação vazia → editor recebe “central/contornável?” → se contornável, remove afirmação e redator pode escrever com base suficiente; senão hold story e próximo ciclo quando autorizado. Nenhuma afirmação inventada e nenhum SIWC desperdiçado em packet vazio.

### C4. Resposta SIWC concluída e rejeitada por tipo/identificador
SIWC response durable + usage receipt + hash → Motor falha na conversão → task cognitiva preservada → adapter versionado reconcilia somente tipo/ID sem semântica → valida hash/proveniência → consumidor retoma → 0 nova chamada SIWC → ledger registra artifact original e derivado. Se reparo exigiria inventar conteúdo, hold para análise; não chamar agente apenas porque JavaScript/Python esperava campo literal.

### C5. Queda de energia durante chamada
Antes da saída de rede: task pode ser retomada com lease/fencing; depois do sinal de solicitação externa: uncertain até reconciliar. Se resposta durável aparece, recupera; se não, não repetir automaticamente. Director vê a pauta “aguarda reconciliação”, e outras pautas progridem.

### C6. Preview incompleto
Matéria real arquivada, image asset autorizado → renderer gera HTML → servidor 127.0.0.1 sobe → Chrome responde mas imagem 404 → compositor aponta caminho, direitos, versão → corrige e renderiza sem chamar jornalista → screenshot real confirma → gate humano ainda pendente. Essa rotina não consome tokens da redação.

## D. Diagnóstico específico da ENG-CODEX-011 antes de qualquer nova consulta

Ponto factual: 4/4 requisições autorizadas, última em endpoint público de Proton 11.0-2e com HTTP 200, 2.120 bytes, hash SHA-256 reportado, mas provider packet blocked sem docs/claims e sem alegação official_statement. Causa exata **DESCONHECIDA** porque corpo/exception não foram persistidos.

Obrigação de engenharia:
1. Descrever cada transição da chamada: quota guard → transport → FetchResult → parser/metadata → IncrementalRadarService → RadarStore observação/documento → GitHubReleaseResearchProvider → register entity/topic/claim → ResearchService._validate_provider_references → ResearchPacket → ResearchResultRouter.
2. Inspecionar as linhas reais locais do banco e logs: source registered? cache? snapshot? document? topic? entity? claim? source links? pacote/constraints? ledger de chamadas e ponto de commit? NÃO fazer novo HTTP nem SIWC nesta fase.
3. Verificar em código as oportunidades de falha: parser exigindo tag_name, tipo de URL do documento, idioma, data, política de acesso, ID, validação de relações/documento/origem e link duplicado. **Não afirmar qual é a causa sem artefato que a prove.**
4. Verificar como o ResearchService captura qualquer Exception e converte a texto de classe. Migrar para reason_code/phase tipados com logging restrito de diagnósticos, preservando segredo/direito; sem liberar traceback completo público.
5. Quando não existe resposta bruta, **não pode inventar conteúdo equivalente**. Reproduzir o contrato com uma fixture pública de esquema/propriedades representativas e comparar caminhos de sucesso/negativo; reconhecer que isso não é replay exato da chamada perdida.
6. Corrigir transação/idempotência se o erro for interno; se depender dos 2.120 bytes perdidos, produzir relatório de impossibilidade e preparar política de retenção mínima permitida para a PRÓXIMA coleta autorizada.
7. Depois da correção, poder fazer preview interno com qualquer versão real arquivada, marcada RASCUNHO; não exigir primeiro novo custo de pesquisa para validar renderer. Matéria sem prova central permanece bloqueada no gate editorial.
8. Nenhuma ampliação silenciosa da autorização ENG-011. A futura prova com pesquisa pública deve ter autorização e orçamento explícitos da nova missão.

## E. Plano de implantação por unidades, com saída verificável

**U00 Inventário de verdade:** mapear todos os contratos e branches, decisões antigas/novas, status do código, referência da missão 011, filas e dados privados. Entrega: matriz de rastreabilidade e dependências reais. Sem consumir SIWC.

**U01 Observabilidade e razão de bloqueio:** melhorar transporte/parser/provider/ResearchService para erro tipado, métricas e redaction, preservando corpo apenas quando licenciado. Regressões para 200 parse success/fail, exceptions, zero docs, dedupe, proxy/SSRF, quota. Corrigir root cause se comprovável.

**U02 Normalização de fronteiras:** tipar IDs e eventos, canonical JSON sem editar bytes/hashes, adapters de schema, compatibilidade com histórico, idempotência no source registration, testes unicode/CRLF, comparação policy tuple/list e claims legíveis. E2E sintético de integração útil MAS SEM confundi-lo com piloto real.

**U03 Recuperação geral:** unificar recovery por última fronteira durável, sem proliferar handlers por string de erro no runner; distinguir pré-externo/pós-externo/uncertain; leases, backoff, receipt, locks; executar fault injection em cada fronteira e provar ausência de chamadas duplicadas.

**U04 Multi-fonte Radar:** arquitetura de conectores oficiais/independentes/comunidade dentro de allowlists específicas; validação ética/legal, enriquecimento, lineage, dedupe, seleção de candidatos e indexação. Construir e testar offline até nova autorização de coleta real; GitHub continua conector específico, NÃO a única fonte.

**U05 Triagem-investigador-editor:** handoffs tipados com IDs coerentes, “monitoramento” e carteira, escolha real agente, matriz de papéis por tema; teste de casos falsos/rumores/sem pauta.

**U06 Redação-pesquisa de retorno:** request natural→ResearchRequest→ResearchService→ResearchPacket→mesmo redator com nova versão. Testar packet encontrado, parcial, vazio, bloqueado, ambiguous, fora de escopo, stale, idempotente, orçamento. Usar respostas reais 011 arquivadas quando válidas, sem SIWC novo só por falha interna.

**U07 Checagem-revisão:** fact-check e revisão editorial independentes, hash de versão vigente, correction loop limitado, texto leitor versus audit metadata e qualidade P/T/J/F sem alterar DNA.

**U08 Imagem-layout-visual:** renderizar uma versão interna REAL já existente; servir HTTP loopback; conferir no navegador o texto e imagem. Separar “visual de rascunho validado” de “matéria editoral aprovada”.

**U09 Edição multipauta/autorizações:** composição com story em hold sem travar tudo, direitos por asset/canal, reviewer human gate, publicação/despesa desligadas e protegidas.

**U10 Piloto real final autorizado:** 1 pauta inédita descoberta pelo Radar em fontes externas diversificadas autorizadas, nenhuma fixture como input, agentes realmente executando papéis requeridos; pesquisa complementar devolvida e utilizada; fact-check/revisão; ilustração com direitos; navegador; relatório de custo. Realizar **após** U01–U09 passarem sem depender de retries humanos de schema. Não declarar PASS com incidentes críticos pendentes.

Para CADA unidade, Codex deve entregar: commits/PR draft isolados, diff legível, lista arquivos tocados, contratos versão/hash, testes positivos/negativos com resultado, artefatos reais quando aplicável, status HONESTO, riscos, próxima unidade. Sem PRs empilhadas caoticamente sem plano de reconciliação. Não gastar franquia apenas repetindo toda suíte enquanto uma correção localizada ainda não passou.

## F. Bateria de aceitação final (checks que realmente importam)

**F1 Autonomia:** Radar descobre história real sem título fornecido por engenheiro, editor agentico escolhe matéria/persona; transições persistidas.

**F2 Identidade:** três perfis aprovados carregados íntegros e distinção perceptível em textos, com ao menos uma revisão humana comparativa posterior; nenhuma mudança silenciosa de DNA.

**F3 Pesquisa:** pedido em linguagem natural com pontuação e paráfrase, retorno real do Radar como ResearchPacket COM documentos/claims, mesmo story/revision; no caso de falha, nenhum continuação SIWC inútil.

**F4 Factualidade:** cada alegação relevante atribuída e rastreável, rumorzinho marcado, ausência/contradição não fabricada.

**F5 Revisão:** checagem real, revisão editorial real, hashes vigentes e versões imutáveis; falha de revisão ativa correção ou hold, não pass automático.

**F6 Imagem:** asset procedente e permissões legíveis para preview, integrado à matéria vigente.

**F7 Browser:** URL HTTP loopback realmente aberta, texto e imagem observados, screenshot ou relatório do navegador, mobile e desktop; file:// não é requisito.

**F8 Resiliência:** fault injection e reinício em 20+ pontos críticos; resposta SIWC persistida jamais requer repetir chamada para mudar ID, JSON, path, hash ou roteamento. Duplicação de fonte/lease/entrega não causa corrida nem custo extra.

**F9 Multi-pauta:** uma bloqueada não paralisa as demais; editor escolhe reserva ou mantém edição parcialmente pronta; aprovação pública continua humana.

**F10 Custo:** por cada inferência: papel, input/output/reasoning/total, latência, status e recibo; franquia observada separada de consumo de tokens e de custo de API. Sem APIs pagas por fallback não autorizado.

**F11 Segurança/direitos:** host fora de escopo, SSRF, credenciais em URL, dados privados, licença restritiva, imagem sem direito ou publicação não autorizada são bloqueados deliberadamente. Segurança NÃO é bug a “consertar” relaxando políticas.

**F12 Entrega final:** link de PR, relatório de evidências, originais/revisões íntegros e privados, visual comprovado e instrução curta de acesso ao diretor; sem alegar E2E se uma condição indispensável falhou.

## G. Comando ao Codex — interpretação correta

Leia esta matriz junto da arquitetura-mestra. Primeiro audite os contratos existentes; em seguida corrija-os por **módulo e responsabilidade**, não por mais um remendo nominal de exception no runner. Não refaça uma chamada SIWC para reparar incompatibilidade de bytes, JSON, ID, source row, claim_refs ou parser. Ao final de cada unidade, comprove o resultado e a ausência de regressões. A meta não é “proibir qualquer pausa”, mas permitir que a operação continue segura, econômica e auditavelmente, estacionando apenas aquilo que não pode legal ou factualmente progredir. Publicação, acesso novo, custo pago e modificações de DNA não ficam implicitamente autorizados.
