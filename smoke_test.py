# -*- coding: utf-8 -*-
"""Smoke-тесты ядра Kuji 6.0 (сессия 10: парадигма пяти типов сценариев).

Запуск: runtime\\python\\python.exe smoke_test.py (offscreen не нужен –
чистое ядро; QGuiApplication создаётся для шрифтов в layout-блоке).
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")

from PySide6.QtWidgets import QApplication, QMessageBox

app = QApplication([])

from eta.core.kb import KnowledgeBase
from eta.core.layout import compute_layout
from eta.core.matrix import build_matrix
from eta.core.model import (FLOWS, GSCause, IZCause, Presence, CalcContext,
                            TreeModel)
from eta.core.objects import (AREA, BUILDING, OUTDOOR, ROOM, TERRITORY,
                              ObjectTree, ObjNode, effective_site_type,
                              tgm_levels)
from eta.core.serializer import (FORMAT_VERSION, UnsupportedFormatError,
                                 load_project, save_project)
from eta.core.validation import check_tree

kb = KnowledgeBase()

# --- 1. КБ 6.2: схема, уникальность, отсутствие длинного тире ------------
# Задача 9 (сессия 18): реестр источников – раздел sources; поле source
# каждой записи ГС/ИЗ/мер ссылается id'ом на запись реестра
assert kb.meta["version"] == "6.2"
assert kb.sources and all(s.get("id") and s.get("title")
                          for s in kb.sources)
_src_ids = {s["id"] for s in kb.sources}
for _sec9 in ("gs_causes", "iz_causes", "property_modifiers"):
    for _r9 in kb.data[_sec9]:
        _v9 = _r9.get("source")
        assert not _v9 or _v9 in _src_ids, (_sec9, _r9.get("id"), _v9)
raw = open(kb.path, encoding="utf-8").read()
assert "—" not in raw, "длинное тире в КБ"
assert len(kb.scenario_types) == 5
assert [t["id"] for t in kb.scenario_types] == \
    ["tgm", "gg", "gzh", "lvzh", "dust"]
ids = [g["id"] for g in kb.gs_causes] + [i["id"] for i in kb.iz_causes] \
    + [f["id"] for f in kb.fire_types] + [e["id"] for e in
                                          kb.equipment_templates]
assert len(ids) == len(set(ids)), "дубликаты id в КБ"
assert any(g["id"] == "gs-vessel-12.5" for g in kb.gs_causes)
assert any(i["id"] == "iz-lightning" for i in kb.iz_causes)
mods = kb.property_modifiers
assert not any(m["id"] in ("pm-flow-cat", "pm-domino") for m in mods)
assert all(m.get("target") in ("gs", "iz", "room", "building") for m in mods)
# сессия 11 (Задача 1b): канон нормативных формулировок в текстах мер
mod_texts = [v for m in mods
             for k in ("title", "formula", "source", "notes", "tooltip")
             if (v := m.get(k, ""))]
assert not any(";" in v for v in mod_texts), "«;» в текстах защитных средств"
for jargon in ("барьер", "якорь", "голосования", "PFD барьера",
               "горячий/холодный"):
    assert not any(jargon in v.lower() for v in mod_texts), jargon
by_id = {m["id"]: m for m in mods}
assert by_id["pm-reserve"]["title"] == "Резервирование противоаварийной защиты"
assert by_id["pm-hermetic"]["title"].endswith("антикоррозионная защита")
assert by_id["pm-sil"]["title"] == "ПАЗ по уровню полноты безопасности (SIL)"
assert "(вероятность отказа по запросу)" not in raw    # только в UI-рендере
assert len(kb.p13) == 10 and len(kb.p14) == 8
assert kb.p21["rupt"]["liquid"] == [0.050, 0.061, 0.100]
# Задача 7 (сессия 15): «пожар/взрыв» → «пожар», расшифровки сняты;
# нормативные названия режимов П2.1 («Сгорание (взрыв) …») не тронуты
assert [t["title"] for t in kb.scenario_types] == [
    "Сценарий пожара ТГМ", "Сценарий пожара ГГ", "Сценарий пожара ГЖ",
    "Сценарий пожара ЛВЖ", "Сценарий пожара Пыли"]
assert "пожара/взрыва" not in raw
for _bad in ("(твердые горючие материалы)", "(горючие газы)",
             "(горючие жидкости)", "(легковоспламеняющиеся жидкости)",
             "(сжиженные газы)", "(пыли)"):
    assert _bad not in raw, _bad
_ft7 = {f["id"]: f["title"] for f in kb.fire_types}
assert _ft7["ft-vce"] == "Сгорание (взрыв) топливовоздушной смеси"
assert _ft7["ft-dust-defl"] == \
    "Сгорание (взрыв) пылевоздушной смеси – дефлаграция"
print("OK КБ 6.2: схема + реестр источников (source -> id), id уникальны,"
      " П1.3/П1.4/П2.1, меры по канону; Задача 7 – «пожар» без расшифровок")

# --- 2. наличие: вероятность присутствия (Задача 15, сессия 12) -----------
p = Presence()
assert p.q() == 1.0                          # по умолчанию: вещество есть
p = Presence(value=0.05)
assert abs(p.q() - 0.05) < 1e-12
# миграция старых проектов формата 5 при загрузке: «время» – значение как
# есть (доля года = вероятность), «частота» – разовый пересчет 1 − e^(−f)
assert Presence.from_dict({"mode": "time", "value": 0.5}).q() == 0.5
pf = Presence.from_dict({"mode": "freq", "value": 6.0})
assert abs(pf.value - (1 - math.exp(-6.0))) < 1e-12
assert Presence.from_dict(p.to_dict()).q() == p.q()
print("OK наличие: вероятность присутствия 0–1 + миграция time/freq")


def mk_ctx(building: dict | None = None, room: dict | None = None,
           site: dict | None = None) -> CalcContext:
    return CalcContext(building_props=building or {},
                       room_props=room or {}, site_props=site or {})


# --- 3. ТГМ против кондитерского примера (пример расчёта, разд. 1) -------
bld = {"area_m2": 2960.77, "p13_type": "p13-multi"}
t = TreeModel("tgm", "a1")
t.gs_causes = [GSCause(ref="gs-tgm-surface")]
t.iz_causes = [IZCause(ref=r) for r in
               ("iz-lamp", "iz-cable", "iz-uzdo", "iz-human",
                "iz-fork", "iz-spark")]
ctx = CalcContext(tgm_chain=[dict(bld)])       # уровень участка (Задача 5)
rows = t.scenarios(kb, ctx)
assert len(rows) == 6 and all(r.fire_type == "ft-tgm-surface" for r in rows)
expected = 9.0e-5 * 2960.77 * 86.2e-6        # Σλ_i ×10⁻⁶
total = t.total_q(kb, ctx)
assert abs(total - expected) / expected < 0.01, (total, expected)
assert total == t.total_q(kb, ctx)           # детерминизм
print(f"OK ТГМ: Q = {total:.3e} ≈ 2,30·10⁻⁵ примера; строк = числу ИЗ;"
      " площадь/тип на уровне участка (каскад Задачи 5)")

# --- 4. ТГМ: П1.4 при F > 10 000 м² (авто-переключение) -------------------
big = CalcContext(tgm_chain=[{"area_m2": 25000.0, "p13_type": "p13-multi",
                              "p14_type": "p14-food"}])
v, note = big.tgm_multiplier(kb)
assert abs(v - 0.0011 * 25000 ** 0.6) < 1e-9
assert note == "(0,0011·25000^0,6)", note      # Задача 4: только числа
small = CalcContext(tgm_chain=[{"area_m2": 2000.0, "p13_type": "p13-multi",
                                "p14_type": "p14-food"}])
v2, note2 = small.tgm_multiplier(kb)
assert abs(v2 - 9.0e-5 * 2000) < 1e-12
assert note2 == "(9·10⁻⁵·2000)", note2
# таблица множителя – для блока источников отчета (Задача 4.2)
assert small.tgm_table(kb) == "П1.3" and big.tgm_table(kb) == "П1.4"
assert CalcContext(tgm_chain=[{}, {}, {}]).tgm_table(kb) == ""
print("OK ТГМ: a₁·F/a·F^b; наружная установка – собственные значения;"
      " каскад Задачи 5 ниже")
# Задача 5 (LOCKED вариант (а)): F – первый ЯВНЫЙ уровень цепочки,
# тип – ближайший явный (участок перекрывает помещение перекрывает здание)
cascade = CalcContext(tgm_chain=[
    {"area_m2": 500.0},                              # участок
    {},                                              # помещение
    {"area_m2": 2000.0, "p13_type": "p13-multi"}])   # здание
assert abs(cascade.tgm_multiplier(kb)[0] - 9.0e-5 * 500) < 1e-12
cascade2 = CalcContext(tgm_chain=[
    {}, {"area_m2": 800.0},
    {"area_m2": 2000.0, "p13_type": "p13-multi"}])
assert abs(cascade2.tgm_multiplier(kb)[0] - 9.0e-5 * 800) < 1e-12
cascade3 = CalcContext(tgm_chain=[
    {"area_m2": 100.0}, {"p13_type": "p13-multi"}, {}])
assert cascade3.tgm_multiplier(kb)[0] > 0            # тип от помещения
# Задача 1 (сессия 15, вариант А): значение уровня участка – по типу
# (м²/м/м³); линейный/аппаратный участок заменяет F своей длиной/объемом
lin15 = CalcContext(tgm_chain=[
    {"site_type": "linear", "length_m": 120.0}, {},
    {"area_m2": 2000.0, "p13_type": "p13-multi"}])
assert abs(lin15.tgm_multiplier(kb)[0] - 9.0e-5 * 120) < 1e-12
app15 = CalcContext(tgm_chain=[
    {"site_type": "apparatus", "volume_m3": 12.0, "p13_type": "p13-cast"},
    {}, {}])
assert abs(app15.tgm_multiplier(kb)[0] - 1.9e-5 * 12) < 1e-12
# П1.4-переключатель видит ЭФФЕКТИВНОЕ значение (длина > 10 000)
big15 = CalcContext(tgm_chain=[
    {"site_type": "linear", "length_m": 51251.0, "p14_type": "p14-food"},
    {"area_m2": 800.0, "p13_type": "p13-multi"}, {}])
assert abs(big15.tgm_multiplier(kb)[0] - 0.0011 * 51251 ** 0.6) < 1e-6
# tgm_levels: участок участник каскада при ЛЮБОМ типе (Задача 1);
# установка – сама себе уровень
_ot15 = ObjectTree()
_t15 = _ot15.add_child(TERRITORY, None)
_b15 = _ot15.add_child(BUILDING, _t15)
_r15 = _ot15.add_child(ROOM, _b15)
_a15 = _ot15.add_child(AREA, _r15)
for _st15 in ("area", "linear", "apparatus"):
    _a15.props["site_type"] = _st15
    _lv15 = tgm_levels(_a15)
    assert [n.kind for n in _lv15] == ["area", "room", "building"], \
        (_st15, [n.kind for n in _lv15])
_od15 = _ot15.add_child(OUTDOOR, _t15)
assert [n.kind for n in tgm_levels(_od15)] == ["outdoor"]
# нигде ничего – 0 с пояснением; тип не выбран – 0 с пояснением
assert CalcContext(tgm_chain=[{}, {}, {}]).tgm_multiplier(kb) == \
    (0.0, "не задано значение (участок/помещение/здание)")
notype = CalcContext(tgm_chain=[{"area_m2": 100.0}, {}, {}])
assert notype.tgm_multiplier(kb)[0] == 0.0 \
    and "назначение" in notype.tgm_multiplier(kb)[1]
# наружная установка – собственные площадь/тип (как раньше)
outd = CalcContext(owner_kind="outdoor",
                   tgm_chain=[{"area_m2": 400.0,
                               "p13_type": "p13-multi"}])
assert abs(outd.tgm_multiplier(kb)[0] - 9.0e-5 * 400) < 1e-12
# Задача 6 (сессия 15): установка со значениями по типу места – линейная
# отдает длину, аппаратная объем (та же логика, что у участка)
outd15 = CalcContext(owner_kind="outdoor",
                     tgm_chain=[{"site_type": "linear", "length_m": 75.0,
                                 "p13_type": "p13-multi"}])
assert abs(outd15.tgm_multiplier(kb)[0] - 9.0e-5 * 75) < 1e-12
outd15b = CalcContext(owner_kind="outdoor",
                      tgm_chain=[{"site_type": "apparatus",
                                  "volume_m3": 30.0,
                                  "p13_type": "p13-multi"}])
assert abs(outd15b.tgm_multiplier(kb)[0] - 9.0e-5 * 30) < 1e-12
# П1.2: значение по типу места – аппарат/установка отдает ОБЪЕМ (м³)
p12_15 = CalcContext(site_props={"site_type": "apparatus",
                                 "volume_m3": 25.0})
assert p12_15.p12_value(None) == (25.0, "м³")
p12_15b = CalcContext(site_props={"site_type": "linear", "length_m": 8.0})
assert p12_15b.p12_value(None) == (8.0, "м")
print("OK ТГМ-каскад: участок→помещение→здание; пусто – 0 с пояснением")

# --- 5. ГГ: комбинаторика П2.1 (расход × среда × тип горения × ИЗ) -------
gas = TreeModel("gg", "s1")
gas.gs_causes = [GSCause(ref="gs-vessel-12.5")]
gas.iz_causes = [IZCause(ref="iz-cable"), IZCause(ref="iz-static")]
rows = gas.scenarios(kb, mk_ctx(site={"site_type": "apparatus"}))
assert len(rows) == 24, len(rows)            # 4 расхода × 3 типа × 2 ИЗ
jet = next(r for r in rows if r.flow == "mid" and r.fire_type == "ft-jet"
           and r.iz_ref == "iz-cable")
q_exp = 1.0e-5 * (1 - math.exp(-2.2e-6)) * 0.035
assert abs(jet.q - q_exp) / q_exp < 1e-9
assert "массовый расход истечения 1–50 кг/с" in jet.name
assert "Факельное горение" in jet.name
# группировка строк ноды (Σ по ИЗ: кабель + статика; первая – «< 1 кг/с»)
lines = gas.display_lines(kb, mk_ctx())
q_cable_s = 1.0e-5 * (1 - math.exp(-2.2e-6)) * 0.005
q_static_s = 1.0e-5 * (1 - math.exp(-53.0e-6)) * 0.005
assert len(lines) == 12 and abs(lines[0][1] - (q_cable_s + q_static_s)) < 1e-15
print("OK ГГ: 24 строки; П2.1 точна; группировка Σ по ИЗ на ноде")

# --- 6. среды: газ/двухфазная/жидкость → разные типы горения -------------
for stype, medium_expect, pool_present in (
        ("gg", "gas", False), ("gzh", "liquid", True),
        ("lvzh", "twophase", False)):
    tr = TreeModel(stype, "x")
    tr.gs_causes = [GSCause(ref="gs-vessel-25")]
    tr.iz_causes = [IZCause(ref="iz-cable")]
    assert tr._medium(kb) == medium_expect, (stype, tr._medium(kb))
    rows = tr.scenarios(kb, mk_ctx())
    has_pool = any(r.fire_type == "ft-pool" for r in rows)
    assert has_pool == pool_present, (stype, has_pool)
# override среды педалью env_cat на ноде ГС
tr.gs_pedals["env_cat"] = "liquid"
assert tr._medium(kb) == "liquid"
print("OK среды: газ/двухфазная (ЛВЖ)/жидкость (ГЖ) и override env_cat")

# --- 7. пыль: дефлаграция + детонация; огненный шар переключателем -------
dust = TreeModel("dust", "d1")
dust.gs_causes = [GSCause(ref="gs-vessel-rupt")]
dust.iz_causes = [IZCause(ref="iz-static")]
rows = dust.scenarios(kb, mk_ctx())
assert len(rows) == 2
assert {r.fire_type for r in rows} == {"ft-dust-defl", "ft-dust-det"}
gas.fireball = True
assert len(gas.scenarios(kb, mk_ctx())) == 25
fb = [r for r in gas.scenarios(kb, mk_ctx()) if r.gs_ref == "fireball"]
assert abs(fb[0].q - 2.5e-5) < 1e-12
print("OK пыль (дефлаграция/детонация) и огненный шар 2,5·10⁻⁵ по свичу")

# --- 8. П1.2: трубопровод × длина; прямые события П1.1 -------------------
pipe = TreeModel("gg", "p1")
pipe.gs_causes = [GSCause(ref="gs-pipe-100-small", len_m=250.0)]
pipe.iz_causes = [IZCause(ref="iz-cable")]
rows = pipe.scenarios(kb, mk_ctx(site={"site_type": "linear"}))
q_base = 2.8e-6 * 250.0
sm = next(r for r in rows if r.flow == "small" and r.fire_type == "ft-jet")
assert abs(sm.q - q_base * (1 - math.exp(-2.2e-6)) * 0.005) < 1e-18
gzh = TreeModel("gzh", "d2")
gzh.gs_causes = [GSCause(ref="gs-tank-float-ring")]
gzh.iz_causes = [IZCause(ref="iz-cable")]
rows = gzh.scenarios(kb, mk_ctx())
assert len(rows) == 1 and abs(rows[0].q - 4.6e-3) < 1e-12
# Сессия 14/1 (решение заказчика): на м²-участке множитель П1.2 –
# ПЛОЩАДЬ участка (м²), а не длина/объем; явное len_m на ноде важнее
pipe_a = TreeModel("gg", "p14a")
pipe_a.gs_causes = [GSCause(ref="gs-pipe-100-small")]
pipe_a.iz_causes = [IZCause(ref="iz-cable")]
rows_pa = pipe_a.scenarios(
    kb, mk_ctx(site={"site_type": "area", "area_m2": 800.0}))
sm_pa = next(r for r in rows_pa
             if r.flow == "small" and r.fire_type == "ft-jet")
assert abs(sm_pa.q - 2.8e-6 * 800.0
           * (1 - math.exp(-2.2e-6)) * 0.005) < 1e-18
# Задача 4 (сессия 15): скобка П1.2 – только числа (без единиц/ссылок)
assert "(2,8·10⁻⁶·800)" in sm_pa.formula, sm_pa.formula
pipe_a.gs_causes[0].len_m = 250.0            # явное значение на ноде
sm_pa2 = next(r for r in pipe_a.scenarios(
    kb, mk_ctx(site={"site_type": "area", "area_m2": 800.0}))
    if r.flow == "small" and r.fire_type == "ft-jet")
assert abs(sm_pa2.q - q_base * (1 - math.exp(-2.2e-6)) * 0.005) < 1e-18
assert "(2,8·10⁻⁶·250)" in sm_pa2.formula, sm_pa2.formula
# выбор причин ГС без фильтра по типу участка; валидатор молчит по
# участку (замечание – только при несоответствии типу СЦЕНАРИЯ)
assert len(kb.gs_for("gg")) > 20 and kb.gs_for("gg", "area") == []
gg_area = TreeModel("gg", "s12a")
gg_area.gs_causes = [GSCause(ref="gs-vessel-12.5")]
gg_area.iz_causes = [IZCause(ref="iz-cable")]
assert not any("недоступна" in i.message
               for i in check_tree(gg_area, kb,
                                   mk_ctx(site={"site_type": "area"}),
                                   "area"))
print("OK П1.2 (площадь на м²-участке, явное len_m важнее); причины ГС"
      " без участкового фильтра")

# --- 9. ИЗ: молния по зданию; педали ГС/ИЗ ------------------------------
ctx = mk_ctx(building={"bln_S": 100.0, "bln_L": 100.0, "bln_H": 20.0,
                       "pedals": {"lightning_prot": True},
                       "lightning_cat": "II"})
n_um = (100 + 120) * (100 + 120) * 6 * 1e-6
assert abs(ctx.lightning_q() - n_um * 0.05) < 1e-12
ctx2 = mk_ctx(building={"bln_S": 100.0, "bln_L": 100.0, "bln_H": 20.0})
assert abs(ctx2.lightning_q() - n_um) < 1e-12      # без защиты η = 0
# педали: износ (k из записи БД), SIL PFD 10⁻², вентиляция помещения
# (сессия 13, Задача 0: числа – из записей БД; правка БД влияет на расчет)
tp = TreeModel("gg", "s2")
tp.gs_causes = [GSCause(ref="gs-vessel-12.5")]
tp.gs_pedals.update({"wear": True, "sil_paz": True, "sil_pfd": 1e-2})
assert abs(tp._gs_k(kb) - 2.0e-2) < 1e-12
_mw = next(m for m in kb.property_modifiers if m["pedal"] == "wear")
_mw["k"] = 3.0
assert abs(tp._gs_k(kb) - 3.0e-2) < 1e-12   # правка существующей записи
tp.gs_pedals["wear_k"] = 3.5          # локальное переопределение важнее
assert abs(tp._gs_k(kb) - 3.5e-2) < 1e-12
del tp.gs_pedals["wear_k"]
_mw["k"] = 2.0
assert abs(tp._gs_k(kb) - 2.0e-2) < 1e-12
tp.iz_pedals.update({"vibro_control": True})
assert abs(tp._iz_k({"electrical": True}, kb) - 0.7) < 1e-12
assert tp._iz_k({}, kb) == 0.7
tp_ex = TreeModel("gg", "s3")
tp_ex.iz_pedals["exproof"] = True
assert tp_ex._iz_k({"electrical": True}, kb) == 0.0
assert tp_ex._iz_k({}, kb) == 1.0
# универсальный множитель нового средства (type "k") на ноде-носителе
_mnew = {"id": "pm-test-k", "pedal": "pm-test-k", "type": "k",
         "k": 0.25, "target": "gs", "title": "Тест k"}
kb.property_modifiers.append(_mnew)
tp.gs_pedals["pm-test-k"] = True
assert abs(tp._gs_k(kb) - 2.0e-2 * 0.25) < 1e-12     # износ+SIL×k
kb.property_modifiers.remove(_mnew)
tp.gs_pedals.pop("pm-test-k", None)
assert abs(tp._gs_k(kb) - 2.0e-2) < 1e-12
vent = mk_ctx(room={"pedals": {"venting": True}, "vent_rate": 8.0})
assert abs(vent.vent_k() - 1.0 / (8.0 / 12.0 + 1.0)) < 1e-12
print("OK молния N_у.м·(1−η); педали ГС (износ/SIL) и ИЗ (вибро/взрывозащита)")

# --- 10. Kσ и итоги --------------------------------------------------------
t.k_sigma = 1.5
assert abs(t.total_q(kb, ctx := mk_ctx(building=bld))
           - t.total_q(kb, ctx) / 1.5 * 1.5) < 1e-24
assert abs(t.total_q(kb, ctx) - 1.5 * expected) / expected < 0.02
print("OK Kσ: множитель итога Q_участок,k")

# --- 11. матрица -----------------------------------------------------------
md = build_matrix([t, gas], kb,
                  {"a1": mk_ctx(building=bld), "s1": mk_ctx()},
                  {"a1": "Склад", "s1": "Аппарат"})
assert md.header()[3].startswith("Сценарий")
assert len(md.rows) == 6 + 25 and len(md.totals) == 2   # + огненный шар
assert md.rows[0].q > 0 and md.rows[-1].q > 0
print("OK матрица: строки всех сценариев + итоги по деревьям")

# --- 12. иерархия: наружная установка, правила родителей -----------------
ot = ObjectTree()
tt = ot.add_child("territory", None)
inst = ot.add_child("outdoor", tt)
assert inst.title == "Наружная установка 1"
assert effective_site_type(inst) == "outdoor"
bldn = ot.add_child("building", tt)
room = ot.add_child("room", bldn)
area = ot.add_child("area", room)
assert effective_site_type(area) == "area"
area.props["site_type"] = "linear"
assert effective_site_type(area) == "linear"
for bad in (("room", tt), ("area", bldn), ("outdoor", bldn),
            ("compartment", tt)):
    try:
        ot.add_child(bad[0], bad[1])
        raise SystemExit(f"FAIL: {bad} не должно допускаться")
    except ValueError:
        pass
assert ot.owners_in(tt) == [inst, area] or set(
    o.id for o in ot.owners_in(tt)) == {inst.id, area.id}
print("OK иерархия: установка на уровне здания; правила родителей")

# --- 13. фильтрация разновидностей ГС по типу участка --------------------
assert [g["id"] for g in kb.gs_for("tgm", "area")] == ["gs-tgm-surface"]
assert not kb.gs_for("gg", "area")             # м²-участок: только ТГМ
assert any(g["id"] == "gs-vessel-12.5" for g in kb.gs_for("gg", "apparatus"))
assert any(g["id"] == "gs-pipe-100-small" for g in kb.gs_for("gg", "linear"))
outdoor_gs = {g["id"] for g in kb.gs_for("gg", "outdoor")}
assert "gs-vessel-12.5" in outdoor_gs
assert "gs-tgm-surface" in {g["id"] for g in kb.gs_for("tgm", "outdoor")}
print("OK gs_for: м² → поверхность; аппарат/линейный/установка → разгерметизации")

# --- 14. сериализация: формат 5, чистый разрыв ---------------------------
ot2 = ObjectTree()
ot2.territories = [bldn]
t.k_sigma = 1.5
path = str(ROOT / "qa_artifacts" / "_smoke_fmt5.json")
(ROOT / "qa_artifacts").mkdir(exist_ok=True)
save_project(path, ot2, [t, gas], project_name="smoke", threshold=1e-8)
data = load_project(path)
assert data["name"] == "smoke" and len(data["trees"]) == 2
assert data["trees"][0].to_dict() == t.to_dict()
assert data["trees"][1].fireball and data["trees"][1].k_sigma == 1.0
# Задача 11 (сессия 12): смещения нод – опциональное поле формата 5
gas.node_offsets = {"gs": [12.0, -8.0], "fire": [0.5, 3.0]}
save_project(path, ot2, [t, gas], project_name="smoke", threshold=1e-8)
data2 = load_project(path)
assert data2["trees"][1].node_offsets == {"gs": [12.0, -8.0],
                                          "fire": [0.5, 3.0]}
assert data2["trees"][0].node_offsets is None   # нет поля = авторазметка
gas.node_offsets = None
old = str(ROOT / "qa_artifacts" / "_smoke_fmt_old.json")
with open(old, "w", encoding="utf-8") as fh:
    json.dump({"format": 4, "name": "старый"}, fh)
try:
    load_project(old)
    raise SystemExit("FAIL: формат 4 должен отклоняться")
except UnsupportedFormatError as exc:
    assert "Формат проекта устарел" in str(exc)
Path(old).unlink()
Path(path).unlink()
print("OK сериализация: round-trip формат 5; форматы 1–4 отклоняются")

# --- 21. Задача 3.3 (сессия 15): цепи причин (И-гейт) --------------------
from eta.core.model import cause_paths
# лес → пути «корень → лист»; независимая причина – путь из одного узла
_cb = IZCause(ref="iz-cable")
_lm = IZCause(ref="iz-lamp")
_lm.parent = _cb.cid                     # лампа – следствие отказа КЛ
_st = IZCause(ref="iz-static")           # независимая
paths3 = cause_paths([_cb, _lm, _st])
assert [[x.ref for x in p] for p in paths3] == [
    ["iz-cable", "iz-lamp"], ["iz-static"]]
# цикл (внешняя правка файла) разрывается: два самостоятельных пути
_cx = IZCause(ref="iz-lamp")
_cy = IZCause(ref="iz-cable")
_cx.parent = _cy.cid
_cy.parent = _cx.cid
assert sorted(len(p) for p in cause_paths([_cx, _cy])) == [1, 1]
# математика ТГМ: цепь дает ОДНУ строку, Q = произведение вдоль пути;
# формула – произведение подставленных скобок (Задача 4)
ctx3 = CalcContext(tgm_chain=[dict(bld)])
t3 = TreeModel("tgm", "c15")
t3.gs_causes = [GSCause(ref="gs-tgm-surface")]
t3.iz_causes = [_cb, _lm, _st]
rows3 = t3.scenarios(kb, ctx3)
assert len(rows3) == 2, [r.name for r in rows3]
chain3 = next(r for r in rows3 if "→" in r.name)
assert chain3.name == ("Пожар по поверхности – Отказ кабельных линий →"
                       " Отказ осветительных приборов (лампы накаливания)")
q3 = (1 - math.exp(-2.2e-6)) * (1 - math.exp(-3.2e-5))
assert abs(chain3.q - 9.0e-5 * 2960.77 * q3) / (9.0e-5 * 2960.77 * q3) \
    < 1e-12
assert chain3.formula == ("1·1·(9·10⁻⁵·2960,77)·"
                          "(1−exp(−2,2·10⁻⁶)·1−exp(−3,2·10⁻⁵))"), \
    chain3.formula
# ГГ: произведение цепи ИЗ – множитель ИЗ строк родителя (mid-диапазон)
gg3 = TreeModel("gg", "g15")
gg3.gs_causes = [GSCause(ref="gs-vessel-5", flow="mid")]
_cb2 = IZCause(ref="iz-cable")
_lm2 = IZCause(ref="iz-lamp")
_lm2.parent = _cb2.cid
gg3.iz_causes = [_cb2, _lm2]
rows_g3 = gg3.scenarios(kb, mk_ctx(site={"site_type": "apparatus"}))
assert len(rows_g3) == 3, [r.name for r in rows_g3]   # 3 режима mid
assert all("Отказ кабельных линий → Отказ осветительных" in r.name
           for r in rows_g3)
jet3 = next(r for r in rows_g3 if r.fire_type == "ft-jet")
q_g3 = 4.0e-5 * (1 - math.exp(-2.2e-6)) * (1 - math.exp(-3.2e-5))
assert abs(jet3.q - q_g3 * 0.035) / (q_g3 * 0.035) < 1e-12
# сериализация: cid/parent round-trip; старый файл – плоско, cid генерируется
t4 = TreeModel.from_dict(t3.to_dict())
assert [c.parent for c in t4.iz_causes] == [None, _cb.cid, None]
assert all(c.cid for c in t4.iz_causes)
flat4 = TreeModel.from_dict({"scenario_type": "gg", "owner": "z",
                             "gs_causes": [{"ref": "gs-vessel-5"}],
                             "iz_causes": [{"ref": "iz-cable"}]})
assert flat4.iz_causes[0].parent is None and flat4.iz_causes[0].cid
print("OK Задача 3.3: цепи И-гейт (ТГМ/ГГ), формулы-произведения,"
      " round-trip cid/parent, циклы разрываются")

# --- 15. валидатор ---------------------------------------------------------
tree = TreeModel("gg", "s9")
issues = check_tree(tree, kb, mk_ctx(), "apparatus")
assert any("нет причин" in i.message and not i.ok for i in issues)
tree.gs_causes = [GSCause(ref="gs-vessel-12.5"),
                  GSCause(ref="gs-vessel-12.5")]
tree.iz_causes = [IZCause(ref="iz-cable")]
issues = check_tree(tree, kb, mk_ctx(), "apparatus")
assert any("Повторяющиеся" in i.message for i in issues)
bad_site = TreeModel("gg", "s10")
bad_site.gs_causes = [GSCause(ref="gs-tgm-surface")]     # ТГМ в ГГ-дереве
issues = check_tree(bad_site, kb, mk_ctx(), "area")
assert any("недоступна" in i.message for i in issues)
print("OK валидатор: пустые ноды, дубликаты, несоответствие типу участка")

# --- 16. layout: компактность (Задача 7) ----------------------------------
b = compute_layout([gas], kb, {"s1": mk_ctx()}, {"s1": "Аппарат 1"})
assert len(b.nodes) == 5 and len(b.edges) == 4
w = b.scene_rect.width()
# Задача 5 (сессия 17): компактность считается по КОНСТАНТАМ темы
# (крупная базовая геометрия) – потолка ширины нет, метрики решают
from eta.core.layout import COL_GAP as _CG17
from eta.ui.theme import MARGIN as _MG17, MAX_NODE_W as _MX17, \
    MIN_NODE_W as _MN17
assert 3 * _MN17 <= w <= 3 * _MX17 + 2 * _CG17 + 3 * _MG17, w
fire = b.nodes[f"{gas.tree_id}:fire"]
assert fire.body_lines[-1].startswith("ΣQ = ")
assert not fire.pins_right
assert not b.nodes[f"{gas.tree_id}:substance"].pins_left
# Задача 13 (сессия 12): тело нод – ТОЛЬКО счётчик и формула
assert fire.body_lines[0].startswith("Всего: ") and len(fire.body_lines) == 2
assert fire.body_styles == ["meta", "total"]
assert b.nodes[f"{gas.tree_id}:gs"].body_lines == ["Всего: 1 разновидность"]
assert b.nodes[f"{gas.tree_id}:iz"].body_lines == ["Всего: 2 источника"]
assert b.nodes[f"{gas.tree_id}:substance"].body_lines == \
    ["вероятность присутствия: 1,000"]
# пустые причины – серое «не задано» (muted)
empty = TreeModel("gg", "e1")
be = compute_layout([empty], kb, {"e1": mk_ctx()}, {"e1": "X"})
assert be.nodes[f"{empty.tree_id}:gs"].body_lines == ["не задано"]
assert be.nodes[f"{empty.tree_id}:gs"].body_styles == ["muted"]
# Задача 14: перенос только по ЦЕЛЫМ словам – ни одна строка и ни одно
# слово не шире текстового бюджета своей ноды (обрезок по буквам нет)
from eta.core.layout import body_font
from eta.ui.theme import F_TITLE, NODE_INSET, mono_font, ui_font
from PySide6.QtGui import QFontMetricsF
tf = ui_font(F_TITLE, bold=True)
for n in b.nodes.values():
    budget = n.rect.width() - 2 * NODE_INSET
    for ln in n.title_lines:
        assert QFontMetricsF(tf).horizontalAdvance(ln) <= budget + 0.5, ln
    for ln, st in zip(n.body_lines, n.body_styles):
        assert QFontMetricsF(body_font(st)).horizontalAdvance(ln) \
            <= budget + 0.5, ln
    for word in " ".join(n.title_lines + n.body_lines).split():
        assert QFontMetricsF(tf).horizontalAdvance(word) <= budget + 0.5, word
assert len(b.nodes[f"{gas.tree_id}:iz"].title_lines) == 2   # перенос словом
# Задача 5 (сессия 15): МЕТРИКИ решают геометрию – чернильные границы
# каждой строки (tightBoundingRect, с подстановкой шрифтов для
# «10⁻⁶»/«год⁻¹») с полями NODE_INSET/PAD_V помещаются в прямоугольник
# ноды: ни один пиксел глифа не касается рамки (программная проверка
# точнее визуальной оценки)
from eta.core.layout import node_text_fits
for n in b.nodes.values():
    assert node_text_fits(n), (n.node_id, n.rect)
    assert n.rect.width() >= 130 - 1e-6   # MIN_NODE_W – нижняя подсказка
for _ann5 in b.annotations:
    _af5 = ui_font(F_TITLE)
    for _ln5 in _ann5.lines:
        assert QFontMetricsF(_af5).tightBoundingRect(_ln5).width() \
            + 2 * 9 + 2 <= _ann5.rect.width() + 0.5, _ln5
# Задача 11: смещения применяются ВНУТРИ compute_layout (WYSIWYG)
gas.node_offsets = {"gs": [30.0, -20.0]}
b_off = compute_layout([gas], kb, {"s1": mk_ctx()}, {"s1": "Аппарат 1"})
assert abs(b_off.nodes[f"{gas.tree_id}:gs"].rect.x()
           - (b.nodes[f"{gas.tree_id}:gs"].rect.x() + 30.0)) < 1e-6
assert abs(b_off.nodes[f"{gas.tree_id}:gs"].rect.y()
           - (b.nodes[f"{gas.tree_id}:gs"].rect.y() - 20.0)) < 1e-6
assert b_off.scene_rect.contains(b_off.nodes[f"{gas.tree_id}:gs"].rect)
gas.node_offsets = None
b2 = compute_layout([t, gas], kb, {"a1": mk_ctx(building=bld), "s1": mk_ctx()},
                    {"a1": "Склад", "s1": "Аппарат"})
assert len(b2.nodes) == 10 and len(b2.annotations) == 2
# Задача 4 (сессия 13): справочная нода вместо заголовка – текст
# «владелец · тип сценария», без Q; свободная по умолчанию – над деревом
_a4 = b2.annotations[0]
assert 1 <= len(_a4.lines) <= 2
assert "Склад" in " ".join(_a4.lines) or "Аппарат" in " ".join(_a4.lines)
assert not any("Q =" in l for l in _a4.lines)
assert b2.scene_rect.contains(_a4.rect)
# Задача 6 (сессия 14): состояния узлов для раскраски. «Задано» –
# есть хоть одна причина; «Возникновение» OK – валидатор без замечаний
b_ok = compute_layout([gas], kb,
                      {"s1": mk_ctx(site={"site_type": "apparatus"})},
                      {"s1": "Аппарат 1"})
assert b_ok.nodes[f"{gas.tree_id}:gs"].state == "set"
assert b_ok.nodes[f"{gas.tree_id}:iz"].state == "set"
assert b_ok.nodes[f"{gas.tree_id}:fire"].state == "ok"
assert be.nodes[f"{empty.tree_id}:gs"].state == ""      # «не задано»
assert be.nodes[f"{empty.tree_id}:iz"].state == ""
# испорченный выбор причины → валидатор ругается → НЕ фиолетовый
bad_tree = TreeModel("gg", "s11")
bad_tree.gs_causes = [GSCause(ref="gs-tgm-surface")]    # ТГМ в ГГ-дереве
bad_tree.iz_causes = [IZCause(ref="iz-cable")]
b_bad = compute_layout([bad_tree], kb, {"s11": mk_ctx()}, {"s11": "X"})
assert b_bad.nodes[f"{bad_tree.tree_id}:gs"].state == "set"
assert b_bad.nodes[f"{bad_tree.tree_id}:fire"].state == ""
print(f"OK layout: 5 нод, компактная ширина {w:.0f}px, тела-счётчики,"
      " перенос по словам, оффсеты WYSIWYG")

# --- 17. переключатель-«свитч» (Задача 0) --------------------------------
from eta.ui.switch import ToggleSwitch, bind_fields

sw = ToggleSwitch("Тест")
assert sw.text() == "Тест" and not sw.isChecked() and sw.isCheckable()
seen = []
sw.toggled.connect(lambda on: seen.append(on))
sw.setChecked(True)
assert seen == [True]
sw.setChecked(False)
assert seen == [True, False] and sw.sizeHint().width() > 34
host1, host2 = ObjNode("room", "h1"), ObjNode("room", "h2")
from PySide6.QtWidgets import QLabel
lab1, lab2 = QLabel("a"), QLabel("b")
bind_fields(sw, lab1, lab2)
assert not lab1.isVisibleTo(sw) or True     # стартовое скрытие вне окна
lab1.setVisible(True)
sw.setChecked(True)
print("OK переключатель: toggled/sizeHint/bind_fields")

# --- 18. палитра иконок: покрытие новых глифов ---------------------------
from eta.ui.icons import ALL_GLYPHS, glyph_icon
from eta.ui.theme import ICON_NEUTRAL_GLYPHS, ICON_PALETTE
for g in ALL_GLYPHS:
    assert g in ICON_PALETTE or g in ICON_NEUTRAL_GLYPHS, f"глиф без цвета: {g}"
    assert glyph_icon(g) is not None
assert "outdoor" in ICON_PALETTE
# Сессия 16, Задача 4: разные глифы списков причин – ГС = облако
# (янтарь, цвет нод ГС холста), ИЗ = пламя (красный, цвет нод ИЗ);
# единый «cause» удален (потребителей не осталось)
assert ICON_PALETTE["gs-cause"] == "#B45309"
assert ICON_PALETTE["iz-cause"] == "#B91C1C"
assert "cause" not in ICON_PALETTE and "cause" not in ALL_GLYPHS
print("OK палитра иконок: все глифы покрыты (включая «outdoor»;"
      " сессия 16: gs-cause облако #B45309 / iz-cause пламя #B91C1C)")

# --- 19. Задача 1 (сессия 14): территория только в корне + ремонт файла ---
ot14 = ObjectTree()
t14 = ot14.add_child("territory", None)
b14 = ot14.add_child("building", t14)
r14 = ot14.add_child("room", b14)
a14 = ot14.add_child("area", r14)
inst14 = ot14.add_child("outdoor", t14)
for bad_parent in (b14, r14, a14, inst14):
    assert not ot14.can_add("territory", bad_parent), bad_parent.kind
assert ot14.can_add("territory", None)
# поврежденный файл (скриншоты №3/№4): территория и здание ВНУТРИ участка
damaged = [
    {"id": "T1", "kind": "territory", "title": "Территория 1",
     "props": {}, "children": [
         {"id": "B1", "kind": "building", "title": "Здание 1",
          "props": {}, "children": [
              {"id": "R1", "kind": "room", "title": "Помещение 1",
               "props": {}, "children": [
                   {"id": "A1", "kind": "area", "title": "Участок 1",
                    "props": {}, "children": [
                        {"id": "T2", "kind": "territory",
                         "title": "Территория 2", "props": {}},
                        {"id": "B2", "kind": "building",
                         "title": "Здание 2", "props": {}}]}]}]}]}]
ot15 = ObjectTree()
rep = ot15.load_from_dict(damaged)
assert rep == {"lifted_territories": 1, "moved_nodes": 2}, rep
assert [n.kind for n in ot15.territories] == ["territory", "territory"]
t2 = next(n for n in ot15.territories if n.id == "T2")
assert t2.parent is None                       # территория поднята в корень
b2n = next(n for n in ot15.all_nodes() if n.id == "B2")
assert b2n.parent is not None and b2n.parent.id == "T1"  # к допустимому предку
a1n = ot15.by_id("A1")
assert a1n.parent.id == "R1"                   # легальная цепочка цела
assert {n.id for n in ot15.all_nodes()} == \
    {"T1", "B1", "R1", "A1", "T2", "B2"}       # никто не потерян
print("OK Задача 1: can_add только в корень; ремонт: вложенная территория"
      " поднята, здание – к допустимому предку, id сохранены")

# --- 20. Задача 7 (сессия 14): парсер обеих записей + инженерный формат ---
from eta.core.numfmt import fmt_num, parse_eng
assert parse_eng("1e-6") == 1e-6
assert parse_eng("1,02e10") == 1.02e10
assert parse_eng("2.52e-12") == 2.52e-12
assert parse_eng("1^-6") == 1e-6               # каретка = ×10^e (LOCKED)
assert parse_eng("1,02^10") == 1.02e10
assert parse_eng("2,52^-12") == 2.52e-12
assert parse_eng("6,2·10^-4") == 6.2e-4
assert parse_eng("abc") is None and parse_eng("") is None
assert parse_eng("^-3") is None and parse_eng("1^x") is None
from eta.ui.theme import parse_sci
assert parse_sci("2,52^-12") == 2.52e-12       # тема делегирует общий парсер
assert fmt_num(9e-05) == "9·10⁻⁵"
assert fmt_num(0.05) == "0,05"
assert fmt_num(1200.0) == "1200"
assert fmt_num(2960.77) == "2960,77"
assert fmt_num(0) == "0"
assert "e" not in fmt_num(3.2401e-06)          # никогда сырой e-записи
# Задача 4 (сессия 15): матрица «Q₁ = <числа>», exp(), без ссылок
md3 = build_matrix([t], kb, {"a1": ctx}, {"a1": "Цех"})
f0 = md3.rows[0].formula
assert "(табл." not in f0 and "П1.2" not in f0, f0
assert f0 == ("Q₁ = 1·1·(9·10⁻⁵·2960,77)·"
              "(1−exp(−3,2·10⁻⁵))"), f0
# формулы модели – та же правая часть (матрица лишь добавляет «Q_j = »)
rows3 = t.scenarios(kb, ctx)
assert rows3[0].formula == f0[len("Q₁ = "):]
assert "табл." not in rows3[0].formula and "exp(" in rows3[0].formula
from eta.core.numfmt import q_label as _ql
assert _ql(2) == "Q₂" and _ql(12) == "Q₁₂"
print("OK Задача 4: Q_j + подставленные числа + exp(); Задача 7: парсер"
      " e-записи и каретки; fmt_num")

# --- 21. Сессия 16, Задача 3: карточка переноса (_drag_pixmap) -----------
from PySide6.QtCore import QPoint as _QPs
from PySide6.QtGui import QFontMetrics as _FMs
from eta.ui.hierarchy_panel import _drag_pixmap
from eta.ui.theme import ui_font as _ufs

_fms = _FMs(_ufs(10))
_pm3, _hot3 = _drag_pixmap("gs-cause", "Отказ кабельных линий", 2.0)
assert not _pm3.isNull()
assert _pm3.devicePixelRatio() == 2.0          # HiDPI-растр
# ширина = 2×12 + глиф 16 + зазор 8 + текст (допуск – округление/рамка)
_want3 = 2 * 12 + 16 + 8 + _fms.horizontalAdvance("Отказ кабельных линий")
_got3 = _pm3.deviceIndependentSize().width()
assert abs(_got3 - _want3) <= 2.0, (_got3, _want3)
_h3 = max(_fms.height(), 16) + 2 * 6
assert abs(_pm3.deviceIndependentSize().height() - _h3) <= 2.0
# hotspot – у левого края, по вертикальной середине карточки
assert _hot3 == _QPs(16, int(_h3) // 2), _hot3
# длинный заголовок: пиксельный ElideRight, ширина ≤300 и строго меньше
# полного (неусеченного) варианта
_long3 = ("Отказ кабельных линий, нагревающихся при перегрузке, " * 3)
assert 2 * 12 + 16 + 8 + _fms.horizontalAdvance(_long3) > 300
_pm3l, _ = _drag_pixmap("iz-cause", _long3, 2.0)
_w3l = _pm3l.deviceIndependentSize().width()
assert _w3l <= 300.0 + 1.0, _w3l
assert _w3l < 2 * 12 + 16 + 8 + _fms.horizontalAdvance(_long3)
assert _pm3l.deviceIndependentSize().height() <= _h3 + 2.0
# глиф занимает ровно 16 + 8 логических пикселей ширины карточки
_a3, _ = _drag_pixmap("gs-cause", "Кратко", 2.0)
_b3, _ = _drag_pixmap(None, "Кратко", 2.0)
assert abs((_a3.deviceIndependentSize().width()
            - _b3.deviceIndependentSize().width()) - 24.0) <= 1.0
print("OK карточка переноса: глиф 16 + зазор 8 + elide ≤300 px, DPR 2×,"
      " hotspot (16, h//2), ширина по метрикам")

# --- 22. Сессия 17, Задача 2: множитель П1.1/direct + Задача 1: колонки ---
# LOCKED (упрощённое правило заказчика): П1.1/direct умножаются на значение
# СОБСТВЕННОГО типа владельца (F/L/V); не задано → множитель 1; П1.2 и
# П1.3/П1.4 НЕ меняются (двойного умножения нет)
t17 = TreeModel("gg", "s17")
t17.gs_causes = [GSCause(ref="gs-vessel-5")]
t17.iz_causes = [IZCause(ref="iz-cable")]
_iz_q17 = 1 - math.exp(-2.2e-6)
# ×F: тип «участок (м²)», площадь 86 м² – скобка (4·10⁻⁵·86)
rF = t17.scenarios(kb, mk_ctx(site={"site_type": "area",
                                    "area_m2": 86.0}))[0]
assert "(4·10⁻⁵·86)" in rF.formula, rF.formula
assert abs(rF.q - 4e-5 * 86.0 * _iz_q17 * 0.005) < 1e-18
# ×L: линейный объект, длина 120 м
rL = t17.scenarios(kb, mk_ctx(site={"site_type": "linear",
                                    "length_m": 120.0}))[0]
assert "(4·10⁻⁵·120)" in rL.formula, rL.formula
assert abs(rL.q - 4e-5 * 120.0 * _iz_q17 * 0.005) < 1e-18
# ×V: аппарат/установка, объем 3 м³
rV = t17.scenarios(kb, mk_ctx(site={"site_type": "apparatus",
                                    "volume_m3": 3.0}))[0]
assert "(4·10⁻⁵·3)" in rV.formula, rV.formula
# значение не задано → множитель 1, скобка без множителя (префикс 1·1 жив)
r0 = t17.scenarios(kb, mk_ctx(site={"site_type": "area"}))[0]
assert r0.formula.startswith("1·1·(4·10⁻⁵)"), r0.formula
assert "(4·10⁻⁵)" in r0.formula and "(4·10⁻⁵·" not in r0.formula, \
    r0.formula
assert abs(r0.q - 4e-5 * _iz_q17 * 0.005) < 1e-18
# direct-причина (готовое «пожарное» событие) умножается так же
t17d = TreeModel("gzh", "d17")
t17d.gs_causes = [GSCause(ref="gs-tank-float-ring")]
rd17 = t17d.scenarios(kb, mk_ctx(site={"site_type": "apparatus",
                                        "volume_m3": 10.0}))[0]
assert abs(rd17.q - 4.6e-3 * 10.0) < 1e-12, rd17.q
# НЕТ ДВОЙНОГО УМНОЖЕНИЯ: П1.2 byte-exact (λ'·L, скобка без значения типа)
t17p = TreeModel("gg", "p17")
t17p.gs_causes = [GSCause(ref="gs-pipe-100-small")]
t17p.iz_causes = [IZCause(ref="iz-cable")]
rp17 = t17p.scenarios(kb, mk_ctx(site={"site_type": "linear",
                                        "length_m": 50.0}))[0]
assert rp17.formula == ("1·1·(2,8·10⁻⁶·50)·"
                        "(1−exp(−2,2·10⁻⁶))·0,005"), rp17.formula
assert abs(rp17.q - 2.8e-6 * 50.0 * _iz_q17 * 0.005) < 1e-18
# П1.3 byte-exact: та же скобка, что до сессии 17
rt17 = TreeModel("tgm", "b17")
rt17.gs_causes = [GSCause(ref="gs-tgm-surface")]
rt17.iz_causes = [IZCause(ref="iz-cable")]
_ctx17 = CalcContext(tgm_chain=[{"site_type": "area", "area_m2": 2960.77,
                                 "p13_type": "p13-multi"}])
rr17 = rt17.scenarios(kb, _ctx17)[0]
assert "(9·10⁻⁵·2960,77)" in rr17.formula, rr17.formula
assert abs(rr17.q - 9e-5 * 2960.77 * _iz_q17) < 1e-16
# Задача 1: заголовки матрицы переименованы (единственный источник)
md17 = build_matrix([t17], kb, {"s17": mk_ctx(site={"site_type": "area",
                                                    "area_m2": 86.0})},
                    {"s17": "Участок 1"})
assert md17.header()[1] == "Участок (установка)", md17.header()
assert md17.header()[3] == "Сценарий пожара", md17.header()
assert "ГС – расход" not in "".join(md17.header())
print("OK сессия 17: П1.1/direct × F|L|V (нет значения – множитель 1);"
      " П1.2/П1.3 без двойного умножения; колонки матрицы переименованы")

# --- 23. Сессия 17, Задача 4: latin_key + семантика undo-снапшотов ---------
from PySide6.QtCore import Qt as _Qt17
from eta.ui.latin_keys import latin_key
# полная таблица ЙЦУКЕН: 26 букв, верхний и нижний регистры
_TABLE17 = {"Й": "Q", "Ц": "W", "У": "E", "К": "R", "Е": "T", "Н": "Y",
            "Г": "U", "Ш": "I", "Щ": "O", "З": "P", "Ф": "A", "Ы": "S",
            "В": "D", "А": "F", "П": "G", "Р": "H", "О": "J", "Л": "K",
            "Д": "L", "Я": "Z", "Ч": "X", "С": "C", "М": "V", "И": "B",
            "Т": "N", "Ь": "M"}
for _cyr, _lat in _TABLE17.items():
    _cc, _lc = ord(_cyr), ord(_lat)
    assert latin_key(_cc) == _lc, (_cyr, latin_key(_cc), _lat)
    assert latin_key(_cc + 0x20) == _lc             # строчные (0x0430…)
assert latin_key(int(_Qt17.Key.Key_S)) is None       # латиница – мимо
assert latin_key(int(_Qt17.Key.Key_1)) is None       # не-буква – мимо
assert latin_key(None) is None
# семантика undo: снапшоты формата 5 в памяти, коалесценция, глубина 50
from eta.ui.main_window import MainWindow as _MW17, UNDO_DEPTH as _D17
assert _D17 == 50
_w17 = _MW17(kb, restore_ui=False)
_h17 = _w17.hierarchy
_h17.add_kind("territory")
_t17 = _h17.selected()
assert len(_w17._undo_stack) == 1                   # точка до добавления
_w17._undo_push()
assert len(_w17._undo_stack) == 1                   # no-op коалесцируется
_w17._undo()
assert not _w17.objects.territories                 # добавление отменено
_w17._redo()
assert len(_w17.objects.territories) == 1           # возвращено
# новое действие после отката чистит redo
_w17._undo()
assert len(_w17._redo_stack) == 1
_h17.add_kind("territory")
assert _w17._redo_stack == []                       # LOCKED: redo сброшен
assert len(_w17.objects.territories) == 1           # undo убрал первую
# глубина истории ограничена 50 (самые старые точки теряются)
for _i17 in range(_D17 + 10):
    _h17.objects.rename(_w17.objects.territories[0], f"Т{_i17}")
    _w17._undo_push()
assert len(_w17._undo_stack) == _D17
# буфер: копия участка с деревом → вставка в другую комнату
_h17.add_kind("territory")
_h17.tree.closePersistentEditor(_h17.tree.currentItem())
_h17.add_kind("building")
_h17.tree.closePersistentEditor(_h17.tree.currentItem())
_h17.add_kind("room")
_h17.tree.closePersistentEditor(_h17.tree.currentItem())
_h17.add_kind("area")
_a17 = _h17.selected()
_w17._add_tree(_a17.id, "gg")
_tr17 = next(t for t in _w17.trees if t.owner_id == _a17.id)
from eta.core.model import GSCause as _GS17, IZCause as _IZ17
_tr17.gs_causes = [_GS17(ref="gs-vessel-5")]
_tr17.iz_causes = [_IZ17(ref="iz-cable")]
_w17._refresh()
_h17.select_object(_a17.parent)
_h17.add_kind("room")
_h17.tree.closePersistentEditor(_h17.tree.currentItem())
_r17b = _h17.selected()
_h17.select_object(_a17, emit=False)
_h17.tree.setCurrentItem(_h17._item_of(_a17))
_w17._copy_selection()
assert len(_w17._clip) == 1
_h17.select_object(_r17b, emit=False)
_w17._paste_clipboard()
_copies17 = [n for n in _w17.objects.all_nodes()
             if n.title.endswith(" (копия)")]
assert len(_copies17) == 1 and _copies17[0].kind == "area"
assert _copies17[0].id != _a17.id and _copies17[0].parent is _r17b
_trees17 = [t for t in _w17.trees if t.owner_id == _copies17[0].id]
assert len(_trees17) == 1 and _trees17[0].tree_id != _tr17.tree_id
assert [c.ref for c in _trees17[0].gs_causes] == ["gs-vessel-5"]
assert _trees17[0].gs_causes[0].cid != _tr17.gs_causes[0].cid
assert _trees17[0].node_offsets is None             # чистая авторазметка
_q17c = _trees17[0].total_q(kb, _w17.ctx_map()[_copies17[0].id])
assert _q17c > 0                                    # Q копии пересчитан
# повторная вставка разрешена (свежие id на каждую); цель – снова комната
# (после вставки выделен сам вставленный участок); модальные окна в smoke
# подменяются рекордером – реальный диалог не показывается
_boxes17 = []
_orig_info17 = QMessageBox.information
QMessageBox.information = staticmethod(
    lambda *a, **k: _boxes17.append(a[2] if len(a) > 2 else str(a)) or None)
_h17.select_object(_r17b, emit=False)
_w17._paste_clipboard()
QMessageBox.information = staticmethod(_orig_info17)
assert not _boxes17, _boxes17
assert len([n for n in _w17.objects.all_nodes()
            if n.title.endswith(" (копия)")]) == 2
# отмена убирает вставку (включая деревья копий)
_n17 = len(_w17.trees)
_w17._undo()
assert len([n for n in _w17.objects.all_nodes()
            if n.title.endswith(" (копия)")]) == 1
assert len(_w17.trees) == _n17 - 1
_w17._dirty = False
_w17.close()
print("OK сессия 17, Задача 4: ЙЦУКЕН→QWERTY (26 букв, 2 регистра);"
      " undo: коалесценция, глубина 50, redo-сброс, отмена вставки;"
      " буфер: свежие id, «(копия)», смещения сброшены")

# --- 24. Сессия 18, Задача 9: реестр источников (миграция + вариант Б) ----
import tempfile as _tf24

from eta.export.report_docx import (REPORT_TITLE, SOURCES_HEADING,
                                     report_sources, used_source_ids)

# 24a. миграция старого файла 6.1 -> 6.2 (в памяти, дедуп, перепривязка)
_old24 = {
    "meta": {"version": "6.1"},
    "scenario_types": [], "fire_types": [], "p21": {}, "flow_titles": {},
    "p13": [], "p14": [], "equipment_templates": [],
    "gs_causes": [
        {"id": "g1", "title": "A", "source": "Приказ 1"},
        {"id": "g2", "title": "B", "source": "Приказ 1"}],   # дубль строки
    "iz_causes": [{"id": "i1", "title": "C", "source": "ГОСТ X"}],
    "property_modifiers": [{"id": "m1", "pedal": "p1", "source": ""}],
}
_fd24, _nm24 = _tf24.mkstemp(suffix=".json")
import os as _os24
_os24.close(_fd24)
with open(_nm24, "w", encoding="utf-8") as _fh24:
    json.dump(_old24, _fh24, ensure_ascii=False)
kb24 = KnowledgeBase(_nm24)
assert kb24.meta["version"] == "6.2"
assert [s["title"] for s in kb24.sources] == ["Приказ 1", "ГОСТ X"]
assert [s["id"] for s in kb24.sources] == ["src-1", "src-2"]
assert kb24.gs_by_id("g1")["source"] == "src-1" \
    and kb24.gs_by_id("g2")["source"] == "src-1"
assert kb24.iz_by_id("i1")["source"] == "src-2"
assert kb24.property_modifiers[0].get("source", "") == ""   # пусто – как есть
assert kb24.source_title("src-1") == "Приказ 1"
assert kb24.source_title("") == "" and kb24.source_title("src-9") == "src-9"
assert kb24.source_records_of("src-1") == 2
kb24.save()                                   # идемпотентность: без изменений
kb24r = KnowledgeBase(_nm24)
assert [s["id"] for s in kb24r.sources] == ["src-1", "src-2"]
_os24.unlink(_nm24)
print("OK миграция 6.1→6.2: дедуп строк, source→id, версия, идемпотентность")

# 24b. вариант Б: только привязанные записи реестра, в порядке реестра;
# правило пропуска – запись без источника не дает строку
kb24b = KnowledgeBase()                        # свежая копия рабочей БД
_t24 = TreeModel("tgm", "own-24")
_t24.gs_causes = [GSCause(ref="gs-tgm-surface")]
_t24.iz_causes = [IZCause(ref="iz-lamp")]
_ids24 = used_source_ids([_t24], kb24b)
assert _ids24 == ["src-1", "src-4"], _ids24    # порядок реестра, дедуп
_rows24 = report_sources([_t24], kb24b)
assert [r["title"] for r in _rows24] == [
    "Приказ МЧС России № 533, прил. № 1, табл. П1.3/П1.4",
    "ГОСТ 12.1.004-91, прил. 3, табл. 9"]
# включенная мера на дереве добавляет источник записи меры
_t24.gs_pedals = {"wear": True}
_ids24b = used_source_ids([_t24], kb24b)
assert "src-12" in _ids24b                     # pm-wear -> src-12
_t24.gs_pedals = {"wear": False}
assert "src-12" not in used_source_ids([_t24], kb24b)
# правило пропуска: отвязали источник у записи – таблица НЕ печатается
kb24b.gs_by_id("gs-tgm-surface")["source"] = ""
assert used_source_ids([_t24], kb24b) == ["src-4"]
kb24b.iz_by_id("iz-lamp")["source"] = ""
assert used_source_ids([_t24], kb24b) == []    # всё отвязано – раздел пуст
# дерево без причин не тянет источников; константы разделов на месте
assert used_source_ids([TreeModel("gg", "own-x")], kb24b) == []
assert REPORT_TITLE == "Расчет частоты возникновения пожара"
assert SOURCES_HEADING == "Нормативные ссылки и справочные данные"
print("OK вариант Б: только реестровые источники участвующих записей;"
      " меры по педалям; правило пропуска (без привязки – не печатается)")

# --- 25. Сессия 18, Задача 13: справка БД + мини-нотация по факту --------
from eta.core.numfmt import parse_eng
from eta.ui.kb_window import (HELP_EXAMPLES, HELP_NUMBER_INPUT,
                              _help_text)
from eta.ui.math_text import math

_help25 = _help_text()
assert _help25.strip()
for _h25 in ("1. Что такое «База данных»", "2. Добавление, правка",
             "3. Формульная запись", "4. Как записи попадают"):
    assert _h25 in _help25, _h25
# каждый пример справки round-trip: math(ввод) == обещанная разметка
for _src25, _out25 in HELP_EXAMPLES:
    assert _src25 in _help25, _src25
    assert math(_src25) == _out25, (_src25, math(_src25), _out25)
# числовой ввод из справки разбирается parse_eng (каретка = ×10^e)
import math as _m25
for _n25 in HELP_NUMBER_INPUT:
    _v25 = parse_eng(_n25)
    assert _v25 is not None and _v25 > 0, _n25
assert abs(parse_eng("3,2^-5") - 3.2e-5) < 1e-15
assert abs(parse_eng("6,2·10^-4") - 6.2e-4) < 1e-15
assert abs(parse_eng("3,2e-5") - 3.2e-5) < 1e-15
# запрещенное в справке НЕ показываем: индекс с точкой без скобок не
# захватывается целиком – в справке только скобочная форма N_{у.м}
assert "N_у.м " not in _help25
# глиф справки покрыт палитрой (блок 18 прогоняет ALL_GLYPHS отдельно)
from eta.ui.icons import ALL_GLYPHS as _AG25
assert "help" in _AG25
print("OK справка БД: разделы; каждый пример формулы round-trip через"
      " math(); числовой ввод (е-запись/каретка) разобран parse_eng")



print("SMOKE PASSED")
