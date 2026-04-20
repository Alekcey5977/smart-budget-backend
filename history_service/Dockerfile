FROM python:3.11-slim
WORKDIR /app
COPY history_service/requirements.txt  ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .env
COPY ./shared ./shared
COPY history_service/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007", "--workers", "2", "--backlog", "4096"]
