# Lapida: Mapeamento de conteúdo para MPEs (Stone × Inteli Academy)

> **Estado em 24/11/2026:** base, ranking, rubrica (visual na base inteira; fala em 423 dos 447
> posts de alto desempenho), indicador de lead, agente, avaliador de criativo, MCP e playbook
> prontos. As cinco hipóteses do motor não foram gastas. A validação da amostra de 50 posts foi
> feita por um segundo avaliador de IA, não por uma pessoa.

## Problema e recorte
Quais características aparecem nos Shorts de maior engajamento voltados a micro e pequenos
empreendedores, e como transformar isso em criativos? O Instagram é a fonte principal do TAPI. Como
a rota de extração não estava disponível neste projeto, a base é só de **YouTube Shorts**, pela API
oficial. Não há modelo preditivo nem publicação automática.

## Base de dados
- **Origem:** YouTube Data API v3 (metadados e métricas públicas), coletada em 23/11/2026.
- **Seleção:** 12 consultas geraram 551 candidatos; a lista final foi escolhida à mão, em
  `src/mpe/canais.py`, por público declaradamente MPE. Marcas foram incluídas por nome.
- **Volume:** 4.545 Shorts, 4.462 com métricas públicas. Até 120 por canal, os mais recentes em 24
  meses, com 14 dias ou mais.
- **Limitações:** seleção por busca favorece canais já encontráveis; o teto de 120 encurta a janela
  dos canais mais ativos; inscritos são os de hoje, não os da data do post; a métrica ignora quem
  viu sem seguir; poucos canais de beleza; parte do conteúdo de marca fala com pessoa física.
- **Licença:** metadados sujeitos aos Termos da API do YouTube. A base não é redistribuída.

## Metodologia
1. **Ranking:** (curtidas + comentários) ÷ seguidores. Alto desempenho = 10% superiores (447 posts).
   Viés medido: 3 perfis pequenos ocupam 52% dessas vagas.
2. **Rubrica:** a do TAPI 6.2 mais 8 marcadores sim/não, em JSON (`src/mpe/rubrica.py`), com
   três avaliadores:
   - *Quadros* (DeepSeek V4.1 Flash): recebe os 3 quadros públicos do Short, a capa, o título e a
     descrição, sem áudio. Responde 7 campos visuais em todos os posts: formato, tema, rosto, texto
     na tela, prova social, ambiente real e citação de regra ou lei. Critério: kappa de 0,60 a
     0,85 contra o Gemini em 120 posts (`scripts/sonda_quadros.py`).
   - *Fala por vídeo* (Gemini 3.5 Flash-Lite): assiste ao vídeo com som. Leu 351 posts, 191 deles
     do topo; a cota gratuita e a instabilidade do serviço impediram mais.
   - *Fala por transcrição* (faster-whisper small local + DeepSeek): lê a transcrição com tempo,
     os quadros e a capa. Leu 485 posts: o topo e os posts com comentário de intenção
     (`scripts/transcrever_topo.py`, `scripts/extrair_transcricao.py`).
   Os dois caminhos de fala foram comparados em 169 posts lidos por ambos
   (`scripts/concordancia_fala.py`, `data/concordancia_fala.csv`): kappa de 0,61 a 0,82 nos
   marcadores sim/não de fala, 0,49 em tipo de gancho, 0,39 em tom e 0,32 em "criador é
   empreendedor real". Dois cuidados saem daí. Os campos de kappa baixo ficam fora das
   comparações. E cada comparação usa um só avaliador de fala dos dois lados, porque a
   transcrição marca oferta explícita e chamada para ação mais vezes que o vídeo nos mesmos posts
   (44% e 28%; 62% e 47%).
3. **Motor de hipóteses** (`src/mpe/motor.py`): compara top × resto **dentro do mesmo perfil**. O
   agente vê metade dos perfis, propõe 5 hipóteses, elas são travadas e testadas uma única vez na
   outra metade (permutação, Bonferroni, corte 0,01). Cada atributo é testado só nos posts em que
   o avaliador do seu campo respondeu. Saída: sustentada, não sustentada ou evidência
   insuficiente. Só um humano aprova o que vai ao playbook. O teste do embaralhamento mede quantos
   achados o motor inventa. São associações, não causas.
