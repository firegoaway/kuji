# SESSION 12 REPORT – Kuji 6.2.0

Date: 10.11.2026. Base: v6.1.0 (sessions 1–11).
Subject: regression-fix + design-polish session, fifteen tasks –
interaction regressions from the session-10 rewrite (Delete, node
drag/pan, sticky/free view modes, clipped hierarchy names) plus the
confirmed design changes (sibling-add, combo popups, informative and
adaptive tooltips, inspector breathing room, splitters, node-body
redesign with word wrap, presence-as-probability). All LOCKED Q&A
decisions implemented as specified; no locked decision was reopened.
Two clarifying interpretations pre-confirmed by the customer before the
session (Task 13 rule applied to all node kinds; Task 15 single
probability field with one-time migration) were implemented verbatim.

**Acceptance:** `smoke_test.py` – PASS (18 blocks; block 2 rewritten to
the probability semantics + migration cases, block 14 extended with the
`node_offsets` round-trip, block 16 extended with body/word-wrap/offset
assertions); `gesture_test.py` – PASS (19 blocks: 13 existing + new
blocks 14–19 – sibling-add, Delete paths and trash enable, hierarchy
h-scrollbar with pixel-intermediate Shift+wheel values, LMB node drag
with offset commit + format-5 round-trip + «Авторазметка», sticky/free
exclusivity + clamp, presence inspector field); `run_qa.cmd` – PASS,
artifacts regenerated (three new: qa_hierarchy/qa_hierarchy2,
qa_tooltip, qa_combo) and vision-reviewed with glm-5.3-flash (2×–3×
crops for pixel truth; ≤4 iterations per artifact, actual ≤2).
Version → **6.2.0**; KB `meta.version` stays **«6.1»** (no KB data
edits this session).

## Task 1 – hierarchy names never clipped + design pass

* Column 0 of the hidden-header tree is now sized to
  max(content, viewport) after every rebuild / expand / collapse /
  rename / panel resize (`HierarchyPanel._sync_column_width`,
  `hierarchy_panel.py`); content width measured via tree font metrics
  (indentation × depth + icon column + widest item text + padding).
  With `ElideNone` + `ScrollBarAsNeeded` the horizontal scrollbar
  engages exactly when content is wider than the panel; the inline
  rename editor inherits the column width (QTreeView default editor
  geometry).
* Design pass (LOCKED): ICON_PX_HIER 28 → 32 on the six toolbar
  buttons, `setIndentation(20)`, tree `setIconSize(22)`, row
  min-height 30 (icon-driven rows ≈ 34 px), subtle hover
  (`#E2E8F0`) and selected (ACCENT bar) states via new QSS
  `QTreeWidget#hierTree` block in `theme.py`. Toolbar layout and all
  behaviors untouched.
* Vision: qa_window/qa_hierarchy – colored glyphs clearly visible,
  indentation readable, h-scrollbar present; qa_hierarchy2 (scrolled
  right) shows the end of the long demo name with no right-edge
  clipping.

## Task 2 – inspector section separators breathing room

`InspectorPanel._section` (`eta/ui/inspector_panel.py`): +6 px spacer
before the HLine, +4 px after it (LOCKED «совсем чуть-чуть»: total per
side ≈ +5 px incl. layout spacing). Everything else identical.
Vision: qa_inspector_building – captions no longer touch the lines.

## Task 3 – adaptive tooltip bubble

`eta/ui/modern_tooltip.py`:

* `ModernTooltip.apply_html()` replaces the fixed `TIP_MAX_W`
  text width: ideal (unwrapped) document width clamped to
  [≈ padding + 24 chars, TIP_MAX_W]; `paintEvent` and the controller
  cache path use the same chosen width. Observed bubble widths in QA:
  175 px (one-word tip) … 580 px (long text at the clamp).
* Wrapping: `wrap_tip_line` – whole words only, ≤85 characters
  (TIP_WRAP_CHARS); a single word longer than the line is split by
  syllables (`_split_long_word`, break after a vowel – «мо-ло-ко»,
  «ре-зер-ву-ар») with the en-dash «–» inserted at the break.
* Rich text (existing HTML tooltips): `_wrap_rich_line` wraps by whole
  words on the visible text; at each break the currently open inline
  tags are closed and re-opened on the next line
  (`<b>…</b>` stays bold across lines).
