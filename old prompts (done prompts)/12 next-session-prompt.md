# PROMPT: Kuji – Session 12. Interaction regressions + hierarchy/canvas/node design polish: sibling-add, Delete/drag/pan/sticky-free restoration, splitters, combo popups, informative tooltips, adaptive tooltips, node-body redesign, word-wrap, presence-as-probability

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–11 are done (v6.1.0: five-type paradigm, KB v6.1, per-pixel smooth scrolling, KB sub-tabs, canon-rewritten «Защитные средства»). Read before starting: `old prompts (done prompts)\REPORT_SESSION_11.md` and `REPORT_SESSION_10.md`. Everything described there works and is covered by tests – do not break it without need. Session 12 is a **regression-fix + design-polish session**: fifteen tasks. Several are interaction regressions introduced during the session-10 UI rewrite – their root causes are already diagnosed (see tasks 10–12) and restated below; verify them, do not re-discover. Precise decisions for every task were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them.

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
| Entry point | `main.py`; launcher `run_app.cmd` |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_matrix, qa_docview, qa_sheet, qa_inspector_fire, qa_inspector_building, qa_switches, qa_kb_templates, qa_kb_measures, qa_kb_tables, qa_kb_tables2, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_stats.json) |
| Core tests | `smoke_test.py` (18 blocks), `gesture_test.py` (13 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – sections: meta (`version` «6.1» – NOT changed this session), scenario_types (5), gs_causes (68), iz_causes (15), fire_types (8), p21, flow_titles, p13 (10), p14 (8), equipment_templates (16), property_modifiers (13, each with `target`: gs/iz/room/building, texts rewritten per the session-11 canon). Old-format backup: `knowledge_base_v5.json` (keep). |
| App version | `eta\__init__.py` → `__version__ = "6.1.0"` – this session bumps to **6.2.0**. KB `meta.version` stays **«6.1»** (no KB data edits planned this session). Status bar shows the version. |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_12.md` (English) at the end |
| Normative literature (in-project, for source-number lookup ONLY) | `literature\` – `Методика_533_RAG_final.md`, `2 ГОСТ 12.1.004-91_distil.md`, `3 СП 12.13130.2009.md`, `БЗ_отказы_оборудования_и_антагонисты.md` |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` with verification (`json.loads` before and after, unique anchor line, no em-dash), delete the script afterwards. Inline `python -c` in pwsh also breaks on quotes – write a file. (This session should not need KB edits at all; tooltips in Task 7 are UI code, not KB data.) |

## 2. STATE AFTER SESSION 11 (v6.1.0) – what exists, all tested

- **Paradigm** (session 10, invariant): five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree «Наличие вещества / Наличие ОК → ГС → ИЗ → Возникновение пожара/взрыва»; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; scenarios enumerated combinatorically; format 5 clean break.
- **Scrolling**: app-wide `ScrollWideFilter` (`eta\ui\scroll.py`) – Shift+wheel horizontal, plain wheel animated per-pixel (`ScrollPerPixel` everywhere incl. KB tables, matrix, hierarchy tree, cause picker, combo popups; `SMOOTH_MS = 150`, `SMOOTH_NOTCH_PX = 60`, OutCubic, retargetable). Scroll position preserved on table reloads. TreeCanvas/DocumentView excluded (they zoom).
- **KB window** (`eta\ui\kb_window.py`): templates tab (search + cards with `selected` highlight + `scroll_to_selected()` + details pane with HTML-escaped rich text), editable `_TableTab`s, read-only `_MeasuresTab` (canon notes «формула (источник) – описание», plain-text coefficient column), `MethodTablesTab` with three sub-tabs П1.3/П1.4/П2.1; bottom bar «Сохранить» (primary) + «Закрыть» right.
- **Inspector** (`eta\ui\inspector_panel.py`): section blocks (`_section` from `eta\ui\controls.py` – HLine + caption + spacing), switches (`ToggleSwitch`), single «Тип (П1.3)/(П1.4)» combo auto-switching at F > 10 000 м², «Молниезащита» switch gating «Категория защиты» + габариты S/L/H; room «СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ» (Аварийная вентиляция + A-поле); commit-on-leave; math labels via mini-notation `math()`.
- **Presence nodes** (task 15 target): `eta\core\model.py::Presence` has modes `time` (доля года 0–1, q = value) and `freq` (интенсивность год⁻¹, q = 1−e^(−f)); node body label rendered in `eta\core\layout.py::display_lines` (lines ~163–167: `f"время присутствия: {value}"` – printed in BOTH modes, no unit); inspector combo in `inspector_panel.py` lines ~417–433; PDF export wording in `eta\export\pdf_export.py` lines ~204, 239–241 (`MODE_RU`).
- **Hierarchy** (`eta\ui\hierarchy_panel.py`): 6-button toolbar spread evenly (BTN 44, ICON_PX_HIER 28), «Группа сценариев» under each Участок/установка, selection survives rebuild, ElideNone + `ScrollBarAsNeeded` (but NO horizontal scrollbar ever appears – see Task 8), toolbar gating per parent rules (`add_kind`, tooltips «… – выделите {need}» line ~104), context menu rename/delete («Удалить» default), F2/double-click rename.
- **Left viewport toolbar** (`eta\ui\left_toolbar.py`): doc-window trigger, zoom ±, fit, sticky/free checkable pair (`mode_requested` signal – currently NOT connected anywhere: Task 12), trash button (`set_trash_enabled` exists but is NEVER called: Task 10), `set_mode(STICKY)` at construction.
- **Canvas** (`eta\ui\canvas.py` + `render.py` + `gestures.py`): sticky/free camera clamp (`set_mode`/`_clamp_to_mode`), wheel zoom, `mousePressEvent` click-select only (no node drag, no LMB pan – Task 11), NodeItem/EdgeItem/HeaderItem built from `compute_layout` (`eta\core\layout.py` – WYSIWYG shared with PDF via `render.py`).
- **Main window** (`eta\ui\main_window.py`): fixed 3-column layout via `_panel()` QHBoxLayout (hierarchy 320 / center 500 / inspector 360 – NOT resizable: Task 9), `_wire()` connects hierarchy/canvas/inspector/left-toolbar signals (but NOT `mode_requested`: Task 12), `act_del` QAction «Удалить выделенное» with `QKeySequence("Delete")` added via `self.addAction` (window-level only: Task 10), `_delete_selection()` deletes hierarchy object or current tree (with `_confirm_tree_delete`), `_update_kb_apply_hint`, status bar ΣQ per tree.
- **Controls** (`eta\ui\controls.py`): `wide_combo()` (popup min-width = 2× button, word-wrap items, spacing 4 – Tasks 5/6), `wrap85`, `HLine`, `section_header`, `HtmlDelegate`.
- **Theme** (`eta\ui\theme.py`): Swiss-utilitarian QSS (objectName-driven); `QFrame#kbCard` states, `QTabWidget#kbSubTabs`, `QLabel#targetBadge`, `outline: none` everywhere, splitter-handle styles ALREADY present (Task 9 will use them).
- **Tests/QA**: both suites green (18 + 13 blocks); QA artifacts current and vision-reviewed.

## 3. CODE MAP (extend, don't break)

- `main.py` – entry (QSS, `install_scroll_wide`, `install_modern_tooltips`, `migrate_qsettings`, `MainWindow(kb)`).
- `eta\core\model.py` – `Presence` (Task 15: simplify to probability), `GSCause`, `IZCause`, `ScenarioRow`, `CalcContext`, `TreeModel` (engine; add per-tree `node_offsets` in Task 11).
- `eta\core\kb.py` – KB accessors; `eta\core\objects.py` – kinds + PARENT_RULES + toolbar need-map (Task 4 touches `hierarchy_panel` gating + `objects.py` hint strings); `eta\core\serializer.py` – format 5 (Task 11 adds optional `node_offsets`; Task 15 migrates old presence modes on load); `eta\core\validation.py`; `eta\core\layout.py` – 5-node layout + `display_lines` + node sizing (Tasks 13/14/15: body redesign, word-wrap, presence label; Task 11: apply `node_offsets` INSIDE `compute_layout` so canvas and PDF stay WYSIWYG); `eta\core\matrix.py`.
- `eta\ui\main_window.py` – Tasks 9/10/12 (splitters, Delete wiring, mode wiring); `canvas.py` – Task 11 (drag/pan); `render.py` – Tasks 13/14; `docview.py`/`doc_window.py` – untouched; `hierarchy_panel.py` – Tasks 1/4/8/10; `inspector_panel.py` – Tasks 2/7/7.1/15; `kb_window.py` – untouched this session (unless combo tasks touch shared `controls.py`); `controls.py` – Tasks 5/6 (`wide_combo`); `scroll.py` – verify only; `dialogs.py`; `theme.py` – new QSS; `icons.py` – Task 11 auto-layout glyph; `modern_tooltip.py` – Task 3; `gestures.py` – must survive Task 11.
- `eta\export\pdf_export.py` – Task 15 wording; keep one-painter/newPage discipline.
- Tests: `smoke_test.py` (18 blocks), `gesture_test.py` (13 blocks) – update/add per task list below; `visual_qa_runner.py` – add shots where valuable.

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py` – never fork geometry. Task 11 offsets and Tasks 13/14 body changes MUST go through `compute_layout`/`layout.py` so screen and PDF stay WYSIWYG.
2. No new external dependencies; PySide6-native only.
3. Style: flat Swiss-utilitarian; new visuals via `theme.py` QSS (objectName-driven), no ad-hoc colors; `outline: none` everywhere focus rectangles could appear.
4. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference renamed/changed strings or behaviors (grep the tests first); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop+2× upscale for pixel truth) the affected artifacts before declaring the task done. Animations must not break offscreen tests.
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions below are NOT to be re-asked.
7. Modal dialogs block offscreen tests: use/extend the existing testable seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_tree_delete`, patched `exec` capture) – do not break them.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses: «уровень полноты безопасности (SIL)», «вероятность отказа по запросу (PFD)».
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Math in labels/tooltips via the project mini-notation (`math()`, `math_html_lines`); raw HTML must be escaped (`html.escape`) – KB titles contain «< 450 м³».

