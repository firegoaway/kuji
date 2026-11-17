# SESSION 10 REPORT – Kuji 6.0.0

Date: 10.11.2026. Base: v5.0.0 (sessions 1–9).
Subject: FULL PARADIGM REWORK of the event-tree calculation into five
invariant base scenario types (node-class model), hierarchy rework with
«Наружная установка», KB-apply flow gated on Участок selection,
«Логическое дерево событий» terminology, export matrix stretched to page
width + approved report sheet, switches instead of checkboxes, properties
panel cleanup, compact layout, delete-dialog defaults, hierarchy toolbar
layout. Both reference documents («1 Методология…», «Пример расчёта
частот для кондитерского цеха.md») were read end-to-end before any code;
all paradigm decisions were locked through user Q&A rounds (see
«Decisions»).

**Acceptance:** `smoke_test.py` – PASS (18 blocks, rewritten for the new
paradigm); `gesture_test.py` – PASS (12 scenario blocks, rewritten);
`run_qa.cmd` – PASS, artifacts regenerated and vision-reviewed
(qa_window, qa_matrix, qa_docview, qa_sheet, qa_switches, qa_kb_templates,
qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report – all PASS).
Version → **6.0.0**; KB `meta.version` → «6.0»; README rewritten;
format 5 clean break.

## Decisions locked by the user (Q&A)

1. Invariant tree for all five types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль):
   `Q_сценария = Q_вещество · Q_ОК · Q_ГС-разн. · Q_ИЗ-разн. · P_типа`,
   `Q_участок,k = Σ Q_сценариев × Kσ`; scenario count = combinatorics of
   ГС × расход × тип горения × ИЗ (no physical plausibility checks).
2. ТГМ multiplier from the BUILDING properties: a₁·F (П1.3), auto-switch
   to a·F^b (П1.4) when F > 10 000 м²; releases use П1.1 frequencies and
   П1.2 pipeline leak rates × routing length (length lives in Участок
   properties with the new type dropdown участок м² / линейный объект м /
   аппарат м³, defaults pre-filled).
3. П2.1 mapping: мгновенное → факельное (газ/двухфазная) / пролив
   (жидкость); последующее → вспышка / пролив; с изб. давлением →
   сгорание (взрыв) топливовоздушной смеси; пыль → дефлаграция +
   детонация; «Огненный шар» as a switch on the «Возникновение
   пожара/взрыва» node (2,5·10⁻⁵ год⁻¹ per apparatus, прил. 1 п. 5).
4. Node title «Возникновение пожара/взрыва» (for ТГМ – «…пожара»).
5. И/ИЛИ/НЕ machinery, badges, ghosts, right wing with barriers, domino
   cascades – REMOVED entirely (fixed structure, logic hard-wired).
6. Canvas topology fixed: Наличие вещества + Наличие ОК → ГС; ГС + ИЗ →
   Возникновение; scenarios as text lines on the node, in the matrix and
   the inspector; «Группа сценариев» under each Участок/установка in the
   hierarchy; selecting a scenario shows its tree with that scenario's
   frequency.
7. Serialization: format 5, clean break (formats 1–4 rejected with
   «Формат проекта устарел»).
8. KB: full rewrite in place (backup `knowledge_base_v5.json`), Kσ kept
   as a multiplier (default 1.0).
9. Protective measures redistributed with `target` field: молниезащита →
   Building/Установка, аварийная вентиляция (renamed) → Помещение,
   SIL/T_тест/дренаж/датчики/резерв/износ/герметичность/категория среды
   → ГС node, виброконтроль/взрывозащита → ИЗ node; расход and домино
   deleted.
10. Hierarchy: Наружная установка = standalone apparatus under Territory
    (building level), owns trees DIRECTLY; rooms only in buildings; trees
    only on Участки/установки (multi-selection semantics preserved).
11. Task 3: «Применить на холсте» disabled with tooltip unless an
    Участок/установка is selected; double-click on a template card equals
    the button.
12. Task 5 report sheet: approved composition («Отчет о расчете частоты
    возникновения пожара» – no «взрыва»), per-row formulas, toggle in the
    export dialog (default on); PDF header drops «(FTA + ETA)».
13. Extra requests: delete dialogs default to «Удалить» (Task 8);
    hierarchy toolbar icons bigger and evenly spread (Task 9).

## Task 1 – the core (model/KB/serialization)

* `knowledge_base.json` (v6.0): sections meta, scenario_types (5),
  gs_causes (68: П1.1 by apparatus class × hole incl. полное разрушение,
  direct П1.1 fire events for floating/fixed-roof tanks, П1.2 for seven
  pipeline diameters × leak size, gs-tgm-surface), iz_causes (15: ГОСТ
  табл. 9 + молния + статика + нагретые вещества, `electrical` flag),
  fire_types (8) with П2.1 mapping, p21/p13/p14 tables, flow_titles,
  equipment_templates (16), property_modifiers (13, +target). Old
  sections (initiating_events, barrier_events, cause_events, presets,
  echelons, fta_gates, pending_events, value_library) deleted.
