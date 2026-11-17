# SESSION 17 REPORT – Kuji 6.6.0

Date: 13.11.2026. Base: v6.5.2 (sessions 1–16/1).
Subject: calculation-fix + UX/typography session, seven tasks: the
П1.1 site-value multiplier, matrix column renames, inspector header
cleanup, layout-independent shortcuts + undo/redo + hierarchy
clipboard, bigger tree with smart fit, rubber-band selection with
group operations, full PDF report rework. All LOCKED Q&A decisions
implemented as specified; none re-opened; no clarifying questions
were needed (the prompt locked every ambiguity). Version → **6.6.0**;
KB `meta.version` stays **«6.1»** (no KB edits); serialization and
format 5 untouched (undo snapshots and the clipboard live IN MEMORY).

**Acceptance:** `smoke_test.py` – PASS (23 blocks: NEW block 22
«П1.1/direct × F|L|V + колонки», NEW block 23 «latin_key + undo
semantics + clipboard»; block 16 width bounds now derive from the
theme constants). `gesture_test.py` – PASS (52 blocks: NEW 49
«Tasks 1+2+3 live», NEW 50 «shortcuts RU + undo/redo + clipboard»,
NEW 51 «big tree + fit cap + rubber band + group ops», NEW 52
«hybrid PDF»; updated block 1 «v6.6», block 21 +real Cyrillic Alt+Ф,
block 22 «Площадь:», block 36 «numbered sources / Q_В», block 20
status «Q_В»). `run_qa.cmd` regenerated (app 6.6.0, report_pages 5,
+ NEW `qa_matrix2.png` artifact – matrix scrolled right, formula
column visible); vision review passed for all affected artifacts
(details per task). Implemented in the suggested order 1 → 7,
tests+QA green after every task.

## Task 1 – Matrix column renames

* `eta/core/matrix.py` `MatrixData.header()`: «Сценарий (ГС – расход –
  тип горения – ИЗ)» → **«Сценарий пожара»**; «Участок/установка» →
  **«Участок (установка)»**. Single source confirmed by grep – the
  in-app table (`_refresh_matrix`), the PDF matrix page and all
  tests consume it. Smoke block 22 asserts the new header strings;
  gesture block 49 asserts the table headers through the live
  window. In-app widths unchanged (`resizeColumnsToContents`); the
  PDF widths were reworked in Task 7.

## Task 2 – П1.1/direct site-value multiplier (engine, LOCKED)

* Root placement: `TreeModel._q_gs` in `eta/core/model.py` had a
  raw fallback branch `q = g["q"]` for kinds p11/direct. The branch
  now multiplies λ by the owner's own type value:
  `CalcContext.p11_site_value()` (NEW) resolves via the same
  type-driven resolver used for ТГМ/П1.2 – `tgm_level_value(site_props)`
  → F (area_m2) / L (length_m) / V (volume_m3) by `site_type`; not
  set → None → multiplier 1, the piece stays bare `(4·10⁻⁵)`.
* Formula piece: `({fmt_num(q)}·{fmt_num(site_v)})` – engineering
  notation, comma mantissa, exactly the LOCKED example
  `(4·10⁻⁵·86)`; flow-scoped/rupt variants and dependent-chain
  members (И-гейт) go through the same branch, e.g. the chain piece
  `(4·10⁻⁵·86·1·10⁻⁵·86)`. The `1·1` presence prefix untouched.
* No double multiplication (explicit smoke assertions): p12 stays
  byte-exact `1·1·(2,8·10⁻⁶·50)·(1−exp(−2,2·10⁻⁶))·0,005`; p13 stays
  `(9·10⁻⁵·2960,77)`.
* Reactivity: editing the value or switching the type combo in the
  inspector emits `object_props_changed` → full `_refresh` – the
  matrix formula cell, the fire-node ΣQ and the status bar update
  without re-selecting. Gesture block 49 drives the real combo
  (area 86 → linear 50 → typed 120 → apparatus 10) and asserts the
  live formula cell each step, plus the inherited case: with no own
  value the area inherits the building's 1200 m² through
  `effective_properties` → `(4·10⁻⁵·1200)` (same semantics as П1.2,
  demonstrated live; the «nowhere set → multiplier 1» case is a pure
  smoke block).
