# Imagem só para rodar os testes de integração (não vai para produção).
FROM python:3.12-slim

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /tests
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY test_api.py .

CMD ["pytest", "-v", "test_api.py"]
