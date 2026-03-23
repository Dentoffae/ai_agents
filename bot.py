"""
Telegram-бот интерфейс для AI-агента.
Запуск: python bot.py
"""

import os
import threading
from dotenv import load_dotenv
import telebot
from telebot.types import Message, BotCommand

from agent import AIAgent
from logger import log, log_separator

load_dotenv()

# ─── Инициализация бота ───────────────────────
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN не найден.\n"
        "Добавь в agent/.env:\n"
        "TELEGRAM_BOT_TOKEN=ваш_токен_от_BotFather"
    )

bot = telebot.TeleBot(TOKEN, parse_mode="Markdown")

# ─── Пул агентов (по одному на пользователя) ─
_agents: dict[int, AIAgent] = {}
_agent_locks: dict[int, threading.Lock] = {}
_model_choice: dict[int, str] = {}

MODELS = {
    "55":   "gpt-5.4-2026-03-05",
    "mini": "gpt-4o-mini",
    "4o":   "gpt-4o",
}

WELCOME = (
    "👋 *Привет! Я AI-агент на базе OpenAI.*\n\n"
    "Я умею:\n"
    "🌤 Узнавать погоду\n"
    "💰 Показывать курс крипты и валют\n"
    "🌐 Искать информацию в интернете\n"
    "🧮 Считать математику\n"
    "📋 Вести список напоминаний\n"
    "📁 Читать и писать файлы\n"
    "💻 Выполнять команды терминала\n\n"
    "Просто напиши мне что-нибудь!"
)

HELP = (
    "📖 *Команды:*\n\n"
    "/start — приветствие\n"
    "/help — это меню\n"
    "/memory — история диалога\n"
    "/clear — очистить память\n"
    "/model — сменить модель GPT\n"
    "/status — текущие настройки\n\n"
    "*Примеры запросов:*\n"
    "• Какая погода в Токио?\n"
    "• Сколько стоит Bitcoin в рублях?\n"
    "• Курс доллара к евро\n"
    "• Напомни завтра в 10:00 позвонить врачу\n"
    "• Покажи мои напоминания\n"
    "• Сколько будет sqrt\\(144\\) \\+ 5²?\n"
    "• Найди новости про искусственный интеллект"
)


def get_agent(user_id: int) -> AIAgent:
    """Возвращает агента для данного пользователя, создаёт если нет."""
    if user_id not in _agents:
        model = _model_choice.get(user_id, "gpt-5.4-2026-03-05")
        log.info(f"Создание агента для user_id={user_id}, модель={model}")
        _agents[user_id] = AIAgent(model=model)
        _agent_locks[user_id] = threading.Lock()
    return _agents[user_id]


def get_lock(user_id: int) -> threading.Lock:
    if user_id not in _agent_locks:
        _agent_locks[user_id] = threading.Lock()
    return _agent_locks[user_id]


def safe_reply(message: Message, text: str) -> None:
    """Отправляет ответ, разбивая на части если > 4000 символов."""
    MAX = 4000
    if len(text) <= MAX:
        try:
            bot.reply_to(message, text)
        except Exception:
            # Если Markdown сломан — отправляем plain text
            bot.reply_to(message, text, parse_mode=None)
        return
    # Разбиваем длинный текст на части
    parts = [text[i:i + MAX] for i in range(0, len(text), MAX)]
    for i, part in enumerate(parts):
        try:
            if i == 0:
                bot.reply_to(message, part)
            else:
                bot.send_message(message.chat.id, part)
        except Exception:
            try:
                bot.send_message(message.chat.id, part, parse_mode=None)
            except Exception as e:
                log.error(f"Не удалось отправить часть {i+1}: {e}")


# ─── КОМАНДЫ ─────────────────────────────────

@bot.message_handler(commands=["start"])
def cmd_start(message: Message) -> None:
    user = message.from_user
    log.info(f"/start от {user.first_name} (id={user.id})")
    get_agent(user.id)  # Инициализируем агента заранее
    bot.reply_to(message, WELCOME)


@bot.message_handler(commands=["help"])
def cmd_help(message: Message) -> None:
    log.info(f"/help от user_id={message.from_user.id}")
    bot.reply_to(message, HELP)


@bot.message_handler(commands=["memory"])
def cmd_memory(message: Message) -> None:
    user_id = message.from_user.id
    log.info(f"/memory от user_id={user_id}")
    agent = get_agent(user_id)
    result = agent.show_memory()
    bot.reply_to(message, result, parse_mode=None)


@bot.message_handler(commands=["clear"])
def cmd_clear(message: Message) -> None:
    user_id = message.from_user.id
    log.info(f"/clear от user_id={user_id}")
    agent = get_agent(user_id)
    agent.clear_memory()
    bot.reply_to(message, "🗑 Память очищена.")


