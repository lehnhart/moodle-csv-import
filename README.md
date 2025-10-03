# Moodle CSV Import

Ferramenta para importação de arquivos CSV para o Moodle.

## Descrição

Este projeto fornece uma interface para realizar o pré-processamento de dados contidos em planilhas, permitindo gerar um arquivo CSV no padrão de importação aceito pelo Moodle, facilitando a inscrição/matrícula em massa de usuários em seus respectivos cursos e grupos.

## Requisitos

- Python 3.12 ou superior
- Ambiente virtual Python (venv)
- Pacotes Python listados em `pyproject.toml`

## Instalação e Uso

### Usando Docker (Recomendado)

1. Clone o repositório:
```bash
git clone https://github.com/lehnhart/moodle-csv-import.git
cd moodle-csv-import
```

2. Construa e execute o container:
```bash
docker compose up --build -d
```

A aplicação estará disponível em `http://localhost:5000`

Para parar a aplicação:
```bash
docker compose down
```

### Instalação Local

1. Clone o repositório:
```bash
git clone https://github.com/lehnhart/moodle-csv-import.git
cd moodle-csv-import
```

2. Instale as dependências usando uv:
```bash
uv sync
```

3. Execute o script principal:
```bash
uv run main.py
```

A aplicação estará disponível em `http://localhost:5000`

## Estrutura do Projeto

```
main.py              # Script principal
pyproject.toml       # Configurações do projeto e dependências
uploads/             # Pasta para processamento temporário de arquivos CSV
Dockerfile          # Configuração para construção da imagem Docker
docker-compose.yml  # Configuração para orquestração do container
```

## Requisitos para Docker

- Docker Engine 24.0.0 ou superior
- Docker Compose V2 ou superior

## Configuração do Container

O container Docker é configurado com:
- Python 3.12 com uv pré-instalado
- Porta 5000 exposta para acesso à aplicação
- Healthcheck configurado para monitoramento
- Ambiente de produção otimizado
- Reinício automático em caso de falhas

## Contribuindo

Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.