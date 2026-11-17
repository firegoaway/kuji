# SESSION 15 REPORT – Kuji 6.5.0

Date: 12.11.2026. Base: v6.4.2 (sessions 1–14 + addenda 14/1, 14/2).
Subject: engine-propagation + hierarchy-interaction + typography
session, eleven tasks. All LOCKED Q&A decisions implemented as
specified; no locked decision was reopened; no clarifying questions
were needed (the prompt locked every ambiguity). Version → **6.5.0**;
KB `meta.version` stays **«6.1»** (data-title edits are not schema
changes; the only structural KB field added is data-level: templates
gain no new required keys, flow-scoped template entries are encoded
inside the existing `gs_causes` string list).

**Acceptance:** `smoke_test.py` – PASS (21 blocks of session 14 +
rewritten block 4 cascade semantics + extended block 1 with the
Task-7 KB renames + NEW block 21 «Задача 3.3» chain math);
`gesture_test.py` – PASS (blocks 1–38 of sessions 12–14 with updated
assertions where behavior changed deliberately: version 6.5, the
cause-picker seam now carries (ref, flow), the hierarchy block 3 now
asserts the NEW structure, block 32 asserts scenario-row collapse +
new blocks 39–45). `run_qa.cmd` regenerated and vision-reviewed
(glm-5.3-flash crops) – see the QA section.

## Task 1 – участок type switch feeds the ТГМ calculation

* Root cause confirmed exactly as diagnosed: `objects.tgm_levels`
  included the участок level only when `site_type == "area"`, so
  linear/apparatus участки had no path into the ТГМ math at all.
* Fix (LOCKED вариант А):
  1. `objects.tgm_levels` – the участок participates at **any**
     site type; the list stays [участок → помещение → здание],
     outdoor = [self].
  2. NEW `model.tgm_level_value(props)` – the single resolver of a
     level's value: a level with `site_type` (участок/установка)
     contributes **its own value by type** (`area_m2` /
     `length_m` / `volume_m3` from `SITE_FIELD`), помещение/здание
     contribute `area_m2`. Explicitness = key presence; None – the
     level sets nothing, the cascade continues.
  3. `CalcContext.tgm_multiplier` resolves F through
     `tgm_level_value` (explicitness = key presence → variant (а)
     inheritance intact); the П1.3/П1.4 switch uses this effective
     value (length 51 251 m → П1.4 formula, test-verified).
  4. `MainWindow.tgm_view` uses the same resolver (the inherited-grey
     area display follows the type value).
* Dimensionality note: on linear/apparatus участки the multiplier is
  a₁ × длина/объем – a deliberate customer decision (LOCKED), visible
  in the substituted formula numbers.

## Task 2 – immediate recalculation on value edits

* Verified every form's wiring (type combo, value spin, area/type
  fields at every level): all of them already write props through
  `valueChanged`/`currentIndexChanged` → `object_props_changed` →
  `_refresh` (canvas, matrix, status bar, hierarchy rows). Together
  with Task 1 the value actually flows: gesture block 40 proves the
  «Возникновение» node ΣQ and the status bar change **without leaving
  the panel** while typing 51251 into «Длина, м». Commit-on-leave
  remains only for the «Название» line edit (it never affected Q).

## Task 3 – hierarchy restructure + cause dependencies + reparenting

### 3.1/3.2 Structure
* «Группа сценариев» and the grouped display rows are **removed**.
  Under each owner: one **scenario row** per tree (the scenario-type
  title per Task 7), children = all user-added causes: GS rows with
  the prefix «Образование ГС: <название>» (+ « – <диапазон расхода>»
  for flow-scoped entries), IZ rows plain. Dependent causes sit under
  their parent's row (chains of any depth). Live-updated on every
  add/remove/drag (full rebuild via `tree_changed`).
* Expansion state: object collapse persists as before; NEW stable
  keys track collapsed scenario rows (`tree_id`, stored in the legacy
  `hierarchy_groups_collapsed` ui key) and collapsed cause rows
  (`[tree_id, cid]`, new optional `hierarchy_causes_collapsed` key);
  all three survive rebuilds and file round-trips.

### 3.3 Cause dependencies via drag-and-drop (LOCKED)
* Data: `GSCause`/`IZCause` gain stable `cid` (generated when absent)
  and optional `parent` (a cid in the same list). Serialization
  round-trips both; old files load flat (parents absent → None, cids
  generated); cycles from hand-edited files are broken (cycle nodes
  become independent).
