# -*- coding: utf-8 -*-
"""Правая панель: инспектор (сессия 10.1 – UX-полировка).

Структура форм – БЛОКАМИ: тонкая разделительная линия, заголовок блока,
отступ; зависимые поля показываются только при включении переключателя
(«Молниезащита» → категория + габариты S/L/H; «Аварийная вентиляция» →
поле A). Единый список «Тип (П1.3/П1.4)» автоматически переключается на
таблицу П1.4 при площади > 10 000 м². Подписи с формулами набираются
математической типографикой (F<sub>зд</sub>, N<sub>у.м</sub>).
Введённые значения применяются, когда курсор покидает панель свойств.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox,
                               QFormLayout, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QPushButton,
                               QScrollArea, QVBoxLayout, QWidget)

from ..core.kb import KnowledgeBase
from ..core.model import TGM_AREA_LIMIT_M2, TreeModel, tgm_level_value
from ..core.numfmt import fmt_num
from ..core.objects import (AREA, BUILDING, COMPARTMENT, DEFAULT_PROPS,
                            KIND_TITLES, OUTDOOR, ROOM, SITE_FIELD, SITE_TYPES,
                            TERRITORY, ObjNode)
from .controls import HLine, compact_combo, section_header, wide_combo
from .switch import ToggleSwitch, bind_fields
from .theme import PEDALS_CAPTION, math, mono_font

SECTION_GAP = 12      # интервал между блоками (после содержимого)

# Задача 6 (сессия 15): подсказки поля «ЗНАЧЕНИЕ» по типу места –
# значение идет в множитель ТГМ (a₁ × значение) и в П1.2 по типу
_SITE_VALUE_TIP = {
    "area": "Площадь, м²: значение подставляется в множитель ТГМ"
            " (a₁·F по табл. П1.3, при значении > 10 000 – a·F^b"
            " по табл. П1.4) и в П1.2 на м²-месте",
    "linear": "Длина, м: значение подставляется в множитель ТГМ"
              " (a₁ × значение) и в П1.2 для трубопроводных"
              " разновидностей",
    "apparatus": "Объем, м³: значение подставляется в множитель ТГМ"
                 " (a₁ × значение) и в П1.2 для аппаратных"
                 " разновидностей",
}


def _caption(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("caption")
    lab.setWordWrap(True)
    return lab


def _ensure_default(p: dict, key: str, default):
    """Задача 2 (сессия 13): инвариант «показано = записано» – значение,
    которое форма ПОКАЗЫВАЕТ, всегда лежит в props объекта. Отсутствующий
    ключ получает умолчание здесь же (без сигналов: значение и так уже
    отображено; поведение эквивалентно вводу пользователем).

    Задача 5 (сессия 14, LOCKED вариант (а)): ЕДИНСТВЕННОЕ исключение –
    площадь и тип (П1.3/П1.4) помещения и участка: наследуемое
    состояние показывается, но НЕ записывается (в props попадает только
    явно выбранное значение)."""
    if p.get(key) is None:
        p[key] = default
    return p[key]


def _set_grey(w: QWidget, on: bool) -> None:
    """Задача 5: показать значение поля как НАСЛЕДУЕМОЕ – приглушенный
    цвет (QSS [inactive="true"]) либо обычный после явного ввода."""
    w.setProperty("inactive", "true" if on else "false")
    w.style().unpolish(w)
    w.style().polish(w)


class InspectorPanel(QWidget):
    object_props_changed = Signal(object)       # свойства объекта изменены
    object_title_changed = Signal(object, str)  # «Название» переименовано
    tree_changed = Signal()                     # дерево изменено (пересчёт)
    # Задача 8 (сессия 15): вторым аргументом – диапазон расхода строки
    # выбора (small|mid|big|rupt|None)
    add_gs_requested = Signal(str, object)
    remove_gs_requested = Signal(int)           # индекс причины ГС
    add_iz_requested = Signal(str)
    remove_iz_requested = Signal(int)

    def __init__(self, kb: KnowledgeBase, parent=None):
        super().__init__(parent)
        self.kb = kb
        self._obj: ObjNode | None = None
        self._tree: TreeModel | None = None
        self._node_kind = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)
        self.title = QLabel("СВОЙСТВА")
        self.title.setObjectName("panelTitle")
        root.addWidget(self.title)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.form_host = QWidget()
        self.form_host.setObjectName("inspectorForm")
        self._lay = QVBoxLayout(self.form_host)
        self._lay.setContentsMargins(0, 0, 4, 0)
        self._lay.setSpacing(6)
        self._lay.addStretch(1)
        self.scroll.setWidget(self.form_host)
        # применение введённых значений при уходе курсора из панели (§4)
        self.form_host.installEventFilter(self)
        self.scroll.installEventFilter(self)
        root.addWidget(self.scroll, 1)

    # ============================ сервис ============================
    def eventFilter(self, obj, ev) -> bool:
        if ev.type() == QEvent.Type.Leave:
            focused = self.form_host.focusWidget()
            if focused is not None:
                focused.clearFocus()   # → editingFinished → применение
        return super().eventFilter(obj, ev)

    def _clear(self) -> None:
        while self._lay.count() > 1:
            item = self._lay.takeAt(0)
            w = item.widget()
            if w is not None:
                # немедленно снять с родителя: без этого виджет до
                # отложенного удаления рисуется поверх новой формы
                w.setParent(None)
                w.deleteLater()

    def _add(self, w: QWidget) -> None:
        self._lay.insertWidget(self._lay.count() - 1, w)

    def _row(self, label, w: QWidget) -> QWidget:
        """Строка «подпись – поле»; подпись может быть QLabel с формулой."""
        if not isinstance(label, QLabel):
            label = QLabel(label)
        host = QWidget()
        lay = QHBoxLayout(host)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.addWidget(label)
        lay.addWidget(w, 1)
        return host

    def _section(self, caption: str = "", rich: bool = False) -> None:
        """Начало блока: разделительная линия + заголовок + интервал.

        Сессия 12, Задача 2: вокруг линии добавлено «воздуха» (+6 px до
        линии, +4 после) – блоки больше не слипаются с сепаратором."""
        pre = QWidget()
        pre.setFixedHeight(6)
        self._add(pre)
        self._add(HLine())
        post = QWidget()
        post.setFixedHeight(4)
        self._add(post)
        if caption:
            self._add(section_header(caption, rich=rich))
        spacer = QWidget()
        spacer.setFixedHeight(4)
        self._add(spacer)

    def _gap(self) -> None:
        g = QWidget()
        g.setFixedHeight(SECTION_GAP - 6)
        self._add(g)

    def _spin(self, value, lo, hi, dec=1, step=1.0, suffix="",
              changed=None) -> QDoubleSpinBox:
        sp = QDoubleSpinBox()
        sp.setRange(lo, hi)
        sp.setDecimals(dec)
        sp.setSingleStep(step)
        if suffix:
            sp.setSuffix(suffix)
        sp.setValue(float(value))
        if changed:
            sp.valueChanged.connect(lambda v: changed(v))
        return sp

    # ---------- единый список «Тип (П1.3/П1.4)» с автопереключением ----
    def _type_combo_13_14(self, obj: ObjNode, on_change) -> tuple:
        """Список функционального назначения здания/установки: строки
        П1.3, при значении уровня > 10 000 – автоматически переключается
        на строки П1.4 (§2/§3). Задача 6 (сессия 15): значение уровня –
        по типу места (м²/м/м³, tgm_level_value), не только площадь.
        Задача 11 (сессия 15): подпись «Функциональное назначение»."""
        p = obj.props
        combo = wide_combo()
        label = QLabel(math("Тип (П1.3):"))

        def _big() -> bool:
            v = tgm_level_value(p)
            return bool(v is not None and v > TGM_AREA_LIMIT_M2)

        def fill() -> None:
            big = _big()
            key = "p14_type" if big else "p13_type"
            combo.blockSignals(True)
            combo.clear()
            rows = self.kb.p14 if big else self.kb.p13
            for r in rows:
                combo.addItem(r["title"], r["id"])
            combo.setCurrentIndex(max(0, combo.findData(p.get(key, ""))))
            combo.blockSignals(False)
            # Задача 2 (сессии 13): показанная строка списка немедленно
            # записывается в props (движок видел пустой p13_type → Q = 0)
            p[key] = combo.currentData()
            # Задача 11 (сессия 15): «Тип (П1.3)» → «Функциональное
            # назначение (П1.3)» (и П1.4) – везде
            label.setText(math(
                "Функциональное назначение (П1.4):" if big
                else "Функциональное назначение (П1.3):"))

        def picked(i: int) -> None:
            big = _big()
            key = "p14_type" if big else "p13_type"
            p[key] = combo.currentData()
            on_change()

        combo.currentIndexChanged.connect(picked)
        fill()
        return label, combo, fill

    # ---------- тип (П1.3/П1.4) с наследованием (Задача 5, вариант (а)) ----
    INHERIT_ROW = "– наследуется –"

    def _tgm_eff(self, obj: ObjNode) -> dict:
        """Эффективные значения ТГМ для уровня (пустой словарь-заглушка,
        если геттер не подключен – автономные тесты)."""
        return dict(self._tgm_view(obj)) if self._tgm_view else {}

    def _type_combo_inherited(self, obj: ObjNode, on_change) -> tuple:
        """Задача 5 (LOCKED): список функционального назначения
        (П1.3)/(П1.4) для ПОМЕЩЕНИЯ и УЧАСТКА – как у здания, но со
        строкой-заполнителем «– наследуется –»: пока назначение не выбрано
        явно, в props НИЧЕГО не пишется (выбранное значение всегда
        сохраняется; возврат к заполнителю снимает явный выбор). Подпись
        переключается по ЭФФЕКТИВНОМУ значению каскада
        (участок → помещение → здание). Задача 11 (сессия 15): подпись
        «Функциональное назначение (П1.3/П1.4)»."""
        p = obj.props
        combo = wide_combo()
        label = QLabel(math("Функциональное назначение (П1.3):"))

        def _big() -> bool:
            f = self._tgm_eff(obj).get("f")
            return bool(f is not None and f > TGM_AREA_LIMIT_M2)

        def fill() -> None:
            big = _big()
            key = "p14_type" if big else "p13_type"
            combo.blockSignals(True)
            combo.clear()
            combo.addItem(self.INHERIT_ROW, None)
            for r in (self.kb.p14 if big else self.kb.p13):
                combo.addItem(r["title"], r["id"])
            val = p.get(key)
            combo.setCurrentIndex(max(0, combo.findData(val)
                                      if val else 0))
            combo.blockSignals(False)
            label.setText(math(
                "Функциональное назначение (П1.4):" if big
                else "Функциональное назначение (П1.3):"))
            # подсказка: что именно наследуется на этом уровне
            view = self._tgm_eff(obj)
            eff = view.get("type14" if big else "type13")
            if val is None and eff:
                rec = (self.kb.p14_by_id(eff) if big
                       else self.kb.p13_by_id(eff)) or {}
                combo.setToolTip(
                    f"Наследуется: {rec.get('title', eff)}"
                    " (от ближнего уровня с явным выбором)")
            else:
                combo.setToolTip(
                    "Функциональное назначение здания по табл."
                    " П1.3/П1.4; строка «– наследуется –» берет"
                    " назначение от помещения или здания (в свойствах"
                    " уровня ничего не пишется)")

        def picked(_i: int) -> None:
            big = _big()
            key = "p14_type" if big else "p13_type"
            data = combo.currentData()
            if data is None:
                p.pop(key, None)      # вернулись к наследованию
            else:
                p[key] = data
            on_change()

        combo.currentIndexChanged.connect(picked)
        fill()
        return label, combo, fill

    def _area_field_inherited(self, obj: ObjNode, suffix: str = "",
                              lo: float = 1.0, hi: float = 100_000.0
                              ) -> QDoubleSpinBox:
        """Задача 5 (LOCKED): поле ПЛОЩАДИ помещения/участка. Своего
        значения нет – показывается НАСЛЕДУЕМОЕ (приглушенным цветом,
        подсказка «наследуется от …»), в props ничего не пишется; ввод
        пользователем записывает СОБСТВЕННОЕ значение уровня."""
        p = obj.props
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setDecimals(1)
        spin.setSuffix(suffix)
        own = p.get("area_m2")

        def _commit(v: float) -> None:
            p["area_m2"] = float(v)
            _set_grey(spin, False)     # стало явным – обычный цвет
            self.object_props_changed.emit(obj)

        if own is not None:
            spin.setValue(float(own))
        else:
            view = self._tgm_eff(obj)
            eff = view.get("f")
            src = view.get("f_kind")
            shown = float(eff) if eff is not None \
                else float(DEFAULT_PROPS[obj.kind].get("area_m2", 100.0))
            spin.blockSignals(True)
            spin.setValue(shown)
            spin.blockSignals(False)
            _set_grey(spin, True)
            if src:
                spin.setToolTip(
                    f"Наследуется от «{KIND_TITLES.get(src, src)}»"
                    f" ({fmt_num(shown)}{suffix}); введите значение,"
                    " чтобы задать собственную площадь уровня")
            else:
                spin.setToolTip(
                    "Площадь не задана ни на одном уровне каскада"
                    " (участок → помещение → здание)")
        spin.valueChanged.connect(_commit)
        return spin

    # ============================ объекты ============================
    def show_object(self, obj: ObjNode) -> None:
        self._obj, self._tree, self._node_kind = obj, None, ""
        self._clear()
        # Задача 3 (сессия 17, LOCKED): ВСЕКАПС-подпись вида объекта над
        # именем УДАЛЕНА – форма начинается сразу с полужирного имени
        self.title.setText("")
        self._add(QLabel(f"<b>{obj.title}</b>"))
        name = QLineEdit(obj.title)
        name.editingFinished.connect(
            lambda: self.object_title_changed.emit(obj, name.text().strip()))
        self._add(self._row("Название:", name))
        p = obj.props

        def setp(key):
            return lambda v: (p.__setitem__(key, v),
                              self.object_props_changed.emit(obj))

        if obj.kind == BUILDING:
            self._building_form(obj)
        elif obj.kind == ROOM:
            self._room_form(obj)
        elif obj.kind == AREA:
            self._area_form(obj)
        elif obj.kind == OUTDOOR:
            self._outdoor_form(obj)
        elif obj.kind == TERRITORY:
            # Задача 3 (сессия 17, LOCKED): «ТЕРРИТОРИЯ» → «ПАРАМЕТРЫ
            # ТЕРРИТОРИИ» (единый шаблон «ПАРАМЕТРЫ …» для секций,
            # названных по виду объекта)
            self._section("ПАРАМЕТРЫ ТЕРРИТОРИИ")
            # Задача 12 (сессия 13): «Площадь территории» + компактный
            # переключатель км²|м² рядом со значением. Хранение ВСЕГДА
            # нормализовано в км² (strike_area_km2); выбранная единица –
            # в props (strike_area_unit, по умолчанию км²) и попадает в
            # файл проекта. Задача 2: обе величины сразу пишутся в props.
            # Поле информативное: частота ударов молнии считается по
            # размерам и категории защиты здания/наружной установки.
            km2 = _ensure_default(p, "strike_area_km2", 0.05)
            unit = _ensure_default(p, "strike_area_unit", "km2")
            host = QWidget()
            hl = QHBoxLayout(host)
            hl.setContentsMargins(0, 0, 0, 0)
            hl.setSpacing(6)
            spin = QDoubleSpinBox()
            # Задача 4 (сессия 14): переключатель единиц – КОМПАКТНЫЙ
            # (ширина по содержимому «км²»/«м²», ~60–80 px, не тянется
            # с формой); остальные списки остаются wide_combo
            unit_cb = compact_combo()
            unit_cb.addItem("км²", "km2")
            unit_cb.addItem("м²", "m2")
            unit_cb.setCurrentIndex(max(0, unit_cb.findData(unit)))

            def _apply_unit(u: str) -> None:
                p["strike_area_unit"] = u
                v_km2 = float(p.get("strike_area_km2", 0.05) or 0.0)
                spin.blockSignals(True)
                if u == "m2":
                    spin.setDecimals(1)
                    spin.setRange(0.0, 1e12)
                    spin.setSuffix(" м²")
                    spin.setValue(v_km2 * 1e6)
                else:
                    spin.setDecimals(6)
                    spin.setRange(0.0, 1e6)
                    spin.setSuffix(" км²")
                    spin.setValue(v_km2)
                spin.blockSignals(False)

            def _commit(v: float) -> None:
                u = p.get("strike_area_unit", "km2")
                p["strike_area_km2"] = (float(v) / 1e6 if u == "m2"
                                        else float(v))
                self.object_props_changed.emit(obj)

            spin.valueChanged.connect(_commit)
            unit_cb.currentIndexChanged.connect(
                lambda _i: _apply_unit(unit_cb.currentData()))
            _apply_unit(unit)
            hl.addWidget(spin, 1)
            hl.addWidget(unit_cb)
            tip = ("Площадь территории – информативное поле, на расчет"
                   " не влияет. Частота ударов молнии определяется"
                   " габаритами и высотой здания (наружной установки)"
                   " и категорией молниезащиты – см. свойства здания.")
            spin.setToolTip(tip)
            unit_cb.setToolTip("Единица измерения площади территории"
                               " (значение хранится в км²)")
            self._add(self._row("Площадь:", host))
        elif obj.kind == COMPARTMENT:
            # Задача 3 (сессия 17, LOCKED): «ПОЖАРНЫЙ ОТСЕК» → «ПАРАМЕТРЫ
            # ПОЖАРНОГО ОТСЕКА» (единый шаблон секций)
            self._section("ПАРАМЕТРЫ ПОЖАРНОГО ОТСЕКА")
            cb = wide_combo()
            for r in ("REI 30", "REI 60", "REI 90", "REI 120", "REI 150"):
                cb.addItem(r, r)
            cb.setCurrentIndex(max(0, cb.findData(
                _ensure_default(p, "fire_resist_walls", "REI 90"))))
            cb.currentIndexChanged.connect(
                lambda _i: (p.__setitem__("fire_resist_walls",
                                          cb.currentData()),
                           self.object_props_changed.emit(obj)))
            self._add(self._row("Предел огнестойкости стен:", cb))

    # ---------- здание ----------
    def _building_form(self, obj: ObjNode) -> None:
        p = obj.props

        def changed() -> None:
            self.object_props_changed.emit(obj)

        self._section("РАСЧЕТНЫЕ СВОЙСТВА")
        dp = DEFAULT_PROPS[BUILDING]
        # Задача 2 (сессия 13): умолчания формы – из DEFAULT_PROPS, и они
        # немедленно записываются в props («показано = записано»)
        area = self._spin(_ensure_default(p, "area_m2", dp["area_m2"]),
                          1, 1_000_000,
                          dec=1, step=100, suffix=" м²",
                          changed=lambda v: (p.__setitem__("area_m2", v),
                                             changed(), type_fill()))
        area.setToolTip(math(
            "F_зд – площадь здания; при F > 10 000 м²"
            " множитель ТГМ считается по формуле a·F^b"
            " (табл. П1.4), иначе a₁·F (табл. П1.3)"))
        self._add(self._row(math("Площадь F_зд:"), area))
        t_label, t_combo, type_fill = self._type_combo_13_14(obj, changed)
        self._add(self._row(t_label, t_combo))

        # средства противоаварийной защиты: молниезащита (+ категория,
        # + габариты S/L/H – только для расчета молниезащиты, §6)
        self._section("СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ")
        p.setdefault("pedals", {})
        pedals = p["pedals"]
        sw = ToggleSwitch("Молниезащита")
        sw.setChecked(bool(pedals.get("lightning_prot", False)))
        # Задача 7: содержательная подсказка вместо дублирования подписи
        sw.setToolTip(
            "При включении молниезащиты частота поражения здания молнией"
            " умножается на (1 − η_МЗ). Надежность защиты по категориям"
            " I–IV – 0,98, 0,95, 0,90, 0,80"
            " (СО 153-34.21.122-2003, табл. 2.2).")
        cat = wide_combo()
        for c, eta_txt in (("I", "0,98"), ("II", "0,95"),
                           ("III", "0,90"), ("IV", "0,80")):
            cat.addItem(f"Уровень {c} · η = {eta_txt}", c)
        cat.setCurrentIndex(max(0, cat.findData(
            _ensure_default(p, "lightning_cat", dp["lightning_cat"]))))
        cat.currentIndexChanged.connect(
            lambda _i: (p.__setitem__("lightning_cat", cat.currentData()),
                        changed()))
        cat_row = self._row("Категория защиты:", cat)
        dims = QWidget()
        fl = QFormLayout(dims)
        fl.setContentsMargins(0, 2, 0, 2)
        fl.setSpacing(6)

        def setp(key):
            return lambda v: (p.__setitem__(key, v), changed())

        for key, lab in (("bln_S", "S (ширина), м:"), ("bln_L", "L (длина), м:"),
                         ("bln_H", "H (высота), м:")):
            fl.addRow(lab, self._spin(_ensure_default(p, key, dp[key]),
                                      1, 2000, dec=0,
                                      changed=setp(key)))
        dims_host = QWidget()
        dh = QVBoxLayout(dims_host)
        dh.setContentsMargins(0, 0, 0, 0)
        dh.setSpacing(4)
        cap_dims = QLabel(math(
            "Габариты (N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶):"))
        cap_dims.setWordWrap(True)
        dh.addWidget(cap_dims)
        dh.addWidget(dims)

        def _sw(on: bool) -> None:
            pedals["lightning_prot"] = on
            changed()

        sw.toggled.connect(_sw)
        bind_fields(sw, cat_row, dims_host)
        self._add(sw)
        self._add(cat_row)
        self._add(dims_host)
        # Задача 0: универсальные меры с носителем «здание»
        self._universal_measures_block(obj)

    # ---------- помещение ----------
    def _room_form(self, obj: ObjNode) -> None:
        p = obj.props

        def changed() -> None:
            self.object_props_changed.emit(obj)

        # Задача 3 (сессия 17, LOCKED): «ПОМЕЩЕНИЕ» → «ПАРАМЕТРЫ
        # ПОМЕЩЕНИЯ» (единый шаблон секций)
        self._section("ПАРАМЕТРЫ ПОМЕЩЕНИЯ")
        # Задача 5 (LOCKED вариант (а)): площадь и тип НЕ материализуются –
        # без своего значения показывается наследуемое (серым, в props не
        # пишется); здание остается последним звеном каскада
        self._add(self._row(
            "Площадь, м²:", self._area_field_inherited(obj)))
        t_label, t_combo, _t_fill = self._type_combo_inherited(obj, changed)
        self._add(self._row(t_label, t_combo))
        # §10: аварийная вентиляция и её параметры – отдельный блок
        self._section("СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ")
        p.setdefault("pedals", {})
        pedals = p["pedals"]
        sw = ToggleSwitch("Аварийная вентиляция")
        sw.setChecked(bool(pedals.get("venting", False)))
        # Задача 7: содержательная подсказка вместо дублирования подписи
        sw.setToolTip(
            "При включении аварийной вентиляции условная вероятность"
            " сохранения взрывоопасной концентрации снижается"
            " до P_ост = 1/(A·T + 1). Делитель массы – по"
            " ГОСТ Р 12.3.047-98, прил. А, п. А.2.5.")
        holder = QWidget()
        hl = QHBoxLayout(holder)
        hl.setContentsMargins(0, 0, 0, 0)
        lab = QLabel(math("Кратность воздухообмена A, ч⁻¹:"))
        lab.setWordWrap(True)
        hl.addWidget(lab)
        hl.addWidget(self._spin(
            _ensure_default(p, "vent_rate", DEFAULT_PROPS[ROOM]["vent_rate"]),
            0.5, 60, dec=1, suffix=" ч⁻¹",
            changed=lambda v: (p.__setitem__("vent_rate", v),
                               self.object_props_changed.emit(obj))), 1)

        def _vent(on: bool) -> None:
            pedals["venting"] = on
            self.object_props_changed.emit(obj)

        sw.toggled.connect(_vent)
        bind_fields(sw, holder)
        self._add(sw)
        self._add(holder)
        # Задача 0: универсальные меры с носителем «помещение»
        self._universal_measures_block(obj)

    # ---------- участок/наружная установка: блоки «ТИП» и «ЗНАЧЕНИЕ» ------
    # Задача 6 (сессия 15): блок общий для участка и наружной установки –
    # выбор типа места (м²/м/м³) и значение по типу. inherit_area=True
    # (участок): площадь без собственного значения показывается
    # НАСЛЕДУЕМОЙ (вариант (а) сессии 14, в props не пишется);
    # inherit_area=False (наружная установка): значение материализуется
    # сразу – установка сама себе последний уровень каскада
    # («показано = записано»).
    def _site_type_section(self, obj: ObjNode, on_change,
                           inherit_area: bool = True,
                           on_value=None) -> QComboBox:
        p = obj.props
        self._section("ТИП")
        st = wide_combo()
        for sid, title in SITE_TYPES:
            st.addItem(title, sid)
        st.setCurrentIndex(max(0, st.findData(
            _ensure_default(p, "site_type", "area"))))

        value_host = QWidget()
        vh = QHBoxLayout(value_host)
        vh.setContentsMargins(0, 0, 0, 0)
        vh.setSpacing(8)
        value_lab = QLabel("")
        value_spin = QDoubleSpinBox()
        value_spin.setRange(0.1, 10_000_000)
        value_spin.setDecimals(1)
        value_spin.setMinimumWidth(140)
        vh.addWidget(value_lab)
        vh.addWidget(value_spin, 1)

        def _refresh_value(sid: str) -> None:
            key, lab, default = SITE_FIELD[sid]
            value_lab.setText(lab + ":")
            value_spin.blockSignals(True)
            if sid == "area" and inherit_area:
                # Задача 5 (LOCKED вариант (а)): площадь участка НЕ
                # материализуется – без своего значения показывается
                # наследуемое (серым; в props не пишется)
                own = p.get("area_m2")
                if own is not None:
                    value_spin.setValue(float(own))
                    _set_grey(value_spin, False)
                    value_spin.setToolTip(
                        "Собственная площадь участка; при отсутствии"
                        " она наследуется: помещение → здание")
                else:
                    view = self._tgm_eff(obj)
                    eff, src = view.get("f"), view.get("f_kind")
                    shown = float(eff) if eff is not None \
                        else float(default)
                    value_spin.setValue(shown)
                    _set_grey(value_spin, True)
                    if src:
                        value_spin.setToolTip(
                            f"Наследуется от «{KIND_TITLES.get(src, src)}»"
                            f" ({fmt_num(shown)}); введите значение,"
                            " чтобы задать собственную площадь участка")
                    else:
                        value_spin.setToolTip(
                            "Площадь не задана ни на одном уровне"
                            " каскада (участок → помещение → здание)")
            else:
                # линейный/аппаратный объект и наружная установка –
                # каскада нет, материализация («показано = записано»);
                # умолчание – из DEFAULT_PROPS вида (у установки площадь
                # 400, у участка – 100), SITE_FIELD – запасной вариант
                default = DEFAULT_PROPS.get(obj.kind, {}).get(key, default)
                value_spin.setValue(float(_ensure_default(p, key, default)))
                _set_grey(value_spin, False)
                value_spin.setToolTip(_SITE_VALUE_TIP.get(sid, ""))
            value_spin.blockSignals(False)

        def _on_type(i: int) -> None:
            sid = st.itemData(i)
            p["site_type"] = sid
            _refresh_value(sid)
            self.object_props_changed.emit(obj)

        st.currentIndexChanged.connect(_on_type)
        _refresh_value(p.get("site_type", "area"))

        def _on_val(v: float) -> None:
            sid = p.get("site_type", "area")
            key = SITE_FIELD[sid][0]
            p[key] = float(v)
            if sid == "area" and inherit_area:
                _set_grey(value_spin, False)   # стало собственным
            self.object_props_changed.emit(obj)
            if on_value is not None:
                on_value()

        value_spin.valueChanged.connect(_on_val)
        self._add(self._row("Выберите тип:", st))
        self._section("ЗНАЧЕНИЕ")
        self._add(value_host)
        return st

    # ---------- участок (§11: блоки «ТИП» и «ЗНАЧЕНИЕ») ----------
    def _area_form(self, obj: ObjNode) -> None:
        def changed() -> None:
            self.object_props_changed.emit(obj)

        self._site_type_section(obj, changed, inherit_area=True)
        # Задача 5 (LOCKED): тип (П1.3/П1.4) на участке – с наследованием
        self._section("РАСЧЕТНЫЕ СВОЙСТВА")
        a_label, a_combo, _a_fill = self._type_combo_inherited(obj, changed)
        self._add(self._row(a_label, a_combo))

    # ---------- наружная установка ----------
    def _outdoor_form(self, obj: ObjNode) -> None:
        p = obj.props

        def changed() -> None:
            self.object_props_changed.emit(obj)

        # Задача 6 (сессия 15): селектор типа + значение по типу – тот же
        # блок, что у участка; умолчание типа существующих проектов –
        # «участок (м²)» (миграция: site_type пишется при открытии формы).
        # Правка значения перезаполняет список П1.3/П1.4 (автопереключение
        # по ЭФФЕКТИВНОМУ значению уровня), поэтому комбо строится раньше
        t_label, t_combo, t_fill = self._type_combo_13_14(obj, changed)
        self._site_type_section(obj, changed, inherit_area=False,
                                on_value=t_fill)
        self._section("РАСЧЕТНЫЕ СВОЙСТВА")
        self._add(self._row(t_label, t_combo))

        self._section("СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ")
        p.setdefault("pedals", {})
        pedals = p["pedals"]
        sw = ToggleSwitch("Молниезащита")
        sw.setChecked(bool(pedals.get("lightning_prot", False)))
        # Задача 7: содержательная подсказка вместо дублирования подписи
        sw.setToolTip(
            "При включении молниезащиты частота поражения здания молнией"
            " умножается на (1 − η_МЗ). Надежность защиты по категориям"
            " I–IV – 0,98, 0,95, 0,90, 0,80"
            " (СО 153-34.21.122-2003, табл. 2.2).")
        cat = wide_combo()
        for c, eta_txt in (("I", "0,98"), ("II", "0,95"),
                           ("III", "0,90"), ("IV", "0,80")):
            cat.addItem(f"Уровень {c} · η = {eta_txt}", c)
        cat.setCurrentIndex(max(0, cat.findData(
            _ensure_default(p, "lightning_cat", "II"))))
        cat.currentIndexChanged.connect(
            lambda _i: (p.__setitem__("lightning_cat", cat.currentData()),
                        changed()))
        cat_row = self._row("Категория защиты:", cat)

        def _sw(on: bool) -> None:
            pedals["lightning_prot"] = on
            changed()

        sw.toggled.connect(_sw)
        bind_fields(sw, cat_row)
        self._add(sw)
        self._add(cat_row)

    # ============================ ноды дерева ============================
    def current_tree(self) -> TreeModel | None:
        """Задача 9 (сессия 15): дерево, чья нода показана в инспекторе
        (self._tree из show_tree_node). Причины добавляются/удаляются
        ИМЕННО в него – окно больше не угадывает дерево по выделению
        (со вторым деревом того же владельца _current_tree() молча
        возвращал None и операция терялась)."""
        return self._tree

    def current_node_kind(self) -> str | None:
        """Вид показанной ноды дерева (gs/iz/fire/…; Задача 1 сессии 16:
        после удаления причин из иерархии окно обновляет форму ноды)."""
        return self._node_kind or None

    def show_tree_node(self, tree: TreeModel, node_kind: str) -> None:
        self._obj, self._tree, self._node_kind = None, tree, node_kind
        self._clear()
        titles = tree.node_titles(self.kb)
        self.title.setText("НОДА ДЕРЕВА")
        self._add(QLabel(f"<b>{titles.get(node_kind, node_kind)}</b>"))

        if node_kind in ("substance", "oxidizer"):
            pres = getattr(tree, node_kind)
            # Задача 15 (сессия 12): единственное поле – «Вероятность
            # присутствия», безразмерная 0–1; значение вводит
            # пользователь (режимы «время/частота» упразднены)
            self._section("ВЕРОЯТНОСТЬ ПРИСУТСТВИЯ")
            spin = self._spin(pres.value, 0.0, 1.0, dec=3, step=0.05,
                              changed=lambda v: (setattr(pres, "value", v),
                                                 self.tree_changed.emit()))
            spin.setToolTip(
                "Вероятность присутствия вещества (окислителя)"
                " на рассматриваемом участке – доля года,"
                " безразмерная, 0–1. Учитывается в Q_сценария множителем.")
            self._add(self._row("Вероятность присутствия:", spin))
            note = QLabel("Вероятность присутствия – множитель"
                          " в Q_сценария (0–1)")
            note.setFont(mono_font(10))
            self._add(note)
        elif node_kind == "gs":
            self._cause_block(tree, gs=True)
            self._pedal_block(tree, gs=True)
        elif node_kind == "iz":
            self._cause_block(tree, gs=False)
            self._pedal_block(tree, gs=False)
        elif node_kind == "fire":
            self._section("КОЭФФИЦИЕНТ БЕЗОПАСНОСТИ")
            self._add(self._row(
                math("K_σ:"),
                self._spin(tree.k_sigma, 1.0, 3.0, dec=2, step=0.1,
                           suffix=" ×", changed=lambda v: (
                               setattr(tree, "k_sigma", float(v)),
                               self.tree_changed.emit()))))
            self._section("ОСОБЫЙ СЦЕНАРИЙ")
            fb = ToggleSwitch("Огненный шар (диффузионное горение)")
            fb.setChecked(tree.fireball)
            fb.setToolTip("Частота внешнего воздействия 2,5·10⁻⁵ год⁻¹"
                          " на аппарат (Приказ МЧС России № 533,"
                          " прил. № 1, п. 5)")
            fb.toggled.connect(lambda on: (setattr(tree, "fireball", on),
                                           self.tree_changed.emit()))
            self._add(fb)

    # ---------- блок причин ГС/ИЗ ----------
    def _cause_block(self, tree: TreeModel, gs: bool) -> None:
        causes = tree.gs_causes if gs else tree.iz_causes
        self._section("ПРИЧИНЫ ОБРАЗОВАНИЯ ГС" if gs
                      else "ПРИЧИНЫ ПОЯВЛЕНИЯ ИЗ")
        for i, c in enumerate(causes):
            rec = (self.kb.gs_by_id(c.ref) if gs else self.kb.iz_by_id(c.ref)) \
                or {}
            row = QWidget()
            lay = QHBoxLayout(row)
            lay.setContentsMargins(0, 0, 0, 0)
            lay.setSpacing(6)
            # Задача 8 (сессия 15): у развернутых строк ГС показывается
            # диапазон расхода (независимая причина своего диапазона);
            # Задача 3.3: зависимые ветви помечены «→» (И-гейт)
            title = rec.get("title", c.ref)
            if gs and c.flow and self.kb.flow_titles.get(c.flow):
                title += f" – {self.kb.flow_titles[c.flow]}"
            if getattr(c, "parent", None):
                title = "→ " + title
            lab = QLabel(title)
            lab.setWordWrap(True)
            lay.addWidget(lab, 1)
            if gs and rec.get("kind") == "p12":
                spin = QDoubleSpinBox()
                spin.setRange(0.1, 100_000)
                spin.setDecimals(1)
                spin.setSuffix(" м")
                spin.setValue(c.len_m if c.len_m is not None else 50.0)

                def _len(v, idx=i):
                    tree.gs_causes[idx].len_m = float(v)
                    self.tree_changed.emit()

                spin.valueChanged.connect(_len)
                lay.addWidget(spin)
            btn = QPushButton("Убрать")
            btn.setFixedWidth(70)
            if gs:
                btn.clicked.connect(
                    lambda _=False, idx=i:
                    self.remove_gs_requested.emit(idx))
            else:
                btn.clicked.connect(
                    lambda _=False, idx=i:
                    self.remove_iz_requested.emit(idx))
            lay.addWidget(btn)
            self._add(row)
        add = QPushButton("Добавить причину…")
        add.setObjectName("primary")
        add.clicked.connect(lambda: self._pick_cause(tree, gs))
        self._add(add)

    def pick_cause_for(self, tree: TreeModel, kind: str) -> None:
        """Задача 2 (сессия 19, LOCKED): публичный вход в выбор причины для
        УКАЗАННОГО дерева и вида ноды («gs»/«iz») – общий для кнопки
        инспектора и двойного клика по ноде холста. Диалог и сигналы
        add_gs_requested/add_iz_requested те же, поэтому отмена, отметка
        «изменено» и перерисовка не дублируются."""
        if kind not in ("gs", "iz"):
            return
        self._pick_cause(tree, gs=(kind == "gs"))

    def _pick_cause(self, tree: TreeModel, gs: bool) -> None:
        records = self._cause_records(tree, gs)
        dlg = _CausePickerDialog(records, self)
        if dlg.exec() == _CausePickerDialog.Accepted and dlg.selected_id:
            if gs:
                self.add_gs_requested.emit(dlg.selected_id,
                                           dlg.selected_flow)
            else:
                self.add_iz_requested.emit(dlg.selected_id)

    def _cause_records(self, tree: TreeModel, gs: bool) -> list[dict]:
        """Записи для выбора причины (шов для тестов без модального
        диалога). Сессия 14/1 (решение заказчика): причины ГС доступны
        на ЛЮБОМ участке, включая «участок (м²)», – фильтр по типу
        участка снят; фильтруется только тип сценария (applies).
        ИЗ – вся библиотека.
        Задача 8 (сессия 15, LOCKED): для ГГ/ГЖ/ЛВЖ каждая
        разгерметизационная запись развернута в СТРОКИ ПО ДИАПАЗОНАМ
        массового расхода истечения (small/mid/big; «полное разрушение»
        – одна строка rupt; direct/поверхность – без диапазона) –
        независимые причины; ТГМ и Пыль – одна строка на запись
        (математика этих типов не ветвится по расходу)."""
        if not gs:
            return self.kb.iz_all()
        out = []
        for g in self.kb.gs_for(tree.scenario_type):
            if tree.scenario_type in ("gg", "gzh", "lvzh"):
                for flow in self.kb.flow_variants(g):
                    r = dict(g)
                    r["flow"] = flow
                    r["row_title"] = self.kb.flow_row_title(g, flow)
                    out.append(r)
            else:
                out.append(g)
        return out

    # ---------- педали нод (защитные средства) ----------
    def _pedal_block(self, tree: TreeModel, gs: bool) -> None:
        pedals = tree.gs_pedals if gs else tree.iz_pedals
        target = "gs" if gs else "iz"
        mods = self.kb.modifiers_for_target(target)
        if not mods:
            return
        self._section(PEDALS_CAPTION, rich=False)
        for m in mods:
            key = m.get("pedal")
            if not key:
                continue
            sw = ToggleSwitch(m.get("title", key))
            sw.setChecked(bool(pedals.get(key, False)))
            # Задача 7: содержательная подсказка из базы знаний, если она
            # задана; дублировать подпись строки бессмысленно – тогда
            # подсказки нет вовсе
            if m.get("tooltip"):
                sw.setToolTip(m["tooltip"])

            def _tog(on: bool, k=key) -> None:
                pedals[k] = on
                self.tree_changed.emit()

            sw.toggled.connect(_tog)
            self._add(sw)
            if gs and key == "sil_paz":
                form = QWidget()
                fl = QFormLayout(form)
                fl.setContentsMargins(0, 0, 0, 0)
                sil = wide_combo()
                sil.addItem("Нет", 0)
                for lvl in (1, 2, 3, 4):
                    lo, hi = (m.get("ranges", {}).get(
                        str(lvl), [10.0 ** -lvl, 10.0 ** (1 - lvl)]))
                    sil.addItem(
                        f"SIL {lvl}: PFD {fmt_num(lo)}…{fmt_num(hi)}", lvl)
                sil.setCurrentIndex(int(pedals.get("sil", 0)))

                def _sil(i: int) -> None:
                    lvl = sil.itemData(i)
                    pedals["sil"] = int(lvl)
                    if lvl:
                        pedals["sil_pfd"] = 10.0 ** -int(lvl)
                    self.tree_changed.emit()

                sil.currentIndexChanged.connect(_sil)
                fl.addRow("Уровень полноты безопасности (SIL):", sil)
                bind_fields(sw, form)
                self._add(form)

    # ---------- внедрение колбэка владельца (для фильтра причин) ----------
    def _universal_measures_block(self, obj: ObjNode) -> None:
        """Задача 0 (сессия 13): новые защитные средства библиотеки
        (универсальный множитель k, type "k") с носителем «помещение»
        или «здание» – переключатели прямо в свойствах объекта."""
        p = obj.props
        p.setdefault("pedals", {})
        pedals = p["pedals"]
        mods = [m for m in self.kb.modifiers_for_target(obj.kind)
                if m.get("type") == "k"]
        if not mods:
            return
        self._section(PEDALS_CAPTION, rich=False)
        for m in mods:
            sw = ToggleSwitch(m.get("title", m.get("pedal", "")))
            sw.setChecked(bool(pedals.get(m["pedal"], False)))
            if m.get("tooltip"):
                sw.setToolTip(m["tooltip"])
            else:
                kv = fmt_num(float(m.get("k", 1.0)))
                sw.setToolTip(
                    f"Универсальный множитель k = {kv}: частоты"
                    " разгерметизации нод ГС дерева умножаются на k,"
                    " пока переключатель включен.")

            def _tog(on: bool, k=m["pedal"]) -> None:
                pedals[k] = on
                self.object_props_changed.emit(obj)

            sw.toggled.connect(_tog)
            self._add(sw)

    def set_owner_getter(self, getter) -> None:
        self._owner_getter = getter

    _owner_getter = None

    def set_tgm_view(self, getter) -> None:
        """Задача 5 (сессия 14): источник эффективных площади/типа ТГМ
        (MainWindow.tgm_view – каскад участок → помещение → здание)."""
        self._tgm_view = getter

    _tgm_view = None


class _CausePickerDialog(QDialog):
    """Выбор разновидности причины: поиск + список с частотами.
    Задача 8 (сессия 15): у записей ГС для ГГ/ГЖ/ЛВЖ строки развернуты
    по диапазонам расхода (row_title); выбранная строка несет свой
    диапазон (selected_flow) – каждая строка = независимая причина."""

    def __init__(self, records: list[dict], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить причину")
        self.setMinimumSize(520, 420)
        self.selected_id: str | None = None
        self.selected_flow: str | None = None
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 12)
        search = QLineEdit()
        search.setPlaceholderText("Поиск по названию…")
        lay.addWidget(search)
        self.listw = QListWidget()
        self.listw.setWordWrap(True)
        # Задача 2 (сессия 11): попиксельный скролл списка причин
        self.listw.setVerticalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel)
        self.listw.setHorizontalScrollMode(
            QListWidget.ScrollMode.ScrollPerPixel)
        self.listw.verticalScrollBar().setSingleStep(20)
        lay.addWidget(self.listw, 1)
        self._records = records
        self._fill("")
        search.textChanged.connect(self._fill)
        self.listw.itemDoubleClicked.connect(lambda _it: self._accept())
        btn = QPushButton("Добавить")
        btn.setObjectName("primary")
        btn.clicked.connect(self._accept)
        lay.addWidget(btn)

    def _fill(self, text: str) -> None:
        self.listw.clear()
        t = text.strip().lower()
        for r in self._records:
            title = r.get("row_title", r.get("title", r["id"]))
            if t and t not in title.lower():
                continue
            q = r.get("q", r.get("q_per_m", r.get("lam", "")))
            suffix = (f"  ·  {fmt_num(q)}"
                      if isinstance(q, float) else "")
            it = QListWidgetItem(title + suffix)
            it.setData(Qt.ItemDataRole.UserRole, r["id"])
            it.setData(Qt.ItemDataRole.UserRole + 1, r.get("flow"))
            self.listw.addItem(it)

    def _accept(self) -> None:
        it = self.listw.currentItem()
        if it is not None:
            self.selected_id = it.data(Qt.ItemDataRole.UserRole)
            self.selected_flow = it.data(Qt.ItemDataRole.UserRole + 1)
            self.accept()
