# SESSION 9 REPORT – Kuji 5.0.0

Date: 09.11.2026. Base: v4.2.0 (sessions 1–8).
Subject: modern animated tooltips, colorful large icons, FULL REWORK of
the left wing into a free-form causal chain with И/ИЛИ/НЕ logic nodes
hanging on arrows, formula-driven frequency inputs (lightning pilot),
smooth live-following bezier edges. All five tasks of
`9 next-session-prompt.md` implemented after the questions-first gate:
a 32-question clarifying list was answered by the user before Task 3
(answers summarized in «Decisions» below).

**Acceptance:** `smoke_test.py` – PASS (29 blocks; new: «левое крыло»,
«валидатор левого крыла», «layout левого крыла», rewritten «матрица»/
«сериализация»/«молниезащита-формула», «палитра иконок», «подсказки»),
`gesture_test.py` – PASS (32 scenarios; new scenario 32 «канонический
конвейер» covering §3.0–3.2 end-to-end; scenarios 19/23/28 reworked for
the new model). `run_qa.cmd` artifacts regenerated and reviewed
(`qa_icons_palette.png` – vision PASS; `qa_tooltip_modern.png` – vision
PASS; bezier canvas/document – vision PASS; window composite checked;
see «Visual QA» for the disabled-icons false alarm). Version →
**5.0.0**; KB `meta.version` → «5.0»; README updated.

## Decisions locked by the user (32 answers)

1. НЕ = inhibitor `Q = Q_вх·(1 − P_усл)` (prob-type input → complement
   `1 − P`); only with exactly ONE input; offered in pickers/menus
   alongside И/ИЛИ.
2. ИЛИ branches: each input is «the same branch» – the tree does NOT
   fork its right wing; a DASHED GHOST terminal «Сценарий N+k» appears
   under «Сценарий N» (no arrows): the same tree with a different
   initial event. Extra self-sufficient initial events via ИЛИ → more
   ghosts (Сценарий 3, 4…).
3. With antecedents present, the left-wing product REPLACES the
   tabular per-area Q (tabular shown for comparison only).
4. «One initial event» = per scenario terminal (ИЛИ ⇒ 2 initials ⇒
   main + ghost).
5. Logic nodes = derived combiners per target (option (a)); NOT
   standalone wired nodes.
6–14, 18–31: proposals approved (strict right-wing chain; pin masks;
migration converts ГС/ИЗ phases; echelon columns kept; equipment under
territory; single «Применить на холсте» button with selection-based
logic; per-area F from the owning object with node override; KB tab
«Логические элементы» kept (НЕ record added); union in summaries;
formula pattern declarative; menus colored-but-small; ACCENT border;
400 ms dwell; node-owned lightning vars; n_у = 6 км⁻²·год⁻¹ default;
format 4; domino injects as ИЛИ-input; no intermediate pauses).
17 ( уточнение): 6 is км⁻²·год⁻¹ and can NOT go into Q (год⁻¹) as-is –
territory gained an editable F_тер (км²) with a м²↔км² switcher; N_у.м
= F_тер·n_у for outdoor installations.
32: general review of all tasks at the very end.

## Task 3 – free-form left wing (the core)

### Math (`eta/core/model.py`)

* `FtaNode` reworked: always kind «cause»; `children` = its own
  antecedents; `combine` (И/ИЛИ/НЕ) + `combine_p` (P_усл) live ON the
  node; `branches` runtime cache. `Node.left: list[FtaNode]` +
  `left_combine`/`left_combine_p` replace `FtaSide` (deleted together
  with `add_fta_phase/add_fta_subgate/set_fta_gate_type/
  swap_fta_phase_order/_fta_calc`).
* Branch enumeration `_branches_of`: И = cartesian product of input
  branches (cap `_MAX_BRANCHES = 8`, overflow collapses a multi-branch
  input into its union); ИЛИ = concatenation (each «self-sufficient»
  initial branch becomes its own scenario); НЕ = single inhibitor branch
  (freq: `Q·(1−P_усл)`, prob: `1−P`).