* Math: NEW `model.cause_paths(causes)` builds the forest → paths
  «корень → лист»; `TreeModel._path_factor` multiplies values and
  formula pieces along a path. A dependent cause contributes no
  independent row: every root-to-leaf path is ONE row whose factor is
  the product along the path – ТГМ:
  q_sub·q_ox·(a₁·значение)·Π(1−exp(−λ_i)); ГГ/ГЖ/ЛВЖ: the chain
  product multiplies as the ИЗ-factor of the parent's scenario rows
  (flow scope of a GS chain = the root's flow, documented). Branching
  (one parent, several children) yields one row per root-to-leaf
  path.
* UI/UX: `_HierTree(QTreeWidget)` – drag enabled on cause/scenario/
  object rows; during dragMove the valid target highlights blue
  (#DBEAFE), invalid targets red (#FEE2E2) plus the Forbidden cursor;
  `HierarchyPanel.drop_ok/handle_drop` are the validation/operation
  seams (tests drive them directly). Rules enforced: ИЗ→ИЗ / ГС→ГС of
  the same tree only; no drop onto itself or a descendant; drop on
  the scenario row detaches to top level. After the drop the tree,
  canvas, inspector, matrix and Q update immediately (tree_changed →
  full refresh).
* «Убрать» removes the cause **with all children**; the new
  `MainWindow._confirm_remove_chain` seam shows the chain list
  («Удалить причину с зависимыми ветвями (N)?»). The inspector marks
  dependent causes with the «→» prefix.
* Click on a cause row (LOCKED): the tree stays on the canvas, the
  inspector opens the ГС/ИЗ node form, the canvas node gets the
  dashed selection (`controller.select_node`).

### 3.4 Object reparenting (LOCKED)
* `objects.move_subtree(node, new_parent)` – the whole subtree moves
  (children, trees via unchanged `owner_id`, their causes and
  dependencies, collapsed state, node offsets). Drops enforce
  `PARENT_RULES` (`can_add`) and reject own descendants / same
  parent; invalid targets get the red-frame + forbidden-cursor
  feedback and nothing moves. The selection follows the moved object
  (`select_object(dnode, emit=True)`).

### 3.5 Tree reparenting (LOCKED)
* A scenario row dragged onto another участок/установка (and only an
  owner – any other target is invalid) changes `tree.owner_id`; the
  canvas annotation follows (rebuilt from owner titles). The scenario
  type is carried by the row itself and never changes during the
  move; drops onto non-owners are rejected with feedback.

## Task 4 – formula typography

* `ScenarioRow.formula` is now the **fully substituted right-hand
  side**: numbers only, grouping parentheses, `exp(...)` instead of
  «e^(…)». Sample (smoke-asserted byte-for-byte):
  `Q₁ = 1·1·(9·10⁻⁵·2960,77)·(1−exp(−3,2·10⁻⁵))`.
* j subscript = the row's number in the matrix «№» column (and the
  PDF report numbers its calculation lines with the same running
  counter). Implemented via NEW `numfmt.q_label(j)`/`sub_digits`
  (Unicode subscripts – plain-text safe in QTableWidgetItems and
  PDF).
* Symbolic names removed from formulas: the ТГМ multiplier piece is
  `(9·10⁻⁵·2960,77)` / `(0,0011·25000^0,6)` (`_tgm_resolve` returns
  value + piece + table); П1.2 `(2,8·10⁻⁶·800)`; П1.1 `(4·10⁻⁵)`;
  lightning `(5,6·10⁻³)`; the П2.1 factor is a bare number
  (`·0,005`); the fireball row is `2,5·10⁻⁵`. Chain rows multiply
  their pieces: `(1−exp(−2,2·10⁻⁶)·1−exp(−3,2·10⁻⁵))`
  (`_join_pieces` unwraps exactly one paren layer).
* `matrix.build_matrix` prefixes `Q_j = ` (no more ref-stripping –
  the RHS is clean by construction; the old `_TABLE_REF` regex is
  deleted).
* The PDF report: calculation lines `[… Q₂ = <RHS>]`; NO references
  inside formulas; each sheet carries a compact
  «Источники: табл. П1.3 – множитель a₁·F; …» block under РЕЗУЛЬТАТЫ,
  derived from the tree's data (`_tree_sources`: used П1.1/П1.2/
  П1.3/П1.4/П2.1 tables + λ ИЗ + lightning + нагретое вещество +
  огненный шар) – not hand-maintained. The ИСХОДНЫЕ ДАННЫЕ section
  keeps its per-cause sources.

## Task 5 – node text clipping, FINAL fix (metrics-driven geometry)

* Root cause (per the customer guidance): the node width was computed
  from `horizontalAdvance`, and `QPainter.drawText(QRectF, flags,
  text)` **clips to the rect by default** – substituted-font
  superscripts («10⁻⁶», «год⁻¹») and sub-pixel tails were cut by the
  frame.
