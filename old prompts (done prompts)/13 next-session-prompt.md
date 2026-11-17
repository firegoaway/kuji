# PROMPT: Kuji – Session 13. Stabilization + KB libraries as engineer tables + canvas reference nodes

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–12 are done (v6.2.0: five-type paradigm, KB v6.1, per-pixel scrolling, KB sub-tabs, session-11 canon texts, session-12 interaction restoration – Delete, node drag with persisted offsets, «Авторазметка», sticky/free wiring, splitters, adaptive tooltips/combo popups, presence-as-probability). Read before starting: `old prompts (done prompts)\REPORT_SESSION_12.md` and `REPORT_SESSION_11.md`. Everything described there works and is covered by tests – do not break it without need. Session 13 is a **stabilization + KB-overhaul + canvas-annotation session**: thirteen tasks (0–12). Precise decisions for every task were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them. Root causes for several defects are already diagnosed (see tasks 1, 2, 3, 5, 6.2) – verify them, do not re-discover.

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
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_hierarchy (+qa_hierarchy2 scrolled), qa_tooltip, qa_combo, qa_matrix, qa_docview, qa_sheet, qa_inspector_fire, qa_inspector_building, qa_switches, qa_kb_templates, qa_kb_measures, qa_kb_tables, qa_kb_tables2, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_stats.json) |
| Core tests | `smoke_test.py` (18 blocks), `gesture_test.py` (19 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – sections: meta (`version` «6.1»), scenario_types (5), gs_causes (68), iz_causes (15), fire_types (8), p21, flow_titles, p13 (10), p14 (8), equipment_templates (16), property_modifiers (13, `target`: gs/iz/room/building). Backup: `knowledge_base_v5.json` (keep). This session does NOT mass-edit KB data via scripts; user edits happen through the new editable UI at runtime. If a schema change becomes unavoidable: byte-safe Python script rule below + bump meta.version to «6.2» and document it; otherwise meta.version stays «6.1». |
| App version | `eta\__init__.py` → `__version__ = "6.2.0"` – this session bumps to **6.3.0**. Status bar shows the version; gesture test asserts it (update the assertion). |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_13.md` (English) at the end |
| Normative literature (for source-number lookup ONLY) | `literature\` – `Методика_533_RAG_final.md`, `2 ГОСТ 12.1.004-91_distil.md`, `3 СП 12.13130.2009.md`, `БЗ_отказы_оборудования_и_антагонисты.md` |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` with verification (`json.loads` before/after, unique anchor line, no em-dash), delete the script afterwards. Inline `python -c` in pwsh breaks on quotes – write a file. |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE (contains an old «территория» lightning mode). Do not wire it in; leave as-is unless a task requires cleanup. |

## 2. STATE AFTER SESSION 12 (v6.2.0) – what exists, all tested

- **Paradigm** (invariant): five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree «Наличие вещества / Наличие ОК → ГС → ИЗ → Возникновение пожара/взрыва»; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5.
- **Presence** = single user-entered «Вероятность присутствия» 0–1 (`Presence.value`, `q()=clamp`; old `time`/`freq` migrate on load); node label «вероятность присутствия: 0,050»; PDF wording updated.
- **Node bodies**: «Всего: N …» (Russian plurals via `_plural`) + «ΣQ = … год⁻¹» (style `total`, mono bold F_FORMULA=12); «не задано» gray (`muted`); presence line (`meta`). Styles live in `NodeGeo.body_styles`, fonts in `layout.body_font()`, colors in `render.BODY_COLORS`.
- **Word wrap**: `layout.wrap_words()` – whole words only, node width grows to the longest word (MAX_NODE_W cap raised when needed) – no mid-word clipping anywhere.
- **Canvas** (`eta\ui\canvas.py`): LMB drag node (threshold 5 px) with persisted per-tree `node_offsets` (slots `substance|oxidizer|gs|iz|fire`, format 5 optional field, applied INSIDE `compute_layout` → canvas/PDF WYSIWYG; scene rect = union of actual rects); click-on-release selects and emits `node_clicked` → inspector; LMB-empty/middle pan; wheel = smooth zoom to cursor (gestures mixin `_init_gestures()` – pinch/tap work); «Авторазметка» button (left toolbar, glyph `auto-layout`) clears offsets of shown trees; `tree_offsets_changed` → dirty. Delete on canvas = delete owning tree (confirm seam). **Tree header** is still a `TreeHeader` block rendered above each tree (title `owner · type` + blue `Q = … год⁻¹` right-aligned) – Task 4 replaces it.
- **Modes**: sticky/free wired (`_apply_mode`), exclusive buttons, `clamp_to_mode()` public; sticky clamps to scene rect ±40. Free mode still limited by scrollbar ranges derived from sceneRect – Task 5.
- **Hierarchy** (`eta\ui\hierarchy_panel.py`): 6-button toolbar (ICON_PX_HIER 32, even spreads); sibling-add gating (`_gating_target`: scenario row/«Группа сценариев» count as owner); column-0 width = max(content, viewport) with h-scrollbar, smooth Shift+wheel (`scroll.py` animates BOTH axes, 60 px/notch); QSS `#hierTree` (hover/selected, min-height 30, indent 20, item icons 22); context menu: «Переименовать… / Удалить с поддеревом… / Свойства / Добавить дерево…▸» (Task 6 trims); Delete via tree-viewport event filter + `_delete_current` (EditingState guard; fallback `_selected`); `add_kind` re-selects the new node after rebuild.
- **Main window** (`eta\ui\main_window.py`): QSplitter hierarchy|center|inspector (320/500/360, non-collapsible, state in QSettings `ui/splitter`); `_delete_selection` priority: canvas node→owner tree / hierarchy object / single current tree; `_update_trash` (selection-based); menus Ctrl+N/O/S/E, F9, Alt+A (`act_fit` – broken on RU layout, Task 3), window-level Delete action (kept); doc pop-out (`_doc_host` hidden host, `DocumentWindow`, geometry NOT persisted – Tasks 1/11); KB window lazy singleton (geometry NOT persisted – Task 11); `migrate_qsettings` (ui/* keys).
- **Inspector** (`eta\ui\inspector_panel.py`): `_section` with +6/+4 px around HLine; building form (F_зд, «Тип (П1.3)/(П1.4)» auto-switch combo, молниезащита + категория + S/L/H), room form (площадь, аварийная вентиляция + A), area form («Выберите тип:» + value), outdoor form, territory form («Площадь ударов молнии F_тер, км²:» – Task 12), compartment form; presence form single field; cause blocks («Добавить причину…» picker, «Убрать»), pedal blocks (KB tooltips wired); commit-on-leave. **Known defect family (Task 2): form builders DISPLAY defaults via `p.get(key, default)` without WRITING them – engine reads props and sees nothing.**
- **Controls** (`eta\ui\controls.py`): `wide_combo()` – adaptive popup width clamped [button, 2×button], spacing 2, item padding via QSS; `wrap85`; `HLine`, `section_header`, `HtmlDelegate`.
- **Tooltips** (`eta\ui\modern_tooltip.py`): adaptive bubble (ideal width clamped [≈24 chars+padding, TIP_MAX_W=560]); ≤85-char lines (`wrap_tip_line`, `TIP_WRAP_CHARS=85`), whole-word wrap, syllable split with «–» (`_split_long_word`), HTML-aware wrap with tag re-opening (`_wrap_rich_line`); `ModernTooltip.apply_html`.
- **KB window** (`eta\ui\kb_window.py`): tabs «Шаблоны оборудования» / «Разновидности ГС» / «Разновидности ИЗ» / «Типы горения» / «Таблицы типовых частот» (sub-tabs П1.3/П1.4/П2.1) / «Защитные средства»; bottom bar `[Сохранить(primary)] [Закрыть]` right; `_TableTab` (editable raw tables – machine columns: Id/Название/…), `_MeasuresTab` (read-only «Наименование средства | Коэффициент | Примечание», canon notes «формула (источник) – описание», QLabel rich cells + `_apply_row_heights`), `MethodTablesTab` read-only; per-pixel scroll everywhere; dirty-guard close.
- **Scrolling**: `eta\ui\scroll.py` app filter – Shift+wheel horizontal, plain wheel animated per-pixel, both smooth; TreeCanvas/DocumentView excluded (zoom).
- **Tests/QA**: both suites green (18 + 19 blocks); QA artifacts current and vision-reviewed (session 12).

## 3. CODE MAP (extend, don't break)

- `main.py` – entry (QSS, `install_scroll_wide`, `install_modern_tooltips`, `migrate_qsettings`, `MainWindow(kb)`).
- `eta\core\model.py` – `Presence`, `GSCause`, `IZCause`, `ScenarioRow`, `CalcContext` (tgm_multiplier П1.3/П1.4, lightning_q from building props, vent_k), `TreeModel` (engine; `node_offsets`; Task 4 adds annotation state). `eta\core\kb.py` – accessors (`gs_for` gating, `iz_all`, `modifiers_for_target`, save/reload). `eta\core\objects.py` – kinds, PARENT_RULES, toolbar need-map, `DEFAULT_PROPS` (defaults NOT materialized into node props – Task 2 fixes the display path). `eta\core\serializer.py` – format 5 (objects+trees+ui; optional `node_offsets`; Task 4 adds optional per-tree annotation). `eta\core\validation.py`. `eta\core\layout.py` – `wrap_words`, `_body_spec`, `_plural`, `compute_layout` (offsets inside, union scene rect, `TreeHeader`s – Task 4 converts to annotation node), `fmt_q`. `eta\core\matrix.py`. `eta\core\formulas.py` – dead legacy (see §1).
- `eta\ui\main_window.py` – Tasks 1, 2 (commit-on-build via inspector), 3, 6 (menu/button/delete), 11. `canvas.py` – Tasks 4, 5 (annotation drag/attach; free-mode range). `render.py` – Task 4 annotation rendering (canvas+PDF shared). `docview.py`/`doc_window.py` – Tasks 1, 11. `hierarchy_panel.py` – Task 6. `inspector_panel.py` – Tasks 2, 12. `kb_window.py` – Tasks 0, 7, 8, 9, 10. `controls.py` – Task 7 shared wrap helper. `scroll.py` – verify only. `dialogs.py`. `theme.py` – new QSS/fonts as needed. `icons.py` – Task 6 new glyph («Добавить дерево»). `modern_tooltip.py` – reuse `wrap_tip_line`. `gestures.py` – don't break. `switch.py`.
- `eta\export\pdf_export.py` – Task 4: annotation on the schematic sheet; one-painter/newPage discipline.
- Tests: `smoke_test.py`, `gesture_test.py` – update/add per task list below; `visual_qa_runner.py` – add shots where valuable (annotation node on canvas + in PDF page, new KB tabs incl. editable buttons, reopened doc window, territory form with unit combo).

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py` – never fork geometry. Task 4 annotations and any geometry change go through them once.
2. No new external dependencies; PySide6-native only.
3. Style: flat Swiss-utilitarian; new visuals via `theme.py` QSS (objectName-driven), no ad-hoc colors; `outline: none` everywhere focus rectangles could appear.
4. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference renamed/changed strings or behaviors (grep the tests first); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop+2× upscale for pixel truth) the affected artifacts before declaring the task done. Animations must not break offscreen tests.
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions below are NOT to be re-asked.
7. Modal dialogs block offscreen tests: use/extend the existing testable seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_tree_delete`, patched `exec` capture) – do not break them. New confirmations (e.g. multi-delete batch) must be built as seams too.
8. Suggested implementation order (independent items first; renumber freely if dependencies demand): 1 → 2 → 3 → 5 → 12 → 11 → 6 → 7 → 8 → 9 → 10 → 4 → 0. Task 4 (reference nodes) and Task 0 (measures library) are the two largest – do them last, with tests after each sub-step.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses: «уровень полноты безопасности (SIL)», «вероятность отказа по запросу (PFD)».
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Math in labels/tooltips via the project mini-notation (`math()`, `math_html_lines`); raw HTML must be escaped (`html.escape`) – KB titles contain «< 450 м³». QTableWidgetItem cells render NO HTML (plain text only) – rich cells are QLabel cell widgets (`_MeasuresTab` pattern with `_apply_row_heights`).

---

## TASK 1. «ДОКУМЕНТ» POP-OUT WINDOW IS BLANK ON SECOND OPEN

**Defect (screenshot №1):** reopening the pop-out «Документ» window shows a completely empty window (title «ДОКУМЕНТ – ТАБЛИЦА / ЛИСТ ДЛЯ PDF – Kuji», no toolbar/table/content).

**Root cause (diagnosed):** `MainWindow._on_doc_window_closed()` does `self._doc_host.setParent(self)` and `self._doc_host.hide()`. On reopen, `open_doc_window()` creates a new `DocumentWindow(self._doc_host)` (reparenting the host into the new window) but the host itself remains HIDDEN → the window shows an empty surface. First open works because the host was never hidden.

**Requirements:** fix so reopening always shows the full document panel (matrix/schematic stack + mode caption). Either keep the host visible when reparenting (`self._doc_host.show()` on open) or stop hiding it on close. Verify no double-ownership artifacts when the window is closed and reopened repeatedly. Gesture test: open → close → reopen → `doc_stack` visible and `matrix_table.rowCount() > 0`; close/reopen cycle twice.

## TASK 2. Q = 0 ALTHOUGH «ALL PARAMETERS SET» (displayed ≠ stored)

**Defect (screenshot №2):** a ТГМ tree shows «Q = 0 год⁻¹» while the inspector displays «Площадь F_зд: 1200,0 м²» and «Тип (П1.3): Электростанции». Customer-confirmed repro: values were left at their displayed defaults → Q = 0; after touching the area (1200 → 1300) Q became non-zero.

**Root cause (diagnosed, LOCKED):** object form builders display fallback defaults (`p.get(key, default)`) WITHOUT writing them into `node.props`; the engine (`CalcContext.tgm_multiplier` etc.) reads only props → empty `p13_type`/`area_m2` → multiplier 0 → Q = 0. The combo additionally displays row 0 via `setCurrentIndex(max(0, findData(cur)))` while the property stays empty.

**Requirements:**
1. Invariant: **a value shown in a form is always stored in the object's properties.** When a form field initializes from a default (area, П1.3/П1.4 type, bln S/L/H, lightning category, vent rate, site type/value, outdoor fields, territory area), write that default into `props` at form build (and for combos, write `currentData()` of the displayed index). Keep the parent-cascade semantics of `effective_properties` intact (node-level writes behave exactly like the user typing).
2. Cover all object forms in `inspector_panel.py` (building/room/area/outdoor/territory/compartment) and the shared `_type_combo_13_14` fill.
3. Regression tests (gesture): create Т→З→П→У + ТГМ tree with causes, touch NOTHING in the forms → assert `total_q > 0` (status bar and tree annotation/formula non-zero); assert `props` contain the displayed keys right after opening each form.
4. Update QA/pixel shots if numbers change in demo projects (visual_qa_runner `build_demo` may now see materialized defaults).

## TASK 3. Alt+A («ПОКАЗАТЬ ВСЁ») DOES NOT FIRE

**Defect:** the menu action works by mouse, the Alt+A shortcut does not.

**Diagnosed likely cause:** `act_fit.setShortcut(QKeySequence("Alt+A"))` matches only the Latin «A»; on the Russian keyboard layout the same physical key produces «Ф» and Qt matches shortcuts by resulting text → no match. (Also verify the shortcut is not eaten by focused viewports – it must work with focus in the tree, canvas, inspector, KB window.)

**Requirements:**
1. Make «Показать всё» (Alt+A) layout-independent: register BOTH sequences – `Alt+A` and `Alt+Ф` – on the action (`setShortcuts([...])`), and verify via a real key simulation in tests: `QTest.keyClick(widget, Qt.Key.Key_A, Qt.KeyboardModifier.AltModifier)` (QTest sends key CODES, which are layout-independent) with focus in tree/canvas/inspector → `canvas.fit_tree` triggered (spy on the view transform or `_clamp_to_mode` calls).
2. Keep the menu entry and the left-toolbar «Показать всё» button as-is.
3. Sweep the app for other letter shortcuts with the same class of problem (currently only Alt+A) – document in the report; fix if found.

## TASK 4. REFERENCE (TITLE) NODES INSTEAD OF THE FLOATING HEADER

**Defect (screenshot №3):** the tree header text «hangs in the air» above each tree: «Участок 1 · Сценарий пожара ТГМ (твердые горючие материалы)» plus the blue «Q = 0 год⁻¹» on the right.

**LOCKED design (Q&A rounds 1–2):**
1. The floating header DISAPPEARS entirely (both the title line and the Q text). The Q value is NOT duplicated anywhere in the air – it already lives in the «Возникновение пожара» node and the status bar.
2. Instead, each tree gets ONE auto-generated **reference (title) node**: text «{owner_title} · {scenario_type_title}» (live-updates on rename/type change). ONE node per tree (not two).
3. The reference node is a first-class draggable item: LMB drag (same threshold mechanics as node drag from session 12). While dragging, when it comes near a tree node (threshold ~20–30 px), the candidate node highlights (accent outline) and a small tooltip «Привязать» appears; on release near a node the reference node MAGNETICALLY SNAPS to it (sensible offset – e.g., centered above the node) and afterwards FOLLOWS that node whenever it moves (manual drag, «Авторазметка», layout rebuilds). Dragging it away DETACHES it (free-floating position persists); it can then be re-attached to another node.
4. Default state (new tree): free-floating at the former header position above the tree.
5. Persistence (format 5, optional per-tree field, e.g. `annotation: {"attached": slot|null, "offset": [dx, dy]}` – text is auto-generated, not stored). Round-trip in tests. Tree deletion removes its annotation. «Авторазметка»: attached annotations follow their nodes to auto positions; free ones return to the default position.
6. Reference nodes render on the canvas AND in the PDF schematic sheet (WYSIWYG through `compute_layout`/`render.py` – no forked geometry). Visual style: compact, flat, clearly secondary to calculation nodes – dashed 1px border, muted fill (#F8FAFC), secondary text color, rounded corners; auto width to the title, ≤2 lines (word wrap per `wrap_words`).
7. Hover tooltip: «Справочная нода – перетащите; отпустите рядом с нодой дерева, чтобы привязать» (normative Russian, en-dash).

**Implementation pointers:** `TreeModel.annotation` (dict|None); `layout.py` computes the annotation geometry (attached → derived from the node rect + stored offset; free → default position + stored offset) and includes it in the scene union; `render.py::draw_annotation`; `canvas.py` extends the drag machinery (annotation items are draggable but not selectable-for-delete; press/move/release with the same 5 px threshold; drop decides attach/detach; commit → update `tree.annotation` → `rebuild_last()`); edges/nodes unchanged. Old `TreeHeader` machinery and its PDF call sites are replaced by the annotation. Status bar «Q_возникновение: …» per tree stays as-is.

**Tests (gesture):** annotation exists per tree with exact text; rename owner → text updates; drag onto gs node → `attached == "gs"`; drag the gs node → annotation follows (positions recomputed); drag annotation away → `attached is None`; save/load round-trip preserves annotation state; PDF schematic page contains the annotation (render assertion); «Авторазметка» resets a free annotation to default position and keeps attachments.

## TASK 5. «СВОБОДНЫЙ ОБЗОР» MUST BE TRULY UNRESTRICTED

**Defect:** free mode behaves exactly like sticky – the camera cannot leave the tree area.

**Diagnosed cause:** `_clamp_to_mode()` correctly does nothing in free mode, but the view's scrollbar RANGES are derived from the scene rect (`setSceneRect(layout.scene_rect)`) – panning is bounded by the scene rect in BOTH modes.

**Requirements:** in free mode the camera must be movable without ANY limits. Suggested approach: on switching to free, set the view's scene rect to the layout rect grown by a huge margin (e.g., ±100 000 px); on switching back to sticky, restore the layout rect and clamp. `fit_tree`, PDF export and DocumentView must keep using `layout.scene_rect` (verify export geometry is NOT affected by the enlarged view rect). Gesture test: switch free → scrollbars have huge range → pan far beyond the tree (scrollbar max) → view content moves; switch sticky → clamp returns the visible rect inside tree bounds + 40 px.

## TASK 6. CONTEXT MENU / TOOLBAR «ДОБАВИТЬ ДЕРЕВО» / DELETE SEMANTICS

**Defect (screenshot №4):** the context menu on a hierarchy item contains «Свойства» and «Добавить дерево…▸» which the customer wants gone from the menu.

**Requirements:**
1. Context menu keeps ONLY «Переименовать…» and «Удалить с поддеревом…» (same icons, default button «Удалить» – unchanged). Remove the «Свойства» and «Добавить дерево…» entries (the `props_requested` signal/wiring can go away if nothing else uses it – check and clean).
2. **New toolbar button «Добавить дерево»** in the hierarchy toolbar, positioned to the RIGHT of «Добавить наружную установку» (7 buttons total, spread recomputed; new stylized glyph in `icons.py` registered in ALL_GLYPHS + palette/neutral set; smoke icon-coverage block updated). LOCKED behavior: click opens a menu of the 5 scenario types (as the old submenu did); the button is ENABLED when the gating target is (a) an Участок or наружная установка → tree is created on it directly, or (b) a ПОМЕЩЕНИЕ → a new «Участок N» is auto-created under that room first, then the tree is created on it (status-bar notification «Создан Участок N …»; new участок gets default props per Task 2 invariant); otherwise disabled with a hint tooltip in the parenthetical style (e.g. «Добавить дерево (выделите участок, наружную установку или помещение)»).
3. **6.1 (LOCKED wording):** the disabled tooltip of «Добавить наружную установку» becomes exactly `Добавить наружную установку (выделите территорию)` – same parenthetical pattern (drop the «– выделите …» dash form). Apply the same pattern to the new button's hint.
4. **6.2 Delete semantics (LOCKED):** Delete removes ONLY what is selected (plus its descendants) – never anything above the selection.
   - BUG (customer-confirmed): with an Участок selected, ONE Delete press removes the whole branch up to the territory. Reproduce first (deep chain Т→З→П→У + siblings, QTest Delete, count survivors), find the mechanism (suspects: key auto-repeat/filter re-entry, stale `_selected` fallback in `_delete_current` firing on the parent after rebuild, or selection restore races during `_refresh`), fix, and add a regression gesture block.
   - Multi-select: support Ctrl/Shift multi-selection in the tree for deletion (verify current selection mode; set ExtendedSelection if needed): Delete with multiple selected objects opens ONE confirmation window listing all selected titles («Удалить N объектов с поддеревьями?» – built as a testable seam like `_confirm_delete`, default button «Удалить»); on confirm, delete every selected subtree (deduplicate: skip nodes that are descendants of other selected nodes), single rebuild. Deletion still removes owned trees of removed owners (existing `_on_subtree_removed` behavior).

## TASK 7. KB TABLES: HORIZONTAL SCROLLBAR + NO MID-WORD TRUNCATION (ALL TABLES)

**Defect (screenshot №5):** the «Защитные средства» table has NO horizontal scrollbar at the bottom; the right «Примечание» column is cut off mid-word; rows are clipped at the bottom.

**LOCKED scope: ALL tables of the KB window** («Защитные средства», «Таблицы типовых частот» sub-tabs, and the redesigned libraries of tasks 8–10).

**Requirements:**
1. Column widths auto-fit the widest cell content (never squeezed); when total width exceeds the viewport, the horizontal scrollbar appears (AsNeeded policy; per-pixel smooth scrolling is already installed – verify). Vertical scrolling must keep working with taller wrapped rows.
2. Cell text is limited to **85 characters per line**; longer text wraps by WHOLE WORDS; a single word longer than the line splits by SYLLABLES with the en-dash «–» (reuse the session-12 algorithm: `modern_tooltip.wrap_tip_line`/`_split_long_word` – factor a shared helper into `controls.py` and use it from both places; do not duplicate the splitter).
3. Row heights adjust to wrapped content (`_apply_row_heights` pattern for QLabel cells).
4. Nothing is ever cut mid-word or mid-row; QA shots `qa_kb_measures` + new tab shots must show the scrollbar and wrapped cells.

## TASK 8. TAB «ТИПЫ ГОРЕНИЯ» → «ТАБЛИЦА ТИПОВЫХ РЕЖИМОВ ПОЖАРА» (READ-ONLY)

**Defect (screenshot №6):** the current table is machine-oriented (columns «Id | Название | Типы сценариев | Колонка П2.1 | P | Q (огненный шар) | Среды», raw codes `None`, `instant|delayed`, `2.5e-05`).

**LOCKED design (reference table, READ-ONLY):**
1. Rename the tab to **«Таблица типовых режимов пожара»** (update any caption inside the tab accordingly, e.g. «ТИПОВЫЕ РЕЖИМЫ ПОЖАРА (прил. № 2, табл. П2.1)» – find the exact current strings in `kb_window.py`).
2. Columns exactly: **«Режим пожара | Базовая частота | Примечание»**. Content per row:
   - «Пожар по поверхности»: базовая частота `a₁·F (табл. П1.3/П1.4)`; примечание explains it is the ТГМ multiplier from the building/installation properties.
   - «Факельное горение», «Пожар-вспышка», «Пролив», «Сгорание (взрыв) ТВС», dust дефлаграция/детонация: базовая частота `по табл. П2.1 (по расходу и среде)`; примечание explains the conditional probability is selected by mass flow (<1 / 1–50 / >50 кг/с / полный разрыв) and medium (газ / двухфазная / жидкость) per прил. № 2 к Приказу МЧС России № 533, табл. П2.1 – take exact wording from KB sources / `literature\`, do not invent numbers.
   - «Огненный шар (диффузионное горение)»: базовая частота `2,5·10⁻⁵ год⁻¹`; примечание: частота внешнего воздействия на аппарат (Приказ МЧС России № 533, прил. № 1, п. 5).
3. Numbers in engineering format (comma decimal, Unicode superscripts – «2,5·10⁻⁵», never `2.5e-05`). Formula cells render with REAL sub/superscripts via the mini-notation in QLabel rich cells (QTableWidgetItem renders no HTML – pitfall).
4. Table obeys Task 7 (auto-width columns, h-scrollbar, ≤85-char word/syllable wrap). Read-only – no add/delete buttons.

## TASK 9. TAB «РАЗНОВИДНОСТИ ИЗ» → «ИСТОЧНИКИ ЗАЖИГАНИЯ (ИЗ)» – EDITABLE LIBRARY

**Defect (screenshot №7):** machine columns «Id | Название | λ, год⁻¹ | Режим (lightning) | P | Источник», mostly empty columns, scientific notation `2.2e-06`, truncated «Источник» column, no h-scrollbar.

**LOCKED design:**
1. Tab renamed to **«Источники зажигания (ИЗ)»**; the section caption «РАЗНОВИДНОСТИ ПРИЧИН ИЗ (ГОСТ 12.1.004-91, табл. 9)» becomes **«БИБЛИОТЕКА ПРИЧИН ПОЯВЛЕНИЯ ИСТОЧНИКОВ ЗАЖИГАНИЯ (ИЗ)»**.
2. Columns exactly: **«Наименование ИЗ | λ, год⁻¹ | Примечание»** (sources live inside «Примечание»). λ in engineering format («3,2·10⁻⁵»). Special rows: «Удар молнии» → λ = `расчётная величина` + примечание «рассчитывается по свойствам здания/установки: N_у.м·(1 − η_МЗ)» with its normative sources; rows with direct probability P (нагретые вещества) → λ column shows `P = 1 (вероятность)` (generalize: `P = <value> (вероятность)`).
3. **Editable library**: title, λ (numeric), примечание (plain mini-notation text; render rich via QLabel; edit via double-click opening a small multi-line editor dialog with a live preview – engineer's choice within the existing patterns). New records: «Добавить запись» and «Удалить запись» buttons at the BOTTOM-LEFT (opposite side from «Сохранить»/«Закрыть», which stay bottom-right). LOCKED field set for a new record: only the 3 visible fields (наименование, λ, примечание); everything else generated automatically (id `iz-<uuid8>`, `lam` numeric, defaults for mode/electrical). No extra fields in the table.
4. Deleting a record that is referenced by trees of the open project: allow it, but the confirmation (seam) warns how many trees use it («используется в N деревьях – ссылки будут потеряны»); removed refs degrade gracefully (existing fallback behavior – verify).
5. Changes persist through the existing «Сохранить» flow (`kb.save()`); reload («Закрыть» with dirty guard) unchanged. Task 7 rules apply. KB `meta.version` unchanged (schema untouched; user edits are runtime data).

## TASK 10. TAB «РАЗНОВИДНОСТИ ГС» → «ГОРЮЧИЕ СРЕДЫ (ГС)» – EDITABLE LIBRARY

Same treatment as Task 9, by analogy (LOCKED):
1. Tab renamed to **«Горючие среды (ГС)»**; caption «РАЗНОВИДНОСТИ ПРИЧИН ГС (П1.1/П1.2/поверхность)» becomes **«БИБЛИОТЕКА ПРИЧИН ВОЗНИКНОВЕНИЯ ГОРЮЧИХ СРЕД (ГС)»**.
2. Columns exactly: **«Наименование ГС | Частота, год⁻¹ | Примечание»**. Content: П1.1 rows → «4,6·10⁻³ год⁻¹» (engineering format); П1.2 pipeline rows → «2,8·10⁻⁶ м⁻¹·год⁻¹ × L» + примечание «L – длина прокладки, м; задается на ноде ГС (или в свойствах участка)»; «Поверхность (ТГМ)» → `a₁·F (табл. П1.3/П1.4)` + примечание.
3. Editable with the same «Добавить запись»/«Удалить запись» bottom-left buttons; new record = 3 visible fields only (наименование, частота год⁻¹, примечание); auto: id `gs-<uuid8>`, kind `p11`, sensible defaults for `applies`/`site_kinds` so the record appears in the cause pickers for the release scenario types (document the chosen defaults in the report); deletion warning for referenced records as in Task 9.
4. Task 7 rules apply (auto-width, h-scrollbar, ≤85-char word/syllable wrap, formula rendering with real sub/superscripts).

## TASK 11. UI MEMORY FOR ALL WINDOWS

**Requirement:** if the user moved/resized any window and closed the app, everything must reopen the way it was left. Everywhere.

1. Main window geometry + splitter state already persist (`ui/geometry`, `ui/splitter`) – keep.
2. **KB window**: save geometry on close → restore on (re)creation (`ui/kb_geometry`). The window is a lazy singleton in `MainWindow` – restore at creation time.
3. **«Документ» pop-out**: save its geometry on close → restore on open (`ui/doc_geometry`). LOCKED: no auto-reopen at launch – only size/position are remembered; the user opens it manually.
4. Verify restore works when a saved monitor is absent (Qt ignores off-screen geometry gracefully – test by saving with a shifted position and reopening; no crash, window visible).
5. Tests: hermetic QSettings (existing pattern); gesture blocks: resize doc window → close → reopen → size preserved; same for KB window; main window state unchanged.

## TASK 12. TERRITORY AREA FIELD: «ПЛОЩАДЬ ТЕРРИТОРИИ» + UNIT SWITCH км² | м²

**Defect (screenshot №8):** the territory form shows «Площадь ударов молнии F_тер, км²:» = 0,050000 (red arrow markup). The field is informative-only in the current engine (lightning is computed from building/installation properties; `formulas.py` territory mode is dead code – do not wire it).

**LOCKED design:**
1. Rename the label to **«Площадь территории:»**.
2. Add a compact unit combo next to the value: **«км² | м²»** (LOCKED: combo next to the spin). The stored value stays normalized in км² (`strike_area_km2`); the chosen unit is stored in the object props (e.g. `strike_area_unit`: `"km2"|"m2"`, default `"km2"`) and persists in the project file. Switching units converts the displayed value (м² = км²×10⁶) with sensible decimals/suffix (« км²»/« м²»).
3. Tooltip (normative Russian, en-dash): the field is informative; the lightning frequency is calculated from the building/installation dimensions (S/L/H or area) and protection category.
4. Task 2 invariant applies here too: the displayed default (0,05 км²) is committed to props when the form is built.
5. Tests: gesture – open territory form, switch to м², value converts; type a value in м², reopen form – unit and converted value persist; round-trip through save/load.

---

## 6. LOCKED DECISIONS (Q&A rounds before this session – normative, not to re-ask)

1. (Task 4) The floating tree header disappears; each tree gets ONE auto-generated reference node with the title text only; NO Q text node (Q lives in the «Возникновение» node and status bar).
2. (Task 4) Reference nodes: LMB-draggable; magnetic snap to nodes with «Привязать» hint; follow the attached node; detach by dragging away; persist attachment/offset in the project; render in canvas AND PDF.
3. (Task 6) «Добавить дерево» toolbar button right of «Добавить наружную установку»: opens the 5-type menu; enabled on Участок/наружная установка directly and on ПОМЕЩЕНИЕ with auto-creation of a new Участок first.
4. (Task 6.1) Exact wording: `Добавить наружную установку (выделите территорию)`.
5. (Task 6.2) Customer-confirmed bug: one Delete on an Участок removes the branch up to the territory; fix = only the selection (+descendants) dies; multi-select deletes via ONE confirmation window listing the batch.
6. (Tasks 8/9/10) Exact new tab names/captions/columns as written in the tasks; «Таблица типовых режимов пожара» is read-only; IZ and GS libraries are editable with «Добавить запись»/«Удалить запись» bottom-left; new records fill only the 3 visible fields, the rest is auto-generated; existing records are fully editable (approved for measures too).
7. (Task 0) «Защитные средства» gets the FULL redesign into an editable library THIS session (not deferred): editable fields = наименование, коэффициент/формула (mini-notation), примечание с источником, носитель (ГС-нода/ИЗ-нода/помещение/здание); pedal key and the rest auto-generated; a new measure works as a switch on its target node with a universal multiplier k (numeric); existing 13 records become editable with the same field set.
8. (Task 11) Windows remember size/position; «Документ» does NOT auto-reopen at launch.
9. (Task 12) «Площадь территории» + км²|м² combo; value normalized/stored in км²; unit persisted per object; informative only – engine untouched.
10. (Task 7) Scrollbars + ≤85-char word/syllable wrapping apply to ALL KB tables.
11. (Task 2) Root cause confirmed by the customer (defaults displayed but not stored; touching 1200→1300 fixed Q) – the «displayed = stored» invariant is normative.

## 7. FINAL DELIVERABLES

1. Questions asked per task BEFORE its implementation where genuinely ambiguous (§0); locked decisions not re-asked.
2. All thirteen tasks (0–12) implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated for renamed strings/behaviors; new blocks: doc reopen cycle, defaults-committed Q>0, Alt+A both layouts, annotation node lifecycle + persistence + PDF, free-mode unbounded range, context menu trimmed + «Добавить дерево» button incl. room→auto-участок, delete only-selection + multi-batch seam, KB tables h-scroll/wrap, renamed KB tabs + editable add/delete round-trips, window memory, territory unit switch); `run_qa.cmd` regenerated and vision-reviewed (annotation node on canvas + PDF, new KB tabs incl. bottom-left buttons and scrollbar, reopened doc window, territory form).
3. Version → **6.3.0** (KB `meta.version` stays «6.1» unless a schema change was truly needed – then 6.2 + documented); README updated where behavior is user-visible (reference nodes, editable KB libraries, renamed tabs, window memory, territory units, delete semantics, Alt+A).
4. `old prompts (done prompts)\REPORT_SESSION_13.md` (English): per-task summary, files touched, root causes with the exact fix for tasks 1/2/3/5/6.2, before→after strings for every changed user-facing label/tooltip/tab caption/column header, test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only (§1); never pwsh string cmdlets; delete scripts after use; no em-dash anywhere.
- Modal dialogs block offscreen tests (`QMessageBox.exec`, `QDialog.exec`): use the seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_tree_delete`, patched `exec` capture) – extend, don't break. New confirmations (multi-delete) must be seams too.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: app-level filters/animations keep strong module-level refs (`scroll.py::_ACTIVE_FILTER`, tooltip `_ACTIVE`, the `_smooth` dict); toolbar buttons use `NoFocus`.
- Delete delivery: item views hold focus in their VIEWPORT and `QTreeWidget` claims Delete via ShortcutOverride – the working mechanism is the viewport event filter (`hierarchy_panel.py`, `canvas.py`, session 12). The inline rename editor still owns Delete while editing (verified). Do not regress.
- `add_kind` must re-select the new node after rebuild (session-12 fix) – Delete right after adding must work.
- Letter shortcuts are layout-dependent on Windows: register Latin+Cyrillic twins (Task 3); QTest keyClick sends key CODES (layout-independent) – use it for shortcut tests.
- Synthetic mouse: use `QTest.mousePress/mouseMove/mouseRelease` with explicit positions; inline-constructed `QMouseEvent` sent via `sendEvent` can die inside filter chains (AttributeError wrapped as nested «Internal C++ object» errors) – do not reintroduce.
- Canvas gestures mixin (`gestures.py`) is initialized in `TreeCanvas._init_gestures()` – integrate new mouse handling through/around it, don't break pinch/tap/СКМ-pan.
- `node_offsets` slots are `substance|oxidizer|gs|iz|fire` (real node ids); offsets apply inside `compute_layout` (WYSIWYG canvas/PDF); scene rect is the union of actual rects.
- QTableWidgetItem cells render NO HTML (plain text only) – rich cells are QLabel cell widgets with `_apply_row_heights`; math via mini-notation (`math()`/`math_html_lines`), escape raw HTML (KB titles contain «< 450 м³»).
- QLabel has no `setTextWidth` (that is QTextDocument) – use `setFixedWidth` or explicit `<br>`.
- Wrapping ≤85 chars: whole words; syllable split with «–» only for single overlong words; the shared helper lives once (factor from `modern_tooltip.wrap_tip_line` into `controls.py`).
- `QPdfWriter`: one QPainter per document, new pages ONLY via `newPage()`; PDF export uses `layout.scene_rect` – do not let the free-mode enlarged VIEW scene rect leak into exports.
- Offscreen QA: `QT_QPA_FONTDIR=C:\Windows\Fonts` mandatory; `FT_New_Face failed…` and «plugin does not support raise()/propagateSizeHints()» are harmless stderr noise; long runs as background jobs with `python -u`; never leave a modal open in a test.
- QSS `outline: none` everywhere needed (tabs, lists, tables, tree) – the customer rejects dotted focus rectangles anywhere.
- WYSIWYG invariant: canvas and PDF both consume `compute_layout` + `render.py` – every geometry change (annotations!) goes through them once.
- Vision QA reads downscaled images – crop and 2× upscale before asking glm-5.3-flash about pixel truth; programmatic checks beat vision estimates (a session-12 «>100-char lines» claim was refuted by unit assertions).
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
