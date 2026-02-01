# Используем легкий образ
FROM python:3.13-slim

# Устанавливаем системные зависимости
# ВАЖНО: Добавили curl. НЕ ставим docker.io через apt, он сломан.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем non-root пользователя для безопасности
RUN useradd -m -u 1000 appuser

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файлы зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Скачиваем официальную статическую сборку Docker CLI
# Используем версию 29.2.0
RUN curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-29.2.0.tgz-o /tmp/docker.tgz \
    && tar xzvf /tmp/docker.tgz -C /tmp \
    && mv /tmp/docker/docker /usr/local/bin/ \
    && chmod +x /usr/local/bin/docker \
    && rm -rf /tmp/docker.tgz /tmp/docker

# Копируем код бота
COPY bot ./bot

# Меняем владельца файлов на appuser
RUN chown -R appuser:appuser /app

# Переключаемся на non-root пользователя
USER appuser

# Запуск бота
ENTRYPOINT ["python", "-m", "bot.main"]