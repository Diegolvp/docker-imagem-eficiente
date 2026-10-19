# Imagem Docker eficiente + Docker Compose: API de conversão de temperatura (Python)

API em Flask que converte Celsius para Fahrenheit e Kelvin, empacotada numa imagem Docker otimizada com **multi-stage build** e orquestrada com **Docker Compose** junto com PostgreSQL e Redis.

Rotas: `/` (informações + contador de visitas no Redis), `/converter?celsius=25` (conversão, com cache no Redis e gravação no Postgres), `/historico` (últimas 10 conversões) e `/health` (verifica app, banco e cache).

## Arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Aplicação Flask |
| `requirements.txt` | Dependências com versões fixas |
| `Dockerfile` | Dockerfile otimizado e comentado (multi-stage, `python:3.12-slim`) |
| `Dockerfile.naive` | Versão sem otimização, só para comparar o tamanho |
| `.dockerignore` | Deixa de fora do contexto de build os arquivos desnecessários |
| `compose.yaml` | Stack completa: app + PostgreSQL + Redis, com redes, volumes e restart |
| `db/init.sql` | Cria a tabela `conversoes` na primeira subida do Postgres |
| `compose.test.yaml` | Stack descartável para testes automáticos (CI) |
| `tests/` | Testes de integração (pytest) e o Dockerfile que os executa |
| `.github/workflows/ci.yml` | GitHub Actions: roda o compose de testes a cada push/PR |

## Docker Compose

| Serviço | Imagem | Rede | Volume | Restart |
|---|---|---|---|---|
| `app` | `docker-imagem-eficiente:1.0` (este Dockerfile) | `frontend` + `backend` | — | `unless-stopped` |
| `db` | `postgres:16-alpine` | `backend` | `pgdata` | `unless-stopped` |
| `cache` | `redis:7-alpine` | `backend` | `redisdata` | `unless-stopped` |

- **Redes:** `frontend` é onde a API fica publicada na porta 8000. `backend` é `internal: true`: banco e cache não têm porta exposta nem acesso externo, e só a app fala com eles.
- **Volumes:** `pgdata` e `redisdata` são volumes nomeados, então os dados sobrevivem a `docker compose down`. O `init.sql` entra como bind mount somente leitura.
- **Ordem de subida:** `depends_on` com `condition: service_healthy` faz a app esperar o Postgres (`pg_isready`) e o Redis (`redis-cli ping`) ficarem saudáveis.
- **Restart:** `unless-stopped` reinicia o container se ele cair ou se o Docker reiniciar, menos quando você o para de propósito.
- **Variáveis:** usuário e senha do banco aceitam `POSTGRES_USER`, `POSTGRES_PASSWORD` e `POSTGRES_DB` (por um arquivo `.env`, por exemplo), com `app` como padrão.

## Testes automáticos (CI)

O `compose.test.yaml` sobe app, banco (em `tmpfs`, sempre limpo) e cache, e roda o container `tests`, que faz requisições reais na API. O comando termina com o código de saída do pytest:

```bash
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down -v
```

No GitHub, o workflow `.github/workflows/ci.yml` roda esse mesmo comando a cada push na `main` e em pull requests (aba **Actions**).

## Como executar no GitHub Codespaces

1. No repositório, clique em **Code → Codespaces → Create codespace on main**.
2. No terminal do Codespace, rode:

```bash
# 1. Construir a imagem e subir a stack inteira em segundo plano
docker compose up -d --build

# 2. Ver os 3 serviços (aguarde ~10 s até todos ficarem "healthy")
docker compose ps

# 3. Testar a API
curl http://localhost:8000/
curl "http://localhost:8000/converter?celsius=25"   # "origem": "calculado"
curl "http://localhost:8000/converter?celsius=25"   # "origem": "cache" (Redis)
curl http://localhost:8000/historico                # gravado no Postgres

# 4. Ver redes, volumes e logs
docker network ls | grep docker-imagem-eficiente
docker volume ls | grep docker-imagem-eficiente
docker compose logs app

# 5. Restart: derrubar o Gunicorn (PID 1) por dentro e ver o Docker reiniciar o container
docker exec temperatura-app python -c "import os, signal; os.kill(1, signal.SIGTERM)"
sleep 5
docker compose ps app
docker inspect -f 'RestartCount={{.RestartCount}}' temperatura-app   # deve mostrar 1
#   (docker stop/kill contam como parada manual, e aí o unless-stopped não reinicia)

# 6. Persistência: derrubar e subir de novo; o histórico continua lá
docker compose down
docker compose up -d
sleep 10 && curl http://localhost:8000/historico

# 7. Rodar os testes automáticos (o mesmo do CI)
docker compose -f compose.test.yaml up --build --abort-on-container-exit --exit-code-from tests
docker compose -f compose.test.yaml down -v

# 8. Limpar tudo
docker compose down -v
```

> **Evidência para entregar:** prints do terminal com os passos 2, 3, 5, 6 e 7 (serviços `healthy`, respostas do `curl`, restart automático, histórico após o `down`/`up` e `6 passed` nos testes).

3. **Finalize o Codespace** para não gastar as horas mensais: no terminal, `gh codespace stop`, ou no GitHub em **Code → Codespaces → ⋯ → Stop codespace** (use **Delete** se não for mais usar).

### Comparação de tamanho (atividade anterior)

```bash
docker build -t app-otimizada .
docker build -f Dockerfile.naive -t app-naive .
docker images | grep app-
```

## Escolhas de otimização

1. **Imagem base `python:3.12-slim`.** A variante slim tem só o essencial do Debian. A imagem fica em torno de **150 MB**, contra **mais de 1 GB** da `python:3.12` completa usada no `Dockerfile.naive`. Isso significa menos download, deploy mais rápido e menos pacotes com possíveis vulnerabilidades.

2. **Multi-stage build.** O primeiro estágio instala as dependências num ambiente virtual (`/opt/venv`). A imagem final copia só esse venv pronto, então arquivos temporários da instalação não entram nela. Se no futuro alguma dependência precisar de compilador (gcc etc.), ele é instalado só no builder e também não chega à imagem final.

3. **Ordem das camadas pensando no cache.** O `requirements.txt` é copiado e instalado **antes** do código. Quando só o `app.py` muda, o Docker reaproveita a camada das dependências e o rebuild leva poucos segundos.

4. **Sem cache do pip e sem `.pyc`.** `PIP_NO_CACHE_DIR=1` e `PYTHONDONTWRITEBYTECODE=1` evitam guardar arquivos inúteis na imagem.

5. **`.dockerignore`.** Evita mandar `.git`, `venv`, `__pycache__` etc. para o build. O contexto fica menor, o build fica mais rápido e nada desnecessário vaza para a imagem.

6. **Usuário não-root (`appuser`).** Se a aplicação for comprometida, o atacante não tem privilégios de root dentro do container.

7. **Gunicorn em vez do servidor do Flask.** O servidor embutido do Flask é só para desenvolvimento. O Gunicorn é um servidor de produção e atende requisições em paralelo com 2 workers.

8. **`HEALTHCHECK`.** O Docker verifica a rota `/health` e marca o container como `healthy` ou `unhealthy`, ou seja, sabe se a aplicação está respondendo e não só se o processo está vivo. Como a imagem slim não tem `curl`, quem faz a requisição é o próprio Python.

9. **Versões fixas e `CMD` em forma exec.** `python:3.12-slim` em vez de `latest` e dependências com versão fixa deixam o build reproduzível. A forma JSON do `CMD` faz o Gunicorn ser o PID 1 e receber o sinal do `docker stop`, o que permite um desligamento limpo.
