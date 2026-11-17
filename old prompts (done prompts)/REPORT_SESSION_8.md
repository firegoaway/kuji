# SESSION 8 REPORT – Kuji 4.2.0

Date: 07–08.11.2026 (night). Base: v4.1.0 (sessions 1–7).
Subject: GOST terminology for SIL/PFD, native LaTeX-style math rendering in
the GUI, unsaved-changes guard for the «База знаний» window, automatic
tree compaction (layout engine), pin/edge anchoring fixes, section-header
rename. All six tasks of `8 next-session-prompt.md` implemented.

**Acceptance:** `smoke_test.py` – PASS (27 blocks; new: «math renderer»,
«компактизация», «релевантность списков»), `gesture_test.py` – PASS
(31 scenarios; new: scenario 30 «guard БЗ» + extended scenario 23
«пины» with the scenario-node guard, left-pin drag suppression, pin
anchoring). `run_qa.cmd` artifacts regenerated and visually reviewed
(below). Version → **4.2.0** (`eta/__init__.py`, status bar).

## Task 3 – Unsaved-changes guard, «База знаний» window

* `eta/ui/kb_window.py`: `closeEvent` + testable seam `_ask_close_guard()`
  (three Russian buttons: «Сохранить» / «Не сохранять» / «Отмена»);
  guard fires when `_dirty_count > 0`; «Не сохранять» → `_reload_from_file()`
  (memory + UI revert, `kb_reloaded` emitted); «Отмена» → `e.ignore()`.
  New bottom-bar button **«Закрыть»** (standard, not `primary`) routes
  through the same `self.close()` path. `_rebuild_all()` now also calls
  `equip_tab._show_form()` so the equipment form is rebuilt from the
  reloaded KB (stale local form state cannot survive a discard).
* `eta/ui/main_window.py`: `closeEvent` closes the KB window FIRST;
  `if not self.kb_window.close(): e.ignore()` – cancelling the KB guard
  aborts the application quit.
* Tests: `gesture_test.py` scenario 30 reproduces the user's exact flow
  (open KB → «По оборудованию» → tick the drain pedal → ✕) on a COPY of
  the JSON: «Отмена» keeps the window + edits; «Не сохранять» leaves the
  disk file untouched, reverts memory AND the checkbox after reopen,
  `_dirty_count == 0`; «Сохранить» persists; the app-quit path aborts on
  KB «Отмена». Legacy scenarios that close a dirty KB window now mock the
  guard (scenarios 24/29) – previously they silently discarded, which the
  guard by design no longer allows.

## Task 6 – Section header rename

* New shared constant `theme.PEDALS_CAPTION =
  "ЗАЩИТНЫЕ МЕРЫ И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ"` (measured 297 px at the
  caption font – fits one line even at the 320 px inspector minimum; the
  longer «…МОДИФИКАТОРЫ ИНТЕНСИВНОСТИ ОТКАЗОВ» variant measured 443 px and
  would clip). Used in BOTH places: `kb_window.py` (equipment library
  form) and `inspector_panel.py`. Internal `pedals` keys, `PEDALS` tuple,
  `pm-*` ids untouched.
* User-visible sweep: event-picker filter tooltip «(педальки отображения)»
  → «(переключатели отображения)»; inspector hint «Барьер цепочки…» →
  «Защита цепочки…»; PDF legend «барьер цепочки» → «защита цепочки».
  No user-visible «педальки»/«барьер(ы)» remain (code comments may keep
  them where they refer to the `pedals` key). Tests assert the new caption
  in both forms (scenarios 26/30).

## Task 1 – GOST terminology (SIL/PFD fields)

* Labels (inspector + KB equipment form): «Уровень полноты безопасности
  (SIL):», «Вероятность отказа по запросу (PFD) контура:», «Интенсивность
  опасных необнаруживаемых отказов (λ_DU), ч⁻¹:», «Периодичность проверок
  защит (T_тест), мес:»; «Резервирование:» unchanged (1oo1/1oo2/2oo3).
  Long labels wrap (word-wrap on QFormLayout labels) – nothing elided.
* SIL combo items via new `theme.sil_combo_item()`: «SIL 1: PFD 10⁻²…10⁻¹»
  – REAL Unicode superscripts, no `10^` carets anywhere in the UI (range
  source: табл. 2 ГОСТ Р МЭК 61508-1-2012).
* Pedal caption composed by the UI: «ПАЗ по уровню полноты безопасности
  (SIL, реле/клапаны)» (KB title `pm-sil-paz` untouched).
* Tooltips now cite «ГОСТ Р МЭК 61508» / «ГОСТ Р МЭК 61508-6-2012»
  (PFD_avg formula), rendered through the math backend.

