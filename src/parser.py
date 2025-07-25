"""Парсер данных с сайтов магистерских программ ИТМО."""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

import requests
from bs4 import BeautifulSoup
from loguru import logger

# Импортируем PDF парсер
try:
    from .pdf_parser import PDFParser
except ImportError:
    from pdf_parser import PDFParser


@dataclass
class ProgramInfo:
    """Модель данных о магистерской программе."""
    id: int
    name: str
    url: str
    slug: str
    description: str
    duration: Optional[str] = None
    format: Optional[str] = None
    language: Optional[str] = None
    cost_russian: Optional[int] = None
    cost_foreign: Optional[int] = None
    admission_requirements: List[str] = None
    subjects: List[Dict[str, Any]] = None
    career_prospects: str = ""
    pdf_url: Optional[str] = None
    pdf_path: Optional[str] = None
    program_name_from_pdf: Optional[str] = None  # Добавляем название из PDF
    
    def __post_init__(self):
        if self.admission_requirements is None:
            self.admission_requirements = []
        if self.subjects is None:
            self.subjects = []


class ITMOParser:
    """Парсер для сайта abit.itmo.ru"""
    
    BASE_URL = "https://abit.itmo.ru"
    API_BASE_URL = "https://api.itmo.su/constructor-ep/api/v1/static/programs"
    
    def __init__(self, output_dir: str = "./data"):
        """
        Инициализация парсера.
        
        Args:
            output_dir: Директория для сохранения PDF файлов
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Настройка сессии
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Инициализируем PDF парсер
        self.pdf_parser = PDFParser()
    
    def get_page_content(self, url: str) -> str:
        """Получает содержимое страницы."""
        try:
            logger.info(f"Загружаю страницу: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            logger.error(f"Ошибка загрузки страницы {url}: {e}")
            raise
    
    def extract_program_data(self, html_content: str, url: str) -> Optional[ProgramInfo]:
        """Извлекает данные программы из HTML."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Поиск JSON данных в script тегах
        script_tags = soup.find_all('script', {'id': '__NEXT_DATA__'})
        if not script_tags:
            logger.error("Не найден JSON с данными программы")
            return None
        
        try:
            json_data = json.loads(script_tags[0].string)
            props = json_data.get('props', {}).get('pageProps', {})
            api_program = props.get('apiProgram', {})
            
            if not api_program:
                logger.error("Не найдены данные программы в JSON")
                return None
            
            # Извлечение основных данных
            program_id = api_program.get('id')
            name = api_program.get('title', '')
            slug = api_program.get('slug', '')
            
            # Формирование URL для PDF
            pdf_url = f"{self.API_BASE_URL}/{program_id}/plan/abit/pdf" if program_id else None
            
            # Извлечение описания
            description = api_program.get('about_lead', '') + ' ' + api_program.get('about_desc', '')
            
            # Создание объекта программы
            program = ProgramInfo(
                id=program_id,
                name=name,
                url=url,
                slug=slug,
                description=description.strip(),
                duration=api_program.get('study_period'),
                format=api_program.get('study_mode'),
                language=api_program.get('language'),
                cost_russian=api_program.get('education_cost_russian'),
                cost_foreign=api_program.get('education_cost_foreigner'),
                career_prospects=api_program.get('career_info', ''),
                pdf_url=pdf_url
            )
            
            logger.info(f"Извлечены данные программы: {name} (ID: {program_id})")
            return program
            
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Ошибка парсинга JSON данных: {e}")
            return None
    
    def download_pdf(self, program: ProgramInfo) -> bool:
        """Скачивает PDF файл учебного плана."""
        if not program.pdf_url:
            logger.warning(f"Нет URL для PDF программы {program.name}")
            return False
        
        try:
            logger.info(f"Скачиваю PDF для программы: {program.name}")
            logger.info(f"URL: {program.pdf_url}")
            
            response = self.session.get(program.pdf_url, timeout=30)
            response.raise_for_status()
            
            # Создание имени файла
            safe_name = re.sub(r'[^\w\s-]', '', program.name).strip()
            safe_name = re.sub(r'[-\s]+', '-', safe_name)
            filename = f"{safe_name}_учебный_план.pdf"
            filepath = self.output_dir / filename
            
            # Сохранение файла
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            program.pdf_path = str(filepath)
            logger.success(f"PDF сохранен: {filepath}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Ошибка скачивания PDF для {program.name}: {e}")
            return False
    
    def parse_pdf_content(self, program: ProgramInfo) -> bool:
        """Парсит содержимое PDF файла и добавляет данные в программу."""
        if not program.pdf_path or not Path(program.pdf_path).exists():
            logger.warning(f"PDF файл не найден для программы {program.name}")
            return False
        
        try:
            logger.info(f"Парсинг PDF файла для программы: {program.name}")
            
            # Парсим PDF
            pdf_data = self.pdf_parser.parse_pdf(program.pdf_path)
            
            if pdf_data['parsing_success']:
                # Добавляем данные из PDF в программу
                program.program_name_from_pdf = pdf_data['program_name_from_pdf']
                program.subjects = pdf_data['subjects']
                
                logger.success(f"PDF успешно обработан. Найдено предметов: {len(program.subjects)}")
                return True
            else:
                logger.warning(f"Не удалось извлечь данные из PDF для программы {program.name}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка парсинга PDF для программы {program.name}: {e}")
            return False
    
    def parse_program(self, url: str) -> Optional[ProgramInfo]:
        """Парсит одну программу по URL."""
        try:
            # Получение содержимого страницы
            html_content = self.get_page_content(url)
            
            # Извлечение данных программы
            program = self.extract_program_data(html_content, url)
            if not program:
                return None
            
            # Скачивание PDF
            pdf_downloaded = self.download_pdf(program)
            
            # Парсинг PDF, если он был скачан
            if pdf_downloaded:
                self.parse_pdf_content(program)
            
            return program
            
        except Exception as e:
            logger.error(f"Ошибка парсинга программы {url}: {e}")
            return None
    
    def parse_all_programs(self) -> List[ProgramInfo]:
        """Парсит все программы магистратуры."""
        urls = [
            "https://abit.itmo.ru/program/master/ai",
            "https://abit.itmo.ru/program/master/ai_product"
        ]
        
        programs = []
        for url in urls:
            logger.info(f"Обрабатываю программу: {url}")
            program = self.parse_program(url)
            if program:
                programs.append(program)
            
            # Задержка между запросами
            time.sleep(1)
        
        return programs
    
    def save_programs_data(self, programs: List[ProgramInfo], filename: str = "programs.json"):
        """Сохраняет данные программ в JSON файл."""
        filepath = self.output_dir / filename
        
        programs_data = []
        for program in programs:
            programs_data.append(asdict(program))
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(programs_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Данные программ сохранены в: {filepath}")


def main():
    """Основная функция для запуска парсера."""
    logger.info("Запуск парсера программ ИТМО")
    
    parser = ITMOParser()
    programs = parser.parse_all_programs()
    
    if programs:
        parser.save_programs_data(programs)
        logger.success(f"Обработано программ: {len(programs)}")
        
        for program in programs:
            logger.info(f"Программа: {program.name}")
            logger.info(f"Название из PDF: {program.program_name_from_pdf}")
            logger.info(f"Количество предметов: {len(program.subjects)}")
            logger.info(f"PDF: {program.pdf_path}")
    else:
        logger.error("Не удалось обработать ни одной программы")


if __name__ == "__main__":
    main() 