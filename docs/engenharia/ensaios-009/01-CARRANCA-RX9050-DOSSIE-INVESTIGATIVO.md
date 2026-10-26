# PACOTE 01 — Arlindo Carranca / RX 9050 e fronteiras da GPU de entrada
**Data de curadoria:** 25/10/2026. **Uso:** BATERIA FUTURA, não inferir hoje. **Gênero:** reportagem investigativa de hardware, apresentação do produto → auditoria das variantes → benchmarks de terceiros → limitações/metodologias → veredito contextual, com base nas FONTES, jamais teste de laboratório próprio.

## Material FONTE: não está em ordem de “conclusão”
- **H01 AMD RX 9050 8 GB — ficha oficial, fabricante.** https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9050.html
  AMD declara RDNA 4, 16 CUs, até 2600 MHz boost, 1920 MHz game, 1024 SP, 8 GB GDDR6 18 Gbps, BUS 128-bit, bandwidth máximo 288 GB/s, Infinity Cache 32 MB, 92 W típico, PSU sugerida 450 W, 1x8-pin, PCIe 5.0 x16. A vitrine traz exemplos de FPS a “1080p Medium”; tratar como MERCHANDISING COM CONDIÇÕES, não resultado medido pela Revista Gamer.
- **H02 AMD RX 9050 4 GB — ficha oficial, fabricante.** https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9050-4gb.html
  Mesmos 16 CUs/boost e 92 W típicos, mas 4 GB, BUS 64-bit, largura de banda até 144 GB/s e Infinity Cache 16 MB. **Não é apenas a mesma placa com metade da VRAM:** barramento/bandwidth/cache também diferem. Não confundir ficha 4 GB com 8 GB ou atribuir a ambas as conclusões dos benchmarks 8 GB.
- **H03 PowerColor — release da AIB 28/07/2026.** https://www.powercolor.com/news-detail90.htm
  Reaper RX 9050 8 GB, compacta 2-slot/duas ventoinhas, 200×100×40 mm, 1x8-pin, 8GB/128-bit/18Gbps, disponibilidade APJ/LATAM em parceiros selecionados a partir de 28/07. Release de marca, não comparação independente.
- **H04 Sapphire — anúncio de parceira 28/07/2026.** https://www.sapphirenation.net/rx-9050-release
  PULSE RX 9050 8 GB, game até 2260/boost 2760 MHz conforme a própria Sapphire; isto é um modelo customizado, NÃO incoerência automática com clocks de referência AMD. Comparar variantes por modelo exato.
- **H05 ASRock — anúncio de parceira 28/07/2026.** https://www.asrock.com/news/index.us.asp?iD=5827
  Série Challenger RX 9050, foco RDNA 4/FSR, versão 8 GB e até 2600 MHz boost declarados; confirmar SKU/ficha.
- **H06 PCWorld — notícia/reação de mercado 28/07/2026.** https://www.pcworld.com/article/3200962/amd-reveals-the-radeon-rx-9050-and-4gb-graphics-cards-are-back.html
  Reporta 8 GB para venda avulsa e 4 GB em desktops pré-montados (OEM), cita US$ 279 para 8 GB no contexto de anúncio e limitação de mercado inicial. **Preço/região/canal/data importam**: não converter em preço atual do Brasil sem evidência.
- **H07 TechSpot / Hardware Unboxed — BENCHMARK independente extenso, 8 GB, 2026.** https://www.techspot.com/review/3162-amd-radeon-rx-9050-8gb/
  Bateria comparativa de 10 jogos: média reportada RX 9050 8 GB = 49 FPS (1080p) vs RTX 5050 59 FPS e RX 9060 XT 8 GB 86 FPS; 1440p RX9050 33 FPS vs RX9060XT 8GB 53 FPS, agregados das condições/testes selecionados pela fonte. Exemplos ilustrativos isolados: Cyberpunk 2077 Phantom Liberty 1080p High RX9050 67 FPS vs RX9060XT8 111 FPS; Marvel’s Spider-Man Remastered 1080p Very High RX9050 104 vs RX9060XT8 182; STALKER 2 1440p Epic RX9050 8 FPS, 9060XT8 9 e 9060XT16 42 — **evidência de cenário/VRAM muito específico, não regra universal**. Ler procedimento, drivers, sistema, RT/FSR e gráficos originais antes de reproduzir números; não misturar presets de jogos nem interpolar novos.
- **H08 Tom’s Hardware — cobertura SECUNDÁRIA de teste de outlet japonês GDM 31/07/2026.** https://www.tomshardware.com/pc-components/gpus/amds-new-radeon-rx-9050-is-roughly-30-percent-slower-than-the-rtx-5050-in-games-early-testing-shows-the-cheapest-8gb-rdna-4-gpu-comfortably-handles-1080p-gaming-but-doesnt-impress
  Narra medições feitas **pela GDM, não pelo Tom’s**: Ryzen 7 9800X3D, ASRock Challenger RX9050 vs Gigabyte Windforce RTX5050; comparações 1080/1440/4K, resultados variados e alguns anomalamente invertidos em DOOM. A manchete de “~30% atrás” se refere à amostra GDM/condições, não à média TechSpot. O texto avisa que é preliminar e de UMA fonte primária. Procurar e citar GDM original ao usar dados e verificar eventual diferença de frame generation/upscaling.
