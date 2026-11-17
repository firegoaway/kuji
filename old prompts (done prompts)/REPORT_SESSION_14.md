# SESSION 14 REPORT – Kuji 6.4.0

Date: 11.11.2026. Base: v6.3.0 (sessions 1–13).
Subject: hierarchy-integrity + engine-cascade + visual-state session,
seven tasks. All LOCKED Q&A decisions implemented as specified; no
locked decision was reopened and no clarifying questions were needed
(the prompt locked every ambiguity). Version → **6.4.0**; KB
`meta.version` stays **«6.1»** (no schema change; KB data untouched).
**Addendum (same day, → 6.4.1): post-delivery defect report
«trees ГГ/ГЖ/ЛВЖ/Пыли have no GS causes» – see the «Session 14/1»
section at the end.**

**Acceptance:** `smoke_test.py` – PASS (18 blocks of session 13 +
rewritten confectionery/cascade blocks 3/4 + new block 16 state
assertions + new blocks 19–20); `gesture_test.py` – PASS (blocks 1–29
of sessions 12/13, assertions updated where behavior changed
deliberately: version 6.4, block 20 «показано = записано» exception,
+ new blocks 30–36); `run_qa.cmd` – PASS, artifacts regenerated
(including the new qa_hierarchy3 multi-select shot) and
vision-reviewed (glm-5.3-flash, crops + 1.4–2× upscale).

## Task 1 – territory nesting bug (screenshots №1/№3/№4)

* Root cause confirmed exactly as diagnosed:
  `PARENT_RULES[TERRITORY]` is an EMPTY set and `can_add` treated an
  empty set as «allowed with ANY parent» (`if not allowed: return
  True`) → «Добавить территорию» with a building/участок/помещение
  selected attached the territory as a CHILD of that object → the
  deep alternating chains of the screenshots.
* Fix (three layers):
  1. `objects.py::can_add` – empty allowed-set now means
     `parent is None` (territory only at root).
  2. `hierarchy_panel.add_kind` – `kind == TERRITORY` always routes to
     `parent = None` regardless of selection (the sibling rule
     «territory under territory» already produced a root sibling);
     button stays always enabled; error text of `add_child` for
     territory explains the root rule.
  3. **Load repair (LOCKED вариант (а))** – `load_from_dict` now
     returns a repair report: nested territories are lifted to root
     WITH their whole subtrees (children keep relative structure);
     then the remaining structure is re-validated against
     `PARENT_RULES` – invalid placements move to the nearest valid
     ancestor; if none exists in the chain, to the first territory
     that is neither the node itself nor its descendant (a new
     «Территория 1» is created only when no territory exists at all;
     documented conservative choice: exotic kinds may land on a
     formally imperfect level, but nothing is ever lost and
     territories are always at root). All object ids (and therefore
     tree `owner_id`s) are preserved. When a repair changed something,
     `MainWindow._load_project_data` shows an 8000 ms status message.
* Tooltips/statusTip updated (see strings below).
* Tests: smoke block 19 (can_add matrix + damaged-dict repair with
  exact expected report `{"lifted_territories": 1, "moved_nodes": 2}`,
  id set preserved); gesture block 30 (select building → click
  «Добавить территорию» → new territory AT ROOT, top-level count +1)
  and block 32 (full damaged project file → repaired in a live
  window, tree alive, status message asserted).

## Task 2 – Ctrl/Shift multi-select with the real mouse

* Root cause confirmed and found in TWO places:
  1. every `itemSelectionChanged` → `_on_select` → `object_selected`
     → `MainWindow._on_object_selected` → `_refresh()` →
     `hierarchy.rebuild()` → `tree.clear()` + refill → the
     multi-selection died instantly;
  2. (discovered live, gesture block 31) even without the rebuild,
     `_on_select` → `select_object()` → `setCurrentItem()` performs a
     ClearAndSelect and wiped the Ctrl-selection.
* Fix:
  1. `MainWindow._refresh(rebuild_hierarchy: bool = True)` – the
     selection paths (`_on_object_selected`,
     `_on_scenario_selected`) refresh the canvas/matrix/status/trash
     WITHOUT rebuilding the hierarchy tree; structural changes keep
     the full rebuild.
  2. `_on_select` only updates the panel-side `_selected` state – it
     never touches `setCurrentItem` (the tree state is already
     correct: the click made the item current).
  3. Multi-select semantics unchanged (session 13 / Q&A 12):
     inspector shows the last-clicked (current) object; Delete opens
     the ONE batch window; `_selected_deletable_nodes` unchanged.
