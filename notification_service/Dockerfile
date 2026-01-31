FROM python:3.11-slim
WORKDIR /app
COPY notification_service/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY ./shared ./shared
COPY notification_service/app ./app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8006"]