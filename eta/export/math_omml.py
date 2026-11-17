# -*- coding: utf-8 -*-
r"""Юникод-математика «Куджи» → LaTeX для OMML-формул Word (сессия 20, п.4).

ЗАЧЕМ. Отчёт всегда печатал формулы и размерности плоским текстом с
юникод-надстрочниками («Q₁ = 1,1·(4·10⁻⁶·1200)·(1−exp(−4,6·10⁻⁶))·0,15 =
3,31·10⁻⁸ год⁻¹»). Для Word такой текст – обычные символы: формулу нельзя
редактировать как формулу, выравнивание знаков не работает. Pandoc умеет
превращать LaTeX-математику в НАСТОЯЩИЙ OOXML-мат:

  * `$ ... $`   → `<m:oMath>`      (строчная формула в тексте/ячейке);
  * `$$ ... $$` → `<m:oMathPara>`  (выключная формула отдельной строкой,
    по центру – как просит заказчик для расчётных выражений).

Этот модуль – ЕДИНСТВЕННЫЙ переводчик между нашей типографикой и LaTeX.
Грани́ца ответственности: ЭКРАН, матрица в интерфейсе и вся числовая
типографика ниже по стеку НЕ меняются (инженер по-прежнему видит
«9·10⁻⁵»); LaTeX рождается только при сборке Markdown для pandoc, то есть
только в .docx.

КАК УСТРОЕН ПЕРЕВОД. Ключевое правило – каждый фрагмент упаковывается
РОВНО один раз. Всё, что уже стало готовым LaTeX (`\text{год}^{-1}`,
`_{\text{В}}`), на время остальных замен прячется в защищённый маркер
`\x00N\x00`, иначе цепочка regex'ов порождает `\text{\text{...}}` – а
такое texmath Pandoc ОТКАЗЫВАЕТСЯ парсить и оставляет `$...$` текстом
(проверено пробой на реальном pandoc 3.4).

Порядок обработки строки:

  1. единицы измерения с показателем и без → `\text{...}^{...}`
     (`год⁻¹` → `\text{год}^{-1}`, `км²` → `\text{км}^{2}`);
  2. подстрочники: цифры (`Q₁` → `Q_{1}`) и индексы словами
     (`Q_В` → `Q_{\text{В}}`, `Q_i` → `Q_{i}`, `N_{у.м}` → `\text{у.м}`);
  3. одиночные кирилличные слова вне индексов → `\text{...}` (иначе
     texmath спотыкается о голую кириллицу);
  4. оставшиеся надстрочники и каретка → `^{...}` (`10⁻⁶`, `10^-6`, `F^b`);
  5. операторы и греческие: `·`/`×`/`*` → `\cdot`/`\times`, `−` → `-`,
     `Σ` → `\sum`, `λ` → `\lambda`, `σ` → `\sigma`, `≤≥≈≠∞%` → команды;
  6. функции `exp|ln|lg|log|min|max|…` → `\exp|…`;
  7. запятая в мантиссе → `{,}` («3,31» → «3{,}31», без пробела после
     знака препинания);
  8. возврат защищённых фрагментов.

Модуль чистый: ни Qt, ни файловой системы; вызывающий код передаёт сюда
ТОЛЬКО математические фрагменты – русские подписи сценариев остаются
текстом за пределами `$...$`.
"""

from __future__ import annotations

import re

# ──────────────── юникод-надстрочники/подстрочники (как в numfmt) ────────
_SUP2PLAIN = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4",
              "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9",
              "⁻": "-", "⁺": "+"}
_SUB2PLAIN = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4",
              "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}
_SUP_CHARS = "".join(_SUP2PLAIN)
_SUB_CHARS = "".join(_SUB2PLAIN)

_SUP_RUN = re.compile(f"[{_SUP_CHARS}]+")
_SUB_RUN = re.compile(f"[{_SUB_CHARS}]+")