* Tests: gesture block 31 uses REAL `QTest.mouseClick` on
  `visualItemRect` centers (with `scrollToItem` + viewport-clamped
  click X – the wide long-name column shifts centers out of the
  viewport): plain click → 1 selected; Ctrl+click → 2; +Ctrl on a
  child → 3; plain click resets to 1; Shift+click → range of 2;
  batch Delete from a real Ctrl-selection → one window, both objects
  removed, territory alive. Programmatic `setSelected` with blocked
  signals is used ONLY for the qa_hierarchy3 screenshot.

## Task 3 / 3.1 – collapsed state of the hierarchy

* Root cause confirmed: `rebuild()` unconditionally called
  `tree.expandAll()` + `_expand_scenario_groups()`, and rebuild ran
  on every selection change (Task 2 coupling).
* Fix:
  1. `rebuild()` captures the collapsed state BEFORE `clear()`
     (a set of collapsed object ids + a set of owner ids of collapsed
     «Группа сценариев» groups) and restores it after the refill via
     `_apply_expansion`; unknown/new items default EXPANDED.
  2. New участки (AREA) and наружные установки (OUTDOOR) are added
     COLLAPSED (LOCKED: only these two kinds; `add_kind` /
     `_add_tree_for` call `collapse_node`; the auto-«Участок N» from
     «Добавить дерево» on a room too). Buildings/rooms/compartments
     stay expanded.
  3. **Persistence (LOCKED 11б):** format 5 `ui` dict –
     `{"hierarchy_collapsed": [oid…], "hierarchy_groups_collapsed":
     [owner_oid…]}` written by `MainWindow._save_project`, applied by
     the new `MainWindow._load_project_data` (also the testable seam
     for opening a project without the file dialog); unknown ids
     ignored; files without saved state open fully expanded.
* Tests: gesture block 32 – new участок/установка collapsed while
  building/room expanded; a manually collapsed building stays
  collapsed across selection changes AND a full `_refresh()`; a
  collapsed «Группа сценариев» survives rebuilds; save/load round
  trip restores both lists in a fresh window; QA qa_hierarchy shows
  «Участок 1» with the ▶ arrow (vision-verified).

## Task 4 – compact unit combo «км²|м²»

* Cause confirmed: the combo was a `wide_combo` (QSS
  `QComboBox { min-width: 110px; }` + adaptive popup machinery).
* Fix: new `compact_combo()` helper in `controls.py` (choice
  documented in its docstring: a helper rather than one-off sizing,
  because unit selectors may appear elsewhere) – objectName
  `compactCombo`, `AdjustToContents`, Fixed size policy; QSS rule
  `QComboBox#compactCombo { min-width: 0px; padding: 4px 6px; }`
  exempts it from the shared min-width, so all other combos (KB,
  forms) stay wide. The territory unit combo switched to it; the
  standard popup renders «км²»/«м²» fully readable.
* Test: gesture block 33 – objectName + `width() <= 90` (measured
  49 px); QA qa_inspector_territory vision-verified (compact combo
  next to the spin, no wide combo).

## Task 5 – ТГМ area/type inheritance cascade (engine + forms)

* Engine: `CalcContext` gained `tgm_chain` – a list of the levels'
  OWN props dicts (nearest first: участок → помещение → здание;
  outdoor = [itself]), built by `MainWindow.ctx_map` via the new
  `objects.tgm_levels(node)` helper (explicitness = key presence;
  the chain is built from the object tree, NOT from the merged
  `effective_properties` – the merged dict cannot show which level
  set what; documented in the helper). `tgm_multiplier` resolves:
  * **F** = first level with an explicit `area_m2` (участок counts
    only when its `site_type` is «area»; linear/apparatus участки
    never feed the ТГМ area);
  * the П1.3/П1.4 switch `F > 10 000 м²` uses this effective F;
  * **type** = nearest level with an explicit `p13_type`/`p14_type`
    for the effective-F key; nothing set anywhere → multiplier 0
    with the «не выбран тип (П1.3|П1.4)» note; no area anywhere →
    «не задана площадь (участок/помещение/здание)».
  * Outdoor keeps its own area/type (`tgm_levels` → [self]);
    lightning/vent/universal-k still read the merged
    building/room/site props as before.
  * Backward compatibility: `tgm_chain is None` (old direct calls)
    → chain = `[building_props]` – session-13 style contexts keep
    working (smoke blocks 10/11 untouched).