---

## TASK 1. HIERARCHY PANEL: NAMES TRUNCATED AGAIN + PROPER UI/UX DESIGN

**Defect (screenshot 1):** item names in the object tree are clipped at the panel edge again (e.g. «Одностенный изотермический резерв…» cut mid-word with no ellipsis; the inline rename editor is equally clipped). Related: Task 8 (no horizontal scrollbar).

**Requirements:**
1. No name ever clipped: full text available via the horizontal scrollbar from Task 8; inline rename editor width follows the column width.
2. Design pass over the tree (LOCKED: bigger colored glyphs + clearer level indentation; the rest at your discretion within the flat Swiss style): increase hierarchy glyphs (ICON_PX_HIER 28 → ~32), increase level indentation (e.g. `setIndentation(20)`), comfortable row height (~30 px), subtle hover background and selected state via QSS in `theme.py` (objectName-driven, no ad-hoc colors), consistent 8 px grid paddings. Keep the 6-button toolbar layout and all behaviors intact.
3. Vision-verify on a regenerated `qa_window.png` (and, if useful, a dedicated hierarchy grab with long names).

## TASK 2. INSPECTOR SECTION SEPARATORS: A LITTLE MORE BREATHING ROOM

**Defect (screenshot 2):** sections like «ПЛОЩАДЬ» / «СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ» sit too tight around their HLine separators.

