# Usa a imagem oficial do uv na versão que foi desenvolvida com Python 3.12
FROM ghcr.io/astral-sh/uv:0.8.15-python3.12-bookworm-slim

# Define o diretório de trabalho
WORKDIR /app

# Copia os arquivos de configuração
COPY pyproject.toml uv.lock ./

# Instala as dependências do projeto
RUN uv sync --locked && uv pip install gunicorn

# Copia o código da aplicação
COPY . .

# Cria e configura o diretório de uploads
RUN mkdir -p uploads && \
    chown -R nobody:nogroup /app && \
    chmod -R 755 /app

# Muda para usuário não-root
USER nobody

# Expõe a porta da aplicação
EXPOSE 5000

# Configura variáveis de ambiente
ENV FLASK_APP=main:app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Inicia a aplicação
CMD ["python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "main:app"]