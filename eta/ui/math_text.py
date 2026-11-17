"""Мини-рендерер математической нотации (сессия 8, Задача 2).

Один источник истины для «формульных» строк интерфейса. Парсер понимает
практическое подмножество LaTeX и ОДНОВРЕМЕННО принимает уже сложившийся
Unicode-стиль базы данных (греческие λ/Σ/∏, «·», «≈», «⁻¹», «²»):

  * макросы: ``\\lambda \\sigma \\Sigma \\prod \\cdot \\times \\approx
    \\le \\ge \\pm`` (и большие греческие прописные); неизвестный макрос
    печатается буквально (``\\foo`` → ``\\foo``);
  * индексы: ``_{...}`` и ``^{...}`` со скобками, одноуровневые ``_DU``,
    ``T_ТО`` (кириллица разрешена), ``^2``, ``^-2``, ``^+5``;
    вложенность индексов не поддерживается – подмножество без неё;
  * Unicode-надстрочники (⁻¹, ²) остаются как есть: это уже готовые
    глифы надстрочными знаками, дополнительно не преобразуются.

Два бэкенда:

  * **A (виджеты)** – ``math(text)`` возвращает HTML с ``<sub>``/``<sup>``
    для QLabel (метки форм), QToolTip и прочего rich text;
  * **B (QPainter)** – ``paint_math()``/``math_size()`` рисуют и меряют
    прогоны с уменьшенным кеглем индексов (~0,65×) и сдвигом базовой
    линии (±~0,35× кегля). Этим же бэкендом считает ширину ``layout.py``
    (геометрия узлов/плашек) и рисует ``render.py``/``pdf_export.py`` –
    экран и PDF остаются строго WYSIWYG.

Хранилище данных не меняется: в БД строки лежат в исходной мини-нотации,
рендеринг – забота исключительно слоя отображения.
"""

from __future__ import annotations

import html as _html
import re
from dataclasses import dataclass

from PySide6.QtCore import QPointF
from PySide6.QtGui import QFont, QFontMetricsF, QPainter, QColor

# кегль индексов и сдвиг базовой линии (доля от кегля базового шрифта)
SCRIPT_SCALE = 0.65
SCRIPT_SHIFT = 0.35

# известные макросы (неизвестные печатаются буквально)
_MACROS: dict[str, str] = {
    "lambda": "λ", "mu": "μ", "sigma": "σ", "Sigma": "Σ", "sum": "Σ",
    "prod": "∏", "pi": "π", "alpha": "α", "beta": "β", "gamma": "γ",
    "delta": "δ", "Delta": "Δ", "eta": "η", "rho": "ρ", "tau": "τ",
    "phi": "φ", "omega": "ω", "Omega": "Ω", "theta": "θ",
    "cdot": "·", "times": "×", "approx": "≈", "le": "≤", "ge": "≥",
    "pm": "±", "ne": "≠", "infty": "∞", "rightarrow": "→", "to": "→",
}

_RE_MACRO = re.compile(r"\\([A-Za-z]+)")
_RE_SCRIPT_WORD = re.compile(r"[+-]?[0-9A-Za-zА-Яа-яЁё]+")


@dataclass(frozen=True)
class MathRun:
    """Прогон текста одного уровня: обычный / нижний / верхний индекс."""

    text: str
    script: str = "base"          # "base" | "sub" | "sup"


def math_runs(text: str) -> list[MathRun]:
    """Разбор мини-нотации в последовательность прогонов.

    Одноуровневая (без вложенных индексов); подряд идущие прогоны одного
    уровня сливаются. Чистый текст без разметки даёт единственный прогон
    base – вызов безопасен для любых строк.
    """
    runs: list[MathRun] = []
    buf = ""
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\\":
            m = _RE_MACRO.match(text, i)
            if m and m.group(1) in _MACROS:
                if buf:
                    runs.append(MathRun(buf))
                    buf = ""
                runs.append(MathRun(_MACROS[m.group(1)]))
                i = m.end()
                continue
            buf += ch                       # неизвестный макрос – буквально
            i += 1
            continue
        if ch in "_^":
            script = "sub" if ch == "_" else "sup"
            j = i + 1
            if j < n and text[j] == "{":
                k = text.find("}", j)
                if k == -1:                 # нет закрывающей – буквально
                    buf += ch
                    i += 1
                    continue
                content = text[j + 1:k]
                i = k + 1
            else:
                m = _RE_SCRIPT_WORD.match(text, j)
                if m is None:               # индекс без содержимого – буквально
                    buf += ch
                    i += 1
                    continue
                content = m.group(0)
                i = m.end()
            if buf:
                runs.append(MathRun(buf))
                buf = ""
            if content:
                runs.append(MathRun(content, script))
            continue
        buf += ch
        i += 1
    if buf:
        runs.append(MathRun(buf))
    # слияние соседних прогонов одного уровня
    merged: list[MathRun] = []
    for r in runs:
        if merged and merged[-1].script == r.script:
            merged[-1] = MathRun(merged[-1].text + r.text, r.script)
        else:
            merged.append(r)
    return merged or [MathRun("")]


