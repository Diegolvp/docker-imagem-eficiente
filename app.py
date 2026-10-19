"""API simples de conversão de temperatura (Flask + PostgreSQL + Redis).

- PostgreSQL guarda o histórico das conversões.
- Redis faz cache das conversões e conta as visitas.
"""
import json
import os
import socket

import psycopg
import redis
from flask import Flask, jsonify, request

app = Flask(__name__)

# Endereços dos serviços vêm de variáveis de ambiente (definidas no compose).
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://app:app@localhost:5432/app")
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CACHE_TTL = int(os.environ.get("CACHE_TTL", "60"))

# Timeouts curtos: se o Redis não responder, a requisição falha rápido em vez de travar.
cache = redis.Redis.from_url(
    REDIS_URL, decode_responses=True, socket_connect_timeout=2, socket_timeout=2
)


def db():
    return psycopg.connect(DATABASE_URL, connect_timeout=3)


@app.get("/")
def index():
    return jsonify(
        mensagem="Olá do container Docker! Use /converter?celsius=25 e /historico",
        container=socket.gethostname(),
        visitas=cache.incr("visitas"),
    )


@app.get("/converter")
def converter():
    try:
        celsius = float(request.args.get("celsius", ""))
    except ValueError:
        return jsonify(erro="Informe um número, ex.: /converter?celsius=25"), 400

    chave = f"conversao:{celsius}"
    em_cache = cache.get(chave)
    if em_cache:
        resultado = json.loads(em_cache)
        resultado["origem"] = "cache"
    else:
        resultado = {
            "celsius": celsius,
            "fahrenheit": round(celsius * 9 / 5 + 32, 2),
            "kelvin": round(celsius + 273.15, 2),
        }
        cache.set(chave, json.dumps(resultado), ex=CACHE_TTL)
        resultado["origem"] = "calculado"

    with db() as conn:
        conn.execute(
            "INSERT INTO conversoes (celsius, fahrenheit, kelvin) VALUES (%s, %s, %s)",
            (resultado["celsius"], resultado["fahrenheit"], resultado["kelvin"]),
        )
    return jsonify(resultado)


@app.get("/historico")
def historico():
    with db() as conn:
        linhas = conn.execute(
            "SELECT celsius, fahrenheit, kelvin, criado_em FROM conversoes "
            "ORDER BY id DESC LIMIT 10"
        ).fetchall()
    return jsonify(
        [
            {"celsius": c, "fahrenheit": f, "kelvin": k, "criado_em": t.isoformat()}
            for c, f, k, t in linhas
        ]
    )


@app.get("/health")
def health():
    # Só responde "ok" se o banco e o cache estiverem acessíveis.
    try:
        cache.ping()
        with db() as conn:
            conn.execute("SELECT 1")
    except Exception as erro:
        return jsonify(status="erro", detalhe=str(erro)), 503
    return "ok", 200


if __name__ == "__main__":
    # Apenas para rodar localmente sem Docker; no container quem serve é o Gunicorn.
    app.run(host="0.0.0.0", port=8000)
