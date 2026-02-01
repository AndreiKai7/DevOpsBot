# Используем легкий образ
FROM python:3.13-slim

# Устанавливаем системные зависимости
# ДОБАВИЛИ docker.io, чтобы работала команда /ps и /logs
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    docker.io \
    && rm -rf /var/lib/apt/lists/*

# Создаем non-root пользователя для безопасности
RUN useradd -m -u 1000 appuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем код бота
COPY bot ./bot

# Меняем владельца файлов на appuser
RUN chown -R appuser:appuser /app

# Переключаемся на non-root пользователя
USER appuser

# Запуск бота
ENTRYPOINT ["python", "-m", "bot.main"]