"""
AI-агент на базе OpenAI Tools API (без зависимости от LangChain-агентов).
Поддерживает: выбор инструментов, долговременную память, историю диалога.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from tools import TOOL_SCHEMAS, TOOL_FUNCTIONS
from logger import log, log_separator

load_dotenv()

MEMORY_FILE = Path(__file__).parent / "memory.json"

SYSTEM_PROMPT = """Ты — умный AI-ассистент с доступом к инструментам. Отвечаешь на русском языке.

Правила выбора инструментов:
- Вопрос о погоде → get_weather
- Вопрос о цене криптовалюты (bitcoin, ethereum и т.д.) → get_crypto_price
- Вопрос о курсе обычных валют (доллар, евро, рубль, AED...) → get_exchange_rate
- Поиск информации, новости, общие вопросы → web_search
- Математические вычисления, формулы → calculate
- Добавить напоминание → add_reminder (дату интерпретируй сам из фразы, текущий год 2026)
- Показать напоминания → get_reminders
- Удалить напоминание → delete_reminder
- Прочитать файл → read_file
- Записать файл → write_file
- Системная команда → run_terminal_command
- HTTP-запрос к API → http_request

Общие правила:
- Всегда используй инструменты для актуальных данных — не выдумывай
- Отвечай структурированно и понятно
- Если запрос неясен — уточни у пользователя
- При добавлении напоминания всегда подтверди дату и время пользователю
"""


def load_memory() -> list:
    log.debug(f"Загрузка памяти из {MEMORY_FILE}")
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                history = data.get("history", [])
                log.debug(f"Память загружена: {len(history)} сообщений")
                return history
        except (json.JSONDecodeError, KeyError) as e:
            log.warning(f"Не удалось прочитать память: {e} — начинаем с чистой")
            return []
    log.debug("Файл памяти не найден — начинаем с чистой истории")
    return []


def save_memory(history: list) -> None:
    data = {
        "last_updated": datetime.now().isoformat(),
        "total_messages": len(history),
        "history": history[-50:],
    }
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    log.debug(f"Память сохранена: {len(history)} сообщений → {MEMORY_FILE.name}")


class AIAgent:
    def __init__(self, model: str = "gpt-5.4-2026-03-05"):
        log_separator("ИНИЦИАЛИЗАЦИЯ АГЕНТА")
        log.info(f"Модель: {model}")

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key == "sk-your-api-key-here":
            log.error("OPENAI_API_KEY не задан в .env файле")
            raise ValueError(
                "OPENAI_API_KEY не найден или не задан.\n"
                "Открой файл agent/.env и вставь свой ключ:\n"
                "OPENAI_API_KEY=sk-..."
            )

        masked_key = api_key[:8] + "..." + api_key[-4:]
        log.debug(f"API ключ найден: {masked_key}")

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.history = load_memory()

        log.info(f"Агент готов. Инструментов: {len(TOOL_SCHEMAS)}. История: {len(self.history)} сообщений.")
        log_separator()

    def _run_tool(self, name: str, args: dict) -> str:
        log.debug(f"Вызов инструмента: {name}  аргументы: {json.dumps(args, ensure_ascii=False)}")
        func = TOOL_FUNCTIONS.get(name)
        if not func:
            log.error(f"Инструмент '{name}' не найден в реестре")
            return f"Инструмент '{name}' не найден."
        t0 = time.perf_counter()
        try:
            result = func(**args)
            elapsed = (time.perf_counter() - t0) * 1000
            preview = result[:200].replace("\n", " ") + ("..." if len(result) > 200 else "")
            log.info(f"🔧 {name}({_fmt_args(args)})  [{elapsed:.0f}ms]  → {preview}")
            log.debug(f"Полный результат [{name}]:\n{result}")
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000
            log.error(f"Инструмент {name} завершился с ошибкой [{elapsed:.0f}ms]: {e}", exc_info=True)
            return f"Ошибка инструмента {name}: {e}"

    def chat(self, user_input: str) -> str:
        log_separator(f"ЗАПРОС")
        log.info(f"👤 Пользователь: {user_input}")
        self.history.append({"role": "user", "content": user_input})

        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self.history[-20:]
        log.debug(f"Передаём в LLM: {len(messages)} сообщений (включая system)")

        total_t0 = time.perf_counter()

        for iteration in range(1, 6):
            log.debug(f"── Итерация {iteration} / 5 ──")
            llm_t0 = time.perf_counter()

            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=TOOL_SCHEMAS,
                    tool_choice="auto",
                )
            except Exception as e:
                log.error(f"Ошибка запроса к OpenAI API: {e}", exc_info=True)
                answer = f"Ошибка обращения к OpenAI: {e}"
                self._finalize(answer)
                return answer

            llm_elapsed = (time.perf_counter() - llm_t0) * 1000
            msg = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            usage = response.usage

            log.debug(
                f"LLM ответ [{llm_elapsed:.0f}ms] | finish_reason={finish_reason} | "
                f"tokens: prompt={usage.prompt_tokens}, completion={usage.completion_tokens}, total={usage.total_tokens}"
            )

            if msg.tool_calls:
                log.debug(f"LLM запросил {len(msg.tool_calls)} инструмент(ов)")
                messages.append(msg)
                for i, tc in enumerate(msg.tool_calls, 1):
                    log.debug(f"  Инструмент {i}/{len(msg.tool_calls)}: {tc.function.name}  raw_args={tc.function.arguments}")
                    try:
                        args = json.loads(tc.function.arguments)
                    except json.JSONDecodeError as e:
                        log.error(f"Не удалось распарсить аргументы инструмента {tc.function.name}: {e}")
                        args = {}

                    result = self._run_tool(tc.function.name, args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    })
            else:
                answer = msg.content or "Нет ответа."
                total_elapsed = (time.perf_counter() - total_t0) * 1000
                log.info(f"🤖 Ответ агента [{total_elapsed:.0f}ms, итераций: {iteration}]:\n{answer}")
                self._finalize(answer)
                return answer

        log.warning("Достигнут лимит в 5 итераций без финального ответа")
        answer = "Достигнут лимит вызовов инструментов."
        self._finalize(answer)
        return answer

    def _finalize(self, answer: str) -> None:
        self.history.append({"role": "assistant", "content": answer})
        save_memory(self.history)
        log_separator()

    def clear_memory(self) -> None:
        log.info("Память очищена пользователем")
        self.history = []
        save_memory(self.history)

    def show_memory(self) -> str:
        log.debug(f"Запрос истории: {len(self.history)} сообщений")
        if not self.history:
            return "История диалога пуста."
        lines = [f"📝 История ({len(self.history)} сообщений, показаны последние 10):"]
        for msg in self.history[-10:]:
            role = "👤" if msg["role"] == "user" else "🤖"
            preview = msg["content"][:100] + "..." if len(msg["content"]) > 100 else msg["content"]
            lines.append(f"{role} {preview}")
        return "\n".join(lines)


def _fmt_args(args: dict) -> str:
    """Краткое форматирование аргументов для лога."""
    parts = []
    for k, v in args.items():
        v_str = str(v)
        if len(v_str) > 40:
            v_str = v_str[:40] + "..."
        parts.append(f"{k}={v_str!r}")
    return ", ".join(parts)