## Task 2 – Native LaTeX-style math rendering

* New module `eta/ui/math_text.py` (dependency-free): mini-notation parser
  (Greek macros `\lambda \Sigma \prod \cdot \approx \le \ge \pm …`,
  sub/sup `_{…}`, `^…`, single-char `_DU`/`^2`, signed exponents `^-2`,
  Cyrillic indices `T_тест`, nested-free; unknown macros render
  literally; existing Unicode style `λ · ≈ ⁻¹` passes through).
  Backends: **A** `math(text)` → `<sub>/<sup>` HTML for QLabel/QToolTip;
  **B** `paint_math(painter, x, y, …)` / `math_size()` / `math_height()` /
  `math_wrap()` – runs at ×0.65 font with ±0.35×em baseline shift.
  `theme.py` re-exports everything as the single entry point.
* Integration: `layout.py::_measure` and the edge-callout sizes measure
  through `math_size` (render-measure unity); `render.py` paints node
  `q_text`, badges and callout line-2 via `paint_math` (canvas AND PDF –
  WYSIWYG preserved); matrix summary (QLabel) and the PDF matrix footnote
  + legend + FTA summary line via the math backends; equipment-form
  labels/tooltips through `math()`. QComboBox uses Unicode superscripts
  (one consistent approach). Storage untouched – pure display layer.
* Tests: smoke block «math renderer» (sub/sup/Greek/Cyrillic/literal
  macros/HTML/measure-vs-paint equality); smoke 5b width assertions now
  measure via `math_size`; `qa_export_a3.pdf` regenerated.

## Task 4 – Automatic compaction of generated trees

Root causes confirmed and fixed in `eta/core/layout.py::compute_layout`:

1. **Column pitch (Step 1):** per-column `gap = callout_w_max(next column's
   incoming edges) + 2·PAD`, `PAD = 10` px, floor 48 px; `MIN_COL_W`
   remains the header minimum; `HGAP = 176` now drives only FTA columns.
   The ~600 px bridges are gone (measured ETA pitches down to 48 px on
   narrow callout columns, e.g. «PFD = 0,100»).
2. **Verticals (Step 2):** bottom-up contour packing (Reingold–Tilford),
   contours keyed by **effective column**, not tree depth
   (`eff_col(child) = max(level_idx(child), eff_col(parent))`) – the
   generator inserts barriers non-monotonically (SIL stage 2 BEFORE
   reserve/ignition stage 1), so same/decreasing-level chain links stack
   diagonally in the parent's column (stagger ≤ centering slack, 20 px per
   link) instead of colliding in one column. Sibling gap `ΔY_min = 30 px`
   (`DY_MIN`); «ДА» branch (unfavorable, green TOP port) is ALWAYS above
   the «НЕТ» branch; parent centered on child input ports
   `Y = (Y_in(c₁)+Y_in(c_k))/2 − H/2`; a single visible child in the NEXT
   column aligns port-to-port → **straight 2-point edge** when
   `|Y_out − Y_in| < 4 px` (`STRAIGHT_SNAP`).
3. **Routing (Step 3):** callouts pinned right of the output port
   (`X = right + 8`, top callout above the top-port line, bottom below the
   bottom-port line); Z-route with the trunk AFTER the callout:
   `X_bend = right + 8 + W_callout + 16` (`BEND_PAD`), clamped to stay
   left of intermediate columns for level-skipping edges, and
   `min(bend, max(callout_right + 2, child_left − 12))` so the trunk never
   lands inside its own/sibling callout; same-column stacks share a
   uniform per-column trunk `max(callout_right)+16` (right of ALL callouts
   anchored in that column).
4. **Collision audit (safety pass):** node∩node, node∩callout,
   callout∩callout, segment∩foreign node/callout (own edge's boxes
   excluded); deterministic push-apart shifts the lower movable ETA node
   down (manual nodes are audited but never moved); ≤ `AUDIT_PASSES = 8`
   iterations; residuals reported in `Layout.collisions` (empty on all
   generated trees tested). `row_cuts` recomputed as mid-gaps between
   same-column boxes (PDF row slicing) + manual-node borders.
* Verification tree (pump ЛВЖ/big + drain+leak+SIL+reserve pedals):
  pre-fix span ≈ 2000+ px with 4 surviving collisions → post-fix ≈ 450 px,
  `collisions == []`. Manual-drag-onto-another-node + relayout resolves
  to zero node overlaps. FTA side unchanged (phases centered on the root,
  center anchors, HGAP pitch).

## Task 5 – Pin semantics and edge anchoring