* The architectural fix (guidance followed verbatim):
  1. `layout.ink_rect(font, text)` = `QFontMetricsF.tightBoundingRect`
     – the exact ink box of every line (font substitution included).
  2. `make_node` (layout.py): wrap_words stays the FIRST stage (the
     MAX_NODE_W budget is a wrap hint only); the DECIDING stage is
     metrics: width = max line ink + 2×NODE_INSET (20 px) + 2 px
     safety; height = 2×PAD_V (24 px) + per-font line heights. No
     hard cap clamps the text rect anymore (MIN_NODE_W remains a
     lower hint).
  3. `render.draw_node`/`draw_annotation` draw every line with
     `Qt.TextFlag.TextDontClip` – nothing can be cut even on
     sub-pixel overshoot.
  4. Canvas `boundingRect()` derives from NodeGeo.rect (+3 px) as
     before; the geometry protocol is documented in
     `canvas._move_node_item` (nodes move via `setPos`, edges mutate
     only through `setPath` which calls `prepareGeometryChange`
     internally); edges/pins derive from the same rects after
     offsets, so curves cannot overlap the widened frames.
  5. WYSIWYG: the fix lives once in `compute_layout`/`render` –
     canvas and PDF consume it.
  6. Programmatic proof: NEW `layout.node_text_fits(node)` asserts
     every line's ink + margins fits the node rect; smoke runs it on
     all demo-tree nodes and the annotations (programmatic metrics
     assertions beat vision estimates), plus the QA vision pass on
     2× crops.

## Task 6 – наружная установка: site-type selector

* The outdoor form gets the SAME «ТИП + ЗНАЧЕНИЕ» block as the
  участок (shared builder `InspectorPanel._site_type_section`;
  `inherit_area=False` – the installation is its own last level, the
  value materializes immediately, «показано = записано»). Defaults
  come from `DEFAULT_PROPS[OUTDOOR]` (area 400 / length 50 / volume
  10).
* Migration: absent `site_type` on an outdoor (projects ≤6.4.2) →
  «участок (м²)» (written at first form open; the engine also treats
  an absent site_type as «area», so old projects compute unchanged
  before the form is ever opened).
* Engine: `tgm_levels(outdoor) = [self]`, `tgm_level_value` resolves
  by type → the multiplier/P1.3-P1.4 switch follow the installation's
  own value; `p12_value` is now type-driven for both участки and
  installations (area → м², linear → м, apparatus → м³; the
  аппарат-участок previously fell into the length branch – unified
  and documented).
* The outdoor «Функциональное назначение (П1.3/П1.4)» combo stays and
  its auto-switch now follows the type-driven effective value
  (`_type_combo_13_14` rebuilt on every value edit via the
  `on_value=type_fill` hook).

## Task 7 – «пожар/взрыв» → «пожар», decoding removals (KB data edit)

Byte-safe script (read_bytes/write_bytes + verification; deleted
after use). Normative П2.1 regime names untouched.

* scenario_types titles (KB → hierarchy/canvas annotation/matrix/
  PDF/KB window – all derive from the data):
  - «Сценарий пожара ТГМ (твердые горючие материалы)» → «Сценарий пожара ТГМ»
  - «Сценарий пожара/взрыва ГГ (горючие газы)» → «Сценарий пожара ГГ»
  - «Сценарий пожара/взрыва ГЖ (горючие жидкости)» → «Сценарий пожара ГЖ»
  - «Сценарий пожара/взрыва ЛВЖ (легковоспламеняющиеся жидкости)» → «Сценарий пожара ЛВЖ»
  - «Сценарий пожара/взрыва Пыли» → «Сценарий пожара Пыли»
* fire_node_title: «Возникновение пожара/взрыва» → «Возникновение
  пожара» (4 records; the model fallback string updated too).
* Verified NOT touched: «Сгорание (взрыв) топливовоздушной смеси»,
  «Сгорание (взрыв) пылевоздушной смеси – дефлаграция/детонация»
  (smoke asserts them byte-exact).

## Task 8 – flow-scoped GS causes (LOCKED) + 8.4 verification

