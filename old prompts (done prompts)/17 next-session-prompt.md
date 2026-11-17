# PROMPT: Kuji – Session 17. П1.1-множитель участка + переименования колонок + шорткаты RU/undo/clipboard + крупное дерево + рамка выделения + переработка PDF + шапка инспектора

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia No. 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–16 are done (v6.5.2). Read before starting: `old prompts (done prompts)\REPORT_SESSION_16.md` (cause-Delete fix, detach ×4 + «Отцепить» hint, ГС/ИЗ glyphs, drag card). Everything described there works and is covered by tests – do not break it without need. Session 17 is a **calculation-fix + UX/typography session**: seven tasks. One engine change is included (Task 2); serialization, KB and format 5 are NOT touched by any task. All design decisions below were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them, including the deliberately simplified П1.1 rule (see Task 2). Ask questions per §0 when a task or part of it is ambiguous.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report – in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian with correct sentence structure and etiquette (this overrides English for question lists; it is the single exception). If the user did not understand a question, REPHRASE it properly instead of repeating.
- **Application UI language: RUSSIAN** – unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menu items, messages, PDF texts) must be in normative Russian engineering style (§5 canon).
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README/PDF. Never «—» (em dash).
- Questions protocol (HARD GATE): ask **incrementally, per task, as work progresses**, NOT as one giant upfront list. When a task or part of it is ambiguous, has no concrete object, or carries double meaning – STOP that task, formulate a SHORT numbered question list in Russian about exactly that task, send it, and WAIT. Do not implement on assumptions. Principle #1 from the customer: «Лучше 10 раз спросить и переспросить, чем 1 раз накосячить.» While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items – but nothing that changes data semantics or file formats. All LOCKED decisions below must NOT be re-asked.

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` – Python 3.14.3, PySide6 6.12.0 |
| Entry point | `main.py`; launcher `run_app.cmd` (manual start is the USER's habit – never launch it in automated batches) |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_hierarchy, qa_hierarchy2/3, qa_tooltip, qa_combo, qa_matrix, qa_docview, qa_sheet, qa_switches, qa_inspector_*, qa_kb_*, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_drag_card, qa_stats.json) |
| Core tests | `smoke_test.py` (22 blocks), `gesture_test.py` (48 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – `meta.version` stays «6.1». This session does NOT edit the KB. Keep the rule anyway: NEVER edit the KB via pwsh string cmdlets, only temporary Python scripts over `read_bytes()/write_bytes()`, deleted after use. |
| App version | `eta\__init__.py` → `__version__ = "6.5.2"` – this session bumps to **6.6.0** (feature session). The gesture test asserts the substring «6.5» in block 1 – UPDATE it to «6.6». |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_17.md` (English) at the end |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE. Do not wire it in. |

## 2. STATE AFTER SESSION 16 (v6.5.2) – what exists, all tested