1. **Edges on pins:** pin geometry moved to `theme.py`
   (`PIN_Y_TOP = 0.32 / PIN_Y_BOT = 0.68`, `PIN_R/PIN_HIT_R`,
   `pin_centers()`); canvas imports it (`_pin_centers` alias kept for
   tests); every ETA edge starts exactly at the parent's output pin
   (unfavorable «ДА» branch → TOP GREEN `right-yes`; favorable «НЕТ»
   branch → BOTTOM RED `right-no` – reconciled with the callout labels
   «P(ДА)/PFD» vs «НЕТ·P») and ends at the child's left pin by row
   (first/upper child → `left-yes`, second → `left-no`); arrowheads point
   into the child. FTA edges keep center anchors (no pins by design).
2. **Right-pin menu:** a node whose split is `SPLIT_SCENARIO` (already
   ends with «Сценарий N») no longer offers intermediate events –
   explanatory tooltip «Узел уже завершается сценарием – добавление
   промежуточных событий недоступно» (insertion above the terminal stays
   available by clicking the TERMINAL's right pin). Picker ordering now
   by relevance (`TreeCanvas._ordered_barriers`): tag-overlap with the
   branch first (incl. dust*/sug* families), «alien-medium» events last,
   then stage proximity, then title – `b-dust-blast` is first only on
   dust paths (verified: dust leaf → first; ЛВЖ ignited leaf → burn-pressure
   first). **Filter-verification finding:** the degenerate lists were
   mostly caused by a REAL bug – `_retag_subtree` overwrote each node's
   own incoming-branch tags, so `required_parent_tags` (e.g. `dust-cloud`)
   never accumulated and the dust chain was unreachable from pins; fixed
   (node keeps its tags; children recomputed from them). The remaining
   single-candidate cases (only `b-paz` early in a chain) are legitimate
   stage-monotonicity and stay strict (normative chronology).
3. **Left-pin drag suppressed:** `_pin_link_allowed()` is now
   `key == "right-yes"`; a drag attempt from any left pin is cancelled
   with the tooltip «Левые пины – наращивание дерева отказов (FTA)
   кликом; связь тянется только от правого зелёного пина»; short click on
   left pins still opens the causes picker. Hover tooltips explain the
   difference per pin. `_apply_cause_from_picker`/`add_fta_cause` audited:
   FTA nodes can no longer be attached to the ETA side through the link
   path (guard on source pin + existing model-side checks).
4. Tests: smoke 13b/13c (pin endpoints for every edge, branch order,
   straight single-child edges, gap ≤ callout+2·PAD, audit clean, manual
   drag resolution, relevance); gesture scenario 23 extended (scenario
   guard, terminal-pin insertion, left-drag model-unchanged, two-branch
   pin anchoring), `_assert_icons` untouched and passing.

## Files touched

`eta/__init__.py` (4.2.0) · `eta/ui/math_text.py` (NEW) · `eta/ui/theme.py`
(pin geometry, PEDALS_CAPTION, sil_combo_item, math re-exports) ·
`eta/core/layout.py` (compaction rewrite) · `eta/core/model.py`
(`_retag_subtree` fix) · `eta/ui/render.py` (math painting) ·
`eta/ui/canvas.py` (pins/picker/drag) · `eta/ui/kb_window.py` (guard,
labels, caption) · `eta/ui/inspector_panel.py` (labels, caption, hints) ·
`eta/ui/event_picker.py` (tooltip) · `eta/ui/matrix_view.py` (math
summary) · `eta/export/pdf_export.py` (math legend/footnote, «защита
цепочки») · `eta/ui/main_window.py` (quit routing) · `smoke_test.py` ·
`gesture_test.py` · `README.md`.

## Test results / QA

* `smoke_test.py` – PASS, 27 blocks (was 24 + math/compaction/relevance).
* `gesture_test.py` – PASS, 31 scenarios (was 29 + guard scenario, pin
  extensions, GOST-label assertions; updated drag/edge-click assertions to
  pin-based anchors). The label assertions caught and fixed a real sign
  bug in `theme.sil_combo_item` (was rendering «10²…10¹» instead of
  «10⁻²…10⁻¹»).
* `run_qa.cmd` – artifacts regenerated (`qa_window.png` now shows the KB
  window on «Библиотека типовых сценариев → По оборудованию» with the
  selected «Компрессор центробежный (ГГ)» entry; the session-7 «Без
  частоты» tab moved to a separate `qa_kb_pending.png`), plus
  `qa_canvas.png`, `qa_matrix.png`, `qa_docview.png`, `qa_sheet.png`,
  `qa_export_a3.pdf`, `qa_stats.json` (`pdf_rendered: true`).
  Visual review (glm-5.3-flash, one pass before the model's 5-hour quota
  ran out): canvas – no overlapping node boxes, no edge-through-node/label
  crossings, connectors in empty space; main window – v4.2.0 in the status
  bar; KB bottom bar – «Перечитать из файла» / «Закрыть» / «Сохранить».
  The remaining Task-1 acceptance (exact GOST label texts, λ_DU/T_тест
  real subscripts, SIL superscript ranges without carets, «ЗАЩИТНЫЕ МЕРЫ
  И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ» caption in BOTH forms, ПАЗ pedal wording)
  is proven programmatically by the new gesture assertions (scenarios 26
  and 30), which read the live widgets of both real forms.
* Known §1 font-metrics assertion: PASSED in this environment throughout
  the session (the offscreen font substitution issue did not reproduce);
  the assertion now measures through `math_size` – same renderer that
  draws, so it stays meaningful either way. One transient zoom-smoothness
  flake (scenario 1, timing-sensitive, untouched code) occurred once
  under load and passed on every subsequent run.

## Known issues / notes

* The `_retag_subtree` fix means previously generated models may now
  offer MORE intermediate events than before (tags accumulate) – the
  intended Smart-Linking behavior per the KB design.
* Same-column barrier stacks (e.g. SIL inserted at stage 2 before a
  stage-1 barrier) render as a diagonal cascade inside the parent's
  column; their connectors share a uniform trunk right of all callouts.
* PDF row slicing uses mid-gap cuts between same-column boxes; with
  contour packing these are denser than the old uniform grid.
* The physical-split favorable leaf remains a hidden safe share
  (session-6 semantics); two-branch pin anchoring is covered by the
  generator-tree smoke block.

## Addendum (post-session, user requests): ПАЗ, вентиляция, мониторинг, износ tooltips

The user supplied screenshots of four pedal tooltips (composed from
`pm-sil` / `pm-venting` / `pm-vibro` / `pm-wear` title–formula–source)
and replacement texts. Implemented for all four, same mechanism:

* `knowledge_base.json`: the four records each gained a dedicated
  `"tooltip"` field with the full explanation –
  **ПАЗ**: «Учет надежности систем ПАЗ…» (barriers, PFD in low-demand
  mode, `F_вых = F_вх · PFD_рез`, voting «1 из 2»/«2 из 3»,
  conservatism, SIL 1 example PFD = 0,1 per ГОСТ Р МЭК 61508-1-2012
  табл. 2); **вентиляция**: «Учет работы вытяжной (аварийной)
  вентиляции…» (barrier role, no normative P_вок(A) → engineering
  estimate, `P_ост = 1 / (A · T + 1)`, the ГОСТ Р 12.3.047-98 (А.2.5,
  ф. А.13) «делитель массы» K = A · T + 1, conservative P_ост = 1/K);
  **мониторинг**: «Учет систем непрерывного контроля параметров
  (температуры и вибрации) оборудования…» (`λ_итог = λ_баз · k`,
  k = 0,7, early detection of degradation failures,
  ГОСТ 12.1.004-91 п. 7.9); **износ**: «Учет физического износа
  оборудования при превышении назначенного срока службы…»
  (`λ_итог = λ_баз · k`, k = 2…5, «кривая ванны» per ГОСТ 27.002-2015,
  OREDA/SINTEF beyond useful life). Only short en-dashes «–».
* `math_text.py::math_html_lines()` (re-exported via `theme`): renders
  such multi-line hints as rich text with REAL sub/superscripts and
  soft-wraps each logical line at ~88 chars, so the hint window grows
  downward at a bounded width instead of stretching one line across the
  screen.
* `inspector_panel.pedal_tip()` and the `kb_window` pedal tooltip prefer
  `mod["tooltip"]` (fallback: title–formula–source as before); the
  checkboxes set `toolTipDuration(60_000)` for the long hints.
* Tests: gesture scenarios 26/30 assert all four headings and key
  phrases (formulas with real `<sub>` indices, «делителя массы»,
  «равным 0,7»/«ГОСТ 12.1.004-91 (п. 7.9)», «от 2 до 5»/«k = 2»/
  «кривой ванны»/OREDA/SINTEF/ГОСТ 27.002-2015), no em-dash, and the
  60 s duration on BOTH forms; tooltip assertions compare against the
  `<br>`-flattened text (soft-wrap may split phrases across lines).
  Both suites green. Rendered proofs: `qa_artifacts/qa_paz_tooltip.png`
  (528×406), `qa_vent_tooltip.png` (572×374), `qa_vibro_tooltip.png`
  (566×422), `qa_wear_tooltip.png` (557×470) – complete texts,
  vision-verified sub/superscripts and dashes.
