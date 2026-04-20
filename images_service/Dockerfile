FROM python:3.11-slim
WORKDIR /app
COPY images_service/requirements.txt  ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .env .env
COPY ./shared ./shared
COPY images_service/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003", "--workers", "2", "--backlog", "4096"]
