FROM python:3.9-slim

WORKDIR /app

# REMOVED: Dependency installation during build
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY models ./models
COPY app.py .

# Expor porta para a API
EXPOSE 7000

# Comando para iniciar a aplicação
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7000"]
