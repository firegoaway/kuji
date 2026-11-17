# SESSION 16 REPORT – Kuji 6.5.2

Date: 13.11.2026. Base: v6.5.1 (sessions 1–15/1).
Subject: defect-fix + interaction-polish session, four tasks: the
cause-Delete data-loss bug, discoverable detach (four ways), distinct
ГС/ИЗ cause glyphs, drag-thumbnail rework. All LOCKED Q&A decisions
implemented as specified; none re-opened; no clarifying questions were
needed (the prompt locked every ambiguity). Version → **6.5.2**; KB
`meta.version` stays **«6.1»** (no KB edits this session); engine,
math, serialization and format 5 untouched.

**Acceptance:** `smoke_test.py` – PASS (22 blocks: palette block 18
extended with `gs-cause`/`iz-cause` + «cause»-removed assertions; NEW
block 21 «карточка переноса» – `_drag_pixmap` unit checks);
`gesture_test.py` – PASS (48 blocks: updated block 15(в) – canvas
Delete now requires a USER-CLICK node selection; NEW blocks 47
«cause Delete/trash» and 48 «detach paths + glyph difference»).
`run_qa.cmd` regenerated (app 6.5.2) incl. the NEW `qa_drag_card.png`
artifact; vision review passed (details below). Implemented in the
suggested order 1 → 2 → 4 → 3, tests+QA green after every task.

## Task 1 – Delete/trash on a selected cause row deletes THE CAUSES, never the участок

* Root cause confirmed exactly as diagnosed:
  `HierarchyPanel._selected_deletable_nodes()` fell back to the
  panel's last selected OBJECT (`self._selected`) whenever the tree
  selection contained no object rows. Cause rows carry no oid and
  clicks on them never update `_selected`, so selecting a cause row
  and pressing Delete (viewport filter → `_delete_current`) or
  clicking the trash (`_update_trash` → `selected_objects()` →
  `_delete_selection`) silently substituted the previously selected
  объект – almost always the участок owning the tree.
* Fix (wiring per the recommendation, LOCKED semantics kept):
  1. `HierarchyPanel` splits selection inspection into
     `_selection_objects()` (objects of real object-row selections,
     no fallback), `_selection_causes()` (dedup + stable
     (tree_id, kind, cid) markers), `selected_causes()`,
     `_scenario_rows_selected()`, `has_tree_rows_selected()`.
     `_selected_deletable_nodes()` keeps the legacy fallback ONLY
     for pure object flows: it is blocked whenever the selection
     contains cause rows or scenario rows (or the current row is a
     scenario). New signal `causes_delete_requested = Signal(list)`
     carries the WHOLE marker list (not one (tree_id, kind) group)
     so a cross-tree/cross-list multi-selection still gets ONE
     confirmation window.
  2. `_delete_current()` (Delete key): objects → object flow
     unchanged; pure-cause selection → `causes_delete_requested`
     (causes deleted with dependent branches); scenario rows →
     safe no-op (no dialog, no deletion); empty selection → legacy
     `_selected` fallback while the object is alive.
  3. MainWindow `_on_causes_delete_requested` →
     `_delete_selected_causes(markers)`: collects every chain
     (roots selected + descendants; a descendant selected together
     with its parent is already inside the parent's chain), ONE
     confirmation via the NEW testable seam
     `_confirm_remove_causes(chain, kb)` (appearance/semantics of
     `_confirm_remove_chain`: chain list with «(зависимая ветвь)»
     marks, «Удалить» default), then removes by cid, `_mark_dirty`,
     full `_refresh` (hierarchy/canvas/matrix/Q/status), and
     rebuilds the inspector form if it was showing an affected
     tree's gs/iz node (new accessor
     `InspectorPanel.current_node_kind()`).
  4. `_delete_selection` priority is now: pure cause selection →
     USER-CLICKED canvas node (tree deletion, canvas flow) →
     selected object rows (mixed selections delete ONLY the
     objects – LOCKED) → single current tree, and the single-tree
     fallback fires ONLY when the hierarchy selection has no
     scenario/cause rows. NEW `_canvas_sel_by_click` flag:
     a cause-row click programmatically dashed-selects the canvas
     node (`controller.select_node`), which must NOT count as a
     canvas choice – otherwise the trash would delete the tree.
     The flag is set by `_on_canvas_node` (user click →
     `select_node` + `node_clicked`), cleared by
     `_on_cause_selected` and `_on_canvas_empty`. This is the one
     deliberate deviation from the prompt's literal priority order
     («canvas node → cause rows»): LOCKED requirement 2 (trash on
     cause rows deletes the causes) wins over the dashed artifact;
     tree deletion via a real canvas click is fully preserved.
  5. `_update_trash`: enabled for cause rows selected, real object
     rows (non-territory), or a user-clicked canvas node; a pure
     scenario-row selection disables the trash (LOCKED no-op).
  6. After cause deletion former siblings keep their positions
     (full rebuild; the deleted marker simply does not restore –
     no selection jump to an object).

