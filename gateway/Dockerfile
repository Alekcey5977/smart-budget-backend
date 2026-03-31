FROM python:3.11-slim
WORKDIR /app

# Копируем requirements и устанавливаем зависимости
COPY gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Копируем shared пакет
COPY ./shared ./shared

# Копируем приложение
COPY gateway/app ./app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
