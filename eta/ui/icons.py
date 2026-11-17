"""Векторные иконки приложения Kuji: монограмма «Qj», нарисованная кодом.

Swiss Utilitarian: плоские геометрические формы, только ACCENT #2563EB и
TEXT_PRIMARY #0F172A на белом, одинаковая толщина штрихов, без градиентов,
теней и скруглений. Одна и та же геометрия (в координатах 256×256)
используется и для растровых иконок окна/панели задач (QIcon), и для
генерации ассетов в assets/ (скрипт tools_make_icons.py).
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPen

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets"
ICON_CANVAS = 256.0          # система координат монограммы
STROKE = 20.0                # толщина штриха в координатах 256×256

_Q_CENTER = QPointF(104.0, 112.0)
_Q_RADIUS = 66.0
_Q_TAIL_A = QPointF(150.0, 158.0)
_Q_TAIL_B = QPointF(196.0, 206.0)
_J_STEM_TOP = QPointF(196.0, 66.0)
_J_STEM_BOT = QPointF(196.0, 170.0)
_J_HOOK_END = QPointF(156.0, 196.0)   # крючок «j» пересекает ножку Q
_J_DOT = QPointF(196.0, 34.0)


def _stroke_pen(color: QColor, width: float) -> QPen:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.PenCapStyle.FlatCap)
    pen.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return pen


def draw_qj(painter: QPainter, size: float = ICON_CANVAS) -> None:
    """Рисует монограмму «Qj» во весь текущий paint-устройство.

    Координаты нормируются от базовой системы 256×256 к `size`.
    """
    k = size / ICON_CANVAS

    def p(pt: QPointF) -> QPointF:
        return QPointF(pt.x() * k, pt.y() * k)

    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    # белая подложка – иконка читается и в светлом, и в тёмном окружении
    painter.fillRect(QRectF(0.0, 0.0, size, size), QColor("#FFFFFF"))

    dark, accent = QColor("#0F172A"), QColor("#2563EB")

    # «Q» – кольцо + диагональная ножка
    painter.setPen(_stroke_pen(dark, STROKE * k))
    painter.drawArc(QRectF((_Q_CENTER.x() - _Q_RADIUS) * k,
                           (_Q_CENTER.y() - _Q_RADIUS) * k,
                           2 * _Q_RADIUS * k, 2 * _Q_RADIUS * k),
                    0, 360 * 16)
    painter.drawLine(p(_Q_TAIL_A), p(_Q_TAIL_B))

    # «j» – подстрочная, ножка пересекает хвост Q (акцентный цвет)
    painter.setPen(_stroke_pen(accent, STROKE * k))
    painter.drawLine(p(_J_STEM_TOP), p(_J_STEM_BOT))
    hook = QPainterPath(p(_J_STEM_BOT))
    hook.quadTo(p(QPointF(198.0, 204.0)), p(_J_HOOK_END))
    painter.drawPath(hook)
    r = STROKE * 0.85 * k
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(accent)
    painter.drawEllipse(p(_J_DOT), r, r)


def qj_pixmap(size_px: int) -> QImage:
    """Растеризует монограмму в QImage заданного размера."""
    img = QImage(size_px, size_px, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    painter = QPainter(img)
    draw_qj(painter, float(size_px))
    painter.end()
    return img


def _pm(px: int):
    from PySide6.QtGui import QPixmap
    return QPixmap.fromImage(qj_pixmap(px))


def app_icon() -> QIcon:
    """Иконка приложения: из assets/icon.ico (если сгенерирован), иначе
    прямая растеризация монограммы (те же пути QPainterPath)."""
    ico = ASSETS_DIR / "icon.ico"
    if ico.exists():
        icon = QIcon(str(ico))
        if not icon.isNull():
            return icon
    icon = QIcon()
    for px in (16, 20, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(_pm(px))
    return icon


# =====================================================================
# Глифы левой панели инструментов (Задача 3): плоская векторная графика,
# 1px-штрихи, монохром; активные состояния – ACCENT.
# =====================================================================
GLYPH_IN, GLYPH_OUT, GLYPH_FIT = "zoom-in", "zoom-out", "fit"
GLYPH_STICKY, GLYPH_FREE, GLYPH_TRASH = "sticky", "free", "trash"
# иерархия объекта (Задача 2): площадка/здание/отсек/помещение/участок/агрегат
GLYPH_TERRITORY = "territory"
GLYPH_BUILDING = "building"
GLYPH_COMPARTMENT = "compartment"
GLYPH_ROOM = "room"
GLYPH_AREA = "area"
GLYPH_EQUIPMENT = "equipment"
GLYPH_OUTDOOR = "outdoor"        # наружная установка (сессия 10, Задача 2)
# Задачи 1/8 сессии 6: событие, причина, защита, переименование,
# свойства, сброс позиции, связь домино, фильтр-воронка, матрица
GLYPH_EVENT_ADD = "event-add"
# Сессия 16, Задача 4: у списков причин РАЗНЫЕ глифы – ГС = облако
# (янтарь #B45309, цвет класса нод ГС на холсте), ИЗ = пламя (красный
# #B91C1C, цвет класса нод ИЗ): одна семантика – один цвет на всех
# поверхностях; единый глиф «cause» удален (других потребителей нет)
GLYPH_GS_CAUSE = "gs-cause"
GLYPH_IZ_CAUSE = "iz-cause"
GLYPH_SHIELD = "shield"
GLYPH_PENCIL = "pencil"
GLYPH_PROPS = "props"
GLYPH_CROSSHAIR = "crosshair"
GLYPH_DOMINO = "domino-link"
GLYPH_FUNNEL = "funnel"
GLYPH_MATRIX = "matrix"
GLYPH_SCHEMA = "schema"
# сессия 8: таблица сценариев → отдельное pop-out окно
GLYPH_TABLE_POP = "table-pop"
# сессия 12, Задача 11: авторазметка (сброс перетаскивания нод)
GLYPH_AUTOLAYOUT = "auto-layout"
# сессия 13, Задача 6: «Добавить дерево» (панель иерархии) – ветвящееся
# дерево узлов со знаком «+»
GLYPH_TREE_ADD = "tree-add"
# сессия 18, Задача 13: справка «Базы данных» – круг со знаком вопроса
GLYPH_HELP = "help"

_GLYPH_COLORS = {"base": QColor("#475569"), "accent": QColor("#2563EB"),
                 "danger": QColor("#DC2626")}

# палитра глифов и толщина штрихов – единый источник в theme.py (сессия 9,
# Задача 1): цвет глифа по умолчанию берётся из ICON_PALETTE; нейтральные
# служебные глифы (ICON_NEUTRAL_GLYPHS) остаются slate; active-состояние –
# осветлённый вариант собственного цвета (у нейтральных – ACCENT, как раньше)
from .theme import (ICON_BASE, ICON_NEUTRAL_GLYPHS, ICON_PALETTE,
                    ICON_STROKE, ICON_STROKE_THIN)

# полный реестр имён глифов (проверка покрытия палитрой в smoke-тесте)
ALL_GLYPHS = (GLYPH_IN, GLYPH_OUT, GLYPH_FIT, GLYPH_STICKY, GLYPH_FREE,
              GLYPH_TRASH, GLYPH_TERRITORY, GLYPH_BUILDING, GLYPH_COMPARTMENT,
              GLYPH_ROOM, GLYPH_AREA, GLYPH_EQUIPMENT, GLYPH_OUTDOOR,
              GLYPH_EVENT_ADD,
              GLYPH_GS_CAUSE, GLYPH_IZ_CAUSE, GLYPH_SHIELD, GLYPH_PENCIL,
              GLYPH_PROPS, GLYPH_CROSSHAIR, GLYPH_DOMINO, GLYPH_FUNNEL,
              GLYPH_MATRIX, GLYPH_SCHEMA, GLYPH_TABLE_POP, GLYPH_AUTOLAYOUT,
              GLYPH_TREE_ADD, GLYPH_HELP)


def glyph_color(name: str, active: bool = False) -> QColor:
    """Цвет глифа: палитра → нейтральный slate → ACCENT для active."""
    hexc = ICON_PALETTE.get(name)
    if hexc is not None:
        c = QColor(hexc)
        return c.lighter(135) if active else c
    if active:
        return _GLYPH_COLORS["accent"]
    return QColor(ICON_BASE)


def _pen(color: QColor, w: float) -> QPen:
    p = QPen(color, w)
    p.setCapStyle(Qt.PenCapStyle.FlatCap)
    p.setJoinStyle(Qt.PenJoinStyle.MiterJoin)
    return p


def _draw_glyph(painter: QPainter, name: str, color: QColor) -> None:
    """Глиф в системе координат 24×24 (вызывается из scaled-пейнтера)."""
    painter.setPen(_pen(color, ICON_STROKE))

    if name in (GLYPH_IN, GLYPH_OUT):
        # лупа: круг + ручка + (плюс | минус)
        painter.drawEllipse(QRectF(3.0, 3.0, 13.0, 13.0))
        painter.drawLine(QPointF(14.6, 14.6), QPointF(20.5, 20.5))
        if name == GLYPH_IN:
            painter.drawLine(QPointF(6.5, 9.5), QPointF(12.5, 9.5))
            painter.drawLine(QPointF(9.5, 6.5), QPointF(9.5, 12.5))
        else:
            painter.drawLine(QPointF(6.5, 9.5), QPointF(12.5, 9.5))

    elif name == GLYPH_FIT:
        # «показать всё»: угловые скобки + заполненный квадрат в центре
        for (x1, y1, x2, y2) in ((3, 3, 9, 3), (3, 3, 3, 9),          # ┌
                                 (21, 3, 15, 3), (21, 3, 21, 9),      # ┐
                                 (3, 21, 9, 21), (3, 21, 3, 15),      # └
                                 (21, 21, 15, 21), (21, 21, 21, 15)):  # ┘
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(9.5, 9.5, 5.0, 5.0))

    elif name in (GLYPH_STICKY, GLYPH_FREE):
        # липкий: контент-рамка впритык к квадрату; свободный: рамка шире
        # и четыре стрелки наружу (камеру можно увести за контент)
        box = QRectF(9.0, 9.0, 6.0, 6.0)
        frame = QRectF(6.0, 6.0, 12.0, 12.0) if name == GLYPH_STICKY \
            else QRectF(2.0, 2.0, 20.0, 20.0)
        painter.setPen(_pen(color, ICON_STROKE))
        painter.setBrush(color)
        painter.drawRect(box)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if name == GLYPH_STICKY:
            painter.drawRect(frame)
        else:
            dash = _pen(color, ICON_STROKE_THIN)
            dash.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(dash)
            painter.drawRect(frame)
            painter.setPen(_pen(color, ICON_STROKE))
            for (ax, ay) in ((8.0, 8.0), (16.0, 8.0), (8.0, 16.0), (16.0, 16.0)):
                sx = 1.0 if ax > 12 else -1.0
                sy = 1.0 if ay > 12 else -1.0
                painter.drawLine(QPointF(ax, ay), QPointF(ax + 4.5 * sx, ay + 4.5 * sy))
                painter.drawPoint(QPointF(ax + 4.5 * sx, ay + 4.5 * sy))

    elif name == GLYPH_TRASH:
        # мусорка: крышка + ручка + корпус (HAZARD)
        painter.drawLine(QPointF(4.0, 6.0), QPointF(20.0, 6.0))
        painter.drawLine(QPointF(9.5, 3.0), QPointF(14.5, 3.0))
        painter.drawLine(QPointF(9.5, 3.0), QPointF(9.5, 6.0))
        painter.drawLine(QPointF(14.5, 3.0), QPointF(14.5, 6.0))
        painter.drawLine(QPointF(6.5, 9.0), QPointF(8.0, 21.0))
        painter.drawLine(QPointF(17.5, 9.0), QPointF(16.0, 21.0))
        painter.drawLine(QPointF(6.5, 9.0), QPointF(17.5, 9.0))
        painter.drawLine(QPointF(8.0, 21.0), QPointF(16.0, 21.0))

    elif name == GLYPH_TERRITORY:
        # площадка: пунктирные границы + застройка внутри
        dash = _pen(color, ICON_STROKE_THIN)
        dash.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(dash)
        painter.drawRect(QRectF(2.5, 4.0, 19.0, 16.0))
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawRect(QRectF(8.0, 10.0, 8.0, 6.0))
        painter.drawLine(QPointF(11.0, 10.0), QPointF(11.0, 16.0))

    elif name == GLYPH_BUILDING:
        # здание: контур + скат крыши + дверь + окна
        painter.drawRect(QRectF(5.0, 7.0, 14.0, 14.0))
        painter.drawLine(QPointF(3.5, 7.0), QPointF(12.0, 2.5))
        painter.drawLine(QPointF(12.0, 2.5), QPointF(20.5, 7.0))
        painter.drawRect(QRectF(10.0, 15.0, 4.0, 6.0))
        painter.drawLine(QPointF(7.0, 10.0), QPointF(9.5, 10.0))
        painter.drawLine(QPointF(14.5, 10.0), QPointF(17.0, 10.0))

    elif name == GLYPH_COMPARTMENT:
        # пожарный отсек: рамка + противопожарная преграда (пунктир) посередине
        painter.drawRect(QRectF(2.5, 5.0, 19.0, 14.0))
        dash = _pen(color, ICON_STROKE)
        dash.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(dash)
        painter.drawLine(QPointF(12.0, 5.0), QPointF(12.0, 19.0))
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawLine(QPointF(10.4, 8.0), QPointF(13.6, 8.0))

    elif name == GLYPH_ROOM:
        # помещение: контур + внутренняя перегородка с проемом
        painter.drawRect(QRectF(3.5, 4.0, 17.0, 16.0))
        painter.drawLine(QPointF(12.0, 4.0), QPointF(12.0, 9.0))
        painter.drawLine(QPointF(12.0, 13.0), QPointF(12.0, 20.0))
        painter.drawLine(QPointF(12.0, 11.0), QPointF(15.0, 11.0))

    elif name == GLYPH_AREA:
        # участок (технологическая зона): пунктирная зона + агрегат
        dash = _pen(color, ICON_STROKE_THIN)
        dash.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(dash)
        painter.drawEllipse(QPointF(12.0, 12.0), 9.0, 9.0)
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawRect(QRectF(9.0, 9.0, 6.0, 6.0))
        painter.drawLine(QPointF(12.0, 15.0), QPointF(12.0, 18.0))

    elif name == GLYPH_EQUIPMENT:
        # агрегат (насос, ИСО-подобный): корпус + патрубки + рама
        painter.drawEllipse(QRectF(6.0, 5.0, 11.0, 11.0))
        painter.drawLine(QPointF(11.5, 2.0), QPointF(11.5, 5.0))
        painter.drawLine(QPointF(11.5, 16.0), QPointF(11.5, 19.5))
        painter.drawLine(QPointF(5.0, 19.5), QPointF(18.5, 19.5))
        painter.drawLine(QPointF(11.5, 8.0), QPointF(15.0, 10.5))

    elif name == GLYPH_OUTDOOR:
        # наружная установка (сессия 10): вертикальный сосуд на опорах,
        # земля и солнце (аппарат под открытым небом)
        painter.drawRoundedRect(QRectF(8.0, 3.5, 8.0, 12.0), 3.0, 3.0)
        painter.drawLine(QPointF(9.5, 15.5), QPointF(7.5, 20.0))
        painter.drawLine(QPointF(14.5, 15.5), QPointF(16.5, 20.0))
        painter.drawLine(QPointF(3.5, 20.0), QPointF(20.5, 20.0))
        painter.drawEllipse(QRectF(16.8, 2.8, 4.4, 4.4))
        thin = _pen(color, ICON_STROKE_THIN)
        painter.setPen(thin)
        painter.drawLine(QPointF(19.0, 0.8), QPointF(19.0, 2.2))
        painter.drawLine(QPointF(19.0, 7.8), QPointF(19.0, 9.2))
        painter.drawLine(QPointF(17.0, 5.0), QPointF(15.6, 5.0))

    elif name == GLYPH_EVENT_ADD:
        # ключевое/инициирующее событие: узел-рамка + молния + «+»
        painter.drawRect(QRectF(3.0, 6.0, 12.0, 12.0))
        bolt = QPainterPath(QPointF(11.0, 7.5))
        bolt.lineTo(QPointF(8.2, 13.0))
        bolt.lineTo(QPointF(10.2, 13.0))
        bolt.lineTo(QPointF(9.0, 16.5))
        bolt.lineTo(QPointF(12.6, 11.2))
        bolt.lineTo(QPointF(10.4, 11.2))
        bolt.lineTo(QPointF(12.0, 7.5))
        bolt.closeSubpath()
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(bolt)
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawLine(QPointF(17.5, 4.0), QPointF(21.5, 4.0))
        painter.drawLine(QPointF(19.5, 2.0), QPointF(19.5, 6.0))

    elif name == GLYPH_GS_CAUSE:
        # ГС (образование горючей среды, сессия 16): ОБЛАКО паров/газа –
        # плоское основание и три выпуклых сегмента, контур штрихом
        # (геометрически не связан с пламенем ИЗ – списки различимы
        # с одного взгляда в 16–22 px)
        cloud = QPainterPath(QPointF(5.0, 17.5))
        cloud.quadTo(QPointF(1.8, 17.5), QPointF(2.6, 13.2))
        cloud.quadTo(QPointF(3.0, 8.0), QPointF(8.2, 8.2))
        cloud.quadTo(QPointF(9.6, 3.6), QPointF(13.8, 5.2))
        cloud.quadTo(QPointF(19.6, 4.2), QPointF(20.2, 9.8))
        cloud.quadTo(QPointF(22.4, 10.8), QPointF(21.0, 14.6))
        cloud.quadTo(QPointF(20.4, 17.5), QPointF(17.4, 17.5))
        cloud.closeSubpath()
        painter.drawPath(cloud)

    elif name == GLYPH_IZ_CAUSE:
        # ИЗ (источник зажигания, сессия 16): ПЛАМЯ – внешний контур
        # капли-факела + внутренний язычок (тоньше); оптический размер
        # и вес штриха – как у облака ГС
        flame = QPainterPath(QPointF(12.0, 2.4))
        flame.quadTo(QPointF(17.6, 7.8), QPointF(18.0, 12.8))
        flame.quadTo(QPointF(18.4, 19.6), QPointF(12.0, 21.6))
        flame.quadTo(QPointF(5.6, 19.6), QPointF(6.0, 12.8))
        flame.quadTo(QPointF(6.4, 7.8), QPointF(12.0, 2.4))
        flame.closeSubpath()
        painter.drawPath(flame)
        inner = QPainterPath(QPointF(12.0, 10.8))
        inner.quadTo(QPointF(15.0, 13.4), QPointF(14.4, 16.0))
        inner.quadTo(QPointF(12.0, 17.9), QPointF(9.6, 16.0))
        inner.quadTo(QPointF(9.0, 13.4), QPointF(12.0, 10.8))
        inner.closeSubpath()
        painter.setPen(_pen(color, ICON_STROKE_THIN))
        painter.drawPath(inner)
        painter.setPen(_pen(color, ICON_STROKE))

    elif name == GLYPH_SHIELD:
        # защита/барьер: щит с ключевым отверстием
        shield = QPainterPath(QPointF(12.0, 2.5))
        shield.lineTo(QPointF(20.5, 5.5))
        shield.lineTo(QPointF(20.5, 12.0))
        shield.quadTo(QPointF(20.5, 18.0), QPointF(12.0, 21.5))
        shield.quadTo(QPointF(3.5, 18.0), QPointF(3.5, 12.0))
        shield.lineTo(QPointF(3.5, 5.5))
        shield.closeSubpath()
        painter.drawPath(shield)
        painter.drawEllipse(QPointF(12.0, 10.0), 1.4, 1.4)
        painter.drawLine(QPointF(12.0, 11.4), QPointF(12.0, 15.0))

    elif name == GLYPH_PENCIL:
        # переименование: карандаш под углом + линия строки
        painter.drawLine(QPointF(15.5, 3.0), QPointF(20.5, 8.0))
        painter.drawLine(QPointF(5.0, 13.5), QPointF(15.5, 3.0))
        painter.drawLine(QPointF(5.0, 13.5), QPointF(3.4, 20.0))
        painter.drawLine(QPointF(5.0, 13.5), QPointF(11.5, 15.1))
        painter.drawLine(QPointF(20.5, 8.0), QPointF(11.5, 17.0))
        painter.drawLine(QPointF(11.5, 15.1), QPointF(11.5, 17.0))

    elif name == GLYPH_PROPS:
        # свойства: строки списка с точками-маркерами
        for i, y in enumerate((5.0, 10.5, 16.0, 21.0)):
            painter.drawEllipse(QPointF(4.5, y), 1.2, 1.2)
            painter.drawLine(QPointF(8.0, y), QPointF(20.5, y))

    elif name == GLYPH_CROSSHAIR:
        # сброс позиции: прицел
        painter.drawEllipse(QRectF(6.0, 6.0, 12.0, 12.0))
        painter.drawEllipse(QRectF(11.4, 11.4, 1.2, 1.2))
        painter.drawLine(QPointF(12.0, 2.0), QPointF(12.0, 6.0))
        painter.drawLine(QPointF(12.0, 18.0), QPointF(12.0, 22.0))
        painter.drawLine(QPointF(2.0, 12.0), QPointF(6.0, 12.0))
        painter.drawLine(QPointF(18.0, 12.0), QPointF(22.0, 12.0))

    elif name == GLYPH_DOMINO:
        # связь домино: пунктирная стрелка между двумя кадрами
        painter.drawRect(QRectF(2.0, 3.5, 7.0, 7.0))
        painter.drawRect(QRectF(15.0, 13.5, 7.0, 7.0))
        dash = _pen(color, ICON_STROKE_THIN)
        dash.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(dash)
        painter.drawLine(QPointF(9.0, 7.0), QPointF(18.5, 17.0))
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawLine(QPointF(14.0, 16.5), QPointF(18.5, 17.0))
        painter.drawLine(QPointF(18.5, 17.0), QPointF(17.8, 12.7))

    elif name == GLYPH_FUNNEL:
        # фильтр: воронка (штрих тоньше основного – линии близко,
        # при 2.2px сливаются в пятно)
        painter.setPen(_pen(color, ICON_STROKE_THIN))
        painter.drawLine(QPointF(3.0, 4.0), QPointF(21.0, 4.0))
        painter.drawLine(QPointF(3.0, 4.0), QPointF(10.0, 12.0))
        painter.drawLine(QPointF(21.0, 4.0), QPointF(14.0, 12.0))
        painter.drawLine(QPointF(10.0, 12.0), QPointF(10.0, 20.0))
        painter.drawLine(QPointF(14.0, 12.0), QPointF(14.0, 20.0))
        painter.drawLine(QPointF(10.0, 20.0), QPointF(14.0, 20.0))

    elif name == GLYPH_MATRIX:
        # матричный вид: сетка таблицы со строкой-заголовком
        painter.drawRect(QRectF(3.0, 4.0, 18.0, 16.0))
        painter.drawLine(QPointF(3.0, 9.0), QPointF(21.0, 9.0))
        painter.drawLine(QPointF(9.0, 9.0), QPointF(9.0, 20.0))
        painter.drawLine(QPointF(15.0, 9.0), QPointF(15.0, 20.0))
        painter.drawLine(QPointF(3.0, 14.5), QPointF(21.0, 14.5))

    elif name == GLYPH_SCHEMA:
        # схематический вид: узлы цепочки со связями
        painter.drawRect(QRectF(2.0, 9.5, 6.0, 5.0))
        painter.drawRect(QRectF(9.0, 9.5, 6.0, 5.0))
        painter.drawRect(QRectF(16.0, 9.5, 6.0, 5.0))
        painter.drawLine(QPointF(8.0, 12.0), QPointF(9.0, 12.0))
        painter.drawLine(QPointF(15.0, 12.0), QPointF(16.0, 12.0))

    elif name == GLYPH_AUTOLAYOUT:
        # авторазметка: ноды возвращаются на автоматические места –
        # слева два узла, справа итоговый, соединения сходятся к нему
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(QRectF(3.0, 4.0, 6.0, 6.0))
        painter.drawRect(QRectF(3.0, 14.0, 6.0, 6.0))
        painter.drawRect(QRectF(15.0, 9.0, 6.0, 6.0))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(_pen(color, ICON_STROKE))
        painter.drawLine(QPointF(9.0, 7.0), QPointF(15.0, 12.0))
        painter.drawLine(QPointF(9.0, 17.0), QPointF(15.0, 12.0))

    elif name == GLYPH_TREE_ADD:
        # «Добавить дерево» (сессия 13, Задача 6): сверху родительский
        # узел, ниже два дочерних со связями + знак «+» слева внизу
        painter.drawRect(QRectF(3.0, 3.0, 7.0, 7.0))
        painter.drawRect(QRectF(14.5, 4.0, 6.5, 6.5))
        painter.drawRect(QRectF(14.5, 14.0, 6.5, 6.5))
        painter.drawLine(QPointF(10.0, 6.5), QPointF(12.25, 6.5))
        painter.drawLine(QPointF(12.25, 7.25), QPointF(12.25, 17.25))
        painter.drawLine(QPointF(12.25, 7.25), QPointF(14.5, 7.25))
        painter.drawLine(QPointF(12.25, 17.25), QPointF(14.5, 17.25))
        painter.drawLine(QPointF(3.9, 18.5), QPointF(9.1, 18.5))
        painter.drawLine(QPointF(6.5, 15.9), QPointF(6.5, 21.1))

    elif name == GLYPH_HELP:
        # справка (сессия 18, Задача 13): круг + знак вопроса – дуга,
        # ножка и точка; штрих ICON_STROKE, плоский канон
        painter.drawEllipse(QRectF(2.2, 2.2, 19.6, 19.6))
        q = QPainterPath(QPointF(9.2, 8.2))
        q.quadTo(QPointF(9.2, 5.2), QPointF(12.2, 5.2))
        q.quadTo(QPointF(15.2, 5.2), QPointF(15.2, 7.8))
        q.quadTo(QPointF(15.2, 9.8), QPointF(12.9, 10.9))
        q.quadTo(QPointF(12.0, 11.4), QPointF(12.0, 13.2))
        painter.drawPath(q)
        painter.drawLine(QPointF(12.0, 16.4), QPointF(12.0, 16.8))

    elif name == GLYPH_TABLE_POP:
        # таблица + стрелка «открыть в отдельном окне» (верхний-правый
        # угол): сетка таблицы в нижне-левой зоне, диагональная стрелка
        # выходит из-под верхней кромки таблицы наружу, к углу
        painter.drawRect(QRectF(2.5, 9.0, 14.0, 12.5))          # рамка
        painter.drawLine(QPointF(2.5, 13.0), QPointF(16.5, 13.0))   # заголовок
        painter.drawLine(QPointF(2.5, 17.5), QPointF(16.5, 17.5))   # строка тела
        painter.drawLine(QPointF(8.5, 9.0), QPointF(8.5, 21.5))     # колонка 1
        painter.drawLine(QPointF(13.5, 13.0), QPointF(13.5, 21.5))  # колонка 2
        painter.drawLine(QPointF(14.6, 8.9), QPointF(20.5, 3.0))    # стержень ↗
        painter.drawLine(QPointF(16.2, 3.0), QPointF(20.5, 3.0))    # наконечник
        painter.drawLine(QPointF(20.5, 3.0), QPointF(20.5, 7.3))


def glyph_icon(name: str, active: bool = False, size_px: int = 24,
               color: str | None = None) -> QIcon:
    """Иконка-глиф; по умолчанию – СОБСТВЕННЫЙ цвет из ICON_PALETTE
    (сессия 9, Задача 1); active=True – осветлённый вариант своего цвета
    (нейтральные глифы – ACCENT, как раньше).

    color (HEX-строка) принудительно задаёт цвет – например, "#FFFFFF"
    для глифа на синем фоне primary-кнопки (Задача: контраст иконок).
    """
    if color is not None:
        c = QColor(color)
    else:
        c = glyph_color(name, active)
    icon = QIcon()
    for px in (16, 20, 24, 32, 40, 48):
        img = QImage(px, px, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.transparent)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        p.scale(px / 24.0, px / 24.0)
        _draw_glyph(p, name, c)
        p.end()
        from PySide6.QtGui import QPixmap
        icon.addPixmap(QPixmap.fromImage(img))
    return icon


# =====================================================================
# «Применить на холсте» (вкладка «Библиотека типовых сценариев» окна
# «База данных»): белая outline-кнопка с синим контуром (#primaryOutline,
# сессия «контраст иконки») – глиф БЕЛЫЙ с ЧЁРНЫМ контуром: заливка
# перекрывает рамку холста под стрелкой (аккуратное наслоение), контур
# #0F172A читается на белом фоне кнопки.
# Видимая часть глифа – 16×16; холст SVG шире на 3px (справа прозрачный
# встроенный отступ) – суммарный зазор иконка→текст ≈7px (замер QA:
# 4px межэлементного интервала стиля + 3px отступа).
# =====================================================================

APPLY_TO_CANVAS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="19" height="16"'
    ' viewBox="0 0 19 16">'
    # холст: прямоугольник со скруглением
    '<rect x="5.9" y="2.7" width="8.1" height="10.6" rx="1.6"'
    ' fill="#FFFFFF" stroke="#0F172A" stroke-width="1.8"'
    ' stroke-linejoin="round"/>'
    # стрелка «на холст»: замкнутый контур (древко + наконечник)
    '<path d="M1.3 7.1 H7.6 V5.2 L10.8 8 L7.6 10.8 V8.9 H1.3 Z"'
    ' fill="#FFFFFF" stroke="#0F172A" stroke-width="1.8"'
    ' stroke-linejoin="round" stroke-linecap="round"/>'
    '</svg>'
)


def apply_to_canvas_icon() -> QIcon:
    """Белый глиф с чёрным контуром «стрелка на холст» для
    #primaryOutline-кнопки «Применить на холсте».

    SVG (видимый глиф 16×16 + 3px прозрачного отступа справа, штрих 1.8,
    скруглённые соединения) растеризуется QSvgRenderer'ом в QPixmap с
    devicePixelRatio (1×/1.5×/2×/3×) – чётко на HiDPI-экранах во всех
    состояниях кнопки.setIconSize → QSize(19, 16).
    """
    from PySide6.QtGui import QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderer = QSvgRenderer(APPLY_TO_CANVAS_SVG.encode("utf-8"))
    if not renderer.isValid():
        raise ValueError("APPLY_TO_CANVAS_SVG: некорректный SVG")
    renderer.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
    icon = QIcon()
    for dpr in (1.0, 1.5, 2.0, 3.0):
        pm = QPixmap(round(19 * dpr), round(16 * dpr))
        pm.setDevicePixelRatio(dpr)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        renderer.render(painter, QRectF(0.0, 0.0, 19.0, 16.0))
        painter.end()
        icon.addPixmap(pm)
    return icon
