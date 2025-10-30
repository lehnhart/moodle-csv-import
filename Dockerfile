# Usa a imagem oficial do uv na versão que foi desenvolvida com Python 3.12
FROM ghcr.io/astral-sh/uv:0.8.15-python3.12-bookworm-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia apenas os manifestos primeiro para aproveitar cache
COPY pyproject.toml uv.lock ./

# Instala dependências do projeto usando uv
RUN uv sync --locked

# Copia o código da aplicação
COPY . .

# Cria o diretório de uploads (sem volume; temporário dentro do container)
RUN mkdir -p uploads && \
    chown -R nobody:nogroup /app && \
    chmod -R 755 /app

# Não rodar como root
USER nobody

# Expõe a porta da aplicação
EXPOSE 5000

# Configura variáveis de ambiente
ENV FLASK_APP=main.py \
    FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Inicia a aplicação usando uv
CMD ["uv", "run", "main.py", "--host", "0.0.0.0", "--port", "5000"]