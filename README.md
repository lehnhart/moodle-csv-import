# Moodle CSV Import

Ferramenta para importação de arquivos CSV para o Moodle.

## Descrição

Este projeto fornece uma interface para realizar o pré-processamento de dados contidos em planilhas, permitindo gerar um arquivo CSV no padrão de importação aceito pelo Moodle, facilitando a inscrição/matrícula em massa de usuários em seus respectivos cursos e grupos.

## Requisitos

- Python 3.12 ou superior
- Ambiente virtual Python (venv)
- Pacotes Python listados em `pyproject.toml`

## Instalação

1. Clone o repositório:
```bash
git clone https://github.com/lehnhart/moodle-csv-import.git
cd moodle-csv-import
```

2. Instale as dependências usando uv:
```bash
uv sync
```

## Uso

Execute o script principal:

```bash
uv run main.py
```

## Estrutura do Projeto

```
main.py              # Script principal
pyproject.toml       # Configurações do projeto e dependências
uploads/             # Pasta para processamento temporário de arquivos CSV.
```

## Contribuindo

Sinta-se à vontade para abrir issues ou enviar pull requests com melhorias.

## Licença

Este projeto está licenciado sob a licença MIT. Veja o arquivo `LICENSE` para mais detalhes.