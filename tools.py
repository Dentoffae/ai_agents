"""
Инструменты AI-агента:
- Web Search (DuckDuckGo)
- Weather (Open-Meteo + геокодинг)
- Crypto Price (CoinGecko)
- HTTP API Request
- File System (чтение/запись)
- Terminal Command (безопасное выполнение)
- Exchange Rate (курс обычных валют)
- Reminders (напоминания)
- Calculator (вычисления)
"""

import os
import json
import math
import subprocess
import requests
from pathlib import Path
from datetime import datetime, timedelta
from duckduckgo_search import DDGS

REMINDERS_FILE = Path(__file__).parent / "reminders.json"


# ─────────────────────────────────────────────
# 1. WEB SEARCH
# ─────────────────────────────────────────────
def web_search(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
        if not results:
            return "Поиск не дал результатов."
        output = []
        for i, r in enumerate(results, 1):
            output.append(f"{i}. {r.get('title', '')}\n   {r.get('body', '')}\n   URL: {r.get('href', '')}")
        return "\n\n".join(output)
    except Exception as e:
        return f"Ошибка поиска: {e}"


# ─────────────────────────────────────────────
# 2. WEATHER TOOL
# ─────────────────────────────────────────────
def _geocode_city(city: str) -> tuple:
    url = "https://geocoding-api.open-meteo.com/v1/search"
    resp = requests.get(url, params={"name": city, "count": 1, "language": "ru"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    results = data.get("results")
    if not results:
        raise ValueError(f"Город '{city}' не найден.")
    return results[0]["latitude"], results[0]["longitude"]


def get_weather(city: str) -> str:
    try:
        lat, lon = _geocode_city(city)
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current_weather": True,
            "hourly": "relative_humidity_2m",
            "forecast_days": 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        cw = data["current_weather"]

        wmo_codes = {
            0: "ясно", 1: "преимущественно ясно", 2: "переменная облачность", 3: "пасмурно",
            45: "туман", 48: "изморозь", 51: "лёгкая морось", 53: "умеренная морось",
            55: "густая морось", 61: "небольшой дождь", 63: "умеренный дождь",
            65: "сильный дождь", 71: "небольшой снег", 73: "умеренный снег",
            75: "сильный снег", 80: "ливень", 81: "сильный ливень",
            95: "гроза", 96: "гроза с градом",
        }
        condition = wmo_codes.get(cw["weathercode"], f"код {cw['weathercode']}")

        humidity = ""
        if "hourly" in data and "relative_humidity_2m" in data["hourly"]:
            h_vals = data["hourly"]["relative_humidity_2m"]
            if h_vals:
                humidity = f"\n💧 Влажность: {h_vals[0]}%"

        return (
            f"🌤 Погода в {city}:\n"
            f"🌡 Температура: {cw['temperature']}°C\n"
            f"💨 Ветер: {cw['windspeed']} км/ч\n"
            f"☁ Условия: {condition}{humidity}"
        )
    except ValueError as e:
        return str(e)
    except Exception as e:
        return f"Ошибка получения погоды: {e}"


# ─────────────────────────────────────────────
# 3. CRYPTO PRICE TOOL
# ─────────────────────────────────────────────
COIN_ALIASES = {
    "биткоин": "bitcoin", "btc": "bitcoin",
    "эфир": "ethereum", "эфириум": "ethereum", "eth": "ethereum",
    "солана": "solana", "sol": "solana",
    "dogecoin": "dogecoin", "doge": "dogecoin", "догикоин": "dogecoin",
    "litecoin": "litecoin", "ltc": "litecoin",
    "ripple": "ripple", "xrp": "ripple",
    "cardano": "cardano", "ada": "cardano",
    "bnb": "binancecoin", "бнб": "binancecoin",
}

CURRENCY_ALIASES = {
    "рубли": "rub", "рублях": "rub", "рублей": "rub", "руб": "rub",
    "доллары": "usd", "долларах": "usd", "долларов": "usd",
    "евро": "eur",
}


def get_crypto_price(coin: str, currency: str = "usd") -> str:
    try:
        coin_id = COIN_ALIASES.get(coin.lower(), coin.lower())
        currency_id = CURRENCY_ALIASES.get(currency.lower(), currency.lower())

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": currency_id, "include_24hr_change": True}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if coin_id not in data:
            return f"Монета '{coin}' не найдена. Попробуй: bitcoin, ethereum, solana."

        price = data[coin_id][currency_id]
        change = data[coin_id].get(f"{currency_id}_24h_change")
        symbols = {"usd": "$", "eur": "€", "rub": "₽"}
        sym = symbols.get(currency_id, currency_id.upper())

        change_str = ""
        if change is not None:
            arrow = "📈" if change >= 0 else "📉"
            change_str = f"\n{arrow} За 24ч: {change:+.2f}%"

        formatted = f"{price:,.2f}" if price >= 1 else f"{price:.8f}"
        return f"💰 {coin_id.capitalize()} → {sym}{formatted}{change_str}"
    except Exception as e:
        return f"Ошибка получения курса: {e}"


# ─────────────────────────────────────────────
# 4. HTTP API REQUEST
# ─────────────────────────────────────────────
def http_request(url: str, method: str = "GET", body: str = "") -> str:
    try:
        method = method.upper()
        json_body = json.loads(body) if body.strip() else None
        resp = requests.request(method, url, headers={"Content-Type": "application/json"}, json=json_body, timeout=15)
        ct = resp.headers.get("content-type", "")
        if "application/json" in ct:
            try:
                result = json.dumps(resp.json(), ensure_ascii=False, indent=2)
            except Exception:
                result = resp.text
        else:
            result = resp.text[:2000]
        return f"Статус: {resp.status_code}\n{result}"
    except Exception as e:
        return f"Ошибка HTTP: {e}"


# ─────────────────────────────────────────────
# 5. FILE SYSTEM
# ─────────────────────────────────────────────
def read_file(filepath: str) -> str:
    try:
        filepath = os.path.expanduser(filepath)
        if not os.path.exists(filepath):
            return f"Файл не найден: {filepath}"
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > 5000:
            return content[:5000] + f"\n\n... (показано 5000 из {len(content)} символов)"
        return content
    except Exception as e:
        return f"Ошибка чтения: {e}"


def write_file(filepath: str, content: str) -> str:
    try:
        filepath = os.path.expanduser(filepath)
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Файл записан: {filepath} ({len(content)} символов)"
    except Exception as e:
        return f"Ошибка записи: {e}"


# ─────────────────────────────────────────────
# 6. TERMINAL COMMAND
# ─────────────────────────────────────────────
BLOCKED = ["rm -rf", "del /f /s", "format", "mkfs", "shutdown", "reboot", ":(){:|:&};:"]


def run_terminal_command(command: str) -> str:
    for b in BLOCKED:
        if b in command.lower():
            return f"Команда заблокирована: содержит '{b}'"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30, encoding="utf-8", errors="replace")
        out = result.stdout.strip()
        err = result.stderr.strip()
        response = ""
        if out:
            response += f"Вывод:\n{out}"
        if err:
            response += f"\nОшибка:\n{err}"
        return response or f"Выполнено (код: {result.returncode})"
    except subprocess.TimeoutExpired:
        return "Таймаут 30 секунд."
    except Exception as e:
        return f"Ошибка: {e}"


# ─────────────────────────────────────────────
# 7. EXCHANGE RATE TOOL
# ─────────────────────────────────────────────
CURRENCY_NAMES = {
    "доллар": "USD", "доллары": "USD", "долларов": "USD", "usd": "USD",
    "евро": "EUR", "eur": "EUR",
    "рубль": "RUB", "рубли": "RUB", "рублей": "RUB", "rub": "RUB",
    "фунт": "GBP", "gbp": "GBP",
    "йена": "JPY", "jpy": "JPY",
    "юань": "CNY", "cny": "CNY",
    "дирхам": "AED", "дирхамы": "AED", "aed": "AED",
    "белорусский рубль": "BYN", "byn": "BYN",
    "гривна": "UAH", "uah": "UAH",
    "тенге": "KZT", "kzt": "KZT",
    "лира": "TRY", "try": "TRY",
    "франк": "CHF", "chf": "CHF",
}


def get_exchange_rate(base: str, target: str) -> str:
    try:
        base_code = CURRENCY_NAMES.get(base.lower(), base.upper())
        target_code = CURRENCY_NAMES.get(target.lower(), target.upper())

        url = "https://api.exchangerate.host/latest"
        params = {"base": base_code, "symbols": target_code}
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success", True) and "rates" not in data:
            # Fallback: попробуем другой бесплатный API
            url2 = f"https://open.er-api.com/v6/latest/{base_code}"
            resp2 = requests.get(url2, timeout=10)
            resp2.raise_for_status()
            data2 = resp2.json()
            rate = data2["rates"].get(target_code)
            if rate is None:
                return f"Валюта '{target_code}' не найдена."
            return (
                f"💱 Курс валют:\n"
                f"1 {base_code} = {rate:.4f} {target_code}\n"
                f"Обновлено: {data2.get('time_last_update_utc', 'н/д')}"
            )

        rates = data.get("rates", {})
        rate = rates.get(target_code)
        if rate is None:
            return f"Валюта '{target_code}' не найдена."

        date = data.get("date", "н/д")
        return (
            f"💱 Курс валют:\n"
            f"1 {base_code} = {rate:.4f} {target_code}\n"
            f"Дата: {date}"
        )
    except Exception as e:
        # Финальный fallback
        try:
            base_code = CURRENCY_NAMES.get(base.lower(), base.upper())
            target_code = CURRENCY_NAMES.get(target.lower(), target.upper())
            url = f"https://open.er-api.com/v6/latest/{base_code}"
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            rate = data["rates"].get(target_code)
            if rate:
                return f"💱 1 {base_code} = {rate:.4f} {target_code}"
            return f"Не удалось получить курс {base_code} → {target_code}"
        except Exception as e2:
            return f"Ошибка получения курса валют: {e2}"


# ─────────────────────────────────────────────
# 8. REMINDERS TOOL
# ─────────────────────────────────────────────
def _load_reminders() -> list:
    if REMINDERS_FILE.exists():
        try:
            with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_reminders(reminders: list) -> None:
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)


def add_reminder(text: str, reminder_datetime: str) -> str:
    try:
        reminders = _load_reminders()
        new_id = max((r["id"] for r in reminders), default=0) + 1

        # Парсим дату — принимаем несколько форматов
        dt = None
        for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M", "%d.%m.%Y %H:%M", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(reminder_datetime.strip(), fmt)
                break
            except ValueError:
                continue

        if dt is None:
            return f"Не удалось распознать дату '{reminder_datetime}'. Используй формат YYYY-MM-DD HH:MM"

        reminder = {
            "id": new_id,
            "text": text,
            "datetime": dt.strftime("%Y-%m-%d %H:%M"),
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        }
        reminders.append(reminder)
        _save_reminders(reminders)
        return f"✅ Напоминание #{new_id} добавлено:\n📌 {text}\n🕐 {dt.strftime('%d.%m.%Y в %H:%M')}"
    except Exception as e:
        return f"Ошибка добавления напоминания: {e}"


def get_reminders() -> str:
    try:
        reminders = _load_reminders()
        if not reminders:
            return "📭 Список напоминаний пуст."
        now = datetime.now()
        lines = [f"📋 Напоминания ({len(reminders)} шт.):"]
        for r in sorted(reminders, key=lambda x: x["datetime"]):
            try:
                dt = datetime.strptime(r["datetime"], "%Y-%m-%d %H:%M")
                status = "🔴 просрочено" if dt < now else "🟢 предстоит"
            except Exception:
                status = ""
            lines.append(f"  #{r['id']} [{status}] {r['datetime']} — {r['text']}")
        return "\n".join(lines)
    except Exception as e:
        return f"Ошибка получения напоминаний: {e}"


def delete_reminder(reminder_id: int) -> str:
    try:
        reminders = _load_reminders()
        original_count = len(reminders)
        reminders = [r for r in reminders if r["id"] != int(reminder_id)]
        if len(reminders) == original_count:
            return f"Напоминание #{reminder_id} не найдено."
        _save_reminders(reminders)
        return f"🗑 Напоминание #{reminder_id} удалено."
    except Exception as e:
        return f"Ошибка удаления: {e}"


# ─────────────────────────────────────────────
# 9. CALCULATOR TOOL
# ─────────────────────────────────────────────
_SAFE_MATH = {
    k: v for k, v in math.__dict__.items() if not k.startswith("_")
}
_SAFE_MATH.update({"abs": abs, "round": round, "min": min, "max": max, "pow": pow})


def calculate(expression: str) -> str:
    try:
        # Нормализация: заменяем ^ на ** и русские запятые на точки
        expr = expression.replace("^", "**").replace(",", ".").strip()

        # Запрет опасных конструкций
        forbidden = ["import", "open", "exec", "eval", "os", "sys", "__", "subprocess"]
        for f in forbidden:
            if f in expr.lower():
                return f"Недопустимое выражение: содержит '{f}'"

        result = eval(expr, {"__builtins__": {}}, _SAFE_MATH)

        if isinstance(result, float):
            if result == int(result) and abs(result) < 1e15:
                formatted = str(int(result))
            else:
                formatted = f"{result:.10g}"
        else:
            formatted = str(result)

        return f"🧮 {expression} = {formatted}"
    except ZeroDivisionError:
        return "Ошибка: деление на ноль."
    except Exception as e:
        return f"Ошибка вычисления: {e}"


# ─────────────────────────────────────────────
# РЕЕСТР ИНСТРУМЕНТОВ — функции + схемы OpenAI
# ─────────────────────────────────────────────
TOOL_FUNCTIONS = {
    "web_search": web_search,
    "get_weather": get_weather,
    "get_crypto_price": get_crypto_price,
    "http_request": http_request,
    "read_file": read_file,
    "write_file": write_file,
    "run_terminal_command": run_terminal_command,
    "get_exchange_rate": get_exchange_rate,
    "add_reminder": lambda text, reminder_datetime: add_reminder(text, reminder_datetime),
    "get_reminders": lambda: get_reminders(),
    "delete_reminder": lambda reminder_id: delete_reminder(reminder_id),
    "calculate": calculate,
}

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Поиск информации в интернете через DuckDuckGo. Используй для актуальных новостей и общих вопросов.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Поисковый запрос"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Текущая погода в городе. Используй при вопросах о погоде.",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string", "description": "Название города"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_crypto_price",
            "description": "Текущий курс криптовалюты. Используй при вопросах о цене крипты.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {"type": "string", "description": "Название монеты: bitcoin, ethereum, solana и т.д."},
                    "currency": {"type": "string", "description": "Валюта: usd, eur, rub. По умолчанию usd."},
                },
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "http_request",
            "description": "HTTP-запрос к любому API.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL запроса"},
                    "method": {"type": "string", "description": "GET, POST, PUT, DELETE"},
                    "body": {"type": "string", "description": "JSON-тело для POST/PUT (необязательно)"},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Прочитать содержимое файла.",
            "parameters": {
                "type": "object",
                "properties": {"filepath": {"type": "string", "description": "Путь к файлу"}},
                "required": ["filepath"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Записать текст в файл.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepath": {"type": "string", "description": "Путь к файлу"},
                    "content": {"type": "string", "description": "Содержимое файла"},
                },
                "required": ["filepath", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_terminal_command",
            "description": "Выполнить команду в терминале. Опасные команды заблокированы.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "Команда для выполнения"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_exchange_rate",
            "description": "Актуальный курс обычных валют (USD, EUR, RUB, AED, BYN и др.). Используй при вопросах о курсе валют, стоимости доллара/евро/рубля.",
            "parameters": {
                "type": "object",
                "properties": {
                    "base": {"type": "string", "description": "Базовая валюта: USD, EUR, RUB и т.д."},
                    "target": {"type": "string", "description": "Целевая валюта: RUB, USD, AED, BYN и т.д."},
                },
                "required": ["base", "target"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_reminder",
            "description": "Добавить напоминание. Используй при запросах типа 'напомни мне', 'поставь напоминание'. Дату интерпретируй из естественного языка и передавай в формате YYYY-MM-DD HH:MM.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Текст напоминания"},
                    "reminder_datetime": {"type": "string", "description": "Дата и время в формате YYYY-MM-DD HH:MM"},
                },
                "required": ["text", "reminder_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reminders",
            "description": "Показать все напоминания. Используй при запросах 'покажи напоминания', 'что запланировано'.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delete_reminder",
            "description": "Удалить напоминание по ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reminder_id": {"type": "integer", "description": "ID напоминания для удаления"},
                },
                "required": ["reminder_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Калькулятор для математических вычислений. Поддерживает: +,-,*,/,**, скобки, sin, cos, sqrt, log, pi, e и другие функции из math. Используй при любых вычислительных запросах.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {"type": "string", "description": "Математическое выражение, например: (25*4)+10**2 или sqrt(144)+log(100)"},
                },
                "required": ["expression"],
            },
        },
    },
]