@bot.message_handler(commands=["status"])
def cmd_status(message: Message) -> None:
    user_id = message.from_user.id
    agent = get_agent(user_id)
    model = agent.model
    history_len = len(agent.history)
    text = (
        f"⚙️ *Текущие настройки:*\n\n"
        f"🤖 Модель: `{model}`\n"
        f"💬 Сообщений в памяти: `{history_len}`\n"
        f"🆔 Ваш ID: `{user_id}`"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=["model"])
def cmd_model(message: Message) -> None:
    user_id = message.from_user.id
    log.info(f"/model от user_id={user_id}")
    keyboard = telebot.types.InlineKeyboardMarkup()
    keyboard.row(
        telebot.types.InlineKeyboardButton("gpt-5.4-2026-03-05 (последняя)", callback_data="model_55"),
    )
    keyboard.row(
        telebot.types.InlineKeyboardButton("gpt-4o-mini (быстрая)", callback_data="model_mini"),
        telebot.types.InlineKeyboardButton("gpt-4o (умная)", callback_data="model_4o"),
    )
    bot.reply_to(message, "Выбери модель:", reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith("model_"))
def callback_model(call: telebot.types.CallbackQuery) -> None:
    user_id = call.from_user.id
    key = call.data.replace("model_", "")
    model = MODELS.get(key, "gpt-4o-mini")
    _model_choice[user_id] = model

    # Пересоздаём агента с новой моделью, сохраняя историю
    old_history = []
    if user_id in _agents:
        old_history = _agents[user_id].history
    _agents.pop(user_id, None)

    new_agent = get_agent(user_id)
    new_agent.history = old_history

    log.info(f"Смена модели user_id={user_id}: {model}")
    bot.answer_callback_query(call.id, f"Модель изменена: {model}")
    bot.edit_message_text(
        f"✅ Модель изменена на `{model}`",
        call.message.chat.id,
        call.message.message_id,
    )


# ─── ОСНОВНОЙ ОБРАБОТЧИК СООБЩЕНИЙ ───────────

@bot.message_handler(func=lambda m: True, content_types=["text"])
def handle_message(message: Message) -> None:
    user_id = message.from_user.id
    user_name = message.from_user.first_name or str(user_id)
    user_text = message.text.strip()

    log_separator(f"TG | {user_name} ({user_id})")
    log.info(f"Сообщение от {user_name}: {user_text}")

    lock = get_lock(user_id)

    # Проверяем, не занят ли агент этим пользователем
    if not lock.acquire(blocking=False):
        log.warning(f"Агент занят для user_id={user_id}")
        bot.reply_to(message, "⏳ Подожди, обрабатываю предыдущий запрос...")
        return

    # Показываем статус "печатает..."
    bot.send_chat_action(message.chat.id, "typing")

    def process():
        try:
            agent = get_agent(user_id)
            response = agent.chat(user_text)

            # Экранируем спецсимволы Markdown если нужно
            try:
                safe_reply(message, response)
            except Exception as e:
                log.warning(f"Ошибка Markdown, отправляем plain: {e}")
                bot.reply_to(message, response, parse_mode=None)

        except Exception as e:
            log.error(f"Ошибка обработки сообщения от user_id={user_id}: {e}", exc_info=True)
            bot.reply_to(
                message,
                f"❌ Произошла ошибка:\n`{e}`\n\nПопробуй ещё раз или напиши /clear"
            )
        finally:
            lock.release()

    # Запускаем в отдельном потоке чтобы не блокировать бота
    thread = threading.Thread(target=process, daemon=True)
    thread.start()


@bot.message_handler(func=lambda m: True)
def handle_other(message: Message) -> None:
    bot.reply_to(message, "Я понимаю только текстовые сообщения. Напиши мне что-нибудь!")


# ─── ЗАПУСК ───────────────────────────────────

def main():
    log_separator("TELEGRAM BOT СТАРТ")

    # Устанавливаем команды в меню Telegram (повторяем до 3 раз при таймауте)
    commands = [
        BotCommand("start",  "Начать / приветствие"),
        BotCommand("help",   "Список команд и примеры"),
        BotCommand("model",  "Сменить модель GPT"),
        BotCommand("memory", "История диалога"),
        BotCommand("clear",  "Очистить память"),
        BotCommand("status", "Текущие настройки"),
    ]
    for attempt in range(1, 4):
        try:
            bot.set_my_commands(commands)
            log.info("Команды бота зарегистрированы")
            break
        except Exception as e:
            log.warning(f"Попытка {attempt}/3 — не удалось зарегистрировать команды: {e}")
            if attempt < 3:
                import time; time.sleep(3)

    me = bot.get_me()
    log.info(f"Бот запущен: @{me.username} ({me.first_name})")
    print(f"\n✅ Бот @{me.username} запущен. Нажми Ctrl+C для остановки.\n")

    bot.infinity_polling(timeout=30, long_polling_timeout=20)


if __name__ == "__main__":
    main()
