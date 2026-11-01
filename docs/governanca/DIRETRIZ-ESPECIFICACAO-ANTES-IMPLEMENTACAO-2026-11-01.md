# Revista Back — Diretriz da Direção: arquitetura e contrato antes da implementação

**Origem:** discussão entre Direção e Fundador 6, 01/11/2026.
**Natureza:** diretriz de governança do desenvolvimento. **Os campos e o formato final da memória editorial continuam em estudo; este documento não é uma ordem ao Codex.**

## Problema identificado pela Direção

Pedidos anteriores ao Codex detalharam o objetivo, mas deixaram em aberto escolhas estruturais que deveriam ter sido discutidas e definidas pelo Fundador e pela Direção: quais campos, seus significados e variantes, identificadores, vinculação dos fatos a suas fontes, regras de não duplicação, ciclo de vida e quantidade de contexto transmitida aos agentes. É possível construir um código tecnicamente funcional que ainda assim seja inadequado do ponto de vista editorial, do custo de inferência e da operação contínua.

A Direção determina a mudança de método: o Fundador assume elaboração e discussão da arquitetura funcional/informacional, e o Codex implementa os contratos aprovados, aponta impossibilidades e conflitos encontrados no código, propõe alternativas e pede deliberação quando uma decisão extrapolar sua alçada. Codex conserva decisões de implementação de baixo nível que não alterem contratos, comportamento editorial nem limites acordados.

## Regras para próximas ordens de engenharia

1. **Especificar antes de construir:** definir significado de cada campo, tipos, obrigatoriedade, aliases/variações, proveniência, identificadores, referência a dados canônicos, regras de atualização e ciclo de vida. Distinguir decisões aprovadas de hipóteses e opções técnicas.
2. **Não perder riqueza do coletor:** conservar a captura original íntegra e verificável; separar o dado bruto de uma representação normalizada e de uma visão enxuta para consumo de agentes. Um campo não reconhecido deve ser sinalizado, não silenciosamente descartado.
3. **Não repetir informação sem necessidade:** registrar conteúdo repetido uma vez no armazenamento canônico, relacionar por IDs e guardar no diálogo apenas referência, diferença/novidade, estado e justificativa. Não confundir preservação auditável de eventos com material que precisa ser reenviado ao modelo a cada turno.
4. **Contexto por papel:** jornalista e revisor recebem recortes adequados à tarefa, só questões pendentes e fontes relevantes, em vez de histórico acumulado sem controle. Reaproveitar evidências sem ocultar incertezas nem promover alegações do coletor a provas.
5. **Medição obrigatória:** verificar de onde vêm os aproximadamente 380 mil e 319 mil caracteres apontados no teste TUXEDO. São tamanhos de payload, **não medição do tamanho do banco de memória**. Identificar repetição de conteúdo e medir tokens, tamanho por componente e custo antes de fixar limites.
6. **Contratos testáveis:** especificar testes de nenhuma perda de campos, deduplicação sem perda de proveniência, mudança de estado por issue, reconstituição após falha, isolamento entre matérias e orçamento de contexto por papel. O Codex não deve escolher sozinho a política editorial diante de uma condição não prevista.
7. **Responsabilidades:** Diretor homologa objetivos, escolhas editoriais e limites; Fundador desenha contratos e valida coerência; Codex examina viabilidade, implementa, testa e relata achados com propostas alternativas para nova deliberação quando necessário.

## Situação específica da factory Censurado

A implementação de dossiês, diálogo e memória reportada pelo Codex estava apenas em commits locais no último checkpoint, sem merge. A Direção e o Fundador precisam auditar o modelo de dados, sua eventual redundância e a montagem dos prompts antes de autorizar ativação contínua. **Não interpretar teste E2E funcional como homologação do formato da memória.**

## Próximo trabalho do Fundador

Projetar e levar à Direção, em etapas curtas, (a) contrato do coletor e aliases, (b) armazenamento canônico e referências, (c) protocolo de questões/turnos e regras de compactação, (d) composição do contexto por papel, (e) teste de aceitação e orçamentos. **Ainda não há autorização para nova reestruturação ou instrução de correção ao Codex por efeito deste registro.**
