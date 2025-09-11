# Serviço de Transcrição de Áudio para Texto

Este serviço utiliza o modelo Whisper para transcrever arquivos de áudio em texto.

## Funcionalidades

- Recebe arquivos de áudio via API REST
- Transcreve o áudio para texto usando o modelo Whisper
- Encaminha o texto transcrito para o serviço de processamento de texto

## Requisitos

- Python 3.9+
- Modelo Whisper (baixado automaticamente na primeira execução)

## Variáveis de Ambiente

- `WHISPER_MODEL_SIZE`: Tamanho do modelo Whisper a ser utilizado (tiny, base, small, medium, large)
- `TEXT_PROCESSOR_URL`: URL do serviço de processamento de texto

## Endpoints da API

- `GET /health`: Verificação de saúde do serviço
- `POST /transcribe`: Recebe um arquivo de áudio e retorna o texto transcrito
  - Parâmetros:
    - `file`: Arquivo de áudio (multipart/form-data)
    - `forward`: Booleano indicando se o texto deve ser encaminhado para o próximo serviço (padrão: true)

## Executando Localmente

```bash
pip install -r requirements.txt
uvicorn app:app --reload
```

## Construindo a Imagem Docker

```bash
docker build -t audio-to-text:latest .
```