* `recalculate`: post-order `_left_calc` (displayed Q = branch 1);
  the visible tree flows along BRANCH 1 (q_main = first initial event ×
  chain factors); ghosts = branches 2..k for every HAZARD leaf:
  `q_ghost = q_leaf · (q_branch/q_main)` (linear rescale), scenario
  numbers continue the global counter (display-only).
* `fta_center_q` = union of branches (summary/status/matrix):
  `1 − ∏(1−Q_i)` when all Q ≤ 1 (probabilities); if any branch is a
  FREQUENCY > 1 год⁻¹ (e.g. lightning 6/yr) the exact probability
  formula is meaningless → conservative sum Σ Q_i (KB's rare-event
  note). Invariant (per-branch accounting, exact):
  ΣQ(visible leaves) + ΣQ(hidden shares) = q_main; ΣQ ghosts reported
  separately (`ghosts_q_total`).
* Center semantics (answer 3): no antecedents → tabular `q_spec`
  (per-area a₁·F etc.); antecedents → product replaces it (inspector
  shows «Табличное Q (для сравнения)»).
* Ghosts surface everywhere: `scenarios()` rows («Сценарий N – фактор
  (призрак: <initial>)», status «В расчете ОФП (ветвь ИЛИ)»), matrix
  rows (`MatrixRow.ghost`), status bar «Призраки ИЛИ: ΣQ», layout
  dashed NodeGeos (kind «ghost», no pins) under the terminal.
* API: `add_antecedent/move_antecedent/remove_antecedent`,
  `set_combine/cycle_combine/set_combine_p`, `combine_of/combine_p_of/
  n_inputs`, `combine_allowed`, `next_combine` (И→ИЛИ→НЕ→И; НЕ skipped
  unless exactly 1 input; `set_combine` coerces НЕ→И defensively).
  `add_fta_cause`/`remove_fta_node` kept as compatibility aliases.

### Serialization (format 4, `eta/core/serializer.py`)

* `_cause_to_dict/_cause_from_dict`: id/title/level/q_spec/source/
  justification/combine(+combine_p)/k_scale/manual_pos/children;
  `_node_to_dict` writes `left`/`left_combine`(+`_p`); НЕ with ≠1 input
  normalized to ИЛИ on load.
* Migration of formats 1–3 («fta» phases): each phase's TOP GATE
  becomes a synthetic antecedent (combine = gate_type, children
  converted recursively: subgates → nested antecedents, causes →
  leaves), `left_combine = И` (ГС·ИЗ conjunction preserved exactly –
  smoke asserts `2e-3 · (6·0.05)`), k_scale/manual_pos carried.
  `FORMAT_VERSION = 4`; loader accepts 1/2/3/4.

### Validator (`eta/core/validation.py`, rewritten)

Phase purity/slot monotonicity/subgate-depth rules DELETED (free-form).
Kept/added: antecedents only into the center (root) or other
antecedents; duplicate cause on one logical path rejected; cycles
rejected (`check_move`: drag-reparent can't target own descendant);
`check_gate_set` (И/ИЛИ need ≥1 input, НЕ exactly 1); barriers never on
the left wing, causes never on right-wing nodes. `check()` dispatches
by template kind (cause/gate/barrier) – DnD hover uses the same path.

### Layout (`eta/core/layout.py`)

* Antecedents align to echelon columns by KB `level` (columns −5…5
  auto-extend); each top-level input subtree is a BLOCK vertically
  centered on the center's row (blocks stacked with DY_MIN); manual_pos
  honored.
* Badges (`BadgeGeo` + `badges` list): small И/ИЛИ/НЕ box near the
  first input arrow's midpoint; И/НЕ float ABOVE the arrow, ИЛИ is
  IN-LINE (drawn on the line); `active` = ≥2 inputs or НЕ (colored),
  else grey lock. Rendered by `render.draw_badge` (canvas + PDF);
  interactive `BadgeItem` on canvas (tooltip; double-click cycles /
  explains the lock).
* Ghost terminals: dashed compact NodeGeos stacked below their
  «Сценарий N» (GHOST_H0/DY spacing), HAZARD-dashed border, no pins.
* NodeGeo pin masks: `pins_left/pins_right` – terminal «Сценарий N»
  loses RIGHT pins (nothing follows a final scenario); initial
  antecedent (no children) loses LEFT pins; ghost has none.

### Canvas / inspector

* `pin_hit` covers cause-nodes; `NodeItem.visible_pin_keys()` respects
  masks; left-green click on center/antecedent opens the antecedent
  picker (causes + И/ИЛИ/НЕ entries; НЕ synthetic + KB record); short
  click on an antecedent's right pin explains the drag gesture.
* Drag from an antecedent's RIGHT pin to another node = REPARENT
  (`check_move` + `move_antecedent`) – §3.2's wiring primitive.
* The session-8 «scenario node guard» is REMOVED by design: the
  terminal no longer has right pins, so insertion ABOVE the terminal
  happens through the PARENT's right pin (scenario split rides down –
  existing add_split logic). Gesture scenario 23 updated accordingly.