* `compose_tip_html` now pre-wraps both plain (via `wrap_tip_line` +
  `math()` per line, replacing `math_html_lines`'s 88-char wrap) and
  HTML input.
* Verified: unit checks (max line 81 chars on the QA long tooltip,
  syllable splitting, tag re-opening) + vision qa_tooltip (compact
  short bubble, 4-line wrapped long bubble). A vision claim of
  «>100-char lines» was refuted programmatically (all lines ≤85).

## Task 4 – sibling-add

`hierarchy_panel.py`: new `_gating_target()` – the object the toolbar
gates on: the selected object; a scenario row or «Группа сценариев»
counts as its owner Участок/установка. `_sync_toolbar()` enables
«Добавить X» when the target IS an X (sibling under the same parent)
or a valid parent of X (child, as before); «Наружная установка» keeps
the territory-only rule, «Территория» is always enabled. `add_kind()`
resolves the parent accordingly (target.kind == kind → target.parent;
territory sibling → root). Hint texts updated («выделите помещение или
участок», «…здание, отсек или помещение» etc. in the toolbar and in
`objects.py::add_child`). Gesture block 14: Участок selected →
«Добавить участок» enabled → new sibling under the same room; building
sibling under the same territory; outdoor disabled unless territory;
scenario-row selection enables the owner's «Добавить участок».

## Task 5 – combo popup vertical hit area

`controls.py::wide_combo`: `QListView.setSpacing(4 → 2)`; new QSS
`QComboBox QAbstractItemView::item { padding: 7px 8px; }` in
`theme.py`. Vision qa_combo: items ~28–32 px tall, minimal gaps,
whole height clickable.

## Task 6 – adaptive combo popup width

`_patched_show_popup` now computes the widest item text via view font
metrics (+34 px for item padding/frame/scrollbar allowance) and clamps
to [button width, 2× button width] (COMBO_POPUP_K stays 2.0); longer
items wrap by words inside the popup (existing behavior). Dead
duplicate `_on_shown` removed. Vision qa_combo: popup ≈ button width
for short items, no empty space. Applies app-wide (all `wide_combo`).

## Tasks 7/7.1 – informative tooltips

Root cause: `ToggleSwitch.__init__` did `setToolTip(text)` – every
switch duplicated its own label. Fix: the default is REMOVED
(`switch.py`); sites set real content or nothing:

* «Аварийная вентиляция» (room form): «При включении аварийной
  вентиляции условная вероятность сохранения взрывоопасной
  концентрации снижается до P_ост = 1/(A·T + 1). Делитель массы – по
  ГОСТ Р 12.3.047-98, прил. А, п. А.2.5.»
* «Молниезащита» (building + outdoor forms): «При включении
  молниезащиты частота поражения здания молнией умножается на
  (1 − η_МЗ). Надежность защиты по категориям I–IV – 0,98, 0,95, 0,90,
  0,80 (СО 153-34.21.122-2003, табл. 2.2).»
* Pedal switches in the node forms get the informative `tooltip` text
  from the KB record when present (`_pedal_block`), otherwise NO
  tooltip (per 7.1 – never a label duplicate). «Огненный шар» and the
  export-dialog switch already had informative tooltips and are
  unchanged.

## Task 8 – hierarchy horizontal scrollbar (smooth, Shift+wheel)

Root cause confirmed: hidden-header `QTreeWidget` keeps column 0 at
viewport width, so the scrollbar range never becomes non-zero – fixed
by `_sync_column_width` (Task 1 mechanism). `ScrollPerPixel` vertical
+ horizontal was already set (session 11) – re-verified. The app-wide
`ScrollWideFilter` drives the bar via Shift+wheel; its horizontal
branch now uses the same smooth per-pixel animation as the vertical
(`_smooth_scroll`, 60 px/notch, OutCubic) instead of a discrete 3-step
jump – gesture block 16 asserts pixel-intermediate values (observed
e.g. `[0, 22, 32, 42, 50, 55, …]`, scrollbar range 252 px for the long
demo name).

## Task 9 – resizable panel boundaries (splitters)

`main_window.py`: the fixed `_panel()` QHBoxLayout is replaced by a
horizontal `QSplitter` (hierarchy | center | inspector); minimum widths
320/500/360 kept as `setMinimumWidth`, `setCollapsible(false)` each,
stretch center 1 / sides 0, initial sizes 320/500/360. Handle QSS
strengthened after the first vision pass (7 px slate #94A3B8 base,
ACCENT hover, #1D4ED8 pressed) – handles now clearly visible and
comfortably grabbable. Splitter state persists in QSettings
(`ui/splitter`, saved in `closeEvent`, restored in `_restore_ui` when
`restore_ui` is true; hermetic ini in tests). Pop-out «Документ» and
all resize behaviors unaffected (gesture block 10, vision qa_window).

## Task 10 – Delete key + «Удалить выделенное» restored

Root causes confirmed and fixed:

1. `set_trash_enabled()` was never called → new
   `MainWindow._update_trash()`: enabled when the hierarchy selection
   is a deletable object (not the territory root), OR a canvas node is
   selected, OR a scenario is selected («its» tree). Called from
   `_refresh`, `_on_canvas_node`, `_on_canvas_empty`.
2. The window-level `act_del` shortcut never fires inside the tree
   (the view claims Delete via ShortcutOverride for inline editing and
   keeps focus in its viewport). Fix in `hierarchy_panel.py`:
   `_delete_current()` + Delete handling in the tree-viewport event
   filter (fires before the view sees the key); an additional
   `QShortcut(Delete, WidgetShortcut)` on the tree is kept as a second
   path. While the rename editor is open the key goes to the editor
   (not the viewport) and edits text – gesture block 15(б) verifies.
3. Canvas: Delete on a selected node deletes the OWNING tree via the
   existing `_confirm_tree_delete` seam (LOCKED #5) – viewport event
   filter on the canvas emits `delete_requested` →
   `MainWindow._delete_selection` (reworked priority: canvas node →
   owner tree; hierarchy object; single current tree).
* Two latent bugs found by the new tests and fixed: (a) item views
  keep focus in the viewport, so shortcuts must live there;
  (b) after `add_kind`, `currentItem` was empty (select_object ran
  before the rebuilt tree contained the new node) – `add_kind` now
  re-selects the new node after rebuild, so Delete immediately after
  adding works.
* Gesture block 15: tree Delete deletes via the seam; editor Delete
  leaves the object alive; canvas Delete removes the dust tree only;
  trash transitions disabled (territory) → enabled (building) →
  enabled (canvas node).

## Task 11 – canvas node drag + pan + auto-layout

`eta/ui/canvas.py` rewritten (mouse handling + gestures integration):

* LMB on a node: press → threshold 5 px → drag (node + its edges move
  live; edge endpoints/control points shift on the dragged side);
  release without move → select + `node_clicked` (this signal was
  never emitted before – click-to-inspector is restored). LMB on empty
  space and middle button: camera pan (scrollbar-based). Wheel: smooth
  zoom to cursor via the gestures mixin (`_init_gestures()` – its call
  was lost in session 10, which silently killed pinch/tap/middle-pan;
  now restored); zoom buttons animate around the viewport center.
* Persistence: `TreeModel.node_offsets: {slot: [dx, dy] | None}`
  (format 5 stays 5; field written only when non-empty, read
  optionally). **Slot keys are the real per-tree node ids
  `substance | oxidizer | gs | iz | fire`** (the session prompt's
  «presence1/presence2» do not exist anywhere in the codebase –
  documented deviation, semantics unchanged). On release,
  `_commit_node_drag` stores offset = previous + drag delta, rebuilds
  both scenes via `controller.rebuild_last()` (camera not re-fitted),
  clamps to sticky bounds and emits `tree_offsets_changed` → dirty
  flag.
* Offsets are applied INSIDE `compute_layout` (`layout.py`) before
  edges are built, so canvas, schematic doc-view and PDF stay WYSIWYG;
  the scene rect is now the union of actual node rects + headers
  (sticky clamp and fit see dragged extents).
* «Авторазметка»: new toolbar button next to «Показать всё»
  (`left_toolbar.py`), new neutral glyph `auto-layout` in `icons.py`
  (registered in ALL_GLYPHS + ICON_NEUTRAL_GLYPHS – smoke icon-palette
  block passes), signal → `MainWindow._auto_layout()` clears
  `node_offsets` of the current trees, refresh + fit.
* Gesture block 17: synthetic QTest press/move(+40,+18)/release on the
  gs node → `node_offsets["gs"] ≈ [40/zoom, 18/zoom]` (observed
  [38.27, 17.22]); save → load round-trip equal; «Авторазметка» →
  offsets None. Smoke block 14/16 assert serialization round-trip and
  exact layout translation.

## Task 12 – sticky / free view modes restored

Root cause confirmed: `ViewportToolbar.mode_requested` was emitted by
both buttons but never connected. Fix (`main_window._wire`):
`lt.mode_requested` → `canvas.set_mode(mode)` + `lt.set_mode(mode)` +
`canvas.clamp_to_mode()` (new public alias). Buttons are an exclusive
checked pair; sticky default on startup. Gesture block 18: click
«Свободный» → free checked / sticky unchecked / `canvas.mode() ==
"free"`; camera pushed to the far corner; click «Липкий» → clamp
returns the visible rect inside scene bounds + 40 px margin.

## Task 13 – node body redesign (LOCKED #7)

`eta/core/layout.py::_body_spec` + `render.py`: under each header ONLY
a count caption and the formula.

* «Возникновение пожара/взрыва»: «Всего: N сценариев» (correct Russian
  plural via `_plural`) + «ΣQ = X год⁻¹» (new style `total`: mono,
  bold, F_FORMULA = 12 px – «+2 px over meta», set after the first
  vision pass said 11 px read too weak).
* «ГС»: «Всего: N разновидностей»; «ИЗ»: «Всего: N источников»;
  N = 0 → «не задано» in the cutoff gray (style `muted`).
* Presence nodes: «вероятность присутствия: 0,050» (Task 15 label).
* No per-line cause/scenario lists on nodes anywhere (they remain in
  the inspector, «Группа сценариев» and the matrix). The node design
  (headers, accent bars, palette) unchanged; heights shrink with the
  shorter bodies.
* `NodeGeo` gained `body_styles`; `render.py` draws per-style
  fonts/colors (meta/muted/total); canvas and PDF share it (WYSIWYG).
* Smoke block 16 asserts the exact body strings; vision confirmed the
  counters-only bodies and no clipping.

## Task 14 – whole-word wrapping, no mid-word clipping

`layout.py`: new `wrap_words()` (words only, NO ellipsis/truncation);
`make_node` grows the node width to the longest wrapped line and to
the longest WORD (cap MAX_NODE_W is raised when a word is longer –
words are never cut); heights per style fonts. Vision on 2× canvas
crops: all five headers fully readable, «(ГГ)», «(ОК)», «(ГС)», «(ИЗ)»
parentheses intact, «Возникновение пожара/взрыва» complete; smoke
block 16 asserts no line and no word exceeds its node's text budget.

## Task 15 – presence = «вероятность присутствия»

* `model.py::Presence`: single `value` (0–1), `q() = clamp(value)`;
  `to_dict()` writes `{"value": …}` only; `from_dict()` migrates old
  data once: `time` → value as is (доля года IS the probability),
  `freq` → `1 − e^(−f)`. Engine formula `Q_сценария = Q_вещество ·
  Q_ОК · …` untouched; confectionery example stays exact (smoke
  block 3 unchanged and passing).
* Inspector: mode combo removed; single spin field «Вероятность
  присутствия» (0–1, 3 decimals, step 0.05) with the specified
  tooltip; note line «Вероятность присутствия – множитель в
  Q_сценария (0–1)».
* Node label: «вероятность присутствия: 1,000» (3 decimals, comma).
* PDF report: «Наличие вещества: вероятность присутствия 1; наличие
  ОК: вероятность присутствия 1» – `MODE_RU` removed; vision
  confirmed no «время/частота присутствия» wording remains.
* Smoke block 2 rewritten (probability + both migration cases);
  gesture block 19 checks the inspector field and that no
  presence-mode combo items remain.

## Files touched (session 12)

eta/__init__.py (6.2.0) · eta/core/model.py (Presence, node_offsets)
· eta/core/layout.py (word wrap, body styles, offsets, union scene
rect) · eta/core/objects.py (hint strings) · eta/ui/theme.py (QSS:
hierTree, combo items, splitters; F_FORMULA; ICON_PX_HIER 32;
auto-layout neutral) · eta/ui/controls.py (wide_combo Tasks 5/6)
· eta/ui/switch.py (no default tooltip) · eta/ui/inspector_panel.py
(sections spacing, presence field, informative tooltips)
· eta/ui/modern_tooltip.py (adaptive width, 85-char word/syllable
wrap) · eta/ui/hierarchy_panel.py (column width sync, design hooks,
sibling gating, Delete, add_kind current fix) · eta/ui/main_window.py
(splitter + persistence, delete/trash wiring, mode wiring,
auto-layout, offsets dirty) · eta/ui/canvas.py (rewrite: drag/pan,
gestures init, viewport filters, offsets commit) · eta/ui/gestures.py
(untouched) · eta/ui/left_toolbar.py («Авторазметка») ·
eta/ui/icons.py (auto-layout glyph) · eta/ui/render.py (body styles)
· eta/ui/scroll.py (smooth horizontal) · eta/export/pdf_export.py
(presence wording) · smoke_test.py · gesture_test.py (blocks 14–19)
· visual_qa_runner.py (long demo name, qa_hierarchy/2, qa_tooltip,
qa_combo) · README.md · qa_artifacts (regenerated).

## Test results / Visual QA

* smoke_test.py – PASS, 18 blocks: KB 6.1 canon, presence probability
  + migration (time 0,5 → 0,5; freq 6,0 → 1−e^−6), confectionery ТГМ
  exact, П1.3/П1.4 switch, ГГ combinatorics, media mapping, dust and
  fireball, П1.2 × length, lightning, pedals, Kσ, matrix, hierarchy
  rules, gs_for gating, format-5 round-trip (+ node_offsets; formats
  1–4 rejected), validator, layout (bodies, word-fit widths, offsets
  WYSIWYG, scene 710 px), ToggleSwitch, icon palette (incl.
  auto-layout).
* gesture_test.py – PASS, 19 blocks (new: 14 sibling-add, 15 Delete
  paths + trash transitions, 16 h-scrollbar with pixel-intermediate
  Shift+wheel values `[0, 22, 32, 42, 50, 55…]` over a 252 px range,
  17 drag → offsets [38.27, 17.22] + round-trip + «Авторазметка»,
  18 sticky/free exclusivity + clamp, 19 presence field).
* run_qa.cmd – PASS; vision-reviewed with glm-5.3-flash (2×–3× crops):
  qa_window (splitters visible, 6 large toolbar icons), qa_hierarchy
  (colored glyphs ~22 px, indent levels, h-scrollbar) +
  qa_hierarchy2 (full long name reachable, no right clipping),
  qa_canvas crops (all five headers complete, counters-only bodies,
  «Всего: 60 сценариев» plural correct), _crop_fire_formula (ΣQ line
  blue/bold/larger vs the smaller lighter «Всего» line), qa_tooltip
  (compact short bubble, wrapped long bubble), qa_combo (popup =
  button width, tall items), qa_inspector_building (breathing room),
  qa_pdf_report («вероятность присутствия», no old wording).
  Vision-loop fixes made during QA (both re-verified): F_FORMULA
  11 → 12; splitter handle 6 px BORDER → 7 px #94A3B8.

## Known issues / notes

* Slot keys for `node_offsets` are `substance/oxidizer/gs/iz/fire` –
  the prompt's `presence1/presence2` do not exist in the codebase;
  semantics (optional per-tree offset dict, format 5) as specified.
* Delete delivery uses tree/canvas VIEWPORT event filters (plus the
  prescribed WidgetShortcut QShortcut on the tree kept as a second
  path): QTreeWidget claims Delete through ShortcutOverride for
  inline editing and item views hold focus in their viewports, so a
  plain shortcut is unreliable there. The rename editor still owns
  Delete while editing (verified).
* Dragging a node beyond the next tree's origin can visually overlap
  the neighboring tree block (offsets are purely visual, per LOCKED
  semantics); «Авторазметка» resets.
* HTML tooltip lines wrap by whole words; a single word longer than
  85 chars inside rich text is not syllable-split (plain text is) –
  no such string exists in the current UI.
* `ToggleSwitch` rows without a KB tooltip intentionally have no
  tooltip at all (7.1); qa_switches sample therefore shows none.
* Manual `run_app.cmd` start left to the user's habit (launcher
  untouched).