**Requirement (LOCKED):** increase the vertical spacing before and after each section separator line by a SMALL amount («совсем чуть-чуть» – ~4–6 px total per side). The `_section` builder lives in `eta\ui\controls.py` (HLine + caption + spacing) and is used by `inspector_panel.py`. Keep everything else identical; update `qa_inspector_building.png` vision check.

## TASK 3. TOOLTIP («СНОСКА») SIZE MUST ADAPT TO ITS TEXT

**Defect (screenshot 3):** the dark modern tooltip (e.g. «Добавить участок – выделите помещение» on a disabled toolbar button) renders as a wide bubble with lots of empty space when the text is short.

**Requirements (LOCKED):**
1. The tooltip bubble width adapts to the text: no excessive empty space for short texts; a sensible minimum (≈ padding + ~24 chars) so one-word tips don't look like slivers.
2. Maximum line length **85 characters**; longer texts wrap.
3. Wrapping is strictly by WHOLE WORDS; if a single word is longer than the line, split it by SYLLABLES inserting the en-dash «–» at the break (simple Russian-friendly syllable splitter; no hyphenation library).
4. Implement in `eta\ui\modern_tooltip.py` (size computation + text layout); applies app-wide to all modern tooltips. Vision-verify on a crop: short tooltip = compact bubble; long tooltip = wrapped at ≤85 chars.