* `eta/core/model.py` – rewritten: `Presence` (время/частота modes,
  Q = 1−e^(−f)), `GSCause` (with len_m), `IZCause`, `ScenarioRow`,
  `CalcContext` (tgm_multiplier with П1.3/П1.4 auto-switch, lightning_q
  from building props, vent_k), `TreeModel.scenarios/total_q/
  display_lines` implementing the confirmed formula; pedal multipliers
  (wear ×k, hermetic ×0.5, SIL PFD with voting, T_тест PFD_avg, drain
  ×0.05, leak-detectors ×0.2, ventilation 1/(A/12+1); ИЗ: vibro ×0.7,
  exproof zeroes electrical causes). Verified against the confectionery
  example: ТГМ Q = 2.297·10⁻⁵ vs document's 2.30·10⁻⁵; П2.1 exact to
  1e-9; ГГ combinatorics 4 расхода × 3 типа × N ИЗ.
* `eta/core/objects.py` – kinds territory/building/compartment/room/
  area/outdoor (EQUIPMENT deleted), PARENT_RULES, SITE_TYPES/SITE_FIELD,
  DEFAULT_PROPS with pre-filled values (building: area_m2/p13_type/
  p14_type/bln dims; area: site_type switch; outdoor: area+types+
  молниезащита), `effective_site_type`.
* `eta/core/serializer.py` – format 5 (objects + trees + ui),
  `UnsupportedFormatError` for older formats.
* `eta/core/validation.py` – new rules: empty ГС/ИЗ causes, duplicates,
  causes unavailable for the site type/scenario type, ТГМ context
  missing, Kσ range.
* `eta/core/layout.py` – rewritten for the fixed 5-node graph (3 occupied
  columns, compact by construction – Task 7), tree headers with Q,
  per-tree prefixed node ids, bezier edges kept.
* Deleted: `eta/core/domino.py`, `eta/core/generator.py`.

## Task 1/2/3 – UI rework

* `canvas.py` rewritten: NodeItem/EdgeItem/HeaderItem from the layout
  bundle, node click → inspector, hover → modern tooltip, sticky/free
  viewport, gestures mixin kept; pins/pickers/DnD/badges/domino removed.
* `render.py` rewritten: flat node drawing by class (presence/gs/iz/fire
  accent bars), bezier edges with tangent arrowheads, tree headers.
* `inspector_panel.py` rewritten: object forms (building: F_зд, П1.3/П1.4
  dropdowns, S/L/H, молниезащита switch + категория bound; room:
  аварийная вентиляция switch + A bound; area: «Выберите тип» + value
  field; outdoor: площадь/типы/молниезащита; territory/compartment) and
  tree-node forms (presence режим/значение, ГС/ИЗ cause blocks with
  «Добавить причину…» picker and «Убрать», len_m field for П1.2, node
  pedals, fire: Kσ + «Огненный шар»). Inherited-props dump and «Путь:»
  line removed (Task 6, carried into the rewrite).
* `hierarchy_panel.py` rewritten: 6-button toolbar (outdoor glyph added
  to icons.py/theme palette) evenly spread (Task 9), «Группа сценариев»
  with grouped scenario rows, context menu with «Добавить дерево…»,
  delete confirmation defaulting to «Удалить» (Task 8), F2/double-click
  rename.
* `kb_window.py` rewritten: «Шаблоны оборудования» (cards + details +
  «Применить на холсте» gated on selection, Task 3), table editors for
  ГС/ИЗ/типы горения/защитные меры, read-only П1.3/П1.4/П2.1 tables,
  close guard kept. `event_picker.py`, `palette_panel.py`,
  `matrix_view.py` deleted.
* `main_window.py` rewritten: tree ownership + ctx_map per owner,
  selection semantics (scenario → its tree; object → owners_in trees),
  inspector wiring (add/remove cause signals), KB apply with site-kind
  filtering of template causes (dropped varieties reported in the status
  bar), format-5 save/load, doc window, status bar ΣQ per tree, menus
  (Ctrl+N/O/S/E, F9, Alt+A, Delete), QSettings + migration.
* `matrix.py`/`docview.py`/`dialogs.py` adapted; `pdf_export.py`
  rewritten (see Task 5).

## Task 0 – switches

`eta/ui/switch.py` (new): `ToggleSwitch` (QAbstractButton, 34×18 track,
white knob, ACCENT on, 130 ms slide, instant offscreen), `bind_fields`.
Deployed: inspector pedals + lightning/ventilation blocks, KB equipment
tab rows via `QFormLayout.setRowVisible`, KB pending filters, event
picker filters (panel later deleted with the old KB window; switches
live on in templates tab). Live visibility: SIL block, wear k,
«Категория защиты», vent A-field. QA: `qa_switches.png` vision PASS.
Fixed during QA: stale-widget overlap in rebuilt forms (setParent(None)
before deleteLater) – root cause of garbled double text in screenshots.