# Единицы измерения отчёта. Правило, спасающее кириллические слова от
# поедания одиночными буквами: СО СТРАШНЫМ показателем степени принимается
# любая единица (год⁻¹, м², А⁻¹), БЕЗ показателя – только многобуквенные
# ядра (год, сут, мин, сек, кг, км, Па, кВт …).
_UNIT_CORES = ("км/ч", "м³/с", "м²/с", "кг/с", "л/с", "г/с",
               "кВт", "кПа", "дм³", "мм²", "км²", "км³", "моль", "кДж",
               "м³", "м²", "год", "сут", "мин", "сек", "кг", "мг", "км",
               "мм", "Па", "Вт", "град", "Дж", "м", "л", "г", "т", "ч", "с",
               "А", "В", "К")
_UNIT_ALT = "|".join(re.escape(u) for u in _UNIT_CORES)
_UNIT_PLAIN_ALT = "|".join(re.escape(u) for u in _UNIT_CORES if len(u) > 1)
_EXP_ALT = rf"(?:([{_SUP_CHARS}]+)|\^\{{?(-?[\dA-Za-z])\}}?)"
# единица СО степенью (показатель обязателен)
_UNIT_EXP_RE = re.compile(
    rf"(?<![0-9A-Za-zА-Яа-яЁё%.])({_UNIT_ALT}){_EXP_ALT}")
# единица без показателя – только длинные ядра и на границе слова
_UNIT_PLAIN_RE = re.compile(
    rf"(?<![0-9A-Za-zА-Яа-яЁё%.])({_UNIT_PLAIN_ALT})"
    rf"(?!{_EXP_ALT})(?![0-9A-Za-zА-Яа-яЁё])")

_CYR_WORD = re.compile(r"[А-Яа-яЁё]+(?:\.[А-Яа-яЁё]+)*")
_SUBSCRIPT_WORD = re.compile(r"_([A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё0-9.]*)")
_CARET = re.compile(r"\^\s*\{?(-?[\dA-Za-z]+)\}?")
_TEN_SUP = re.compile(rf"10([{_SUP_CHARS}]+)")
_DECIMAL = re.compile(r"(?<=\d),(?=\d)")
_FUNCS = ("exp", "ln", "lg", "log", "sin", "cos", "tg", "ctg", "arctg",
          "min", "max")
_FUNC_RE = re.compile(r"(?<![A-Za-z\\])(" + "|".join(_FUNCS) + r")(?=[\s(]|$)")

# символы: операторы, отношения, греческие (то, что реально встречается в
# формулах Методики № 533 и в нашей базе знаний)
_SYMBOLS = {
    "·": r" \cdot ", "⋅": r" \cdot ", "×": r" \times ",
    "÷": r" \div ",
    "−": "-", "–": "-",
    "≤": r"\leq ", "≥": r"\geq ", "≈": r"\approx ", "≠": r"\neq ",
    "∝": r"\propto ", "∞": r"\infty ", "√": r"\sqrt",
    "Σ": r"\sum ", "∑": r"\sum ", "∏": r"\prod ",
    "°": r"^{\circ}", "%": r"\%",
    "α": r"\alpha ", "β": r"\beta ", "γ": r"\gamma ", "δ": r"\delta ",
    "ε": r"\varepsilon ", "ζ": r"\zeta ", "η": r"\eta ", "θ": r"\theta ",
    "κ": r"\kappa ", "λ": r"\lambda ", "μ": r"\mu ", "ν": r"\nu ",
    "ξ": r"\xi ", "π": r"\pi ", "ρ": r"\rho ", "ς": r"\sigma ",
    "σ": r"\sigma ", "τ": r"\tau ", "υ": r"\upsilon ", "φ": r"\varphi ",
    "χ": r"\chi ", "ψ": r"\psi ", "ω": r"\omega ",
    "Γ": r"\Gamma ", "Δ": r"\Delta ", "Θ": r"\Theta ", "Λ": r"\Lambda ",
    "Ξ": r"\Xi ", "Π": r"\Pi ", "Φ": r"\Phi ",
    "Ψ": r"\Psi ", "Ω": r"\Omega ",
}


def _sup_plain(run: str) -> str:
    """Группа надстрочников → обычная строка («⁻⁶» → «-6»)."""
    return "".join(_SUP2PLAIN[c] for c in run)


