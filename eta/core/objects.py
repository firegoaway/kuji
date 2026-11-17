# -*- coding: utf-8 -*-
"""Иерархия объекта (сессия 10, Задача 2): Территория → Здание →
[Пожарный отсек] → Помещение → Участок; Наружная установка – отдельный
аппарат под Территорией (на уровне Здания).

Оборудования в дереве иерархии больше НЕТ (парадигма сессии 10):
логические деревья событий создаются на Участках и Наружных установках
и живут в проекте отдельно от иерархии (ProjectStore). Тип Участка
выбирается в его свойствах: «участок (м²)» – по умолчанию, «линейный
объект (м)», «аппарат/установка (м³)»; пользователь может переименовать
Участок в «Аппарат 1», «Трубопровод 1» и рассматривать его как аппарат.

Контейнеры (территория/здание/отсек/помещение) сами «не горят» – на
холсте показываются деревья дочерних Участков/установок. Свойства
родителей каскадно применяются к расчету деревьев (молниезащита здания,
вентиляция помещения).
"""

from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

TERRITORY, BUILDING, COMPARTMENT, ROOM, AREA, OUTDOOR = (
    "territory", "building", "compartment", "room", "area", "outdoor")

KIND_TITLES = {
    TERRITORY: "Территория",
    BUILDING: "Здание",
    COMPARTMENT: "Пожарный отсек",
    ROOM: "Помещение",
    AREA: "Участок",
    OUTDOOR: "Наружная установка",
}

# правило вложения: какой родитель допустим для каждого уровня
# (сессия 10: наружная установка – самостоятельный аппарат под
# территорией, на одном уровне со зданием; участки – только в помещениях)
PARENT_RULES: dict[str, set[str]] = {
    TERRITORY: set(),                       # корень иерархии – всегда можно
    BUILDING: {TERRITORY},
    COMPARTMENT: {BUILDING},
    ROOM: {BUILDING, COMPARTMENT},          # в отсек или напрямую в здание
    AREA: {ROOM},
    OUTDOOR: {TERRITORY},
}

CONTAINER_KINDS = set(PARENT_RULES) - {AREA, OUTDOOR}
TOOLBAR_KINDS = (TERRITORY, BUILDING, COMPARTMENT, ROOM, AREA, OUTDOOR)

# владельцы деревьев (на чем создаются логические деревья событий)
TREE_OWNER_KINDS = {AREA, OUTDOOR}

# тип Участка (свойство «Выберите тип», сессия 10 вопрос C):
# площадь м² / линейный объект м / аппарат-установка м³
SITE_TYPES = (
    ("area", "участок (м²)"),
    ("linear", "линейный объект (м)"),
    ("apparatus", "аппарат/установка (м³)"),
)
SITE_FIELD = {
    "area": ("area_m2", "Площадь, м²", 100.0),
    "linear": ("length_m", "Длина, м", 50.0),
    "apparatus": ("volume_m3", "Объем, м³", 10.0),
}

# значения свойств по умолчанию: при создании объекта все поля заполнены
# стандартными значениями (пользователь меняет под свой объект)
DEFAULT_PROPS: dict[str, dict] = {
    TERRITORY: {
        "strike_area_km2": 0.05,     # площадь ударов молнии, км²
    },
    BUILDING: {
        "fire_rating": "II",          # степень огнестойкости
        "floors": 1,                  # этажность
        "area_m2": 1200.0,            # площадь здания F_зд, м² (П1.3/П1.4)
        "p13_type": "p13-multi",      # тип здания по табл. П1.3
        "p14_type": "p14-food",       # тип здания по табл. П1.4
        "bln_S": 100.0,               # размеры для N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶
        "bln_L": 100.0,
        "bln_H": 20.0,
        "lightning_cat": "II",        # категория молниезащиты
        "pedals": {"lightning_prot": False},
    },
    COMPARTMENT: {"fire_resist_walls": "REI 90"},
    ROOM: {
        "area_m2": 100.0,
        "vent_rate": 8.0,             # кратность воздухообмена A, ч⁻¹
        "pedals": {"venting": False},
    },
    AREA: {
        "site_type": "area",          # участок м² | линейный объект м | аппарат м³
        "area_m2": 100.0,
        "length_m": 50.0,
        "volume_m3": 10.0,
        "pedals": {},
    },
    OUTDOOR: {
        "site_type": "area",           # Задача 6 (сессия 15): тип значения
        "area_m2": 400.0,              # площадь установки, м² (для ТГМ)
        "length_m": 50.0,              # линейный объект, м
        "volume_m3": 10.0,             # аппарат/установка, м³
        "p13_type": "p13-multi",       # тип по табл. П1.3/П1.4
        "p14_type": "p14-other",
        "lightning_cat": "II",
        "pedals": {"lightning_prot": False},
    },
}