# ---------- производные шрифты ----------
def _script_font(font: QFont, script: str) -> QFont:
    """Шрифт индекса: тот же шрифт, кегль ×SCRIPT_SCALE."""
    f = QFont(font)
    px = font.pixelSize()
    if px > 0:
        f.setPixelSize(max(1, round(px * SCRIPT_SCALE)))
    else:
        pt = font.pointSize()
        if pt > 0:
            f.setPointSizeF(max(1.0, pt * SCRIPT_SCALE))
    return f


def _run_font(font: QFont, run: MathRun) -> QFont:
    return _script_font(font, run.script) if run.script != "base" else font


def _run_shift(font: QFont, run: MathRun) -> float:
    """Сдвиг базовой линии: индексы вниз/вверх на ±SCRIPT_SHIFT кегля."""
    px = font.pixelSize() if font.pixelSize() > 0 else font.pointSize()
    if run.script == "sup":
        return -SCRIPT_SHIFT * px
    if run.script == "sub":
        return SCRIPT_SHIFT * px
    return 0.0


# ---------- бэкенд B: измерение и рисование (QPainter) ----------
def math_size(text: str, font: QFont) -> float:
    """Ширина строки в мини-нотации при базовом шрифте font (px).

    Измеряется тем же набором прогонов/шрифтов, которым рисует
    paint_math – ширины layout.py остаются точными."""
    total = 0.0
    for run in math_runs(text):
        fm = QFontMetricsF(_run_font(font, run))
        total += fm.horizontalAdvance(run.text)
    return total


def math_height(text: str, font: QFont) -> float:
    """Высота строки с учётом подъёма верхних индексов (для инсетов)."""
    fm = QFontMetricsF(font)
    top = fm.ascent()
    bottom = fm.descent()
    for run in math_runs(text):
        if run.script == "sup":
            top = max(top, QFontMetricsF(_run_font(font, run)).ascent()
                      - _run_shift(font, run))
        elif run.script == "sub":
            bottom = max(bottom,
                         QFontMetricsF(_run_font(font, run)).descent()
                         + _run_shift(font, run))
    return top + bottom


def paint_math(painter: QPainter, x: float, y: float, text: str,
               font: QFont, color: str | QColor | None = None) -> float:
    """Нарисовать строку мини-нотации от базовой линии (x, y).

    Возвращает суммарное горизонтальное продвижение (ширину)."""
    pen_color = QColor(color) if color is not None else None
    cursor = float(x)
    for run in math_runs(text):
        f = _run_font(font, run)
        painter.setFont(f)
        if pen_color is not None:
            painter.setPen(pen_color)
        painter.drawText(QPointF(cursor, y + _run_shift(font, run)), run.text)
        cursor += QFontMetricsF(f).horizontalAdvance(run.text)
    return cursor - float(x)


def math_wrap(text: str, font: QFont, max_width: float) -> list[str]:
    """Перенос строки мини-нотации по словам (граница – пробел)."""
    if math_size(text, font) <= max_width:
        return [text]
    lines: list[str] = []
    cur = ""
    for word in text.split(" "):
        cand = (cur + " " + word).strip() if cur else word
        if cur and math_size(cand, font) > max_width:
            lines.append(cur)
            cur = word
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


# ---------- бэкенд A: rich text для виджетов ----------
def math(text: str) -> str:
    """HTML с настоящими <sub>/<sup> для QLabel/QToolTip (rich text).

    QComboBox HTML не понимает – для списков используются Unicode-
    надстрочники (theme._sup), один подход на весь интерфейс."""
    parts: list[str] = []
    for run in math_runs(text):
        t = _html.escape(run.text)
        if run.script == "sub":
            parts.append(f"<sub>{t}</sub>")
        elif run.script == "sup":
            parts.append(f"<sup>{t}</sup>")
        else:
            parts.append(t)
    return "".join(parts)


def math_plain(text: str) -> str:
    """Схлопнуть в обычный текст (индексы – просто подряд)."""
    return "".join(r.text for r in math_runs(text))


def math_html_lines(text: str, wrap_chars: int = 88) -> str:
    """Многострочный текст мини-нотации в rich text для QToolTip/QLabel.

    Каждая логическая строка дополнительно мягко переносится по словам до
    ``wrap_chars`` символов – длинные подсказки остаются читаемыми:
    окно подсказки растет ВНИЗ ограниченной ширины, а не растягивается на
    весь экран одной строкой. Пустые строки дают абзацный отступ."""
    out_lines: list[str] = []
    for ln in text.split("\n"):
        if not ln.strip():
            out_lines.append("&nbsp;")
            continue
        cur = ""
        for word in ln.split(" "):
            cand = (cur + " " + word).strip() if cur else word
            if cur and len(cand) > wrap_chars:
                out_lines.append(math(cur))
                cur = word
            else:
                cur = cand
        out_lines.append(math(cur))
    return "<br>".join(out_lines)
