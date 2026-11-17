# -*- coding: utf-8 -*-
"""Зачистка готового .docx (сессия 20, п.2).

ЗАЧЕМ. Отчёт собирается pandoc'ом из ГОСТ-шаблона `reference.docx`,
клонированного из рабочего документа «(К1) Ф3.6, ФОК Донецк.docx». С
шаблоном в файл переходят чужие отчёту тяжести:

  * `docProps/app.xml` с наследием донора – `<Template>Normal.dotm</Template>`,
    его Words/Pages/TotalTime. Упоминание Normal.dotm в открываемом
    документе участвует в цепочке Word «в документе Normal.dotm обнаружено
    содержимое, которое не удалось прочитать … восстановить?», а на ответе
    «Да» Word ПЕРЕЗАПИСЫВАЕТ пользовательский Normal.dotm вместе с его
    макросами и предустановками. Риск для машины заказчика неприемлем,
    поэтому следов чужого шаблона в нашем файле быть не должно;
  * лишние теги `word/settings.xml`: `attachedTemplate`, `linkStyles`,
    `savePreviewPicture` и простыня `rsids`;
  * бесхозные медиа – десятки PNG и `*.bin` (в том числе росчерк подписи
    ~0,5 Мб) из тела донора, которые pandoc переносит в пакет, хотя ни
    один элемент на них не ссылается. Отчёт раздувается примерно вдвое, и
    Word тратит время на разбор ненужного.

ЧТО ДЕЛАЕТ `tidy_package(path)`:
  1. в каждом `*.rels` убирает связи, на которые не ссылается владельческая
     часть (нет `r:id`/`r:embed`/`r:link` с таким Id), и связи типов из
     `DROP_REL_TYPES`;
  2. строит граф достижимости от `_rels/.rels` и выбрасывает всё, до чего
     дойти нельзя, вместе с Override'ами в `[Content_Types].xml`;
  3. вычищает из `word/settings.xml` теги из `SETTINGS_DROP`;
  4. проверяет результат (каждый XML читается, висячих связей нет) и
     атомарно заменяет файл.

Никакого Qt, детерминированно: тот же вход → тот же выход. Повреждение
считается ошибкой и всплывает русской диагностикой экспорта.
"""

from __future__ import annotations

import os
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile

_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

# структуры .docx, которые остаются ВСЕГДА, даже если обвязка почему-то
# на них не ссылается (разные версии pandoc по-разному описывают связи;
# без этого списка можно потерять settings.xml вместе с колонтитулами)
KEEP_ALWAYS = (
    "word/document.xml",
    "word/styles.xml",
    "word/settings.xml",
    "word/webSettings.xml",
    "word/fontTable.xml",
    "word/numbering.xml",
    "docProps/core.xml",
)

# Типы связей, которые ОЧИЩАЮТСЯ по принципу «нет r:id в части – нет
# связи». Только они: styles/settings/numbering/theme/webSettings/
# fontTable/footnotes/comments в OOXML НЕ ссылаются на себя через r:id
# (Word подхватывает их неявно), а header/footer нужны колонтитулам ГОСТ-
# рамки. Если бы мы чистили «по используемым Id» всё подряд, пакет терял
# бы стили и колонтитулы – проверено пробой на pandoc.
PRUNE_IF_UNUSED_TYPES = (
    f"{_NS}/image",
    f"{_NS}/oleObject",
    f"{_NS}/package",
    f"{_NS}/hyperlink",
)

# типы связей, не нужные отчёту никогда (наследие шаблона-донора)
DROP_REL_TYPES = (
    f"{_NS}/extended-properties",
    f"{_NS}/custom-properties",
    f"{_NS}/thumbnail",
)

# необязательные теги word/settings.xml, удаляемые без следа
SETTINGS_DROP = (
    r"<w:attachedTemplate\b[^>]*/>",
    r"<w:linkStyles\b[^>]*/>",
    r"<w:savePreviewPicture\b[^>]*/>",
    r"<w:rsids\b[^>]*>.*?</w:rsids>",
    r"<w:rsids\b[^>]*/>",
)

_REL_ATTR_RE = re.compile(r'(?:r:id|r:embed|r:link)="([^"]+)"')
_REL_ITEM_RE = re.compile(r"<Relationship\b[^>]*/>")
_ID_RE = re.compile(r'\bId="([^"]+)"')
_TYPE_RE = re.compile(r'\bType="([^"]+)"')
_TARGET_RE = re.compile(r'\bTarget="([^"]+)"')
_MODE_RE = re.compile(r'\bTargetMode="([^"]+)"')
_OVERRIDE_RE = re.compile(r"<Override\b[^>]*/>")
_PART_RE = re.compile(r'\bPartName="([^"]+)"')


def _rels_path_of(part: str) -> str:
    """`word/document.xml` → `word/_rels/document.xml.rels`."""
    folder, _, name = part.rpartition("/")
    return f"{folder}/_rels/{name}.rels" if folder else f"_rels/{name}.rels"


def _part_of_rels(rels: str) -> str:
    """Обратное преобразование; для корневого `_rels/.rels` → ''."""
    folder, _, file = rels.rpartition("/")
    base_folder, _, _ = folder.rpartition("/")
    name = file[:-len(".rels")] if file.endswith(".rels") else file
    if not name:
        return ""
    return f"{base_folder}/{name}" if base_folder else name


def _resolve(base_part: str, target: str) -> str:
    """Target из .rels → имя части. Основание – ПУТЬ владельческой части
    (`word/document.xml`), а не папка: так делает сам OPC. Корневая
    обвязка пакета передаётся пустой строкой."""
    if target.startswith("/"):
        return target.lstrip("/")
    folder, _, _ = base_part.rpartition("/")
    joined = f"{folder}/{target}" if folder else target
    return os.path.normpath(joined).replace("\\", "/")