def effective_site_type(node: ObjNode | None) -> str:
    """Тип места, где висит дерево: участок → его site_type,
    наружная установка → «outdoor»."""
    if node is None:
        return "area"
    if node.kind == OUTDOOR:
        return "outdoor"
    return node.props.get("site_type", "area")


def tgm_levels(node: ObjNode) -> list[ObjNode]:
    """Задача 1 (сессия 15, LOCKED вариант А): уровни каскада ТГМ – от
    ближнего к дальнему:

        участок (ЛЮБОГО типа: значение уровня – по типу участка,
        см. model.tgm_level_value) → помещение → здание;

    наружная установка – сама себе уровень (Задача 6 – тоже по типу).
    Явность значения = наличие ключа в props уровня: цепочка строится
    по дереву объектов, а не по слитому словарю effective_properties
    (там невидно, какой уровень что задал)."""
    if node.kind == OUTDOOR:
        return [node]
    out: list[ObjNode] = []
    if node.kind == AREA:
        out.append(node)          # участник каскада при ЛЮБОМ site_type
    room = node.nearest(ROOM)
    if room is not None and room not in out:
        out.append(room)
    bld = node.nearest(BUILDING)
    if bld is not None and bld not in out:
        out.append(bld)
    return out


class ObjNode:
    """Узел иерархии объекта."""

    def __init__(self, kind: str, title: str = "", oid: str | None = None):
        self.id: str = oid or uuid.uuid4().hex[:10]
        self.kind: str = kind
        self.title: str = title or KIND_TITLES.get(kind, kind)
        # в props хранятся ТОЛЬКО явно заданные значения (каскад
        # effective_properties игнорирует отсутствующие; умолчания –
        # DEFAULT_PROPS, их подставляют редакторы)
        self.props: dict = {}
        self.parent: "ObjNode | None" = None
        self.children: list["ObjNode"] = []

    # ---------- служебное ----------
    def walk(self):
        yield self
        for ch in self.children:
            yield from ch.walk()

    def ancestors(self) -> list["ObjNode"]:
        out, cur = [], self.parent
        while cur is not None:
            out.append(cur)
            cur = cur.parent
        return out[::-1]

    def is_descendant_of(self, other: "ObjNode") -> bool:
        cur = self.parent
        while cur is not None:
            if cur is other:
                return True
            cur = cur.parent
        return False

    def path_title(self) -> str:
        parts = [a.title for a in self.ancestors()] + [self.title]
        return " → ".join(parts)

    def nearest(self, kind: str) -> "ObjNode | None":
        """Ближайший предок заданного типа (включая сам узел)."""
        cur: ObjNode | None = self
        while cur is not None:
            if cur.kind == kind:
                return cur
            cur = cur.parent
        return None


def add_denied_message(kind: str) -> str:
    """Задача 4 (сессия 17): текст информационного окна «нельзя добавить»
    (единый источник для add_child и вставки буфера обмена иерархии;
    подсказки учитывают и правило «соседа»)."""
    need = {BUILDING: "территорию или здание",
            COMPARTMENT: "здание или пожарный отсек",
            ROOM: "здание, отсек или помещение",
            AREA: "помещение или участок", OUTDOOR: "территорию",
            TERRITORY: "корень иерархии – территория создается"
                       " всегда в корне, независимо от выделения"
            }.get(kind, "родителя")
    return f"«{KIND_TITLES[kind]}» нельзя добавить" \
           f" в выбранный элемент – выделите {need}"


