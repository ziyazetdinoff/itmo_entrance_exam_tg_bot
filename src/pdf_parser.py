"""Парсер PDF файлов с учебными планами ИТМО."""

import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

import pdfplumber
from loguru import logger


@dataclass
class Subject:
    """Модель данных о дисциплине/модуле."""
    semester: str
    name: str
    credits: Optional[float] = None
    hours: Optional[int] = None
    type: str = "дисциплина"  # дисциплина, практика, аттестация, модуль


class PDFParser:
    """Парсер для PDF файлов с учебными планами."""
    
    def __init__(self):
        """Инициализация парсера."""
        pass
    
    def extract_program_name_from_pdf(self, pdf_path: str) -> Optional[str]:
        """Извлекает название программы из PDF файла."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                if not pdf.pages:
                    logger.error(f"PDF файл пустой: {pdf_path}")
                    return None
                
                # Ищем название программы на первой странице
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                if not text:
                    logger.error(f"Не удалось извлечь текст из PDF: {pdf_path}")
                    return None
                
                lines = text.split('\n')
                
                # В наших PDF название программы обычно во второй строке
                if len(lines) >= 2:
                    program_name = lines[1].strip()
                    if program_name.startswith('ОП '):
                        program_name = program_name[3:]  # Убираем префикс "ОП "
                    
                    logger.info(f"Найдено название программы: {program_name}")
                    return program_name
                
                logger.warning(f"Не удалось найти название программы в PDF: {pdf_path}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка извлечения названия программы из PDF {pdf_path}: {e}")
            return None
    
    def find_curriculum_table(self, pdf_path: str) -> Optional[List[Dict[str, Any]]]:
        """Ищет и извлекает таблицу с учебным планом."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_subjects = []
                
                for page_num, page in enumerate(pdf.pages):
                    # Ищем таблицы на странице
                    tables = page.extract_tables()
                    
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        # Парсим таблицу, начиная с первой или второй строки в зависимости от страницы
                        start_row = 2 if page_num == 0 else 0  # На первой странице пропускаем заголовки
                        page_subjects = self._parse_curriculum_table(table, start_row)
                        all_subjects.extend(page_subjects)
                        
                        logger.info(f"На странице {page_num + 1} найдено предметов: {len(page_subjects)}")
                
                return all_subjects if all_subjects else None
                
        except Exception as e:
            logger.error(f"Ошибка поиска таблицы учебного плана в PDF {pdf_path}: {e}")
            return None
    
    def _parse_curriculum_table(self, table: List[List], start_row: int = 0) -> List[Dict[str, Any]]:
        """Парсит таблицу учебного плана."""
        subjects = []
        
        if not table or len(table) <= start_row:
            return subjects
        
        logger.info(f"Парсинг таблицы, начиная со строки {start_row}, всего строк: {len(table)}")
        
        # Парсим строки данных
        for row_idx, row in enumerate(table[start_row:], start_row):
            if not row or len(row) < 4:  # Ожидаем минимум 4 столбца
                continue
            
            # Извлекаем данные из строки (структура: семестр, название, з.ед., часы)
            semester = self._extract_cell_value(row, 0)
            name = self._extract_cell_value(row, 1)
            credits_str = self._extract_cell_value(row, 2)
            hours_str = self._extract_cell_value(row, 3)
            
            # Пропускаем пустые или служебные строки
            if not name or len(name.strip()) < 3:
                continue
            
            # Пропускаем заголовки и промежуточные строки
            name_lower = name.lower()
            if any(skip_word in name_lower for skip_word in [
                'итого', 'всего', 'общая', 'семестр', 'наименование', 'трудоемкость',
                'блок', 'модули', 'дисциплины', 'практики', 'аттестации', 'гиа'
            ]):
                # Проверяем, не является ли это названием блока с полезной информацией
                if any(block_word in name_lower for block_word in ['блок']):
                    # Это может быть заголовок блока, пропускаем
                    logger.debug(f"Пропускаем заголовок блока: {name}")
                continue
            
            # Парсим числовые значения
            credits = self._parse_numeric_value(credits_str)
            hours = self._parse_numeric_value(hours_str, is_int=True)
            
            # Пропускаем строки без валидных данных о кредитах или часах
            if credits is None or hours is None:
                logger.debug(f"Пропускаем строку без числовых данных: {name}")
                continue
            
            # Определяем тип предмета
            subject_type = self._determine_subject_type(name)
            
            subject_data = {
                'semester': semester,
                'name': name.strip(),
                'credits': credits,
                'hours': hours,
                'type': subject_type
            }
            
            subjects.append(subject_data)
            logger.debug(f"Добавлен предмет: {subject_data}")
        
        logger.info(f"Извлечено предметов из таблицы: {len(subjects)}")
        return subjects
    
    def _extract_cell_value(self, row: List, index: int) -> str:
        """Извлекает значение ячейки по индексу."""
        if index >= len(row):
            return ""
        
        cell_value = row[index]
        return str(cell_value).strip() if cell_value else ""
    
    def _parse_numeric_value(self, value_str: str, is_int: bool = False) -> Optional[float]:
        """Парсит числовое значение из строки."""
        if not value_str:
            return None
        
        # Очищаем строку от лишних символов
        clean_value = re.sub(r'[^\d.,]', '', value_str)
        clean_value = clean_value.replace(',', '.')
        
        if not clean_value:
            return None
        
        try:
            if is_int:
                return int(float(clean_value))
            else:
                return float(clean_value)
        except (ValueError, TypeError):
            return None
    
    def _determine_subject_type(self, name: str) -> str:
        """Определяет тип предмета по его названию."""
        name_lower = name.lower()
        
        if any(keyword in name_lower for keyword in ['практика', 'стажировка']):
            return 'практика'
        elif any(keyword in name_lower for keyword in ['аттестация', 'экзамен', 'зачет', 'вкр', 'защита']):
            return 'аттестация'
        elif any(keyword in name_lower for keyword in ['модуль', 'блок']):
            return 'модуль'
        elif any(keyword in name_lower for keyword in ['воркшоп', 'workshop']):
            return 'воркшоп'
        else:
            return 'дисциплина'
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """Парсит PDF файл и возвращает структурированные данные."""
        logger.info(f"Начинаю парсинг PDF файла: {pdf_path}")
        
        # Извлекаем название программы
        program_name = self.extract_program_name_from_pdf(pdf_path)
        
        # Извлекаем таблицу с учебным планом
        subjects_data = self.find_curriculum_table(pdf_path)
        
        result = {
            'pdf_path': pdf_path,
            'program_name_from_pdf': program_name,
            'subjects': subjects_data or [],
            'parsing_success': bool(subjects_data)
        }
        
        logger.info(f"Парсинг завершен. Найдено предметов: {len(result['subjects'])}")
        return result


