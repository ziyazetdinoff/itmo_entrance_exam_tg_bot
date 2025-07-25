#!/usr/bin/env python3
"""
Главный файл для запуска Telegram бота ИТМО.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.append(str(Path(__file__).parent))

from loguru import logger
from src.bot import main as bot_main


if __name__ == "__main__":
    try:
        logger.info("🤖 Запуск Telegram бота...")
        asyncio.run(bot_main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1) 