# -*- coding: utf-8 -*-
"""Валидация логического дерева событий (сессия 10).

Структура дерева фиксирована (инвариант пяти типов сценариев), поэтому
проверяются не «фазы» и не логические элементы, а:
  * наличие причин в нодах ГС/ИЗ;
  * дубликаты разновидностей внутри ноды;
  * соответствие разновидностей ГС типу участка (м²/м/м³/установка)
    и типу сценария;
  * заполненность контекста расчета (площадь/тип здания для ТГМ).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CheckResult:
    ok: bool
    message: str


def check_tree(tree, kb, ctx, site_kind: str = "area") -> list[CheckResult]:
    """Список замечаний по дереву (пустой – всё в порядке)."""
    out: list[CheckResult] = []

    if not tree.gs_causes:
        out.append(CheckResult(
            False, "В ноде «Образование горючей среды» нет причин –"
                   " добавьте разновидность кнопкой «Добавить причину»"))
    if not tree.iz_causes:
        out.append(CheckResult(
            False, "В ноде «Появление источника зажигания» нет причин –"
                   " добавьте разновидность кнопкой «Добавить причину»"))

    # Задача 8 (сессия 15): дубликат = та же запись И ТОТ ЖЕ диапазон
    # расхода; Задача 3.3: одна и та же запись может висеть зависимой
    # ветвью под разными родителями – дублем НЕ считается
    pairs = [(c.ref, c.flow, c.parent) for c in tree.gs_causes]
    dup = {p for p in pairs if pairs.count(p) > 1}
    if dup:
        def _pair_title(item: tuple) -> str:
            ref, flow, _parent = item
            t = (kb.gs_by_id(ref) or {}).get("title", ref)
            if flow and kb.flow_titles.get(flow):
                t += f" – {kb.flow_titles[flow]}"
            return t
        titles = ", ".join(_pair_title(p) for p in dup)
        out.append(CheckResult(
            False, f"Повторяющиеся причины ГС: {titles}"))
    refs_iz = [c.ref for c in tree.iz_causes]
    dup_iz = {r for r in refs_iz if refs_iz.count(r) > 1}
    if dup_iz:
        titles = ", ".join((kb.iz_by_id(r) or {}).get("title", r)
                           for r in dup_iz)
        out.append(CheckResult(
            False, f"Повторяющиеся причины ИЗ: {titles}"))

    # Сессия 14/1 (решение заказчика): причины ГС доступны на ЛЮБОМ
    # участке (включая м²) – проверяется только соответствие типу
    # СЦЕНАРИЯ; тип участка больше не «ловушка»
    available = {g["id"] for g in kb.gs_for(tree.scenario_type)}
    for c in tree.gs_causes:
        if c.ref not in available and c.ref != "fireball":
            g = kb.gs_by_id(c.ref) or {}
            out.append(CheckResult(
                False, f"Причина «{g.get('title', c.ref)}» недоступна"
                       " для этого типа участка/сценария"))
    known = {i["id"] for i in kb.iz_causes}
    for c in tree.iz_causes:
        if c.ref not in known:
            out.append(CheckResult(
                False, f"Неизвестная причина ИЗ: {c.ref}"))

    if tree.scenario_type == "tgm":
        v, note = ctx.tgm_multiplier(kb)
        if v <= 0:
            out.append(CheckResult(
                False, f"Множитель ТГМ не рассчитан: {note} – заполните"
                        " значение (по типу участка) и тип на участке,"
                        " в помещении или здании (первое явное значение"
                        " уровня)"))

    if not (1.0 <= float(tree.k_sigma) <= 3.0):
        out.append(CheckResult(
            False, "Kσ вне разумного диапазона (методика рекомендует"
                   " 1,2–2,0)"))
    return out
