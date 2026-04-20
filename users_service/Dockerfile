FROM python:3.11-slim
WORKDIR /app
COPY users_service/requirements.txt  ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .env
COPY ./shared ./shared
COPY users_service/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4", "--backlog", "4096"]