## TASK 4. TOOLBAR: ADDING A SIBLING WHEN A CHILD IS SELECTED

**Defect (screenshot 4):** with an «Участок» selected, the button «Добавить участок» is disabled; the user must re-select the parent room first.

**Locked rule (Q&A):** the button «Добавить X» is ENABLED when the selected node is (a) an X itself – then a SIBLING X is created under the SAME parent as the current X, or (b) a valid parent of X – then a CHILD is created as before. A selected «Группа сценариев» or a scenario row inside a tree counts as selecting its owner Участок/установка. Applies by analogy: Помещение (selected room → sibling room in the same building/compartment; selected building/compartment → child room), Здание (selected building → sibling in the same territory; selected territory → child), Участок (as above). «Наружная установка» and «Территория» keep their current rules (installation only into territory when territory selected; territory always). Update the toolbar gating logic in `hierarchy_panel.py` (and the tooltip texts «… – выделите {need}» where the semantics change), keep `PARENT_RULES` in `objects.py` consistent, extend gesture tests: select Участок → «Добавить участок» enabled → click → new sibling under the same room.

## TASK 5. COMBO POPUP ITEMS: VERTICAL HIT AREA TOO SMALL

**Defect (screenshot 5 = «Категория защиты» popup «Уровень I · η = 0,98 … IV»):** the popup items are short lines separated by large dead gaps – the user misses with the mouse; the gaps are not clickable.

**Requirements (LOCKED):** increase the clickable vertical bounds of popup items and leave only a small gap between them: item vertical padding up (~6–8 px), `QListView` `setSpacing` down (4 → ~2), so nearly the whole popup height is clickable. Implement in `wide_combo()` (`eta\ui\controls.py`) + QSS for the popup items in `theme.py`. Applies to all `wide_combo` popups app-wide.

## TASK 6. COMBO POPUP WIDTH: ADAPTIVE, CLAMPED TO BUTTON WIDTH…2× BUTTON WIDTH

**Defect (screenshot 6 = «Выберите тип:» popup «участок (м²) / линейный объект (м) / аппарат/установка (м³)»):** the popup is far wider than its short content.

**Locked rule (Q&A):** popup width = adaptive to content, but never LESS than the button width and never MORE than 2× the button width. Whatever does not fit on one line wraps by whole words (existing word-wrap behavior stays). Implement in `_patched_show_popup`/`_on_shown` in `wide_combo()` (`eta\ui\controls.py`): compute the widest item's width (sizeHint), clamp to [button width, 2× button width]. Applies to ALL combos in the app (the long-item П1.3/П1.4 type combos will wrap – that is accepted).

## TASK 7 (+7.1). INFORMATIVE TOOLTIPS FOR «Аварийная вентиляция» AND «Молниезащита»

**Defect (screenshots 7/8):** the toggle rows currently show tooltips that merely repeat the row label («Аварийная вентиляция», «Молниезащита») – useless.

**Locked decision (Q&A):** variant (b) – replace with short informative tooltips: what happens when the switch is ON and how it participates in the frequency calculation. Normative Russian, 1–2 sentences, en-dash, no «;», math via the mini-notation rendered as rich text. Drafts (adapt phrasing if needed, keep the substance and references):
- «Аварийная вентиляция»: `При включении аварийной вентиляции условная вероятность сохранения взрывоопасной концентрации снижается до P_ост = 1/(A·T + 1). Делитель массы – по ГОСТ Р 12.3.047-98, прил. А, п. А.2.5.`
- «Молниезащита»: `При включении молниезащиты частота поражения здания молнией умножается на (1 − η_МЗ). Надежность защиты по категориям I–IV – 0,98, 0,95, 0,90, 0,80 (СО 153-34.21.122-2003, табл. 2.2).`
Locate where the duplicate-label tooltips come from (likely a default `setToolTip(text)` on `ToggleSwitch` or in the building/room form builders in `inspector_panel.py`); ensure OTHER toggle rows don't regress – any row whose tooltip would just duplicate its label gets NO tooltip instead of a redundant one.

