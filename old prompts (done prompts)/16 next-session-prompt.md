# PROMPT: Kuji – Session 16. Cause-Delete bug + discoverable detach + drag-thumbnail design + distinct ГС/ИЗ glyphs

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia No. 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–15/1 are done (v6.5.1). Read before starting: `old prompts (done prompts)\REPORT_SESSION_15.md` INCLUDING its «SESSION 15/1 ADDENDUM» at the end (real-mouse drag bugfix, «Редактировать» mode, soft colors, and the two customer follow-up decisions). Everything described there works and is covered by tests – do not break it without need. Session 16 is a **defect-fix + interaction-polish session**: four tasks (two hierarchy-flow fixes, two visual-design tasks). No engine, math, or serialization changes are expected (the И-gate chain math already handles `parent = None`). All design decisions below were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them. Ask questions per §0 when a task or part of it is ambiguous.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report – in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian with correct sentence structure and etiquette (this overrides English for question lists; it is the single exception). If the user did not understand a question, REPHRASE it properly instead of repeating.
- **Application UI language: RUSSIAN** – unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menu items, messages) must be in normative Russian engineering style (§5 canon).
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README. Never «—» (em dash).
- Questions protocol (HARD GATE): ask **incrementally, per task, as work progresses**, NOT as one giant upfront list. When a task or part of it is ambiguous, has no concrete object, or carries double meaning – STOP that task, formulate a SHORT numbered question list in Russian about exactly that task, send it, and WAIT. Do not implement on assumptions. Principle #1 from the customer: «Лучше 10 раз спросить и переспросить, чем 1 раз накосячить.» While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items – but nothing that changes data semantics or file formats. All LOCKED decisions below must NOT be re-asked.

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` – Python 3.14.3, PySide6 6.12.0 |
| Entry point | `main.py`; launcher `run_app.cmd` (manual start is the USER's habit – never launch it in automated batches) |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_hierarchy, qa_hierarchy2, qa_hierarchy3 (multi-select), qa_tooltip, qa_combo, qa_matrix, qa_docview, qa_sheet, qa_switches, qa_inspector_fire, qa_inspector_building, qa_inspector_territory, qa_kb_templates, qa_kb_measures, qa_kb_iz, qa_kb_gs, qa_kb_fire_modes, qa_kb_tables, qa_kb_tables2, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_stats.json) |
| Core tests | `smoke_test.py` (22 blocks), `gesture_test.py` (46 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – `meta.version` stays «6.1». This session does NOT edit the KB (no byte-safe scripts needed); keep the rule anyway: NEVER edit the KB via pwsh string cmdlets, only temporary Python scripts over `read_bytes()/write_bytes()`, deleted after use. |
| App version | `eta\__init__.py` → `__version__ = "6.5.1"` – this session bumps to **6.5.2**. The gesture test asserts the substring «6.5» (stays valid). |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_16.md` (English) at the end |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE. Do not wire it in. |

## 2. STATE AFTER SESSION 15/15.1 (v6.5.1) – what exists, all tested

