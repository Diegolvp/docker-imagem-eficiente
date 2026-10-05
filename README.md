# Imagem Docker eficiente: API de conversão de temperatura (Python)

API em Flask que converte Celsius para Fahrenheit e Kelvin, empacotada numa imagem Docker otimizada com **multi-stage build**.

Rotas: `/` (informações), `/converter?celsius=25` (conversão) e `/health` (verificação de saúde).

## Arquivos

| Arquivo | Função |
|---|---|
| `app.py` | Aplicação Flask |
| `requirements.txt` | Dependências com versões fixas |
| `Dockerfile` | Dockerfile otimizado e comentado (multi-stage, `python:3.12-slim`) |
| `Dockerfile.naive` | Versão sem otimização, só para comparar o tamanho |
| `.dockerignore` | Deixa de fora do contexto de build os arquivos desnecessários |

## Como executar no GitHub Codespaces

1. Suba estes arquivos num repositório do GitHub.
2. No repositório, clique em **Code → Codespaces → Create codespace on main**.
3. No terminal do Codespace, rode:

```bash
# 1. Construir a imagem otimizada
docker build -t app-otimizada .

# 2. (Comparação) Construir a imagem sem otimização
docker build -f Dockerfile.naive -t app-naive .

# 3. Comparar os tamanhos
docker images | grep app-

# 4. Executar o container em segundo plano
docker run -d --name app -p 8000:8000 app-otimizada

# 5. Testar se está funcionando
curl http://localhost:8000/
curl "http://localhost:8000/converter?celsius=25"

# 6. Ver o status (após ~5 s deve aparecer "healthy") e os logs
docker ps
docker logs app

# 7. Confirmar que não roda como root
docker exec app whoami
```

Saída esperada da conversão:

```json
{"celsius":25.0,"fahrenheit":77.0,"kelvin":298.15}
```

> **Evidência para entregar:** tire o print do terminal mostrando os passos 3, 5 e 6 (tamanhos das imagens, resposta do `curl` e o container com status `healthy`).

Para limpar: `docker rm -f app`

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