* QA: qa_matrix2 (NEW artifact) + qa_canvas verified; formulas
  contain the multiplier pieces (TGM rows `(9·10⁻⁵·2400)` visible in
  the scrolled matrix screenshot).

## Task 3 – Inspector header cleanup (LOCKED)

* `inspector_panel.py`: label «Площадь территории:» → **«Площадь:»**
  (tooltip keeps explaining it is the territory area); section
  headers «ТЕРРИТОРИЯ»/«ПОЖАРНЫЙ ОТСЕК»/«ПОМЕЩЕНИЕ» →
  **«ПАРАМЕТРЫ ТЕРРИТОРИИ»/«ПАРАМЕТРЫ ПОЖАРНОГО ОТСЕКА»/«ПАРАМЕТРЫ
  ПОМЕЩЕНИЯ»** (uniform pattern; building has no kind-named section;
  «ТИП»/«ЗНАЧЕНИЕ» of участок/установка untouched); `show_object` no
  longer sets the ALL-CAPS kind caption – the form starts directly
  with the bold object name for ALL kinds; «НОДА ДЕРЕВА» (tree-node
  form) STAYS.
* Tests updated (gesture 22 «Площадь:», new asserts in block 49 for
  all three sections, empty caption and «НОДА ДЕРЕВА»); QA vision
  qa_inspector_territory: PASS («Территория 1» bold name first, no
  ALL-CAPS caption, «ПАРАМЕТРЫ ТЕРРИТОРИИ», «Площадь:»).

## Task 4 – Layout-independent shortcuts + undo/redo + clipboard (LOCKED)

* **Universal Cyrillic→Latin filter** (NEW module
  `eta/ui/latin_keys.py`): pure function `latin_key(code)` with the
  full 26-letter ЙЦУКЕН table (upper 0x0410–0x042F and lower
  0x0430–0x044F – NOTE: Cyrillic case is a numeric +0x20, NOT a bit
  mask; `code & ~0x20` breaks for У/Ц/Ш/Щ/Ф/Ы/Р/Я/Ч/С/Т/Ь whose bit
  0x20 is already set – first smoke run caught it, fixed to
  `code - 0x20` for the lowercase range). `LatinKeyFilter`
  (application-level, installed once in `MainWindow.__init__`,
  strong module-level ref) re-delivers Ctrl/Alt + Cyrillic letter as
  the Latin positional key event and consumes the original; the
  synthetic event has a Latin code so no re-processing loop is
  possible. Every letter shortcut – current and future – fires in
  both layouts; the existing explicit twins stay (harmless).
* **Undo/redo (Ctrl+Z / Ctrl+Y, depth 50)**: snapshot-based on the
  format-5 dict path in memory (`objects.to_dict()` + trees) as a
  JSON string. Central seam `MainWindow._undo_push()`: the
  PRE-state is kept in `_undo_base` (the last settled state), so the
  moment of the call (before OR after the write) does not matter –
  post-write inspector seams are covered by design. Coalescing: a
  push is skipped when the state equals the base (streams of
  valueChanged) or when the base is already the stack top; a real
  new action clears the redo stack. Push points wired to every
  mutation seam: `tree_changed`/`subtree_removed`/`object_props_
  changed`/`object_title_changed`/`inspector.tree_changed` signals,
  tree add/delete, cause add/remove, template apply, node-offset
  commit, annotation drag, paste. Restore = load dicts back +
  `_refresh` + selection marker restored where alive
  (`tree_id`s/oids survive the round-trip) + `_sync_inspector_alive`
  (a dead form falls back to the live selection). `_new_project`/
  `_load_project_data` reset the history.
