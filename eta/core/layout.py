# -*- coding: utf-8 -*-
"""Авто-раскладка логического дерева событий (сессия 10; сессия 12).

Структура дерева фиксирована (инвариант пяти типов):

    колонка 0             колонка 1                колонка 2
    [Наличие вещества] ─┐
                         ├→ [Образование ГС (ГС)] ─→ [Возникновение
    [Наличие ОК] ───────┘                           пожара]
                         [Появление ИЗ (ИЗ)] ──────↗

Сессия 12:
  * Задача 13 – тело ноды МИНИМАЛИСТИЧНО: счётчик «Всего: N …» и
    формула ΣQ (перечисления причин/сценариев живут в инспекторе,
    «Группе сценариев» и матрице); формула чуть крупнее;
  * Задача 14 – перенос только по ЦЕЛЫМ словам: нода растет под
    самое длинное слово (клап MAX_NODE_W поднимается при нужде),
    усечений по буквам больше нет;
  * Задача 15 – подпись нод наличия: «вероятность присутствия: …»;
  * Задача 11 – ручные смещения нод (node_offsets) применяются здесь:
    холст и PDF строго WYSIWYG.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from PySide6.QtCore import QPointF, QRectF

from ..ui.theme import (F_FORMULA, F_META, F_TITLE, MARGIN,
                        MAX_NODE_W, MIN_NODE_W, NODE_INSET, PAD_V, PIN_R,
                        mono_font, ui_font)
from .model import TreeModel
from .numfmt import fmt_q  # noqa: F401  – пере-экспорт: потребители
# (статус-бар, матрица, БД) продолжают импортировать layout.fmt_q
from .validation import check_tree

_LINE_STEP = 1.28     # межстрочный интервал

# шаг колонок и вертикали. Задача 5 (сессия 17): зазоры увеличены
# пропорционально крупной базовой геометрии – дерево дышит свободнее
COL_GAP = 64.0       # зазор между колонками (бейджей больше нет)
ROW_GAP = 36.0       # вертикальный зазор между нодами одной колонки
TREE_GAP = 88.0      # горизонтальный зазор между деревьями

# Задача 4 (сессия 13): справочная (титульная) нода дерева
ANN_INSET = 9.0       # горизонтальный отступ текста
ANN_PAD_V = 5.0       # вертикальные поля
ANN_MIN_W = 120.0     # минимальная ширина плашки
ANN_MAX_W = 300.0     # стартовый потолок ширины (растет под ≤2 строки)
ANN_SNAP_GAP = 14.0   # зазор до ноды при магнитной привязке (сверху)
ANN_SNAP_DIST = 30.0  # порог «рядом с нодой» для привязки, px

# стили строк тела ноды (Задача 13): шрифт задается в theme.py
BODY_STYLES = ("meta", "muted", "total")


def _fm(font):
    from PySide6.QtGui import QFontMetricsF
    return QFontMetricsF(font)


def ink_rect(font, text: str) -> QRectF:
    """Задача 5 (сессия 15): ТОЧНЫЕ метрики строки – tightBoundingRect
    по QFontMetricsF: фактические чернильные границы глифов, включая
    подстановку шрифта для надстрочников («10⁻⁶», «год⁻¹»). Раньше
    ширина ноды считалась по horizontalAdvance, а отрисовка Qt
    КЛЕЙПИЛА текст по прямоугольнику строки – хвосты надстрочников
    срезались рамкой. Теперь геометрия решается метриками, а отрисовка
    идет с Qt.TextFlag.TextDontClip (render.py) – резать нечего."""
    return _fm(font).tightBoundingRect(text)


def body_font(style: str):
    """Шрифт строки тела ноды по стилю (мета-подпись / серое «не
    задано» / формула ΣQ – моноширинная, чуть крупнее, полужирная)."""
    if style == "total":
        return mono_font(F_FORMULA, bold=True)
    return ui_font(F_META)


def wrap_words(text: str, font, max_width: float) -> list[str]:
    """Перенос по ЦЕЛЫМ словам (Задача 14): усечений по буквам нет –
    слово, не поместившееся в max_width, остается одной строкой и
    РАСШИРЯЕТ ноду (ширина в make_node учитывает самое длинное слово).
    Пустой текст – пустой список."""
    fm = _fm(font)
    if not text:
        return []
    if fm.horizontalAdvance(text) <= max_width:
        return [text]
    lines: list[str] = []
    cur = ""
    for w in text.split(" "):
        cand = (cur + " " + w).strip() if cur else w
        if cur and fm.horizontalAdvance(cand) > max_width:
            lines.append(cur)
            cur = w
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return lines


def line_height(font) -> float:
    return _fm(font).height() * _LINE_STEP


def node_text_fits(n: NodeGeo, pad_h: float | None = None,
                   pad_v: float | None = None) -> bool:
    """Задача 5 (сессия 15): программная проверка «ни один пиксел
    глифа не касается рамки ноды» – чернильные границы каждой строки
    (ink_rect) с полями помещаются в прямоугольник ноды. Используется
    тестами (программные проверки точнее визуальных оценок)."""
    from ..ui.theme import NODE_INSET as _INSET, PAD_V as _PV
    inset = _INSET if pad_h is None else pad_h
    pv = _PV if pad_v is None else pad_v
    title_font = ui_font(F_TITLE, bold=True)
    w_max = max((ink_rect(title_font, t).width()
                 for t in n.title_lines), default=0.0)
    h = pv + len(n.title_lines) * line_height(title_font)
    styles = n.body_styles or ["meta"] * len(n.body_lines)
    for ln, style in zip(n.body_lines, styles):
        f = body_font(style)
        w_max = max(w_max, ink_rect(f, ln).width())
        h += line_height(f)
    h += pv
    return (w_max + 2 * inset <= n.rect.width() + 0.5
            and h <= n.rect.height() + 0.5)


@dataclass
class NodeGeo:
    node_id: str
    rect: QRectF
    title_lines: list[str]
    body_lines: list[str] = field(default_factory=list)
    body_styles: list[str] = field(default_factory=list)   # meta|muted|total
    q_text: str = ""
    kind: str = "presence"     # presence | gs | iz | fire
    pins_left: bool = True
    pins_right: bool = True
    # Задача 6 (сессия 14): состояние узла для раскраски – "" (обычные
    # цвета класса), "set" (причины ГС/ИЗ заданы – синий), "ok"
    # («Возникновение»: валидатор без замечаний – фиолетовый)
    state: str = ""


@dataclass
class EdgeGeo:
    src: str
    dst: str
    p1: QPointF
    p2: QPointF
    c1: QPointF = None
    c2: QPointF = None
    dashed: bool = False

    def sampled(self) -> list[QPointF]:
        """Полилиния для hit-тестов/аудита (16 сегментов, де Кастельжо)."""
        if self.c1 is None:
            return [self.p1, self.p2]
        pts = [self.p1]
        for i in range(1, CURVE_SAMPLES):
            t = i / CURVE_SAMPLES
            mt = 1.0 - t
            x = (mt ** 3 * self.p1.x() + 3 * mt * mt * t * self.c1.x()
                 + 3 * mt * t * t * self.c2.x() + t ** 3 * self.p2.x())
            y = (mt ** 3 * self.p1.y() + 3 * mt * mt * t * self.c1.y()
                 + 3 * mt * t * t * self.c2.y() + t ** 3 * self.p2.y())
            pts.append(QPointF(x, y))
        pts.append(self.p2)
        return pts


@dataclass
class Annotation:
    """Справочная (титульная) нода дерева (Задача 4, сессия 13): текст
    «владелец · тип сценария» генерируется автоматически (обновляется
    при переименовании/смене типа), плашка компактная и явно вторичная.
    attached – слот привязанной ноды (None – свободная); offset:
    привязанная – от левого-верхнего угла ноды, свободная – от позиции
    по умолчанию (default_pos). default_pos/offset нужны холсту для
    пересчета офсетов при перетаскивании (в файл не пишутся)."""
    tree_id: str
    rect: QRectF
    lines: list[str]
    attached: str | None
    default_pos: QPointF
    offset: list[float]


@dataclass
class LayoutBundle:
    nodes: dict[str, NodeGeo] = field(default_factory=dict)
    edges: list[EdgeGeo] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
    scene_rect: QRectF = field(default_factory=QRectF)

    def width(self) -> float:
        return self.scene_rect.width()


# безьевые рёбра (сессия 9, Задача 5 – сохранены). Задача 5 (сессия 17):
# вылет кривых чуть больше – мягче дуги под крупными нодами
CURVE_MIN_D = 40.0
CURVE_MAX_D = 260.0
CURVE_FRAC = 0.55
FAN_STEP = 12.0
CURVE_SAMPLES = 16


def _plural(n: int, one: str, few: str, many: str) -> str:
    """Русская форма множественного числа: 1 сценарий, 2 сценария,
    5 сценариев (Задача 13)."""
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _fmt_prob(v: float) -> str:
    """0.05 → «0,050» (вероятность присутствия, Задача 15)."""
    return f"{min(1.0, max(0.0, float(v))):.3f}".replace(".", ",")


def _body_spec(tree: TreeModel, node_id: str, kb, ctx) -> list[tuple[str, str]]:
    """Строки тела ноды: (текст, стиль). Задача 13: под заголовком –
    только счётчик и формула (решение заказчика №7); пустые причины –
    серое «не задано» (валидатор напомнит)."""
    if node_id == "gs":
        n = len(tree.gs_causes)
        if n == 0:
            return [("не задано", "muted")]
        return [(f"Всего: {n} "
                 + _plural(n, "разновидность", "разновидности",
                           "разновидностей"), "meta")]
    if node_id == "iz":
        n = len(tree.iz_causes)
        if n == 0:
            return [("не задано", "muted")]
        return [(f"Всего: {n} "
                 + _plural(n, "источник", "источника", "источников"),
                 "meta")]
    if node_id in ("substance", "oxidizer"):
        pres = getattr(tree, node_id)
        return [(f"вероятность присутствия: {_fmt_prob(pres.value)}",
                 "meta")]
    if node_id == "fire":
        n = len(tree.scenarios(kb, ctx))
        return [(f"Всего: {n} "
                 + _plural(n, "сценарий", "сценария", "сценариев"), "meta"),
                (f"ΣQ = {fmt_q(tree.total_q(kb, ctx))} год⁻¹", "total")]
    return []


# ------------------------------ расчёт блока дерева ----------------------
def _make_annotation(tree: TreeModel, text: str, x0: float, tree_w: float,
                     nodes: dict[str, NodeGeo]) -> Annotation:
    """Геометрия справочной ноды (Задача 4, сессия 13): авто-ширина под
    текст (≤2 строк, перенос по целым словам), компактная высота.
    Позиция: привязанная – левый-верх ноды + offset; свободная – над
    деревом по центру (бывшая позиция заголовка) + offset."""
    f = ui_font(F_TITLE)
    budget = ANN_MAX_W - 2 * ANN_INSET
    lines = wrap_words(text, f, budget)
    while len(lines) > 2:            # потолок растет, пока ≤2 строки
        budget += 50.0
        lines = wrap_words(text, f, budget)
    # Задача 5 (сессия 15): ширина плашки – по чернильным границам
    # строк (tightBoundingRect) + 2×ANN_INSET + 2 px запаса
    w = max(ANN_MIN_W,
            min(budget + 2 * ANN_INSET,
                max(ink_rect(f, ln).width() for ln in lines)
                + 2 * ANN_INSET + 2.0))
    h = ANN_PAD_V + len(lines) * line_height(f) + ANN_PAD_V
    # позиция по умолчанию: по центру над деревом (бывший заголовок)
    tree_top = min(n.rect.top() for n in nodes.values())
    default_pos = QPointF(x0 + (tree_w - w) / 2.0, tree_top - h
                          - ANN_SNAP_GAP)
    ann = tree.annotation or {}
    attached = ann.get("attached")
    off = ann.get("offset") or (0.0, 0.0)
    base = (nodes[attached].rect.topLeft()
            if attached in nodes else default_pos)
    rect = QRectF(base.x() + float(off[0]), base.y() + float(off[1]),
                  w, h)
    return Annotation(tree_id=tree.tree_id, rect=rect, lines=lines,
                      attached=attached, default_pos=default_pos,
                      offset=[float(off[0]), float(off[1])])


def _layout_tree(tree: TreeModel, kb, ctx, origin_x: float,
                 owner_title: str) -> tuple[dict[str, NodeGeo], list[EdgeGeo],
                                            Annotation, float]:
    titles = tree.node_titles(kb)
    kinds = {"substance": "presence", "oxidizer": "presence",
             "gs": "gs", "iz": "iz", "fire": "fire"}

    def make_node(nid: str, body: list[tuple[str, str]], kind: str) -> NodeGeo:
        """Задача 5 (сессия 15, ФИНАЛЬНЫЙ фикс обрезки): геометрию текста
        решают МЕТРИКИ, а не константы. Первая стадия – перенос по целым
        словам (wrap_words, бюджет MAX_NODE_W – только подсказка
        переноса); РЕШАЮЩАЯ стадия – точные чернильные границы каждой
        строки (ink_rect → tightBoundingRect, учитывает подстановку
        шрифтов для «10⁻⁶»/«год⁻¹»). Ширина ноды = самая широкая строка
        + 2×NODE_INSET (20 px) + 2 px запаса; высота = 2×PAD_V (24 px) +
        строки по метрикам. Отрисовка – с TextDontClip (render.py):
        надстрочники больше не срезаются рамкой ни на холсте, ни в PDF
        (WYSIWYG: оба потребителя получают одну геометрию)."""
        title_font = ui_font(F_TITLE, bold=True)
        budget = MAX_NODE_W - 2 * NODE_INSET
        title_lines = wrap_words(titles[nid], title_font, budget)
        body_lines: list[str] = []
        body_styles: list[str] = []
        for text, style in body:
            for ln in wrap_words(text, body_font(style), budget):
                body_lines.append(ln)
                body_styles.append(style)
        # РЕШАЮЩАЯ стадия: чернильные границы каждой строки
        w_ink = max((ink_rect(title_font, t).width()
                     for t in title_lines), default=0.0)
        h = PAD_V + len(title_lines) * line_height(title_font)
        for ln, style in zip(body_lines, body_styles):
            f = body_font(style)
            w_ink = max(w_ink, ink_rect(f, ln).width())
            h += line_height(f)
        h += PAD_V
        # ширина: чернила + 2×NODE_INSET (20 px) + 2 px запаса;
        # MIN_NODE_W – нижняя подсказка, потолка нет (длинное слово
        # расширяет ноду – усечений по буквам не бывает)
        w = max(MIN_NODE_W, w_ink + 2 * NODE_INSET + 2.0)
        n = NodeGeo(node_id=f"{tree.tree_id}:{nid}",
                    rect=QRectF(0, 0, w, max(h, 56.0)),
                    title_lines=title_lines, body_lines=body_lines,
                    body_styles=body_styles, kind=kind)
        n.pins_left = kind != "presence"
        n.pins_right = kind != "fire"
        return n

    nodes: dict[str, NodeGeo] = {
        nid: make_node(nid, _body_spec(tree, nid, kb, ctx), kinds[nid])
        for nid in ("substance", "oxidizer", "gs", "iz", "fire")}

    # Задача 6 (сессия 14): состояния узлов. «Задано» – в ноде есть хоть
    # одна причина (условие серого «не задано» наоборот); «Возникновение»
    # OK – валидатор НЕ имеет замечаний к дереву (все issues .ok).
    # check_tree вызывается ОДИН раз на дерево на пересборку (дешево),
    # а не на каждую отрисовку ноды.
    nodes["gs"].state = "set" if tree.gs_causes else ""
    nodes["iz"].state = "set" if tree.iz_causes else ""
    site_kind = ("outdoor" if ctx.owner_kind == "outdoor"
                 else (ctx.site_props.get("site_type") or "area"))
    nodes["fire"].state = ("ok"
                           if all(i.ok for i in
                                  check_tree(tree, kb, ctx, site_kind))
                           else "")

    # колонки: 0 – наличие, 1 – ГС/ИЗ, 2 – возникновение
    col_w = [max(nodes[k].rect.width() for k in ("substance", "oxidizer")),
             max(nodes["gs"].rect.width(), nodes["iz"].rect.width()),
             nodes["fire"].rect.width()]
    x0 = origin_x
    x1 = x0 + col_w[0] + COL_GAP
    x2 = x1 + col_w[1] + COL_GAP

    left_h = nodes["substance"].rect.height() + ROW_GAP \
        + nodes["oxidizer"].rect.height()
    mid_h = nodes["gs"].rect.height() + ROW_GAP + nodes["iz"].rect.height()
    total_h = max(left_h, mid_h, nodes["fire"].rect.height())

    nodes["substance"].rect.moveLeft(x0)
    nodes["substance"].rect.moveTop(total_h / 2 - left_h / 2)
    nodes["oxidizer"].rect.moveLeft(x0)
    nodes["oxidizer"].rect.moveTop(nodes["substance"].rect.bottom() + ROW_GAP)

    nodes["gs"].rect.moveLeft(x1)
    nodes["gs"].rect.moveTop(total_h / 2 - mid_h / 2)
    nodes["iz"].rect.moveLeft(x1)
    nodes["iz"].rect.moveTop(nodes["gs"].rect.bottom() + ROW_GAP)

    nodes["fire"].rect.moveLeft(x2)
    nodes["fire"].rect.moveTop(total_h / 2
                               - nodes["fire"].rect.height() / 2)

    # Задача 11 (сессия 12): ручные смещения нод (перетаскивание ЛКМ) –
    # применяются ВНУТРИ compute_layout: холст и PDF видят одну геометрию
    # (WYSIWYG); рёбра строятся по смещённым прямоугольникам
    offsets = tree.node_offsets or {}
    for slot, node in nodes.items():
        off = offsets.get(slot)
        if off:
            node.rect.translate(float(off[0]), float(off[1]))

    # рёбра: горизонтальные касательные (безье), 2-точечные если прямые
    edges: list[EdgeGeo] = []

    def _edge(a: NodeGeo, b: NodeGeo, fan: int = 0):
        p1 = QPointF(a.rect.right(), a.rect.center().y() + fan * FAN_STEP)
        p2 = QPointF(b.rect.left(), b.rect.center().y() + fan * FAN_STEP)
        gap = p2.x() - p1.x()
        if abs(p1.y() - p2.y()) < 2.0:
            edges.append(EdgeGeo(a.node_id, b.node_id, p1, p2))
            return
        d = min(CURVE_MAX_D, max(CURVE_MIN_D, CURVE_FRAC * gap))
        edges.append(EdgeGeo(
            a.node_id, b.node_id, p1, p2,
            c1=QPointF(p1.x() + d, p1.y()),
            c2=QPointF(p2.x() - d, p2.y())))

    _edge(nodes["substance"], nodes["gs"], fan=-1)
    _edge(nodes["oxidizer"], nodes["gs"], fan=1)
    _edge(nodes["gs"], nodes["fire"], fan=-1)
    _edge(nodes["iz"], nodes["fire"], fan=1)

    # Задача 4 (сессия 13): справочная нода вместо висящего заголовка
    # (Q не дублируется – он в ноде «Возникновение» и в статус-баре)
    st = kb.scenario_type_by_id(tree.scenario_type) or {}
    ann = _make_annotation(
        tree, f"{owner_title} · {st.get('title', tree.scenario_type)}",
        x0, x2 + col_w[2] - x0, nodes)
    return nodes, edges, ann, total_h


def compute_layout(trees: list[TreeModel], kb, ctx_map: dict,
                   owner_titles: dict[str, str] | None = None) -> LayoutBundle:
    """Раскладка списка деревьев (выделенные участок/сценарий/помещение).
    ctx_map: owner_id → CalcContext; owner_titles: owner_id → титул."""
    bundle = LayoutBundle()
    owner_titles = owner_titles or {}
    x = MARGIN
    max_h = 0.0
    for tree in trees:
        ctx = ctx_map.get(tree.owner_id)
        if ctx is None:
            from .model import CalcContext
            ctx = CalcContext()
        nodes, edges, ann, h = _layout_tree(
            tree, kb, ctx, x, owner_titles.get(tree.owner_id, "Дерево"))
        # ключи с префиксом дерева (несколько деревьев не конфликтуют)
        bundle.nodes.update({n.node_id: n for n in nodes.values()})
        bundle.edges.extend(edges)
        bundle.annotations.append(ann)
        x = max(n.rect.right() for n in nodes.values()) + TREE_GAP
        max_h = max(max_h, h)
    if bundle.nodes:
        # габариты сцены – по ФАКТИЧЕСКИМ позициям нод (включая
        # перетащенные, Задача 11) и справочных нод (Задача 4): кламп и
        # вписывание видят выросший лист
        right = max(n.rect.right() for n in bundle.nodes.values())
        bottom = max(n.rect.bottom() for n in bundle.nodes.values())
        top = min(min(n.rect.top() for n in bundle.nodes.values()),
                  min((a.rect.top() for a in bundle.annotations),
                      default=0.0))
        left = min(MARGIN - PIN_R,
                   min((a.rect.left() for a in bundle.annotations),
                       default=MARGIN - PIN_R))
        right = max(right, max((a.rect.right() for a in bundle.annotations),
                               default=right))
        bundle.scene_rect = QRectF(
            left, top - MARGIN / 2,
            right - left + MARGIN / 2 + PIN_R,
            bottom - (top - MARGIN / 2) + MARGIN / 2)
    else:
        bundle.scene_rect = QRectF(0, 0, MARGIN * 4, MARGIN * 2)
    return bundle
