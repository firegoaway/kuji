# -*- coding: utf-8 -*-
"""Матрица сценариев (сессия 10): строки-сценарии всех деревьев проекта
или выбранного участка/сценария с частотами и формулами.

Замещает матрицу «причины × ветви» сессий 5–9: правого крыла с
защитными средствами больше нет, каждая строка – комбинация
«ГС × расход × тип горения × ИЗ» из TreeModel.scenarios().

Задача 4 (сессия 15): формула – полностью подставленные числа с
индексом строки Q_j (номер = колонка «№»; отчетный лист PDF нумерует
строки так же). Табличных ссылок в формулах больше нет вовсе – ссылки
живут в исходных данных и блоке источников отчета.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .numfmt import q_label


@dataclass
class MatrixRow:
    tree_id: str
    title: str          # владелец (участок/установка)
    scenario_type: str  # tgm|gg|gzh|lvzh|dust
    name: str           # «Разгерметизация … – расход – тип – ИЗ»
    q: float
    formula: str


@dataclass
class MatrixData:
    rows: list[MatrixRow] = field(default_factory=list)
    totals: list[tuple[str, str, float]] = field(default_factory=list)
    # (tree_id, титул дерева, ΣQ×Kσ)

    def header(self) -> list[str]:
        # Задача 1 (сессия 17): колонки переименованы (LOCKED) –
        # «Сценарий (ГС – расход – тип горения – ИЗ)» → «Сценарий
        # пожара», «Участок/установка» → «Участок (установка)»
        return ["№", "Участок (установка)", "Тип сценария",
                "Сценарий пожара",
                "Q, год⁻¹", "Формула"]


def build_matrix(trees: list, kb, ctx_map: dict,
                 owner_titles: dict[str, str] | None = None) -> MatrixData:
    """Матрица по списку деревьев (обычно – деревья выделенного узла).
    Задача 4 (сессия 15): колонка «Формула» = «Q_j = <подставленные
    числа>», j – сквозной номер строки (совпадает с колонкой «№» и с
    нумерацией расчетных строк PDF-отчета)."""
    owner_titles = owner_titles or {}
    data = MatrixData()
    idx = 0
    for tree in trees:
        ctx = ctx_map.get(tree.owner_id)
        if ctx is None:
            from .model import CalcContext
            ctx = CalcContext()
        st = kb.scenario_type_by_id(tree.scenario_type) or {}
        title = owner_titles.get(tree.owner_id, "Участок")
        for r in tree.scenarios(kb, ctx):
            idx += 1
            data.rows.append(MatrixRow(
                tree_id=tree.tree_id, title=title,
                scenario_type=st.get("substance", tree.scenario_type),
                name=r.name, q=r.q,
                formula=f"{q_label(idx)} = {r.formula}"))
        data.totals.append((tree.tree_id,
                            f"{title} · {st.get('title', '')}",
                            tree.total_q(kb, ctx)))
    return data
