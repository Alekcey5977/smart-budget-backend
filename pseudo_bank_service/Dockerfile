FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*
COPY pseudo_bank_service/requirements.txt  ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .env
COPY ./shared ./shared
COPY pseudo_bank_service/app ./app
COPY pseudo_bank_service/scripts ./scripts
COPY testData /testData
RUN chmod +x /app/scripts/load_test_data.sh
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8004", "--backlog", "4096"]