* 8.4 Methodology verification (source: `literature\
Методика_533_RAG_final.md`, табл. П2.1, lines 719–727):
  - Interval groups confirmed exactly: «Малый (<1)», «Средний
    (1 - 50)», «Большой (>50)», «Полный разрыв» – массовый расход
    истечения, кг/с. All 12 conditional-probability rows of the KB
    `p21` match the source table value-for-value (small gas/twophase/
    liquid [0,005; 0,005; 0,080]/[0,005; 0,005; 0,080]/[0,005;
    0,005; 0,050]; mid [0,035; 0,036; 0,240]/[0,035; 0,036; 0,240]/
    [0,015; 0,015; 0,050]; big [0,150; 0,176; 0,600]/[…]/[0,040;
    0,042; 0,050]; rupt [0,200; 0,240; 0,600]/[…]/[0,050; 0,061;
    0,100]).
  - Regime attachment confirmed: 3 columns per interval×medium, all
    P > 0 → all regimes appear automatically; gas/twophase:
    мгновенное → факельное, последующее → пожар-вспышка, с избыточным
    давлением → сгорание (взрыв) ТВС; liquid: мгновенное/
    последующее → пожар пролива, давление → ТВС (`_MEDIUM_FIRE`
    unchanged – correct).
  - **Wording discrepancy found and fixed**: the KB `flow_titles`
    said «скорость сгорания» – a term that does not occur in the
    methodology; П2.1 says «массовый расход истечения, кг/с».
    `flow_titles` renamed (byte-safe script):
    «скорость сгорания < 1 кг/с» → «массовый расход истечения < 1
    кг/с» (likewise 1–50 / > 50); «полный разрыв» unchanged. The
    KB-window П2.1 sub-tab already used the correct term.
  - «Огненный шар» stays a separate switch (прил. № 1, п. 5), not a
    flow row.
* 8.1 Exploded rows: NEW `kb.flow_variants(rec)` (p11/p12
  non-direct: 3 ranges; «полное разрушение»/«разрыв» titles: one
  «rupt» row; direct/p13: one row without a range) and
  `kb.flow_row_title(rec, flow)` (sub-parts after ": " capitalized:
  «Разгерметизация, Отверстие 5 мм»; range suffix after an en-dash;
  the rupt row carries no suffix – the range is already in its
  title). Applied in the picker `_cause_records` (ГГ/ГЖ/ЛВЖ;
  ТГМ/Пыль stay one row – their math has no flow branching) and in
  the KB library `GSLibraryTab` (rows per record×range; edits change
  the RECORD, deletion removes the record with all its rows).
* 8.2 Independence: `GSCause.flow` (small|mid|big|rupt|None) is part
  of the cause; two entries of the same opening with different ranges
  are distinct causes; the duplicate validator treats (ref, flow,
  parent) triples as duplicates only. Each entry generates only its
  range's scenarios; all regimes of the interval appear automatically
  (P > 0). The user may still drag a GS cause under another GS cause
  (Task 3.3).
* 8.3 No-flow causes: direct П1.1 events, ТГМ-поверхность (p13) and
  dust remain single rows without a speed suffix.
* 8.5 Engine/data: `scenarios()` iterates `(gs.flow,) if gs.flow else
  FLOWS` (None → all four ranges, old projects unchanged);
  serialization round-trips `flow` (optional field); the picker
  dialog carries `selected_flow`; `add_gs_requested` is now
  `Signal(str, object)`; template entries may encode
  «ref#диапазон» (`_apply_library_equipment` parses it into
  `GSCause(ref, flow)`).
* **Defect found & fixed during implementation**: rebuilding the
  library table fired `itemChanged` per `setItem`, and
  `_on_title_edited` wrote the ROW text back into the record –
  invisible before (row text == record title), but with exploded
  rows it appended a range suffix to the record title on every
  reload. All three library `reload()` implementations now block
  signals during the rebuild; the GS `_on_title_edited` additionally
  strips a known range suffix so a hand edit of an exploded row
  cannot double it.

## Task 9 – causes refused on a second tree

* Root cause confirmed: `MainWindow._current_tree()` returned None
  with 2+ trees on one owner, so the four cause handlers silently
  no-oped.