## Task 2 – discoverable detach: a dependent cause can be freed FOUR ways (all LOCKED)

* `drop_ok(drag, target)` is now a thin wrapper over the NEW
  `drop_kind(drag, target, pos=None) -> "attach" | "detach" | None`;
  `handle_drop(drag, target, pos=None)` consumes the kind. `pos`
  (viewport coordinates) decides the drop ZONE inside a row via the
  new `_drop_zone()`: top 25 % «above», bottom 25 % «below»,
  middle 50 % «on»; programmatic seam calls without a position get
  «on» – all session-15 seam tests unchanged and green.
* The four ways (each verified in gesture block 48):
  1. **Scenario row** (existing): drop → detach; while dragging over
     it a mini-hint «Отцепить» appears near the cursor
     (`scene_tip`, the same machinery as the canvas «Привязать»
     hint) in ADDITION to the blue highlight.
  2. **Owner row** (участок/наружная установка owning the dragged
     cause's tree): drop → detach; any OTHER object row stays
     invalid (red + ForbiddenCursor) – causes never leave their
     tree.
  3. **ПКМ on a cause row**: «Отцепить от родителя», enabled only
     when the cause HAS a parent. Actions are built in the testable
     helper `_cause_context_actions(it) -> list[(title, callable)]`
     operating through `_detach_cause(tree_id, kind, cid)`; `exec`
     lives only in the interactive `_context_menu` path. Object
     rows keep their menu unchanged («Переименовать…» /
     «Удалить с поддеревом…»).
  4. **Empty space or the above/below edge zone of a same-list,
     same-tree cause row**: `itemAt(pos) is None` → detach (causes
     only; object/tree drags onto empty space stay invalid);
     «above»/«below» (edge quarters) of a same-list cause row →
     detach, edge zones of another list/tree → invalid. Edge zones
     NEVER reorder (LOCKED): only `parent = None` is ever written,
     the row returns to its position among the roots.
* Feedback unchanged otherwise: blue highlight for every valid
  target, red + ForbiddenCursor for invalid; after a detach the
  model updates immediately, the row is selected and scrolled into
  view (`_reveal_cause`), and the status bar shows
  «Причина отцеплена – независимая». Math untouched
  (`cause_paths` already treats `parent = None` as a root).
* Harness lesson (documented in the test): a synthetic QDropEvent
  reaches `dropEvent` ONLY after a QDragEnterEvent/QDragMoveEvent
  pair put the view into drag state – block 48 always delivers
  enter → move → drop exactly like real DnD.

## Task 4 – distinct glyphs for ГС and ИЗ cause rows (done before Task 3: the card consumes them)

* TWO new hand-drawn vector glyphs in `icons.py` (24×24 system,
  `ICON_STROKE` 2.2, antialiased, same visual weight):
  * **ГС = cloud** (`GLYPH_GS_CAUSE = "gs-cause"`): a closed
    QPainterPath outline – flat base from (5.0; 17.5) to (17.4;
    17.5), left rise quad(1.8; 17.5 → 2.6; 13.2), left bump
    quad(3.0; 8.0 → 8.2; 8.2), central bump quad(9.6; 3.6 →
    13.8; 5.2), right bump quad(19.6; 4.2 → 20.2; 9.8), right
    descent quad(22.4; 10.8 → 21.0; 14.6), corner quad(20.4; 17.5
    → close). Color **#B45309** (amber, the canvas GS node class).
  * **ИЗ = flame** (`GLYPH_IZ_CAUSE = "iz-cause"`): outer
    teardrop outline from the tip (12.0; 2.4) right side
    quad(17.6; 7.8 → 18.0; 12.8) bottom quad(18.4; 19.6 →
    12.0; 21.6) left quad(5.6; 19.6 → 6.0; 12.8) up quad(6.4;
    7.8 → close), plus an inner tongue (thin stroke 1.7):
    (12.0; 10.8) quad(15.0; 13.4 → 14.4; 16.0) quad(12.0; 17.9 →
    9.6; 16.0) quad(9.0; 13.4 → close). Color **#B91C1C** (red,
    the canvas IZ node class). The tongue was enlarged once after
    the first vision pass (it collapsed to a dot at 22 px) – now a
    visible hollow at row size.