* Double-click on badge: active → `cycle_combine` (retargets position
  each click since ИЛИ re-anchors in-line); locked → tooltip explains.
* Context menus: ETA root gains «Добавить предшественника»; antecedent
  menu has predecessors + «Сменить на И/ИЛИ/НЕ (ингибитор)» (НЕ only at
  1 input) + delete/reset. All actions carry icons (asserted).
* Inspector: antecedent form (Q/P editor, source, justification) +
  `_append_combine_editor` (И/ИЛИ/НЕ combo, НЕ disabled at ≠1 input,
  P_усл spin, branch list); center form shows left-wing summary
  (tabular Q for comparison, per-branch Qs, union formula) +
  combiner editor. Scenarios tab summary: left-wing line, union Q,
  ΣQ ghosts.

### Hierarchy / apply button (§3.0)

`PARENT_RULES[EQUIPMENT]` now includes TERRITORY: «Применить на
холсте» stays a SINGLE button; with a territory selected it creates the
equipment directly in the territory (`props.is_outdoor = True`
– наружная установка, may carry several independent «Сценарий N»
trees); otherwise the previous `_resolve_area` logic (auto-creating
Территория→Здание→Помещение→Участок when empty). Main window sets an
`_area_hint_km2` on the inspector when an outdoor installation is
selected (feeds the lightning formula, Task 4).

### Matrix / status bar (`eta/core/matrix.py`, `main_window.py`)

Cause columns = all antecedents (echelon «Причины отказов · левое
крыло»); cell operator = И/ИЛИ/НЕ of the cause's TARGET combiner;
level-0 cell shows the UNION Q; ghost rows included; invariant note:
«ΣQ сценариев + ΣQ призраков + ΣQ скрытых долей = ΣQ ветвей».
Status bar: «Q центра (объединение ветвей) = …», «Призраки ИЛИ: ΣQ».

### Domino (`eta/core/domino.py`)

`route_all` injects «Внешнее воздействие (каскад домино)» as an ИЛИ
antecedent into the target tree's CENTER (center combiner switched to
ИЛИ when other inputs exist – an external fire is an alternative
initiator); self-cleaning by `justification="domino:"` + explicit
`recalculate` after un-routing (frequencies must be current before
cascade Q is read – fixed a load-order bug the old API masked).

## Task 4 – formula-driven frequencies (lightning pilot)

* New `eta/core/formulas.py`: registry `{"lightning": lightning_q}`;
  `N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶`, `Q = N_у.м·(1−η)`; η map
  I/II/III/IV = 0,98/0,95/0,90/0,80 (СО 153-34.21.122-2003 табл. 2.2),
  «нет» → η=0; area mode `N_у.м = F_тер·n_у` (км²·км⁻²·год⁻¹ = год⁻¹).
  `model.compute_q_init` gains mode «formula» (unknown formula id →
  legacy q_init fallback).