def _prune_rels(xml: str, used_ids: set[str]) -> str:
    """Убрать из .rels (а) связи типов из `DROP_REL_TYPES`, (б) неиспользуемые
    медиа/гиперссылки. Прочие связи НЕ трогаем – они неявные (см.
    `PRUNE_IF_UNUSED_TYPES`).

    Корневому `_rels/.rels` передаётся пустое `used_ids`. """
    def keep(item: str) -> bool:
        m_type = _TYPE_RE.search(item)
        type_val = m_type.group(1) if m_type else ""
        if type_val in DROP_REL_TYPES:
            return False
        if _MODE_RE.search(item):                 # внешняя цель не проверяется
            return True
        if type_val in PRUNE_IF_UNUSED_TYPES:
            m_id = _ID_RE.search(item)
            if m_id and m_id.group(1) not in used_ids:
                return False
        return True

    return _REL_ITEM_RE.sub(
        lambda m: m.group(0) if keep(m.group(0)) else "", xml)


def _validate(parts: dict[str, bytes]) -> None:
    """Каждый XML читается; ни одна внутренняя связь не ведёт в никуда."""
    for name, data in parts.items():
        if name.endswith((".xml", ".rels")):
            try:
                ET.fromstring(data)
            except ET.ParseError as exc:
                raise RuntimeError(
                    f"Поврежденный XML после зачистки отчета: {name}"
                    f" ({exc})") from exc
    for name in [n for n in parts if n.endswith(".rels")]:
        owner = _part_of_rels(name)
        for item in _REL_ITEM_RE.findall(parts[name].decode("utf-8")):
            if _MODE_RE.search(item):
                continue
            mt = _TARGET_RE.search(item)
            if mt and _resolve(owner, mt.group(1)) not in parts:
                raise RuntimeError(
                    "Отчет ссылается на отсутствующую часть: "
                    + mt.group(1))


def tidy_package(path: str) -> dict:
    """Зачистить .docx на месте, вернуть отчёт что именно убрано."""
    path = str(path)
    with zipfile.ZipFile(path) as z:
        order = list(z.namelist())
        parts: dict[str, bytes] = {n: z.read(n) for n in order}

    report = {"dropped_parts": [], "dropped_rels": 0, "settings": []}

    # 1. обвязки частей: какие Id реально упомянуты в XML владельца
    for name in [n for n in order if n.endswith(".rels")]:
        owner = _part_of_rels(name)
        body = parts.get(owner) if owner else None
        used = set(_REL_ATTR_RE.findall(body.decode("utf-8", "replace"))) \
            if body is not None else set()
        xml = parts[name].decode("utf-8")
        pruned = _prune_rels(xml, used)
        if pruned != xml:
            report["dropped_rels"] += (len(_REL_ITEM_RE.findall(xml))
                                       - len(_REL_ITEM_RE.findall(pruned)))
            parts[name] = pruned.encode("utf-8")

    # 2. достижимость от корневой обвязки пакета. Обходим ЧАСТИ (обвязку
    #    каждой!), а `reachable` отдельно пополняется списком KEEP_ALWAYS –
    #    иначе уже «помеченная» часть (document.xml) ни разу не попала бы в
    #    очередь, и всё, что живёт в её обвязке (стили связи, колонтитулы),
    #    уехало бы как недостижимое (проверено пробой на pandoc).
    reachable = {"[Content_Types].xml"}
    walked: set[str] = set()
    queue = [""]
    while queue:
        owner = queue.pop()
        if owner in walked:
            continue
        walked.add(owner)
        rels = "_rels/.rels" if not owner else _rels_path_of(owner)
        if rels not in parts:
            continue
        reachable.add(rels)
        for item in _REL_ITEM_RE.findall(parts[rels].decode("utf-8",
                                                            "replace")):
            if _MODE_RE.search(item):
                continue
            mt = _TARGET_RE.search(item)
            if not mt:
                continue
            target = _resolve(owner, mt.group(1))
            if target in parts:
                reachable.add(target)
                queue.append(target)
    reachable |= {p for p in KEEP_ALWAYS if p in parts}

    # 3. недоступное – вон, вместе с записями о типе содержимого
    for name in order:
        if name not in reachable and name != "_rels/.rels":
            report["dropped_parts"].append(name)
    if report["dropped_parts"]:
        dead = set(report["dropped_parts"])
        for name in dead:
            parts.pop(name, None)
        ct = parts["[Content_Types].xml"].decode("utf-8")

        def ct_rep(m: re.Match) -> str:
            mp = _PART_RE.search(m.group(0))
            return "" if (mp and mp.group(1).lstrip("/") in dead) \
                else m.group(0)

        parts["[Content_Types].xml"] = _OVERRIDE_RE.sub(
            ct_rep, ct).encode("utf-8")

    # 4. settings.xml: следы чужого шаблона и ненужные флаги
    if "word/settings.xml" in parts:
        st = parts["word/settings.xml"].decode("utf-8")
        for pattern in SETTINGS_DROP:
            pruned = re.sub(pattern, "", st, flags=re.S)
            if pruned != st:
                report["settings"].append(
                    re.search(r"<w:(\w+)", pattern).group(1))
                st = pruned
        parts["word/settings.xml"] = st.encode("utf-8")

    # 5. проверка и атомарная замена
    _validate(parts)
    fd, tmp_name = tempfile.mkstemp(suffix=".docx",
                                    dir=os.path.dirname(path) or ".")
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp_name, "w", zipfile.ZIP_DEFLATED) as z:
            for name in order:
                if name in parts:
                    z.writestr(name, parts[name])
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise
    return report
