"""
CLI-интерфейс для запуска AI-агента.
Запуск: python run.py
"""

import sys
import os

# Добавляем директорию агента в путь
sys.path.insert(0, os.path.dirname(__file__))

from agent import AIAgent
from logger import log, LOG_FILE

BANNER = """
╔══════════════════════════════════════════════════════════════╗
║           🤖  LOCAL AI AGENT  (powered by OpenAI)           ║
║                                                              ║
║  Возможности:                                                ║
║  🌐 Поиск в интернете    🌤 Погода    💰 Курс крипто        ║
║  📁 Файлы               🔗 HTTP API  💻 Терминал            ║
╠══════════════════════════════════════════════════════════════╣
║  Команды:                                                    ║
║  /memory  — показать историю диалога                        ║
║  /clear   — очистить память                                  ║
║  /help    — показать это меню                                ║
║  /exit    — выйти                                            ║
╚══════════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Примеры запросов:
  • Какая сейчас погода в Москве?
  • Сколько стоит Bitcoin в рублях?
  • Найди информацию о последних новостях AI
  • Прочитай файл C:/Users/me/notes.txt
  • Запусти команду: dir
  • Сделай GET запрос к https://httpbin.org/get
"""


def print_separator():
    print("─" * 64)


def main():
    print(BANNER)
    print(f"📄 Лог пишется в: {LOG_FILE}\n")
    log.info("=== Сессия начата ===")

    # Выбор модели
    print("Выбери модель (Enter для gpt-5.4-2026-03-05):")
    print("  1. gpt-5.4-2026-03-05 (последняя) [по умолчанию]")
    print("  2. gpt-4o-mini        (быстрая, дешёвая)")
    print("  3. gpt-4o             (умная)")

    choice = input("Выбор [1/2/3]: ").strip()
    model_map = {"1": "gpt-5.4-2026-03-05", "2": "gpt-4o-mini", "3": "gpt-4o"}
    model = model_map.get(choice, "gpt-5.4-2026-03-05")

    print(f"\n⚙ Инициализация агента ({model})...", flush=True)

    try:
        agent = AIAgent(model=model)
        print("✅ Агент готов к работе!\n")
    except ValueError as e:
        log.error(f"Ошибка инициализации: {e}")
        print(f"\n❌ Ошибка: {e}\n")
        sys.exit(1)
    except Exception as e:
        log.error(f"Неожиданная ошибка запуска: {e}", exc_info=True)
        print(f"\n❌ Не удалось запустить агент: {e}\n")
        sys.exit(1)

    print_separator()

    while True:
        try:
            user_input = input("\n👤 Вы: ").strip()
        except (KeyboardInterrupt, EOFError):
            log.info("=== Сессия завершена пользователем ===")
            print("\n\n👋 До свидания!")
            break

        if not user_input:
            continue

        # Обработка команд
        if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
            log.info("=== Сессия завершена командой /exit ===")
            print("👋 До свидания!")
            break

        elif user_input.lower() == "/memory":
            print("\n" + agent.show_memory())
            continue

        elif user_input.lower() == "/clear":
            agent.clear_memory()
            print("🗑 Память очищена.")
            continue

        elif user_input.lower() == "/help":
            print(HELP_TEXT)
            continue

        # Запрос к агенту
        print("\n🤖 Агент думает...", flush=True)
        print_separator()

        try:
            response = agent.chat(user_input)
            print(f"\n🤖 Агент:\n{response}")
        except KeyboardInterrupt:
            log.warning("Запрос прерван пользователем (Ctrl+C)")
            print("\n⚠ Запрос прерван пользователем.")
        except Exception as e:
            log.error(f"Необработанная ошибка в chat(): {e}", exc_info=True)
            print(f"\n❌ Ошибка: {e}")

        print_separator()


if __name__ == "__main__":
    main()
