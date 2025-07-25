"""Модели базы данных и CRUD операции."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import (
    create_engine, 
    Column, 
    Integer, 
    String, 
    Text, 
    DateTime, 
    Boolean, 
    JSON,
    Float,
    ForeignKey
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from loguru import logger

from .config import settings

Base = declarative_base()


class User(Base):
    """Модель пользователя Telegram."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Пользовательские предпочтения
    preferences = Column(JSON, default=dict)
    
    # Связи
    conversations = relationship("Conversation", back_populates="user")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"


class Conversation(Base):
    """Модель диалога с пользователем."""
    
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Контекст диалога
    context = Column(JSON, default=dict)
    
    # Связи
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation")
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, user_id={self.user_id})>"


class Message(Base):
    """Модель сообщения в диалоге."""
    
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    telegram_message_id = Column(Integer, nullable=True)
    
    role = Column(String(20), nullable=False)  # 'user' или 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Метаданные сообщения
    message_metadata = Column(JSON, default=dict)
    
    # Связи
    conversation = relationship("Conversation", back_populates="messages")
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"


class Program(Base):
    """Модель магистерской программы."""
    
    __tablename__ = "programs"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(Integer, unique=True, nullable=False)  # ID с сайта ИТМО
    name = Column(String(500), nullable=False)
    slug = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False)
    
    # Основная информация
    description = Column(Text, nullable=True)
    duration = Column(String(100), nullable=True)
    format = Column(String(100), nullable=True)
    language = Column(String(100), nullable=True)
    
    # Стоимость
    cost_russian = Column(Integer, nullable=True)
    cost_foreign = Column(Integer, nullable=True)
    
    # Карьерные перспективы
    career_prospects = Column(Text, nullable=True)
    
    # PDF данные
    pdf_url = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    program_name_from_pdf = Column(String(500), nullable=True)
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    subjects = relationship("Subject", back_populates="program")
    
    def __repr__(self):
        return f"<Program(id={self.id}, name={self.name})>"


class Subject(Base):
    """Модель учебной дисциплины."""
    
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    program_id = Column(Integer, ForeignKey("programs.id"), nullable=False)
    
    name = Column(String(500), nullable=False)
    semester = Column(String(20), nullable=False)
    credits = Column(Float, nullable=True)
    hours = Column(Integer, nullable=True)
    subject_type = Column(String(100), default="дисциплина")
    
    # Связи
    program = relationship("Program", back_populates="subjects")
    
    def __repr__(self):
        return f"<Subject(id={self.id}, name={self.name})>"