- **Paradigm (invariant):** five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5.
- **Hierarchy structure (session 15):** under each owner (участок/наружная установка) – one **scenario row** per tree (scenario-type title, e.g. «Сценарий пожара ТГМ»), children = all user-added causes: GS rows prefixed «Образование ГС: <название>» (+ « – <диапазон расхода>» for flow-scoped entries), IZ rows plain. Dependent causes nest under their parent's row. Cause and scenario rows are **selectable + drag-enabled** (`ItemIsSelectable` is MANDATORY – Qt never starts drags from non-selectable items; this was the 15/1 real-mouse bug). Object rows are selectable/editable/drag-enabled.
- **Cause dependencies (И-гейт):** drag a cause row onto another cause of the SAME list (ИЗ→ИЗ, ГС→ГС, same tree only) → target becomes PARENT; Q = Q(родитель) × Q(потомок); each root→leaf path is ONE scenario row with the product of factors; chain names use « → ». Detach exists: drop on the scenario row of the same tree sets `parent = None`. «Убрать» in the inspector removes a cause WITH its children (`MainWindow._confirm_remove_chain` seam).
- **Drag UX:** styled semi-transparent pill with the row title (`_drag_pixmap` in hierarchy_panel.py, set via `drag.setPixmap/setHotSpot` in `_HierTree.startDrag`); during dragMove valid targets highlight blue (#DBEAFE), invalid red (#FEE2E2) + ForbiddenCursor; private MIME mark `application/x-kuji-hier` (module constant `_HIER_MIME` in hierarchy_panel.py) tags own drags and lets tests synthesize drag events; after a successful cause drop the target row expands and the moved row is selected (`_reveal_cause`). Objects reparent via drag under `PARENT_RULES` (`move_subtree`); scenario rows drag onto other owners (type preserved). **Known defects (Tasks 3–4):** the current pill has a slightly OFF-CENTER text (a manual +4 px y-shift on top of AlignVCenter), no icon, no HiDPI (no `devicePixelRatio`), a crude 42-char truncation instead of pixel eliding, and 0.88 opacity; and ALL cause rows (GS and IZ) carry the SAME red glyph `GLYPH_CAUSE` («cause», #B91C1C) – the two lists are indistinguishable at a glance.
- **THE DEFECT (Task 1):** clicking a cause row selects it and emits `cause_selected` (opens the node form, dashed-selects the canvas node) but NEVER updates `HierarchyPanel._selected`. The delete flow `_selected_deletable_nodes()` collects `selectedItems()` → object oids; cause rows carry no oid → the list is empty → the **legacy fallback** («if no object rows are selected, use the last selected object `_selected` while it is alive») silently substitutes the previously selected object – almost always the УЧАСТОК that owns the tree. Both the Delete key (viewport event filter → `_delete_current`) and the trash button (`MainWindow._update_trash` → `hierarchy.selected_objects()` → same method; then `_delete_selection` → `hierarchy.delete_objects(nodes)`) hit this. Result: selecting a cause and pressing Delete (or clicking the trash) deletes the whole участок with a confirmation the user confirm-clicked through.
- **Task 2 background:** detaching by dropping onto the scenario row is implemented and seam-tested (gesture block 44), but it is undiscoverable: no hint marks the scenario row as a detach target, and dropping on empty space does nothing (itemAt → None → invalid). The customer tried and concluded a nested cause «cannot be moved back out».
- **Engine (unchanged this session):** ТГМ multiplier = a₁ × the level value by its type (`tgm_level_value`; участок/установка give м²/м/м³); П1.2 by type; flow-scoped GS rows (small/mid/big/rupt, «массовый расход истечения» wording); substituted formulas `Q₂ = 1·1·(2,2·10⁻⁴·1200)·(1−exp(−3,2·10⁻⁶))`; metrics-driven node geometry (ink_rect/TextDontClip) – none of this changes.
- **KB window:** template tab has the «Редактировать → Сохранить/Отмена» mode (read-only by default; cancel restores the snapshot; libraries keep direct cell editing – customer decision). Soft colors: selection #93C5FD + dark text (hierarchy tree and lists), primary buttons #3B82F6 (hover #2563EB). Canvas node-state colors (#2563EB «задано», #7C3AED «ок») are LOCKED from session 14 – do not touch.
- **Tests/QA:** smoke 22 blocks, gestures 46 blocks, both green; block 46 is the real-mouse drag harness (see §8 pitfalls for its mechanics).

## 3. CODE MAP (extend, don't break)

- `eta\ui\hierarchy_panel.py` – Tasks 1–3 live here:
  - `_HierTree(QTreeWidget)` – `startDrag` (styled card via `_drag_pixmap` + `_HIER_MIME`; Task 3 reworks the card), `dragEnterEvent` (own drags or the MIME mark), `dragMoveEvent`/`dropEvent` (highlight, accept/ignore, `drop_ok`/`handle_drop` calls; drop events arrive THROUGH THE VIEWPORT – `viewportEvent` forwards them),
  - `drop_ok(drag_it, target_it)` / `handle_drop` – validation/operation seams (tests call them directly),
  - `_drag_pixmap(text)` module function – the Task-3 culprit (rework into a glyph+title card with exact centering, elide, HiDPI),
  - `_selected_deletable_nodes()` – the Task-1 culprit (fallback to `_selected`), `_delete_current()` (Delete key), `_gating_target`, `_on_select` (cause rows return early without touching `_selected`),
  - `_context_menu(pos)` – ПКМ menu for OBJECT rows only («Переименовать…», «Удалить с поддеревом…»; uses `menu.exec` – modal, needs a seam for the new cause item),
  - `_reveal_cause`, `_cause_row_of`, `_scen_row_of`, `_tree_by_id`, `_cause_by_cid` – row/cause lookup helpers (rows must be RE-FETCHED after every rebuild: Qt deletes QTreeWidgetItems on `clear()`). Cause rows get their glyphs in `_add_cause_rows.make` (currently `GLYPH_CAUSE` for both kinds).
- `eta\ui\icons.py` – Task 4: the glyph registry (`ALL_GLYPHS`, `ICON_PALETTE` in theme.py, hand-drawn vector glyphs via QPainter branches, `glyph_icon(name)`); `ICON_PX_HIER = 32` for hierarchy buttons, tree rows use `setIconSize(22)`. The smoke test asserts every glyph in `ALL_GLYPHS` is covered by `ICON_PALETTE` (or `ICON_NEUTRAL_GLYPHS`).
- `eta\ui\theme.py` – `ICON_PALETTE` entries for the two new glyphs; QSS unchanged.
- `eta\ui\main_window.py` – `_update_trash` (trash enablement), `_delete_selection` (priority: canvas node → hierarchy objects → single tree), `_cause_subtree`/`_confirm_remove_chain` (chain collection + confirm seam for cause removal), `_remove_gs_cause`/`_remove_iz_cause` (inspector path), `_on_cause_selected` (cause-row click behavior), `_inspected_tree`.
- Tests: `gesture_test.py` blocks 44–46 are the DnD/cause harness – extend with blocks 47 (Task 1) and 48 (Task 2, + icon-difference assertions from Task 4); `smoke_test.py` icon-palette block extended for the new glyphs + a pixmap unit block for `_drag_pixmap` (pure function, headless-testable).
- Do not touch: engine (`model.py`, `objects.py`, `matrix.py`, `kb.py`), `layout.py`/`render.py`, `kb_window.py`, PDF export, serializer.

## 4. SESSION RULES

1. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference changed behavior; run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop + 2× upscale) the affected artifacts (qa_hierarchy*, qa_window) before declaring the task done.
2. No new external dependencies; PySide6-native only.
3. Style: flat Swiss-utilitarian; new visuals via `theme.py`; `outline: none` where focus rectangles could appear; soft-color palette of 15/1 (#93C5FD selection, #3B82F6 primary buttons).
4. Modal dialogs block offscreen tests: use/extend the existing seams (`_confirm_delete`, `_confirm_multi_delete`, `_confirm_remove_chain`) – any NEW confirmation must be a seam too; the ПКМ menu must be testable without `exec` (build actions separately from showing).
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions not re-asked.
7. Suggested order: Task 1 (deletion correctness – data-loss class) → Task 2 (detach affordances) → Task 4 (glyphs – needed by Task 3's card icon) → Task 3 (drag card consumes the new glyphs).
8. Format-5 compatibility: no file-format changes; all four tasks are panel/UI-layer only.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses.
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Numbers shown to the user: engineering notation («9·10⁻⁵», comma mantissa, Unicode superscripts).

---

## TASK 1. DELETE/TRASH ON A SELECTED CAUSE ROW MUST NOT DELETE THE УЧАСТОК (data-loss bug)

**Defect (customer report):** select any cause row in the hierarchy window and press Delete (or click the trash button) – the entire участок disappears (with all its trees/scenarios).

**Root cause (diagnosed, verify quickly):** `HierarchyPanel._selected_deletable_nodes()` falls back to the panel's last selected OBJECT (`self._selected`) whenever the current tree selection contains no object rows. Cause rows carry no oid and clicks on them never update `_selected`, so the fallback substitutes the previously selected объект (the участок). Both delete paths (Delete key via the viewport filter → `_delete_current`, and `MainWindow._update_trash`/`_delete_selection` → `selected_objects()`) go through this method.

**Requirements (LOCKED):**
1. **Delete on selected cause row(s) deletes THE CAUSES, never an object that is not selected.** Pure-cause selection (single or Ctrl/Shift multi) → remove those causes, each WITH its dependent branches, in ONE confirmation window that lists every chain (reuse the semantics/appearance of `_confirm_remove_chain`; make the new confirm a testable seam). The «Убрать» button in the inspector keeps working unchanged.
2. **The trash button behaves identically**: enabled when cause rows are selected; clicking it deletes the selected causes (with the same confirmation); it must never fall back to `_selected`.
3. **Scenario rows are a safe no-op for Delete/trash**: pressing Delete with a scenario row current does NOTHING (no dialog, no deletion); the trash is disabled (or clicking it does nothing) unless causes/objects are selected. Deleting a whole TREE stays where it is today (Delete/canvas-node or the canvas flow) – do not add tree deletion here.
4. **Mixed selections (Ctrl+click causes + объект rows):** the OBJECT deletion flow runs unchanged and cause rows in the selection are IGNORED (object deletion is the heavier, confirmed operation; causes are deleted only from pure-cause selections). Document this rule in the report.
5. The legacy purpose of the fallback («selection empty after a rebuild/deletion – delete the panel-selected object while alive») must keep working for OBJECT selections: apply the fallback ONLY when the current item is an object row or the selection is truly empty of cause/scenario rows – never when a cause or scenario row is current/selected.
6. **Recommended wiring (keep modals + seams in MainWindow):** `HierarchyPanel` gains a `causes_delete_requested` signal (tree_id, kind, list of cids); the panel collects the selected cause markers (dedupe, order stable); MainWindow handles it with `_cause_subtree` chains + the confirm seam + `_mark_dirty` + `_refresh`, and refreshes the inspector if it was showing the affected tree's node form. `selected_objects()` returns ONLY objects from actual object-row selections (no cause-only fallback). `_delete_selection` priority becomes: canvas node → selected cause rows → selected object rows → single current tree.
7. Full refresh of hierarchy/canvas/matrix/status after deletion (existing `_refresh` path); the former siblings of removed rows keep their positions (no selection jump to an object unless the user selects one).

**Acceptance tests (gesture block 47, real input):**
- Click a cause row → press Delete (real `QTest.keyClick` on the tree viewport) → the confirm seam fires listing the chain → the cause (and its children) is gone, **the участок is alive**, its tree remains with the remaining causes; matrix/Q/status recomputed.
- A dependent cause with children: Delete → one window lists the whole chain; declining the seam leaves everything intact.
- Multi-select two cause rows (real Ctrl+click) → ONE confirm window → both chains removed.
- Trash button with a cause row selected → same behavior; with a scenario row selected → trash does nothing.
- Regression: object rows still delete via Delete/trash exactly as before (block 30/31 flows stay green); mixed selection deletes only the objects.
- The inspector «Убрать» path (block 44) unchanged.

## TASK 2. DISCOVERABLE DETACH: RETURN A DEPENDENT CAUSE TO INDEPENDENT (four ways)

**Defect (customer report):** a cause dropped under another cause cannot be moved back out to become independent. The implemented detach (drop onto the scenario row) is seam-tested but undiscoverable; dropping on empty space does nothing.

**Requirements (LOCKED – the customer chose ALL FOUR affordances):**
1. **Drop onto the scenario row** (existing) – keep; while a cause is dragged over the scenario row, show an explicit «Отцепить» hint near the cursor (QToolTip-style, like the canvas annotation snap hint) in addition to the blue highlight.
2. **Drop onto the owner row** (the участок/наружная установка row that owns the dragged cause's tree) – detaches. Dropping a cause onto ANY OTHER object row stays invalid (red + forbidden cursor): causes never leave their tree.
3. **ПКМ context menu on a cause row** – «Отцепить от родителя» (enabled only when the cause HAS a parent). Object rows keep their existing menu unchanged. Build the menu actions in a testable helper (e.g., `_cause_context_actions(...) -> list[(title, callable)]`); `menu.exec` only in the interactive path – tests invoke the callables directly.
4. **Drop onto empty space OR into the edge zone of a row** – both detach:
   - Empty space: `itemAt(pos)` is None inside the tree viewport → detach (only for a dragged CAUSE; object/tree drags onto empty space remain invalid as today).
   - Edge zones: compute the drop zone from `visualItemRect(target)` and the event position – top 25% of the row = «above», bottom 25% = «below», middle 50% = «on». For a dragged cause: «on» a same-list cause = attach as child (existing); «above»/«below» ANY cause row of the same tree and list = DETACH to top level. This is deliberately NOT reordering (customer LOCKED «no reordering» in the 15/1 Q&A): edge zones never change the order of rows; they only free the dragged cause. Edge-zone drops on rows of another list/tree stay invalid.
5. Feedback rules unchanged otherwise: blue highlight for every valid target (attach or detach), red + ForbiddenCursor for invalid; during dragMove a detach target additionally shows the «Отцепить» hint. After a detach: the cause returns to the top level under the scenario row, the model updates (`parent = None`), and hierarchy/canvas/matrix/Q refresh immediately; the detached row gets selected and scrolled into view (reuse `_reveal_cause`).
6. The math needs no changes (`cause_paths` already treats `parent = None` as a root); serialization unchanged.

**Acceptance tests (gesture block 48, synthetic drag events through the viewport + menu seam):**
- For EACH of the four paths: enter→move→drop (or the menu action) → `cause.parent is None`, the row is a direct child of the scenario row, the scenario count recomputes (chain row splits back into independent rows), the detached row is selected.
- Edge-zone math: a drop position at the top 20% of the parent row's rect detaches; the middle of the same row re-attaches (verify both).
- Invalid cases still rejected with red highlight: cause onto another list's cause (ГС→ИЗ), onto another tree's cause, onto a foreign object row, onto itself/descendant (attach zone).
- Hint shown on hover over scenario row/owner row/edge zone while dragging a cause (assert the tooltip text once).

---

## TASK 3. PROPER DRAG THUMBNAIL (rework `_drag_pixmap`; customer: current pill «выглядит неказисто, текст слегка смещён»)

**Context:** `startDrag` already builds a custom QPixmap card (no Qt default row-grab) – the problem is the card's QUALITY: the text is drawn with a manual `y + 4` shift on top of `AlignVCenter` (visible off-center), padding is asymmetric, there is no icon, no HiDPI handling, titles are hard-truncated at 42 chars instead of pixel-elided, and 0.88 opacity looks washed. Rework it into a clean card per the UI/UX guidance below (edited to the project's flat canon: the guidance's «мягкая тень» option is NOT allowed – use its alternative, a contrasting 1 px border).

**Requirements (LOCKED):**
1. **Layout (no offset):** card = [glyph 16×16] – 8 px gap – [single-line title]; everything vertically CENTERED in one draw rect (`AlignVCenter | AlignLeft`) with NO manual y-shifts; symmetric paddings 6 px vertical / 12 px horizontal; rounded corners radius 6; opacity ~0.95.
2. **Style (flat canon):** light fill harmonized with the theme (#FFFFFF or #EFF6FF), 1 px #3B82F6 border, dark primary text – the card must read clearly over tree rows WITHOUT shadows or gradients (project style bans them).
3. **Title handling:** `QFontMetrics.elidedText(title, Qt.ElideRight, max_text_width)` with the card capped at ~300 px total width (padding + icon + gap + text + padding).
4. **Glyph:** the card carries the dragged row's ACTUAL glyph (Task 4's GS/IZ glyphs for cause rows; the kind glyph for object rows; GLYPH_EVENT_ADD for scenario rows) – so the user sees the row type during the drag. Render it from the same vector glyph machinery (`glyph_icon`) at 16 px.
5. **HiDPI:** create the QPixmap with `devicePixelRatio` set (2×, or the screen's ratio when available) so text and glyph stay crisp; the pixmap's `deviceIndependentSize` is what the width math uses.
6. **Hotspot:** `QPoint(16, height // 2)` – the cursor holds the card near its left edge so the card hangs to the RIGHT of the cursor and does not cover the drop target under it.
7. `startDrag` passes the row's glyph alongside the title (the marker data already knows cause kind; object/scenario rows resolve their glyph by kind/glyph name).

**Acceptance tests:** smoke unit block on `_drag_pixmap(glyph, text)`: returns non-null QPixmap; `devicePixelRatio` set; card width = padding+16+gap+elided-text+padding within tolerance for a short title; a long title elides (width capped, «…» present in a rendered sample or width strictly less than the unelided variant); a new QA artifact `qa_drag_card.png` (the runner renders 2–3 sample cards onto a neutral background) is vision-reviewed: text vertically centered, glyph visible, no clipping.

## TASK 4. PRINCIPALLY DIFFERENT GLYPHS FOR ГС AND ИЗ CAUSE ROWS

**Defect:** GS rows («Образование ГС: …») and IZ rows currently carry the IDENTICAL red `GLYPH_CAUSE` glyph – the two lists are easy to confuse in the hierarchy.

**Requirements (LOCKED concepts, customer-confirmed):**
1. **ГС (Образование горючей среды) = CLOUD** – a gas/fuel-cloud silhouette, **amber #B45309** – the same color the canvas uses for the GS node class (one semantic = one color across surfaces).
2. **ИЗ (Источник зажигания) = FLAME** – a flame silhouette, **red #B91C1C** – the canvas IZ class color. The two shapes (cloud vs flame) are geometrically unrelated and readable at 16–22 px.
3. Implementation: two new hand-drawn vector glyphs in `icons.py` (QPainterPath/strokes consistent with the existing glyph style: `ICON_STROKE` 2.2, antialiased, same visual weight/optical size as sibling glyphs); names e.g. `GLYPH_GS_CAUSE = "gs-cause"`, `GLYPH_IZ_CAUSE = "iz-cause"`; register both in `ICON_PALETTE` (theme.py) with the locked hexes. Wire: `_add_cause_rows.make` picks the glyph by `kind` («gs»/«iz»). The `cause` glyph: if nothing else uses it after the swap (verify by grep), remove it from `ALL_GLYPHS` + `ICON_PALETTE` and update the smoke coverage list; otherwise leave it parked.
4. Hierarchy rows keep the existing 22 px icon grid; the drag card (Task 3) reuses the same glyphs at 16 px. Canvas node styling is NOT touched (its colors already match by design).
5. Same visual weight: neither glyph should dominate the row (balanced bounding boxes, consistent stroke width).

**Acceptance tests:** smoke icon-palette block covers the two new names; gesture block 48 asserts GS rows and IZ rows of one tree carry different icons (e.g., `item.icon(0)` pixmaps differ, or expose/compare via glyph names); QA vision review of a qa_hierarchy crop: amber cloud vs red flame clearly distinguishable at 100 % zoom.

---

## 6. LOCKED DECISIONS (Q&A rounds before this session – normative, not to re-ask)

1. (Task 1) Delete/trash on selected cause rows deletes the CAUSES with their dependent branches, in one confirmation window; the участок is never touched by cause-row deletion.
2. (Task 1) Delete + trash are uniform; scenario rows are a safe no-op; mixed selections delete only the object rows.
3. (Task 1) The `_selected` fallback keeps working for pure-object flows only.
4. (Task 2) Detach works four ways: drop on the scenario row (with «Отцепить» hint), drop on the owner участок/установка row, ПКМ «Отцепить от родителя», drop on empty space or the above/below edge zone of a same-list cause row.
5. (Task 2) Edge zones detach; they do NOT reorder (no reordering anywhere – customer decision from 15/1).
6. (Task 2) Causes never move to another tree/object; such drops stay invalid with feedback.
7. Engine, math, serialization, KB, format – untouched this session.
8. (Task 3) The drag card is FLAT: no soft shadow (the guidance's alternative – a contrasting 1 px #3B82F6 border – is the chosen variant; the project canon bans shadows/gradients); glyph 16 px + 8 px gap + centered single-line title, symmetric 6/12 px paddings, radius 6, opacity ~0.95, `ElideRight` capped ~300 px, `devicePixelRatio` for crispness, hotspot `QPoint(16, height // 2)`.
9. (Task 4) ГС = cloud in amber #B45309, ИЗ = flame in red #B91C1C – the canvas node-class colors (customer-confirmed concepts); vector glyphs in the existing icons.py style, same visual weight, wired per cause kind; canvas node styling untouched.

## 7. FINAL DELIVERABLES

1. All four tasks implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated; new blocks 47 «cause Delete/trash» and 48 «detach paths + glyph difference»; smoke: icon-palette coverage for the two new glyphs + a `_drag_pixmap` unit block); `run_qa.cmd` regenerated and vision-reviewed (qa_hierarchy*, qa_window, plus the NEW `qa_drag_card.png` sample rendering at minimum).
2. Version → **6.5.2** (KB `meta.version` stays «6.1»); README updated where behavior is user-visible (Delete on causes; detach paths; the new glyphs/card are visual – mention briefly).
3. `old prompts (done prompts)\REPORT_SESSION_16.md` (English): per-task summary, files touched, root causes with the exact fix, before→after for every changed user-facing string/menu item/hint/glyph, the drag-card parameters used (sizes, paddings, hotspot) and the exact vector forms/colors of the two glyphs, test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- **Drag events deliver through the VIEWPORT** (`viewportEvent` forwards DragEnter/Move/Drop to the view's handlers); tests must `QApplication.sendEvent(tree.viewport(), ev)`. Constructing the events needs `QMimeData` from **QtCore** (not QtGui) carrying `_HIER_MIME`.
- **Real-mouse drag initiation** (block 46 pattern): `QTest.mousePress` on the viewport + a hand-built `QMouseEvent(MouseMove, …, buttons=LeftButton)` delivered via `sendEvent(viewport)` → asserts `startDrag` fires. `QTest.mouseMove` alone sends buttons=NoButton and never starts a drag. The offscreen platform CANNOT execute `QDrag.exec` – beyond initiation, deliver synthetic drag events.
- **Selectable rows are mandatory** for both drags and click-to-current: never create draggable rows without `ItemIsSelectable`.
- **Stale QTreeWidgetItem references**: every rebuild (`rebuild()`) deletes all items – re-fetch rows by marker (`_cause_row_of`/`_scen_row_of`) after ANY refresh; assertions comparing `it.parent()` identities must use freshly fetched items.
- **Wide-name column**: `visualItemRect` centers can lie outside the viewport – clamp click X into the viewport (block 31 lesson).
- **itemChanged feedback**: block signals while programmatically filling any QTableWidget/QTreeWidget (session-15 KB-library corruption bug).
- Modal dialogs block offscreen tests – seams only; new confirms/menus must be seam-testable.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: keep strong module-level refs for app-level filters/animations; toolbar buttons NoFocus.
- Delete delivery: the tree's viewport event filter is installed EXACTLY ONCE; the rename editor owns Delete while editing (`EditingState` guard in `_delete_current` – keep).
- Selection ↔ rebuild coupling: never rebuild the tree on selection change; never `expandAll()` blindly; preserve per-oid collapsed state; programmatic `setCurrentItem` on a hidden item expands ancestors.
- Letter shortcuts need Latin+Cyrillic twins; QTest keyClick sends key CODES; the Alt+A/Alt+Ф ambiguity warning is known and harmless.
- QTableWidgetItem renders NO HTML; rich cells are QLabel cell widgets; mini-notation for math.
- Offscreen QA: `QT_QPA_FONTDIR=C:\Windows\Fonts`; stderr noise is harmless; never leave a modal open in a test.
- Vision QA reads downscaled images – crop and 2× upscale before asking glm-5.3-flash; programmatic checks beat vision estimates. A drag pixmap cannot be captured mid-drag offscreen – render sample cards directly via `_drag_pixmap` into a QA artifact instead.
- HiDPI: `QPixmap.setDeviceRatio`/`QPixmap(devicePixelRatio=…)` before painting; compare `deviceIndependentSize()` in tests, not raw `width()`.
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
- Cyrillic/KB edits: byte-safe temporary Python scripts only (not needed this session, but the rule stands); no em-dash anywhere.