class _Guard:
    """Защита уже готовых LaTeX-фрагментов от повторной обработки."""

    def __init__(self) -> None:
        self.parts: list[str] = []

    def keep(self, latex: str) -> str:
        self.parts.append(latex)
        return f"\x00{len(self.parts) - 1}\x00"

    def release(self, text: str) -> str:
        return re.sub(r"\x00(\d+)\x00",
                      lambda m: self.parts[int(m.group(1))], text)


def _units(s: str, g: _Guard) -> str:
    """Размерности → `\text{...}^{...}` под защитой guard'а."""

    def rep(m: re.Match) -> str:
        core = m.group(1)
        exp = m.group(2) or m.group(3) or ""
        if m.group(2):
            exp = _sup_plain(exp)
        body = f"\\text{{{core}}}"
        return g.keep(f"{body}^{{{exp}}}" if exp else body)

    s = _UNIT_EXP_RE.sub(rep, s)           # сперва со степенью
    return _UNIT_PLAIN_RE.sub(rep, s)      # потом длинные без степени


def _subscripts(s: str, g: _Guard) -> str:
    """Индексы: цифры-подстрочники и `_слово` (кириллица – в \\text)."""
    s = _SUB_RUN.sub(lambda m: g.keep("_{" + _sup_plain_digit(m.group(0)) + "}"),
                     s)

    def rep(m: re.Match) -> str:
        tok = m.group(1)
        if re.search(r"[А-Яа-яЁё]", tok):
            return g.keep("_{\\text{" + tok + "}}")
        return g.keep("_{" + tok + "}")

    return _SUBSCRIPT_WORD.sub(rep, s)


def _sup_plain_digit(run: str) -> str:
    """Подстрочники цифр (та же таблица знаков, отдельная для ясности)."""
    return "".join(_SUB2PLAIN[c] for c in run)


def _cyrillic(s: str, g: _Guard) -> str:
    """Голой кириллице в формуле не место: упаковки в `\text{}`."""
    return _CYR_WORD.sub(lambda m: g.keep("\\text{" + m.group(0) + "}"), s)


def _powers(s: str) -> str:
    """Степени: оставшиеся юникод-надстрочники и каретка → `^{...}`."""
    s = _TEN_SUP.sub(lambda m: "10^{" + _sup_plain(m.group(1)) + "}", s)
    s = _SUP_RUN.sub(lambda m: "^{" + _sup_plain(m.group(0)) + "}", s)
    return _CARET.sub(lambda m: "^{" + m.group(1) + "}", s)


def expr(text) -> str:
    """Тело LaTeX-формулы из юникод-строки нашей типографики.

    Пустая строка (или только пробелы) → пустая строка: вызывающий код не
    должен выдавать `$ $`."""
    s = str(text or "").strip()
    if not s:
        return ""
    g = _Guard()
    s = _units(s, g)             # 1. размерности (пока нетронутые ⁻¹/²)
    s = _subscripts(s, g)        # 2. индексы
    s = _cyrillic(s, g)          # 3. кириллица вне индексов
    s = _powers(s)               # 4. степени
    for src, dst in _SYMBOLS.items():   # 5. операторы и греческие
        if src in s:
            s = s.replace(src, dst)
    s = _FUNC_RE.sub(r"\\\1", s)  # 6. функции
    s = _DECIMAL.sub("{,}", s)     # 7. десятичная запятая без пробела
    s = g.release(s)               # 8. возврат защищённых фрагментов
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def inline(text) -> str:
    """Строчная формула `$…$` → Word соберёт `<m:oMath>`."""
    body = expr(text)
    return f"${body}$" if body else ""


def display(text) -> str:
    """Выключная формула `$$…$$` отдельной строкой → `<m:oMathPara>`
    (в Word – по центру)."""
    body = expr(text)
    return f"$${body}$$" if body else ""


def has_math(text) -> bool:
    """Есть ли в строке математика (для условной упаковки в `$…$`)."""
    return bool(expr(text))