* **Actions**: one shared set of four QActions (parent = the
  QApplication, ApplicationShortcut) created once by
  `_ensure_edit_actions()` and added to each window's «Правка» menu;
  the triggered handlers dispatch to `_edit_target()` – the newest
  visible MainWindow (the app has one; the shared set avoids the
  QShortcutMap AMBIGUITY that per-window ApplicationShortcut actions
  create when test runs hold several windows – measured: Qt fired
  the first-created window's action). QLineEdit/QSpinBox keep their
  own Ctrl+Z/C/V through Qt's ShortcutOverride when they can
  undo/copy.
* **Hierarchy clipboard (Ctrl+C / Ctrl+V)**: `_copy_selection` takes
  the really selected object rows (multi-select dedupes ancestors as
  in delete), serializes each subtree with ALL descendant trees
  (causes, dependencies, pedals), root title += « (копия)»,
  `node_offsets` dropped; `_remap_clip_ids` deep-copies with FRESH
  oid/tree_id/cid on every copy AND on every paste (repeated pastes
  never collide; parent links preserved via the cid map).
  `_paste_clipboard` validates the root kind with `can_add` under
  the current selection (denied → the standard information box text
  from the refactored `objects.add_denied_message`), paste-at-root
  with nothing selected for territories; pasted roots become
  selected, the last one current; one undo point per paste (undo
  removes the objects AND their trees).
* **Bug found & fixed along the way**: `HierarchyPanel.select_object`
  used `setCurrentItem` without clearing – in ExtendedSelection the
  PROGRAMMATIC selection ACCUMULATED (copy/delete saw stale
  multi-selections). Now `clearSelection()` first, signals blocked.
* Tests: smoke block 23 (latin_key full table + undo coalescing/
  depth 50/redo-clear/undo-of-paste + clipboard fresh ids, «(копия)»,
  offsets dropped, Q recomputed); gesture block 50 – REAL key
  events: Cyrillic Ctrl+В opens the Document window (and Latin
  Ctrl+D still does), Cyrillic Alt+Ф triggers «Показать всё»
  (added to block 21's loop), Ctrl+Я/Ctrl+Н undo/redo, 3 edits → 3
  undos, Ctrl+C → Ctrl+М paste into another room (fresh ids, tree
  carried, Q>0), repeated paste, Ctrl+Z removes the paste, denial
  path shows the info box (seam-suppressed). Harness lesson
  (documented in the tests): the Qt shortcut dispatcher matches
  events of the ACTIVE window – offscreen runs must
  `QApplication.setActiveWindow(w)` before key presses (a real user
  always types into the active window).
* QA vision qa_window: menu bar «Файл, Правка, Вид, База знаний»,
  status bar «Q_В: …» + «v6.6.0» – PASS.

## Task 5 – Bigger event tree on the canvas (LOCKED «both»)

* Chosen parameters (theme.py / layout.py; canvas and PDF share
  them, WYSIWYG preserved – metrics-driven protocol untouched, no
  width caps reintroduced): F_TITLE 12→**14**, F_META 10→**11**,
  F_FORMULA 12→**14** (the ΣQ line exists only on the fire node –
  it IS the «larger/bolder ΣQ» of the accent), PAD_V 12→**16 px**,
  NODE_INSET 10→**13 px** (2× inset 26 px), min node height
  44→**56 px**, COL_GAP 56→**64**, ROW_GAP 28→**36**, TREE_GAP
  72→**88**, connector pen 1.6→**2.0 px** (canvas `_EdgeItem` +
  `render.draw_edge` together), curve fraction 0.5→**0.55** (softer).
* Accent result node: fire class fill #FFF5F5→**#FFEFEF** (deeper
  tint), border **2.6 px** vs 1.4 (render.draw_node), left accent
  strip 3→**4 px** for the fire kind. The session-14 STATE colors
  (blue «задано» #2563EB, purple «ок» #7C3AED) are untouched – the
  accent works through thickness/typography exactly as LOCKED.
* Smart fit (`TreeCanvas.fit_tree`): padding 24→**FIT_PAD_PX 48**
  (inside the 40–60 range), after `fitInView` the zoom is clamped to
  **FIT_MAX_ZOOM 1.5** and re-centered on the scene center; the
  sticky-mode clamp uses the same 48 px field. «Показать всё»
  (Alt+A) goes through the same `fit_tree`; Ctrl+0 in the doc window
  unchanged.
* QA evidence: qa_sheet (2× sheet render) – nodes large and
  readable, ΣQ lines fully inside their boxes, fire nodes visibly
  thick-bordered and tinted, thick soft connectors; programmatic
  gesture 51 part 1 asserts the constants, the ≥56 px node height,
  and the fit behavior: for a single-tree project the fit scale is
  `min(…, 1.5)` (cap engaged when wanted > 1.5, exact match
  otherwise) and > 0.9; `node_text_fits` smoke block still passes.

## Task 6 – Rubber band + group operations (LOCKED вариант 1)

* Canvas mouse model rework (`canvas.py`): ЛКМ on empty + drag =
  **rubber band** (QRubberBand styled `rgba(59,130,246,0.12)` fill +
  1 px `#3B82F6` border); a plain click without movement still
  clears the selection (`empty_clicked` path unchanged). **Pan moves
  to СКМ (kept) + Пробел+ЛКМ** – Space held → OpenHand cursor,
  ЛКМ-drag pans (ClosedHand), Space release restores; the Space hint
  is in the canvas tooltip + status tip (Russian, short).
* Selection model: `TreeCanvasController` gains `selected_nodes()`
  (real selection SET) and `set_selection()`; a node click selects
  it alone; **Ctrl/Shift+click toggles** a node in/out (inspector =
  last clicked node); every selected node shows the existing dashed
  accent outline. The marquee emits the NEW `nodes_selected(list)`
  signal → MainWindow counts it as a USER selection
  (`_canvas_sel_by_click = True`); programmatic dashed selection
  from a cause-row click still does NOT count (session-16 semantics
  preserved). Annotations are not marquee-selectable.
* Group drag: pressing an already selected node (multi-selection)
  drags ALL selected nodes with one delta (per-node `_move_node_item`
  → edges follow); the reworked `_commit_node_drag(items, delta)`
  writes every slot's `node_offsets`, ONE rebuild + ONE
  `tree_offsets_changed` (one undo point); an unselected node keeps
  the single-node behavior.
* Group Delete: `_delete_selection` collects the owner trees of ALL
  selected nodes (multi, possibly cross-tree), ONE confirmation via
  the NEW seam `_confirm_trees_delete(trees)` (appearance of
  `_confirm_tree_delete`, list of tree titles, «Удалить» default);
  `_update_trash` enables for any user-made canvas selection.
* Tests: gesture block 51 part 2 – REAL mouse: marquee below-up
  sweep selects exactly gs+iz; Ctrl+click toggles ±1; group drag
  moves both nodes (offsets `{"gs","iz"}` = same delta, one undo
  point); marquee over two trees + Delete → ONE seam window, both
  trees removed; Space+ЛКМ pans (scrollbars change; zoomed in first
  – after fit the small tree leaves no scrollbar range), ЛКМ-drag
  no longer pans (scrollbars unchanged). Harness notes: marquee
  must START on empty space (node half-widths are ~100 px; the
  annotation plate occupies the space above a tree) and Space needs
  keyPress/keyRelease (keyClick = press+release resets the flag).
* QA: qa_canvas regenerated; three trees readable; vision notes the
  tiny text at fit-zoom for MULTI-tree projects is the expected
  content-fitting (a single tree gets the 1.5× boost).

## Task 7 – PDF report rework (LOCKED hybrid engine)

* Root cause of the «В ОЗНИК НОВ ЕНИЯ» overlap (verified in code
  before the session): the old `export_report` drew each block with
  `TextWordWrap` into a ONE-LINE-height rect (`row_h = 4.4 mm`) –
  wrapped lines physically OVERLAPPED the neighbors; long lines
  clipped at the right edge. Fix: the four text sections are now
  VERSTATED by **QTextDocument + HTML** (`build_report_document`) –
  line breaking/leading belongs to the text engine, so overlaps are
  impossible by construction.
* Engine mechanics (measured traps, both fixed):
  1. `writer.setPageLayout()` AFTER painted pages rewrites the
     MediaBox of the WHOLE document (an attempted A4-portrait report
     block turned all pages A4) → the file keeps ONE layout: the
     spec's A3/A2 LANDSCAPE for every page (the fallback the
     customer's decision explicitly allows; the text column is
     paginated within the usable area).
  2. A SECOND painter session (`QTextDocument.print_(writer)`) after
     the first painter ended REWROTE the file (matrix pages lost) →
     the whole document is painted by ONE QPainter; the QTextDocument
     pages are sliced via `doc.drawContents` per page (pageSize =
     usable pt, transform reset to device units + scale 254/72).
  3. Metrics-unit trap: `QFontMetricsF` of a font inside the ×10
     mm-painter returns LOGICAL pixels = millimeters; the first
     matrix draft compared against mm×10 (wrap budget 10× too wide)
     and divided the line height by 10 – vision QA caught text
     overflowing into neighbor columns; fixed (compare against mm
     directly, `line_h = fm.height() + 0.9`).
* Report content (LOCKED): title «ОТЧЁТ О РАСЧЁТЕ ЧАСТОТЫ
  ВОЗНИКНОВЕНИЯ ПОЖАРА» + subtitle «Объект расчёта: <владелец> – <тип
  сценария>» + compact project/date line; section 1 shows ONLY the
  type-relevant site parameter (`S = 1200 м²` / L / V – never all
  three), functional purpose (П1.3/П1.4), молниезащита, presence
  probabilities, Kσ, «Огненный шар»; section 2 – TABLE «Событие |
  Величина | Источник» with the flow-scope suffix on ГС rows (the
  «triple identical lines» defect gone), values with dimensions,
  sources in brackets; section 3 – per-tree substituted formula
  lines `Q_j = … = … год⁻¹` (mono font, «·»/superscripts never
  collide) then **«Q_В = Σ Q_i · Kσ = … год⁻¹»** and the total
  across trees; section 4 – ONE numbered deduped source list
  (merged `_tree_sources` across trees + the final ГОСТ/Приказ
  entries). «Исполнитель/Дата» REMOVED. **Q_В everywhere**: report,
  matrix totals, and the app status bar (`main_window._update_status`
  «Q_В: …», dialogs tooltip).
* Matrix PDF (QPainter fixes, LOCKED): shaded header band #E2E8F0
  with bold #0F172A text, visible cell grid, column weights
  [6,18,15,32,12,17] recomputed for the new short headers,
  word-wrapped scenario/formula columns with measured row heights,
  Q right-aligned single-line, page breaks ONLY between rows
  (accumulated-height pagination), totals «Q_В = …». Schematic pages
  keep the doc_scene render and inherit the bigger Task-5 layout
  (A3 fit verified in qa_pdf_page1).
* Tests: gesture block 52 via QPdfDocument.getAllText (page count ≥
  2, Q_В present, Q_возникновение/«Исполнитель» absent, the exact
  title, lines starting «1. »/«2. », «Сценарий пожара» header on
  the matrix page, exactly one «S = …» line and no L=/V=, ≥2
  mass-flow suffixes, Q₁=/exp( formula lines, table headers
  Событие/Величина/Источник); block 36 updated (numbered sources,
  no «Источники:» glue line). QA vision on qa_pdf_report (no
  overlaps, shaded/bordered table, no Исполнитель) and
  qa_pdf_matrix_page1 (after the metrics fix: no overflow, row №24
  fully inside, shaded bold header, visible grid) – PASS.

## Before → after (changed user-facing strings)

* Matrix headers: «Сценарий (ГС – расход – тип горения – ИЗ)» →
  «Сценарий пожара»; «Участок/установка» → «Участок (установка)».
* Inspector: «Площадь территории:» → «Площадь:»; sections
  «ТЕРРИТОРИЯ»/«ПОЖАРНЫЙ ОТСЕК»/«ПОМЕЩЕНИЕ» → «ПАРАМЕТРЫ
  ТЕРРИТОРИИ»/«ПАРАМЕТРЫ ПОЖАРНОГО ОТСЕКА»/«ПАРАМЕТРЫ ПОМЕЩЕНИЯ»;
  the ALL-CAPS object-kind caption above the bold name is GONE for
  every object kind («НОДА ДЕРЕВА» stays).
* Status bar: «Q_возникновение: …» → «Q_В: …».
* Formulas: П1.1/direct bracket «(4·10⁻⁵)» → «(4·10⁻⁵·86)» (F/L/V
  by the site's own type; unset stays bare).
* PDF report: title «ОТЧЕТ О РАСЧЕТЕ…» → «ОТЧЁТ О РАСЧЁТЕ ЧАСТОТЫ
  ВОЗНИКНОВЕНИЯ ПОЖАРА» + «Объект расчёта: …»; raw dump «Участок:
  тип …; площадь …; длина …; объем …» → «Место: Участок – S =
  1200 м²» (only the relevant letter); «ГС: … = … [источник]» lines
  → table rows; «Q_возникновение (…) = Σ Q_сценариев × Kσ = …» →
  «Q_В = Σ Q_i · Kσ = … год⁻¹»; «Источники: …; …» per sheet → one
  numbered «1. … 2. …» list at the end; «Исполнитель: ___ Дата:
  ___» → removed.
* NEW menu «Правка»: «Отменить Ctrl+Z», «Вернуть Ctrl+Y»,
  «Копировать Ctrl+C», «Вставить Ctrl+V» (+ status tips).
* Canvas: NEW tooltips/status tip «Рамка выделения: ЛКМ по пустому
  месту и протянуть; Ctrl/Shift + ЛКМ – добавить/убрать ноду из
  выделения; панорама: Пробел + ЛКМ или СКМ; масштаб – колесо».
* NEW confirmation window «Удаление деревьев» (group Delete, list
  of tree titles).
* Clipboard copy status: «Скопировано объектов: N – Ctrl+V, чтобы
  вставить»; paste denial keeps the standard «…нельзя добавить в
  выбранный элемент – выделите …» box.

## Files touched (session 17)

eta/core/matrix.py (header renames) · eta/core/model.py (docstring +
`p11_site_value` + the p11/direct multiplier branch in `_q_gs`) ·
eta/core/objects.py (`add_denied_message` factored out of
`add_child`) · eta/ui/latin_keys.py (NEW: ЙЦУКЕН table, `latin_key`,
`LatinKeyFilter`, idempotent install) · eta/ui/theme.py (fonts/
paddings constants grown, comments) · eta/core/layout.py (gaps,
min-height 56, CURVE_FRAC 0.55) · eta/ui/render.py (fire accent:
border 2.6, fill #FFEFEF, strip 4; edge pen 2.0) · eta/ui/canvas.py
(rubber band + Space+ЛКМ pan + multi-selection + group drag +
FIT_PAD_PX/FIT_MAX_ZOOM + edge pen) · eta/ui/hierarchy_panel.py
(`select_object` clears stale multi-selection) ·
eta/ui/inspector_panel.py (header/label renames, caption removal) ·
eta/ui/main_window.py («Правка» menu + shared edit actions +
`_edit_target`; undo/redo snapshot machinery; clipboard copy/paste;
`_on_canvas_nodes_selected`; group-delete seam
`_confirm_trees_delete`; Q_В status; push points in all mutation
seams) · eta/ui/dialogs.py (Q_В tooltip) · eta/export/pdf_export.py
(full rework: matrix export with measured rows/shaded header/grid/
between-row breaks; `build_report_document` HTML builder;
one-painter `drawContents` report painting; unified layout) ·
eta/__init__.py (6.6.0) · smoke_test.py (blocks 16 constants, NEW
22/23) · gesture_test.py (blocks 1/20/21/22/36 updated; NEW 49–52) ·
visual_qa_runner.py (qa_matrix2 artifact) · README.md · qa_artifacts
(regenerated, +qa_matrix2).

## Test results / Visual QA

* smoke_test.py – PASS: 23 blocks. Block 22: p11 ×F(86)/×L(120)/×V(3)
  values AND pieces, unset → bare bracket + prefix intact, direct ×10,
  p12 byte-exact, p13 byte-exact, new matrix headers. Block 23:
  latin_key 26 letters × both cases, S/1/D/Z/C/V mappings, non-Cyr
  None; undo push/coalesce/depth 50/redo-clear; clipboard subtree +
  trees with fresh ids, «(копия)», offsets dropped, Q>0, repeated
  paste, undo removes paste (objects AND trees).
* gesture_test.py – PASS: 52 blocks ending `GESTURES PASSED`
  (exit 0). Block 49 (real inspector): «ПАРАМЕТРЫ …» sections,
  «Площадь:», empty kind caption, «НОДА ДЕРЕВА» kept, new headers,
  live multiplier through real combo/spin (×1200 inherited → ×86 →
  ×50 → ×120 → ×10). Block 50 (real keys): Cyrillic Ctrl+В/Alt+Ф/
  Ctrl+Я/Ctrl+Н/Ctrl+М, Latin paths, 3 edits → 3 undos, copy/paste/
  re-paste/undo-of-paste, denial info box. Block 51 (real mouse):
  constants + fit cap (≤1.5, exact when uncapped, >0.9), marquee
  exact-set selection, Ctrl toggle, group drag (both offsets, one
  undo point), group delete ONE window both trees, Space+ЛКМ pans,
  ЛКМ-drag doesn't. Block 52: hybrid PDF text set (Q_В, title,
  numbered sources, single S=, flow suffixes, table headers,
  Q₁=/exp(), absent old strings).
* run_qa.cmd regenerated: app 6.6.0, 3 trees, matrix_rows 6,
  report_pages 5, pdf_rendered true; NEW qa_matrix2.png. Vision
  review (glm-5.3-flash): qa_window (menu bar + Q_В + v6.6.0),
  qa_inspector_territory (renamed header/label, no caption), qa_matrix2 (headers + formula pieces),
  qa_canvas/qa_sheet (large nodes, accent fire node, thick soft
  edges, ΣQ inside boxes), qa_pdf_report (no overlaps, bordered
  shaded table, no Исполнитель), qa_pdf_matrix_page1 (clean after
  the metrics fix). One pre-existing demo artifact noted: the TGM
  tree's annotation plate uses the session-13 demo's custom offset
  [-110,−70] and partially sits behind the GS node – stored demo
  data, not a session-17 regression.

## Known issues / notes

* The PDF keeps ONE page layout per file (spec size, landscape) for
  ALL pages – QPdfWriter rewrites the MediaBox of existing pages on
  any later `setPageLayout` (measured); the A4-portrait report idea
  was dropped per the LOCKED fallback clause.
* QTextDocument pages are painted by slicing `drawContents` with the
  single QPainter (a second painter session via `print_` was
  measured to REWRITE the file, losing the matrix pages).
* At fit-zoom a MULTI-tree project still shows small text (content
  fitting, downscale unlimited); a single tree now scales up to
  1.5×.
* Undo history is per-window, in-memory, depth 50; file-level state
  (project path, dirty flag) is not part of the snapshot; undoing to
  the on-disk state does not clear the dirty flag.
* The RU-layout filter covers Ctrl/Alt + Cyrillic letters; the
  existing per-shortcut twins (Ctrl+У, Ctrl+Й, Alt+Ф…) remain
  registered and harmless.
* Offscreen-test lessons documented in the tests: shortcut dispatch
  needs the ACTIVE window (`QApplication.setActiveWindow`);
  marquee/press points must be verified against item geometry; Space
  hold = keyPress+keyRelease; `QFontMetricsF` under the ×10 mm
  painter returns millimeters.
* run_qa.cmd may exit 1 on teardown after writing all artifacts
  (offscreen quit race, cosmetic – as in previous sessions).