## TASK 8. HIERARCHY: HORIZONTAL SCROLLBAR (SMOOTH, SHIFT+WHEEL)

**Defect (screenshot 9):** long tree names are hard-clipped at the panel edge; there is NO horizontal scrollbar at the bottom of the tree.

**Root cause (verified):** `QTreeWidget` with hidden header keeps column 0 width = viewport width regardless of content – the scrollbar policy is `ScrollBarAsNeeded` but the range never becomes non-zero, so nothing scrolls and ElideNone clips text mid-word.

**Requirements:**
1. After every rebuild/expansion/rename, set column 0 width to max(content width, viewport width) so the horizontal scrollbar engages exactly when content is wider than the panel. Content width via `QFontMetrics` of the tree font over the widest item text + indentation + icon column.
2. The scrollbar must scroll SMOOTHLY per-pixel (session-11 `ScrollPerPixel` is already set on this tree – verify) and be driven by **Shift+mouse wheel when the cursor is over the hierarchy panel** – the app-wide `ScrollWideFilter` in `eta\ui\scroll.py` already implements exactly this for any `QAbstractScrollArea` under the cursor; do NOT add a second mechanism, just make the scrollbar exist. Verify with a gesture-test block: long name → `horizontalScrollBar().maximum() > 0` → Shift+wheel event on the tree viewport changes the value through intermediate pixels.

## TASK 9. RESIZABLE PANEL BOUNDARIES (SPLITTERS)

**Defect (screenshot 10 area):** the three main panels (hierarchy / canvas+document / inspector) have fixed widths – the user cannot drag the boundaries.

**Requirements:**
1. Replace the fixed `_panel()` QHBoxLayout in `main_window.py` with a horizontal `QSplitter`: hierarchy | center | inspector. Keep the current minimum widths (320 / 500 / 360) as `setMinimumWidth`/`setCollapsible(false)`; initial sizes = current defaults; stretch: center 1, sides 0.
2. QSS for `QSplitter::handle` already exists in `theme.py` (6 px, hover) – verify it looks right and the handles are comfortably grabbable (~6–8 px).
3. Persist splitter sizes in QSettings (the app already saves/restores UI state – extend; hermetic QSettings in tests, see pitfalls). Restore on startup when `restore_ui` is true.
4. The pop-out «Документ» window and all resize behaviors must keep working; `qa_window.png` vision check.

## TASK 10. DELETE KEY + «УДАЛИТЬ ВЫДЕЛЕННОЕ» BUTTON RESTORED

**Defect (user report):** the Delete key stopped working on the canvas and in the hierarchy window; the left-toolbar trash button «Удалить выделенное» is permanently grayed out.

**Root causes (verified in code):**
1. `left_toolbar.py::set_trash_enabled()` is never called from anywhere – the button is disabled at construction and stays so forever.
2. `main_window.py` adds `act_del` («Удалить выделенное», `QKeySequence("Delete")`) via `self.addAction(act_del)` – a window-level action whose shortcut does not fire when focus sits inside the tree/editor widgets that consume/steal it; there is no shortcut registered on the hierarchy tree or the canvas viewport.

