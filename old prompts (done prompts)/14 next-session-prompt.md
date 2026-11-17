# PROMPT: Kuji – Session 14. Hierarchy integrity + inheritance cascade + node states + math typography

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–13 are done (v6.3.0: five-type paradigm, KB v6.1 with editable libraries, reference annotation nodes, «показано = записано» defaults, layout-independent shortcuts, unbounded free view, delete-only-selection with multi-select batch, window memory, territory units км²|м²). Read before starting: `old prompts (done prompts)\REPORT_SESSION_13.md` (and `REPORT_SESSION_12.md` for deeper history). Everything described there works and is covered by tests – do not break it without need. Session 14 is a **hierarchy-integrity + engine-cascade + visual-state session**: seven tasks. All design decisions were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them. Root causes for tasks 1, 2, 3, 3.1 are ALREADY DIAGNOSED AND CODE-VERIFIED (see the tasks) – verify them quickly, do not re-discover.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report – in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian (this overrides English for question lists; it is the single exception).
- **Application UI language: RUSSIAN** – unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, node texts, messages) must be in normative Russian engineering style (§5 canon).
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README. Never «—» (em dash).
- Questions protocol (HARD GATE): ask **incrementally, per task, as work progresses**, NOT as one giant upfront list. When a task or part of it is ambiguous, has no concrete object, or carries double meaning – STOP that task, formulate a SHORT numbered question list in Russian about exactly that task, send it, and WAIT. Do not implement on assumptions. Principle #1 from the customer: «Better to ask 10 times than to mess up once.» While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items – but nothing that changes data semantics or file formats. All LOCKED decisions below must NOT be re-asked.

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` – Python 3.14.3, PySide6 6.12.0 |
| Entry point | `main.py`; launcher `run_app.cmd` (manual start is the USER's habit – never launch it in automated batches) |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_hierarchy (+qa_hierarchy2 scrolled), qa_tooltip, qa_combo, qa_matrix, qa_docview, qa_sheet, qa_switches, qa_inspector_fire, qa_inspector_building, qa_inspector_territory, qa_kb_templates, qa_kb_measures, qa_kb_iz, qa_kb_gs, qa_kb_fire_modes, qa_kb_tables, qa_kb_tables2, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_stats.json) |
| Core tests | `smoke_test.py` (18 blocks), `gesture_test.py` (session-12 blocks 1–19 + session-13 blocks 20–29; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – sections: meta (`version` «6.1»), scenario_types (5), gs_causes (68), iz_causes (15), fire_types (8), p21, flow_titles, p13 (10), p14 (8), equipment_templates (16), property_modifiers (13, `target`: gs/iz/room/building; new user measures may add type "k" records at runtime). Backup: `knowledge_base_v5.json` (keep). This session does NOT edit KB data via scripts. `meta.version` stays «6.1» unless a schema change becomes unavoidable (none is planned). |
| App version | `eta\__init__.py` → `__version__ = "6.3.0"` – this session bumps to **6.4.0**. Status bar shows the version; gesture test asserts it (update the assertion). |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_14.md` (English) at the end |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` with verification, delete the script afterwards. Inline `python -c` in pwsh breaks on quotes – write a file. |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE. Do not wire it in. |

## 2. STATE AFTER SESSION 13 (v6.3.0) – what exists, all tested

- **Paradigm** (invariant): five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree «Наличие вещества / Наличие ОК → ГС → ИЗ → Возникновение пожара/взрыва»; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5.
- **ТГМ multiplier today**: `CalcContext.tgm_multiplier` reads `building_props`: `F = building.area_m2`, `>10 000 → a·F^b` by `p14_type` else `a₁·F` by `p13_type`. `ctx_map` (main_window) builds building_props = nearest building (outdoor installation = itself), room_props = nearest room, site_props = owner's own. **Task 5 changes the F/type source – see below.**
- **«Показано = записано» invariant (session 13)**: every displayed form default is materialized into props at form build (`_ensure_default` in inspector_panel). Defaults come from `DEFAULT_PROPS` (objects.py). **Task 5 amends this for room/участок area/type: variant (а) «наследуется» – see task.**
- **Hierarchy** (`eta\ui\hierarchy_panel.py`): 7-button toolbar (6 kinds + «Добавить дерево», violet glyph, room→auto-«Участок N»); `PARENT_RULES` (objects.py): building→territory, compartment→building, room→building/compartment, area→room, outdoor→territory, territory→root; ExtendedSelection is SET but **real Ctrl/Shift multi-select is broken – Task 2**; context menu = «Переименовать…»/«Удалить с поддеревом…» only; `props_requested` removed; Delete = only the selection (+descendants), batch window `_confirm_multi_delete`; **known defect: `rebuild()` calls `tree.expandAll()` + `_expand_scenario_groups()` unconditionally – Task 3.1**; viewport event filter installed ONCE (session-13 fix); rename editor owns Delete while editing.
- **Canvas** (`eta\ui\canvas.py`): LMB node drag (5 px threshold) with persisted `node_offsets` (slots substance|oxidizer|gs|iz|fire, applied inside `compute_layout`); annotation items (`AnnotationItem` work scene / `_DocAnnotationItem` doc scene) with magnetic attach (ANN_SNAP_DIST 30 px, «Привязать» tip), follow-on-drag, detach; LMB-empty/СКМ pan; wheel zoom (gestures mixin `_init_gestures()`); Delete on canvas deletes the owning tree; sticky clamp / free mode (work scene ±100 000 px margin, doc scene keeps exact layout rect).
- **Annotation nodes** (`layout.py::Annotation`, `render.py::draw_annotation`): one per tree, text `{owner} · {type}` (live), dashed 1 px border, APP_BG fill, secondary text, ≤2 lines; in scene union; format-5 optional per-tree field `annotation` on TreeModel; «Авторазметка» resets free ones, attached follow nodes.
- **Node bodies/colors**: body = «Всего: N …» + «ΣQ = … год⁻¹»; styles meta/muted/total; KIND_STYLE in render.py: presence (BORDER/#FFFFFF), gs (amber #B45309 / #FFFBF5), iz (red #B91C1C / #FFF7F5), fire (HAZARD #DC2626 / #FFF5F5); empty causes → gray «не задано». **Task 6 adds state colors.**
- **Main window** (`eta\ui\main_window.py`): QSplitter 320/500/360 (`ui/splitter`); `_delete_selection` priority canvas-node→hierarchy-batch→tree; `_update_trash` via `hierarchy.selected_objects()`; Alt+A twins (Alt+A + Alt+Ф, ApplicationShortcut; Ctrl+E/У, Ctrl+D/В, Ctrl+Q/Й twins); doc pop-out: reopen fix + `ui/doc_geometry`; KB window lazy singleton + `ui/kb_geometry`; `_usage(section, id)` counts referencing trees/objects for library deletions; `_auto_layout` resets node offsets + free annotations.
- **Inspector** (`eta\ui\inspector_panel.py`): building form (F_зд + «Тип (П1.3)/(П1.4)» auto-switch combo `_type_combo_13_14`, молниезащита + категория + S/L/H, `_universal_measures_block` for type-"k" measures), room form (площадь, аварийная вентиляция + A, universal measures), area form («Выберите тип:» + SITE_FIELD value), outdoor form, territory form («Площадь территории:» + spin + unit combo км²|м², value normalized in `strike_area_km2`, unit in `strike_area_unit`, informative-only tooltip), compartment form; presence form; cause blocks; pedal blocks (KB tooltips); commit-on-leave.
- **KB window** (`eta\ui\kb_window.py`): tabs «Шаблоны оборудования» / «Горючие среды (ГС)» (`GSLibraryTab`) / «Источники зажигания (ИЗ)» (`IZLibraryTab`) / «Таблица типовых режимов пожара» (`FireModesTab`, read-only, 8 rows, abbreviated names) / «Таблицы типовых частот» (sub-tabs П1.3/П1.4/П2.1) / «Защитные средства» (`MeasuresLibraryTab`: 4 columns «Наименование средства | Коэффициент | Носитель | Примечание»; coefficient numeric edits drive the ENGINE – model reads the KB record; universal k type-"k" measures on any target). `_LibraryTab` base (3 columns, note/number editors `_NoteEditor`/`_NumberEditor` with live preview); bottom bar `[Добавить запись] [Удалить запись]` LEFT, `[Сохранить] [Закрыть]` RIGHT; `kb.reindex()` runs on every library mutation (indexes never stale); dirty-guard close; engineering format everywhere via `_fmt_eng` (layout.fmt_q).
- **Engine** (`eta\core\model.py`): `_gs_k(kb)`/`_iz_k(rec, kb)` read modifier numbers from KB records (`modifier_by_pedal`); universal type-"k" branch on node pedals; `CalcContext.universal_k(kb)` for room/building-target measures (× Q_ГС in `_q_gs`); `tgm_multiplier(kb)` as above; `lightning_q`, `vent_k`; scenario formula strings built with `:g` formatting and inline notes like `[a₁·F = 9e-05·1200 (табл. П1.3)]` **– Task 7 changes display**.
- **Objects** (`eta\core\objects.py`): kinds/PARENT_RULES/`DEFAULT_PROPS`/`effective_properties` cascade/`add_child(kind, parent)` with `can_add` validation; **known defect in `can_add` – Task 1**; `load_from_dict` (no repair today).
- **Serializer** (`eta\core\serializer.py`): format 5; optional per-tree `node_offsets`, `annotation`; `save_project(..., ui: dict | None)` / `load_project` returns `ui` (currently unused by MainWindow) **– Task 3 uses it for collapsed state**.
- **Wrap/typography**: shared helpers in `controls.py` (`wrap_words85`/`split_long_word`/`wrap_text85`, ≤85 chars, syllable split with «–»); used by tooltips and all KB tables; `theme.py`: `fmt_q` («6,20 × 10⁻⁴» with « × »), `parse_sci` (comma/dot + e-notation), QSS (QComboBox min-width 110px – relevant to Task 4); `layout.py::fmt_q` («3,2·10⁻⁵» with «·») used by KB/status/nodes.
- **Matrix** (`eta\core\matrix.py` + `_refresh_matrix`): columns №/Участок/Тип/Сценарий/Q/Формула; **Q column prints `f"{row.q:.3e}"` with comma – raw «3,240e-06» (Task 7); Формула column shows raw `9e-05` and `(табл. П1.3)` refs (Task 7)**.
- **Tests/QA**: both suites green; QA artifacts current and vision-reviewed (session 13).

## 3. CODE MAP (extend, don't break)

- `eta\core\objects.py` – Task 1 (`can_add` guard, root-only territory, `load_from_dict` repair), Task 3 (nothing), Task 5 (explicitness semantics live in props presence).
- `eta\core\model.py` – Task 5 (`tgm_multiplier` cascade via ctx), Task 7 (formula strings).
- `eta\core\matrix.py`, `eta\ui\main_window.py::_refresh_matrix` – Task 7 (Q column + formula cleanup).
- `eta\core\layout.py` / `eta\ui\render.py` – Task 6 (state colors computed in layout, drawn in render; shared canvas/PDF).
- `eta\core\validation.py` – Task 6 (reuse `check_tree` verdict for the fire node state).
- `eta\ui\hierarchy_panel.py` – Tasks 2, 3, 3.1 (selection decoupling, expansion preservation, collapsed-by-default for new участок/установка), Task 1 (add_kind routing + tooltip).
- `eta\ui\main_window.py` – Tasks 2 (refresh split), 3 (ui-dict save/load of collapsed set), 5 (ctx_map cascade inputs if needed).
- `eta\ui\inspector_panel.py` – Tasks 4 (compact unit combo), 5 (type combo + area with «наследуется» on room/участок forms; variant (а) semantics).
- `eta\ui\controls.py` / `theme.py` – Task 4 (compact combo helper/QSS), Task 7 (parser: caret notation; engineering formatter single source).
- `eta\ui\kb_window.py` – Task 7 (`_NumberEditor` hint text accepts both notations).
- `eta\export\pdf_export.py` – Task 6 (colors via render.py automatically), Task 7 (report formulas/values in engineering notation; table references in the REPORT stay).
- Tests: `smoke_test.py`, `gesture_test.py` – update/add per task list; `visual_qa_runner.py` – add shots where valuable (repaired project load, collapsed new участок, multi-select visible selection, colored задано nodes, matrix math).
- Do not touch: `eta\ui\gestures.py` (don't break), `eta\ui\scroll.py`, `eta\ui\switch.py`, `eta\core\formulas.py` (dead).

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py` – never fork geometry or colors. Task 6 colors go through `render.py` once.
2. No new external dependencies; PySide6-native only.
3. Style: flat Swiss-utilitarian; new visuals via `theme.py` (objectName-driven), no ad-hoc colors (Task 6 hexes are LOCKED); `outline: none` everywhere focus rectangles could appear.
4. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference changed strings/behaviors (grep the tests first); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop+2× upscale for pixel truth) the affected artifacts before declaring the task done. Animations must not break offscreen tests.
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions below are NOT to be re-asked.
7. Modal dialogs block offscreen tests: use/extend the existing seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_multi_delete`, `_confirm_delete_rec`, patched `exec` capture) – do not break them.
8. Suggested order: 1 → 2 → 3/3.1 → 4 → 7 → 5 → 6. Task 5 (engine cascade) is the most semantic one – do it after the mechanical hierarchy work, with the confectionery example updated in the same commit.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses: «уровень полноты безопасности (SIL)».
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Math in labels/tooltips via the project mini-notation (`math()`, `math_html_lines`); raw HTML escaped; QTableWidgetItem cells render NO HTML; rich cells are QLabel cell widgets.
- Numbers shown to the user: ALWAYS engineering notation («9·10⁻⁵», comma mantissa, Unicode superscripts) – never `9e-05` (Task 7 makes this global).

---

## TASK 1. TERRITORY NESTING BUG (screenshots №1/№3/№4 of the first batch)

**Defect (customer screenshots):** №1 – deep alternating chain «Территория 1 → Здание 1 → Территория 2 → Здание 2 → …» (territories nested inside buildings); №3 – «Территория 2» INSIDE «Участок 3» (red arrow + «??»); №4 – the same plus «Здание 2» inside that same участок.

**Root cause (diagnosed and code-verified, confirmed by the customer):** `objects.py::can_add` – `PARENT_RULES[TERRITORY]` is an EMPTY set, and `can_add` treats an empty set as «allowed with ANY parent» (`if not allowed: return True`). So «Добавить территорию» with a building/участок/помещение selected calls `add_child("territory", target)` and succeeds → the territory becomes a CHILD of that object. `add_kind` then also allows «Добавить здание» under that (formally legal) nested territory → the chains in the screenshots.

**Requirements (LOCKED):**
1. A territory is created ONLY at the ROOT of the hierarchy, regardless of what is currently selected. Fix `can_add` (territory requires `parent is None`), fix `add_kind` routing (territory always attaches to root; the sibling rule «territory under territory» creates a root sibling as today), keep the button always enabled; update its tooltips (enabled hint and statusTip) to say the territory is created в корне иерархии (normative Russian, en-dash).
2. **Load repair (LOCKED вариант (а)):** `load_from_dict` (and therefore project open) automatically straightens damaged files: any territory found NOT at root is lifted to root together with its whole subtree (children keep their relative structure under it); after lifting, re-validate the remaining structure against `PARENT_RULES` (orphaned/invalid placements that cannot occur via the UI should also be lifted to the nearest valid ancestor or root – implement conservatively and document). Trees owned by moved objects keep their `owner_id`s – nothing is lost. When a repair actually changed something, show a status-bar message (8000 ms) in Russian, e.g. «Файл содержит вложенные территории – N территорий перемещены в корень иерархии».
3. Regression tests (smoke + gesture): `can_add("territory", <building/area/room/outdoor>)` is False, `can_add("territory", None)` True; gesture: select a building, click «Добавить территорию» → new territory appears at ROOT (not inside); craft a damaged project dict (nested territory with a building and a tree under it), load → territory at root with subtree intact, trees alive, status message shown, id round-trip preserved.

## TASK 2. CTRL/SHIFT MULTI-SELECT IN THE HIERARCHY (real mouse)

**Defect:** Ctrl+LMB / Shift+LMB do not produce a multiple selection in the running app.

**Root cause (diagnosed):** every `itemSelectionChanged` → `_on_select` → `object_selected` → `MainWindow._on_object_selected` → `_refresh()` → `hierarchy.rebuild(...)` → `tree.clear()` + refill + `expandAll()` + `_restore_selection` (single currentItem only). The full rebuild on every selection change instantly destroys the multi-selection (session-13 tests passed because they set selection programmatically with signals blocked – real Ctrl-click goes through the live signal chain).

**Requirements:**
1. Decouple selection from structure: a selection change must NOT rebuild the tree. Split the hierarchy update paths: structural rebuild (objects/trees changed) vs selection-only update (inspector form, toolbar gating, trash state, KB apply hint). `_refresh` should not recreate QTreeWidgetItems when only the selection moved; multi-selection must survive clicks, inspector updates, and trash transitions.
2. Multi-select semantics stay as confirmed (session 13 / Q&A 12): inspector shows the last-clicked (current) object; Delete opens the ONE batch confirmation window («Удалить N объектов с поддеревьями?»); «Удалить запись»-style batch flows unchanged.
3. Tests must use REAL mouse simulation: `QTest.mouseClick(viewport-rect-of-item, LeftButton, ControlModifier / ShiftModifier)` – verify 2- and 3-object selections survive, Delete batch works from a real Ctrl-selection, and a plain click resets to single selection. (Lesson: programmatic `setSelected` with blocked signals hides this class of bug.)

## TASK 3 / 3.1. COLLAPSED STATE OF THE HIERARCHY

**Defect (screenshot №2 of the first batch):** «Добавить участок» adds the участок already EXPANDED with its child «Группа сценариев» visible. **3.1:** after the user collapses any node (участок, здание, помещение…), the FIRST left-click anywhere resets everything to expanded again.

**Root cause (diagnosed, same family as Task 2):** `rebuild()` unconditionally calls `tree.expandAll()` (+ `_expand_scenario_groups()`), and rebuild runs on every selection change / refresh.

**Requirements (LOCKED):**
1. Rebuild preserves the expanded/collapsed state per object id: capture the set of COLLAPSED object ids (and the expansion state of «Группа сценариев» groups) before `clear()`, restore after refill. Unknown/new items default EXPANDED – EXCEPT new Участки and new наружные установки, which are added COLLAPSED (LOCKED: only these two kinds; здания/помещения/отсеки are added expanded as now). The auto-created «Участок N» from the «Добавить дерево» button (room flow) is also added collapsed.
2. Clicks, selection changes, inspector updates, canvas selections – nothing re-expands collapsed nodes (follows from Task 2 + this task).
3. **Persist the collapsed state in the project file (LOCKED 11б):** format 5 `ui` dict (serializer already supports `ui`): e.g. `ui = {"hierarchy_collapsed": [oid, ...]}`. MainWindow collects the currently collapsed ids on save, applies them after load (unknown ids ignored). On open WITHOUT saved state: everything expanded (as today). Round-trip tests required.
4. Tests: new участок/установка added collapsed (others expanded); collapse здание → click empty area / another object → stays collapsed; «Группа сценариев» collapsed stays collapsed across rebuilds; save/load round-trip of the collapsed set.

## TASK 4. COMPACT UNIT COMBO «км²|м²» (screenshot №1 of the second batch)

**Defect:** in the territory form the unit combo next to «Площадь территории:» is ~200 px wide while its text («км²») is ~20 px (red oval in the screenshot). Cause: the combo is a `wide_combo` (QSS `QComboBox { min-width: 110px; }` + row stretch + adaptive popup machinery).

**Requirements:** make the unit combo COMPACT – content-sized (text + dropdown arrow, roughly 60–80 px), never stretching with the panel; the popup list stays adaptive/readable («км²»/«м²»). Do not change other combos (KB/forms keep `wide_combo`); either a small `compact_combo()` helper in `controls.py` or targeted sizing for this one combo (document the choice). Test: combo width ≤ ~90 px while the territory form is open (gesture assertion on `width()`); QA shot qa_inspector_territory updated.

## TASK 5. ТГМ AREA/TYPE INHERITANCE CASCADE (engine + forms)

**Customer's requirement:** the «Возникновение пожара» node (the ТГМ multiplier a₁·F / a·F^b) must take the area from the УЧАСТОК that owns the tree, not from the building; if the участок's own area is not set – from the ПОМЕЩЕНИЕ containing the участок; the type selection (П1.3/П1.4) must exist at the building AND the room AND the участок, and the effective type for a tree is the nearest explicitly chosen level. Outdoor installations keep their own area and type (unchanged). Trees are created ONLY on участки and наружные установки – the model does NOT change (LOCKED Q&A 2: вариант (а); no trees on rooms).

**LOCKED semantics (variant (а), resolves the conflict with the session-13 invariant):**
1. **Area:** `F` for the multiplier = the first EXPLICITLY set `area_m2` in the chain участок → помещение → здание (outdoor: its own `area_m2` as today). The П1.3-vs-П1.4 switch (`F > 10 000 м²`) uses this effective F.
2. **Type:** the room form and the участок form get the SAME «Тип (П1.3)/(П1.4)» combo as the building (auto-switching label by the level's effective F). Their combos have a placeholder row «– наследуется –» as the DEFAULT: **nothing is written into props until the user explicitly chooses a type** (the session-13 «показано = записано» invariant is interpreted for these fields as: the CHOSEN value is always stored; the inherited state is displayed but not stored). The BUILDING combo keeps materializing as today (it is the last link of the cascade). The effective type for a tree = the nearest level in участок → помещение → здание that has an explicit `p13_type`/`p14_type` (per key: if the effective F is ≤ 10 000, cascade `p13_type`; else `p14_type`; if nobody set it, the building's materialized value applies; if no building at all and nothing set → multiplier 0 with the existing «не выбран тип» note).
3. **Room/участок AREA display follows the same principle:** the form shows the effective (inherited) value when the level's own `area_m2` is absent – render it as a clearly inherited state (e.g., grey placeholder text of the inherited value + hint tooltip «наследуется от помещения/здания»); the user editing the field writes the level's OWN value (thereafter it is explicit). Do NOT materialize defaults for room/участок area. The territory form and building form keep their current materialization. Normative Russian for all new strings, en-dash.
4. **Cascade inputs:** extend `CalcContext`/`ctx_map` so `tgm_multiplier` resolves F and the type over the three levels (site/room/building props with explicitness = key presence; note `effective_properties` already merges parent props – you need per-level EXPLICIT values, so build the chain from the object tree, not from the merged dict; document the helper). Outdoor stays as now.
5. **Confectionery control example (smoke block 3) is updated** to the new semantics (the 2960.77 м² area and `p13-multi` type move to the room/участок level of the test context; keep the numeric result ~2,30·10⁻⁵). The customer confirmed the semantics change recalculates existing ТГМ projects (Q&A 4) – document in the report and README.
6. Tests (smoke + gesture): cascade участka overrides room overrides building; unset участок falls back to room, unset room to building; «наследуется» placeholder shown and not stored until explicit choice; effective-F auto-switch of the combo label at each level; outdoor unchanged; validation note when nothing is set.

## TASK 6. NODE STATE COLORS (screenshot №2 of the second batch)

**Customer's requirement:** the ГС and ИЗ nodes keep their CURRENT colors while their causes are «не задано» (amber/red borders with cream/pink fills – exactly as today); as soon as the causes are заданы, the node switches to a BLUE border with a white-light-blue fill. The «Возникновение пожара/взрыва» node keeps its current red/pink styling until its calculation is complete and correct, then switches to a VIOLET border with a white-light-blue fill.

**LOCKED specifics:**
1. Colors: ГС/ИЗ «задано» – border `#2563EB`, fill `#EFF6FF`; «Возникновение» OK – border `#7C3AED`, fill `#F5F3FF`. «Задано» = the node has at least one cause (the existing «не задано» condition inverted). «Возникновение» OK = **`check_tree` has NO failed issues for the tree** (LOCKED Q&A 5: «валидатор не имеет замечаний к дереву» – all issues `.ok`; not merely Q > 0).
2. WYSIWYG: the state colors apply identically on the canvas and in the PDF/лист (single source in `layout.py`/`render.py` – e.g., a per-node `state` computed in `compute_layout` from causes + validator verdict, consumed by `draw_node` in `render.py`). Node text content is unchanged.
3. Performance: run `check_tree` once per tree per rebuild (it is cheap), not per node paint.
4. Tests: smoke/gesture assert the state flags for: empty GS («не задано», old colors), filled GS/IZ (blue state), fire node violet iff the validator is clean (make a tree with an invalid cause selection → NOT violet; fix the cause → violet). QA shots qa_canvas/qa_sheet show the mixed states.

