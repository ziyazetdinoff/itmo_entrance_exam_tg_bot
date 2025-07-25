# ITMO Entrance Exam Telegram Bot

Чат-бот для помощи абитуриентам в выборе магистерских программ ИТМО.

## Функции

- Парсинг информации о программах магистратуры ИТМО (AI и AI Product)
- Диалоговая система для сбора информации об абитуриенте
- RAG-система для ответов на вопросы о программах
- Рекомендации по выбору программы и дисциплин

## Технологический стек

- **Backend**: Python 3.11
- **Bot Framework**: python-telegram-bot
- **Database**: PostgreSQL
- **RAG/LLM**: LangChain + Anthropic Claude
- **Vector DB**: ChromaDB
- **Containerization**: Docker + Docker Compose

## 🐳 Быстрый старт через Docker (рекомендуется)

### 📋 Требования
- Docker и Docker Compose
- Telegram Bot Token (от @BotFather)
- Anthropic API ключ

### 🚀 Автоматический запуск за 3 шага

1. **Клонируйте репозиторий**
   ```bash
   git clone <repository-url>
   cd itmo_entrance_exam_tg_bot
   ```

2. **Настройте токены**
   ```bash
   cp env.example .env
   # Отредактируйте .env файл и укажите ТОЛЬКО эти 2 строки:
   # TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather
   # ANTHROPIC_API_KEY=ваш_ключ_от_claude.ai
   ```

3. **Запустите всё одной командой**
   ```bash
   docker-compose up --build -d
   ```

**Готово!** 🎉 Docker автоматически:
- Соберёт Docker образы
- Запустит PostgreSQL базу данных
- Дождётся готовности БД
- Спарсит данные с сайта ИТМО
- Проиндексирует их для ИИ
- Запустит Telegram бота

### 📱 Как получить токены

**Telegram Bot Token:**
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен

**Anthropic API Key:**
1. Зайдите на [console.anthropic.com](https://console.anthropic.com)
2. Зарегистрируйтесь/войдите
3. Создайте API ключ
4. Скопируйте ключ

### 🛠️ Управление системой

**Вариант 1: Docker команды**
```bash
# 🚀 Запуск всей системы (первый раз с сборкой)
docker-compose up --build -d

# 🚀 Обычный запуск (после первого раза)
docker-compose up -d

# 📋 Просмотр логов бота
docker-compose logs -f bot

# 📋 Просмотр всех логов
docker-compose logs -f

# 🛑 Остановка системы
docker-compose down

# 🔄 Перезапуск только бота
docker-compose restart bot

# 📊 Статус контейнеров
docker-compose ps

# 🧹 Полная очистка (с удалением данных)
docker-compose down -v
```
📖 **[Полный справочник Docker команд](DOCKER_COMMANDS.md)**

**Вариант 2: Makefile (удобные команды)**
```bash
# 📋 Список всех команд
make help

# 🚀 Запуск системы (автоматическая настройка + запуск)
make start

# 📋 Просмотр логов
make logs

# 🛑 Остановка
make stop

# 🔄 Перезапуск
make restart

# 📊 Статус
make status

# 🔧 PgAdmin (веб-интерфейс БД)
make admin
```

---

## 💻 Альтернативный запуск (без Docker)

Если не хотите использовать Docker, можете запустить локально:

### Требования
- Python 3.9+
- PostgreSQL
- Все токены из раздела выше

### Установка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка .env (укажите локальную БД)
cp env.example .env
# DATABASE_URL=postgresql://user:pass@localhost:5432/dbname

# Парсинг данных
python parse_data.py

# Запуск бота
python main.py
```

## 🛠️ Разработка

### Локальная установка
```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка dev зависимостей
pip install pytest pytest-asyncio pytest-mock black isort mypy
```

### Запуск тестов
```bash
# Все тесты
pytest

# С покрытием кода
pytest --cov=src --cov-report=html

# Только быстрые тесты
pytest -m "not slow"
```

### Форматирование кода
```bash
# Форматирование
black src/ tests/
isort src/ tests/

# Проверка типов
mypy src/

# Проверка стиля
flake8 src/
```

### Структура команд
```bash
# Парсинг данных
python parse_data.py

# Запуск бота
python main.py

# Тесты
pytest

# Очистка данных
rm -rf data/ logs/ vector_db/
```

📁 Структура проекта

```
itmo_entrance_exam_tg_bot/
├── 🚀 БЫСТРЫЙ ЗАПУСК
│   ├── Makefile                # 🎯 Удобные команды (make start, make stop, ...)
│   ├── QUICK_START.md          # ⚡ Краткое руководство по запуску
│   └── .env                    # ⚙️ Переменные окружения (создать из .env.example)
│
├── 🧩 ИСХОДНЫЙ КОД
│   ├── src/
│   │   ├── __init__.py
│   │   ├── bot.py             # 🤖 Telegram bot + handlers
│   │   ├── parser.py          # 📊 Парсинг сайтов ИТМО
│   │   ├── pdf_parser.py      # 📄 Парсинг PDF файлов
│   │   ├── rag.py             # 🧠 RAG + LLM + embeddings
│   │   ├── database.py        # 🗄️ SQLAlchemy модели + CRUD
│   │   ├── config.py          # ⚙️ Настройки приложения
│   │   └── utils.py           # 🛠️ Логирование + вспомогательные функции
│   │
│   ├── main.py                # 🎯 Главный файл запуска бота
│   └── parse_data.py          # 📋 Скрипт первичного парсинга
│
├── 🧪 ТЕСТИРОВАНИЕ
│   ├── tests/
│   │   ├── conftest.py        # Конфигурация pytest + фикстуры
│   │   └── test_main.py       # Основные тесты
│   └── .github/workflows/
│       └── ci.yml             # 🚀 GitHub Actions pipeline
│
├── 🐳 DOCKER
│   ├── Dockerfile             # Docker образ приложения
│   ├── docker-compose.yml     # Оркестрация сервисов
│   ├── docker-entrypoint.sh   # Автоматизация запуска
│   └── .dockerignore          # Исключения для Docker
│
├── 📦 КОНФИГУРАЦИЯ
│   ├── requirements.txt       # Зависимости Python
│   ├── pyproject.toml         # Конфигурация проекта
│   ├── .env.example           # Пример переменных окружения
│   └── .gitignore            # Исключения для Git
│
└── 📖 ДОКУМЕНТАЦИЯ
    ├── README.md              # Основная документация
    └── QUICK_START.md         # Быстрый старт
```

## Настройка

1. Получите Telegram Bot Token от @BotFather
2. Получите Anthropic API ключ
3. Настройте переменные в `.env` файле

## Лицензия

MIT License 