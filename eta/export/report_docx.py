# -*- coding: utf-8 -*-
"""Единый DOCX-отчет «Куджи» (Задача 11, сессия 18; LOCKED).

ОДИН проект = ОДИН docx. PDF-экспорт упразднен; новый конвейер:

  1. КОНТЕНТ-МОДЕЛЬ (чистые функции, тестируются smoke-блоками без
     pandoc): разделы по дереву иерархии объектов, «Нормативные
     ссылки и справочные данные» (Задача 9, вариант Б), параметры
     расчета, исходные данные, результаты, матрица.
  2. Промежуточный Markdown + сырые блоки OOXML (```{=openxml}):
     титульная страница точными кеглями (18/12 pt), разрывы страниц и
     НАСТОЯЩЕЕ поле оглавления Word (TOC \\o "1-3"; пользователь
     обновляет его сам – ПКМ → «Обновить поле»).
  3. Встроенный pandoc (runtime\\pandoc\\pandoc.exe, 3.4; внешний путь
     НЕ используется) с --reference-doc=eta\\export\\reference.docx –
     шаблон получен ОДИН раз из ГОСТ Р 21.101-донца (рамки и штампы в
     колонтитулах, Times New Roman, синие заголовки, A4 портрет);
     pandoc сохраняет sectPr/колонтитулы шаблона (проверено пробой).

Правила текста (Задачи 3–7, LOCKED): заголовок «Расчет частоты
возникновения пожара» (18 pt) + «Куджи v… от dd.mm.yyyy» (12 pt) –
единственные строки титула; НЕТ «Объект расчёта: …» и строки
проекта/даты; колонка «Источник» – без квадратных скобок, пустой –
«–»; Kσ и «Огненный шар: включен» – отдельными строками (строка
огненного шара – только при включенном переключателе).
"""

from __future__ import annotations

import subprocess
import tempfile
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape as _x

from .. import __version__
from ..core.objects import KIND_TITLES

# Задача 3 (LOCKED): заголовок документа – титул и вершина модели
REPORT_TITLE = "Расчет частоты возникновения пожара"

# Раздел «Нормативные ссылки и справочные данные» (Задача 9)
SOURCES_HEADING = "Нормативные ссылки и справочные данные"

# Расчетный раздел (иерархия объектов)
CALC_HEADING = "Расчет частоты возникновения пожара"

# Раздел схем и матриц
TREE_HEADING = "Логическое дерево событий"

# Задача 4 (LOCKED): строка «Параметров расчета» при включенном шаре
FIREBALL_LINE = "Огненный шар: включен"

# Задача 10 (LOCKED): форматы листа схемы – ровно шесть
PAGE_FORMATS: dict[str, tuple[float, float]] = {
    "A4P": (210.0, 297.0), "A4L": (297.0, 210.0),
    "A3P": (297.0, 420.0), "A3L": (420.0, 297.0),
    "A2P": (420.0, 594.0), "A2L": (594.0, 420.0),
}
FORMAT_LABELS: dict[str, str] = {
    "A4P": "ISO A4 – 210 × 297 мм (книжная)",
    "A4L": "ISO A4 – 297 × 210 мм (альбомная)",
    "A3P": "ISO A3 – 297 × 420 мм (книжная)",
    "A3L": "ISO A3 – 420 × 297 мм (альбомная)",
    "A2P": "ISO A2 – 420 × 594 мм (книжная)",
    "A2L": "ISO A2 – 594 × 420 мм (альбомная)",
}
SCHEMA_DPI = 300.0

# Пути конвейера (внедренные ресурсы, внешние каталоги не нужны)
PANDOC_EXE = Path(__file__).resolve().parents[2] / "runtime" / "pandoc" \
    / "pandoc.exe"
REFERENCE_DOCX = Path(__file__).resolve().parent / "reference.docx"

# Ширина колонки текста reference.docx: A4 (11906 twips) – поля
# 1418+567 twips = 9921 twips ≈ 175 мм ≈ 661 px при 96 dpi
_TEXT_COL_PX = 655


