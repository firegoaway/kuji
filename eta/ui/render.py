# -*- coding: utf-8 -*-
"""Отрисовка логического дерева событий (сессия 10): ноды фиксированной
структуры, безьевые рёбра, заголовки блоков. Единый код для холста
(QGraphicsScene) и векторного PDF – WYSIWYG строгий."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QPainter, QPainterPath, QPen)

from ..core.layout import (ANN_INSET, ANN_PAD_V, Annotation, EdgeGeo,
                           NodeGeo, body_font, line_height as _lh)
from .theme import (ACCENT, APP_BG, BORDER, CUTOFF, EDGE, F_TITLE, HAZARD,
                    NODE_FILL, NODE_INSET, PAD_V, TEXT_PRIMARY,
                    TEXT_SECONDARY, ui_font)

# цветовые роли по классам нод (плоская палитра, без теней). Задача 5
# (сессия 17): «Возникновение пожара» – акцентный «сток» дерева:
# заметно толще рамка (draw_node) и чуть глубже заливка класса; ЦВЕТА
# СОСТОЯНИЙ (синий «задано», фиолетовый «ок», сессия 14) НЕ тронуты –
# выразительность через толщину/типографику, не через цвет состояния
KIND_STYLE = {
    "presence": {"border": BORDER, "accent": TEXT_SECONDARY,
                 "fill": NODE_FILL},
    "gs": {"border": "#B45309", "accent": "#B45309", "fill": "#FFFBF5"},
    "iz": {"border": "#B91C1C", "accent": "#B91C1C", "fill": "#FFF7F5"},
    "fire": {"border": HAZARD, "accent": HAZARD, "fill": "#FFEFEF"},
}

# Задача 6 (сессия 14, LOCKED): цвета СОСТОЯНИЯ – «задано» у ГС/ИЗ
# (синяя рамка #2563EB, светло-голубая заливка #EFF6FF) и «расчет
# завершен и корректен» у «Возникновения» (фиолетовая #7C3AED,
# заливка #F5F3FF). Пустые/ошибочные состояния сохраняют прежние
# цвета класса. Стили применяются и на холсте, и в PDF (WYSIWYG).
STATE_STYLE = {
    "set": {"border": "#2563EB", "accent": "#2563EB", "fill": "#EFF6FF"},
    "ok": {"border": "#7C3AED", "accent": "#7C3AED", "fill": "#F5F3FF"},
}

# стили строк тела ноды (сессия 12, Задача 13): мета-подпись / серое
# «не задано» (валидатор подскажет) / формула ΣQ – моно, крупнее, акцент
BODY_COLORS = {"meta": TEXT_SECONDARY, "muted": CUTOFF, "total": ACCENT}


def draw_annotation(p: QPainter, a: Annotation,
                    candidate: bool = False) -> None:
    """Справочная (титульная) нода дерева (Задача 4, сессия 13):
    компактная, плоская, ЯВНО вторичная по отношению к расчетным нодам –
    пунктирная рамка 1 px, приглушенная заливка, вторичный цвет текста,
    скругление. Рисуется одинаково для холста и PDF (WYSIWYG).
    Задача 5 (сессия 15): текст рисуется с Qt.TextFlag.TextDontClip –
    Qt по умолчанию КЛЕЙПИТ drawText по прямоугольнику строки, и
    надстрочники срезались рамкой."""
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    p.setPen(QPen(QColor(BORDER), 1.0, Qt.PenStyle.DashLine))
    p.setBrush(QBrush(QColor(APP_BG)))
    p.drawRoundedRect(a.rect, 6.0, 6.0)
    f = ui_font(F_TITLE)
    p.setFont(f)
    p.setPen(QColor(TEXT_SECONDARY))
    y = a.rect.top() + ANN_PAD_V
    for line in a.lines:
        p.drawText(QRectF(a.rect.left() + ANN_INSET, y,
                          a.rect.width() - 2 * ANN_INSET, _lh(f)),
                   int(Qt.AlignmentFlag.AlignLeft
                       | Qt.AlignmentFlag.AlignVCenter
                       | Qt.TextFlag.TextDontClip), line)
        y += _lh(f)
    p.restore()


def draw_node(p: QPainter, n: NodeGeo) -> None:
    """Расчетная нода дерева. Задача 5 (сессия 15, ФИНАЛЬНЫЙ фикс):
    каждая строка рисуется с Qt.TextFlag.TextDontClip – Qt по умолчанию
    обрезает drawText по прямоугольнику строки, и надстрочники
    («ΣQ = 2,28·10⁻⁶ год⁻¹», «1,000») срезались рамкой. Геометрию ноды
    (rect) заранее решили МЕТРИКИ (layout.make_node: tightBoundingRect
    + 2×NODE_INSET + 2 px), поэтому DontClip лишь страхует от
    субпиксельных хвостов – холст и PDF рисуют одинаково (WYSIWYG)."""
    # Задача 6 (сессия 14): сначала цвет состояния («задано»/«ок»),
    # при отсутствии состояния – обычные цвета класса ноды
    st = STATE_STYLE.get(getattr(n, "state", ""),
                         KIND_STYLE.get(n.kind, KIND_STYLE["presence"]))
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # корпус. Задача 5 (сессия 17): акцентный «сток» дерева – нода
    # «Возникновение пожара» – заметно толще рамка (2,6 против 1,4);
    # цвет рамки остается ЦВЕТОМ КЛАССА/СОСТОЯНИЯ (коллизий нет)
    border_w = 2.6 if n.kind == "fire" else 1.4
    p.setPen(QPen(QColor(st["border"]), border_w))
    p.setBrush(QBrush(QColor(st["fill"])))
    p.drawRoundedRect(n.rect, 8.0, 8.0)
    # титул
    y = n.rect.top() + PAD_V
    f = ui_font(F_TITLE)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(TEXT_PRIMARY))
    for line in n.title_lines:
        p.drawText(QRectF(n.rect.left() + NODE_INSET, y,
                          n.rect.width() - 2 * NODE_INSET, _lh(f)),
                   int(Qt.AlignmentFlag.AlignLeft
                       | Qt.AlignmentFlag.AlignVCenter
                       | Qt.TextFlag.TextDontClip), line)
        y += _lh(f)
    # акцентная полоска слева (цвет класса; у «Возникновения» – шире,
    # Задача 5 сессии 17: акцентный узел читается с одного взгляда)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(st["accent"]))
    strip_w = 4.0 if n.kind == "fire" else 3.0
    p.drawRoundedRect(QRectF(n.rect.left(), n.rect.top() + 6, strip_w,
                             n.rect.height() - 12), 1.5, 1.5)
    # строки тела (счётчик «Всего: N …», вероятность присутствия,
    # формула ΣQ – по стилям, Задача 13)
    styles = n.body_styles or ["meta"] * len(n.body_lines)
    for line, style in zip(n.body_lines, styles):
        f = body_font(style)
        p.setFont(f)
        p.setPen(QColor(BODY_COLORS.get(style, TEXT_SECONDARY)))
        p.drawText(QRectF(n.rect.left() + NODE_INSET + 4, y,
                          n.rect.width() - 2 * NODE_INSET - 4, _lh(f)),
                   int(Qt.AlignmentFlag.AlignLeft
                       | Qt.AlignmentFlag.AlignVCenter
                       | Qt.TextFlag.TextDontClip), line)
        y += _lh(f)
    p.restore()


def edge_path(e: EdgeGeo) -> QPainterPath:
    path = QPainterPath(e.p1)
    if e.c1 is None:
        path.lineTo(e.p2)
    else:
        path.cubicTo(e.c1, e.c2, e.p2)
    return path


def draw_edge(p: QPainter, e: EdgeGeo) -> None:
    p.save()
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    pen = QPen(QColor(EDGE), 2.0)     # Задача 5 (сессия 17): толще/мягче
    if e.dashed:
        pen.setStyle(Qt.PenStyle.DashLine)
    p.setPen(pen)
    path = edge_path(e)
    p.drawPath(path)
    # стрелка по конечной касательной (P3 − C2 либо P2 − P1)
    if e.c2 is not None:
        d = e.p2 - e.c2
    else:
        d = e.p2 - e.p1
    if d.isNull():
        p.restore()
        return
    ang = _angle(d)
    p.setBrush(QColor(EDGE))
    p.setPen(Qt.PenStyle.NoPen)
    tip = e.p2
    a1 = tip - QPointF(9 * _cos(ang + 0.42), 9 * _sin(ang + 0.42))
    a2 = tip - QPointF(9 * _cos(ang - 0.42), 9 * _sin(ang - 0.42))
    tri = QPainterPath(tip)
    tri.lineTo(a1)
    tri.lineTo(a2)
    tri.closeSubpath()
    p.drawPath(tri)
    p.restore()


# ---- мини-обертки тригонометрии (QPointF → угол/вектор)
import math as _math  # noqa: E402


def _angle(v: QPointF) -> float:
    return _math.atan2(v.y(), v.x())


def _cos(a: float) -> float:
    return _math.cos(a)


def _sin(a: float) -> float:
    return _math.sin(a)
