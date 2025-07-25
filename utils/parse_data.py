#!/usr/bin/env python3
"""
Скрипт для парсинга данных магистерских программ ИТМО.
Запускает парсер и скачивает PDF файлы с учебными планами.
"""

import sys
from pathlib import Path

# Добавляем src в путь для импорта
sys.path.append(str(Path(__file__).parent / "src"))

from loguru import logger
from parser import ITMOParser

def setup_logging():
    """Настройка логирования."""
    logger.remove()  # Удаляем стандартный обработчик
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/parser.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB"
    )

def main():
    """Основная функция."""
    # Настройка логирования
    Path("logs").mkdir(exist_ok=True)
    setup_logging()
    
    logger.info("🚀 Запуск парсера программ ИТМО")
    logger.info("Целевые программы:")
    logger.info("  • Искусственный интеллект")
    logger.info("  • Управление ИИ-продуктами/AI Product")
    
    try:
        # Создание парсера
        parser = ITMOParser(output_dir="./data")
        
        # Парсинг всех программ
        programs = parser.parse_all_programs()
        
        if not programs:
            logger.error("❌ Не удалось получить данные ни одной программы")
            return 1
        
        # Сохранение данных
        parser.save_programs_data(programs)
        
        # Вывод результатов
        logger.success(f"✅ Успешно обработано программ: {len(programs)}")
        print("\n" + "="*60)
        print("📊 РЕЗУЛЬТАТЫ ПАРСИНГА")
        print("="*60)
        
        for i, program in enumerate(programs, 1):
            print(f"\n{i}. {program.name}")
            print(f"   ID: {program.id}")
            print(f"   URL: {program.url}")
            print(f"   Длительность: {program.duration}")
            print(f"   Формат: {program.format}")
            print(f"   Язык: {program.language}")
            print(f"   PDF URL: {program.pdf_url}")
            print(f"   PDF файл: {program.pdf_path}")
            
            if program.description:
                desc_preview = program.description[:150] + "..." if len(program.description) > 150 else program.description
                print(f"   Описание: {desc_preview}")
        
        print(f"\n📁 Все файлы сохранены в директории: ./data/")
        logger.success("🎉 Парсинг завершен успешно!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 