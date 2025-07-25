"""Вспомогательные функции и настройка логирования."""

import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from .config import settings


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Настройка логирования.
    
    Args:
        log_file: Имя файла для логов (опционально)
    """
    # Убираем стандартный обработчик
    logger.remove()
    
    # Консольный вывод
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.log_level,
        colorize=True,
    )
    
    # Файловый вывод
    if log_file:
        logs_path = Path(settings.logs_dir) / log_file
    else:
        logs_path = Path(settings.logs_dir) / "app.log"
    
    logger.add(
        str(logs_path),
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="10 MB",
        retention="1 month",
        compression="zip",
    )
    
    logger.info(f"Логирование настроено. Файл: {logs_path}")


def format_program_info(program_data: dict) -> str:
    """
    Форматирует информацию о программе для отображения пользователю.
    
    Args:
        program_data: Словарь с данными программы
        
    Returns:
        Отформатированная строка
    """
    info_parts = []
    
    # Название программы
    if program_data.get("name"):
        info_parts.append(f"📚 **{program_data['name']}**\n")
    
    # Основная информация
    if program_data.get("duration"):
        info_parts.append(f"⏱ Длительность: {program_data['duration']}")
    
    if program_data.get("format"):
        info_parts.append(f"📖 Формат: {program_data['format']}")
    
    if program_data.get("language"):
        info_parts.append(f"🌐 Язык: {program_data['language']}")
    
    # Стоимость
    if program_data.get("cost_russian"):
        info_parts.append(f"💰 Стоимость (граждане РФ): {program_data['cost_russian']:,} руб.")
    
    if program_data.get("cost_foreign"):
        info_parts.append(f"💰 Стоимость (иностранцы): {program_data['cost_foreign']:,} руб.")
    
    # Описание
    if program_data.get("description"):
        desc = program_data["description"]
        if len(desc) > 500:
            desc = desc[:500] + "..."
        info_parts.append(f"\n📝 Описание:\n{desc}")
    
    # Карьерные перспективы
    if program_data.get("career_prospects"):
        career = program_data["career_prospects"]
        if len(career) > 300:
            career = career[:300] + "..."
        info_parts.append(f"\n🚀 Карьерные перспективы:\n{career}")
    
    # Количество предметов
    if program_data.get("subjects"):
        subjects_count = len(program_data["subjects"])
        info_parts.append(f"\n📊 Всего дисциплин: {subjects_count}")
    
    return "\n".join(info_parts)


def format_subjects_list(subjects: list, limit: int = 10) -> str:
    """
    Форматирует список предметов для отображения.
    
    Args:
        subjects: Список предметов
        limit: Максимальное количество предметов для показа
        
    Returns:
        Отформатированная строка
    """
    if not subjects:
        return "Предметы не найдены."
    
    formatted_subjects = []
    
    # Группируем по семестрам
    by_semester = {}
    for subject in subjects:
        semester = subject.get("semester", "Неизвестно")
        if semester not in by_semester:
            by_semester[semester] = []
        by_semester[semester].append(subject)
    
    for semester in sorted(by_semester.keys()):
        semester_subjects = by_semester[semester]
        formatted_subjects.append(f"\n**Семестр {semester}:**")
        
        for subject in semester_subjects[:limit]:
            name = subject.get("name", "Без названия")
            credits = subject.get("credits", 0)
            hours = subject.get("hours", 0)
            subject_type = subject.get("type", "дисциплина")
            
            formatted_subjects.append(
                f"• {name} ({credits} з.е., {hours} ч.) - {subject_type}"
            )
        
        if len(semester_subjects) > limit:
            remaining = len(semester_subjects) - limit
            formatted_subjects.append(f"... и еще {remaining} предметов")
    
    return "\n".join(formatted_subjects)


def sanitize_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов.
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Очищенное имя файла
    """
    import re
    
    # Убираем недопустимые символы
    clean_name = re.sub(r'[<>:"/\\|?*]', '', filename)
    
    # Заменяем пробелы на подчеркивания
    clean_name = re.sub(r'\s+', '_', clean_name)
    
    # Ограничиваем длину
    if len(clean_name) > 200:
        clean_name = clean_name[:200]
    
    return clean_name


def extract_keywords(text: str) -> list:
    """
    Извлекает ключевые слова из текста.
    
    Args:
        text: Входной текст
        
    Returns:
        Список ключевых слов
    """
    import re
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Убираем пунктуацию и извлекаем слова
    words = re.findall(r'\b[а-яё]+\b', text)
    
    # Фильтруем короткие слова и стоп-слова
    stop_words = {
        'в', 'на', 'с', 'по', 'для', 'от', 'до', 'из', 'к', 'о', 'об',
        'и', 'или', 'но', 'а', 'да', 'нет', 'не', 'что', 'как', 'где',
        'это', 'то', 'так', 'уже', 'еще', 'был', 'была', 'было', 'были'
    }
    
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    # Убираем дубликаты, сохраняя порядок
    seen = set()
    unique_keywords = []
    for keyword in keywords:
        if keyword not in seen:
            seen.add(keyword)
            unique_keywords.append(keyword)
    
    return unique_keywords[:20]  # Возвращаем до 20 ключевых слов 