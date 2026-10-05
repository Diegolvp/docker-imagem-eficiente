# syntax=docker/dockerfile:1
# =============================================================================
# Dockerfile otimizado com MULTI-STAGE BUILD
#   Estágio 1 (builder): instala as dependências num ambiente virtual (venv).
#   Estágio 2 (final):   recebe só o venv pronto e o código, sem restos da instalação.
# =============================================================================

# ---------- ESTÁGIO 1: BUILD ----------
# Versão fixa (não "latest") para builds reproduzíveis.
# "slim" é a variante Debian enxuta (~130 MB, contra ~1 GB da imagem padrão).
FROM python:3.12-slim AS builder

# Não guarda o cache do pip e não checa versão nova do pip (menos lixo, build mais rápido).
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Instala as dependências num venv isolado, que depois é copiado inteiro para o estágio final.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copia primeiro SÓ o requirements.txt. Enquanto ele não mudar, o Docker
# reaproveita esta camada do cache e não reinstala as dependências.
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- ESTÁGIO 2: IMAGEM FINAL ----------
# Mesma imagem base do builder, para que o venv copiado funcione sem ajustes.
FROM python:3.12-slim

# PYTHONDONTWRITEBYTECODE: não cria arquivos .pyc (imagem mais limpa)
# PYTHONUNBUFFERED: logs aparecem na hora no "docker logs"
# PATH: usa o Python e os pacotes do venv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Cria um usuário comum para não rodar a aplicação como root.
RUN useradd --create-home --uid 1000 appuser

WORKDIR /app

# Copia do builder apenas o venv com as dependências já instaladas.
COPY --from=builder /opt/venv /opt/venv

# Copia o código por último, porque é o que mais muda (aproveita melhor o cache).
COPY --chown=appuser:appuser app.py .

USER appuser

# Documenta a porta usada pela aplicação.
EXPOSE 8000

# O Docker verifica periodicamente se a aplicação está respondendo.
# A imagem slim não tem curl, então o próprio Python faz a requisição.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]

# Gunicorn é um servidor de produção (o servidor embutido do Flask é só para desenvolvimento).
# Forma "exec" (JSON): o Gunicorn vira o PID 1 e recebe o sinal do "docker stop" corretamente.
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "app:app"]