* Forms (variant (а) – the ONE deliberate exception to the
  session-13 «показано = записано» invariant):
  * room form and участок form get the «Тип (П1.3)/(П1.4)» combo
    with the placeholder row **«– наследуется –»** (data None):
    nothing is written until an explicit choice; re-picking the
    placeholder removes the explicit key; the label switches by the
    level's effective F; the tooltip shows the inherited type title
    while on the placeholder;
  * room/участок area: own value → normal spin; absent → the
    inherited effective F shown grey (property `inactive="true"`,
    QSS `QDoubleSpinBox[inactive="true"] { color: CUTOFF; }`) with
    the «наследуется от «Здание»/«Помещение»…» tooltip; editing
    writes the level's OWN value and recolors the field;
    linear/volume значения materialize as before (the exception
    covers area + type only);
  * the building combo (and outdoor) keep materializing as today
    (the building is the last link of the cascade).
* Confectionery control example (smoke block 3) moved to the new
  semantics: area 2960.77 + `p13-multi` now live at the УЧАСТОК level
  (`CalcContext(tgm_chain=[...])`); the numeric result stays
  2,30·10⁻⁵. The recalculated-existing-projects consequence is
  documented in README («каскад ТГМ» bullet) and here: a ТГМ tree
  whose owner building carried the area now resolves F over
  участок → помещение → здание, so values materialized on the
  building still apply (fallback), but any explicit room/участок
  value now overrides – Q values of existing projects change
  accordingly (customer-confirmed, Q&A 4).
* Tests: smoke block 4 extended (участок overrides помещение
  overrides здание; room-type override; empty chains → 0 with exact
  note; outdoor own); gesture block 34 (live window): placeholder
  shown and NOT stored (`p13_type` absent until explicit pick),
  inherited grey area 2000 from the building, own inputs stored and
  recolored, engine multiplier 9·10⁻⁵·300 via the room's area+type,
  собственная площадь 25 000 → auto-switch to П1.4 labels at every
  level + 0 with the «не выбран тип (П1.4)» note until the building
  gets `p14_type`, then a·F^b computes.

## Task 6 – node state colors