- **Paradigm (invariant):** five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5. In the formula display the leading `1·1` is the substance/oxidizer PRESENCE probabilities – not a site parameter.
- **Engine multipliers that already work (do not double them):** ТГМ `a₁·F` / `a·V^b` via `CalcContext.tgm_multiplier` (model.py ~312, value by site type through `tgm_level_value`); pipelines П1.2 `λ'·(F|L|V by site type)` via `p12_value` (model.py ~358, used in `scenarios` ~530-534 with the substituted piece `(5,7·10⁻⁶·50)`). The ТГМ/П1.2 pieces are live: editing the value or switching the type recalculates canvas/matrix/status without leaving the panel (gesture blocks 40/41).
- **Hierarchy (session 15/16):** scenario row per tree under each owner, cause children (ГС prefix «Образование ГС:», ИЗ plain; flow-scope suffix « – массовый расход истечения …»); cause/scenario rows selectable+draggable; И-гейт attach = drop on a same-list cause (zones: middle 50 % «on», edge 25 % detach); detach four ways (scenario row, owner row, ПКМ «Отцепить от родителя», empty space/edge zone) + «Отцепить» cursor hint; Delete/trash on a pure cause selection deletes THE CAUSES with branches (one window, seam `_confirm_remove_causes`), the участок is never touched; scenario rows are a safe no-op; mixed selections delete only objects; canvas Delete deletes a tree only for a USER-CLICKED node (`MainWindow._canvas_sel_by_click`).
- **Glyphs/drag card (session 16):** ГС = amber cloud `gs-cause` #B45309, ИЗ = red flame `iz-cause` #B91C1C (canvas node-class colors); drag card `_drag_pixmap(glyph, text, dpr)` = flat #EFF6FF card, 1 px #3B82F6 border, glyph 16 + 8 gap + elided single-line title ≤300 px, DPR-aware, hotspot `QPoint(16, h//2)`.
- **Canvas:** QGraphicsView `TreeCanvas` (eta\ui\canvas.py); mouse today: ЛКМ on node = press→drag (threshold ~5 px) or click-select (`select_node` + `node_clicked` → inspector); ЛКМ on empty = **PAN** (`_lmb_pan_origin` in mousePressEvent ~408; a click without movement clears selection, `empty_clicked`); СКМ = pan (gesture mixin `_gesture_mouse_press`); wheel = zoom to cursor (`set_zoom_level` clamps 0.08–6.0); `fit_tree()` (~345) = `fitInView(scene_rect + 24 px)` on every refresh; «липкий/свободный обзор» modes with `_clamp_to_mode`; nodes move via `node_offsets` (WYSIWYG: canvas and PDF share `compute_layout`); node geometry is metrics-driven (`layout.make_node`: ink width + 2×NODE_INSET 20 px + 2 px, height = 2×PAD_V 12 px + line heights; no width cap).
- **Matrix/document:** in-app table + PDF derive from `matrix.build_matrix` (header in eta\core\matrix.py:39-40). Pop-out document window with Ctrl+(+/−)/Ctrl+0 zoom shortcuts (doc_window.py).
- **PDF export today (eta\export\pdf_export.py, ONE QPainter over QPdfWriter, 254 dpi, landscape, margins MARGIN_MM):** `export_schematic` (doc_scene render), `export_matrix` (column weights [6,40,16,106,24,68], row_h 4.6 mm, header drawn with default pen, no cell wrap, `rows_per_page` math can cut the last row mid-height), `export_report` (blocks `head/line` drawn with `TextWordWrap` into a ONE-LINE-height rect row_h 4.4 mm → wrapped lines OVERLAP neighbors – this is the «В ОЗНИК НОВ ЕНИЯ» artifact on the customer's screenshots; long lines clip at the right edge; totals «Q_возникновение = …» at ~182; report line «Q_возникновение (…) = Σ Q_сценариев × Kσ = …» at ~326; «Источники: …» joined with «;» at ~332; final section «ИСТОЧНИКИ» + «Исполнитель: ___ Дата: ___» at ~339-341). Status bar label «Q_возникновение: » in main_window.py:407.
- **Tests/QA:** smoke 22 blocks, gestures 48 blocks, both green; qa_drag_card.png exists; run_qa.cmd regenerates everything.

## 3. CODE MAP (extend, don't break)

- `eta\core\matrix.py` – Task 1: the ONLY place with the two column titles (lines 39-40). PDF matrix + in-app table + tests consume them.
- `eta\core\model.py` – Task 2: `scenarios()` ГС-factor branch (p12 ~530-534, p13 via `tgm_multiplier` ~526; p11/direct currently use `g["q"]` raw – find the branch, add the site-value multiplier); substituted piece format `(4·10⁻⁵·86)` like the existing `(5,7·10⁻⁶·50)`; `fmt_num` from numfmt.
- `eta\ui\inspector_panel.py` – Task 3: `show_object` (~345-353: top caption `self.title.setText(KIND_TITLES…upper())` at 348, bold name at 349); section headers: «ТЕРРИТОРИЯ» 369, «ПОЖАРНЫЙ ОТСЕК» 429, «ПОМЕЩЕНИЕ» 530 (building has no kind-named section; участок/установка use «ТИП»/«ЗНАЧЕНИЕ» – untouched); «Площадь территории:» label at 427 (tooltip wording may stay); tree-node form header «НОДА ДЕРЕВА» at 749 STAYS.
- Shortcuts (Task 4): main_window.py 165-226 (Ctrl+N/O/S StandardKeys, Ctrl+E/У, Ctrl+Q/Й, Ctrl+D/В, Alt+A/Ф, Delete, F9), hierarchy_panel.py 474/487 (F2, Delete), doc_window.py 78-85 (Ctrl+±, Ctrl+0). No Ctrl+Z/Y/C/V exist anywhere yet.
- Undo/clipboard (Task 4): MainWindow `_mark_dirty` (main_window.py ~814) and the mutation seams (add/delete/rename object, `object_props_changed`, cause add/remove, `handle_drop` attach/detach, tree add/delete/move, `_apply_library_equipment`); serializer dict round-trip for snapshots (eta\core\serializer.py, format 5, in-memory); hierarchy `_selection_objects`/`_dedupe_ancestors`/`add_kind`/`objects.add_child`/`move_subtree` for paste semantics; fresh ids via `objects`/`model` id generators (`_new_cid`).
- Canvas (Tasks 5/6): `eta\ui\canvas.py` mousePressEvent/mouseMoveEvent/mouseReleaseEvent (~390-502), `_move_node_item`, `_commit_node_drag`, `fit_tree`, `set_zoom_level`, `_gesture_mouse_press` (СКМ pan mixin); `eta\ui\theme.py` node knobs (NODE_INSET, PAD_V, MIN_NODE_W, node fonts F_TITLE/…) and `eta\core\layout.py make_node` (metrics-driven); render.py `draw_node` (fire node accent styling).
- PDF (Task 7): `eta\export\pdf_export.py` (full rework of `export_report`, targeted fixes in `export_matrix`); `main_window.py:407` status label («Q_В: »); QPdfDocument.getAllText used by gesture tests to assert PDF text.
- Tests: extend gesture_test.py with blocks 49 (Task 2+1+3), 50 (Task 4), 51 (Tasks 5/6), 52 (Task 7 PDF text); smoke_test.py: new blocks for the multiplier math/no-double-multiply, the RU→Latin key map, undo snapshot semantics. Update every assertion that references renamed strings (matrix headers, «Площадь территории», «ТЕРРИТОРИЯ» sections, «Q_возникновение», version «6.5»→«6.6»).
- Do not touch: `eta\core\kb.py`, KB json, serializer format, `layout.py` WYSIWYG protocol (only its size constants), `kb_window.py` (except if a renamed string leaks there – verify by grep).

## 4. SESSION RULES

1. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference changed behavior; run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop + 2× upscale) the affected artifacts before declaring the task done (Task 2/1: qa_canvas/qa_matrix/qa_hierarchy; Task 3: qa_inspector_territory/qa_window; Task 4: qa_window; Task 5: qa_canvas/qa_sheet/qa_window; Task 6: qa_canvas; Task 7: qa_pdf_page1/qa_pdf_matrix_page1/qa_pdf_report + qa_window for the status bar).
2. No new external dependencies; PySide6-native only (QTextDocument/HTML is native).
3. Style: flat Swiss-utilitarian; new visuals via `theme.py`; no shadows/gradients; soft palette of 15/1 (#93C5FD selection, #3B82F6 primary).
4. Modal dialogs block offscreen tests: every NEW confirmation is a seam (like `_confirm_trees_delete` for group delete); menus testable without `exec`.
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions not re-asked.
7. Suggested order: Task 1 → 2 → 3 → 4 → 5 → 6 → 7 (PDF last: it consumes the new headers, Q_В and the bigger layout). Tests+QA after every task.
8. Format-5 compatibility: no file-format changes. Undo snapshots and the clipboard live IN MEMORY only.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new/changed strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses.
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Numbers shown to the user: engineering notation («9·10⁻⁵», comma mantissa, Unicode superscripts).

---

## TASK 1. MATRIX COLUMN RENAMES (quick, exact strings)

Rename in `eta\core\matrix.py:39-40` (the single source; the in-app table, the PDF matrix page and all tests consume it):
1. «Сценарий (ГС – расход – тип горения – ИЗ)» → **«Сценарий пожара»**.
2. «Участок/установка» → **«Участок (установка)»**.
Verify by grep that no other place hardcodes the old titles; update QA vision (qa_matrix) and any test that asserts headers. Column widths must still look right in-app and in the PDF (the PDF gets its own width rework in Task 7 – here only ensure no in-app regression).

## TASK 2. П1.1/DIRECT ГС-ПРИЧИНЫ: МНОЖИТЕЛЬ ЗНАЧЕНИЯ УЧАСТКА (engine; LOCKED – упрощённое правило заказчика)

**Customer decision (final, LOCKED – quoted from the Q&A):** «Я понимаю методологическую разницу с Приказом МЧС № 533, но для логики нашей программы подтверждаю именно упрощённое правило для причин П1.1/direct: Оставляй П1.2 (λ·L) и ТГМ П1.3/П1.4 (a₁·F / a·V^b) без изменений (чтобы не было двойного умножения). Для причин П1.1 умножай λ на параметр выбранного типа участка из инспектора: F (для типа «участок (м²)»), L (для «линейный объект») или V (для «аппарат/установка»). Отображай множитель в формуле явно: `(4·10⁻⁵·86)` и обновляй расчёт в реальном времени при смене типа или значения параметра участка.»
The customer knows this deviates from the per-unit reading of табл. П1.1 and chose it consciously – do NOT re-open, do NOT «fix» to N, do NOT add an N field.

**Requirements:**
1. In `model.py scenarios()` the ГС factor for kinds **p11 and direct** (including their flow-scoped and rupt variants) becomes `λ × (F|L|V)` where F/L/V is the VALUE OF THE TREE OWNER'S OWN TYPE (участок or наружная установка – both have the type selector; resolve via the existing type-driven value resolver used for ТГМ/П1.2, e.g. `tgm_level_value(ctx.site_props)`); if the value is not set → multiplier 1 (formula shows the bare `(4·10⁻⁵)` piece). П1.2 and p13 pieces stay EXACTLY as today – no double multiplication (write an explicit smoke assertion for that).
2. Substituted formula piece: `(4·10⁻⁵·86)` – engineering notation, comma mantissa, same style as `(5,7·10⁻⁶·50)`. The `1·1·` presence prefix is untouched.
3. Reactivity (1.1 of the customer report): switching the type combo (участок (м²) → линейный объект → аппарат/установка) or editing the value must IMMEDIATELY update formulas and Q on the canvas node, in the matrix table and in the status bar – without re-selecting anything. This already works for ТГМ/П1.2; after the multiplier change it must work for П1.1 trees too. Add a gesture regression: a ГЖ tree with a П1.1 cause; real combo switch + real value typing → the matrix formula cell and the node ΣQ change live.
4. No new fields, no serialization change, no KB change.

**Acceptance:** smoke block (pure engine: pieces for p11 ×86 / ×L / ×V; p12/p13 unchanged byte-exact; None-value → no multiplier); gesture block 49 part 1 (live reactivity through the real inspector); QA vision qa_canvas/qa_matrix show the new pieces.

## TASK 3. ШАПКА ИНСПЕКТОРА: ЧИСТКА ЗАГОЛОВКОВ (LOCKED)

From the customer screenshot (marks 1.2/1.3/1):
1. «Площадь территории:» → **«Площадь:»** (inspector_panel.py:427; the tooltip wording may keep explaining that it is the territory area).
2. Section header «ТЕРРИТОРИЯ» (under the divider) → **«ПАРАМЕТРЫ ТЕРРИТОРИИ»**; apply the SAME uniform pattern to the other kind-named sections: «ПОЖАРНЫЙ ОТСЕК» → **«ПАРАМЕТРЫ ПОЖАРНОГО ОТСЕКА»**, «ПОМЕЩЕНИЕ» → **«ПАРАМЕТРЫ ПОМЕЩЕНИЯ»** (the building form has no kind-named section; «ТИП»/«ЗНАЧЕНИЕ» of участок/установка stay as they are).
3. REMOVE the top ALL-CAPS object-type caption above the object name (`show_object` line 348: `self.title.setText(KIND_TITLES…upper())`) – for ALL object kinds uniformly; the form starts directly with the bold object name. The tree-node form header «НОДА ДЕРЕВА» (line 749) STAYS (it marks the context switch, is not an object-type duplicate).
Update tests that assert the old strings (grep «Площадь территории», «ТЕРРИТОРИЯ», «ПОМЕЩЕНИЕ» across tests); QA vision qa_inspector_territory + qa_window.

## TASK 4. ШОРТКАТЫ В РУССКОЙ РАСКЛАДКЕ + UNDO/REDO + БУФЕР ОБМЕНА ИЕРАРХИИ (LOCKED)

1. **Universal layout-independent shortcut mechanism (LOCKED):** an application-level event filter that, for KeyPress events with Ctrl and/or Alt modifiers whose `key()` is a Cyrillic Qt.Key_* code, translates the key to its Latin POSITIONAL equivalent (full ЙЦУКЕН table) and re-delivers the event, so EVERY letter shortcut – current (`Ctrl+N/O/S/E/Q/D`, `Alt+A`, future ones) – fires in both layouts without manual twins. Keep the existing explicit twins (harmless). Implementation notes: a pure module-level function (e.g. `latin_key(code) -> int | None`) for testability; guard against re-processing the synthetic event; install once on the QApplication; strong module-level ref (PySide6 GC pitfall). No `nativeVirtualKey` tricks needed – Qt Cyrillic key codes are enough.
2. **Undo/redo (LOCKED):** `Ctrl+Z` = undo, `Ctrl+Y` = redo; history depth **50**; «любых действий» – snapshot-based: serialize the full model state (objects + trees, format-5 dict path in memory) and push BEFORE each mutation; restore = load dicts back + full `_refresh` (+ selection restored where the marker still exists). Push points: every existing mutation seam (object add/delete/rename, props commits, cause add/remove, attach/detach drop, tree add/delete/move, template apply, node-offset commits) – centralize via a `MainWindow._undo_push()` seam and call it from the seams (NOT from `_mark_dirty` directly: valueChanged streams must coalesce – skip a push when the serialized state equals the stack top). Redo stack clears on a new action after undo. Ctrl+Z/Ctrl+Y must work in BOTH layouts via item 1. Clipboard-style actions (Task 4.3) are undoable like any add.
3. **Hierarchy clipboard (LOCKED):** `Ctrl+C` copies the SELECTED object row(s) (multi-select: dedupe ancestors as in delete) as full SUBTREES (descendants + their trees with causes/dependencies; deep copy in an internal in-memory clipboard, fresh oids/tree_ids/cids with parent mapping preserved; the copied ROOT gets title suffix « (копия)», descendants keep titles; node_offsets dropped for a clean layout). `Ctrl+V` pastes under the CURRENTLY SELECTED object if `can_add` allows the root kind (else the existing information box from `add_kind`'s ValueError path), or at the hierarchy ROOT when nothing is selected (territories only). Repeated pastes allowed. Copy on non-object rows (causes/scenarios) is a safe no-op. Both shortcuts work in both layouts (item 1). New pasted objects become selected; `_mark_dirty` + full refresh; undoable.
4. Tests: smoke (latin-key map unit; undo snapshot semantics); gesture block 50: Cyrillic `QTest.keyClick(w, Qt.Key.Key_Ы, ControlModifier)` triggers Save's action (or another verifiable action) while the Latin path still works; Ctrl+Z undoes an add (object disappears), Ctrl+Y redoes; 3 edits → 3 undos; clipboard: copy участок with a tree → paste into another room → subtree+trees exist with fresh ids, titles « (копия)», Q recomputes; undo removes the paste.
5. UI strings: tooltips/menu items for undo/redo/copy/paste in Russian («Отменить», «Вернуть», «Копировать», «Вставить»); if you add them to the «Правка» menu or toolbar – follow the flat canon; shortcuts displayed as text (Ctrl+Z etc.).

## TASK 5. КРУПНОЕ ДЕРЕВО СОБЫТИЙ НА ХОЛСТЕ (LOCKED – вариант «и то и другое»)

The customer: with 36 scenarios the matrix is huge while the 5-node tree is a small island (screenshot №2). LOCKED: BOTH bigger base geometry AND smarter fit.
1. **Base sizing/typography (upstream in theme.py/layout.py so canvas AND PDF schematic grow together, WYSIWYG preserved):** increase node paddings and fonts – concrete numbers are yours to pick with QA verification: noticeably larger node height (PAD_V up from 12 px), larger inner inset (NODE_INSET up from 20 px), larger title/value fonts (F_TITLE and the value lines), thicker/softer connector curves. Keep the metrics-driven geometry protocol (ink-based width, TextDontClip, no caps) – scale constants, don't break the mechanism.
2. **Accent result node:** «Возникновение пожара» gets a more expressive treatment per the guidance: a clearly thicker border, slightly tinted fill and a larger/bolder ΣQ line – readable at a glance as the «causes → event» sink. Flat canon only (no shadows/gradients); canvas node-state colors (#2563EB «задано», #7C3AED «ок») are LOCKED session-14 decisions – the accent must not collide with them (work with border thickness/typography, not state colors).
3. **Smart fit:** `fit_tree()` – padding 40–60 px (replace 24), and an UPSCALE CAP of **1.5×**: a small tree may scale UP to fill the canvas but never beyond 1.5× (after fitInView, clamp to [., 1.5] and re-center); large trees still fit fully (downscale unlimited). Keep the sticky-mode clamp consistent with the new padding. «Показать всё» (Alt+A/Ф) uses the same logic; Ctrl+0 in the doc window unchanged.
4. Tests/QA: gesture block 51 part 1 asserts programmatically (zoom level after fit for a small single-tree project is ≤1.5 and >1.0; node heights grew vs the previous constants – assert against theme values); vision QA qa_canvas/qa_sheet/qa_window (tree large, readable at 100 %, no clipped ink – `node_text_fits` smoke block still passes).

## TASK 6. РАМКА ВЫДЕЛЕНИЯ И ГРУППОВЫЕ ОПЕРАЦИИ НА ХОЛСТЕ (LOCKED)

1. **Rubber band (LOCKED вариант 1):** ЛКМ-drag on EMPTY canvas = rectangle selection (replaces ЛКМ-pan); a plain ЛКМ click without movement on empty still clears the selection (`empty_clicked` path unchanged). Style the rubber band per the guidance: translucent blue fill rgba(59,130,246,0.12) + 1 px #3B82F6 border. Selection = all NodeItems intersecting the rect (annotations are NOT group-selectable).
2. **Pan (compensation, LOCKED):** pan moves to СКМ (already exists) **plus NEW Space+ЛКМ**: holding Space switches the cursor to hand; ЛКМ-drag pans; release of Space restores. Show the Space hint in the canvas tooltip/status tip (Russian, short).
3. **Selection model:** the canvas controller gains a real selection SET (node ids) in addition to the current single `select_node`; a node click selects it alone; **Ctrl/Shift+click toggles** a node in/out of the set; every selected node shows the existing dashed accent outline. The inspector still opens the LAST clicked node's form; `_canvas_sel_by_click` semantics from session 16 are preserved (a user click/marquee selection counts; programmatic dashed selection from a cause-row click does not).
4. **Group drag:** dragging ANY selected node moves ALL selected nodes together (same `_move_node_item` delta per node; edges follow; commit via the existing node_offsets path on release; one dirty/refresh). Dragging an unselected node keeps today's single-node behavior.
5. **Group Delete (LOCKED вариант 1):** Delete/trash with several nodes selected (possibly of different trees) deletes ALL trees owning the selected nodes with ONE confirmation window listing them (new seam `_confirm_trees_delete(trees)`; reuse `_confirm_tree_delete` appearance). Single-node behavior unchanged (session 16).
6. Tests: gesture block 51 part 2 – real mouse: press on empty → move → release selects exactly the nodes inside the rect (assert the selection set); Ctrl+click toggles; group drag changes every selected node's offsets and the edges follow (assert node_offsets); group Delete shows ONE seam window and removes both trees; Space+ЛКМ pans (scrollbars change); ЛКМ-drag no longer pans. QA vision qa_canvas.

## TASK 7. ПЕРЕРАБОТКА PDF-ОТЧЁТА (LOCKED – гибрид: QTextDocument для текста, QPainter для матрицы/схем)

Screenshots №3–№5 defects (all verified in code): overlapping wrapped lines («В ОЗНИКНОВ ЕНИЯ» – see §2 root cause), clipped right edges, pale matrix headers, mid-row page cuts, tiny font with huge line spacing, raw dump of all three site fields, triple identical ГС lines (flow suffix not shown in the report), «Kσ»/«·» glyph collisions («10910⁻⁵»), «Q_возникновение», «Источники: …» через «;», «Исполнитель/Дата».

1. **Engine split (LOCKED):** text report pages («1. Объект и параметры», «2. Исходные данные», «3. Результаты расчёта», «4. Источники») move to **QTextDocument + HTML** printed onto the SAME QPdfWriter file: render QPainter pages FIRST (schematics, matrix), end that painter, then `QTextDocument.print(writer)` (it opens its own painter and appends pages; set the writer page layout before; A4 portrait for the report block is acceptable if you set the layout per document – if per-section orientation is not achievable cleanly, keep everything landscape A3 and say so in the report). Body 10–11 pt, tables 8.5–9.5 pt, line-height 1.3–1.4, a Cyrillic-capable system font with real superscripts (Segoe UI / DejaVu Sans); formulas in the mono font (`mono_font`) so «·»/superscripts never collide; numbers «1,09 · 10⁻⁵» never wrap.
2. **Report content (инженерный стиль, LOCKED):**
   - Title «ОТЧЁТ О РАСЧЁТЕ ЧАСТОТЫ ВОЗНИКНОВЕНИЯ ПОЖАРА» + subtitle «Объект расчёта: <владелец> – <тип сценария>» (real names, no truncation; project name + date line kept compact).
   - «1. Объект и параметры»: human-readable, ONLY the type-relevant site field (S = 86 м² / L / V – never all three), functional purpose (П1.3/П1.4), молниезащита, presence probabilities of substance/oxidizer, Kσ, «Огненный шар» switch. No raw prop dumps.
   - «2. Исходные данные»: compact TABLE `Событие | Величина | Источник`; ГС rows include the flow-scope suffix (fixes the triple-identical lines); values with dimensions (год⁻¹ / безразм.), sources in brackets.
   - «3. Результаты расчёта»: per tree the Q_j formula lines (existing substituted form), then **«Q_В = Σ Q_i · Kσ = … год⁻¹»** and the total across trees. `Q_возникновение` is GONE: rename to **Q_В** (subscript В) EVERYWHERE – report, matrix totals, AND the app status bar (main_window.py:407 «Q_В: ») – LOCKED «везде».
   - «4. Нормативные и справочные источники»: ONE numbered list (1., 2., …) at the END with dedup – merge `_tree_sources` across trees and the final ГОСТ/Приказ block, drop the per-sheet «Источники: …; …» line. REMOVE «Исполнитель: …» and «Дата: …» completely.
3. **Matrix PDF (QPainter fixes, LOCKED):** header contrast (light #E2E8F0 background + bold #0F172A text or equivalent flat contrast), visible cell grid, column widths recomputed for the NEW short headers (Task 1), word-wrap for the scenario column (multi-line rows via metrics; row height measured, never guessed), Q column right-aligned no-wrap, page breaks BETWEEN rows (never mid-row; fix the `rows_per_page` math), totals line «Q_В = …». Schematic pages keep the existing doc_scene render (they inherit the bigger layout from Task 5 – verify A3 fit).
4. Tests/QA: gesture block 52 via QPdfDocument.getAllText: «Q_В» present, «Q_возникновение» absent, «Исполнитель» absent, «Отчёт» title present, numbered sources (a line starting «1. »), header «Сценарий пожара» present on the matrix page; update old PDF assertions (Источники block format changed). QA vision on qa_pdf_page1/qa_pdf_matrix_page1/qa_pdf_report (crop + 2×): no overlaps, nothing clipped, headers readable, sources numbered. The report must state what layout engine each page uses.

---

## 6. LOCKED DECISIONS (Q&A round before this session – normative, not to re-ask)

1. (Task 2) Simplified П1.1/direct rule, FINAL: multiply λ by the site's own F/L/V by type; П1.2 and П1.3/П1.4 untouched (no double multiplication); explicit piece `(4·10⁻⁵·86)`; live reactivity on type/value change; the customer consciously chose this over the per-unit N reading of табл. П1.1 – do not revisit.
2. (Task 4) Universal Cyrillic→Latin shortcut filter (not per-shortcut twins); Ctrl+Z/Ctrl+Y undo/redo, depth 50, any actions; Ctrl+C/Ctrl+V in the hierarchy for object subtree copy-paste (same or another territory/building/room).
3. (Task 5) Both bigger nodes/typography AND fit-upscale with ceiling 1.5×, fit padding 40–60 px; accent fire node within the flat canon.
4. (Task 6) ЛКМ-drag on empty = rubber band; pan = СКМ + Space+ЛКМ; group Delete removes ALL trees of the selected nodes with ONE confirmation.
5. (Task 7) Hybrid engine: QTextDocument for text pages, QPainter stays for matrix/schematics with fixes; Q_В everywhere incl. status bar; ИСХОДНЫЕ ДАННЫЕ as a table; ONE numbered deduped Источники list at the end; «Исполнитель»/«Дата» removed; only the type-relevant site parameter in section 1.
6. (Task 3) «Площадь:», «ПАРАМЕТРЫ ТЕРРИТОРИИ» (+ uniform pattern for other kind-named sections), no top object-type caption above the name; «НОДА ДЕРЕВА» stays.
7. Engine scope: only the П1.1/direct multiplier changes; serialization/KB/format 5 untouched; KB meta.version stays «6.1».

## 7. FINAL DELIVERABLES

1. All seven tasks implemented; `smoke_test.py` + `gesture_test.py` green (new blocks 49-52 + updated assertions: headers, «Площадь», sections, Q_В, version «6.6»); `run_qa.cmd` regenerated and vision-reviewed (all affected artifacts per §4.1).
2. Version → **6.6.0**; README updated where behavior is user-visible (multiplier + examples of the new formula piece; column renames; shortcuts incl. undo/clipboard with the Space+ЛКМ pan change; bigger tree/fit; rubber band/group ops; PDF report overhaul).
3. `old prompts (done prompts)\REPORT_SESSION_17.md` (English): per-task summary, files touched, root causes with the exact fix (esp. the PDF overlap mechanics and the multiplier placement), before→after for every changed user-facing string, the concrete sizing/fit parameters chosen in Task 5 (with the QA evidence), the shortcut/undo/clipboard design, test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Drag events deliver through the VIEWPORT; a synthetic QDropEvent reaches `dropEvent` ONLY after enter+move put the view into drag state (session-16 lesson, block 48).
- Real-mouse harness: `QTest.mousePress` + button-held MouseMove via sendEvent; `QTest.mouseMove` alone never starts a drag; selectable flags are mandatory for row drags.
- Stale QTreeWidgetItem references: re-fetch rows after every rebuild; item identity asserts need freshly fetched items.
- Wide-name column: clamp click X into the viewport; itemAt check before clicking.
- itemChanged feedback loops: block signals while programmatically filling tables/trees.
- Modal dialogs block offscreen tests – seams only; new confirms/menus must be seam-testable.
- QSettings in tests: hermetic ini. PySide6 GC: strong module-level refs for app-level filters (the Task-4 key filter and any canvas helpers).
- QTest keyClick sends key CODES: for the RU-layout test use real Cyrillic Qt.Key_* codes with ControlModifier – that is exactly what Windows produces in the Russian layout.
- Undo snapshots: in-memory format-5 dicts; never write files; coalesce value-stream pushes by comparing serialized state; redo stack clears on new actions; selection restore by marker only if still alive.
- QPdfWriter: one QPainter at a time – render all QPainter pages first, `end()` the painter, then `QTextDocument.print(writer)` appends text pages; set the page layout before printing; QT_QPA_FONTDIR=C:\Windows\Fonts offscreen.
- Vision QA reads downscaled images – crop + 2× upscale before asking glm-5.3-flash; programmatic checks (metrics, getAllText) beat vision estimates.
- HiDPI: keep `devicePixelRatio` handling in the drag card (session 16) intact; compare `deviceIndependentSize()` in tests.
- Canvas geometry protocol (session 15): nodes move via setPos, edges only through setPath; the Task-5 size changes live in theme constants + metrics – do not reintroduce width caps.
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
- Cyrillic/KB edits: byte-safe temporary Python scripts only (not needed this session, but the rule stands); no em-dash anywhere.