# =====================================================================
# Задача 9 (LOCKED вариант Б): источники участвующих записей
# =====================================================================
def used_source_ids(trees: list, kb, objects=None) -> list[str]:
    """Вариант Б (LOCKED, Задача 9): id записей РЕЕСТРА источников,
    привязанных к записям, УЧАСТВУЮЩИМ в расчете данного проекта:

      * причины ГС/ИЗ деревьев проекта (записи, на которые ссылаются
        причины любых деревьев);
      * ВКЛЮЧЕННЫЕ защитные меры – педали деревьев (gs_pedals/iz_pedals)
        и педали в свойствах объектов иерархии (props["pedals"]).

    Дедупликация; порядок – порядок реестра. Записи БЕЗ привязанного
    источника не дают строк, автоматически выведенные ссылки на
    методические таблицы НЕ печатаются вовсе (правило «пропуска»:
    таблица методики без привязанной записи реестра пропускается)."""
    used: set[str] = set()

    def _take(rec: dict | None) -> None:
        if rec and rec.get("source"):
            used.add(str(rec["source"]))

    for t in trees:
        for c in getattr(t, "gs_causes", []):
            _take(kb.gs_by_id(c.ref))
        for c in getattr(t, "iz_causes", []):
            _take(kb.iz_by_id(c.ref))
        for pedals in (getattr(t, "gs_pedals", {}) or {},
                       getattr(t, "iz_pedals", {}) or {}):
            for pedal, on in pedals.items():
                if on:
                    _take(kb.modifier_by_pedal(pedal))
    if objects is not None:
        for o in objects.all_nodes():
            for pedal, on in (o.props.get("pedals", {}) or {}).items():
                if on:
                    _take(kb.modifier_by_pedal(pedal))
    # порядок вывода – порядок реестра (стабильный, редактируемый)
    return [s["id"] for s in kb.sources if s.get("id") in used]


def report_sources(trees: list, kb, objects=None) -> list[dict]:
    """Готовые строки раздела «Нормативные ссылки и справочные данные»:
    записи реестра варианта Б в порядке реестра (нумерация 1., 2., …
    выполняется при верстке). Пустой список – раздел пропускается."""
    ids = used_source_ids(trees, kb, objects)
    by_id = {s.get("id"): s for s in kb.sources}
    return [by_id[i] for i in ids if i in by_id]


# =====================================================================
# Контент-модель расчетного раздела (чистые функции)
# =====================================================================
def owner_sections(objects, trees: list) -> list:
    """Ветки иерархии с расчетными владельцами: [(владелец, цепочка
    контейнеров до территории, деревья)]. Ветки БЕЗ участков/установок
    с деревьями опускаются (LOCKED). Наружная установка висит под
    территорией – ее цепочка короче (уровень как у здания)."""
    by_owner: dict[str, list] = {}
    for t in trees:
        by_owner.setdefault(t.owner_id, []).append(t)

    def containers_of(node):
        chain = []
        p = node.parent
        while p is not None:
            chain.append(p)
            p = p.parent
        return list(reversed(chain))

    out = []
    for o in objects.all_nodes():
        if o.kind in ("area", "outdoor") and o.id in by_owner:
            out.append((o, containers_of(o), by_owner[o.id]))
    return out


def _site_row(sp: dict) -> tuple[str, str]:
    """Задача 5/7 (LOCKED): только релевантный типу параметр места."""
    from ..core.numfmt import fmt_num
    key, unit, letter = {
        "area": ("area_m2", "м²", "S"),
        "linear": ("length_m", "м", "L"),
        "apparatus": ("volume_m3", "м³", "V"),
    }.get(sp.get("site_type", "area"), ("area_m2", "м²", "S"))
    names = {"S": "Площадь S", "L": "Длина L", "V": "Объем V"}
    v = sp.get(key)
    return (names[letter],
            f"{fmt_num(float(v))} {unit}" if v else "не задано")


def params_rows(tree, ctx, kb) -> list[tuple[str, str]]:
    """«Параметры расчета» (Задача 4/5, LOCKED): таблица
    «Параметр | Значение» – только релевантный типу S/L/V, назначение,
    молниезащита, вероятности присутствия, Kσ (своя строка, без «;»),
    «Огненный шар: включен» – только при включенном переключателе."""
    from ..core.numfmt import fmt_num
    rows: list[tuple[str, str]] = [_site_row(ctx.site_props or {})]
    bp = ctx.building_props or {}
    if bp:
        p13 = (kb.p13_by_id(bp.get("p13_type", "")) or {}).get("title")
        p14 = (kb.p14_by_id(bp.get("p14_type", "")) or {}).get("title")
        if p13:
            rows.append(("Функциональное назначение (П1.3)", p13))
        if p14:
            rows.append(("Функциональное назначение (П1.4)", p14))
        prot = bp.get("pedals", {}).get("lightning_prot")
        rows.append(("Молниезащита",
                     (f"включена, категория {bp.get('lightning_cat', 'II')}"
                      if prot else "отключена")))
    rows.append(("Вероятность присутствия вещества",
                 fmt_num(tree.substance.value)))
    rows.append(("Вероятность присутствия окислителя",
                 fmt_num(tree.oxidizer.value)))
    rows.append(("Коэффициент безопасности Kσ", fmt_num(tree.k_sigma)))
    if tree.fireball:
        rows.append(("Огненный шар", "включен"))
    return rows


