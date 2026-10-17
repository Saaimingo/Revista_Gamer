# Arquivo de protótipos do Bloco 03

**Data:** 2026-10-17 | **Versão:** 0.1 | **Estado:** PROPOSTA — NÃO APROVADO.  
**Objetivo:** guardar **dois mocks de oito faces cada** para debate com diretor e Bloco Fundador, não para publicar uma edição.

- [Estudo comparativo, decisões e riscos](../estudos/ESTUDO-COMPARATIVO-DOIS-MOCKS-TEMATICOS-2026-10-17.md)
- [Mock A — Terror / Resident Evil: 8 faces](mock-a-terror/README.md)
- [Mock B — GTA VI / tema colorido: 8 faces](mock-b-gta/README.md)

## Localização esperada dos 16 PNGs

Dentro de cada pasta, subdiretório `png/`, nomenclatura idêntica: `pagina-01.png` (capa), `pagina-02.png` a `pagina-07.png` (miolo), `pagina-08.png` (contracapa). Arquivos extras de apoio: `visao-geral.jpg` de cada mock e `manifesto.json` com dimensões, fontes locais e SHA-256.

**Estado de transferência:** os **documentos de texto foram registrados no GitHub**, mas **os 16 PNGs ainda não foram transferidos para ele nesta sessão**, por limitação do conector para arquivos binários originados localmente. A direção recebeu um pacote ZIP com as 16 imagens em suas pastas finais. Até que sejam enviados e validados por acesso direto, os links para PNGs não devem ser tratados como disponíveis no repositório.

## Uso restrito / riscos

Os nomes de revista, fotos, caricaturas, nomes comerciais, QR codes, perfis, avaliações, preços, cronologias e especificações técnicas apresentados são **ilustrações sintéticas e fictícias**, não matéria apurada, testes, patrocínios ou campanhas. A presença de franquias e marcas reconhecíveis **não significa licença**. Solicitar avaliação do Bloco 05 antes de divulgação externa. Arquivar não implica aprovação. A estrutura final, a edição real e os efeitos interativos ainda precisam ser debatidos e testados.

## Se for transferir os arquivos manualmente

1. Extrair o ZIP preservando a árvore de pastas.
2. No clone local do repositório, copiar a pasta `docs/visual/prototipos/` do pacote para a pasta homônima no projeto, mantendo os 16 PNGs, as duas visões gerais e o manifesto.
3. Conferir o total de 8 PNGs por mock e verificar suas dimensões e hashes do manifesto; então realizar commit apropriado na área do Bloco 03.
4. Reavaliar o tratamento de direitos por se tratar de repositório **público**. Marcar os arquivos como referenciais/não publicados.
