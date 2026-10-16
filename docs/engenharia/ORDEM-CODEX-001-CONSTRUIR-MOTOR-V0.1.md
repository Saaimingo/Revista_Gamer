# ORDEM DE SERVIÇO — CODEX 001
## Construir e testar Motor Editorial v0.1

**Tipo:** execução de engenharia / primeira implementação
**Status:** execução autorizada para código local e testes, não para deploy/publicação.
**Autoridade:** diretor definiu delegação arquitetural ao chat fundador e atuação do Codex como engenheiro construtor.
**Escopo autorizado:** apenas `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md`.

Você é o **engenheiro construtor da Revista Gamer**. Sua missão não é voltar ao diagnóstico de viabilidade: é **construir e verificar** a versão 0.1 do Motor Editorial, seguindo a especificação aprovada no repositório.

### Referências obrigatórias

Repositório: https://github.com/Saaimingo/Revista_Gamer

Leia em ordem:
1. `docs/engenharia/ESPECIFICACAO-MOTOR-EDITORIAL-V0.1.md` (**contrato principal deste trabalho**);
2. `docs/governanca/BIBLIA-DO-PROJETO.md`;
3. `AGENTS.md` e `docs/governanca/DECISOES.md`;
4. `docs/engenharia/README.md`;
5. `docs/operacao/CONTRATO-ENTREGAS.md`.

Os demais documentos são contexto, não autorização para editar DNAs, pautas, capas, licenças ou publicidade.

### Execução esperada

**Construa um aplicativo Python local, com SQLite, orquestrador de estados, adaptadores determinísticos de simulação, trilha de auditoria, testes, visualização HTML/painel local e aprovação humana interna.**

Desenvolva o **fluxo vertical completo**: itens fictícios -> normalização/deduplicação -> triagem -> apuração simulada -> redação simulada -> revisão -> devolução/correção -> nova revisão -> verificação de mídia -> prévia HTML -> espera pela aprovação humana -> arquivamento interno.

Cada etapa persiste os dados e só prossegue quando as regras permitirem. Simule falha técnica recuperável, mídia de direitos pendentes e passagem inválida para demonstrar os bloqueios. Não crie interface nem mecanismo de publicação externa.

**Você está autorizado a escrever código, criar branch, commits e PR, e executar testes.** Resolva autonomamente problemas técnicos normais, escolha bibliotecas mínimas e documente decisões de engenharia. Se uma solução prevista falhar, experimente alternativa mais simples que preserve os critérios de aceite. NÃO peça ao diretor decisões triviais de implementação.

**Não** faça gastos, instale serviços externos pagos, use chaves de IA, inicie scraping, programe coletas automáticas reais, publique site, abra portas externas ou altere áreas dos outros blocos. Sem rede para o funcionamento do motor, sem LLM na simulação, sem materiais proprietários. O repositório atual pode ser público: nada confidencial deve entrar nele.

### Roteiro recomendado, adaptável pelo engenheiro

1. Inspecione o estado atual do repo e crie branch `codex/motor-editorial-v0.1` sem sobrescrever trabalho existente.
2. Implemente persistência e estados, com testes de transições, idempotência e retomada.
3. Acrescente adaptadores e fixtures fictícias que percorrem todo o circuito, incluindo revisão/retorno e direitos.
4. Implemente prévia HTML e painel/CLI local de operação interna e aprovação.
5. Execute a suíte de testes completa, corrija defeitos e documente como reproduzir.
6. Apresente PR com código, testes, exemplos, comandos executados, resultado real e pendências.

### Definição de pronto

Não basta dizer que a arquitetura é viável. É obrigatório haver **código executável**, fluxo demonstrável, persistência, bloqueios reais, aprovação humana interna e testes com resultados observados. Consulte todos os critérios de aceite da especificação principal.

Se a interface/painel não puder ser aberta no ambiente disponível, teste rotas ou funções por automação e deixe instruções concretas de como o diretor poderá abrir localmente; não afirme inspeção visual não realizada.

Se algo for impossível sob os limites acordados, reporte a restrição com evidências e uma alternativa de menor custo/complexidade. **Só interrompa para aprovação quando a mudança afetar escopo, segurança, direitos, custo ou lançamento.**

Não mescle na `main` automaticamente. Não avançar à v0.2 nem implantar produção. Ao concluir, apresente links, comandos e testes para revisão da arquitetura e do diretor.
