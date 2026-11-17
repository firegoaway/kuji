# -*- coding: utf-8 -*-
"""Загрузчик базы знаний (knowledge_base.json), схема 6.0 (сессия 10).

Парадигма «пяти инвариантных типов сценариев»: база содержит
разновидности причин ГС (П1.1/П1.2/ТГМ-поверхность), разновидности
источников зажигания (табл. 9 прил. 3 ГОСТ 12.1.004-91 + молния +
нагретые вещества), типы горения с привязкой к табл. П2.1, таблицы
П1.3/П1.4 (частоты пожаров в зданиях), шаблоны оборудования для потока
«Применить на холсте» и защитные меры/поправочные коэффициенты
(поле target – куда переносится переключатель: gs|iz|room|building).

База редактируема в памяти; `save()` атомарно перезаписывает файл,
`reload()` перечитывает и пересобирает справочники.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge" / "knowledge_base.json"

# Задача 9 (сессия 18, LOCKED): разделы, чьи записи несут поле source –
# порядок фиксирует нумерацию реестра при миграции (ГС, ИЗ, меры)
_SOURCE_SECTIONS = ("gs_causes", "iz_causes", "property_modifiers")


class KnowledgeBase:
    def __init__(self, path: Path | str | None = None):
        self.path = Path(path) if path else KB_PATH
        self._load()

    # ---------- загрузка / сохранение ----------
    def _load(self) -> None:
        with open(self.path, encoding="utf-8") as fh:
            self.data: dict = json.load(fh)
        # Задача 9: старый файл (схема 6.1, без реестра источников)
        # открывается прозрачно – миграция в памяти, без записи на диск
        self._migrate_sources()
        self._reindex()

    def _migrate_sources(self) -> None:
        """Миграция схемы 6.1 → 6.2 (Задача 9, LOCKED вариант Б).

        Различающиеся непустые строки source записей ГС/ИЗ/мер
        собираются в новый раздел sources: [{id, title}] (идентификаторы
        src-1, src-2, … в порядке первого встречания – детерминированно),
        поле source каждой записи заменяется на id записи реестра,
        meta.version → «6.2». Идемпотентно (раздел уже есть – ничего не
        делает); на диск пишется ТОЛЬКО явным «Сохранить» окна базы."""
        if self.data.get("sources"):
            return
        seen: dict[str, str] = {}          # строка → id, порядок сохранен
        for sec in _SOURCE_SECTIONS:
            for rec in self.data.get(sec, []):
                s = str(rec.get("source", "") or "").strip()
                if s and s not in seen:
                    seen[s] = f"src-{len(seen) + 1}"
        self.data["sources"] = [{"id": i, "title": t}
                                for t, i in seen.items()]
        for sec in _SOURCE_SECTIONS:
            for rec in self.data.get(sec, []):
                s = str(rec.get("source", "") or "").strip()
                if s:
                    rec["source"] = seen[s]
        self.data.setdefault("meta", {})["version"] = "6.2"

    def _reindex(self) -> None:
        self.meta: dict = self.data.get("meta", {})
        self.scenario_types: list[dict] = self.data.get("scenario_types", [])
        self.gs_causes: list[dict] = self.data.get("gs_causes", [])
        self.iz_causes: list[dict] = self.data.get("iz_causes", [])
        self.fire_types: list[dict] = self.data.get("fire_types", [])
        self.p21: dict = self.data.get("p21", {})
        self.flow_titles: dict = self.data.get("flow_titles", {})
        self.p13: list[dict] = self.data.get("p13", [])
        self.p14: list[dict] = self.data.get("p14", [])
        self.equipment_templates: list[dict] = self.data.get(
            "equipment_templates", [])
        self.property_modifiers: list[dict] = self.data.get(
            "property_modifiers", [])
        # Задача 9 (сессия 18): реестр источников
        self.sources: list[dict] = self.data.get("sources", [])

        self._stype_by_id = {t["id"]: t for t in self.scenario_types}
        self._gs_by_id = {g["id"]: g for g in self.gs_causes}
        self._iz_by_id = {i["id"]: i for i in self.iz_causes}
        self._ft_by_id = {f["id"]: f for f in self.fire_types}
        self._tpl_by_id = {e["id"]: e for e in self.equipment_templates}
        self._p13_by_id = {r["id"]: r for r in self.p13}
        self._p14_by_id = {r["id"]: r for r in self.p14}
        self._src_by_id = {s["id"]: s for s in self.sources}
        self._modifier_by_pedal = {m["pedal"]: m for m in self.property_modifiers
                                   if m.get("pedal")}

    def reload(self) -> None:
        """Перечитать файл (старт приложения / после сохранения)."""
        self._load()

    def reindex(self) -> None:
        """Пересобрать индексы после прямых правок списков данных
        (библиотеки ИЗ/ГС/мер редактируют kb.data на лету – индексы
        _gs_by_id/_iz_by_id/_modifier_by_pedal обязаны видеть записи
        сразу, до «Сохранить»; сессия 13, Задачи 0/9/10)."""
        self._reindex()

    def save(self) -> None:
        """Атомарно перезаписать knowledge_base.json текущими данными."""
        fd, tmp_name = tempfile.mkstemp(
            prefix=self.path.stem + "~", suffix=".tmp", dir=str(self.path.parent))
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                json.dump(self.data, fh, ensure_ascii=False, indent=2)
            os.replace(tmp_name, self.path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise

    # ---------- справочники новой схемы ----------
    def scenario_type_by_id(self, tid: str) -> dict | None:
        return self._stype_by_id.get(tid)

    def gs_by_id(self, gid: str) -> dict | None:
        return self._gs_by_id.get(gid)

    def iz_by_id(self, iid: str) -> dict | None:
        return self._iz_by_id.get(iid)

    def fire_type_by_id(self, fid: str) -> dict | None:
        return self._ft_by_id.get(fid)

    def template_by_id(self, eid: str) -> dict | None:
        return self._tpl_by_id.get(eid)

    def gs_for(self, stype: str, site_kind: str | None = None) -> list[dict]:
        """Разновидности ГС, доступные дереву типа stype (и типу участка).
        Наружная установка – самостоятельный аппарат: доступны и
        «поверхностные» (ТГМ), и разгерметизационные разновидности."""
        if site_kind == "outdoor":
            allowed = {"area", "apparatus", "outdoor"}
        elif site_kind is not None:
            allowed = {site_kind}
        else:
            allowed = None
        out = []
        for g in self.gs_causes:
            if stype not in g.get("applies", []):
                continue
            if allowed is not None and not (set(g.get("site_kinds",
                                                       ["apparatus"]))
                                            & allowed):
                continue
            out.append(g)
        return out

    # ---------- Задача 8 (сессия 15): развертка по расходу (П2.1) --------
    def flow_variants(self, rec: dict) -> list:
        """Диапазоны массового расхода истечения записи ГС (табл. П2.1):
        * разгерметизационная запись (p11/p12, не direct) с «полным
          разрушением»/«разрывом» в названии – ОДНА строка «rupt»
          (диапазон «полный разрыв»);
        * прочая разгерметизационная (отверстие/утечка) – ТРИ строки
          small/mid/big (< 1 / 1–50 / > 50 кг/с);
        * direct-события П1.1 и ТГМ-поверхность (p13) – одна строка
          БЕЗ диапазона (None): ветвления по расходу нет.
        Скорость сгорания из сессии 10 заменена на термин методики
        «массовый расход истечения» (Задача 8.4, проверка по прил. 2)."""
        kind = rec.get("kind", "p11")
        if kind in ("direct", "p13"):
            return [None]
        title = rec.get("title", "")
        if "полное разрушение" in title or "разрыв" in title:
            return ["rupt"]
        return ["small", "mid", "big"]

    def flow_row_title(self, rec: dict, flow: str | None) -> str:
        """Подпись развернутой строки (Задача 8.1): подчасти названия
        после двоеточия – с заглавной («Разгерметизация, Отверстие
        5 мм»); суффикс диапазона расхода после тире – у диапазонных
        строк (у «полного разрыва» диапазон уже в названии, у
        безрасходных суффикса нет)."""
        title = rec.get("title", rec.get("id", ""))
        head, sep, sub = title.partition(": ")
        if sep:
            sub = ", ".join(p[:1].upper() + p[1:]
                            for p in sub.split(", "))
            title = head + ": " + sub
        if flow is not None and flow != "rupt":
            title += f" – {self.flow_titles.get(flow, flow)}"
        return title

    def iz_all(self) -> list[dict]:
        return list(self.iz_causes)

    def fire_for(self, stype: str) -> list[dict]:
        return [f for f in self.fire_types if stype in f.get("applies", [])]

    def p13_by_id(self, rid: str) -> dict | None:
        return self._p13_by_id.get(rid)

    def p14_by_id(self, rid: str) -> dict | None:
        return self._p14_by_id.get(rid)

    def modifier_by_pedal(self, pedal: str) -> dict | None:
        """Модификатор свойств по ключу педальки."""
        return self._modifier_by_pedal.get(pedal)

    def modifiers_for_target(self, target: str) -> list[dict]:
        """Меры, чьи переключатели живут на данном носителе
        (gs – нода ГС, iz – нода ИЗ, room – помещение, building – здание)."""
        return [m for m in self.property_modifiers
                if m.get("target") == target]

    # ---------- Задача 9 (сессия 18): реестр источников ----------
    def source_by_id(self, sid: str) -> dict | None:
        return self._src_by_id.get(sid)

    def source_title(self, value) -> str:
        """Отображаемое имя источника записи: id из реестра → название;
        любая другая непустая строка (наследие старых файлов) – как есть;
        пусто/нет – «». Единая точка разрешения для UI и отчета."""
        if not value:
            return ""
        s = str(value)
        e = self._src_by_id.get(s)
        return e.get("title", "") if e else s

    def source_records_of(self, sid: str) -> int:
        """Сколько записей ГС/ИЗ/мер ссылаются на источник (счетчик
        использования для предупреждения при удалении)."""
        return sum(1 for sec in _SOURCE_SECTIONS
                   for rec in self.data.get(sec, [])
                   if rec.get("source") == sid)