**Requirements:**
1. Delete works when focus/selection is in the hierarchy tree: register a `QShortcut(QKeySequence.Delete)` with `Qt.ShortcutContext.WidgetShortcut` on the tree (WidgetShortcut so the inline rename editor keeps Delete for text editing – verify: while renaming, Delete edits text and does NOT delete the object).
2. Delete works when a canvas node is selected (LOCKED decision Q&A #5: variant (a) – deleting from the canvas deletes the OWNING TREE of the selected node via the existing `_confirm_tree_delete` confirmation; individual nodes of the fixed 5-node tree are never deletable).
3. Trash button `setEnabled` follows the current selection state: enabled when the hierarchy selection is a deletable object (not the territory root) OR a canvas node/tree is selected; disabled otherwise. Wire `set_trash_enabled` into the existing selection-change paths (`_on_object_selected`, `_on_canvas_node`, `_on_scenario_selected`, refresh).
4. `_delete_selection()` already implements object-delete / tree-delete with confirmations – reuse it, do not fork logic. Extend gesture tests: tree selection + Delete → object deleted (via the seam); canvas node selected + Delete → confirmation seam returns «Удалить» → tree removed; trash button enable/disable transitions.

## TASK 11. CANVAS: NODE DRAG (LMB) + CAMERA PAN RESTORED + AUTO-LAYOUT BUTTON

**Defect (user report):** nodes cannot be freely dragged with LMB anymore, and camera panning seems gone (was present in earlier sessions; dropped in the session-10 canvas rewrite which kept only click-select).

**Locked scheme (Q&A #4):**
1. LMB drag on a node moves the node; LMB drag on empty space pans the camera; middle-button drag also pans; wheel = zoom to cursor (existing); touch gestures (`gestures.py` mixin) keep working.
2. Dragged positions PERSIST in the project file: extend format 5 serialization with an OPTIONAL per-tree dict `node_offsets: {node_slot: [dx, dy]}` (offsets RELATIVE to the automatic layout position; slot keys reuse the existing per-tree node ids: `presence1`, `presence2`, `gs`, `iz`, `fire`). Keep `FORMAT_VERSION = 5` (the field is optional: absent = auto layout; old files load unchanged; new files without manual drags simply omit it). Round-trip in tests.
3. Apply offsets INSIDE `compute_layout` (canvas + PDF share it – WYSIWYG invariant; the PDF schematic sheet must show dragged positions).
4. **Auto-layout button:** return a working «Авторазметка» action that clears `node_offsets` of the current tree(s) and re-runs the layout. Place a button in the left viewport toolbar (`left_toolbar.py`) next to «Показать всё» + a new glyph in `icons.py` (register it in the icon coverage lists – update the smoke icon-palette block) with a Russian tooltip. Edge headers/edges follow moved nodes (edges are computed from node rects – verify after offsets).
5. Sticky clamp (`_clamp_to_mode`) must respect dragged extents (scene_rect grows with offsets). Selection click vs drag threshold: press selects on release without move; drag starts after ~4–6 px movement (standard QDrag-style threshold) so single clicks don't nudge nodes.

## TASK 12. STICKY / FREE VIEW MODES RESTORED (EXCLUSIVE, EFFECTIVE)

**Defect (screenshot 11):** the two checkable buttons «Липкий обзор»/«Свободный обзор» can be checked SIMULTANEOUSLY and neither affects the camera.

**Root cause (verified):** `ViewportToolbar.mode_requested` is emitted by both buttons but is NOT connected in `MainWindow._wire()`; nothing ever calls `canvas.set_mode()` or `left_toolbar.set_mode()`, so the checked states never synchronize and the canvas mode never changes.

**Requirements:** connect `lt.mode_requested` → set `canvas.set_mode(mode)` + `lt.set_mode(mode)` (exclusive checked pair, sticky default on startup as now); verify the sticky clamp actually constrains panning (drag empty space with LMB from Task 11 – in sticky mode the camera must not leave the tree bounds + margin; in free mode it can) and that both buttons cannot be visually active at once. Gesture-test block: click «Свободный» → `btn_free.isChecked()` true, `btn_sticky.isChecked()` false, `canvas.mode() == "free"`; sticky clamp moves the view back within bounds.

## TASK 13. NODE BODY REDESIGN: COMPACT, MINIMALIST, INFORMATIVE

**Defect (screenshot 12):** under the node headers the content is a wall of repeated truncated lines («Одностенный изотермический» ×5 in the ГС node; ~15 truncated scenario lines + «… ещё 36 сценариев (см. матрицу)» + «ΣQ = …» at the very bottom of the Возникновение node) – noisy and unreadable.

**Locked design (Q&A #7 – the customer REJECTED the «×N counters + first lines» proposal):**
1. Under each node header keep ONLY: a count caption and the formula/value.
2. «Возникновение пожара/взрыва» node body = caption «Всего: N сценариев» + the formula «ΣQ = X год⁻¹» (mono font) – NO individual scenario lines on the node (they live in the hierarchy «Группа сценариев», the matrix and the inspector).
3. «ГС» node body = «Всего: N разновидностей»; «ИЗ» node body = «Всего: N источников» (N = number of configured causes; when N = 0 show «не задано» in the cutoff gray so the user sees the validator will complain).
4. Presence nodes («Наличие вещества»/«Наличие ОК») body = the probability label from Task 15.
5. **Enlarge the formula slightly** (the ΣQ/Q line): ~+2 px over the current meta size; adjust node sizing/heights accordingly in `layout.py` (WYSIWYG: canvas + PDF + `qa_sheet`/`qa_pdf_page1` all reflect it).
6. Keep the node design itself (headers, accent bars, palette) – only the body changes. All changes via `display_lines`/layout sizing in `eta\core\layout.py` + `render.py`; update smoke assertions that count lines/pixel bounds and the affected QA shots.

## TASK 14. NODE TEXT: NO MORE MID-WORD CLIPPING – WHOLE-WORD WRAPPING

**Defect (screenshot 13):** node texts are cut mid-word/letter at the right border without ellipsis («Наличие вещества (ГГ» → «(Г1», «Возникновение пожара/взрыв» → missing «а», «резервуар…» losing its ellipsis).

**Requirements:**
1. Text wrapping inside nodes is strictly by WHOLE WORDS (the `math_wrap` in `eta\ui\math_text.py` already wraps on spaces – the defect is node SIZING: widths don't accommodate the longest word).
2. Node width must grow to fit the longest word of every wrapped line (headers included): minimum width = max over lines of (longest word advance + 2×NODE_INSET), capped by a raised MAX_NODE_W if truly needed – but NEVER clip a word. Headers like «Появление источника зажигания (ИЗ)» wrap to two lines by words; nothing is ever cut mid-word.
3. After Tasks 13+14 the headers «Наличие вещества (ГГ)», «Наличие окислителя (ОК)», «Образование горючей среды (ГС)», «Появление источника зажигания (ИЗ)», «Возникновение пожара/взрыва» must all render COMPLETELY on `qa_canvas.png` (vision check on a 2× crop). Layout test: assert no line's advance exceeds its node's text width budget.

## TASK 15. PRESENCE INPUT = «ВЕРОЯТНОСТЬ ПРИСУТСТВИЯ» (USER-ENTERED PROBABILITY)

**Defect (screenshot 14):** presence nodes print «время присутствия: 1» – «1» of what? No unit; and in «частота» mode the label wrongly says «время» too (`layout.py` lines ~163–167 print the same label for both modes).

**Locked decision (Q&A #6):** rename to «вероятность присутствия» and let the user compute and enter it themselves:
1. Replace the two-mode Presence input with a SINGLE field: «Вероятность присутствия» – dimensionless 0–1, entered by the user (parse via the existing `parse_prob`, comma/dot tolerant, spinbox-style field like other numeric fields). The internal `Presence` class keeps its structure but the effective mode becomes a plain probability: simplify to `q = value` (keep the class name and `q()` API so the engine formula `Q_сценария = Q_вещество·Q_ОК·…` is untouched).
2. Node body label: «вероятность присутствия: 0,050» (formatted value; from Task 13 this is the node's body line). PDF «ИСХОДНЫЕ ДАННЫЕ» lines use the same wording (update `MODE_RU` usage in `pdf_export.py`).
3. Serialization migration on load (format 5 keeps its version): old `time` mode → value maps directly (доля года 0–1 IS the presence probability); old `freq` mode → convert once at load: `value = 1 − e^(−f)` and store as probability; write back always in the new single-value form. Default for new nodes: 1,0 (вещество присутствует) – as before.
4. Inspector form: remove the mode combo; single field with validation 0–1; tooltip: «Вероятность присутствия вещества (окислителя) на рассматриваемом участке – доля года, безразмерная, 0–1. Учитывается в Q_сценария множителем.»
5. Tests: smoke block 2 (presence modes) rewrites to the probability semantics + migration cases (time 0,5 → 0,5; freq 6,0 → 1−e^−6); gesture/inspector blocks that set presence modes updated; confectionery-example math block must stay exact (the example used values that map identically).

---

## 6. LOCKED DECISIONS (Q&A round before this session – normative, not to re-ask)

1. (Task 4) Sibling-add rule as stated; «Группа сценариев»/scenario selection counts as selecting its owner Участок/установка.
2. (Task 6) Adaptive popup width for ALL combos: clamp [button width, 2× button width], wrap by words.
3. (Tasks 7/7.1) Informative tooltips (variant b), drafts in the task text.
4. (Task 11) LMB-drag node / LMB-drag empty + middle-drag pan; dragged positions PERSIST in the project file; auto-layout button returns and works.
5. (Task 10) Delete on canvas deletes the owning tree (with confirmation).
6. (Task 15) Presence = user-entered «вероятность присутствия» (0–1); no modes; old data migrates on load.
7. (Task 13) Node body = header + «Всего: N сценариев» + slightly enlarged formula; no per-line scenario/cause lists on nodes.
8. (Task 1) Bigger hierarchy glyphs + level indents approved; the rest of the tree styling at the engineer's discretion within the Swiss style.

## 7. FINAL DELIVERABLES

1. Questions asked per task BEFORE its implementation where genuinely ambiguous (§0); locked decisions not re-asked.
2. All fifteen tasks implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated for changed labels/behaviors; new blocks: sibling-add, Delete (tree + canvas + trash enable), Shift+wheel h-scroll, drag-offset round-trip + auto-layout, sticky/free exclusivity + clamp, presence probability + migration); `run_qa.cmd` regenerated and vision-reviewed (hierarchy with long names + h-scrollbar, inspector spacing, tooltips, combo popups, splitters, node bodies with word wrap – crop/2× for pixel truth).
3. Version → **6.2.0** (KB `meta.version` stays «6.1»); README updated where behavior is user-visible (splitters, drag/auto-layout, presence probability, hierarchy scrolling).
4. `old prompts (done prompts)\REPORT_SESSION_12.md` (English): per-task summary, files touched, root causes for tasks 10–12 with the exact fix, before→after strings for every changed user-facing label/tooltip, test/QA evidence (including the pixel-intermediate Shift+wheel values), known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only (§1); never pwsh string cmdlets; delete scripts after use; no em-dash anywhere.
- Modal dialogs block offscreen tests (`QMessageBox.exec`, `QDialog.exec`): use the seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_tree_delete`, patched `exec` capture) – extend, don't break.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: app-level filters/animations keep strong module-level refs (`scroll.py::_ACTIVE_FILTER`, the `_smooth` dict); toolbar buttons use `NoFocus` so clicks don't steal the Delete focus.
- `QShortcut` with `WidgetShortcut` context on the tree: the inline rename editor is a child widget – with WidgetShortcut the shortcut must NOT fire while editing (verify; if the editor still triggers it, filter by `self.tree.state() == EditingState` or install an event filter instead).
- Canvas gestures mixin (`gestures.py`) overrides mouse events – integrate drag/pan through/around it, don't break pinch/tap.
- Offscreen QA: `QT_QPA_FONTDIR=C:\Windows\Fonts` mandatory; `FT_New_Face failed…` and «plugin does not support raise()/propagateSizeHints()» are harmless stderr noise; long runs as background jobs with `python -u`; never leave a modal open in a test.
- `QPdfWriter`: one QPainter per document, new pages ONLY via `newPage()`.
- QLabel has no `setTextWidth` (that is QTextDocument) – use `setFixedWidth` or explicit `<br>` from `math_html_lines`.
- Feeding raw HTML into `math()` escapes it – `math()` takes the project mini-notation (`F_зд`, `N_у.м`, `λ_DU`), not `<sub>` tags; QTableWidgetItem cells render NO HTML (plain text only – keep math markup out of them).
- QSS `outline: none` everywhere needed (tabs, lists, tables, tree) – the customer rejects dotted focus rectangles anywhere.
- Table row heights with QLabel cell widgets: compute manually (`_apply_row_heights` pattern).
- WYSIWYG invariant: canvas and PDF both consume `compute_layout` + `render.py` – every geometry change (offsets, node bodies, formula size) goes through them once.
- Vision QA reads downscaled images – crop and 2× upscale before asking glm-5.3-flash about pixel truth (subscripts, clipped letters, focus rings).
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