- **H09 AMD RX 9060 XT — PR oficial 20/05/2025.** https://ir.amd.com/news-events/press-releases/detail/1253/amd-introduces-new-radeon-graphics-cards-and-ryzen-threadripper-processors-at-computex-2025
  RX 9060 XT com 32 CUs, 8/16 GB, 128-bit, 2530 MHz game/3130 MHz boost, 32 MB Infinity Cache, 150/160 W a partir do SKU; preços sugeridos DE ANÚNCIO nos EUA US$299/349, não preços nacionais atuais nem mesmo produto da 9050.
- **H10 AMD RX 9060 XT 16GB — ficha de GPU.** https://www.amd.com/en/products/graphics/desktops/radeon/9000-series/amd-radeon-rx-9060xt.html
  Até 320 GB/s e 160 W típicos nesta ficha, 32 CUs, 2048 SP. Separar VRAM e quantidade de unidades computacionais de comparar 9050 vs 9060XT.
- **H11 Tom’s Hardware RX9060XT 16GB review — independente.** https://www.tomshardware.com/pc-components/gpus/amd-radeon-rx-9060-xt-16gb-review
  Avalia 16 GB favoravelmente frente a placas de 8 GB, mas cita limitação de recursos frente ao ecossistema concorrente e preços de rua diferentes do preço sugerido. Não atribuir a este review benchmarks de RX9050.
- **H12 discussão Reddit/usuários — apenas hipótese e casos individuais.** Fontes de comunidade sobre compradores RX9050, problemas de drivers, 4GB/OEM e preço Brasil só entrarão após coleta explícita, timestamp e sistema/driver/SKU. Nenhum “consenso do Reddit” está comprovado neste pacote.

## Perguntas que o editor passa ao Carranca (NÃO fornecer respostas prontas)
1. O que uma placa RDNA4 de 92 W acrescenta ao 1080p, e para quem os limites são aceitáveis? A comparação correta deveria envolver concorrentes de preços efetivamente comprovados.
2. O modelo 4GB perde apenas capacidade de texturas ou também largura de banda/cache? Há algum benchmark INDEPENDENTE da versão 4GB em H01–H11? **Se não houver, não estimar FPS**.
3. 9050 8GB versus 9060 XT 8GB/16GB: onde a discrepância vem de GPU maior, VRAM, settings, preço ou metodologia? Por que um benchmark de 1440p Epic não prova que 8GB falhará em todo jogo?
4. Quais mudanças de clocks/saídas/cooler dependem da fabricante e SKU? Onde marketing falha em descrever configuração?
5. Qual o papel de FSR e de frame generation, latência e 1% low? Se esses dados não estiverem em H07–H08, apontar a lacuna.
6. Qual o valor no Brasil **somente se houver coleta de preço datada na rodada**? Não inventar disponibilidade/preço atual.
7. Veredito dividido por 1080p nativo/FSR, longevidade/VRAM, sistemas compactos e comparação justa; elogie onde houver mérito, critique onde a amostra suportar.

## Entregáveis pretendidos no próximo ensaio (não produzir antes de autorizá-lo)
Matéria integral ~1.400–2.000 palavras com apresentação, ficha, explicação da tecnologia, comparações por cenário, fontes nomeadas, divergências, limites e veredito. Texto narrativo de Carranca (ironia se surgir do raciocínio, não sarcasmo automático). Quadros podem ser descritos em texto, **não fabricar resultados gráficos nem imagem licenciada**. Emitir 5–8 claims auditáveis com source_id, e uma tabela metodológica se cabível. Melhor RETER conclusão que inventar número. Marcar pelo menos um item para pesquisa complementar local Radar e devolver missing_evidence se índice vazio.

## Armadilhas PREPARADAS PARA AVALIAÇÃO (não antecipar nota ao redator)
Confundir 4GB 64-bit/16MB com 8GB 128-bit/32MB; tratar RX9050 vs RX9060XT como diferença só de VRAM; somar frames gerados a FPS renderizado; tomar Tom’s Hardware como laboratório dos números GDM; usar preço USD/2025 como preço BRL/2026; desconsiderar DOOM como outlier; apresentar manchete ~30% como consenso; alegar que a revista testou.

**Estado dos materiais:** somente referência, resumo/paráfrase e URLs originais, não PDFs/artefatos licenciados copiados. Validar cada URL em novo preflight de direitos/robots antes de coleta automatizada.