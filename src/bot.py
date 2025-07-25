"""Telegram bot для помощи абитуриентам в выборе магистерских программ ИТМО."""

import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

from telegram import (
    Update, 
    ReplyKeyboardMarkup, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode
from loguru import logger

from .config import settings
from .database import db_manager, User, Conversation
from .rag import rag_system
from .utils import format_program_info, format_subjects_list


class ITMOBot:
    """Telegram бот для помощи абитуриентам."""
    
    def __init__(self):
        """Инициализация бота."""
        self.application = None
        self.user_states: Dict[int, Dict[str, Any]] = {}
        
        self._init_bot()
    
    def _init_bot(self):
        """Инициализирует бота."""
        try:
            logger.info("Инициализация Telegram бота...")
            
            # Создаем приложение
            self.application = Application.builder().token(settings.telegram_bot_token).build()
            
            # Регистрируем обработчики
            self._register_handlers()
            
            logger.success("Telegram бот инициализирован успешно")
            
        except Exception as e:
            logger.error(f"Ошибка инициализации бота: {e}")
            raise
    
    def _register_handlers(self):
        """Регистрирует обработчики команд и сообщений."""
        # Команды
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("programs", self.programs_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        
        # Callback кнопки
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Текстовые сообщения
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        logger.info("Обработчики зарегистрированы")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /start."""
        try:
            user_id = update.effective_user.id
            username = update.effective_user.username
            first_name = update.effective_user.first_name
            last_name = update.effective_user.last_name
            
            # Создаем или получаем пользователя
            db_user = db_manager.get_user_by_telegram_id(user_id)
            if not db_user:
                db_user = db_manager.create_user(
                    telegram_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                logger.info(f"Создан новый пользователь: {user_id}")
            else:
                db_manager.update_user_activity(user_id)
            
            # Создаем новый диалог
            conversation = db_manager.create_conversation(db_user.id)
            self.user_states[user_id] = {
                'conversation_id': conversation.id,
                'step': 'greeting'
            }
            
            # Приветственное сообщение
            welcome_text = f"""
🎓 Привет, {first_name}! Я помощник для поступающих в магистратуру ИТМО.

Я помогу тебе:
📚 Узнать о программах "Искусственный интеллект" и "Управление ИИ-продуктами"
🎯 Выбрать подходящую программу
📋 Узнать о предметах и учебном плане
💰 Узнать стоимость обучения
🚀 Понять карьерные перспективы

Задавай любые вопросы или используй команды:
/programs - посмотреть доступные программы
/help - получить помощь
            """
            
            keyboard = [
                ["📚 Показать программы", "❓ Помощь"],
                ["🤖 Искусственный интеллект", "📱 Управление ИИ-продуктами"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            
            await update.message.reply_text(
                welcome_text.strip(),
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Сохраняем сообщение в БД
            db_manager.add_message(
                conversation_id=conversation.id,
                role='assistant',
                content=welcome_text.strip(),
                telegram_message_id=update.message.message_id
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде /start: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуйте позже.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /help."""
        help_text = """
🆘 **Помощь по использованию бота**

**Доступные команды:**
/start - начать диалог заново
/programs - показать доступные программы  
/help - эта справка
/reset - сбросить диалог

**Что я умею:**
• Отвечать на вопросы о программах магистратуры ИТМО
• Сравнивать программы между собой
• Показывать учебные планы и предметы
• Помогать с выбором программы
• Рассказывать о стоимости и условиях поступления

**Примеры вопросов:**
"Какая разница между программами ИИ и AI Product?"
"Сколько стоит обучение для граждан РФ?"
"Какие предметы изучают на программе ИИ?"
"Какие карьерные перспективы?"

Просто задавай вопросы естественным языком! 🚀
        """
        
        await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)
    
    async def programs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /programs."""
        try:
            programs = db_manager.get_all_programs()
            
            if not programs:
                await update.message.reply_text("Программы не найдены. Запустите парсинг данных.")
                return
            
            # Создаем inline клавиатуру с программами
            keyboard = []
            for program in programs:
                button_text = f"📚 {program.name}"
                callback_data = f"program_{program.id}"
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            keyboard.append([InlineKeyboardButton("🔄 Сравнить программы", callback_data="compare_programs")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📋 **Доступные программы магистратуры:**\n\nВыберите программу для подробной информации:",
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка в команде /programs: {e}")
            await update.message.reply_text("Ошибка загрузки программ.")
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик команды /reset."""
        user_id = update.effective_user.id
        
        # Завершаем текущий диалог
        if user_id in self.user_states:
            conversation_id = self.user_states[user_id].get('conversation_id')
            if conversation_id:
                db_manager.end_conversation(conversation_id)
        
        # Удаляем состояние пользователя
        self.user_states.pop(user_id, None)
        
        await update.message.reply_text("Диалог сброшен. Используйте /start для начала.")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик нажатий на inline кнопки."""
        try:
            query = update.callback_query
            await query.answer()
            
            callback_data = query.data
            
            if callback_data.startswith("program_"):
                # Показать информацию о программе
                program_id = int(callback_data.split("_")[1])
                await self._show_program_details(query, program_id)
                
            elif callback_data == "compare_programs":
                # Начать сравнение программ
                await self._start_program_comparison(query)
                
            elif callback_data.startswith("subjects_"):
                # Показать предметы программы
                program_id = int(callback_data.split("_")[1])
                await self._show_program_subjects(query, program_id)
                
            elif callback_data.startswith("compare_"):
                # Добавить программу к сравнению
                program_id = int(callback_data.split("_")[1])
                await self._add_to_comparison(query, program_id)
        
        except Exception as e:
            logger.error(f"Ошибка обработки callback: {e}")
            await query.edit_message_text("Произошла ошибка.")
    
    async def _show_program_details(self, query, program_id: int) -> None:
        """Показывает детальную информацию о программе."""
        try:
            program = db_manager.get_program_by_id(program_id)
            if not program:
                await query.edit_message_text("Программа не найдена.")
                return
            
            # Конвертируем SQLAlchemy объект в словарь
            program_data = {
                'name': program.name,
                'description': program.description,
                'duration': program.duration,
                'format': program.format,
                'language': program.language,
                'cost_russian': program.cost_russian,
                'cost_foreign': program.cost_foreign,
                'career_prospects': program.career_prospects,
                'subjects': [
                    {
                        'name': s.name,
                        'semester': s.semester,
                        'credits': s.credits,
                        'hours': s.hours,
                        'type': s.subject_type
                    } for s in program.subjects
                ]
            }
            
            # Форматируем информацию
            info_text = format_program_info(program_data)
            
            # Создаем клавиатуру с действиями
            keyboard = [
                [InlineKeyboardButton("📚 Показать предметы", callback_data=f"subjects_{program_id}")],
                [InlineKeyboardButton("🤔 Задать вопрос о программе", callback_data=f"ask_{program_id}")],
                [InlineKeyboardButton("🔙 Назад к списку", callback_data="back_to_programs")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                info_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа программы {program_id}: {e}")
            await query.edit_message_text("Ошибка загрузки программы.")
    
    async def _show_program_subjects(self, query, program_id: int) -> None:
        """Показывает предметы программы."""
        try:
            program = db_manager.get_program_by_id(program_id)
            if not program or not program.subjects:
                await query.edit_message_text("Предметы не найдены.")
                return
            
            subjects_data = [
                {
                    'name': s.name,
                    'semester': s.semester,
                    'credits': s.credits,
                    'hours': s.hours,
                    'type': s.subject_type
                } for s in program.subjects
            ]
            
            subjects_text = f"📚 **Предметы программы {program.name}**\n\n"
            subjects_text += format_subjects_list(subjects_data, limit=15)
            
            keyboard = [[InlineKeyboardButton("🔙 Назад к программе", callback_data=f"program_{program_id}")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                subjects_text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Ошибка показа предметов программы {program_id}: {e}")
            await query.edit_message_text("Ошибка загрузки предметов.")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Обработчик текстовых сообщений."""
        try:
            user_id = update.effective_user.id
            message_text = update.message.text
            
            # Обновляем активность пользователя
            db_manager.update_user_activity(user_id)
            
            # Получаем или создаем состояние пользователя
            if user_id not in self.user_states:
                # Создаем новый диалог если его нет
                db_user = db_manager.get_user_by_telegram_id(user_id)
                if db_user:
                    conversation = db_manager.create_conversation(db_user.id)
                    self.user_states[user_id] = {
                        'conversation_id': conversation.id,
                        'step': 'conversation'
                    }
                else:
                    await update.message.reply_text("Пожалуйста, начните с команды /start")
                    return
            
            conversation_id = self.user_states[user_id]['conversation_id']
            
            # Сохраняем сообщение пользователя
            db_manager.add_message(
                conversation_id=conversation_id,
                role='user',
                content=message_text,
                telegram_message_id=update.message.message_id
            )
            
            # Обрабатываем кнопки клавиатуры
            if message_text in ["📚 Показать программы", "📋 Программы"]:
                await self.programs_command(update, context)
                return
            elif message_text in ["❓ Помощь", "🆘 Помощь"]:
                await self.help_command(update, context)
                return
            elif message_text == "🤖 Искусственный интеллект":
                await self._handle_program_question("Искусственный интеллект", update, conversation_id)
                return
            elif message_text == "📱 Управление ИИ-продуктами":
                await self._handle_program_question("Управление ИИ-продуктами", update, conversation_id)
                return
            
            # Обрабатываем обычный вопрос через RAG
            await self._handle_rag_question(message_text, update, conversation_id)
            
        except Exception as e:
            logger.error(f"Ошибка обработки сообщения: {e}")
            await update.message.reply_text("Произошла ошибка. Попробуйте переформулировать вопрос.")
    
    async def _handle_program_question(self, program_name: str, update: Update, conversation_id: int) -> None:
        """Обрабатывает вопрос о конкретной программе."""
        try:
            # Формируем вопрос для RAG
            question = f"Расскажи подробно о программе {program_name}"
            
            await self._handle_rag_question(question, update, conversation_id)
            
        except Exception as e:
            logger.error(f"Ошибка обработки вопроса о программе {program_name}: {e}")
            await update.message.reply_text("Ошибка получения информации о программе.")
    
    async def _handle_rag_question(self, question: str, update: Update, conversation_id: int) -> None:
        """Обрабатывает вопрос через RAG систему."""
        try:
            # Показываем индикатор печати
            await update.message.chat.send_action("typing")
            
            # Получаем ответ от RAG системы
            answer, sources = rag_system.ask(question)
            
            # Ограничиваем длину ответа для Telegram
            if len(answer) > 4000:
                answer = answer[:4000] + "..."
            
            # Отправляем ответ
            await update.message.reply_text(answer, parse_mode=ParseMode.MARKDOWN)
            
            # Сохраняем ответ в БД
            db_manager.add_message(
                conversation_id=conversation_id,
                role='assistant',
                content=answer,
                message_metadata={'sources': len(sources)}
            )
            
        except Exception as e:
            logger.error(f"Ошибка RAG обработки: {e}")
            await update.message.reply_text(
                "Извините, не смог обработать ваш вопрос. Попробуйте переформулировать или используйте /help для получения подсказок."
            )
    
    async def run(self) -> None:
        """Запускает бота."""
        try:
            logger.info("Запуск Telegram бота...")
            
            # Устанавливаем команды бота
            commands = [
                BotCommand("start", "Начать диалог"),
                BotCommand("programs", "Показать программы"),
                BotCommand("help", "Получить помощь"),
                BotCommand("reset", "Сбросить диалог")
            ]
            
            await self.application.bot.set_my_commands(commands)
            
            # Запускаем бота
            await self.application.run_polling(drop_pending_updates=True)
            
        except Exception as e:
            logger.error(f"Ошибка запуска бота: {e}")
            raise
    
    def stop(self) -> None:
        """Останавливает бота."""
        if self.application:
            self.application.stop()
            logger.info("Бот остановлен")


# Функция для запуска бота
async def main():
    """Главная функция для запуска бота."""
    from .utils import setup_logging
    
    # Настройка логирования
    setup_logging("bot.log")
    settings.ensure_directories()
    
    # Создание таблиц БД
    db_manager.create_tables()
    
    # Индексация программ в RAG
    logger.info("Проверка индексации программ...")
    rag_system.index_programs()
    
    # Создание и запуск бота
    bot = ITMOBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main()) 