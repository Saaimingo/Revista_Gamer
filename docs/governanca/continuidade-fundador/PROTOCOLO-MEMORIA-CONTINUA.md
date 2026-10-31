# Protocolo permanente — registro de memória do Fundador

**Decisão expressa do diretor:** 31/10/2026. **Responsável:** bloco/chat Fundador em exercício. **Objetivo:** passagem de bastão confiável a Fundador 5, 6 etc. sem perder contexto em conversas longas.

## Regra obrigatória

Toda ocorrência relevante que **passar pelo Fundador** deve ser documentada **na mesma rodada de trabalho, ou antes de encerrar a sessão**, em `docs/governanca/continuidade-fundador/`: decisão ou mudança de rumo do diretor; entrega, teste, erro ou relatório do Codex; informação, proposta, parecer ou aprovação de outro Bloco; resultado de pesquisa decisiva; mudança de arquitetura, repositório, branch, modelo, custo ou risco; pauta pendente; pedido formal entre setores. Isso inclui **falhas e rejeições**, não apenas sucessos.

Registrar depois de cada marco, não apenas quando o chat estiver cheio. Em novas conversas, consultar este índice **antes** de sugerir reconstruções ou repetir etapas. Esta é uma obrigação de procedimento para o Fundador, **não** um agendamento em segundo plano: sem execução/ferramenta de escrita no GitHub, não é permitido dizer que o arquivo foi atualizado; preparar a anotação para aplicação posterior e comunicar a pendência ao diretor.

## Formato mínimo de cada entrada

- **Quando/quem:** data (Brasil), Fundador responsável, origem (diretor, Bloco 02–06, Codex, GitHub, observação).
- **Tema, antes/depois:** qual situação mudou.
- **Status separado:** `proposto`, `diretriz em debate`, `aprovado pelo diretor`, `implementado`, `testado em mock`, `testado real`, `bloqueado` ou `publicado`. Não trocar uma categoria por outra.
- **Evidências:** repositório, branch, PR/Issue, commit, versão, caminho de artefatos, teste, contagem, resultado; distinguir relato de terceiros de verificação independente.
- **Decisão exata:** o que o diretor aprovou, vetou ou deixou em aberto. Não promover opinião do assistente a aprovação.
- **Próxima ação e responsável:** inclusive restrições de consentimento e limites de segurança.
- **Conexões:** outro setor, documento ou incidente a consultar.

## Responsabilidades e fronteiras

1. O Fundador atualiza o **registro cronológico** e o índice. Quando houver mudança global realmente **aprovada**, atualizar/solicitar também `DECISOES.md` e `STATUS-GERAL.md` conforme governança.
2. Parecer sobre área setorial continua no caminho `docs/<setor>/analises-fundador/`, segundo `docs/operacao/PROTOCOLO-HANDOFF.md`; a memória central guarda resumo e **link**, sem substituir o documento setorial nem editar um DNA/contrato alheio.
3. Relatórios do Codex são registrados como **"Codex relatou"** até checagem independente. Testes offline, simulados, ligação a API real, aprovação editorial, publicação e deploy são marcos diferentes.
4. Alterações em branches e PRs não equivalem a merge na `main`. Código instalado localmente não equivale a versão publicada no GitHub. Link para repositório privado não torna seus conteúdos públicos.
5. O diretor autoriza separadamente mudanças sensíveis: novas inferências reais, custos, permissões, publicação, implantação contínua, domínio, marca, redes e alterações de DNAs ou visual. Um backup **não dá autorização**.
6. Não copiar tokens, cookies, OAuth, e-mails, logs sensíveis, senhas, dados pessoais ou textos inéditos privados para este repositório **público**.
7. Quando o GitHub mudar durante a atualização, usar branch/commit ou mecanismo com verificação de versão. Preservar histórico; nunca reescrever backups antigos, fazer `force push` ou descartar trabalho local do Codex.

## Procedimento de fim de sessão e troca de Fundador

- Registrar últimos fatos e pendências, atualizar o **ponto de parada** e separar "validado" de "ainda não testado".
- Conferir commit/URL do que foi realmente gravado e informar ao diretor. Se não houver gravação, declarar explicitamente.
- Ao abrir sucessor, criar documento `BACKUP-CONTINUIDADE-FUNDADOR-N-PARA-FUNDADOR-N+1-AAAA-MM-DD.md` vinculado aos registros anteriores, sem recontar suposições como fatos; indicar os repositórios, versão mais recente, decisões, estado operacional, pendências e **primeira tarefa a retomar**.
- Manter índice `README.md` atualizado. Cada novo Fundador herda a responsabilidade de registro contínuo.

**Critério de sucesso:** alguém sem acesso à conversa consegue identificar o que realmente foi feito, o que ficou pendente, qual documento prevalece e como continuar sem expor segredos ou ligar processos indevidamente.