4. **Validação por amostra:** 50 posts de 38 perfis, sorteados por `src/mpe/validacao.py`, anotados
   às cegas em 11 campos e comparados com a rubrica automática (`data/validacao_ia.csv`,
   `data/concordancia_ia.csv`). **O segundo avaliador foi um modelo de IA (Claude), com 6 quadros e
   a transcrição Whisper de cada vídeo, não uma pessoa.** Mede acordo entre avaliadores
   independentes, não substitui a amostra manual do TAPI; `scripts/validar.py gerar` cria a página
   para uma pessoa refazer a mesma amostra. Kappa: rosto 0,88; promove produto próprio 0,82;
   formato 0,72; tema 0,72; ambiente real 0,68; chamada para ação 0,64; número no gancho 0,61; tom
   0,60; passo concreto 0,59; texto na tela 0,49 (quase todo vídeo tem); tipo de gancho 0,40.
5. **Indicador de lead** (`src/mpe/comentarios.py`): até 100 comentários por Short, pela API
   oficial (4.632 comentários de 1.308 Shorts; os do próprio canal ficam de fora), classificados
   pelo DeepSeek em intenção, dúvida, relato, reação, crítica e outro. *Intenção* é o comentário
   que pede preço, link, contato ou material; intenção e dúvida juntas são o *interesse*. A
   classificação não foi validada por amostra manual.
6. **Tipo de conteúdo** (`consulta.tipo_conteudo`): informativo, personalidade ou os dois, no
   recorte de Lee, Hosanagar e Nair (2018), com os campos lidos na base inteira.
7. **Checagem do topo** (`consulta.cenarios`, `duvidas.robustez`): 41% do topo não trata de tema de
   negócio (boa parte é vídeo do lojista para o cliente). Cada comparação é refeita sem esses posts e sem
   os canais em que eles são maioria, com o topo recalculado. Firme é o que passa nos três; o resto
   vira hipótese. A plataforma e o agente usam só os firmes.
8. **Avaliador de criativo** (`src/mpe/avaliador.py`): o LLM lê um rascunho e preenche a rubrica; a
   aderência é conta, contra o topo de engajamento ou contra os posts com interesse. Só vira sinal
   a diferença que se mantém com peso igual por perfil. A leitura do rascunho pelo LLM pode variar
   entre execuções.

## Arquitetura
LangGraph: interpretar → consultar → lembrar → redigir → verificar → revisar, com registro em `execucoes`. O LLM redige;
números e posts vêm da base, e criativo que cita post fora das referências é descartado. As
frequências saem dos posts do assunto pedido (título, descrição e transcrição); se o assunto tem
menos de 5 posts no topo, o agente usa o topo inteiro e diz isso na resposta.

### Revisão, memória e radar
- **Memória** (`src/mpe/memoria.py`): o que os 40 roteiros mais recentes do objetivo mais deixaram de
  fora vira aviso no próximo pedido, e some quando o erro para.
- **Revisão** (`agente.revisar`): se a segunda leitura não acha um padrão, o roteiro é reescrito uma
  vez e conferido de novo; só troca se ganhou padrão sem perder nenhum. Em 16 pedidos com e sem
  (32 roteiros de cada lado, 25/11/2026): 25 completos sem, 32 com. O primeiro rascunho ficou igual
  nos dois (25 e 25), então o ganho veio da revisão, e não da memória. Quem confere é a mesma IA:
  mede aderência aos padrões, não resultado. Tempo mediano de 65 para 79 s (máximo de 118).
- **Radar** (`src/mpe/radar.py`): três períodos com o mesmo número de posts e topo refeito em cada um.
  Hoje só há indícios (negócio de verdade em alta; tutorial e texto na tela em queda), todos dentro
  da margem de erro. O agente usa para desempatar, nunca como regra.
- **Atualização** (`scripts/atualizar.py`): coleta, quadros, comentários e o que mudou nos padrões,
  com cópia do banco e volta automática se falhar. Não inclui a fala dos vídeos novos.
- **Acompanhamento** (`src/mpe/acompanhamento.py`, aba `/acompanhar`): lê um Short publicado a cada 6 horas
  enquanto a plataforma está no ar (ou por `scripts/acompanhar.py` no cron), conta pedidos de contato e
  diz se surge um indício novo: vídeo entre os 10% melhores do canal que faz algo raro nele. Um vídeo
  não vira regra e nada muda sozinho. Os três vídeos de exemplo são do canal da Stone, não feitos aqui.
- **Gravação** (`src/mpe/gravacao.py`): a checagem técnica do vídeo enviado é automática; a leitura contra o
  roteiro é assistida, fora da plataforma (`scripts/preparar_gravacao.py`).
