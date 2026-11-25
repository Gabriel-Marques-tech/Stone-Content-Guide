import httpx
import pytest
from pydantic import BaseModel

from mpe.feita import Feita
from mpe.gemini import CotaEsgotada


class Saida(BaseModel):
    tema: str


def cliente(respostas, vistos):
    def responder(pedido):
        vistos.append(pedido)
        return respostas[pedido.headers["authorization"].removeprefix("Bearer ")]

    return httpx.Client(transport=httpx.MockTransport(responder))


BOA = httpx.Response(200, json={"choices": [{"message": {"content": '{"tema": "caixa"}'}}]})
SEM = httpx.Response(402, json={"error": "insufficient_credits"})


def test_passa_para_a_proxima_conta_quando_o_credito_acaba():
    vistos = []
    f = Feita(por_minuto=6000, cliente=cliente({"a": SEM, "b": BOA}, vistos), lista=["a", "b"])
    assert f.json("x", Saida, "https://www.youtube.com/watch?v=abc").tema == "caixa"
    assert len(vistos) == 2
    assert f.json("x", Saida).tema == "caixa"
    assert len(vistos) == 3  # não volta à conta esgotada


def test_envia_video_modelo_do_gateway_e_schema():
    import json

    vistos = []
    f = Feita(
        modelo="gemini-3.5-flash-lite",
        por_minuto=6000,
        cliente=cliente({"a": BOA}, vistos),
        lista=["a"],
    )
    f.json("x", Saida, "https://www.youtube.com/watch?v=abc")
    corpo = json.loads(vistos[0].content)
    assert f.modelo == "gemini-3.5-flash-lite"
    assert corpo["model"] == "google/gemini-3.5-flash-lite"
    assert corpo["messages"][0]["content"][0]["file"]["file_data"].endswith("abc")
    assert corpo["response_format"]["json_schema"]["schema"]["properties"]["tema"]


def test_todas_as_contas_sem_credito_vira_cota_esgotada():
    f = Feita(por_minuto=6000, cliente=cliente({"a": SEM, "b": SEM}, []), lista=["a", "b"])
    with pytest.raises(CotaEsgotada):
        f.json("x", Saida)


def test_insiste_quando_o_modelo_esta_indisponivel():
    fila = [httpx.Response(503, json={"error": {"code": "model_unavailable"}})] * 3 + [BOA]
    http = httpx.Client(transport=httpx.MockTransport(lambda _: fila.pop(0)))
    f = Feita(por_minuto=6000, cliente=http, lista=["a"], pausa=0)
    assert f.json("x", Saida).tema == "caixa"
    assert not fila