def input_rows(tree, kb, ctx) -> list[tuple[str, str, str]]:
    """«Исходные данные» (Задачи 5/7, LOCKED): «Событие | Величина |
    Источник». Источник – НАЗВАНИЕ записи реестра без скобок, пустой –
    «–». У расходных строк ГС – суффикс диапазона массового расхода."""
    from ..core.numfmt import fmt_num
    rows: list[tuple[str, str, str]] = []

    def _src(rec: dict) -> str:
        return kb.source_title(rec.get("source")) or "–"

    for c in tree.gs_causes:
        g = kb.gs_by_id(c.ref) or {}
        title = g.get("title", c.ref)
        if c.flow and kb.flow_titles.get(c.flow):
            title += f" – {kb.flow_titles[c.flow]}"
        if g.get("kind") == "p12":
            _v, _u = ctx.p12_value(c.len_m)
            qv = (f"{fmt_num(g.get('q_per_m', 0))} м⁻¹·год⁻¹"
                  f" × {fmt_num(_v)} {_u}")
        elif g.get("kind") == "p13":
            qv = "a₁·F / a·F^b (табл. П1.3/П1.4)"
        else:
            v = ctx.p11_site_value()
            qv = (f"{fmt_num(g.get('q', 0))} год⁻¹"
                  + (f" × {fmt_num(v)}" if v else ""))
        rows.append((title, qv, _src(g)))
    for c in tree.iz_causes:
        rec = kb.iz_by_id(c.ref) or {}
        qv = (f"P = {fmt_num(rec['p'])}" if "p" in rec
              else f"λ = {fmt_num(rec.get('lam', 0))} год⁻¹")
        rows.append((rec.get("title", c.ref), qv, _src(rec)))
    return rows


def result_lines(tree, kb, ctx) -> list[str]:
    """«Результаты расчета»: подставленные формулы Q_j и строка
    Q_В = Σ Q_i · Kσ (инженерная запись, запятая, юникод-степени)."""
    from ..core.numfmt import fmt_q, q_label
    out = []
    for j, r in enumerate(tree.scenarios(kb, ctx), start=1):
        out.append(f"{q_label(j)} = {r.formula} = {fmt_q(r.q)} год⁻¹"
                   f" ({r.name})")
    out.append(f"Q_В = Σ Q_i · Kσ = {fmt_q(tree.total_q(kb, ctx))} год⁻¹")
    return out


# =====================================================================
# Markdown-верстка (промежуточный формат pandoc)
# =====================================================================
# Скобки ( ) и дефис НЕ экранируем: в CommonMark на позициях текста они
# не управляющие (ссылка требует «[text](url)» целиком), а имена
# сценариев и формулы («1−exp(−3,2·10⁻⁶)») пестрят скобками
_MD_SPECIAL = set("\\`*_{}[]#|~^<>!")


def _md_escape(text: str) -> str:
    """Экранирование спецсимволов Markdown в тексте строк/ячеек
    (вертикальная черта обязательна в ячейках таблиц, крышка –
    надстрочник pandoc, угловые – HTML)."""
    out = []
    for ch in str(text):
        if ch in _MD_SPECIAL:
            out.append("\\" + ch)
        elif ch == "\n":
            out.append(" ")
        else:
            out.append(ch)
    return "".join(out)


def _md_table(header: list[str], rows: list) -> list[str]:
    """Трубочная таблица pandoc: шапка/сетка – стили шаблона, перенос
    по словам делает сам Word."""
    out = ["| " + " | ".join(_md_escape(h) for h in header) + " |",
           "|" + "|".join(["---"] * len(header)) + "|"]
    for row in rows:
        out.append("| " + " | ".join(_md_escape(c) for c in row) + " |")
    out.append("")
    return out


_TOC_OPENXML = (
    "```{=openxml}\n"
    '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
    "<w:r><w:rPr><w:b/><w:sz w:val=\"28\"/></w:rPr>"
    "<w:t>Оглавление</w:t></w:r></w:p>"
    '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
    '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u '
    "</w:instrText></w:r>"
    '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
    "<w:r><w:rPr><w:i/></w:rPr><w:t>Обновите поле (правая кнопка мыши –"
    " «Обновить поле»), чтобы увидеть оглавление</w:t></w:r>"
    '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>\n'
    "```\n")

