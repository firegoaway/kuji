# SESSION 13 REPORT – Kuji 6.3.0

Date: 11.11.2026. Base: v6.2.0 (sessions 1–12).
Subject: stabilization + KB-overhaul + canvas-annotation session,
thirteen tasks (0–12). All LOCKED Q&A decisions implemented as
specified; three clarifying answers were received from the customer
during the session (Task 8: dust rows follow the task text «(а)»,
row names abbreviated; Task 0: «Носитель» as a separate column (а),
coefficient edits of EXISTING records must affect the calculation,
new-record defaults confirmed). No locked decision was reopened.

**Acceptance:** `smoke_test.py` – PASS (18 blocks; block 9 extended
with KB-driven pedal numbers and the universal-k branch; block 14
annotation round-trip; block 16 rewritten to annotations);
`gesture_test.py` – PASS (blocks 1–12 of session 12 + new blocks 20–29
of session 13); `run_qa.cmd` – PASS, artifacts regenerated and
vision-reviewed (glm-5.3-flash, crops/2× where pixel truth mattered).
Version → **6.3.0**; KB `meta.version` stays **«6.1»** (no schema
change; all KB edits are runtime data through the new editable UI).

## Task 1 – «Документ» pop-out blank on second open

* Root cause confirmed as diagnosed: `_on_doc_window_closed` hid the
  host (`hide()` sets an explicit-hidden flag that survives reparent),
  and `open_doc_window` never cleared it → the rebuilt window showed
  an empty surface.
* Fix: `open_doc_window` calls `self._doc_host.show()` at window
  creation (clears the flag; harmless on first open). Close/reopen
  cycles verified ×2 with the full panel visible
  (`doc_stack`, caption label, matrix rows > 0).

## Task 2 – Q = 0 although «all parameters set» (displayed ≠ stored)

