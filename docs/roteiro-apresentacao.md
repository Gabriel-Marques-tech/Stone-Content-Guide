# Roteiro da apresentação (25/11/2026, cerca de 10 minutos)

Tudo roda do terminal, na raiz do projeto. O LLM usado na demo é o DeepSeek pelo gateway da Feita:

    export MPE_FEITA_MODELO=deepseek/deepseek-v4.1-flash-1017

## 1. Problema e recorte (1 min)
- Pergunta do TAPI: o que aparece no conteúdo de maior engajamento para MPEs e como virar criativo
  para a Stone.
- Recorte: só YouTube Shorts, pela API oficial. Instagram ficou de fora (dizer logo no início).
- Base: 4.545 Shorts de 65 canais; 4.462 com métricas; topo = 447 posts (10% superiores).

## 2. O viés do ranking (1 min)
- Abrir o Playbook na plataforma (`/playbook`). 3 perfis pequenos ocupam 52% do topo: por isso cada
  canal pesa igual.
- 41% do topo não fala de negócio (corte de cabelo, pizza, festa). Refizemos tudo sem esses posts e
  sem esses canais. Só é "firme" o que passa nos três recortes.

## 3. O que aparece no topo (2 min)
- Playbook, botão "Ter curtida". Passam na checagem: mostrar mais que o rosto (52% contra 39%) e
  gravar num negócio de verdade (41% contra 28%). Mais da metade dos Shorts da Stone (66 de 120) é
  só rosto falando; depoimento é a marca dela.
- Tutorial parecia padrão (16% contra 11%) e caiu (12% contra 10%): vinha de quem ensina o cliente
  final. Mostrar isso: é o que a checagem compra.
- Dizer a ressalva: dentro do mesmo perfil nenhuma diferença visual chega a 10 pontos.

## 4. O que separa quem recebe pedido de contato (3 min, é o ponto central)
- "Indicador de lead": 4.632 comentários lidos, 320 pedindo contato, em 129 posts.
- Engajamento ajuda: 8,3% do topo tem pedido, contra 2,3% do resto. Mas não basta: mais de 9 em
  cada 10 posts do topo não têm nenhum. (Não dizer "71% dos pedidos estão fora do topo": como o
  topo é 10% da base, o esperado sem relação seria 90%.)
- Playbook, botão "Receber contato". Passam nos três recortes: dizer o que a pessoa ganha (77%
  contra 55%), pedir uma ação (81% contra 67%) e mostrar mais que o rosto (52% contra 41%).
- Falar direto com o dono não passa: 59% contra 47% vira 64% contra 64%. É hipótese.
- Maquininha é o tema com mais pedido (5,9%, 18 posts de 7 canais): hipótese boa para a Stone.
- Frase central: curtida e contato andam juntos, mas não são feitos da mesma coisa. Por isso a
  ferramenta pergunta o objetivo antes.
- Informativo gera mais interesse que personalidade (12% contra 5%).
- Canal da Stone: 120 Shorts, nenhum pedido, com só 23 comentários lidos.

## 5. Demo ao vivo (2 min)
Plataforma (`uv run mpe-app`, http://127.0.0.1:8010): pedir um tema ao vivo. Leva de 40 a 80 s;
enquanto espera, abrir um dos "Pedidos já feitos" e mostrar o texto, o vídeo que inspirou tocando
ao lado, o "Por que assim" e o "Antes de usar". Se a Feita cair, os pedidos já feitos bastam.

Nos seis prontos o roteiro toca como vídeo: "Ouvir" liga o som e o play de cada quadro vai direto à
cena. É uma prévia animada com voz sintética, feita nesta máquina (`scripts/gerar_previa.py`), e não
um vídeo da Feita: dizer isso. O botão "Gerar vídeo", que aparece nos pedidos novos, é o da Feita (Veo,
8 s, 40 créditos) e só gasta no segundo toque.

Com a plataforma fechada (o banco aceita um processo por vez), o agente no terminal:

    uv run python scripts/demo.py

Avaliador de criativo, com o rascunho no estilo "especialista em estúdio" (`rascunho.txt`):

    uv run python scripts/avaliar.py interesse < rascunho.txt
    uv run python scripts/avaliar.py engajamento < rascunho.txt

Mostrar a aderência, os sinais com o Short real de exemplo e a lista de ajustes.

## 6. Entrega e limites (1 min)
- Playbook na plataforma e em documento, com 6 criativos, cada um ligado aos Shorts de origem.
- Função Python e servidor MCP (`uv run mpe-mcp`): `consultar`, `avaliar_criativo`, `perfis`.
- Limites, sem esperar a pergunta: só YouTube; amostra de 50 validada por IA, não por pessoa;
  tipo de gancho e tom com concordância baixa; comentário de intenção é raro (um post tem 74 dos
  320); hipóteses do motor não foram gastas; tudo é associação.

## Pedido final (30 s)
- "Nos deem 20 vídeos: 10 feitos assim e 10 como hoje, em ordem sorteada, com link rastreado em cada
  um. Em seis semanas a Stone sabe se isso traz mais cliques." Com 20 vídeos só um efeito grande
  aparece; por comentário seriam precisos uns 800 de cada lado, e é por isso que precisamos do link.

## Perguntas prováveis
- **Por que não Instagram?** A rota de extração não estava disponível; o código de coleta é
  separado da análise, então a base troca sem mexer no resto.
- **O topo não está cheio de vídeo que não é para lojista?** Está, 41%. Medimos, refizemos as contas
  sem eles e rebaixamos o que caiu. Canais mistos continuam na base.
- **Vocês produziram os vídeos?** Não são peças finais, que estão fora do escopo. São prévias
  animadas para enxergar o roteiro.
- **Isso prova o que funciona?** Não. São frequências descritivas; o teste dentro do mesmo perfil
  está pronto e não achou efeito visual forte.
- **Como validar o lead de verdade?** Com os Insights do Instagram da Stone: cliques no link,
  visitas ao perfil e mensagens.