* Single source: `compute_layout` computes a per-node `state` field
  on `NodeGeo` – gs/iz: `"set"` when the node has ≥1 cause (the
  old «не задано» condition inverted); fire: `"ok"` when
  `check_tree` returns NO failed issues for the tree (LOCKED Q&A 5:
  validator-clean, not merely Q > 0). `check_tree` runs ONCE per
  tree per layout (cheap), never per paint. `render.draw_node`
  resolves `STATE_STYLE` (LOCKED hexes: «set» border #2563EB /
  fill #EFF6FF; «ok» border #7C3AED / fill #F5F3FF) with fallback
  to the class `KIND_STYLE` – canvas and PDF share the same NodeGeo,
  so WYSIWYG holds by construction. Node text content unchanged.
* Tests: smoke block 16 (empty gs → state ""; filled gs/iz → "set";
  fire "ok" for a validator-clean tree; an invalid gs pick → fire
  ""); gesture block 35 (live layout states through
  `canvas.controller.layout`, invalid-cause toggle → fire ""
  → fix → "ok"). QA: qa_canvas/qa_sheet now carry three demo trees
  (two filled → blue/violet; one without causes → amber/red +
  gray «не задано») – vision-verified on canvas crops AND on the
  schematic PDF page crop (violet #7C3AED/#F5F3FF + blue
  #2563EB/#EFF6FF confirmed pixel-wise).

## Task 7 – mathematical notation everywhere + matrix cleanup + caret

* New module `eta/core/numfmt.py` – the ONE shared source:
  `fmt_q` (moved verbatim from layout.py, re-exported there so all
  existing imports keep working), `fmt_num` (numbers for
  formulas/values: `%g` text with comma, engineering «9·10⁻⁵»
  whenever `%g` would show an exponent – «1200»/«0,05»/«2960,77»
  stay plain), `parse_eng` (both notations).
* Display sweep (grep-verified all `:g` user-facing spots):
  * `main_window._refresh_matrix` Q column: `f"{row.q:.3e}"` →
    `fmt_q` («3,240e-06» → «3,24·10⁻⁶»);
  * `model.py` formula pieces (multipliers, notes, P₂₁,
    1−e^(−λ), lightning, direct P, П1.2 ×L) – `fmt_num`;
  * PDF report values (F, S/L/H, A, area/length/volume, presence,
    Kσ, λ/P/q) – `fmt_num` (formulas keep the e-power STRUCTURE,
    only numbers inside change: `1−e^(−3,2·10⁻⁵)`);
  * hierarchy scenario-row tooltip `Q = …` – `fmt_q`;
  * cause-picker suffix in `_CausePickerDialog` – `fmt_num`;
  * inspector SIL combo / universal-k tooltip – `fmt_num`.
* Matrix formula cleanup (LOCKED: matrix ONLY): implemented in the
  matrix layer – `matrix.build_matrix` strips `\s*\((табл\. )?П\d+
  .\d+\)` from `r.formula`; both matrix consumers (main-window
  table and the PDF matrix sheet) get refs-free formulas, while the
  REPORT path reads the model formula directly and keeps its
  references. Choice documented in matrix.py.
* Input parsing (LOCKED): `parse_eng` accepts e-notation
  («1e-6», «1,02e10»), caret («1^-6», «2,52^-12», where m^e =
  m×10^e – caret is ×10^, NOT exponentiation), and the product
  forms «6,2·10^-4»/«×10^»/«*10^»; invalid input → None.
  `theme.parse_sci` delegates to it (single implementation, name
  kept for existing importers). `_NumberEditor` hint and error text
  name both notations. Display of stored values is ALWAYS
  engineering (never echoes the raw input).
* Tests: smoke block 20 (parser unit checks incl. invalid → None,
  `parse_sci` delegation, `fmt_num` cases, matrix formula without
  «(табл.» but with «9·10⁻⁵·2960,77», model formula keeping the
  ref); gesture block 36 (matrix Q column all «·10» superscripts,
  no «e-»; formula column without «(табл.»; `_NumberEditor` seam
  accepts `2,52^-12` and rejects «ой»; PDF report text via
  QPdfDocument.getAllText still contains «табл.П1.3» – compared
  space-insensitively because getAllText injects stray spaces).

## Before → after strings (all changed user-facing texts)

* Toolbar territory tooltip (enabled): «<b>Добавить
  территорию</b> – корень иерархии объектов<br>(доступно всегда)» →
  «<b>Добавить территорию</b> – создается в корне иерархии<br>
  (доступно всегда, независимо от выделения)»; statusTip
  «Территория» → «Добавить территорию – создается в корне
  иерархии».
* add_child error for territory: «…выделите родителя» → «…выделите
  корень иерархии – территория создается всегда в корне,
  независимо от выделения».
* NEW repair messages: «Файл содержит вложенные территории – N
  территорий перемещены в корень иерархии; исправлено размещений:
  M» / «Структура иерархии исправлена – перемещено объектов: N»
  (8000 ms).
* tgm_multiplier notes: «не задана площадь здания/установки» →
  «не задана площадь (участок/помещение/здание)»; «не выбран тип
  здания (П1.3/П1.4)» → «не выбран тип (П1.3/П1.4)»;
  «a₁·F = 9e-05·2960.77 (табл. П1.3)» → «a₁·F = 9·10⁻⁵·2960,77
  (табл. П1.3)» (same for a·F^b).
* Matrix Q column: «3,240e-06» → «3,24·10⁻⁶»; matrix formulas:
  «…[a₁·F = 9e-05·1200 (табл. П1.3)]·1−e^(−3e-05)» → «…[a₁·F =
  9·10⁻⁵·1200]·1−e^(−3·10⁻⁵)».
* Scenario-row tooltip: «Q = 3.24e-06 год⁻¹» → «Q = 3,24·10⁻⁶
  год⁻¹»; cause-picker suffix «· 3.2e-05» → «· 3,2·10⁻⁵».
* Validator: «Множитель ТГМ не рассчитан: … – заполните свойства
  здания/наружной установки» → «… – заполните площадь и тип на
  участке, в помещении или здании (первое явное значение уровня)».
* Room/участок forms: NEW rows «Тип (П1.3):»/«Тип (П1.4):» with the
  placeholder «– наследуется –» (tooltips: «Наследуется: <тип> (от
  ближнего уровня с явным выбором)» / «Тип здания по табл.
  П1.3/П1.4; строка «– наследуется –» берет тип от помещения или
  здания (в свойствах уровня ничего не пишется)»); inherited area
  tooltip «Наследуется от «Здание» (2000); введите значение, чтобы
  задать собственную площадь уровня»; участок section «РАСЧЕТНЫЕ
  СВОЙСТВА» (new). Room area label «Площадь, м²:» unchanged.
* `_NumberEditor`: «Допускается запись вида 3,2e-5 или 3.2e-5» →
  «Допускается запись вида 3,2e-5, 3.2e-5 или 3,2^-5 (каретка –
  умножить на 10 в степени)»; error «…например, 3,2e-5» → «…например,
  3,2e-5 или 3,2^-5».
* Territory unit combo: `wide_combo` (~200 px) → `compact_combo`
  (49 px measured).

## Files touched (session 14)

eta/core/numfmt.py (NEW – fmt_q/fmt_num/parse_eng) ·
eta/core/objects.py (can_add guard, load repair + report, tgm_levels)
· eta/core/model.py (CalcContext.tgm_chain, cascade tgm_multiplier,
fmt_num formulas) · eta/core/matrix.py (refs stripped, matrix layer)
· eta/core/layout.py (fmt_q re-export from numfmt, NodeGeo.state,
validator-driven states) · eta/core/validation.py (cascade hint) ·
eta/ui/render.py (STATE_STYLE LOCKED colors in draw_node) ·
eta/ui/theme.py (parse_sci → parse_eng, QSS compactCombo + inactive
spin) · eta/ui/controls.py (compact_combo) ·
eta/ui/hierarchy_panel.py (territory tooltips/routing, expansion
capture/restore, collapse_node/collapsed_ids/apply_collapsed,
selection without setCurrentItem) · eta/ui/main_window.py
(_refresh split, _load_project_data + repair message, ui-dict
save/load, ctx_map chain, tgm_view, matrix fmt_q, inspector wiring)
· eta/ui/inspector_panel.py (compact unit combo, inherited
type/area builders, room/участок forms, fmt_num spots) ·
eta/ui/kb_window.py (_NumberEditor both notations) ·
eta/export/pdf_export.py (report values fmt_num) ·
eta/__init__.py (6.4.0) · smoke_test.py · gesture_test.py (blocks
30–36 + updated assertions) · visual_qa_runner.py (mixed-state demo
tree, qa_hierarchy3 multi-select shot) · README.md · qa_artifacts
(regenerated).

## Test results / Visual QA

* smoke_test.py – PASS: 21 printed blocks (18 previous, blocks 3/4
  rewritten to the cascade semantics, block 16 extended with state
  flags, new blocks 19 «Задача 1» and 20 «Задача 7»).
* gesture_test.py – PASS: session 12/13 blocks updated (v6.4
  assert; block 20 now asserts «area_m2» NOT materialized on the
  участок) + new blocks 30–36. GESTURES PASSED, exit 0.
* run_qa.cmd – PASS; artifacts regenerated (qa_stats: app 6.4.0,
  pdf_rendered true, report_pages 5). Vision review (crops +
  1.4–2× upscale): qa_canvas left/right (filled tree: GS/IZ blue
  #2563EB/#EFF6FF, fire violet #7C3AED/#F5F3FF; empty tree: amber
  #B45309 GS, red #B91C1C IZ, red #DC2626 fire, gray «не задано»);
  qa_sheet + qa_pdf_page1 (same states on the doc scene / PDF
  schematic page – WYSIWYG); qa_hierarchy (Участок 1 ▶ collapsed,
  Здание/Помещение ▼ expanded, both наружные установки ▶);
  qa_hierarchy3 (two territories simultaneously highlighted);
  qa_matrix (Q column «·10⁻» superscripts, no e-notation);
  qa_inspector_territory (compact combo ≈1/3 of the spin width, no
  wide combo); qa_pdf_report («(табл. П1.3)» references present,
  «a₁·F = 9·10⁻⁵·2400», «1−e^(−3,2·10⁻⁵)»).
* The real knowledge_base.json was never modified (no KB edits this
  session; tests keep their in-memory snapshots).

## Known issues / notes

* ТГМ semantics change recalculates existing projects (LOCKED
  Q&A 4): values previously taken from the building now resolve
  over участок → помещение → здание; a building-materialized area
  still applies as the last link, but any explicit room/участок
  value overrides it.
* The «показано = записано» invariant now has exactly ONE
  deliberate exception (room/участок area + type, variant (а));
  all other forms still materialize.
* Programmatic `select_object(hidden_item)` still auto-expands the
  item's collapsed ancestors (Qt scrollTo behavior) – irrelevant
  for real clicks (a hidden row cannot be clicked) and covered by
  the collapse tests via visible objects.
* QPdfDocument.getAllText injects stray spaces inside words; the
  gesture PDF assertion compares space-insensitively. The temp
  PDF in block 36 is unlinked where Windows permits (guarded).
* run_qa.cmd exits with code 1 on teardown AFTER all artifacts and
  stats are written (offscreen quit race, cosmetic; visible in
  previous sessions too) – judged by artifacts + qa_stats.json.
* QA runner lesson recorded: a stray modal (e.g. add_kind with no
  valid selection) blocks an offscreen run forever – the demo
  builder must keep the add-flow preconditions valid.
* Участок counts toward the ТГМ area only when its type is
  «участок (м²)» (linear/apparatus участки feed П1.2 length /
  volume instead) – documented in tgm_levels.

---

# SESSION 14/1 ADDENDUM – Kuji 6.4.1 (same day)

Customer defect report (screenshot): «У деревьев ГГ, ГЖ, ЛВЖ и Пыли
отсутствуют причины образования ГС в ноде ГС» – a ГГ tree on
«Участок 3», GS node «не задано», the «Добавить причину» dialog empty.

## Diagnosis (code-verified)

* Primary (design of session 10): the Участок had the DEFAULT type
  «участок (м²)», and the KB attaches ГГ/ГЖ/ЛВЖ/Пыль GS causes to
  site kinds «аппарат/установка (м³)»/«линейный объект (м)»
  (`gs_for("gg", "area") == []`); the picker therefore legitimately
  showed nothing. No data was lost – switching the участок type
  restored the list.
* Secondary (real defect, found while reproducing): the picker
  resolved the site kind from the HIERARCHY SELECTION
  (`selected_owner()`), not from the tree's own `owner_id` – with a
  помещение/здание selected (the «show all child trees» mode) the
  list was empty even for a correctly-typed аппарат-участок.

## Customer rulings (Q&A, LOCKED)

1. «Показывать все причины» – remove the site-kind filter from the
   cause picker: all GS causes of the scenario type are offered on
   ANY участок, including «м²»; the user decides applicability.
2. «Оставить все 5 типов» – the «Добавить дерево» menu is unchanged.
3. Custom: «Нет, причины ГС должны быть доступны на м²-участке без
   ловушек и валидаций. А в формулу Q должна идти площадь участка
   м², вместо м³ или м. То есть, по части событий ГС надо дать
   пользователю возможность самому принимать решение.» → no new
   validator note; the П1.2 multiplier on a м²-участок uses the
   участок's AREA (м²) instead of the length/volume values.

## Implemented (6.4.1)

* `inspector_panel._cause_records/_pick_cause` – GS records =
  `kb.gs_for(scenario_type)` without a site kind (applies-only
  filter); the owner/site-kind resolution (and the interim
  `set_objects` seam from the secondary-bug fix) became unnecessary
  and was removed. ИЗ list unchanged (whole library).
* `validation.check_tree` – availability set built without the site
  kind: a cause mismatching the SCENARIO type is still flagged
  («недоступна … для этого типа участка/сценария»), the участок type
  no longer triggers it.
* `model.CalcContext.p12_value(explicit)` (new shared helper) –
  П1.2 multiplier: explicit `len_m` on the GS node wins; on a
  «м²»-участок → the участок's effective `area_m2` (м²) – inherited
  from помещение/здание when the уровень has no own value, per the
  Task-5 cascade props; linear участки keep `length_m` (м); the
  formula note shows the unit («× 800 м² (П1.2)»). `_q_gs` and the
  PDF report's «ГС: …» line both consume the helper (one source).
* `main_window._apply_library_equipment` – equipment templates now
  apply their full GS list without site-kind hiding (the
  «N разновидностей ГС скрыто» status message can no longer trigger
  for site reasons; the seam is kept).
* Tests: smoke block 8 extended (П1.2 × 800 м² on a м²-участок with
  the exact Q and the «× 800 м² (П1.2)» note; explicit len_m = 250
  wins with «× 250 м (П1.2)»; `gs_for("gg")` unfiltered while
  `gs_for("gg", "area")` stays [] – the KB method itself is
  unchanged; validator silent for a correct cause on a м²-участок);
  gesture block 37 rewritten (picker records on a default м²-участок
  > 20 incl. разгерметизация + трубопровод; ИЗ non-empty; validator
  flags only a scenario-type mismatch; `p12_value(None)` → «м²»).
  Both suites PASS (exit 0); `run_qa.cmd` regenerated (qa_stats:
  app 6.4.1).

## Known issues / notes (14/1)

* The session-10 canon «м²-участок – только ТГМ» is superseded for
  the PICKER and VALIDATOR by this customer ruling; the KB field
  `site_kinds` and `gs_for(stype, site_kind)` remain (used by tests
  and available for future consumers), but no runtime path filters
  GS causes by the участок type anymore.
* On a м²-участок the П1.2 multiplier is the (possibly inherited)
  площадь in м² – a deliberate customer decision; the formula note
  and the PDF report show the unit explicitly, so the engineer sees
  what was multiplied.

---

# SESSION 14/2 ADDENDUM – Kuji 6.4.2 (same day)

Customer console report: endless
`AttributeError: 'PySide6.QtCore.QPoint' object has no attribute
'toPoint'` from `canvas.py` lines 87/154 on every mouse move over the
canvas (plus `QAction::event: Ambiguous shortcut overload: Alt+A`).

## Diagnosis

* `NodeItem.hoverEnterEvent` / `AnnotationItem.hoverEnterEvent`
  computed the tooltip position as
  `canvas.mapFromScene(rect.center()).toPoint()`. In this PySide6
  build `QGraphicsView.mapFromScene` resolves to the INTEGER
  overload and returns a **QPoint**, which has no `toPoint()` (only
  `toPointF`). Every hover over a node/reference node raised inside
  the Qt event dispatch: the canvas hover tooltip never showed and
  the console flooded. (The session-12/13 tests never exercised item
  hover — the gesture mouse helpers already wrapped the same call in
  `QPointF(...)`, which is why the quirk never failed a test.)
* The `Ambiguous shortcut overload: Alt+A / Alt+Ф` warnings are
  cosmetic: each twin pair sits on ONE action; on the Russian layout
  both sequences alias to the same physical key, Qt prints the
  ambiguity, and the action still fires (verified again by gesture
  block 21). The twins remain – they are the layout-independence
  fix; the warning is their known harmless cost.

## Fix (6.4.2)

* `canvas.py` (both hover handlers): the position is now computed as
  `QPointF(canvas.mapFromScene(rect.center())).toPoint()` – the
  QPointF constructor accepts both QPoint and QPointF, so the code
  is overload-agnostic; hover tooltips on nodes and reference nodes
  work again and the exception spam is gone. No other call sites
  were affected (`e.position().toPoint()` operates on QPointF;
  `gestures.py` already wrapped its calls).
* Regression: gesture block 38 invokes `hoverEnterEvent` /
  `hoverLeaveEvent` directly on a live NodeItem and AnnotationItem
  with crafted QGraphicsSceneHoverEvents – before the fix each call
  raised AttributeError; now the handlers must complete silently.
* Suites: smoke PASS; gesture PASS (38 blocks, exit 0);
  `run_qa.cmd` regenerated (qa_stats: app 6.4.2, pdf_rendered).