* Root cause confirmed (LOCKED #11): form builders displayed fallback
  defaults (`p.get(key, default)`) without writing them into props;
  the engine read only props → empty `p13_type`/`area_m2` → multiplier
  0 → Q = 0. The П1.3/П1.4 combo additionally displayed row 0 while
  the property stayed empty.
* Fix: `_ensure_default(p, key, default)` in `inspector_panel.py` –
  every displayed default is written into props at form build; the
  type-combo `fill()` writes `combo.currentData()` of the displayed
  index. Covered: building (area, type, lightning category, S/L/H),
  room (area, vent rate), area (site type + value), outdoor (area,
  type, category), territory (strike area), compartment (REI).
  Defaults are now sourced from `DEFAULT_PROPS` (single source) –
  this also fixes a pre-existing mismatch: the building form displayed
  H = 100 while `DEFAULT_PROPS` says 20 (now 20, consistent).
* No signals are emitted on materialization (values are already on
  screen); `_on_object_selected` refreshes right after the form build,
  so Q becomes non-zero immediately.
* Regression: fresh Т→З→П→У + ТГМ tree, forms untouched →
  `Q = 8.45e-07 > 0` (gesture block 20); keys present in props right
  after opening each form.

## Task 3 – Alt+A layout-independent

* Root cause confirmed: `QKeySequence("Alt+A")` matches only Latin
  «A»; on the Russian layout the same key yields «Ф».
* Fix: `self.act_fit.setShortcuts([Alt+A, Alt+Ф])` with
  `ApplicationShortcut` context (works with focus in tree, canvas,
  inspector, and the KB/doc windows). Sweep result: Ctrl+E/Ctrl+D/
  Ctrl+Q have the same defect class → Cyrillic twins registered
  (Ctrl+У / Ctrl+В / Ctrl+Й). Standard keys (Ctrl+N/O/S), F-keys and
  Delete are layout-independent by construction.
* Verified with `QTest.keyClick(widget, Qt.Key_A, Alt)` (key CODES are
  layout-independent) in all four focus targets (gesture block 21).

## Task 4 – reference (title) nodes instead of the floating header

* The floating `TreeHeader` (title + blue Q) is gone everywhere
  (canvas, doc sheet, PDF; `TreeHeader`/`draw_header` removed). Q is
  not duplicated in the air – it lives in the «Возникновение» node
  and the status bar.
* Each tree gets ONE auto-generated annotation node
  (`{owner_title} · {scenario_type_title}`, live-updates on rename and
  type change; auto width, ≤2 lines via `wrap_words`).
  `TreeModel.annotation = {"attached": slot|None, "offset": [dx, dy]}`
  (format 5 optional per-tree field; round-trip in smoke block 14 and
  gesture block 28; tree deletion removes it with the tree).
* LMB drag with the same 5 px threshold; while dragging, the nearest
  node of the same tree within `ANN_SNAP_DIST` (30 px) gets an accent
  dashed outline + a «Привязать» mini-tooltip; release near a node
  snaps magnetically (centered above it: offset =
  [(node_w − ann_w)/2, −(ann_h + 14)]) and the node FOLLOWS the
  attached node afterwards (node drag, «Авторазметка», rebuilds);
  dragging away detaches (free offset from the default position
  persists). Hover tooltip: «Справочная нода – перетащите; отпустите
  рядом с нодой дерева, чтобы привязать».
* Geometry is computed ONCE in `compute_layout` (`Annotation` in
  `layout.py`, included in the scene union) and drawn by
  `render.draw_annotation` (dashed 1 px border, #F8FAFC fill,
  secondary text, rounded corners) – canvas and PDF WYSIWYG;
  annotations render on the PDF schematic sheet through the shared
  doc_scene.
* «Авторазметка»: attached annotations follow their nodes; free ones
  return to the default position (annotation state reset to None).
* Gesture block 28 covers the full lifecycle: existence + exact text,
  rename updates, magnetic attach (`attached == "gs"`, snap offset),
  following on gs drag, detach, format-5 round-trip, «Авторазметка»
  (free reset; attachment survives).

## Task 5 – free mode truly unbounded

* Root cause confirmed: scrollbar ranges derive from the scene rect in
  both modes. Fix: in free mode the WORK scene rect is the layout rect
  grown by ±100 000 px (`TreeCanvas._view_scene_rect`); sticky restores
  the exact layout rect. The doc scene (PDF/лист) always keeps the
  exact layout rect – export geometry is asserted unaffected; `fit_tree`
  and the sticky clamp use `layout.scene_rect` as before.
* Gesture block 18: in free mode both scrollbars have ranges > 100 000,
  the camera pans far beyond the tree, and switching back clamps into
  bounds + 40 px.

## Task 6 – context menu, «Добавить дерево» button, delete semantics

* Context menu keeps ONLY «Переименовать…» and «Удалить с поддеревом…»
  (icons/default button unchanged). «Свойства» and «Добавить дерево…▸»
  removed; `props_requested` signal and its wiring deleted (no other
  consumers).
* New 7th toolbar button «Добавить дерево» (right of «Добавить
  наружную установку», spread recomputed; new violet glyph `tree-add`
  in `icons.py`, registered in ALL_GLYPHS + ICON_PALETTE). Click opens
  the 5-type menu; enabled on Участок/наружная установка (tree created
  directly) and on ПОМЕЩЕНИЕ (auto-created «Участок N» first, status
  message «Создан Участок N – на нём создано дерево «…»», new участок
  selected → its form materializes defaults per Task 2). Testable seam
  `_add_tree_for(stype)` (menu itself stays interactive-only).
* 6.1: disabled tooltips use the parenthetical template everywhere –
  exact `Добавить наружную установку (выделите территорию)`; others:
  `Добавить здание (выделите территорию или здание)`,
  `Добавить пожарный отсек (выделите здание или пожарный отсек)`,
  `Добавить помещение (выделите здание, отсек или помещение)`,
  `Добавить участок (выделите помещение или участок)`;
  new button: `Добавить дерево (выделите участок, наружную установку
  или помещение)`.
* 6.2: Delete removes ONLY the selection (+ descendants). Reproduced
  with a deep chain + QTest (single press deleted exactly the
  selected subtree even with the confirm seam patched True), then all
  three diagnosed suspects were closed structurally:
  (1) the tree viewport event filter was installed TWICE
  (`installEventFilter` at two __init__ sites) – deduplicated to one;
  (2) selection is now explicitly cleared (signals blocked) BEFORE any
  removal, so rebuild-time re-anchoring and Delete auto-repeat find
  nothing; (3) the `_selected` fallback in `_delete_current` is used
  only while the node is still alive in the hierarchy.
* Multi-select: `ExtendedSelection` on the tree; Delete with multiple
  selected objects opens ONE confirmation «Удалить N объектов с
  поддеревьями?» with the title list (seam `_confirm_multi_delete`,
  default button «Удалить»); descendants of selected nodes are
  deduplicated; single rebuild; owned trees of removed owners die with
  them (existing `_on_subtree_removed`). Trash button follows
  multi-selection (`selected_objects`).
* Gesture block 24: button gating incl. exact tooltip strings,
  room→auto-участок with status message and Task-2 defaults, a
  4-press Delete burst kills exactly the victim (ancestors alive), and
  the multi-select batch.

## Task 7 – KB tables: h-scrollbar + no mid-word truncation (ALL tables)

* Shared wrap helper factored into `controls.py`:
  `split_long_word`/`wrap_words85`/`wrap_text85` (moved from
  `modern_tooltip`; the tooltip module now imports them – one
  implementation). Fixed an off-by-one found by the new assertions: a
  syllable piece could be `limit + 1` chars because «–» was not
  counted against the limit.
* `_format_table` (kb_window): columns auto-fit the widest content and
  are NEVER squeezed (no width cap, no stretch of the last section);
  `ScrollBarAsNeeded` horizontal scrollbar; cell-widget (QLabel) widths
  accounted for via sizeHint; rows sized to wrapped content. Applied
  to: «Защитные средства», all three method-table sub-tabs, and the
  new libraries. Cell text ≤85 chars/line, whole-word wrap, syllable
  split for single overlong words.
* Measures notes are pre-wrapped with the shared helper and rendered
  as rich QLabel cells (real sub/superscripts preserved);
  QTableWidgetItem cells stay plain text.
* Gesture block 25: policy/stretch assertions for every table of the
  KB window (incl. sub-tabs), ≤85 visible chars per measures-note
  line, row heights fit line counts, h-scrollbar engages when needed.

## Task 8 – tab «Таблица типовых режимов пожара» (read-only)

* Customer rulings applied: dust rows follow the task text
  («по табл. П2.1 (по расходу и среде)» with the flow/medium note),
  and row names are the abbreviated ones.
* Tab renamed; inner caption «ТИПОВЫЕ РЕЖИМЫ ПОЖАРА (прил. № 2,
  табл. П2.1)»; columns exactly «Режим пожара | Базовая частота |
  Примечание»; 8 rows: Пожар по поверхности (`a₁·F (табл. П1.3/П1.4)`,
  примечание: множитель ТГМ по свойствам здания/установки), Факельное
  горение, Пожар-вспышка, Пролив, Сгорание (взрыв) ТВС, Дефлаграция
  пылевоздушной смеси, Детонация пылевоздушной смеси (all
  «по табл. П2.1 (по расходу и среде)»; примечание: условная
  вероятность выбирается по массовому расходу (<1 / 1–50 / >50 кг/с /
  полный разрыв) и среде (газ / двухфазная / жидкость) по прил. № 2 к
  Приказу МЧС России № 533, табл. П2.1), Огненный шар (диффузионное
  горение) (`2,5·10⁻⁵ год⁻¹`; частота внешнего воздействия на аппарат
  (Приказ МЧС России № 533, прил. № 1, п. 5)).
* Numbers in engineering format (comma decimal, Unicode
  superscripts). Task 7 rules apply. Read-only: no edit triggers,
  record buttons hidden on this tab. Old machine-oriented
  FireTypesTab/_TableTab/GSCausesTab/IZCausesTab classes removed.
* Gesture block 27 asserts names/captions/columns/contents exactly;
  QA shot qa_kb_fire_modes vision-reviewed.

## Tasks 9/10 – editable libraries «Источники зажигания (ИЗ)» / «Горючие среды (ГС)»

* Tabs renamed; captions «БИБЛИОТЕКА ПРИЧИН ПОЯВЛЕНИЯ ИСТОЧНИКОВ
  ЗАЖИГАНИЯ (ИЗ)» / «БИБЛИОТЕКА ПРИЧИН ВОЗНИКНОВЕНИЯ ГОРЮЧИХ СРЕД
  (ГС)»; columns «Наименование ИЗ | λ, год⁻¹ | Примечание» and
  «Наименование ГС | Частота, год⁻¹ | Примечание» (sources live inside
  «Примечание»).
* Content: λ/frequency in engineering format («3,2·10⁻⁵ год⁻¹»);
  «Удар молнии» → «расчётная величина» + примечание
  «рассчитывается по свойствам здания/установки: N_у.м·(1 − η_МЗ)
  (источники)»; direct-probability rows → «P = 1 (вероятность)»
  (generalized `P = <value> (вероятность)`); П1.2 →
  «2,8·10⁻⁶ м⁻¹·год⁻¹ × L» + примечание «L – длина прокладки, м;
  задается на ноде ГС (или в свойствах участка)»; ТГМ-поверхность →
  «a₁·F (табл. П1.3/П1.4)» + примечание.
* Editing: title edited in-cell; numeric λ/frequency via a small
  numeric dialog (accepts «3,2e-5», comma or dot); примечание via a
  multi-line editor with LIVE mini-notation preview; new records:
  «Добавить запись»/«Удалить запись» at the BOTTOM-LEFT of the KB
  window (opposite «Сохранить»/«Закрыть»). New-record fields: only the
  3 visible ones; auto-generated: `iz-<uuid8>` (lam 1e-5),
  `gs-<uuid8>` (kind p11, applies gg/gzh/lvzh/dust, site_kinds
  [apparatus] – documented default so the record appears in the cause
  pickers of the release scenario types), measures `pm-<uuid8>`.
* Deleting a referenced record is allowed with a warning seam
  («используется в N деревьях – ссылки будут потеряны»); usage counts
  come from MainWindow (trees for gs/iz; trees + objects for
  measures). Changes persist through «Сохранить» (kb.save());
  «Закрыть» keeps the dirty-guard. KB meta.version unchanged.
* A latent engine bug was found and fixed while testing: direct list
  edits (add/delete/numeric change) left the KB accessor indexes
  (`_gs_by_id`, `_iz_by_id`, `_modifier_by_pedal`) stale until the
  next save – the engine and the usage counter would miss new records.
  Fix: `kb.reindex()` (public) is called on every library mutation.
* Gesture block 26 asserts captions/columns/formats/seams, add/delete
  flows, usage warning and cancel; the REAL knowledge_base.json is
  never touched by tests (in-memory snapshot/restore).

## Task 0 – «Защитные средства» editable library (customer rulings applied)

* Columns now FOUR (ruling 1а): «Наименование средства | Коэффициент |
  Носитель | Примечание»; «Носитель» values: Нода ГС / Нода ИЗ /
  Помещение / Здание (edited by a small dialog; moves the switch to
  the target form immediately after save/reload).
* Coefficient edits affect the ENGINE (rulings 2 and its correction):
  the hardcoded pedal multipliers in `TreeModel._gs_k/_iz_k` now read
  the KB record (`kb.modifier_by_pedal`) – износ/герметичность/
  вибро-контроль edit `k`, дренаж/датчики утечки edit `p_success`
  (k = 1 − p_success). Records WITHOUT a single numeric coefficient
  (SIL/ПАЗ, периодичность ТО, резервирование, взрывозащита, категория
  среды, молниезащита, самовоспламенение) keep structural engine
  semantics; their coefficient cell is an editable mini-notation TEXT
  (display) – a numeric edit is not meaningful for them.
* New measures: type "k" with a universal numeric multiplier – the
  switch appears on its target node (gs/iz pedal blocks) or, for
  room/building targets, directly in the object's properties
  (`InspectorPanel._universal_measures_block`), and the engine
  multiplies: node targets in `_gs_k/_iz_k`, room/building targets via
  `CalcContext.universal_k` (× Q_ГС of the tree; effective-props
  cascade de-duplicated by a seen-set). Defaults (ruling 3):
  «Новое защитное средство», k = 1, носитель «Нода ГС», formula
  «F_вых = F_вх · k»; pedal key = auto id `pm-<uuid8>`.
* Notes follow the session-11 canon and remain fully editable
  (override field `note`; coefficient text override `coef` for
  structural records). Task 7 rules apply.
* Gesture block 29: 4 columns, engine effect of editing wear k
  (2→4 → ×2), drain p_success (0.95→0.9 → ×2 of 0.05→0.1), universal
  k on a node and on a room (through effective props), target change
  to iz/room, room-form switch visible, deletion warning with usage ≥ 1.

## Task 11 – UI memory for all windows

* Main window geometry + splitter state kept (`ui/geometry`,
  `ui/splitter`). KB window: geometry saved in `closeEvent`
  (`ui/kb_geometry`), restored at creation. «Документ» pop-out:
  geometry saved on close (`ui/doc_geometry`), restored on open;
  NO auto-reopen at launch (LOCKED). Off-screen restore verified
  (position 9500,7500 → window visible, no crash).
* Gesture block 23: resize → close → reopen preserves sizes for both
  windows (sizes kept within the offscreen screen so Qt does not clamp
  them in tests).

## Task 12 – «Площадь территории» + unit switch км²|м²

* Label «Площадь ударов молнии F_тер, км²:» → **«Площадь территории:»**
  with a compact combo «км²|м²» next to the spin (LOCKED placement).
  The stored value stays normalized in км² (`strike_area_km2`); the
  chosen unit is stored in props (`strike_area_unit`, default "km2")
  and persists in the project file; switching converts the display
  (м² = км²×10⁶; decimals 6/1, suffix « км²»/« м²»). Tooltip explains
  the field is informative: the lightning frequency is computed from
  the building/installation dimensions and protection category.
  Task 2 invariant applies (displayed defaults committed).
* Gesture block 22: 0,05 км² ↔ 50 000 м² conversion, value entry in
  м², form reopen keeps unit+value, save/load round-trip.

## Before → after strings (all changed user-facing texts)

* Tabs: «Разновидности ГС» → «Горючие среды (ГС)»; «Разновидности ИЗ»
  → «Источники зажигания (ИЗ)»; «Типы горения» → «Таблица типовых
  режимов пожара».
* Captions: «РАЗНОВИДНОСТИ ПРИЧИН ГС (П1.1/П1.2/поверхность)» →
  «БИБЛИОТЕКА ПРИЧИН ВОЗНИКНОВЕНИЯ ГОРЮЧИХ СРЕД (ГС)»;
  «РАЗНОВИДНОСТИ ПРИЧИН ИЗ (ГОСТ 12.1.004-91, табл. 9)» →
  «БИБЛИОТЕКА ПРИЧИН ПОЯВЛЕНИЯ ИСТОЧНИКОВ ЗАЖИГАНИЯ (ИЗ)»;
  «ТИПЫ ГОРЕНИЯ (П2 п. 4, табл. П2.1)» → «ТИПОВЫЕ РЕЖИМЫ ПОЖАРА
  (прил. № 2, табл. П2.1)».
* GS columns «Id | Название | Тип (p11/p12/p13/direct) | Q, год⁻¹ |
  Q, м⁻¹·год⁻¹ | Типы сценариев | Типы участков | Источник» →
  «Наименование ГС | Частота, год⁻¹ | Примечание»; IZ columns «Id |
  Название | λ, год⁻¹ | Режим (lightning) | P | Источник» →
  «Наименование ИЗ | λ, год⁻¹ | Примечание»; fire-types machine
  columns → «Режим пожара | Базовая частота | Примечание»; measures:
  + column «Носитель».
* Territory: «Площадь ударов молнии F_тер, км²:» → «Площадь
  территории:» + combo «км²|м²».
* Disabled hierarchy tooltips: «<b>Добавить X</b> – выделите Y» →
  «Добавить X (выделите Y)» for building/compartment/room/area/outdoor
  (outdoor exact per LOCKED); new: «Добавить дерево (выделите участок,
  наружную установку или помещение)».
* Shortcuts: Alt+A → Alt+A + Alt+Ф; Ctrl+E → +Ctrl+У; Ctrl+D →
  +Ctrl+В; Ctrl+Q → +Ctrl+Й.
* Context menu: removed «Свойства» and «Добавить дерево…▸» (kept:
  «Переименовать…», «Удалить с поддеревом…»).
* Tree header (canvas/PDF) «Участок · Сценарий …» + blue «Q = … год⁻¹»
  → compact dashed reference node with the title only.

## Files touched (session 13)

eta/__init__.py (6.3.0) · eta/core/model.py (annotation field +
KB-driven pedal numbers + universal_k; serialization) ·
eta/core/layout.py (Annotation, _make_annotation, scene union,
TreeHeader removed) · eta/core/kb.py (public reindex) ·
eta/core/serializer.py (unchanged; annotation rides format 5) ·
eta/ui/canvas.py (AnnotationItem/_DocAnnotationItem, drag/attach/
detach, candidate highlight, free-mode scene rect) ·
eta/ui/render.py (draw_annotation, draw_header removed) ·
eta/ui/main_window.py (doc-window fix + geometry, twins, KB usage,
annotation dirty, auto-layout, delete selection, status wiring) ·
eta/ui/hierarchy_panel.py (7th button, menu trim, ExtendedSelection,
delete rework, parenthetical tooltips, _add_tree_for) ·
eta/ui/inspector_panel.py (displayed=stored, territory units,
universal measures block, DEFAULT_PROPS defaults) ·
eta/ui/kb_window.py (libraries IZ/GS/measures, FireModesTab, Task-7
formatting, note/number editors, bottom-left buttons, geometry save) ·
eta/ui/controls.py (shared wrap helpers) · eta/ui/modern_tooltip.py
(imports shared helpers) · eta/ui/icons.py + theme.py (tree-add glyph,
palette) · smoke_test.py · gesture_test.py (blocks 20–29, version
assert) · visual_qa_runner.py (reopen cycle, territory shot, new KB
shots, annotation demo) · README.md · qa_artifacts (regenerated).

## Test results / Visual QA

* smoke_test.py – PASS (18 blocks): KB 6.1 canon; presence;
  confectionery ТГМ exact; П1.3/П1.4; combinatorics; dust/fireball;
  П1.2; lightning/pedals (now KB-driven: wear k from the record,
  record edit 2→3 → ×1.5, local wear_k override wins; universal k
  new-measure branch ×0.25 on/off); Kσ; matrix; hierarchy; gs_for;
  format-5 round-trip (+ node_offsets, + annotation); validator;
  layout (annotation per tree, ≤2 lines, title text, no «Q =», scene
  contains it); switch; icon palette (incl. tree-add).
* gesture_test.py – PASS: session-12 blocks updated (v6.3, annotation
  assertions, free-mode ranges) + new blocks 20 (displayed=stored,
  Q > 0 untouched forms), 21 (Alt+A four focus targets), 22 (territory
  км²|м² incl. round-trip), 23 (window memory incl. off-screen), 24
  (add-tree button/auto-участок/delete-only-selection/multi-batch),
  25 (tables policy/wrap/scrollbar), 26 (IZ/GS libraries), 27 (fire
  modes reference), 28 (annotation lifecycle), 29 (measures library).
* run_qa.cmd – PASS; vision-reviewed: qa_matrix (reopened doc window
  full), qa_inspector_territory (label + км² combo), qa_hierarchy
  (7 buttons), qa_kb_measures (4 columns, bottom-left buttons,
  h-scrollbar), qa_kb_iz / qa_kb_gs (engineering format, «расчётная
  величина», «× L», buttons), qa_kb_fire_modes (8 rows, exact names,
  a₁·F and 2,5·10⁻⁵), qa_canvas / qa_sheet (annotation boxes, no
  floating header or free-floating Q; presence of two annotations in
  both scenes verified programmatically after one downscale misread).
* All tests run offscreen; the real knowledge_base.json was never
  modified by tests (in-memory snapshots restored).

## Known issues / notes

* Task 8 dust rows cite П2.1 flow/medium selection per the customer's
  ruling, although the KB/engine give dust modes P = 1 with sources
  «прил. № 3 (классы 2–6 / класс 1)» – documented divergence between
  the reference table and the engine (customer's explicit choice).
* Measures with structural semantics (SIL/ТО/резервирование/
  взрывозащита/категория среды/молниезащита/самовоспламенение) have no
  single numeric coefficient; their coefficient is editable display
  text, engine semantics unchanged. Numeric engine-binding covers
  k-records (износ, герметичность, вибро-контроль) and
  p_success-records (дренаж, датчики утечки) + all new type-"k"
  measures.
* Building form default bln_H is now 20.0 (DEFAULT_PROPS) instead of
  the previously displayed 100.0.
* Library edits are in-memory until «Сохранить» (kb.save writes
  knowledge_base.json); the window close dirty-guard reminds.
* Free-mode margin is ±100 000 px (scrollbar ranges scale with zoom);
  the doc scene/PDF remain bounded to the layout rect.
* The QA suite regenerates all artifacts after every task batch; the
  manual `run_app.cmd` start remains the user's habit.