_PAGEBREAK = (
    "```{=openxml}\n"
    '<w:p><w:r><w:br w:type="page"/></w:r></w:p>\n'
    "```\n")


def _title_openxml(version_line: str) -> str:
    """Титульная страница (LOCKED): заголовок 18 pt + «Куджи v… от
    dd.mm.yyyy» 12 pt, обе строки по центру; сам титул НЕ в стиле
    заголовков (в оглавление не попадает)."""
    return (
        "```{=openxml}\n"
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:b/><w:sz w:val="36"/></w:rPr>'
        f"<w:t>{_x(REPORT_TITLE)}</w:t></w:r></w:p>"
        '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
        '<w:r><w:rPr><w:sz w:val="24"/></w:rPr>'
        f"<w:t>{_x(version_line)}</w:t></w:r></w:p>\n"
        "```\n")


def _heading(level: int, text: str) -> str:
    """Заголовок раздела: уровни 2–6 – стили шаблона (синие), глубже –
    полужирный абзац (Word ограничивает стили шестью уровнями)."""
    if 1 <= level <= 6:
        return f"{'#' * level} {_md_escape(text)}\n"
    return f"**{_md_escape(text)}**\n"


def build_markdown(objects, trees: list, kb, ctx_map: dict,
                   owner_titles: dict, fmt_id: str = "A4L",
                   image_files: list | None = None) -> str:
    """Промежуточный Markdown отчета (тестируется без pandoc).
    image_files – [(owner_id, png_path)] готовых схем; при None
    изображения не вставляются (модельный прогон)."""
    from ..core.matrix import build_matrix
    from ..core.model import CalcContext
    from ..core.numfmt import fmt_q

    version_line = f"Куджи v{__version__}" \
                   f" от {date.today().strftime('%d.%m.%Y')}"
    # титул – ОТДЕЛЬНАЯ страница (LOCKED): заголовок, версия, разрыв,
    # затем страница оглавления с полем Word
    md: list[str] = [_title_openxml(version_line), _PAGEBREAK,
                     _TOC_OPENXML, _PAGEBREAK]

    # --- «Нормативные ссылки и справочные данные» (вариант Б) --------
    srcs = report_sources(trees, kb, objects)
    if srcs:
        md.append(_heading(1, SOURCES_HEADING))
        for i, s in enumerate(srcs, start=1):
            md.append(f"{i}. {_md_escape(s.get('title', ''))}")
        md.append("")

    # --- «Расчет частоты возникновения пожара» ------------------------
    md.append(_heading(1, CALC_HEADING))
    sections = owner_sections(objects, trees)
    total = 0.0
    for owner, chain, owner_trees in sections:
        # территория – уровень 2; контейнеры между ней и владельцем
        # углубляют по одному (здание 3, отсек 4, помещение 5); потолок
        # уровня владельца – 5 (LOCKED H2..H5; глубже – жирный абзац)
        md.append(_heading(2, f"{KIND_TITLES['territory']}"
                              f" «{chain[0].title}»"))
        level = 2
        for node in chain[1:]:
            level = min(level + 1, 5)
            md.append(_heading(level, f"{KIND_TITLES.get(node.kind, '')}"
                                      f" «{node.title}»"))
        owner_level = min(level + 1, 5)
        md.append(_heading(owner_level,
                           f"{KIND_TITLES.get(owner.kind, 'Участок')}"
                           f" «{owner.title}»"))
        sub_level = owner_level + 1          # 7+ → жирный абзац
        for tree in owner_trees:
            ctx = ctx_map.get(tree.owner_id) or CalcContext()
            md.append(_heading(sub_level, "Параметры расчета"))
            md.extend(_md_table(["Параметр", "Значение"],
                                params_rows(tree, ctx, kb)))
            md.append(_heading(sub_level, "Исходные данные"))
            md.extend(_md_table(["Событие", "Величина", "Источник"],
                                input_rows(tree, kb, ctx)))
            md.append(_heading(sub_level, "Результаты расчета"))
            for ln in result_lines(tree, kb, ctx):
                md.append(_md_escape(ln) + "\n")
            total += tree.total_q(kb, ctx)
    if sections:
        md.append(f"**Сумма по всем владельцам: {fmt_q(total)} год⁻¹**\n")
    md.append(_PAGEBREAK)

    # --- «Логическое дерево событий»: схема + матрица на владельца ----
    md.append(_heading(1, TREE_HEADING))
    imgs = dict(image_files or [])
    for owner, _chain, owner_trees in sections:
        md.append(_heading(2, f"{KIND_TITLES.get(owner.kind, 'Участок')}"
                              f" «{owner.title}»\n"))
        png = imgs.get(owner.id)
        if png:
            md.append(f"![]({png}){{width={_TEXT_COL_PX}px}}\n")
        data = build_matrix(owner_trees, kb, ctx_map,
                            {owner.id: owner.title})
        md.extend(_md_table(data.header(), [
            [str(i + 1), r.title, r.scenario_type, r.name,
             fmt_q(r.q), r.formula]
            for i, r in enumerate(data.rows)]))
        for _tid, _title, q in data.totals:
            md.append(f"**Q_В = Σ Q_i · Kσ = {fmt_q(q)} год⁻¹**\n")
    return "\n".join(md)