## TASK 7. MATHEMATICAL NOTATION EVERYWHERE + MATRIX FORMULA CLEANUP + CARET INPUT

**Defect (screenshot №3 of the second batch):** the matrix «Формула» cell shows `Q = 1·1·[a₁·F = 9e-05·1200 (табл. П1.3)]·1−e^(−3e-05)` – raw scientific notation and inline table references; the Q column shows `3,240e-06`.

**Requirements (LOCKED):**
1. **Display – whole program:** anywhere a numeric frequency/value is shown to the user in e-notation (`9e-05`, `3,240e-06`, `1e-06`), render ENGINEERING notation «9·10⁻⁵», «3,24·10⁻⁶» (comma decimal mantissa, Unicode superscripts – the `layout.fmt_q` style already used in the KB/status/nodes). Known spots (grep to confirm completeness): `main_window._refresh_matrix` Q column (`f"{row.q:.3e}"`), the matrix «Формула» column, scenario formula strings built in `model.py` (pieces like `f"{q:g}"`, `[a₁·F = …]`, `1−e^(−…)`), the PDF report lines (formulas AND values; the e-power STRUCTURE stays, only numbers inside get engineering format, e.g. `1−e^(−3·10⁻⁵)`), the cause-picker suffix in `inspector_panel._CausePickerDialog` (`f"{q:g}"`). Factor the formatting through ONE shared helper (extend `layout.fmt_q`/theme as needed; never fork).
2. **Matrix formula cleanup (LOCKED: matrix ONLY):** remove table references like «(табл. П1.3)», «(табл. П1.4)», «(П1.2)» from the «Формула» column of the MATRIX; the PDF REPORT keeps its references (LOCKED Q&A 8). Implement so the report path is untouched (either build formula text without refs and re-add refs only in the report, or strip refs in the matrix formatting layer – document the choice).
3. **Input parsing – both notations (LOCKED):** every numeric input that parses values (the KB numeric editor `_NumberEditor`, `theme.parse_sci` consumers) must accept BOTH:
   - e-notation: `1e-6`, `1,02e10`, `2,52e-12` (comma or dot mantissa – works today);
   - CARET notation: `1^-6`, `1,02^10`, `2,52^-12`, where `m^e` means **m×10^e** (LOCKED clarification: caret = «умножить на 10 в степени», NOT exponentiation; `1^-6` = 1×10⁻⁶).
   Extend `theme.parse_sci` (or add a shared `parse_eng`) accordingly; update the `_NumberEditor` hint text (Russian) to name both notations; add unit tests for the parser (both notations, comma/dot, invalid input → None).