- `MPE_APRENDE=0` desliga memória, radar e revisão; `MPE_REVISAR=0` só a revisão.

## Instalação e execução
Requer `uv` e `YOUTUBE_API_KEY` e `GEMINI_API_KEY` em `.env` (na falta, lê `../Galaxies/.env`).
Com `FEITA_API_KEYS=chave1,chave2,chave3` no `.env`, o LLM passa a ser o gateway do Feita
(`https://api.feita.ai/gateway/v1`, mesmo modelo, pago com créditos), trocando de conta quando o
crédito acaba.

    uv sync
    uv run python scripts/coletar.py         # base
    uv run python scripts/extrair_quadros.py # avaliador de quadros, base inteira, retomável
    uv run python scripts/carregar_quadros.py
    scripts/rodar.sh                         # avaliador de fala, retomável
    uv run python scripts/extrair_topo.py    # fala por vídeo só no topo (Gemini direto)
    # fala por transcrição: o Whisper roda no ambiente do Galaxies (faster-whisper + yt-dlp)
    #   uv run --extra multimodal python scripts/transcrever_topo.py ids.json data/legendas
    uv run python scripts/extrair_transcricao.py
    uv run python scripts/carregar_transcricao.py
    uv run python scripts/concordancia_fala.py
    uv run python scripts/coletar_comentarios.py      # indicador de lead
    uv run python scripts/classificar_comentarios.py
    uv run python scripts/carregar_comentarios.py
    uv run python scripts/avaliar.py interesse < rascunho.txt   # avaliador de criativo
    uv run python scripts/validar.py gerar   # página das 50 validações
    uv run python scripts/validar.py medir validacao.csv
    uv run python scripts/gerar_playbook.py
    uv run python scripts/demo.py
    uv run mpe-mcp                           # servidor MCP
    uv run pytest

Apresentação: `uv run python apresentacao/servir.py` (http://127.0.0.1:8020). As capas do mural não
estão no repositório: sem elas aparecem blocos de cor.

Versão pública, só leitura: https://lapida-plataforma.vercel.app (`scripts/exportar_vitrine.py`; não cria, não
grava e não leva chave). O deck aceita controle pelo celular (`apresentacao/controle.html`), com um
código secreto por sala que não fica no repositório.

