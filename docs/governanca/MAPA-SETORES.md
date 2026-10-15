# Mapa dos setores — proposta organizacional v0

**Estado: proposta para validação da direção.** Cada "bloco" é um chat de planejamento especializado; não é automaticamente um processo/serviço nem um agente adicional de produção.

| Setor / bloco | Responsabilidade | Área principal |
|---|---|---|
| Direção e arquitetura (chat fundador) | Coerência geral, padrões de governança, prioridades e validação com o diretor | `docs/governanca/`, `docs/operacao/` |
| Personagens e vozes | DNA, estilo, bordões, critérios de julgamento, referência visual, continuidade da personalidade | `docs/personagens/` |
| Identidade visual e UX | Linguagem gráfica, navegação, folhas/versos, protótipos, acessibilidade, animações leves | `docs/visual/` |
| Redação e método | Pautas, fontes, síntese crítica/comunidade, revisão, modelo de reportagens e séries | `docs/redacao/` |
| Acervo e direitos | Origem de imagens, fichas individuais, permissões verificadas, bloqueios e referências | `docs/acervo/` |
| Engenharia / Codex | Ferramentas, repositórios de código futuros, orquestrador, testes e integração de entregas aprovadas | `docs/engenharia/` |
| Comercial e divulgação | Espaços vendidos, afiliados, marcas, divulgação — sem interferência editorial | `docs/comercial/` |
| Comunidade | Sugestões, feedback e moderação | `docs/comunidade/` |

**Atenção:** esta tabela descreve responsabilidades, NÃO afirma que esses chats já foram criados. Começar com poucos blocos; abrir mais apenas quando a carga real justificar. Todo setor pode ler outros setores; altera sua própria área. Exceções pedem Issue/PR.

## Fluxo entre setores

Direção define princípios -> setor prepara proposta -> direção aprova -> Engenharia implementa -> revisão/teste -> aprovação para publicar. Quando um setor precisar de outra área, abrir Issue direcionada com pergunta, impacto, links e prazo desejado. Nada depende de troca automática entre chats.

## Responsáveis e autoridades

- Diretor humano: aprovação editorial final, publicação, despesas, patrocínios, identidade pública e decisões comerciais.
- Chat fundador: proposta de arquitetura/governança; não substitui a aprovação humana.
- Setores especializados: produzem especificações e propostas, não alteram políticas globais silenciosamente.
- Codex: implementa somente requisitos aprovados e registra bloqueios.

## Admissão de novo chat

Entregar ao novo bloco: este mapa, `README.md`, `AGENTS.md`, documentos setoriais e link das Issues abertas. A cada sessão exigir consulta às versões atuais do GitHub; memória de Project não é sincronização em tempo real.
