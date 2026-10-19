"""Testes de integração: falam com a API de verdade, que usa Postgres e Redis."""
import os

import requests

BASE_URL = os.environ.get("BASE_URL", "http://localhost:8000")


def get(caminho):
    return requests.get(BASE_URL + caminho, timeout=5)


def test_health():
    r = get("/health")
    assert r.status_code == 200
    assert r.text == "ok"


def test_index_conta_visitas_no_redis():
    primeira = get("/").json()["visitas"]
    segunda = get("/").json()["visitas"]
    assert segunda == primeira + 1


def test_converter():
    r = get("/converter?celsius=25")
    assert r.status_code == 200
    dados = r.json()
    assert dados["fahrenheit"] == 77.0
    assert dados["kelvin"] == 298.15


def test_segunda_conversao_vem_do_cache():
    get("/converter?celsius=100")
    r = get("/converter?celsius=100")
    assert r.json()["origem"] == "cache"


def test_converter_valor_invalido():
    r = get("/converter?celsius=abc")
    assert r.status_code == 400
    assert "erro" in r.json()


def test_historico_salvo_no_postgres():
    get("/converter?celsius=-40")
    historico = get("/historico").json()
    assert historico[0]["celsius"] == -40.0
    assert historico[0]["fahrenheit"] == -40.0