Plataforma: `uv run mpe-app` (http://127.0.0.1:8010). Um fluxo: pede-se um tema e um objetivo
(contato ou engajamento) e saem dois criativos editáveis, os Shorts que os inspiraram tocando ao
lado, os padrões medidos que cada um aplica e o que falta conferir. O playbook está em `/playbook`,
com os mesmos números. Os vídeos são prévias animadas feitas nesta máquina
(`scripts/gerar_previa.py`, `scripts/boneco`), não peças finais, que estão fora do escopo do TAPI. Para usar o DeepSeek pela
Feita: `MPE_FEITA_MODELO=deepseek/deepseek-v4.1-flash-1017`. As referências são escolhidas pelo
LLM entre candidatas achadas por palavra na base; o que o roteiro aplica é conferido por uma
segunda leitura pela rubrica, não pela declaração de quem o escreveu. Um pedido leva de 40 a 80 s.

Funções Python: `mpe.agente.executar(banco, llm, {"mode": ..., "query": ...})` e
`mpe.avaliador.avaliar(df, llm, rascunho, objetivo)`. No servidor MCP: `consultar`,
`avaliar_criativo`, `perfis` e o ciclo de hipóteses.

## Modelos
- `gemini-3.5-flash-lite` para a fala e para redigir: direto (plano gratuito, 500 chamadas/dia
  medidas; repetições com erro também contam) ou pelo gateway do Feita (cerca de 1 crédito por
  Short; o link do YouTube vai como arquivo, não como `video_url`).
- `deepseek/deepseek-v4.1-flash-1017` para os quadros, pelo gateway do Feita (cerca de 0,22 crédito
  por post).

## Resultados
Em 24/11/2026. Tabelas completas, exemplos e os seis criativos em `docs/playbook.md`. São
associações observadas em YouTube Shorts, não causas.

**Topo de engajamento contra o resto (447 e 4.015 posts).** O topo vem de 29 perfis e três deles
somam 234 dos 447 posts, então a segunda coluna dá o mesmo peso a cada perfil.

| Característica | Topo | Topo, peso igual por perfil | Resto |
|---|---|---|---|
| Mostra ambiente real | 56% | 41% | 28% |
| Formato tutorial | 26% | 16% | 11% |
| Formato talking head | 36% | 48% | 61% |
| Tema finanças | 9% | 21% | 31% |
| Cita regra ou lei | 6% | 14% | 20% |
| Fala direto com o dono (fala, 191 posts) | 40% | 50% | 66% |
| Tem chamada para ação (fala, 191 posts) | 42% | 44% | 53% |

**Checagem do topo.** Passam nos três recortes: menos rosto falando, mais negócio de verdade, menos
finanças, erro, passo concreto e fala direta com o dono. Tutorial, chamada para ação e citação de
regra não passam. No contato passam dizer o ganho, pedir uma ação e mostrar mais que o rosto; falar
direto com o dono não passa (64% contra 64% sem os posts fora de negócio).

**Dentro do mesmo perfil** (metade de exploração, 25 perfis): nenhuma diferença visual chega a 10
pontos entre os 8 melhores posts e o resto. O contraste da tabela acima descreve quem está no
topo, não o que faz um vídeo de um mesmo criador subir. As cinco hipóteses não foram registradas.

**Indicador de lead.** 320 comentários de intenção em 129 posts de 34 perfis; 566 de dúvida.
Engajamento e pedido de contato andam juntos: 8,3% dos posts do topo têm pedido (37), contra 2,3%
dos demais (92). Parte é mecânica, porque a métrica conta comentários: só entre posts com
comentário lido, 14,8% contra 9,7%. Mesmo no topo, mais de 9 em cada 10 posts não têm pedido. Nas
características de fala os dois lados foram lidos pelo mesmo avaliador, e o lado de comparação são
posts do topo sem comentário de intenção.

| Característica | Posts com intenção | Demais |
|---|---|---|
| Oferta ou benefício explícito | 78% | 55% |
| Tem chamada para ação | 83% | 67% |
| Fala direto com o dono (hipótese) | 60% | 47% |
| Formato talking head | 48% | 59% |

Essas quatro se mantêm com peso igual por canal (77%, 81%, 59% e 49%), mas a terceira cai na
checagem do topo. Gravar em ambiente real (42%
contra 31%) não: cai para 33%. Nos posts com interesse (intenção ou dúvida, 390), passar de 60 s
(44% contra 32%) e mostrar conta com números (35% contra 24%) se mantêm com peso igual e caem na
checagem; citar regra ou lei (33% contra 17%), tratar de finanças (39% contra 27%) e dar passo
concreto (61% contra 49%) já caem com peso igual. Todos ficam como hipótese. O canal da Stone tem 120 Shorts na base, 23 comentários
lidos, nenhum de intenção e 3 de dúvida.

**Tipo de conteúdo** (peso igual por perfil, intervalo de 95% por reamostragem de perfis):

| Tipo | Posts | Entra no topo | Gera interesse |
|---|---|---|---|
| Informativo | 2.806 | 10% (6 a 16) | 12% (8 a 17) |
| Personalidade | 620 | 14% (7 a 23) | 5% (2 a 8) |
| Os dois juntos | 373 | 11% (3 a 22) | 9% (5 a 14) |

Informativo gera mais interesse que personalidade. Na entrada no topo os intervalos se sobrepõem e
a base não separa os tipos.

## Limitações
- Parte do topo não fala com o lojista. A checagem atenua isso, não elimina: depende do tema lido
  pela IA, e canais mistos (como @gestaodepizzarias) continuam na base.
- Um padrão só é tratado como firme se a diferença é de 8 pontos e sobram 5 com peso igual por
  canal, nos três recortes da checagem. Esses cortes foram escolhidos por nós, não por um teste; muitas características foram
  olhadas sem correção.
- A interface foi inspecionada com duas personas simuladas por IA, não com usuários.
- Só YouTube Shorts; o Instagram, fonte principal do TAPI, não entrou.
- A amostra de 50 posts foi validada por IA, não por uma pessoa.
- A fala do topo vem de dois avaliadores (191 por vídeo, 232 por transcrição); tipo de gancho e
  tom têm concordância baixa e não sustentam achado.
- Comentário de intenção é raro e concentrado: um único post tem 74 dos 320. A classificação dos
  comentários não foi conferida por amostra.
- Comentários foram coletados em 24/11/2026, um dia depois das métricas.
- Nada aqui foi confirmado pelo teste do motor; são frequências descritivas.

## Evolução
Instagram, detector de aprendizado nos comentários, verificador de afirmações sobre MEI e
experimento com o faturamento de clientes da Stone, com consentimento e grupo de controle.
