# -*- coding: utf-8 -*-
"""Математическое ядро: модель логического дерева событий (сессия 10).

Парадигма «пяти инвариантных типов сценариев» (ТГМ, ГГ, ГЖ, ЛВЖ, Пыль).
Структура дерева фиксирована и НЕ зависит от типа оборудования:

    [Наличие вещества] ──┐
                         ├──> [Образование горючей среды (ГС)] ──┐
    [Наличие окислителя]─┘                                     ├──>
                                     [Появление ИЗ (ИЗ)] ──────┘
                                     │            │        [Возникновение
                                  (причины ИЗ)  (причины ГС)   пожара]

Разновидности причин («разгерметизация аппарата, отверстие 12,5 мм»,
«отказ кабельных линий»…) выбираются в свойствах нод ГС/ИЗ из базы
знаний; на холст события свободно НЕ размещаются.

Расчет (подтвержден заказчиком, сессия 10):
    Q_сценария = Q_наличия вещества × Q_наличия окислителя
                 × Q_разновидности ГС × Q_разновидности ИЗ × P_типа горения
    Q_участок,k = Σ Q_сценариев × K_σ          (K_σ – коэффициент безопасности)

Множители:
  * ТГМ: Q_ГС = a₁·F_зд (табл. П1.3) либо a·F_зд^b (табл. П1.4 при
    F_зд > 10 000 м²) – берется из свойств здания/наружной установки;
  * ГГ/ГЖ/ЛВЖ/Пыль: Q_ГС = частота разгерметизации (П1.1) либо удельная
    частота утечки трубопровода × длину прокладки (П1.2); сессия 17
    (LOCKED, упрощённое правило заказчика): П1.1/direct умножаются на
    значение СОБСТВЕННОГО типа владельца (F/L/V – тот же резолвер,
    что у ТГМ/П1.2; двойного умножения с П1.2/П1.3 нет);
  * Q_ИЗ = 1 − e^(−λ) (табл. 9 прил. 3 ГОСТ 12.1.004-91); удар молнии –
    N_у.м·(1 − η) по свойствам здания; выход нагретого вещества – P = 1;
  * P_типа горения – табл. П2.1 по массовому расходу (<1 / 1–50 / >50 кг/с /
    полный разрыв) и среде (газ / двухфазная / жидкость); для ТГМ P = 1
    (пожар по поверхности); пыль – дефлаграция/детонация с P = 1;
  * «Огненный шар» – переключатель ноды «Возникновение пожара»,
    частота внешнего воздействия 2,5·10⁻⁵ год⁻¹ на аппарат (прил. № 1 п. 5).

Программа проверяет только МАТЕМАТИЧЕСКОЕ СУЩЕСТВОВАНИЕ комбинации
(все диапазоны расхода умножаются на каждую разгерметизацию);
физическую правдоподобность оценm инженер во внешнем расчете.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field

from .numfmt import fmt_num
from .objects import SITE_FIELD

SCENARIO_TYPES = ("tgm", "gg", "gzh", "lvzh", "dust")
FLOWS = ("small", "mid", "big", "rupt")
TGM_AREA_LIMIT_M2 = 10_000.0        # выше – формула a·F^b (табл. П1.4)


def tgm_level_value(props: dict | None) -> float | None:
    """Задача 1 (сессия 15, LOCKED вариант А): значение уровня каскада
    ТГМ по его СОБСТВЕННЫМ props. Уровень участка/установки (в props
    есть site_type) отдает значение СВОЕГО типа: «участок (м²)» →
    area_m2, «линейный объект (м)» → length_m, «аппарат/установка
    (м³)» → volume_m3; помещение и здание – площадь area_m2. Размерность
    принимается заказчиком сознательно (a₁ × значение). Явность = наличие
    ключа; None – уровень ничего не задал (каскад идет дальше)."""
    p = props or {}
    st = p.get("site_type")
    key = SITE_FIELD.get(st, SITE_FIELD["area"])[0] if st is not None \
        else "area_m2"
    v = p.get(key)
    return float(v) if v else None

# соответствие «среда × колонка П2.1 → тип горения»
_MEDIUM_FIRE = {
    "gas":      {"instant": "ft-jet", "delayed": "ft-flash",
                 "pressure": "ft-vce"},
    "twophase": {"instant": "ft-jet", "delayed": "ft-flash",
                 "pressure": "ft-vce"},
    "liquid":   {"instant": "ft-pool", "delayed": "ft-pool",
                 "pressure": "ft-vce"},
}
_P21_KEYS = ("instant", "delayed", "pressure")


# ============================ наличие вещества/окислителя =================
@dataclass
class Presence:
    """Вероятность присутствия (безразмерная, 0–1): доля года, в течение
    которой вещество/окислитель находится на рассматриваемом участке.
    Значение вводит пользователь; в расчете – множитель Q = значение.

    Сессия 12, Задача 15: режимы «время/частота» упразднены; при
    загрузке старых проектов (формат 5) выполняется разовая миграция:
    «время» – доля года переносится как есть, «частота» f – пересчет
    1 − e^(−f). Запись всегда в новом однокомпонентном виде."""
    value: float = 1.0

    def q(self) -> float:
        return min(1.0, max(0.0, float(self.value)))

    def to_dict(self) -> dict:
        return {"value": float(self.value)}

    @classmethod
    def from_dict(cls, d: dict) -> "Presence":
        v = float(d.get("value", 1.0))
        if d.get("mode") == "freq":
            v = 1.0 - math.exp(-max(0.0, v))
        return cls(value=v)


def _new_cid() -> str:
    return uuid.uuid4().hex[:10]


@dataclass
class GSCause:
    """Причина в ноде ГС: ссылка на разновидность базы данных.
    Для трубопроводных разновидностей (П1.2) – длина прокладки, м.
    Задача 8 (сессия 15): flow – ДИАПАЗОН массового расхода истечения
    записи («small|mid|big|rupt» или None): развернутая строка выбора
    порождает сценарии ТОЛЬКО своего диапазона; None – все диапазоны
    (совместимость со старыми проектами и безрасходными записями).
    Задача 3.3 (сессия 15): cid – стабильный идентификатор записи
    внутри списка (для ссылок parent); parent – cid РОДИТЕЛЬСКОЙ
    причины того же списка (перетащена под неё в иерархии): зависимая
    ветвь И-гейта, Q = Q(родитель) × Q(потомок), собственной строки
    не дает. None – независимая причина (верхний уровень)."""
    ref: str
    len_m: float | None = None
    flow: str | None = None
    cid: str = ""
    parent: str | None = None

    def __post_init__(self):
        if not self.cid:
            self.cid = _new_cid()

    def to_dict(self) -> dict:
        d: dict = {"ref": self.ref, "cid": self.cid}
        if self.len_m is not None:
            d["len_m"] = float(self.len_m)
        if self.flow is not None:
            d["flow"] = self.flow
        if self.parent is not None:
            d["parent"] = self.parent
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "GSCause":
        flow = d.get("flow")
        if flow not in FLOWS:
            flow = None
        return cls(ref=d["ref"],
                   len_m=(float(d["len_m"]) if d.get("len_m") is not None
                          else None),
                   flow=flow,
                   cid=str(d.get("cid") or "") or _new_cid(),
                   parent=d.get("parent"))


@dataclass
class IZCause:
    """Причина в ноде ИЗ: ссылка на разновидность базы данных.
    Задача 3.3 (сессия 15): cid/parent – см. GSCause (зависимые ветви
    И-гейта: Q = Q(родитель) × Q(потомок))."""
    ref: str
    cid: str = ""
    parent: str | None = None

    def __post_init__(self):
        if not self.cid:
            self.cid = _new_cid()

    def to_dict(self) -> dict:
        d: dict = {"ref": self.ref, "cid": self.cid}
        if self.parent is not None:
            d["parent"] = self.parent
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "IZCause":
        return cls(ref=d["ref"],
                   cid=str(d.get("cid") or "") or _new_cid(),
                   parent=d.get("parent"))


def cause_paths(causes: list) -> list[list]:
    """Задача 3.3 (сессия 15): лес причин → пути «корень → лист».
    Перетащенная под родителя причина становится зависимой ветвью
    И-гейта: СОБСТВЕННОЙ строки не дает, ее множитель входит в
    произведение пути. Каждый путь корень→лист дает ОДНУ строку с
    произведением множителей вдоль пути (цепи любой глубины; ветвление
    – несколько путей). Циклы (внешние правки файлов) разрываются:
    узел цикла считается корнем."""
    by_cid = {c.cid: c for c in causes}
    children: dict[str, list] = {}
    roots: list = []
    for c in causes:
        p = c.parent if c.parent in by_cid else None
        if p is None:
            roots.append(c)
        else:
            children.setdefault(p, []).append(c)
    out: list[list] = []
    visited: set[str] = set()

    def rec(path: list) -> None:
        visited.add(path[-1].cid)
        kids = children.get(path[-1].cid, [])
        if not kids:
            out.append(path)
            return
        on_path = {n.cid for n in path}
        for k in kids:
            if k.cid in on_path:      # цикл – путь не продолжаем
                continue
            rec(path + [k])

    for r in roots:
        rec([r])
    # разрыв циклов: не достигнутые с корней узлы – самостоятельные пути
    for c in causes:
        if c.cid not in visited:
            out.append([c])
    return out


def _join_pieces(pieces: list[str]) -> str:
    """Произведение подставленных скобок формулы вдоль цепи (Задача 4:
    «(a)·(b)» внутри одной скобки). Снимается РОВНО один уровень скобок
    (strip("()") съедал бы вложенную закрывающую «(1−exp(−…))»)."""
    def _unwrap(p: str) -> str:
        if p.startswith("(") and p.endswith(")"):
            return p[1:-1]
        return p
    return "(" + "·".join(_unwrap(p) for p in pieces) + ")"


@dataclass
class ScenarioRow:
    """Строка-сценарий: одна комбинация «ГС × расход × тип горения × ИЗ»."""
    name: str
    gs_ref: str
    iz_ref: str | None
    flow: str | None = None          # small|mid|big|rupt|None
    fire_type: str | None = None
    q: float = 0.0
    formula: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "gs": self.gs_ref, "iz": self.iz_ref,
                "flow": self.flow, "fire_type": self.fire_type,
                "q": self.q, "formula": self.formula}


# ============================ контекст расчета ============================
@dataclass
class CalcContext:
    """Свойства объектов иерархии, влияющие на дерево: здание/установка
    (площадь, тип по П1.3/П1.4, молниезащита), помещение (вентиляция),
    участок (тип: м²/м/м³ и значения).

    Задача 5 (сессия 14, LOCKED вариант (а)): tgm_chain – список
    СОБСТВЕННЫХ props уровней каскада ТГМ от ближнего к дальнему
    (участок → помещение → здание; наружная установка – [она сама]).
    Строит MainWindow из дерева объектов (objects.tgm_levels): явность
    значения = наличие ключа в props уровня. None – совместимость со
    старыми вызовами через merged building_props."""
    building_props: dict = field(default_factory=dict)
    room_props: dict = field(default_factory=dict)
    site_props: dict = field(default_factory=dict)
    owner_kind: str = "area"         # area | outdoor
    tgm_chain: list[dict] | None = None

    # ---------- множитель ТГМ: a₁·F (П1.3) или a·F^b (П1.4, F > 10 000 м²)
    def _tgm_resolve(self, kb) -> tuple[float, str, str, str]:
        """Задача 1 + Задача 4 (сессия 15): разрешение множителя ТГМ.
        Возвращает (значение, ПОДСТАНОВЛЕННАЯ скобка формулы, таблица,
        код ошибки). Скобка – только числа («(9·10⁻⁵·2960,77)», для П1.4
        «(0,0011·25000^0,6)»); ссылка на таблицу («П1.3»/«П1.4») –
        отдельно: внутрь формул не попадает, нужна блоку источников
        PDF-отчета. Коды ошибок: value|type|''."""
        levels = self.tgm_chain if self.tgm_chain is not None \
            else [self.building_props]
        f = None
        for props in levels:
            v = tgm_level_value(props or {})
            if v is not None:
                f = v
                break
        if f is None or f <= 0.0:
            return 0.0, "", "", "value"
        big = f > TGM_AREA_LIMIT_M2
        table = "П1.4" if big else "П1.3"
        key = "p14_type" if big else "p13_type"
        type_id = ""
        for props in levels:
            if props.get(key):
                type_id = props.get(key)
                break
        if big:
            row = kb.p14_by_id(type_id) or {}
            a, b = float(row.get("a", 0.0)), float(row.get("b", 0.0))
            if a <= 0:
                return 0.0, "", table, "type"
            return a * f ** b, \
                f"({fmt_num(a)}·{fmt_num(f)}^{fmt_num(b)})", table, ""
        row = kb.p13_by_id(type_id) or {}
        a1 = float(row.get("a1", 0.0))
        if a1 <= 0:
            return 0.0, "", table, "type"
        return a1 * f, f"({fmt_num(a1)}·{fmt_num(f)})", table, ""

    def tgm_multiplier(self, kb) -> tuple[float, str]:
        """Множитель ТГМ: (значение, скобка формулы). Ошибки – 0 с
        пояснением (для валидатора); успех – полностью подставленные
        числа в инженерной записи (Задача 4, сессия 15)."""
        v, piece, table, err = self._tgm_resolve(kb)
        if err == "value":
            return 0.0, "не задано значение (участок/помещение/здание)"
        if err == "type":
            return 0.0, f"не выбрано функциональное назначение ({table})"
        return v, piece

    def tgm_table(self, kb) -> str:
        """Задача 4.2 (сессия 15): какая таблица (П1.3/П1.4) дала
        множитель – для блока источников отчетного листа PDF."""
        v, _piece, table, _err = self._tgm_resolve(kb)
        return table if v > 0 else ""

    # ---------- ИЗ-молния по свойствам здания/установки
    def lightning_q(self) -> float:
        """Q_молнии = N_у.м · (1 − η): N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶ при
        заданных размерах, иначе N_у.м = F·n_у (площадь, км²)."""
        p = self.building_props
        if p.get("pedals", {}).get("lightning_prot"):
            eta = {"I": 0.98, "II": 0.95, "III": 0.90, "IV": 0.80}.get(
                p.get("lightning_cat", "II"), 0.95)
        else:
            eta = 0.0
        s = float(p.get("bln_S", 0.0) or 0.0)
        l = float(p.get("bln_L", 0.0) or 0.0)
        h = float(p.get("bln_H", 0.0) or 0.0)
        n_y = float(p.get("n_y", 6.0) or 6.0)
        if s > 0 and l > 0 and h > 0:
            n_um = (s + 6 * h) * (l + 6 * h) * n_y * 1e-6
        else:
            n_um = float(p.get("area_m2", 0.0) or 0.0) * 1e-6 * n_y
        return n_um * (1.0 - eta)

    # ---------- вентиляция помещения (P_ост = 1/(A·T + 1))
    def vent_k(self) -> float:
        p = self.room_props
        if not p.get("pedals", {}).get("venting"):
            return 1.0
        a = float(p.get("vent_rate", 8.0) or 8.0)
        return 1.0 / (a / 12.0 + 1.0)

    # ---------- множитель трубопроводных разновидностей (П1.2)
    def p12_value(self, explicit: float | None) -> tuple[float, str]:
        """Сессия 14/1 (решение заказчика) + Задача 6 (сессия 15):
        множитель П1.2 (удельная частота × значение по ТИПУ места).
        Явное значение на ноде ГС (len_m) важнее всего; иначе значение
        участка/установки по его типу: «участок (м²)» → ПЛОЩАДЬ (м²),
        линейный объект → длина (м), аппарат/установка → объем (м³).
        Возвращает (значение, единица для пояснения в формуле)."""
        if explicit is not None:
            return float(explicit), "м"
        sp = self.site_props or {}
        st = sp.get("site_type", "area")
        key, _lab, default = SITE_FIELD.get(st, SITE_FIELD["area"])
        v = sp.get(key)
        unit = {"area": "м²", "linear": "м", "apparatus": "м³"}[st]
        return (float(v) if v is not None else default), unit

    # ---------- множитель причин П1.1/direct (сессия 17, LOCKED) ----------
    def p11_site_value(self) -> float | None:
        """Задача 2 (сессия 17, LOCKED – упрощённое правило заказчика):
        значение СОБСТВЕННОГО типа владельца дерева (участок/наружная
        установка): F для «участок (м²)», L для «линейный объект»,
        V для «аппарат/установка» (тот же резолвер по типу, что у
        ТГМ/П1.2). Не задано → None → множитель 1 (скобка формулы без
        множителя). Осознанное отклонение от «на единицу N» табл. П1.1:
        заказчик подтвердил упрощённое правило – не пересматривать."""
        return tgm_level_value(self.site_props)

    # ---------- универсальные меры на помещении/здании (Задача 0) --------
    def universal_k(self, kb) -> float:
        """Произведение множителей k новых защитных средств (type "k"),
        чьи переключатели включены на ПОМЕЩЕНИИ или ЗДАНИИ (носители
        room/building). Каскад свойств: effective-props помещения уже
        включают педали здания – защита от двойного учета по seen."""
        k = 1.0
        seen: set[str] = set()
        mods = kb.property_modifiers if kb is not None else []
        for props in (self.room_props, self.building_props):
            pedals = (props or {}).get("pedals") or {}
            for m in mods:
                ped = m.get("pedal")
                if m.get("type") == "k" and ped and pedals.get(ped) \
                        and ped not in seen:
                    k *= float(m.get("k", 1.0))
                    seen.add(ped)
        return k


# ============================ модель дерева ==============================
class TreeModel:
    """Логическое дерево событий одного типа на одном участке/установке."""

    def __init__(self, scenario_type: str, owner_id: str, title: str = "",
                 tree_id: str | None = None):
        assert scenario_type in SCENARIO_TYPES, scenario_type
        self.tree_id = tree_id or uuid.uuid4().hex[:10]
        self.scenario_type = scenario_type
        self.owner_id = owner_id
        self.title = title
        self.substance = Presence()
        self.oxidizer = Presence()
        self.gs_causes: list[GSCause] = []
        self.iz_causes: list[IZCause] = []
        # педали-переключатели на нодах (словари «ключ → значение»)
        self.gs_pedals: dict = {}
        self.iz_pedals: dict = {}
        self.k_sigma: float = 1.0
        self.fireball: bool = False
        # Задача 11 (сессия 12): визуальные смещения нод относительно
        # автоматической раскладки после перетаскивания ЛКМ; формат 5,
        # поле опциональное: нет/пусто = авторазметка. Ключи – слоты нод
        # (substance/oxidizer/gs/iz/fire), значения [dx, dy]
        self.node_offsets: dict[str, list[float]] | None = None
        # Задача 4 (сессия 13): справочная (титульная) нода дерева взамен
        # «висящего» заголовка. attached – слот ноды, к которой нода
        # привязана (None – свободная), offset [dx, dy]: для привязанной –
        # относительно ЛЕВОГО ВЕРХНЕГО угла ноды, для свободной –
        # относительно позиции по умолчанию (над деревом). None = свежее
        # дерево без правок (свободная нода в позиции по умолчанию).
        # Текст генерируется автоматически (владелец · тип сценария) и
        # НЕ хранится. Формат 5 – поле опциональное.
        self.annotation: dict | None = None

    # ---------- граф для холста/PDF (фиксированная структура) ----------
    def node_titles(self, kb) -> dict[str, str]:
        st = kb.scenario_type_by_id(self.scenario_type) or {}
        subst = st.get("substance", "")
        return {
            "substance": f"Наличие вещества ({subst})",
            "oxidizer": "Наличие окислителя (ОК)",
            "gs": "Образование горючей среды (ГС)",
            "iz": "Появление источника зажигания (ИЗ)",
            "fire": st.get("fire_node_title", "Возникновение пожара"),
        }

    EDGES = (("substance", "gs"), ("oxidizer", "gs"),
             ("gs", "fire"), ("iz", "fire"))

    # ---------- множители педалей ----------
    def _gs_k(self, kb=None) -> float:
        """Произведение поправочных коэффициентов ноды ГС
        (износ, герметичность, ПАЗ/резервирование, ТО, дренаж,
        датчики утечки, вентиляция помещения).

        Задача 0 (сессия 13): числа берутся ИЗ ЗАПИСИ базы данных
        (modifier_by_pedal) – правка коэффициента существующей меры в
        окне БД влияет на расчет; плюс универсальный множитель k для
        новых мер (type "k") на их ноде-носителе."""
        p = self.gs_pedals

        def m(key: str) -> dict:
            rec = kb.modifier_by_pedal(key) if kb is not None else None
            return rec or {}

        k = 1.0
        if p.get("wear"):
            k *= float(p.get("wear_k", m("wear").get("k", 2.0)))
        if p.get("hermetic"):
            k *= float(m("hermetic").get("k", 0.5))
        if p.get("sil_paz"):
            pfd = float(p.get("sil_pfd", 1e-2))
            v = p.get("voting", "1oo1")
            if v == "1oo2":
                pfd = pfd * pfd
            elif v == "2oo3":
                pfd = 3 * pfd * pfd - 2 * pfd ** 3
            k *= max(pfd, 1e-9)
        if p.get("t_test"):
            lam = float(p.get("lambda_du_h",
                              m("t_test").get("lambda_du_h", 1e-6)))
            t_h = float(p.get("t_test_mo", 12)) * 730.0   # мес → ч
            k *= max(1e-9, lam * t_h / 2.0)
        if p.get("drain"):
            k *= 1.0 - float(m("drain").get("p_success", 0.95))
        if p.get("leak_detectors"):
            k *= 1.0 - float(m("leak_detectors")
                             .get("p_success", 0.8))
        # универсальный множитель новых защитных средств (type "k")
        if kb is not None:
            for mod in kb.property_modifiers:
                ped = mod.get("pedal")
                if mod.get("type") == "k" and ped and p.get(ped):
                    k *= float(mod.get("k", 1.0))
        return k

    def _iz_k(self, rec: dict, kb=None) -> float:
        """Коэффициенты ноды ИЗ: контроль t°/вибрации; взрывозащищённое
        исполнение обнуляет электрические источники зажигания. Числа –
        из записи БД (Задача 0, сессия 13); универсальный k – для новых
        мер на ноде ИЗ."""
        p = self.iz_pedals

        def m(key: str) -> dict:
            mod = kb.modifier_by_pedal(key) if kb is not None else None
            return mod or {}

        k = 1.0
        if p.get("vibro_control"):
            k *= float(m("vibro_control").get("k", 0.7))
        if p.get("exproof") and rec.get("electrical"):
            k = 0.0
        if kb is not None:
            for mod in kb.property_modifiers:
                ped = mod.get("pedal")
                if mod.get("type") == "k" and ped and p.get(ped):
                    k *= float(mod.get("k", 1.0))
        return k

    def _medium(self, kb) -> str:
        st = kb.scenario_type_by_id(self.scenario_type) or {}
        env = self.gs_pedals.get("env_cat")
        return env or st.get("medium") or "gas"

    # ---------- частоты ----------
    def _q_gs(self, cause: GSCause, kb, ctx: CalcContext) -> tuple[float, str]:
        """Частота причины ГС: (значение, ПОДСТАНОВЛЕННАЯ скобка формулы
        – только числа, Задача 4 сессии 15)."""
        g = kb.gs_by_id(cause.ref) or {}
        kind = g.get("kind", "p11")
        if kind == "p13":
            v, piece = ctx.tgm_multiplier(kb)
            return v * self._gs_k(kb) * ctx.universal_k(kb) \
                * ctx.vent_k(), piece
        if kind == "p12":
            length, _unit = ctx.p12_value(cause.len_m)
            q = float(g.get("q_per_m", 0.0)) * length
            return q * self._gs_k(kb) * ctx.universal_k(kb) \
                * ctx.vent_k(), \
                f"({fmt_num(g.get('q_per_m', 0))}·{fmt_num(length)})"
        # Задача 2 (сессия 17, LOCKED): причины П1.1/direct (включая их
        # расходные варианты) умножаются на значение СОБСТВЕННОГО типа
        # владельца (F/L/V); не задано → множитель 1, скобка без
        # множителя. П1.2 и П1.3/П1.4 НЕ трогаются – двойного
        # умножения нет (проверяется тестом)
        q = float(g.get("q", 0.0))
        site_v = ctx.p11_site_value()
        if site_v is not None:
            return q * site_v * self._gs_k(kb) * ctx.universal_k(kb) \
                * ctx.vent_k(), \
                f"({fmt_num(q)}·{fmt_num(site_v)})"
        return q * self._gs_k(kb) * ctx.universal_k(kb) * ctx.vent_k(), \
            f"({fmt_num(q)})"

    def _q_iz(self, cause: IZCause, kb, ctx: CalcContext) -> tuple[float, str]:
        """Частота причины ИЗ: (значение, подставленная скобка; «e^»
        заменена на exp(...) – Задача 4 сессии 15)."""
        rec = kb.iz_by_id(cause.ref) or {}
        k = self._iz_k(rec, kb)
        if rec.get("mode") == "lightning":
            q = ctx.lightning_q()
            return q * k, f"({fmt_num(q * k)})"
        if "p" in rec:
            q = float(rec["p"])
            return q * k, f"({fmt_num(q * k)})"
        lam = float(rec.get("lam", 0.0))
        q = 1.0 - math.exp(-lam)     # τ = 1 год
        return q * k, f"(1−exp(−{fmt_num(lam)}))"

    # ---------- расчет сценариев ----------
    def _path_factor(self, path: list, q_fn, kb, ctx) -> tuple[float, str]:
        """Задача 3.3 (сессия 15): множитель ПУТИ цепи причин –
        произведение значений вдоль пути (И-гейт Q = Q(родитель) ×
        Q(потомок)) и произведение подставленных скобок формулы."""
        v = 1.0
        pieces: list[str] = []
        for c in path:
            cv, piece = q_fn(c, kb, ctx)
            v *= cv
            pieces.append(piece)
        return v, (_join_pieces(pieces) if len(pieces) > 1 else pieces[0])

    def scenarios(self, kb, ctx: CalcContext) -> list[ScenarioRow]:
        """Все строки-сценарии дерева. Задача 3.3 (сессия 15): причины
        ГС/ИЗ образуют ЛЕС зависимостей (перетаскивание в иерархии);
        каждый путь «корень → лист» дает ОДНУ строку с произведением
        множителей вдоль пути (зависимая ветвь собственной строки не
        имеет); независимые причины – путь из одного узла, как раньше."""
        rows: list[ScenarioRow] = []
        q_sub = self.substance.q()
        q_ox = self.oxidizer.q()
        flows = kb.flow_titles
        stype = self.scenario_type

        gs_paths = cause_paths(self.gs_causes)
        iz_paths = cause_paths(self.iz_causes)

        def _iz_name(path) -> str:
            return " → ".join((kb.iz_by_id(c.ref) or {}).get("title", c.ref)
                              for c in path)

        for gs_path in gs_paths:
            root = gs_path[0]
            g = kb.gs_by_id(root.ref) or {}
            q_gs, gs_piece = self._path_factor(gs_path, self._q_gs,
                                               kb, ctx)
            gs_title = " → ".join((kb.gs_by_id(c.ref) or
                                   {}).get("title", c.ref)
                                  for c in gs_path)
            kind = g.get("kind", "p11")

            if stype == "tgm":
                for iz_path in iz_paths:
                    q_iz, iz_piece = self._path_factor(iz_path, self._q_iz,
                                                       kb, ctx)
                    rows.append(ScenarioRow(
                        name=(f"Пожар по поверхности"
                              f" – {_iz_name(iz_path)}"),
                        gs_ref=root.ref, iz_ref=iz_path[-1].ref, flow=None,
                        fire_type="ft-tgm-surface",
                        q=q_sub * q_ox * q_gs * q_iz,
                        formula=(f"{fmt_num(q_sub)}·{fmt_num(q_ox)}"
                                 f"·{gs_piece}·{iz_piece}")))
                continue

            if kind == "direct":
                # готовое «пожарное» событие П1.1 (кольцевой зазор и т.п.)
                rows.append(ScenarioRow(
                    name=gs_title, gs_ref=root.ref, iz_ref=None, flow=None,
                    fire_type=g.get("direct_fire", "ft-pool"),
                    q=q_sub * q_ox * q_gs,
                    formula=f"{fmt_num(q_sub)}·{fmt_num(q_ox)}·{gs_piece}"))
                continue

            if stype == "dust":
                for iz_path in iz_paths:
                    q_iz, iz_piece = self._path_factor(iz_path, self._q_iz,
                                                       kb, ctx)
                    for ft in ("ft-dust-defl", "ft-dust-det"):
                        ft_rec = kb.fire_type_by_id(ft) or {}
                        rows.append(ScenarioRow(
                            name=(f"{gs_title} – {ft_rec.get('title', ft)}"
                                  f" – {_iz_name(iz_path)}"),
                            gs_ref=root.ref, iz_ref=iz_path[-1].ref,
                            flow=None, fire_type=ft,
                            q=q_sub * q_ox * q_gs * q_iz,
                            formula=(f"{fmt_num(q_sub)}·"
                                     f"{fmt_num(q_ox)}·{gs_piece}"
                                     f"·{iz_piece}·1")))
                continue

            # ГГ/ГЖ/ЛВЖ: разгерметизация × расход × тип горения (П2.1) × ИЗ.
            # Задача 8.5 (сессия 15): причина (цепь) со СВОИМ диапазоном
            # расхода порождает сценарии только его (развернутые строки
            # выбора); None – все диапазоны, как раньше; диапазон цепи –
            # корневой причины
            medium = self._medium(kb)
            mapping = _MEDIUM_FIRE.get(medium, _MEDIUM_FIRE["gas"])
            flow_scope = (root.flow,) if root.flow else FLOWS
            for flow in flow_scope:
                p21 = (kb.p21.get(flow, {}).get(medium)
                       or [0.0, 0.0, 0.0])
                for i, p in enumerate(p21):
                    ft = mapping[_P21_KEYS[i]]
                    ft_rec = kb.fire_type_by_id(ft) or {}
                    for iz_path in iz_paths:
                        q_iz, iz_piece = self._path_factor(
                            iz_path, self._q_iz, kb, ctx)
                        rows.append(ScenarioRow(
                            name=(f"{gs_title} – {flows.get(flow, flow)}"
                                  f" – {ft_rec.get('title', ft)}"
                                  f" – {_iz_name(iz_path)}"),
                            gs_ref=root.ref, iz_ref=iz_path[-1].ref,
                            flow=flow, fire_type=ft,
                            q=q_sub * q_ox * q_gs * q_iz * float(p),
                            formula=(f"{fmt_num(q_sub)}·"
                                     f"{fmt_num(q_ox)}·{gs_piece}"
                                     f"·{iz_piece}·{fmt_num(p)}")))

        # «Огненный шар» – переключатель ноды «Возникновение пожара»
        if self.fireball and stype != "tgm":
            ft = kb.fire_type_by_id("ft-fireball") or {}
            q = float(ft.get("q", 2.5e-5))
            rows.append(ScenarioRow(
                name=ft.get("title", "Огненный шар"),
                gs_ref="fireball", iz_ref=None, flow=None,
                fire_type="ft-fireball", q=q,
                formula=fmt_num(q)))
        return rows

    def total_q(self, kb, ctx: CalcContext) -> float:
        """Q_участок,k = Σ Q_сценариев × K_σ."""
        s = sum(r.q for r in self.scenarios(kb, ctx))
        return s * float(self.k_sigma)

    def display_lines(self, kb, ctx: CalcContext) -> list[tuple[str, float]]:
        """Сгруппированные строки для текста ноды «Возникновение
        пожара»: по (ГС × расход × тип горения), Σ по ИЗ."""
        rows = self.scenarios(kb, ctx)
        out: list[tuple[str, float]] = []
        for r in rows:
            title = r.name
            if r.iz_ref is not None:
                # отрезать « – <ИЗ>» (последний сегмент)
                title = title.rsplit(" – ", 1)[0]
            if out and out[-1][0] == title:
                out[-1] = (title, out[-1][1] + r.q)
            else:
                out.append((title, r.q))
        return out

    # ---------- сериализация ----------
    def to_dict(self) -> dict:
        d = {
            "id": self.tree_id, "owner": self.owner_id,
            "scenario_type": self.scenario_type, "title": self.title,
            "substance": self.substance.to_dict(),
            "oxidizer": self.oxidizer.to_dict(),
            "gs_causes": [c.to_dict() for c in self.gs_causes],
            "iz_causes": [c.to_dict() for c in self.iz_causes],
            "gs_pedals": dict(self.gs_pedals),
            "iz_pedals": dict(self.iz_pedals),
            "k_sigma": float(self.k_sigma),
            "fireball": bool(self.fireball),
        }
        # Задача 11: смещения пишутся только если есть (старые файлы без
        # поля и новые проекты без перетаскивания остаются «чистыми»)
        if self.node_offsets:
            d["node_offsets"] = {k: [float(v[0]), float(v[1])]
                                 for k, v in self.node_offsets.items()}
        # Задача 4 (сессия 13): состояние справочной ноды (привязка/офсет)
        if self.annotation is not None:
            d["annotation"] = {
                "attached": self.annotation.get("attached"),
                "offset": [float(self.annotation.get("offset", (0.0, 0.0))[0]),
                           float(self.annotation.get("offset", (0.0, 0.0))[1])]}
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TreeModel":
        t = cls(d["scenario_type"], d.get("owner", ""),
                title=d.get("title", ""), tree_id=d.get("id"))
        t.substance = Presence.from_dict(d.get("substance", {}))
        t.oxidizer = Presence.from_dict(d.get("oxidizer", {}))
        t.gs_causes = [GSCause.from_dict(c) for c in d.get("gs_causes", [])]
        t.iz_causes = [IZCause.from_dict(c) for c in d.get("iz_causes", [])]
        t.gs_pedals = dict(d.get("gs_pedals", {}))
        t.iz_pedals = dict(d.get("iz_pedals", {}))
        t.k_sigma = float(d.get("k_sigma", 1.0))
        t.fireball = bool(d.get("fireball", False))
        offs = d.get("node_offsets") or {}
        t.node_offsets = {str(k): [float(v[0]), float(v[1])]
                          for k, v in offs.items()} or None
        # Задача 4 (сессия 13): справочная нода (привязка/офсет)
        ann = d.get("annotation")
        if isinstance(ann, dict):
            off = ann.get("offset") or (0.0, 0.0)
            t.annotation = {"attached": ann.get("attached"),
                            "offset": [float(off[0]), float(off[1])]}
        return t