# =====================================================================
# Сборка файла
# =====================================================================
def render_owner_png(canvas, owner_trees, kb, ctx_map, titles: dict,
                     fmt_id: str, out_path: str) -> bool:
    """Схема ВСЕХ деревьев владельца одним PNG ~300 DPI по ширине
    выбранного формата листа (doc_scene – та же геометрия, что на
    холсте: WYSIWYG). canvas – рабочий TreeCanvas окна (его контроллер
    перестраивается на деревья владельца и возвращается назад)."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QImage, QPainter

    ctrl = canvas.controller
    keep = ctrl._last_rebuild
    try:
        ctrl.rebuild(owner_trees, kb, ctx_map, titles)
        rect = ctrl.layout.scene_rect
        if rect.isEmpty():
            return False
        w_mm = PAGE_FORMATS[fmt_id][0]
        w_px = max(1, int((w_mm - 20.0) / 25.4 * SCHEMA_DPI))
        h_px = max(1, int(w_px * rect.height() / max(rect.width(), 1.0)))
        img = QImage(w_px, h_px, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        p = QPainter(img)
        p.setRenderHints(QPainter.RenderHint.Antialiasing
                         | QPainter.RenderHint.TextAntialiasing)
        ctrl.doc_scene.render(p, QRectF(0.0, 0.0, float(w_px),
                                        float(h_px)), rect)
        p.end()
        return img.save(out_path)
    finally:
        if keep is not None:
            ctrl.rebuild(*keep)


def export_docx(path: str, objects, trees: list, kb, ctx_map: dict,
                owner_titles: dict, fmt_id: str = "A4L",
                canvas=None) -> str:
    """Полный конвейер: PNG схем + Markdown + pandoc → один docx.
    Возвращает путь; ошибки – исключениями с русскими текстами."""
    import zipfile

    if not PANDOC_EXE.exists():
        raise FileNotFoundError(
            "Не найден встроенный конвертер runtime\\pandoc\\pandoc.exe –"
            " переустановите приложение")
    if not REFERENCE_DOCX.exists():
        raise FileNotFoundError(
            "Не найден шаблон отчета eta\\export\\reference.docx")
    # pandoc запускается с cwd=временной папке – ПУТЬ К ВЫВОДУ обязан
    # быть абсолютным (относительный resolution'ился бы в temp)
    path = str(Path(path).resolve())
    with tempfile.TemporaryDirectory(prefix="kuji_docx_") as tmp:
        tmp_dir = Path(tmp)
        images: list[tuple[str, str]] = []
        if canvas is not None:
            for owner, _chain, owner_trees in owner_sections(objects,
                                                             trees):
                png = tmp_dir / f"schema_{owner.id}.png"
                if render_owner_png(canvas, owner_trees, kb, ctx_map,
                                    {owner.id: owner.title}, fmt_id,
                                    str(png)):
                    images.append((owner.id, str(png)))
        md = build_markdown(objects, trees, kb, ctx_map, owner_titles,
                            fmt_id, images)
        md_path = tmp_dir / "report.md"
        md_path.write_text(md, encoding="utf-8")
        r = subprocess.run(
            [str(PANDOC_EXE), "-f", "markdown", "-t", "docx",
             "--reference-doc", str(REFERENCE_DOCX),
             "--resource-path", str(tmp_dir),
             "-o", str(path), str(md_path)],
            capture_output=True, text=True, timeout=300,
            cwd=str(tmp_dir))
        if r.returncode != 0:
            raise RuntimeError("Ошибка pandoc: " + r.stderr[:500])
    # валидация результата: zip целый, титул и поле оглавления на месте
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            raise RuntimeError("Поврежденный docx-файл")
        doc = z.read("word/document.xml").decode("utf-8")
        for probe in (REPORT_TITLE, 'TOC \\o "1-3"'):
            if probe not in doc:
                raise RuntimeError("docx не содержит: " + probe)
    return path
