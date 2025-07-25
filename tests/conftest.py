"""Конфигурация pytest и фикстуры для тестирования."""

import pytest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import Settings
from src.database import Base, DatabaseManager, db_manager
from src.rag import RAGSystem
from src.bot import ITMOBot


@pytest.fixture(scope="session")
def event_loop():
    """Создает event loop для всех тестов."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """Создает временную директорию для тестов."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_dir):
    """Настройки для тестирования."""
    return Settings(
        telegram_bot_token="test_token",
        database_url=f"sqlite:///{temp_dir}/test.db",
        anthropic_api_key="test_anthropic_key",
        debug=True,
        log_level="DEBUG",
        vector_db_path=str(temp_dir / "vector_db"),
        data_dir=str(temp_dir / "data"),
        logs_dir=str(temp_dir / "logs"),
    )


@pytest.fixture
def test_db(test_settings):
    """Тестовая база данных."""
    # Создаем тестовую БД
    engine = create_engine(test_settings.database_url)
    Base.metadata.create_all(bind=engine)
    
    # Создаем менеджер БД
    db = DatabaseManager(test_settings.database_url)
    
    yield db
    
    # Очищаем после тестов
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_program_data():
    """Пример данных программы для тестов."""
    return {
        "id": 1,
        "name": "Искусственный интеллект",
        "slug": "ai",
        "url": "https://abit.itmo.ru/program/master/ai",
        "description": "Программа по искусственному интеллекту",
        "duration": "2 года",
        "format": "Очная",
        "language": "Русский",
        "cost_russian": 350000,
        "cost_foreign": 450000,
        "career_prospects": "Работа в IT-компаниях",
        "pdf_url": "https://example.com/ai.pdf",
        "subjects": [
            {
                "name": "Машинное обучение",
                "semester": "1",
                "credits": 4.0,
                "hours": 144,
                "type": "дисциплина"
            },
            {
                "name": "Глубокое обучение",
                "semester": "2",
                "credits": 3.0,
                "hours": 108,
                "type": "дисциплина"
            }
        ]
    }


@pytest.fixture
def mock_rag_system(test_settings):
    """Мок RAG системы для тестов."""
    mock_rag = Mock(spec=RAGSystem)
    
    # Мокаем методы
    mock_rag.ask.return_value = ("Тестовый ответ", [])
    mock_rag.search.return_value = []
    mock_rag.index_programs.return_value = None
    mock_rag.generate_answer.return_value = "Тестовый ответ"
    
    return mock_rag


@pytest.fixture
def mock_telegram_update():
    """Мок Telegram Update для тестов."""
    mock_update = Mock()
    
    # Мокаем пользователя
    mock_update.effective_user.id = 12345
    mock_update.effective_user.username = "testuser"
    mock_update.effective_user.first_name = "Test"
    mock_update.effective_user.last_name = "User"
    
    # Мокаем сообщение
    mock_update.message = Mock()
    mock_update.message.text = "Тестовое сообщение"
    mock_update.message.message_id = 1
    mock_update.message.reply_text = AsyncMock()
    mock_update.message.chat.send_action = AsyncMock()
    
    return mock_update


@pytest.fixture
def mock_telegram_context():
    """Мок Telegram Context для тестов."""
    mock_context = Mock()
    return mock_context


@pytest.fixture
def sample_users_data():
    """Тестовые данные пользователей."""
    return [
        {
            "telegram_id": 12345,
            "username": "user1",
            "first_name": "John",
            "last_name": "Doe"
        },
        {
            "telegram_id": 67890,
            "username": "user2",
            "first_name": "Jane",
            "last_name": "Smith"
        }
    ]


@pytest.fixture
def sample_subjects_data():
    """Тестовые данные предметов."""
    return [
        {
            "name": "Машинное обучение",
            "semester": "1",
            "credits": 4.0,
            "hours": 144,
            "type": "дисциплина"
        },
        {
            "name": "Глубокое обучение",
            "semester": "2",
            "credits": 3.0,
            "hours": 108,
            "type": "дисциплина"
        },
        {
            "name": "Компьютерное зрение",
            "semester": "3",
            "credits": 3.5,
            "hours": 126,
            "type": "дисциплина"
        }
    ]


@pytest.fixture
def mock_sentence_transformer():
    """Мок SentenceTransformer для тестов."""
    mock_transformer = Mock()
    mock_transformer.encode.return_value = [[0.1, 0.2, 0.3] * 100]  # Fake embeddings
    return mock_transformer


@pytest.fixture
def mock_anthropic_llm():
    """Мок Anthropic LLM для тестов."""
    mock_llm = Mock()
    mock_response = Mock()
    mock_response.content = "Это тестовый ответ от LLM"
    mock_llm.invoke.return_value = mock_response
    return mock_llm


@pytest.fixture
def mock_chroma_collection():
    """Мок ChromaDB коллекции для тестов."""
    mock_collection = Mock()
    mock_collection.count.return_value = 0
    mock_collection.add.return_value = None
    mock_collection.query.return_value = {
        'documents': [["Тестовый документ"]],
        'metadatas': [[{'type': 'test', 'program_id': 1}]],
        'distances': [[0.5]]
    }
    return mock_collection


# Функции-помощники для тестов
def create_test_program(db: DatabaseManager, program_data: dict):
    """Создает тестовую программу в БД."""
    return db.create_or_update_program(program_data)


def create_test_user(db: DatabaseManager, user_data: dict):
    """Создает тестового пользователя в БД."""
    return db.create_user(**user_data)


def create_test_conversation(db: DatabaseManager, user_id: int):
    """Создает тестовый диалог в БД."""
    return db.create_conversation(user_id) 