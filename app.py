"""API simples de conversão de temperatura (Flask)."""
import socket

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.get("/")
def index():
    return jsonify(
        mensagem="Olá do container Docker! Use /converter?celsius=25",
        container=socket.gethostname(),
    )


@app.get("/converter")
def converter():
    try:
        celsius = float(request.args.get("celsius", ""))
    except ValueError:
        return jsonify(erro="Informe um número, ex.: /converter?celsius=25"), 400
    return jsonify(
        celsius=celsius,
        fahrenheit=round(celsius * 9 / 5 + 32, 2),
        kelvin=round(celsius + 273.15, 2),
    )


@app.get("/health")
def health():
    return "ok", 200


if __name__ == "__main__":
    # Apenas para rodar localmente sem Docker; no container quem serve é o Gunicorn.
    app.run(host="0.0.0.0", port=8000)