class ObjectTree(QObject):
    """Иерархия объекта проекта (Территория → … → Участок/Установка)."""

    changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.territories: list[ObjNode] = []

    # ---------- обход ----------
    def all_nodes(self) -> list[ObjNode]:
        out: list[ObjNode] = []
        for t in self.territories:
            out.extend(t.walk())
        return out

    def by_id(self, oid: str) -> ObjNode | None:
        for n in self.all_nodes():
            if n.id == oid:
                return n
        return None

    def tree_owners(self) -> list[ObjNode]:
        """Все владельцы деревьев: участки и наружные установки."""
        return [n for n in self.all_nodes() if n.kind in TREE_OWNER_KINDS]

    def owners_in(self, node: ObjNode | None) -> list[ObjNode]:
        """Владельцы деревьев в поддереве узла (None – весь проект)."""
        if node is None:
            return self.tree_owners()
        if node.kind in TREE_OWNER_KINDS:
            return [node]
        return [n for n in node.walk() if n.kind in TREE_OWNER_KINDS]

    def buttons_toolbar_kinds(self) -> tuple[str, ...]:
        """Порядок уровней для панели инструментов."""
        return TOOLBAR_KINDS

    def _next_title(self, kind: str) -> str:
        n = sum(1 for x in self.all_nodes() if x.kind == kind)
        return f"{KIND_TITLES[kind]} {n + 1}"

    # ---------- изменение ----------
    def can_add(self, kind: str, parent: ObjNode | None) -> bool:
        """Задача 1 (сессия 14): ПУСТОЕ множество допустимых родителей
        означает «родителя нет вообще» – территория создается ТОЛЬКО в
        корне иерархии. Раньше пустое множество трактовалось как «любой
        родитель» – территории вкладывались в здания/участки/помещения
        (скриншоты №1/№3/№4 первой партии)."""
        if kind not in PARENT_RULES:
            return False
        allowed = PARENT_RULES[kind]
        if not allowed:
            return parent is None            # территория – только корень
        return parent is not None and parent.kind in allowed

    def add_child(self, kind: str, parent: ObjNode | None,
                  title: str | None = None) -> ObjNode:
        if not self.can_add(kind, parent):
            # Задача 4 (сессии 12/17): текст – из единого источника
            raise ValueError(add_denied_message(kind))
        node = ObjNode(kind, title or self._next_title(kind))
        if parent is None:
            self.territories.append(node)
        else:
            node.parent = parent
            parent.children.append(node)
        self.changed.emit()
        return node

    def remove_subtree(self, node: ObjNode) -> None:
        if node.parent is not None:
            node.parent.children.remove(node)
        elif node in self.territories:
            self.territories.remove(node)
        self.changed.emit()

    def move_subtree(self, node: ObjNode, new_parent: ObjNode | None,
                     ) -> None:
        """Задача 3.4 (сессия 15, LOCKED): перенос ПОДдерева целиком под
        нового родителя (drag-and-drop в иерархии). Правила PARENT_RULES
        проверяет вызывающий код (can_add); здесь – механика: дети,
        деревья сценариев (owner_id не меняется), их причины и
        зависимости, свернутость и смещения нод переезжают вместе."""
        if new_parent is node.parent:
            return
        if node.parent is not None:
            node.parent.children.remove(node)
        elif node in self.territories:
            self.territories.remove(node)
        node.parent = new_parent
        if new_parent is None:
            self.territories.append(node)
        else:
            new_parent.children.append(node)
        self.changed.emit()

    def rename(self, node: ObjNode, title: str) -> None:
        node.title = title.strip() or node.title
        self.changed.emit()

    def set_props(self, node: ObjNode, props: dict) -> None:
        node.props.update(props)
        self.changed.emit()

    def clear(self) -> None:
        self.territories = []
        self.changed.emit()

    # ---------- каскад свойств ----------
    def effective_properties(self, node: ObjNode) -> dict:
        """Свойства узла с каскадным наследованием вниз: значение потомка
        имеет приоритет над родительским (переопределение локально)."""
        chain = node.ancestors() + [node]     # от территории к узлу
        out: dict = {}
        for anc in chain:
            for k, v in anc.props.items():
                if v is None:
                    continue
                out[k] = v                   # ближе к узлу – важнее
        return out

    def effective_pedals(self, node: ObjNode) -> dict:
        """Эффективные педальки: от корня к узлу, побеждает ближайшее
        ЯВНО заданное значение; не задано нигде – выключено."""
        out: dict = {}
        for anc in node.ancestors() + [node]:
            out.update(anc.props.get("pedals", {}) or {})
        return out

    # ---------- сериализация ----------
    def to_dict(self) -> list[dict]:
        def _node(n: ObjNode) -> dict:
            d: dict = {"id": n.id, "kind": n.kind, "title": n.title,
                       "props": n.props}
            if n.children:
                d["children"] = [_node(c) for c in n.children]
            return d
        return [_node(t) for t in self.territories]

    def load_from_dict(self, data: list[dict]) -> dict | None:
        """Загрузить иерархию формата 5. Задача 1.2 (сессия 14, LOCKED
        вариант (а)): поврежденные файлы автоматически выправляются –

        * территории НЕ в корне поднимаются в корень ЦЕЛИКОМ со своими
          поддеревьями (относительная структура детей сохраняется);
        * прочие недопустимые размещения переносятся к БЛИЖАЙШЕМУ
          допустимому предку; если в цепочке его нет – к первой
          территории корня (а если и её нет – создается «Территория 1»;
          консервативно: экзотические размещения могут остаться
          формально недопустимыми, но ни один объект не теряется);
        * id всех узлов сохраняются – деревья сценариев (owner_id)
          остаются при своих владельцах.

        Возвращает отчет ремонта {"lifted_territories": N,
        "moved_nodes": M} либо None, если исправлять было нечего."""
        def _node(d: dict, parent: ObjNode | None) -> ObjNode:
            kind = d.get("kind", TERRITORY)
            n = ObjNode(kind, d.get("title", ""), d.get("id"))
            n.props.update(d.get("props", {}) or {})
            n.parent = parent
            n.children = [_node(c, n) for c in d.get("children", [])]
            return n
        self.territories = [_node(t, None) for t in data]
        repair = self._repair_structure()
        self.changed.emit()
        return repair

    def _repair_structure(self) -> dict:
        """Механика ремонта load_from_dict (см. докстринг выше).
        Возвращает {"lifted_territories": N, "moved_nodes": M}."""
        lifted = 0
        moved = 0
        # (1) вложенные территории → корень, с поддеревом
        nested = [n for t in self.territories for n in t.walk()
                  if n.kind == TERRITORY and n.parent is not None]
        for n in nested:
            n.parent.children.remove(n)
            n.parent = None
            self.territories.append(n)
            lifted += 1
            moved += 1

        # (2) недопустимые размещения → ближайший допустимый предок
        def _ok(n: ObjNode) -> bool:
            if n.parent is None:
                return n.kind == TERRITORY      # корень – только территории
            return n.parent.kind in PARENT_RULES.get(n.kind, set())

        broken = [n for n in self.all_nodes() if not _ok(n)]
        for n in broken:
            allowed = PARENT_RULES.get(n.kind, set())
            cand = next((a for a in n.ancestors()
                         if a.kind in allowed), None)
            if cand is None:
                # допустимого предка в цепочке нет – первая территория,
                # НЕ являющаяся самим узлом или его потомком (иначе цикл);
                # при полном отсутствии – новая «Территория 1»
                safe = [t for t in self.territories
                        if t is not n and not t.is_descendant_of(n)]
                if safe:
                    cand = safe[0]
                else:
                    cand = ObjNode(TERRITORY, "Территория 1")
                    self.territories.append(cand)
            if n.parent is not None:
                n.parent.children.remove(n)
            elif n in self.territories:
                self.territories.remove(n)
            n.parent = cand
            cand.children.append(n)
            moved += 1
        return {"lifted_territories": lifted, "moved_nodes": moved}