4. Display of stored values is ALWAYS engineering notation (never echo the raw input form back).
5. Tests: parser unit checks (smoke); matrix Q/Формула strings contain «·10» superscripts and no «(табл.» (gesture); a formula from a real ТГМ tree renders as e.g. `Q = 1·1·[a₁·F = 9·10⁻⁵·1200]·1−e^(−3·10⁻⁵)`; PDF report page still contains the table references; KB numeric editor accepts `2,52^-12` (seam-level test).

---

## 6. LOCKED DECISIONS (Q&A rounds before this session – normative, not to re-ask)

1. (Task 1) Territory is ALWAYS created at the root of the hierarchy, regardless of the current selection; the nesting bug mechanism is confirmed; damaged projects are straightened automatically at load (nested territories lifted to root with their subtrees).
2. (Task 2) Trees are created ONLY on участки and наружные установки – unchanged (вариант (а)); Ctrl/Shift multi-select must work with real mouse; nothing beyond the existing batch-delete semantics is required for multi-selection.
3. (Task 3) Only new Участки and наружные установки are added collapsed; other new objects stay expanded; collapsed state survives all clicks/rebuilds AND is persisted in the project file (ui dict), restored on open.
4. (Task 4) The unit combo is made compact/content-sized; other combos unchanged.
5. (Task 5) F-cascade: участок → помещение → здание (explicit values only; outdoor own); type combo exists at building+room+участок with a «– наследуется –» default at room/участок (chosen value is stored, inherited state is not – вариант (а)); building keeps materializing; effective type = nearest explicit level; existing ТГМ projects recalculate (customer confirmed); confectionery example updated.
6. (Task 6) Exact colors: задано ГС/ИЗ border #2563EB + fill #EFF6FF; «Возникновение» OK border #7C3AED + fill #F5F3FF; «OK» = validator has no failed issues; empty/error states keep current colors; colors mirrored in PDF (WYSIWYG).
7. (Task 7) Engineering notation everywhere; table references removed from the MATRIX formulas only (PDF report keeps them); input accepts e-notation AND caret notation m^e = m×10^e (comma/dot); display is always engineering.

## 7. FINAL DELIVERABLES

1. Questions asked per task BEFORE its implementation where genuinely ambiguous (§0); locked decisions not re-asked.
2. All seven tasks implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated; new blocks: territory-root + load repair round-trip, real Ctrl/Shift multi-select surviving clicks, collapsed new участок/установка + expansion persistence + ui round-trip, compact combo width, cascade F/type incl. «наследуется» placeholder and effective-F label switch, node state colors incl. validator-driven fire node, engineering notation in matrix/report/picker + caret parser units); `run_qa.cmd` regenerated and vision-reviewed (repaired load, collapsed участок, multi-select selection visible, colored задано/OK nodes on canvas+sheet, matrix math).
3. Version → **6.4.0** (KB `meta.version` stays «6.1»); README updated where behavior is user-visible (root-only territories + auto-repair, working multi-select, collapsed/persisted hierarchy, compact unit combo, area/type inheritance cascade and recalculated ТГМ projects, node state colors, engineering notation + caret input).
4. `old prompts (done prompts)\REPORT_SESSION_14.md` (English): per-task summary, files touched, root causes with the exact fix for tasks 1/2/3/3.1, before→after strings for every changed user-facing label/tooltip/format, test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only; never pwsh string cmdlets; delete scripts after use; no em-dash anywhere.
- Modal dialogs block offscreen tests: use the seams; new confirmations must be seams too.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: app-level filters/animations keep strong module-level refs; toolbar buttons use NoFocus.
- Delete delivery: tree/canvas VIEWPORT event filters; the tree filter is installed exactly ONCE (session-13 fix – do not duplicate); the rename editor owns Delete while editing.
- **Selection ↔ rebuild coupling is the root cause of both Task 2 and Task 3.1: never rebuild the tree on a selection change, and never `expandAll()` blindly in `rebuild()` – preserve state per oid.**
- **Programmatic `setSelected` with blocked signals hides mouse-path bugs: multi-select tests must use `QTest.mouseClick(..., ControlModifier/ShiftModifier)` on item rects.**
- `add_kind` must re-select the new node after rebuild (session-12 fix); new участок/установка re-selected but COLLAPSED (Task 3).
- The session-13 «показано = записано» materialization now has ONE deliberate exception (room/участок area + type – variant (а) «наследуется»); do not materialize those, do not break the others.
- Letter shortcuts need Latin+Cyrillic twins (Alt+A/Ф etc.); QTest keyClick sends key CODES.
- QTableWidgetItem renders NO HTML; rich cells are QLabel cell widgets; mini-notation for math; `html.escape` KB titles («< 450 м³»).
- One painter per QPdfWriter, new pages via `newPage()` only; PDF export uses `layout.scene_rect` (free-mode enlarged VIEW rect must not leak).
- Offscreen QA: `QT_QPA_FONTDIR=C:\Windows\Fonts`; stderr noise is harmless; never leave a modal open in a test; offscreen screen ~800×600 clamps restored window geometry – keep geometry tests within it.
- KB libraries: `kb.reindex()` after any direct data-list mutation (indexes must see new records immediately).
- The real knowledge_base.json must never be modified by tests – snapshot/restore `kb.data` in memory.
- Vision QA reads downscaled images – crop and 2× upscale before asking glm-5.3-flash; programmatic checks beat vision estimates.
- WYSIWYG invariant: canvas and PDF both consume `compute_layout` + `render.py` – every geometry/color change goes through them once.
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
