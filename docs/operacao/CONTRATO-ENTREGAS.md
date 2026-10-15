# Contrato de entrega entre setores

Todo documento de especificação deve trazer cabeçalho textual simples:

- **Setor responsável**
- **Identificador do artefato** (slug curto e estável)
- **Versão** (ex.: v0.1)
- **Status**: proposta | em_revisao | aprovado | bloqueado | implementado | validado
- **Data de atualização**
- **Dependências** (links para outros documentos/Issues)
- **Aprovador** (quando houver)

## Entrega mínima

1. Objetivo e exclusões.
2. Requisitos e decisões tomadas, identificando o que é hipótese.
3. Exemplos concretos e critérios verificáveis de aceitação.
4. Fontes de informação/referências e autorizações, quando exigidas.
5. Integrações e interfaces com outros setores.
6. Limites de desempenho, custo, acessibilidade e segurança, se relevantes.
7. Pendências e links para Issues.
8. Evidência de testes ou indicação explícita de "não testado".

## Regra especial para o Codex

Ler documentos `aprovado`; gerar tarefas implementáveis com entradas, saídas, testes e estado. Se as informações estiverem incompletas, registrar Issue, nunca improvisar personalidade, direito de mídia ou autorização comercial. Entregas experimentais ficam isoladas e não entram em produção sem aceite.

## Auditoria

Commits/PRs apontam Issue vinculada quando houver. O status em documento deve coincidir com o comentário da Issue. O registro do GitHub é o histórico, não a memória de conversas.