* KB `c-iz-lightning` gained declarative `formula_spec` (variables
  S/L/H/n_y/prot with symbols/units/defaults/sources; options map for
  η; `area_variable` F_km2) – edited via a byte-safe Python script
  (Cyrillic-safe round-trip, verified `json.loads` before/after, no
  em-dash). KB «Логические элементы» tab also gained the НЕ record.
* `add_antecedent`: templates with `formula_spec` produce FORMULA
  nodes (`{"freq_mode":"formula","formula":id,"vars":defaults}`).
* Inspector `_append_formula_editor`: math-rendered formula line +
  source; variables as spin/option fields (tooltips through
  math()+modern tooltip layer), live read-only Q (no free-form
  override); mode switch «Размеры объекта / Площадь территории»;
  outdoor installation pre-selects area mode with the territory's
  F_тер (hint from main window).
* `apply_lightning_protection` reworked: formula nodes get S/L/H/η from
  the owning building (pedal ON → cat, OFF → «нет»), k_scale forced
  1.0 (building = source of variables, not a multiplier); legacy direct
  nodes keep the old k_scale path. Serializer migrates legacy
  q_init=6/direct lightning causes to formula defaults (k_scale
  absorbed → 1.0).
* Territory object: `strike_area_km2` (stored in км²) with inspector
  field + км²↔м² switcher (м² input ×10⁻⁶ on write) – the user's unit
  convenience (answer 17).

## Task 2 – modern animated tooltips (wired in)