* Fix: NEW `InspectorPanel.current_tree()` (the tree of the inspected
  node, i.e. `self._tree` from `show_tree_node`); all cause
  add/remove operations route through `MainWindow._inspected_tree()`
  (inspector's tree first, `_current_tree()` as fallback). The
  template-apply path (`_apply_library_equipment`) creates a NEW tree
  on the selected owner – checked, no such routing bug; KB-apply and
  pedal paths operate on the tree object they hold. Regression:
  gesture block 39 (two trees on one наружная установка, causes added
  to the SECOND tree through the picker seam).

## Task 10 – editable «Шаблоны оборудования»

* The right pane of the templates tab is now an EDIT FORM:
  «Название» (QLineEdit), «Категория» (QLineEdit), «Тип сценария»
  (combo of 5), «Разновидности ГС» (list + «Добавить…» from the GS
  library picker incl. flow-scoped rows / «Убрать»), «Разновидности
  ИЗ» (list + the IZ picker / «Убрать»). Edits write into the record
  immediately (dirty-guard + «Сохранить» = kb.save semantics as the
  other libraries; `kb.reindex()` on every mutation); the card list
  and the form update live.
* [Добавить]/[Удалить] template buttons appear BOTTOM-LEFT of the KB
  window (the uniform record-buttons bar; the tab now exposes
  `add_record`/`delete_current_record`). New template defaults
  (customer-confirmed): title «Новый шаблон оборудования», category
  «Прочее», scenario type «gg», empty lists.
* Deleting warns with the usage count: `MainWindow._usage` gained an
  «equipment_templates» branch = the number of trees whose causes
  reference the template's variety ids; the confirm dialog
  (`_confirm_delete_tpl` seam) lists the number.
* «Применить на холсте» keeps working with the edited lists,
  including flow-scoped entries («gs-vessel-5#mid» → a
  `GSCause(ref, flow="mid")` – gesture-verified through a real apply).

## Task 11 – renames + combo popup width

1. «T_тест» → «T_ТО» (KB pm-ttest: title «Периодичность проверок
   защитных средств (T_ТО)», formula «PFD_avg ≈ λ_DU · T_ТО/2» –
   byte-safe script; the mini-notation renders «ТО» as a real
   subscript; the math_text docstring example updated; no literal
   «T_{ТО}» anywhere).
2. «Тип (П1.3)» → «Функциональное назначение (П1.3)» and
   «Тип (П1.4)» → «Функциональное назначение (П1.4)» in all four
   form builders (building/room/участок/outdoor), the inherited-combo
   tooltip («Функциональное назначение здания по табл. П1.3/П1.4;
   строка «– наследуется –» берет назначение от помещения или
   здания…»), the validator/multiplier error notes («не выбрано
   функциональное назначение (П1.3|П1.4)») and the PDF report lines
   («функциональное назначение (П1.3): …; функциональное назначение
   (П1.4): …»).
3. Combo popups: NEW `PopupWrapDelegate` (wrap by whole words, long
   words by syllables with «–» via `wrap_words85`, ≤85 chars per
   line, multi-line sizeHints) + `_popup_target_width` (popup width =
   longest entry after wrapping, capped at the 85-char width, floor =
   the closed button's width; the 2×-button cap is gone). The closed
   button keeps its sizing; `compact_combo` popups unchanged.

## Before → after (all changed user-facing texts, consolidated)

* ТГМ multiplier notes: «a₁·F = 9·10⁻⁵·2960,77 (табл. П1.3)» →
  «(9·10⁻⁵·2960,77)»; «a·F^b = … (табл. П1.4)» → «(0,0011·25000^0,6)»;
  «не задана площадь (участок/помещение/здание)» → «не задано значение
  (участок/помещение/здание)»; «не выбран тип (П1.3|П1.4)» → «не
  выбрано функциональное назначение (П1.3|П1.4)».
* Validator: «Множитель ТГМ не рассчитан: … – заполните площадь и тип
  на участке…» → «… – заполните значение (по типу участка) и тип на
  участке, в помещении или здании (первое явное значение уровня)».
* Formulas: «Q = 1·1·[a₁·F = 9·10⁻⁵·1200]·1−e^ (−3,2·10⁻⁶)» →
  «Q₁ = 1·1·(9·10⁻⁵·1200)·(1−exp(−3,2·10⁻⁶))»; П1.2 piece
  «5,7·10⁻⁶ м⁻¹·год⁻¹ × 50 м (П1.2)» → «(5,7·10⁻⁶·50)»; П2.1 tail
  «·P₂₁=0,005» → «·0,005»; fireball «частота внешнего воздействия
  2,5·10⁻⁵ год⁻¹ на аппарат (прил. № 1, п. 5)» → «2,5·10⁻⁵» (the
  source moved to the «Источники: …» block).
* PDF report: «тип П1.3: …; тип П1.4: …» → «функциональное назначение
  (П1.3): …; функциональное назначение (П1.4): …»; NEW per-sheet line
  «Источники: табл. П1.3 – множитель a₁·F; …».
* Hierarchy: «Группа сценариев» rows → scenario rows with
  «Образование ГС: …» / plain IZ children; tooltip «Q = … год⁻¹» per
  scenario row (was per grouped display line).
* Cause picker (ГГ/ГЖ/ЛВЖ): «Аппарат (сосуд) под давлением:
  разгерметизация, отверстие 5 мм · 4·10⁻⁵» → three rows
  «Аппарат (сосуд) под давлением: Разгерметизация, Отверстие 5 мм –
  массовый расход истечения < 1 кг/с · 4·10⁻⁵» / «… 1–50 кг/с» /
  «… > 50 кг/с» + one row «Аппарат (сосуд) под давлением:
  Разгерметизация, Полное разрушение» (rupt).
* Scenario-row scenario names: «… – скорость сгорания 1–50 кг/с – …»
  → «… – массовый расход истечения 1–50 кг/с – …».
* Inspector: «Тип (П1.3):» → «Функциональное назначение (П1.3):»
  (label, both combos); outdoor form «Площадь, м²:» → «ТИП» +
  «ЗНАЧЕНИЕ» (value field label by type: «Площадь, м²:»/«Длина, м:»/
  «Объем, м³:»); dependent causes shown as «→ <название>».
* Measures: «Периодичность проверок защитных средств (T_тест)» →
  «… (T_ТО)».
* Cause removal confirm (NEW): «Удалить причину с зависимыми
  ветвями (N)?» + chain list; template deletion (NEW): «Удалить
  шаблон «X»? Его состав используют N деревьев проекта…».
* KB window: GS library rows exploded (see Task 8); templates right
  pane «Выберите шаблон в списке слева.» → the edit form; bottom-left
  buttons now also visible on «Шаблоны оборудования».

## Files touched (session 15)

eta/core/numfmt.py (sub_digits/q_label) · eta/core/objects.py
(DEFAULT_PROPS outdoor site fields, tgm_levels any-type,
move_subtree) · eta/core/model.py (tgm_level_value, _tgm_resolve/
tgm_multiplier/tgm_table, p12_value by type, GSCause.flow, cause
cid/parent, cause_paths, _join_pieces, _path_factor, scenarios over
paths + flow scope, serialization) · eta/core/kb.py (flow_variants,
flow_row_title) · eta/core/matrix.py (Q_j prefix, ref-strip removed)
· eta/core/validation.py (duplicate triple, type-note wording) ·
eta/core/layout.py (ink_rect, metrics-driven make_node/annotation,
node_text_fits) · eta/ui/render.py (TextDontClip on nodes/
annotations) · eta/ui/canvas.py (geometry-protocol comment) ·
eta/ui/theme.py (unchanged constants, comment) ·
eta/ui/controls.py (PopupWrapDelegate, _popup_target_width ≤85) ·
eta/ui/hierarchy_panel.py (_HierTree DnD, scenario/cause rows,
drop_ok/handle_drop, expansion capture v2, cause_selected) ·
eta/ui/inspector_panel.py (current_tree, _site_type_section shared,
outdoor form, exploded _cause_records, flow in cause rows, «→»
chains, «Функциональное назначение» labels, T_ТО) ·
eta/ui/main_window.py (_inspected_tree routing, cause-selected
wiring, chain removal + seam, scenario-selected rework,
_apply_library_equipment «ref#flow», _usage templates, ui-dict
cause-collapse, tgm_view by value) · eta/ui/kb_window.py
(editable TemplatesTab + form + buttons/usage; GSLibraryTab exploded
rows + signal-blocked reloads; suffix-safe title edits) ·
eta/export/pdf_export.py (Q_j lines, _tree_sources block, П1.3/П1.4
label) · eta/knowledge/knowledge_base.json (scenario titles,
fire_node_title, flow_titles, pm-ttest T_ТО – byte-safe scripts) ·
eta/__init__.py (6.5.0) · smoke_test.py (blocks 1/4/21 + assertions)
· gesture_test.py (updated blocks 1/3/9/32/36/37/39 + new 39–45) ·
visual_qa_runner.py (_load_form, comment) · README.md · qa_artifacts
(regenerated).

## Test results / Visual QA

* smoke_test.py – PASS: 22 printed blocks (previous 21 + new block
  21 «Задача 3.3»; blocks 1 and 4 extended with the Task-7 renames
  and the Task-1 type cascade incl. linear/apparatus values and the
  П1.4-by-length switch).
* gesture_test.py – PASS: 45 blocks (blocks 1–38 of sessions 12–14
  with updated assertions where behavior changed deliberately:
  version 6.5, the picker seam (ref, flow), the new hierarchy
  structure in block 3, scenario-row collapse in block 32 + NEW
  blocks 39 «Задача 9», 40 «Задачи 1+2», 41 «Задача 6», 42
  «Задача 11», 43 «Задача 8», 44 «Задача 3», 45 «Задача 10»).
  GESTURES PASSED, exit 0.
* run_qa.cmd – regenerated (twice: the second run expands the участок
  for the hierarchy shot – the runner now re-collapses it afterwards);
  qa_stats: app 6.5.0, kb_version 6.1, 3 trees, pdf_rendered true,
  report_pages 5. Vision review (crops + 2–3× upscale, glm-5.3-flash):
  * qa_canvas (+3× fire-node crop) – **no glyph touches any node
    border**: the «ΣQ = 1,86·10⁻⁵ год⁻¹» row is whole with visible
    right/top/bottom gaps; backed by the programmatic
    `node_text_fits` pass over every node and annotation (metrics
    assertions beat vision estimates).
  * qa_hierarchy – the NEW structure confirmed: «Сценарий пожара
    ТГМ» under «Участок 1» with the cause children
    «Образование ГС: Пожар по поверхности…» + plain IЗ rows; no
    «Группа сценариев» anywhere.
  * qa_matrix – the Q column shows engineering notation; the
    «Формула» column sits beyond the screenshot viewport (horizontal
    scroll) and is verified PROGRAMMATICALLY per cell by gesture
    block 36 (starts with «Q₁ = », contains «exp(−», no «(табл.»,
    no «e^(», no «a₁·F»); the PDF report text is asserted through
    QPdfDocument.getAllText («Q₁=», «exp(−», the
    «Источники:табл.П1.3–множительa₁·F» block).
  * qa_kb_templates – the right pane is the EDIT FORM (Название,
    Категория, Тип сценария combo, РАЗНОВИДНОСТИ ГС list with
    «Добавить…»/«Убрать», РАЗНОВИДНОСТИ ИЗ; the bottom-left record
    buttons visible).
  * qa_kb_gs – exploded flow rows confirmed with the exact suffixes
    («– массовый расход истечения < 1 кг/с», «… 1–50 кг/с»,
    «… > 50 кг/с»), the rupt row «…Разгерметизация, Полное
    разрушение» WITHOUT a suffix, and capitalized sub-parts after
    the colon/comma.
* The real knowledge_base.json edits: three byte-safe scripts
  (T_ТО, scenario titles, flow_titles), each verified by re-reading
  and asserting the exact result, deleted after use. Tests keep
  their in-memory snapshots; the file on disk was never touched by
  tests.

## Known issues / notes

* Task-1 semantics change recalculates existing projects (LOCKED):
  linear/apparatus участки now feed the ТГМ multiplier with
  length/volume; previously such участки fell back to помещение/
  здание area.
* A GS dependency chain uses the ROOT's flow scope for its scenario
  rows (children multiply as factors); mixed-flow chains are the
  user's responsibility (documented choice).
* Template flow entries are encoded «ref#диапазон» inside the
  existing `gs_causes` string list (no schema change; plain refs
  remain valid and mean all ranges).
* «скорость сгорания» is fully replaced by «массовый расход
  истечения» (П2.1 terminology) in data and UI; the KB П2.1 sub-tab
  range labels («< 1 кг/с», «1–50 кг/с», «> 50 кг/с», «полный
  разрыв») were already correct.
* Hierarchy cause/scenario rows are not multi-selectable deletion
  targets (Delete still removes only objects); cause removal goes
  through the inspector «Убрать» (with the chain confirm).
* The gesture harness needed real re-fetches of hierarchy item
  references after every rebuild (Qt deletes QTreeWidgetItems on
  clear) – documented in the test comments for future sessions.
* run_qa.cmd may exit 1 on teardown after writing all artifacts
  (offscreen quit race, cosmetic – as in previous sessions).

---

# SESSION 15/1 ADDENDUM – Kuji 6.5.1 (same day)

Customer defect report: the cause drag-and-drop did not work with the
REAL MOUSE (Task 3.3 of the session). Plus three refinements: a
«Редактировать/Сохранить/Отмена» mode for the template form, softer
UI colors, and a styled drag.

## 1. Real-mouse drag defect – root cause and fix

* Reproduced with a real-mouse harness (QTest.mousePress + a
  button-held QMouseEvent + releases): `startDrag` was NEVER called –
  Qt's item views refuse to start a drag from an item that is not
  **selectable**. The cause and scenario rows were created with
  `ItemIsEnabled | ItemIsDragEnabled` only. The session-15 tests
  passed because they drove `drop_ok`/`handle_drop`/`setCurrentItem`
  programmatically – selectability never mattered there, so the dead
  mouse path went unnoticed. (A second masking factor: real CLICKS on
  those rows never made them current either, so the cause-row click
  behavior was also dead in practice.)
* Fix: cause and scenario rows now carry `ItemIsSelectable` as well
  (object rows always had it). Real clicks select the row and drive
  `_on_select` (the LOCKED 3.6 cause-row click behavior now works
  with the mouse), and real drags reach `startDrag`.
* Styled drag (customer request «перенос должно быть стилизовано»):
  `_drag_pixmap(text)` renders a semi-transparent rounded light-blue
  tag with the row title (flat, theme palette, ≤42 chars); it is set
  via `drag.setPixmap/setHotSpot` in `startDrag`.
* Post-drop UX (per the Gemini-formalized checklist): after a
  successful cause drop the target row is EXPANDED and the moved row
  is SELECTED and scrolled into view (`_reveal_cause`); after a tree
  move the scenario row on the new owner is expanded and selected.
  A private MIME mark (`application/x-kuji-hier`) tags our own drags:
  foreign drags are ignored on enter, and the mark lets tests deliver
  synthetic QDragEnter/Move/DropEvents through the viewport (the way
  real DnD delivers them) because the offscreen platform cannot
  execute `QDrag.exec` at all.
* Tests: gesture block 46 – (а) real press + button-held move asserts
  `startDrag` is invoked through the actual Qt view state machine
  (this was the defect); (b) synthetic enter→move→drop through the
  viewport assert the blue target highlight, the dependency
  (cable.parent = lamp.cid), the immediate single-chain scenario row,
  the expanded target and the selected moved row.

## 2. «Редактировать / Сохранить / Отмена» (template form)

* The «СОСТАВ ШАБЛОНА» form is now READ-ONLY by default; the
  «Редактировать» button (top-right of the form) unlocks all fields
  and morphs into «Сохранить» + «Отмена».
* «Сохранить» fixes the edits (marks the tab dirty for the window's
  «Сохранить» = kb.save) and returns the form to read-only; «Отмена»
  restores the snapshot taken at «Редактировать» (title, category,
  scenario type, both lists) and returns to read-only. Switching
  templates mid-edit auto-cancels (snapshot restored); a rebuild of
  the SAME template (live card preview) does not break the session.
* «Добавить запись» enters the edit mode immediately for the new
  template. The list «Добавить…»/«Убрать» buttons are part of the
  form (disabled in read-only). Dirty is raised only by «Сохранить»
  (and add/delete template), not by in-edit previews.
* Tests: gesture block 45 rewritten – read-only by default, mode
  toggling via real button clicks, commit keeps the edit, cancel
  restores the snapshot.

## 3. Softer colors (customer: «ядовито-синий» → «ласковый»)

* Hierarchy selected row: #2563EB background + white text →
  **#93C5FD** with the dark primary text; QListWidget selections
  likewise (picker lists).
* Primary buttons («Добавить причину», «Применить на холсте»,
  «Добавить…», «Сохранить», «Редактировать» …): #2563EB →
  **#3B82F6**, hover #2563EB, pressed #1D4ED8.
* Canvas node-state colors (#2563EB «задано» etc.) are NOT touched –
  they are a LOCKED session-14 decision and not part of the
  selection/button complaint.
* Vision-verified on the regenerated artifacts: the form is read-only
  with the visible «Редактировать» button; the selected hierarchy row
  is light-blue with dark text.

## Acceptance (15/1)

* smoke_test.py – PASS (22 blocks, unchanged); gesture_test.py – PASS
  (46 blocks: updated 45 + new 46); run_qa.cmd regenerated
  (app 6.5.1); vision review of the two affected artifacts passed on
  first pass.
* Version → 6.5.1.

## Answer to «1.1 – how to give tasks so they don't get lost»

The failure mode here was not a lost task: the feature existed and
its logic was seam-tested, but the REAL-MOUSE path was dead and the
test suite never exercised it (offscreen tests can't run QDrag.exec,
and programmatic calls masked the missing ItemIsSelectable). To
prevent a repeat: (1) for every mouse-interaction requirement, demand
a REAL-MOUSE regression test (press/move/release via QTest, not
programmatic calls) – I've added exactly that as block 46 and will do
so by default for any new mouse behavior; (2) after each session,
manually smoke-test with `run_app.cmd` the specific interactions you
described (the screenshots you send back become the acceptance
criteria); (3) when writing tasks, name the interaction channel
explicitly («мышью», «с клавиатуры») – that tells me which harness
must prove it.

## Customer decisions after 15/1 (Q&A, LOCKED)

1. Reordering causes on the same level (drop «between» rows) is NOT
   needed – nesting under a cause and detaching to the top level are
   sufficient (order does not affect the math).
2. The «Редактировать/Сохранить/Отмена» mode stays on the «Шаблоны
   оборудования» tab only; the ГС/ИЗ/«Защитные средства» libraries
   keep direct cell editing.
