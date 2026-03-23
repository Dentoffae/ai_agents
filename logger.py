"""
Централизованный логгер для AI-агента.
Пишет одновременно в консоль (цветной вывод) и в файл agent.log.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_FILE = Path(__file__).parent / "agent.log"

# ─── ANSI цвета для консоли ───────────────────
COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
    "RESET":    "\033[0m",
    "BOLD":     "\033[1m",
    "DIM":      "\033[2m",
    "TOOL":     "\033[34m",   # blue
    "LLM":      "\033[95m",   # light magenta
}


class ColorFormatter(logging.Formatter):
    """Форматтер с цветами для консольного вывода."""

    FMT = "{color}{bold}[{level}]{reset} {dim}{time}{reset}  {msg}"

    def format(self, record: logging.LogRecord) -> str:
        color = COLORS.get(record.levelname, "")
        time_str = datetime.fromtimestamp(record.created).strftime("%H:%M:%S.%f")[:-3]
        bold = COLORS["BOLD"] if record.levelname in ("ERROR", "CRITICAL") else ""
        dim = COLORS["DIM"]
        reset = COLORS["RESET"]

        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)

        return self.FMT.format(
            color=color, bold=bold, level=record.levelname[:4],
            reset=reset, dim=dim, time=time_str, msg=msg,
        )


class PlainFormatter(logging.Formatter):
    """Форматтер без цветов для файлового вывода."""

    def format(self, record: logging.LogRecord) -> str:
        time_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        msg = record.getMessage()
        if record.exc_info:
            msg += "\n" + self.formatException(record.exc_info)
        return f"[{record.levelname:<8}] {time_str}  {msg}"


def setup_logger(name: str = "agent", level: int = logging.DEBUG) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger  # Уже настроен

    logger.setLevel(level)

    # ── Консоль (INFO и выше) ──────────────────
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(ColorFormatter())

    # ── Файл (DEBUG и выше — всё) ──────────────
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(PlainFormatter())

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.propagate = False

    return logger


# Глобальный логгер — импортируй его в других модулях
log = setup_logger("agent")


def log_separator(label: str = "") -> None:
    """Печатает разделитель в лог-файл для читабельности."""
    sep = "─" * 60
    if label:
        log.debug(f"{sep} {label} {sep}")
    else:
        log.debug(sep * 2)