## Task 4 – terminology

«галстук-бабочка» removed from every live file (main.py, eta/__init__,
pdf header, canvas/validator messages, comments, README, KB meta.title –
byte-safe script). Historical prompts/reports untouched. PDF header now
«Логическое дерево событий – имя» («(FTA + ETA)» dropped per Q&A).

## Task 5 – export

* Matrix sheet: full page width (weighted columns), thin separators,
  blue totals per tree (`Q_возникновение`), superscript fmt_q values.
* Report sheet (approved layout): «ОТЧЕТ О РАСЧЕТЕ ЧАСТОТЫ
  ВОЗНИКНОВЕНИЯ ПОЖАРА – владелец · тип · проект · дата»; sections
  ОБЪЕКТ И ПАРАМЕТРЫ / ИСХОДНЫЕ ДАННЫЕ (causes with sources) / РАСЧЕТ
  (per-row formulas) / РЕЗУЛЬТАТЫ / ИСТОЧНИКИ + signature line; toggled
  by «Добавить отчетный лист» (default on) in the export dialog.
* Engineering fix: one QPainter per document with newPage() (repeated
  begin/end silently dropped report pages); mm-coordinate painter
  (254 dpi ×10) with pixel fonts; QPdfDocument renders composited on
  white for QA.
* QA vision: matrix page PASS (full width, readable, totals), schematic
  PASS, report page PASS (title, sections, stamp without FTA+ETA).

## Task 7 – compact layout

New layout is compact by construction: three occupied columns per tree
(no empty echelon gaps), measured one-tree width 696 px; smoke block 16
asserts bounds; `qa_window.png` shows compact trees (vision PASS).

## Tasks 8/9 (user-added)

* Delete confirmations (hierarchy node, tree): «Удалить» is default AND
  focused → Delete+Enter/Space confirms (gesture block 8 verifies both).
* Hierarchy toolbar: BTN 34→44 px, icons 22→28 px (ICON_PX_HIER), seven
  equal stretches; probe showed gaps 19/19/20/19/19 px, symmetric edges.

## Files touched (session 10)

eta/__init__.py (6.0.0) · eta/core/{kb, model, objects, serializer,
validation, layout, matrix}.py (rewritten) · eta/core/{domino,
generator}.py (deleted) · eta/ui/{canvas, render, inspector_panel,
hierarchy_panel, kb_window, main_window, dialogs, docview}.py
(rewritten/adapted) · eta/ui/switch.py (new) · eta/ui/{event_picker,
palette_panel, matrix_view}.py (deleted) · eta/ui/{theme, icons}.py
(ICON_PX_HIER, outdoor glyph) · eta/export/pdf_export.py (rewritten) ·
main.py (docstring) · knowledge_base.json (v6.0; backup v5) ·
smoke_test.py, gesture_test.py, visual_qa_runner.py (rewritten) ·
README.md (rewritten) · qa_artifacts (regenerated).

## Test results / Visual QA

* smoke_test.py – PASS, 18 blocks (KB integrity, presence modes, ТГМ vs
  confectionery example, П1.3/П1.4 auto-switch, ГГ combinatorics and
  exact П2.1, media mapping, dust/fireball, П1.2 × length, lightning,
  pedal multipliers, Kσ, matrix, hierarchy rules, gs_for gating,
  format-5 round-trip + format-4 rejection, validator, compact layout,
  ToggleSwitch, icon palette coverage incl. «outdoor»).
* gesture_test.py – PASS, 12 blocks (window/menus, hierarchy build with
  toolbar gating, «Группа сценариев», canvas nodes → inspector,
  ГС add/remove with site-type validation, KB apply flow Task 3 incl.
  disabled button + double-click, switch visibility pairs, delete-dialog
  default/focus capture, cascade deletion, format-5 save/load via
  MainWindow, doc window modes, PDF matrix + report export).
* run_qa.cmd – PASS; regenerated artifacts reviewed by vision:
  qa_window.png (PASS), qa_matrix.png (PASS), qa_pdf_matrix_page1.png
  (PASS full width), qa_pdf_page1.png (schematic PASS),
  qa_pdf_report.png (PASS), qa_switches.png (PASS).

## Known issues / notes

* Scenario combinatorics can produce hundreds of rows per tree; the
  «Возникновение…» node shows the first 12 grouped lines + «… ещё N
  сценариев (см. матрицу)»; full enumeration lives in the matrix/report.
* The QPdfDocument PNG preview of PDFs shows unpainted areas black
  unless composited on white (QA runner does this; the PDF itself is
  fine in viewers).
* run_app.cmd manual start left to the user's habit (no code path
  changed in the launcher).
* Session-1–4 projects intentionally do not load (clean break, decision
  Q7); the KB backup `knowledge_base_v5.json` stays beside the new KB.
