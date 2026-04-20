FROM python:3.11-slim
WORKDIR /app
COPY purposes_service/requirements.txt  ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .env
COPY ./shared ./shared
COPY purposes_service/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--workers", "4", "--backlog", "4096"]
