# ENG-CODEX-007 — LEIA PRIMEIRO: novo ciclo de execução sequencial

**Direção → Fundador 2 → Codex | 25/10/2026**
**Status:** pacote completo de instrução/contratos para execução técnica; a implementação pelo Codex **não foi realizada** por esta entrega documental.
**Objetivo:** transformar a fábrica offline já demonstrada em linha de montagem **de papéis especializados sob demanda**, criar Radar determinístico de notícias/rumores e pesquisa especializada compartilhada, e testar os três jornalistas isolados e dentro da fábrica usando acesso SIWC local permitido e controlado.

## Leia nesta ordem

1. [Regimento interno da fábrica](../operacao/REGIMENTO-INTERNO-FABRICA-EDITORIAL-v0.1.md): normas e precedências, rumor/atribuição, autonomia de engenharia, segurança e gates.
2. [Catálogo e DNA funcional dos agentes](ENG-CODEX-007-CATALOGO-E-DNA-FUNCIONAL-DOS-AGENTES-v0.1.md): **6 papéis frequentes de IA + 2 opcionais**, schemas, input/output, ferramentas, responsabilidades e testes; jornalista é persona do redator, **não** processo extra por princípio.
3. [Radar geral e pesquisas sob demanda](ENG-CODEX-007-RADAR-FONTES-RUMORES-E-PESQUISA-v0.1.md): conectores RSS/APIs/HTTP permitidos, cache/diffs, fonte e linhagem de rumor, pessoas/entrevistas, 10+10 pautas, 3–6 rodadas simuladas, perfis hardware/games/criadores compartilhados e `ResearchRequest`.
4. [Ordem contínua E01–E19](ENG-CODEX-007-ORDEM-DE-SERVICO-EXECUCAO-CONTINUA-v0.1.md): sequência sem microaprovações para código/testes/commits/checkpoints, provas offline, ponte real SIWC, testes isolados/integrados dos três jornalistas, limites e handoff.
5. Referências anteriores: [arquitetura de agentes 20/10](ARQUITETURA-AGENTES-ACERVO-VISUAL-E-COMPOSICAO-2026-10-20.md), [anteprojeto Plus](ANTEPROJETO-ORQUESTRACAO-AGENTES-E-PLUS-2026-10-19.md), PRs #8/#10/#18/#24/#25/#26 e #13/#14/#19/#27; Issues #20/#23/#28.

## Decisões e premissas não confundíveis

- **6+2 são perfis funcionais candidatos**, não oito LLMs permanentes, oito agentes já implementados nem quota garantida. Avaliar custo/benefício do desmembramento/reunião dos papéis com evidência.
- **Coleta (determinística) ≠ investigação (IA)**; rumor atribuível pode ser pauta se sua incerteza for transparente. Publicador não equivale a fonte original e citar não concede direitos de copiar.
- **Um ResearchService, múltiplos perfis de pesquisa**: Carranca/Beto/Nina e checador podem pedir dados complementares por fila. O Motor desperta funções; agentes não mandam livremente uns nos outros.
- **Situação atual confirmada no GitHub:** ENG-CODEX-006 tem 95/95 testes reportados, uma `factory-demo` de uma pauta por execução, pass 15/15, revise 18/18, zero SIWC real nessa factory, sem merge, publicação ou versão final de leitor. ENG-CODEX-004 fez **prova local SIWC Luna Max real** anteriormente com perfil neutro, não com o trio.
- **Não repetir construção de autenticação** nem falsificar “19/19” sem reconciliar a última missão local; abrir nova branch em cima da ponta de integração verificada.
- **Autonomia operacional expressa:** Codex **não deve parar a cada teste ou commit**; finalizar E01–E19 conforme dependências e limites, checkpoints após cada etapa. Não burlar confirmações impostas pela plataforma; publicação/gastos/merge/deploy e novas credenciais continuam atos protegidos.
- **Início de coletas recorrentes reais/default ON, VPS e produção externa são posteriores**, não desdobramento automático da sequência.
- **Artefatos pertencem ao diretório do projeto no GitHub**, checkpoints em branch de implementação. Testes reais só contam com logs sem segredo e evidência de resposta do provedor; mocks são rotulados.

## Próximo ato esperado do Codex

Ler estes quatro arquivos pelo ref desta branch de documentação, consultar os HEADs de engenharia, iniciar E01, abrir PR draft e checkpoint próprios, seguir para E02 em diante **automaticamente** após cumprir teste/commit/push por unidade. Se uma operação externa depender de consentimento ou cota, bloquear só ela e seguir código/testes offline. Reportar status com evidência por unidade e não exigir que o diretor fique confirmando ações rotineiras no PC.

**Não executar o código inteiro em um comando gigante nem esperar por uma próxima orientação após cada marco.** Preservar a mesma disciplina da série anterior: checkpoint fiel, concluídos distintos de pendentes, retomada exata após interrupção.