* `ICON_PALETTE` (theme.py): `gs-cause = #B45309`,
  `iz-cause = #B91C1C`; the unified `cause` entry, the
  `GLYPH_CAUSE` constant, its drawing branch and its `ALL_GLYPHS`
  slot are REMOVED (grep confirmed no other consumer; smoke
  asserts the coverage and the removal).
* Wiring: `_add_cause_rows.make` picks the glyph by kind; rows
  keep the 22 px icon grid; canvas node styling untouched (colors
  already matched by design). Hierarchy rows and the drag card now
  share one semantic color language with the canvas.

## Task 3 – drag thumbnail: `_drag_pixmap` reworked into a card

* The old pill's defects are gone: the manual `+4 px` y-shift on
  top of `AlignVCenter`, asymmetric padding, no icon, no HiDPI,
  the hard 42-char truncation, 0.88 opacity.
* New `_drag_pixmap(glyph, text, dpr=2.0)` (LOCKED parameters):
  * Layout `[glyph 16×16] – 8 px gap – [single-line title]`,
    everything vertically centered in ONE draw rect
    (`AlignVCenter | AlignLeft`, QRectF float overload, no manual
    shifts); symmetric paddings 12 px horizontal / 6 px vertical;
    height = max(text height, 16) + 2×6.
  * Style (flat canon): fill **#EFF6FF**, contrasting 1 px
    **#3B82F6** border (the guidance's alternative to the banned
    «мягкая тень»), dark primary text #0F172A, radius 6,
    opacity 0.95; no shadows, no gradients.
  * Title: `QFontMetrics.elidedText(…, Qt.ElideRight, …)` with the
    card capped at **300 px** logical width.
  * HiDPI: the QPixmap is created with `devicePixelRatio` (the
    screen's ratio via `_HierTree._drag_dpr()`, fallback 2×); the
    glyph is rasterized by `glyph_icon` at 16 × ratio px with its
    own DPR; width math uses `deviceIndependentSize`.
  * Hotspot `QPoint(16, int(h) // 2)` – the card hangs to the
    RIGHT of the cursor and does not cover the drop target.
  * `startDrag` passes the row's actual glyph via the NEW
    `HierarchyPanel._row_glyph(it)`: cause rows → gs-cause /
    iz-cause by kind, scenario rows → event-add, object rows →
    the kind glyph (module-level `_kind_glyph`, now shared with
    `_make_item`).

## Before → after (changed user-facing strings / menus / hints / glyphs)

* Cause deletion confirm (NEW, seam `_confirm_remove_causes`):
  window «Удаление причин», text «Удалить выбранные причины с
  зависимыми ветвями (N)?», informative text – the chain list
  («• <название> (зависимая ветвь)», ≤10 + «… и ещё K»), buttons
  «Удалить» (default) / «Отмена».
* Delete on a cause row: before – the whole участок deleted after
  a confirm the user clicked through; after – only the selected
  causes with their dependent branches, участок alive.
* Trash with a cause row selected: before – deleted the участок;
  after – deletes the selected causes (same window). Trash with a
  scenario row selected: before – enabled, deleted the tree;
  after – disabled (safe no-op; tree deletion stays on the canvas
  node selection).
* Status messages: NEW «Причина отцеплена – независимая» (any
  detach); «Зависимая ветвь: Q = Q(родитель) × Q(потомок)» and
  «Дерево «…» перемещено на «…»» unchanged.
* Context menu on a cause row (NEW): «Отцепить от родителя»
  (dependent causes only; independent causes and object rows –
  no new items; object menu unchanged).
* Drag hint (NEW): «Отцепить» near the cursor over any valid
  detach target (scenario row, owner row, edge zone) while
  dragging a cause.
* Cause-row glyphs: before – identical red «gear+arrow»
  (`cause`, #B91C1C) on BOTH lists; after – ГС amber cloud
  (#B45309) / ИЗ red flame (#B91C1C); the `cause` glyph is
  removed from the app entirely.
* Drag visual: before – translucent #DBEAFE pill, ≤42 chars,
  1.2 px border, no icon, no DPR, hotspot at center; after – the
  flat card described in Task 3 with the row's glyph.

## Files touched (session 16)

eta/ui/hierarchy_panel.py (module docstring; `_drag_pixmap` card
+ parameter constants; `_kind_glyph`; `_row_glyph`; `_HierTree`
hint state/methods + zone-aware dragMove/drop + DPR-aware
startDrag; selection inspection split; `causes_delete_requested`;
`_drop_zone`; `drop_kind`/`drop_ok`/`handle_drop` with detach;
`_detach_cause`; `_cause_context_actions`; `_context_menu` for
cause rows; gs/iz glyphs in `_add_cause_rows.make`) ·
eta/ui/main_window.py (`_canvas_sel_by_click` + maintenance in
`_on_cause_selected`/`_on_canvas_node`/`_on_canvas_empty`;
signal wiring; `_cause_chain_from`; `_on_causes_delete_requested`;
`_delete_selected_causes`; `_confirm_remove_causes`;
`_delete_selection`/`_update_trash` rework) ·
eta/ui/inspector_panel.py (`current_node_kind()` accessor) ·
eta/ui/icons.py (`GLYPH_GS_CAUSE`/`GLYPH_IZ_CAUSE` + cloud/flame
branches; `GLYPH_CAUSE` removed; `ALL_GLYPHS`) ·
eta/ui/theme.py (`ICON_PALETTE`: gs-cause/iz-cause, `cause`
removed) · eta/__init__.py (6.5.2) · smoke_test.py (block 18
extended + new block 21) · gesture_test.py (block 15(в) updated;
new blocks 47, 48) · visual_qa_runner.py (qa_drag_card.png
section) · README.md · qa_artifacts (regenerated, +qa_drag_card).

## Test results / Visual QA

* smoke_test.py – PASS: 22 blocks; block 18 asserts both new
  palette entries with the locked hexes and the «cause» removal;
  new block 21 asserts the card geometry from font metrics
  (width = 2×12 + 16 + 8 + advance within 2 px, height =
  max(fm.height, 16) + 12, hotspot (16, h//2), DPR 2.0, long
  title capped ≤ 300 px and strictly narrower than the unelided
  variant, glyph adds exactly 24 px of width).
* gesture_test.py – PASS: 48 blocks ending `GESTURES PASSED`.
  Block 47 (real input): real mouse click on a cause row + real
  `QTest.keyClick` Delete → the seam fires with the full chain,
  causes gone, участок/tree/remaining causes alive, status
  recomputed; declining leaves everything intact; real Ctrl+click
  of two rows → ONE window → both chains removed; trash identical;
  scenario row → trash disabled + Delete no-op; mixed selection →
  only the object deleted. Block 48: for EACH of the four detach
  paths enter→move→drop → `parent is None`, direct child of the
  scenario row, scenario count recomputed (chain 1 row → 2 rows),
  detached row selected; edge-zone math (top 20 % detaches, middle
  re-attaches); hint text «Отцепить» asserted over scenario row,
  owner row and edge zone; invalid targets (other list, other
  tree, foreign object, self, descendant, attach zone) rejected;
  empty-space detach works for causes and stays invalid for
  object/tree drags; GS-row and IZ-row icons of one tree differ
  (pixmap compare) and are identical within a list. Block 15(в)
  now proves canvas Delete through a user-click node selection
  (`select_node` + `node_clicked`, as a real LMB click does).
* run_qa.cmd regenerated: app 6.5.2, 3 trees, pdf_rendered true.
  Vision review (glm-5.3-flash, crops + 2× upscale):
  * qa_hierarchy crop (2×) – «Образование ГС» row carries the
    amber cloud, «Отказ …» rows carry the red flame with the
    inner tongue visible; shapes AND colors distinguishable at a
    glance; no rendering defects (the long-name ellipsis is the
    designed horizontal-scrollbar behavior).
  * qa_drag_card.png (NEW; sample cards rasterized 1:1 at DPR 2
    on a neutral #E2E8F0 background: GS card, IZ card, long-title
    object card) – glyphs visible at the left, title vertically
    centered, symmetric padding, 1 px border with radius 6, the
    long title elided with «…» and the card capped ≈300 px.
  * qa_window – three-panel layout intact, all tree icons render,
    status bar shows v6.5.2, no glitches.

## Known issues / notes

* Mixed selections (causes + objects) delete ONLY the objects by
  design (LOCKED): object deletion is the heavier, confirmed
  operation; causes are deleted only from pure-cause selections.
* The cause-row click's dashed canvas selection no longer makes
  Delete/trash delete the tree; tree deletion remains on an
  explicit canvas-node click (the canvas flow, unchanged).
* A scenario row selected together with a previously user-clicked
  canvas node still enables the trash (the canvas selection is
  the user's explicit choice) – tree deletion then goes through
  `_confirm_tree_delete` as before.
* run_qa.cmd may exit 1 on teardown after writing all artifacts
  (offscreen quit race, cosmetic – as in previous sessions); this
  run exited 0.
* Offscreen DnD: a synthetic QDropEvent must be preceded by
  enter+move events or the view never enters drag state – now
  documented in block 48 for future harnesses.