def parse_all_pdfs(data_dir: str = "./data") -> Dict[str, Dict[str, Any]]:
    """Парсит все PDF файлы в директории."""
    data_path = Path(data_dir)
    pdf_parser = PDFParser()
    results = {}
    
    # Ищем все PDF файлы
    pdf_files = list(data_path.glob("*.pdf"))
    
    if not pdf_files:
        logger.warning(f"Не найдено PDF файлов в директории: {data_dir}")
        return results
    
    logger.info(f"Найдено PDF файлов: {len(pdf_files)}")
    
    for pdf_file in pdf_files:
        try:
            result = pdf_parser.parse_pdf(str(pdf_file))
            results[str(pdf_file)] = result
        except Exception as e:
            logger.error(f"Ошибка парсинга файла {pdf_file}: {e}")
    
    return results


if __name__ == "__main__":
    # Тестируем парсер
    results = parse_all_pdfs()
    
    for pdf_path, result in results.items():
        print(f"\n=== {pdf_path} ===")
        print(f"Название программы: {result['program_name_from_pdf']}")
        print(f"Успешность парсинга: {result['parsing_success']}")
        print(f"Количество предметов: {len(result['subjects'])}")
        
        if result['subjects']:
            print("\nПервые 5 предметов:")
            for subject in result['subjects'][:5]:
                print(f"  - {subject['name']} (семестр: {subject['semester']}, з.ед: {subject['credits']}, часы: {subject['hours']})")
        
        # Группировка по семестрам
        if result['subjects']:
            semesters = {}
            for subject in result['subjects']:
                sem = subject['semester']
                if sem not in semesters:
                    semesters[sem] = 0
                semesters[sem] += 1
            
            print(f"\nРаспределение по семестрам:")
            for sem, count in sorted(semesters.items()):
                print(f"  Семестр {sem}: {count} предметов") 