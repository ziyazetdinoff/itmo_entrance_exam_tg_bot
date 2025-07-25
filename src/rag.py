"""RAG система для ответов на вопросы о программах ИТМО."""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_anthropic import ChatAnthropic
from sentence_transformers import SentenceTransformer
from loguru import logger

from .config import settings
from .database import db_manager, Program
from .utils import extract_keywords


@dataclass
class SearchResult:
    """Результат поиска в векторной БД."""
    content: str
    metadata: Dict[str, Any]
    score: float


class RAGSystem:
    """Система RAG для ответов на вопросы о программах."""
    
    def __init__(self):
        """Инициализация RAG системы."""
        self.embedding_model = None
        self.llm = None
        self.vector_db = None
        self.collection = None
        self.text_splitter = None
        
        self._init_components()
    
    def _init_components(self):
        """Инициализирует компоненты RAG системы."""
        try:
            # Инициализация модели эмбеддингов
            logger.info("Инициализация модели эмбеддингов...")
            self.embedding_model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2')
            
            # Инициализация LLM
            logger.info("Инициализация LLM...")
            self.llm = ChatAnthropic(
                anthropic_api_key=settings.anthropic_api_key,
                model="claude-3-sonnet-20240229",
                temperature=0.3,
                max_tokens=2000
            )
            
            # Инициализация векторной БД
            logger.info("Инициализация векторной БД...")
            self.vector_db = chromadb.PersistentClient(
                path=settings.vector_db_path,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            
            # Создание или получение коллекции
            self.collection = self._get_or_create_collection()
            
            # Инициализация text splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
            
            logger.success("RAG система инициализирована успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации RAG системы: {e}")
            raise
    
    def _get_or_create_collection(self):
        """Создает или получает коллекцию для программ."""
        collection_name = "itmo_programs"
        
        try:
            # Пытаемся получить существующую коллекцию
            collection = self.vector_db.get_collection(collection_name)
            logger.info(f"Используется существующая коллекция: {collection_name}")
        except Exception:
            # Создаем новую коллекцию
            collection = self.vector_db.create_collection(
                name=collection_name,
                metadata={"description": "ITMO Master Programs Information"}
            )
            logger.info(f"Создана новая коллекция: {collection_name}")
        
        return collection
    
    def index_programs(self, force_reindex: bool = False) -> None:
        """
        Индексирует программы в векторную БД.
        
        Args:
            force_reindex: Принудительная переиндексация
        """
        try:
            # Проверяем, есть ли уже данные в коллекции
            if not force_reindex:
                count = self.collection.count()
                if count > 0:
                    logger.info(f"Коллекция уже содержит {count} документов. Пропускаем индексацию.")
                    return
            
            logger.info("Начинаем индексацию программ...")
            
            # Очищаем коллекцию при переиндексации
            if force_reindex:
                self.vector_db.delete_collection(self.collection.name)
                self.collection = self._get_or_create_collection()
            
            # Получаем программы из БД
            programs = db_manager.get_all_programs()
            
            if not programs:
                logger.warning("Нет программ для индексации")
                return
            
            documents = []
            metadatas = []
            ids = []
            
            for program in programs:
                # Создаем документы из разных частей программы
                program_docs = self._create_program_documents(program)
                
                for i, doc in enumerate(program_docs):
                    documents.append(doc['content'])
                    metadatas.append(doc['metadata'])
                    ids.append(f"program_{program.id}_chunk_{i}")
            
            # Создаем эмбеддинги
            logger.info(f"Создание эмбеддингов для {len(documents)} документов...")
            embeddings = self.embedding_model.encode(documents).tolist()
            
            # Добавляем в коллекцию
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
                ids=ids
            )
            
            logger.success(f"Успешно проиндексировано {len(documents)} документов из {len(programs)} программ")
            
        except Exception as e:
            logger.error(f"Ошибка индексации программ: {e}")
            raise
    
    def _create_program_documents(self, program: Program) -> List[Dict[str, Any]]:
        """Создает документы из данных программы."""
        documents = []
        
        # Базовая информация о программе
        base_info = f"""
        Название программы: {program.name}
        Описание: {program.description or 'Нет описания'}
        Длительность: {program.duration or 'Не указана'}
        Формат обучения: {program.format or 'Не указан'}
        Язык обучения: {program.language or 'Не указан'}
        Стоимость для граждан РФ: {program.cost_russian or 'Не указана'} руб.
        Стоимость для иностранцев: {program.cost_foreign or 'Не указана'} руб.
        Карьерные перспективы: {program.career_prospects or 'Не указаны'}
        """
        
        documents.append({
            'content': base_info.strip(),
            'metadata': {
                'type': 'program_info',
                'program_id': program.id,
                'program_name': program.name,
                'source': 'database'
            }
        })
        
        # Разбиваем длинные тексты на чанки
        if program.description and len(program.description) > 500:
            desc_chunks = self.text_splitter.split_text(program.description)
            for chunk in desc_chunks:
                documents.append({
                    'content': f"Описание программы {program.name}: {chunk}",
                    'metadata': {
                        'type': 'description',
                        'program_id': program.id,
                        'program_name': program.name,
                        'source': 'database'
                    }
                })
        
        if program.career_prospects and len(program.career_prospects) > 500:
            career_chunks = self.text_splitter.split_text(program.career_prospects)
            for chunk in career_chunks:
                documents.append({
                    'content': f"Карьерные перспективы программы {program.name}: {chunk}",
                    'metadata': {
                        'type': 'career',
                        'program_id': program.id,
                        'program_name': program.name,
                        'source': 'database'
                    }
                })
        
        # Информация о предметах
        if program.subjects:
            subjects_by_semester = {}
            for subject in program.subjects:
                semester = subject.semester
                if semester not in subjects_by_semester:
                    subjects_by_semester[semester] = []
                subjects_by_semester[semester].append(subject)
            
            for semester, subjects in subjects_by_semester.items():
                subjects_info = f"Предметы {semester} семестра программы {program.name}:\n"
                for subject in subjects:
                    subjects_info += f"- {subject.name} ({subject.credits} з.е., {subject.hours} ч., {subject.subject_type})\n"
                
                documents.append({
                    'content': subjects_info.strip(),
                    'metadata': {
                        'type': 'subjects',
                        'program_id': program.id,
                        'program_name': program.name,
                        'semester': semester,
                        'source': 'database'
                    }
                })
        
        return documents
    
    def search(self, query: str, limit: int = 5) -> List[SearchResult]:
        """
        Поиск релевантных документов.
        
        Args:
            query: Поисковый запрос
            limit: Максимальное количество результатов
            
        Returns:
            Список результатов поиска
        """
        try:
            logger.info(f"Поиск по запросу: {query}")
            
            # Создаем эмбеддинг запроса
            query_embedding = self.embedding_model.encode([query]).tolist()[0]
            
            # Поиск в коллекции
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit,
                include=['documents', 'metadatas', 'distances']
            )
            
            search_results = []
            if results['documents']:
                for i, (doc, metadata, distance) in enumerate(zip(
                    results['documents'][0],
                    results['metadatas'][0],
                    results['distances'][0]
                )):
                    # Преобразуем расстояние в оценку схожести
                    score = 1 / (1 + distance)
                    
                    search_results.append(SearchResult(
                        content=doc,
                        metadata=metadata,
                        score=score
                    ))
            
            logger.info(f"Найдено {len(search_results)} результатов")
            return search_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска: {e}")
            return []
    
    def generate_answer(self, question: str, context: str = None) -> str:
        """
        Генерирует ответ на вопрос с использованием LLM.
        
        Args:
            question: Вопрос пользователя
            context: Контекст для ответа (опционально)
            
        Returns:
            Сгенерированный ответ
        """
        try:
            # Если контекст не предоставлен, ищем релевантную информацию
            if not context:
                search_results = self.search(question, limit=3)
                context = "\n\n".join([result.content for result in search_results])
            
            # Создаем промпт
            prompt = self._create_prompt(question, context)
            
            # Генерируем ответ
            logger.info("Генерация ответа с помощью LLM...")
            response = self.llm.invoke(prompt)
            
            answer = response.content if hasattr(response, 'content') else str(response)
            
            logger.info("Ответ сгенерирован успешно")
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка генерации ответа: {e}")
            return "Извините, произошла ошибка при генерации ответа. Попробуйте переформулировать вопрос."
    
    def _create_prompt(self, question: str, context: str) -> str:
        """Создает промпт для LLM."""
        prompt = f"""Ты — помощник для абитуриентов, который помогает выбрать магистерские программы ИТМО.

КОНТЕКСТ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{question}

ИНСТРУКЦИИ:
1. Отвечай на русском языке
2. Используй только информацию из предоставленного контекста
3. Если в контексте нет нужной информации, честно скажи об этом
4. Будь дружелюбным и полезным
5. Структурируй ответ понятно и логично
6. Используй эмодзи для улучшения восприятия
7. Если речь идет о выборе программы, дай конкретные рекомендации

ОТВЕТ:"""
        
        return prompt
    
    def ask(self, question: str) -> Tuple[str, List[SearchResult]]:
        """
        Отвечает на вопрос пользователя.
        
        Args:
            question: Вопрос пользователя
            
        Returns:
            Кортеж (ответ, список источников)
        """
        try:
            # Поиск релевантной информации
            search_results = self.search(question, limit=5)
            
            if not search_results:
                return "Извините, я не нашел информации по вашему вопросу. Попробуйте переформулировать запрос.", []
            
            # Формируем контекст из найденных результатов
            context = "\n\n".join([
                f"Источник {i+1}:\n{result.content}" 
                for i, result in enumerate(search_results[:3])
            ])
            
            # Генерируем ответ
            answer = self.generate_answer(question, context)
            
            return answer, search_results
            
        except Exception as e:
            logger.error(f"Ошибка обработки вопроса: {e}")
            return "Произошла ошибка при обработке вашего вопроса.", []
    
    def get_program_summary(self, program_id: int) -> Optional[str]:
        """
        Получает краткое резюме программы.
        
        Args:
            program_id: ID программы
            
        Returns:
            Краткое описание программы
        """
        try:
            program = db_manager.get_program_by_id(program_id)
            if not program:
                return None
            
            question = f"Расскажи кратко о программе {program.name}"
            answer, _ = self.ask(question)
            
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка получения резюме программы {program_id}: {e}")
            return None
    
    def compare_programs(self, program_ids: List[int]) -> str:
        """
        Сравнивает несколько программ.
        
        Args:
            program_ids: Список ID программ для сравнения
            
        Returns:
            Сравнительный анализ программ
        """
        try:
            if len(program_ids) < 2:
                return "Для сравнения нужно выбрать как минимум 2 программы."
            
            programs = []
            for pid in program_ids:
                program = db_manager.get_program_by_id(pid)
                if program:
                    programs.append(program)
            
            if len(programs) < 2:
                return "Не удалось найти достаточно программ для сравнения."
            
            # Формируем вопрос для сравнения
            program_names = [p.name for p in programs]
            question = f"Сравни эти программы и помоги выбрать подходящую: {', '.join(program_names)}"
            
            answer, _ = self.ask(question)
            return answer
            
        except Exception as e:
            logger.error(f"Ошибка сравнения программ: {e}")
            return "Произошла ошибка при сравнении программ."


# Глобальный экземпляр RAG системы
rag_system = RAGSystem() 