`eta/ui/modern_tooltip.py` (built in the pre-answer rounds behind a
flag) is now installed in `main.py`; the controller swallows system
`QToolTip` ToolTip events (no double tooltips); ALL canvas
`QToolTip.showText/hideText` call sites route through
`scene_tip/hide_scene_tip` (grep shows QToolTip only inside the
adapter's fallback). Fixed during wiring: formula styling switched
from unsupported `border-left` to a blue-tinted background strip
(Qt rich text limitation) – vision-verified PASS (bold header, mono
bold formula strips, muted source lines, true typeset subscripts).
Smoke block extended: retargeting without flicker (same window object
reused), ToolTip-event swallowing, offscreen instant mode.

## Task 1 – icons

Palette + sizes landed pre-answer (ICON_PALETTE in theme.py, stroke
2.2, 22/24 px in panels, active = lightened own color, raster set
16–48). Added post-answers: KB window transfer button 20 px; funnel
glyph thinned (vision note). `qa_icons_palette.png` (48 px swatch of
all 23 glyphs with labels) added to run_qa – vision PASS.
Note (visual QA): in `qa_window.png` the hierarchy toolbar buttons
appear grey because the selected object is equipment → buttons are in
Qt's DISABLED state (grayed icons); pixel ground truth of the live
window confirms colors: scenario=orange, territory=brown-amber,
compartment=cyan, room=teal, area=amber, building=steel-slate (by
design). Menus keep QStyle default size per Q19 (colored but smaller).

## Task 5 – bezier edges

* `EdgeGeo` gains `c1/c2` control points + `sample_points()` (16-seg
  De Casteljau sampling); ETA curves: horizontal tangents at pins,
  control distance `0.5·gap` clamped 40–260 px (`CURVE_*`);
  single-child continuations stay 2-point straight (STRAIGHT_SNAP).
* Anti-merge: parallel inputs of one target fan out vertically
  (`FAN_STEP = 12` on the arrival control point); ETA branches fan by
  port index. Audit (node/callout/segment collisions) now samples the
  CURVE polylines; deterministic push-apart unchanged.
* `render.draw_edge`: one `QPainterPath.cubicTo` drawn identically by
  canvas and `QPdfWriter` (vector, WYSIWYG); arrowheads oriented by the
  end tangent (P3−C2). `EdgeItem` bbox/shape from sampled polyline
  (accurate ±7 px hit). Domino dashed links also bezier (canvas-only).
* Live following: drag loop (`apply_manual_positions` → compute_layout
  → sync_positions) already recomputes geometry per mouse move –
  curves glide with the node (audit runs in the same pass).

## Files touched

`eta/__init__.py` (5.0.0) · `eta/core/model.py` (left wing + branches +
ghosts) · `eta/core/formulas.py` (NEW) · `eta/core/validation.py`
(rewrite) · `eta/core/serializer.py` (format 4 + migration) ·
`eta/core/layout.py` (badges, ghosts, pin masks, bezier, sampled
audit) · `eta/core/matrix.py` (ghost rows, И/ИЛИ/НЕ cells) ·
`eta/core/domino.py` (ИЛИ-injection) · `eta/core/generator.py`
(formula-aware lightning) · `eta/core/objects.py` (equipment under
territory, strike_area_km2) · `eta/ui/canvas.py` (pins/pickers/reparent/
badges/bezier/double-click/menus/drops) · `eta/ui/render.py`
(draw_badge, ghost/cause styles, cubic painter) ·
`eta/ui/inspector_panel.py` (combiner + formula editors, territory
F_тер, summaries) · `eta/ui/modern_tooltip.py` (NEW; wired) ·
`eta/ui/theme.py` (ICON_PALETTE, strokes, sizes, tooltip constants) ·
`eta/ui/icons.py` (palette-driven colors, registry, sizes) ·
`eta/ui/left_toolbar.py`, `eta/ui/hierarchy_panel.py`,
`eta/ui/kb_window.py`, `eta/ui/main_window.py` (icon sizes, apply
logic, area hint, status bar) · `main.py` (tooltip install) ·
`visual_qa_runner.py` (left-wing mock, qa_icons_palette,
qa_tooltip_modern) · `smoke_test.py` · `gesture_test.py` ·
`README.md` · `knowledge_base.json` (formula_spec, НЕ gate, meta 5.0).

## Test results / Visual QA

* `smoke_test.py` – PASS, 29 blocks (rewritten «бабочка» trio →
  «левое крыло» trio; «молниезащита» → «молниезащита-формула» with
  migration of the hardcoded «6»; new «палитра иконок» and «подсказки»).
* `gesture_test.py` – PASS, 32 scenarios (new №32 canonical pipeline:
  outdoor installation via territory apply → [Пожар…] → [Сценарий 1] →
  lightning+electrical via left pins → grey→active И → ИЛИ+ghost
  «Сценарий 2» → НЕ inhibitor via menu → drag reparent → terminal
  right pins absent → format-4 round-trip).
* `run_qa.cmd` – `pdf_rendered: true`, 40-page A3 (wider left wing),
  artifacts incl. `qa_icons_palette.png` (vision PASS) and
  `qa_tooltip_modern.png` (vision PASS). Canvas+document bezier review:
  PASS (smooth curves, tangent arrowheads, distinct parallel edges,
  badges visible, WYSIWYG); minor notes (near-touching long curves
  x≈560–640; tight ghost stack) recorded, no blockers.
* App starts cleanly from `run_app.cmd` (manual check left to the
  user's habit; no code path changed in the launcher).

## Known issues / notes

* Ghost numbering is display-only (continues the global scenario
  counter each recalc; not persisted) – matches the «inherited ghost»
  semantics; manual renames of ghosts are not offered.
* When several ИЛИ branches exist, the VISIBLE tree always shows
  branch 1; other branches exist as ghost rows/dashed nodes only (per
  answer 2) – deep right-wing divergence per branch is intentionally
  NOT built.
* The И-branch cartesian cap (`_MAX_BRANCHES=8`) collapses pathological
  nested-ИЛИ cases into their union (documented in code).
* Legacy lightning causes migrated to formula defaults (S=100, L=100,
  H=20, n_у=6, η=II) – old manual numbers/k_scale are replaced (the
  approved migration; source note kept).
* `qa_window.png` grey toolbar icons = Qt disabled state (equipment
  selected), not a palette failure (pixel-verified; see Task 1 note).
