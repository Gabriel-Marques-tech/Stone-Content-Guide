"""Servidor MCP: o fluxo do agente e o ciclo do motor de hipóteses como ferramentas."""

from functools import cached_property

from mcp.server.mcpserver import MCPServer

from mpe import hipoteses, motor
from mpe.agente import executar
from mpe.avaliador import Avaliacao, Objetivo, avaliar
from mpe.banco import abrir
from mpe.consulta import base_completa, perfis_em_destaque
from mpe.contrato import Entrada, Saida
from mpe.feita import llm

INSTRUCOES = """Conteúdo para micro e pequenos empreendedores (YouTube Shorts).
Perguntas e criativos: use `consultar` (modos analisar, recomendar, gerar_criativo).
Rascunho pronto: use `avaliar_criativo` para medir a aderência e listar ajustes.
Pesquisa: explorar → propor_hipoteses → confirmar_hipoteses → (o humano decide) aprovar_hipotese.
As regras do teste são fixas: vagas limitadas, metade dos perfis reservada para confirmar e uma
confirmação por hipótese. Nunca aprove uma hipótese sem o pedido explícito do usuário.
Os achados são associações, não causas."""


class Contexto:
    @cached_property
    def banco(self):
        return abrir()

    @cached_property
    def llm(self):
        return llm()

    @property
    def df(self):
        return base_completa(self.banco)


def criar(ctx: Contexto | None = None) -> MCPServer:
    ctx = ctx or Contexto()
    mcp = MCPServer("stone-mpe", instructions=INSTRUCOES)

    @mcp.tool()
    def consultar(entrada: Entrada) -> Saida:
        """Analisa, recomenda ou gera criativos, sempre com os posts de referência."""
        return executar(ctx.banco, ctx.llm, entrada, ctx.df)

    @mcp.tool()
    def avaliar_criativo(rascunho: str, objetivo: Objetivo = "engajamento") -> Avaliacao:
        """Compara um rascunho de roteiro com o que aparece no topo (engajamento) ou nos posts
        que geram comentário de intenção e dúvida (interesse), e diz o que ajustar."""
        return avaliar(ctx.df, ctx.llm, rascunho, objetivo)

    @mcp.tool()
    def perfis() -> list[dict]:
        """Criadores mais presentes no top 10%, com tema e formato predominantes."""
        return perfis_em_destaque(ctx.df).to_dict("records")

    @mcp.tool()
    def explorar() -> list[motor.Teste]:
        """Diferenças top × resto na metade de exploração (p sem correção)."""
        return hipoteses.explorar(ctx.df)

    @mcp.tool()
    def propor_hipoteses() -> list[motor.Hipotese]:
        """O agente propõe e trava as hipóteses a partir da exploração. Só uma vez."""
        return hipoteses.propor(ctx.banco, ctx.df, ctx.llm)

    @mcp.tool()
    def confirmar_hipoteses() -> list[motor.Hipotese]:
        """Testa na metade reservada dos perfis. Cada hipótese é testada uma vez só."""
        return hipoteses.confirmar(ctx.banco, ctx.df)

    @mcp.tool()
    def listar_hipoteses() -> list[motor.Hipotese]:
        """Registro completo, incluindo as que caíram."""
        return hipoteses.ler(ctx.banco)

    @mcp.tool()
    def aprovar_hipotese(id: str) -> motor.Hipotese:
        """Ato humano: libera uma hipótese sustentada para o playbook."""
        return hipoteses.aprovar(ctx.banco, id)

    @mcp.tool()
    def teste_do_embaralhamento(rodadas: int = 20) -> dict:
        """Com rótulos sorteados não há nada a achar: mede a taxa de falso positivo do motor."""
        df = ctx.df
        amostra = df[df["categorizado"] & df["par_motor"].notna()]
        return {"falsos_positivos": motor.falsos_positivos(amostra, rodadas), "alfa": motor.ALFA}

    return mcp


def main():
    criar().run()


if __name__ == "__main__":
    main()
