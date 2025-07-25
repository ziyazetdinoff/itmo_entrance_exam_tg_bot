# ITMO Entrance Exam Telegram Bot
# Makefile для удобного управления Docker контейнерами

.PHONY: help setup start stop restart logs clean build test

# Цвета для вывода
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## 📋 Показать это меню помощи
	@echo "$(GREEN)🤖 ИТМО Telegram Bot - Команды управления$(NC)"
	@echo "=================================================="
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(YELLOW)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

setup: ## ⚙️ Первичная настройка проекта
	@echo "$(GREEN)📋 Настройка проекта...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(YELLOW)Создание .env файла из шаблона...$(NC)"; \
		cp env.example .env; \
		echo "$(RED)⚠️  ВАЖНО: Отредактируйте .env файл и укажите:$(NC)"; \
		echo "   - TELEGRAM_BOT_TOKEN (получить у @BotFather)"; \
		echo "   - ANTHROPIC_API_KEY (получить на claude.ai)"; \
	else \
		echo "$(GREEN)✅ Файл .env уже существует$(NC)"; \
	fi
	@mkdir -p data logs vector_db
	@echo "$(GREEN)✅ Директории созданы$(NC)"

start: setup ## 🚀 Запустить всю систему
	@echo "$(GREEN)🚀 Запуск системы...$(NC)"
	@docker-compose up --build -d
	@echo "$(GREEN)✅ Система запущена!$(NC)"
	@echo "$(YELLOW)📋 Полезные команды:$(NC)"
	@echo "   make logs    - просмотр логов"
	@echo "   make stop    - остановка системы"
	@echo "   make status  - статус контейнеров"

stop: ## 🛑 Остановить систему
	@echo "$(RED)🛑 Остановка системы...$(NC)"
	@docker-compose down
	@echo "$(GREEN)✅ Система остановлена$(NC)"

restart: ## 🔄 Перезапустить систему
	@echo "$(YELLOW)🔄 Перезапуск системы...$(NC)"
	@docker-compose restart
	@echo "$(GREEN)✅ Система перезапущена$(NC)"

restart-bot: ## 🤖 Перезапустить только бота
	@echo "$(YELLOW)🤖 Перезапуск бота...$(NC)"
	@docker-compose restart bot
	@echo "$(GREEN)✅ Бот перезапущен$(NC)"

logs: ## 📋 Показать логи бота
	@echo "$(GREEN)📋 Логи бота (Ctrl+C для выхода):$(NC)"
	@docker-compose logs -f bot

logs-all: ## 📊 Показать логи всех сервисов
	@echo "$(GREEN)📊 Логи всех сервисов (Ctrl+C для выхода):$(NC)"
	@docker-compose logs -f

logs-db: ## 🗄️ Показать логи базы данных
	@echo "$(GREEN)🗄️ Логи базы данных (Ctrl+C для выхода):$(NC)"
	@docker-compose logs -f db

status: ## 📊 Показать статус контейнеров
	@echo "$(GREEN)📊 Статус контейнеров:$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(GREEN)📈 Использование ресурсов:$(NC)"
	@docker stats --no-stream

build: ## 🔨 Пересобрать Docker образы
	@echo "$(GREEN)🔨 Сборка Docker образов...$(NC)"
	@docker-compose build --no-cache
	@echo "$(GREEN)✅ Образы собраны$(NC)"

clean: ## 🧹 Полная очистка (ОСТОРОЖНО: удалит все данные!)
	@echo "$(RED)⚠️  ВНИМАНИЕ: Это удалит ВСЕ данные!$(NC)"
	@read -p "Вы уверены? [y/N]: " confirm && [ "$$confirm" = "y" ]
	@echo "$(RED)🧹 Полная очистка...$(NC)"
	@docker-compose down -v --rmi all
	@docker system prune -f
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

admin: ## 🔧 Запустить с PgAdmin (порт 8080)
	@echo "$(GREEN)🔧 Запуск с PgAdmin...$(NC)"
	@docker-compose --profile admin up -d
	@echo "$(GREEN)✅ PgAdmin доступен на http://localhost:8080$(NC)"
	@echo "   Email: admin@itmo-bot.local"
	@echo "   Password: admin123"

dev: ## 🛠️ Режим разработки (с live reload)
	@echo "$(GREEN)🛠️ Запуск в режиме разработки...$(NC)"
	@docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build
	
test: ## 🧪 Запустить тесты
	@echo "$(GREEN)🧪 Запуск тестов...$(NC)"
	@docker-compose exec bot pytest
	
shell: ## 💻 Войти в контейнер бота
	@echo "$(GREEN)💻 Вход в контейнер бота...$(NC)"
	@docker-compose exec bot /bin/bash

check-env: ## 🔍 Проверить настройки .env
	@echo "$(GREEN)🔍 Проверка .env файла...$(NC)"
	@if [ ! -f .env ]; then \
		echo "$(RED)❌ Файл .env не найден!$(NC)"; \
		echo "$(YELLOW)Запустите: make setup$(NC)"; \
		exit 1; \
	fi
	@if grep -q "your_telegram_bot_token_here" .env || grep -q "your_anthropic_api_key_here" .env; then \
		echo "$(RED)❌ В .env файле обнаружены незаполненные токены!$(NC)"; \
		echo "$(YELLOW)Отредактируйте .env и укажите реальные значения$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Файл .env настроен корректно$(NC)"

# Алиасы для удобства
up: start ## 🚀 Алиас для start
down: stop ## 🛑 Алиас для stop
ps: status ## �� Алиас для status 