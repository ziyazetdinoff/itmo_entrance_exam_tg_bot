FROM python:3.11-slim

# Устанавливаем переменные окружения
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаем рабочую директорию
WORKDIR /app

# Копируем requirements.txt и устанавливаем Python зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем пользователя app
RUN useradd --create-home --shell /bin/bash app

# Создаем необходимые директории и устанавливаем права
RUN mkdir -p /app/data /app/logs /app/vector_db \
    && chown -R app:app /app

# Переключаемся на пользователя app
USER app

# Healthcheck для контейнера
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "from src.database import db_manager; db_manager.get_session().close()" || exit 1

# Открываем порт (если понадобится для webhook)
EXPOSE 8000

# Создаем startup скрипт
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🐳 Запуск ИТМО бота..."\n\
\n\
# Ожидание готовности БД\n\
echo "⏳ Ожидание готовности базы данных..."\n\
while ! pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do\n\
    echo "   База данных не готова, ждем 2 секунды..."\n\
    sleep 2\n\
done\n\
echo "✅ База данных готова!"\n\
\n\
# Проверка и запуск парсинга данных\n\
echo "📊 Проверка данных..."\n\
if python -c "\n\
import sys;\n\
sys.path.append(\"/app\");\n\
from src.database import db_manager;\n\
try:\n\
    programs = db_manager.get_all_programs();\n\
    if len(programs) == 0: sys.exit(0)\n\
    else: print(f\"Найдено {len(programs)} программ в БД\"); sys.exit(1)\n\
except: sys.exit(0)\n\
"; then\n\
    echo "🔄 Запуск парсинга данных..."\n\
    python parse_data.py || echo "⚠️ Парсинг завершился с ошибками, продолжаем"\n\
else\n\
    echo "ℹ️ Данные уже есть в базе, пропускаем парсинг"\n\
fi\n\
\n\
# Запуск бота\n\
echo "🤖 Запуск Telegram бота..."\n\
exec python main.py\n' > /app/startup.sh \
    && chmod +x /app/startup.sh

# Команда запуска
CMD ["/app/startup.sh"] 