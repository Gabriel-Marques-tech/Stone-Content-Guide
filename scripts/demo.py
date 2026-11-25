"""Demonstração: pergunta → análise → referências → criativo → justificativa → teste do motor."""

from mpe import hipoteses, motor
from mpe.agente import executar
from mpe.banco import abrir
from mpe.consulta import base_completa
from mpe.feita import llm

banco, llm = abrir(), llm()
df = base_completa(banco)
for modo, pedido in [
    ("analisar", "quais formatos aparecem mais no topo para negócios de alimentação?"),
    ("gerar_criativo", "como o dono de restaurante calcula o preço do prato"),
]:
    s = executar(banco, llm, {"mode": modo, "query": pedido, "segment": "alimentacao"}, df)
    print(f"\n### {modo}: {pedido}\nsinal: {s.confidence_flag} | execução: {s.run_id}\n{s.explanation}")
    for a in s.findings[:6]:
        print(f"  {a.atributo}: {a.frequencia_top:.0%} de {a.n_top} ({a.status})")
    for r in s.reference_posts:
        print(f"  ref {r.link} | {r.canal} | #{r.posicao} | {r.engajamento:.2%}")
    for c in s.creatives:
        print(f"  GANCHO: {c.gancho}\n  ROTEIRO: {c.roteiro}\n  CTA: {c.chamada_para_acao}\n  de: {c.referencias}")
print("\n### hipóteses")
for h in hipoteses.ler(banco):
    print(h.id, h.afirmacao, "→", h.veredito)
amostra = df[df["categorizado"] & df["par_motor"].notna()]
print("falsos positivos com rótulos embaralhados:", motor.falsos_positivos(amostra), "| alfa", motor.ALFA)