class DatabaseManager:
    """Менеджер для работы с базой данных."""
    
    def __init__(self, database_url: str = None):
        """
        Инициализация менеджера БД.
        
        Args:
            database_url: URL подключения к БД
        """
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"Подключение к БД: {self.database_url}")
    
    def create_tables(self):
        """Создает все таблицы в БД."""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.success("Таблицы БД созданы успешно")
        except Exception as e:
            logger.error(f"Ошибка создания таблиц: {e}")
            raise
    
    def get_session(self) -> Session:
        """Возвращает сессию БД."""
        return self.SessionLocal()
    
    # CRUD операции для пользователей
    def create_user(self, telegram_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> User:
        """Создает нового пользователя."""
        with self.get_session() as session:
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Создан пользователь: {telegram_id}")
            return user
    
    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по Telegram ID."""
        with self.get_session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()
    
    def update_user_activity(self, telegram_id: int) -> None:
        """Обновляет время последней активности пользователя."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if user:
                user.last_active = datetime.utcnow()
                session.commit()
    
    # CRUD операции для диалогов
    def create_conversation(self, user_id: int) -> Conversation:
        """Создает новый диалог."""
        with self.get_session() as session:
            conversation = Conversation(user_id=user_id)
            session.add(conversation)
            session.commit()
            session.refresh(conversation)
            return conversation
    
    def get_active_conversation(self, user_id: int) -> Optional[Conversation]:
        """Получает активный диалог пользователя."""
        with self.get_session() as session:
            return session.query(Conversation).filter(
                Conversation.user_id == user_id,
                Conversation.is_active == True
            ).order_by(Conversation.started_at.desc()).first()
    
    def end_conversation(self, conversation_id: int) -> None:
        """Завершает диалог."""
        with self.get_session() as session:
            conversation = session.query(Conversation).filter(
                Conversation.id == conversation_id
            ).first()
            if conversation:
                conversation.is_active = False
                conversation.ended_at = datetime.utcnow()
                session.commit()
    
    # CRUD операции для сообщений
    def add_message(self, conversation_id: int, role: str, content: str,
                   telegram_message_id: int = None, message_metadata: Dict = None) -> Message:
        """Добавляет сообщение в диалог."""
        with self.get_session() as session:
            message = Message(
                conversation_id=conversation_id,
                role=role,
                content=content,
                telegram_message_id=telegram_message_id,
                message_metadata=message_metadata or {}
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
    
    def get_conversation_messages(self, conversation_id: int, limit: int = 50) -> List[Message]:
        """Получает сообщения диалога."""
        with self.get_session() as session:
            return session.query(Message).filter(
                Message.conversation_id == conversation_id
            ).order_by(Message.timestamp.desc()).limit(limit).all()
    
    # CRUD операции для программ
    def create_or_update_program(self, program_data: Dict[str, Any]) -> Program:
        """Создает или обновляет программу."""
        with self.get_session() as session:
            # Пытаемся найти существующую программу
            program = session.query(Program).filter(
                Program.external_id == program_data.get("id")
            ).first()
            
            if program:
                # Обновляем существующую
                for key, value in program_data.items():
                    if key != "subjects" and hasattr(program, key):
                        setattr(program, key, value)
                program.updated_at = datetime.utcnow()
            else:
                # Создаем новую
                program = Program(
                    external_id=program_data.get("id"),
                    name=program_data.get("name"),
                    slug=program_data.get("slug"),
                    url=program_data.get("url"),
                    description=program_data.get("description"),
                    duration=program_data.get("duration"),
                    format=program_data.get("format"),
                    language=program_data.get("language"),
                    cost_russian=program_data.get("cost_russian"),
                    cost_foreign=program_data.get("cost_foreign"),
                    career_prospects=program_data.get("career_prospects"),
                    pdf_url=program_data.get("pdf_url"),
                    pdf_path=program_data.get("pdf_path"),
                    program_name_from_pdf=program_data.get("program_name_from_pdf")
                )
                session.add(program)
            
            session.commit()
            session.refresh(program)
            
            # Обновляем предметы
            if program_data.get("subjects"):
                self._update_program_subjects(session, program.id, program_data["subjects"])
            
            return program
    
    def _update_program_subjects(self, session: Session, program_id: int, subjects_data: List[Dict]):
        """Обновляет предметы программы."""
        # Удаляем старые предметы
        session.query(Subject).filter(Subject.program_id == program_id).delete()
        
        # Добавляем новые
        for subject_data in subjects_data:
            subject = Subject(
                program_id=program_id,
                name=subject_data.get("name"),
                semester=subject_data.get("semester"),
                credits=subject_data.get("credits"),
                hours=subject_data.get("hours"),
                subject_type=subject_data.get("type", "дисциплина")
            )
            session.add(subject)
        
        session.commit()
    
    def get_all_programs(self) -> List[Program]:
        """Получает все программы."""
        with self.get_session() as session:
            return session.query(Program).all()
    
    def get_program_by_id(self, program_id: int) -> Optional[Program]:
        """Получает программу по ID."""
        with self.get_session() as session:
            return session.query(Program).filter(Program.id == program_id).first()
    
    def search_programs(self, query: str) -> List[Program]:
        """Поиск программ по названию."""
        with self.get_session() as session:
            return session.query(Program).filter(
                Program.name.ilike(f"%{query}%")
            ).all()


# Глобальный экземпляр менеджера БД
db_manager = DatabaseManager() 