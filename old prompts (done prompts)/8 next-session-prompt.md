# PROMPT: Kuji – Session 8. GOST terminology, LaTeX-style math in GUI, KB unsaved-changes guard, automatic tree compaction, pin/edge anchoring fixes, section-header rename

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` — do NOT rename it) — a constructor of hybrid bow-tie logic trees (FTA + ETA) per Order of the Ministry of Emergency Measures of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–7 are done. Read before starting: `old prompts (done prompts)\6 next-session-prompt.md` (sections 0–5: code map, style rules, pitfalls), `7 next-session-prompt.md` (KB enrichment: `pending_events`, equipment categories), and `REPORT_SESSION_*.md`. Everything described there works and is covered by tests — do not break it without need.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, and the session report — in English.
- **Application UI language: RUSSIAN** — unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menus, messages, badges, statuses) must be in Russian.
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- UI terminology follows СПРАВКИ А/Б of previous sessions: «Ключевое / инициирующее событие», «Промежуточные события», «Причины отказов», «Конечный сценарий», «Сценарий N», «База знаний», «логический элемент И/ИЛИ». The words «гейт», «барьер» must NOT appear as UI terms; fire-automation systems (АПС/СОУЭ/СПДЗ/АУПТ) must stay excluded everywhere. Port/pin vocabulary: «пин „ДА/НЕТ“».

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` — Python 3.14.3, PySide6 6.12.0 (QtSvg, QtPdf available) |
| Entry point | `main.py`; launcher `run_app.cmd` |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (sets `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:\Windows\Fonts`); artifacts land in `qa_artifacts\` (`qa_window.png`, `qa_canvas.png`, `qa_matrix.png`, `qa_docview.png`, `qa_sheet.png`, `qa_export_a3.pdf`, `qa_stats.json`) |
| Core tests | `smoke_test.py` (core math/layout invariants), `gesture_test.py` (full UI acceptance, offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` — sections: meta, echelons, fta_gates, initiating_events, barrier_events, cause_events, cause_notes, pending_events, value_library, presets, property_modifiers |
| App version | `eta\__init__.py` → `__version__ = "4.1.0"` — bump to `4.2.0` this session (status bar shows it via `main_window.py`) |
| Session reports | write `old prompts (done prompts)\REPORT_SESSION_8.md` (English) at the end; next-session prompt file `9 next-session-prompt.md` when asked |
| Reference docs | `literature\Методика_533_RAG_final.md`, `literature\2 ГОСТ 12.1.004-91_distil.md`, `literature\БЗ_отказы_оборудования_и_антагонисты.md` |

**Known pre-existing environment failure (do NOT chase it):** `smoke_test.py` line 285 (`assert fm_m.horizontalAdvance(geo.q_text) <= inner + 1e-6`) fails offscreen because the offscreen platform substitutes fonts (stderr: «…or switch to fontconfig»), making measured mono text wider than at runtime. It fails identically with and without any UI change (verified in session 7.5 by A/B test). Re-check it once; if the failure is still ONLY that font-metrics assertion, note it and continue. If your Task 2 changes touch `q_text` measurement, make sure the assertion fails/succeeds for the right reason (measure with the same renderer that draws).

## 2. CODE MAP (what lives where; all tested — extend, don't break)

- `main.py` — entry: `QApplication`, global `app.setStyleSheet(QSS)`, `install_scroll_wide`, `MainWindow(kb)`.
- `eta\core\model.py` — `TreeModel`, `Node`/`FtaNode`, splits `SPLIT_BARRIER = "barrier"`, `SPLIT_PHYSICAL = "physical"`, `SPLIT_SCENARIO = "scenario"`; `add_split(node, tmpl)`, `add_fta_phase`, `add_fta_subgate`, `add_fta_cause`; hidden favorable fractions (`is_hidden_safe`) are NOT measured/placed.
- `eta\core\objects.py` — object hierarchy (Территория→…→Оборудование), `alloc_scenario_title()` («Сценарий N»), equipment `props` defaults: `sil` (0 = none), `sil_pfd` (1e-2), `voting` («1oo1»), `lambda_du_h` (1e-6), `t_test_mo` (12), `pedals`.
- `eta\core\generator.py` — `generate_equipment_chain(model, kb, eq, objects)` builds ETA+FTA from KB: λ-modifiers `λ_итог = λ_баз·∏k_i`; `SIL_DEFAULT_PFD = {1:1e-2, 2:1e-3, 3:1e-4, 4:1e-5}`; `pfd_avg(λ_DU, T_тест) = λ_DU·T/2`; final barrier PFD = `max(PFD_SIL_голосование, PFD_avg)`; «Сработка ПАЗ (SIL)» chain node at level 2.
- `eta\core\layout.py` — `compute_layout(model, kb) -> Layout` (columns per echelon level −5…5, tidy-tree vertical slots, Manhattan edges; shared by canvas AND PDF — WYSIWYG is sacred). Details in Task 4.
- `eta\core\validation.py` — `Validator.check(tmpl, node)` (chronology: `stage_level` strictly above node level; `incompatible_tags` vs `path_tags`; `required_parent_tags`), `compatible_barriers(node)` = all `kb.barriers` passing `check`; `check_fta(tmpl, gate)` (phase order ГС→ИЗ or ИЗ→ГС, monotonic levels, no repeats).
- `eta\core\matrix.py` — scenario matrix; summary line `F_итог = λ_баз · ∏ P` and invariant `ΣQ конечных + скрытых = λ_баз`.
- `eta\core\kb.py` — `KnowledgeBase` (atomic save/reload of the JSON, signal semantics via window).
- `eta\ui\theme.py` — design system «Swiss Utilitarian»: palette (`ACCENT #2563EB`, `TEXT_PRIMARY #0F172A`, `HAZARD #DC2626`, …), fonts (`ui_font`, `mono_font`, stacks Inter/Segoe UI + JetBrains Mono/Consolas), size constants (`HGAP 176`, `VGAP_ROW 44`, `MIN_COL_W 170`, `MIN/MAX_NODE_W 130/208`, `NODE_INSET 10`, `LABEL_INSET 6`, `PAD_H/V`, `MARGIN 32`, `HEADER_H 48`), `fmt_prob/fmt_q/fmt_q_full`, and the global `QSS` (buttons: default, `#primary` blue, `#primaryOutline` white with blue contour — added in session 7.5 for «Применить на холсте»).
- `eta\ui\icons.py` — `glyph_icon(name, active, size_px, color)` panel glyphs; `apply_to_canvas_icon()` — SVG→QSvgRenderer→QPixmap with devicePixelRatio (HiDPI) for the KB-window apply buttons; `app_icon()`.
- `eta\ui\canvas.py` — work viewport `TreeCanvas` (gestures mixin `eta\ui\gestures.py`), `Node` QGraphicsItem, pins: `_pin_centers(rect)` → keys `left-yes/left-no/right-yes/right-no` at 32 %/68 % of node height (green «ДА» top, red «НЕТ» bottom), `PIN_R 5.5`, `PIN_HIT_R 7.5`; `pin_hit(scene_pos)`; modes `IDLE/RUBBER/MOVING_NODE/PIN_PRESS/PIN_LINK`; `_open_pin_picker` (right pin → `compatible_barriers` picker → `add_split`; left pin → causes picker → `add_fta_cause`); `_pin_link_allowed()` = `"yes" in key` (BUG: allows left-yes too); `_apply_cause_from_picker`; context menus `build_eta_menu/build_fta_menu` (every action has an icon — `gesture_test` asserts it).
- `eta\ui\render.py` — `draw_node/draw_edge/draw_edge_label` shared by canvas and PDF (`RenderState`).
- `eta\ui\event_picker.py` — `EventPickerPopup.pick(items, title, parent, pos, filter_groups=…)`: search line + funnel pedal-filters, ~9 visible rows, single/double click/Enter selects.
- `eta\ui\kb_window.py` — «База знаний» window `KnowledgeBaseWindow`: tabs «Ключевые / инициирующие события», «Причины отказов», «Без частоты (требуют задания)», «Логические элементы», «Библиотека значений», «Библиотека типовых сценариев» (`LibraryTab` with sub-tabs `EquipmentLibraryTab` «По оборудованию» and `PresetsTab` «По сценариям»); edits mutate `kb.data` in memory immediately, `_dirty_count` + status label «Правок с последнего сохранения: N», «Сохранить» = `_save_all` (atomic rewrite + `kb.reload()` + `kb_reloaded` signal → model recalc), «Перечитать из файла» = `_reload_from_file`. **No `closeEvent` — closing via ✕ silently keeps in-memory edits (Task 3).** Equipment form fields (lines ~1280–1315): «Категория расхода», «Уровень SIL», «PFD контура», «Резервирование», «λ_DU, ч⁻¹», «T_тест защит, мес», «Коэффициент износа», pedals section; bottom bar: status label, «Перечитать из файла», «Сохранить».
- `eta\ui\inspector_panel.py` — right panel; equipment props form repeats «Уровень SIL» (line ~311), «PFD контура» (~328), «λ_DU, ч⁻¹» (~362); SIL combo items built as `f"SIL {lvl}: 10^{...}…"` — plain caret text (also in `kb_window.py` ~1288).
- `eta\ui\main_window.py` — toolbar («База знаний…» opens the KB window non-modally), `closeEvent` (UI-state saving), doc window management, status bar with version.
- `eta\export\pdf_export.py` — vector A3 PDF from the SAME scene/layout (WYSIWYG).

## 3. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py`; any visual change must go through both automatically — never fork geometry.
2. KB JSON edits are data edits; UI terminology changes must not rename internal ids/keys (`sil`, `sil_pfd`, `lambda_du_h`, `t_test_mo`, `pedals`, `b-*` ids, …). Backward compatibility of loading old JSON must hold.
3. No new external dependencies; everything is PySide6-native.
4. Style: flat Swiss-utilitarian, `QSS` in `theme.py`; buttons by objectName (`primary`, `primaryOutline`); icons only via `icons.py` glyph/SVG pipeline (HiDPI-aware).
5. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) and keep them green (modulo the known font-metrics assertion, §1); update their assertions to the new expected strings/geometry; add new regression tests as specified per task. Run `run_qa.cmd` and visually review the regenerated `qa_artifacts\*.png` before declaring done.
6. Manual smoke check with `run_app.cmd` is the user's habit — the app must start cleanly from it.
7. Keep all current features working: DnD from KB to canvas, «Применить на холсте» (both sub-tabs), smart linking, scenario «Сценарий N» flows, matrix/PDF export, QSettings restore.

---

## TASK 1. Russian GOST terminology for SIL / PFD equipment fields

**Problem.** In «База знаний» → «Библиотека типовых сценариев» → «По оборудованию» (right properties form, `kb_window.py` ~1285–1315) and in the main-window inspector (`inspector_panel.py` ~289–362), the fields use anglicisms: «Уровень SIL:», «PFD контура:», «λ_DU, ч⁻¹:», «T_тест защит, мес:», pedal checkbox «SIL системы ПАЗ (реле/клапаны)» (title comes from KB `property_modifiers`, id `pm-sil-paz`), plus combo rows `SIL 1: 10^-2…10^-1` built with a caret. The user wants Russian scientific / fire-technical phrasing per the Russian GOST corpus already cited in the KB: **ГОСТ Р МЭК 61508-1-2012** (табл. 2 — SIL ranges) and **ГОСТ Р МЭК 61508-6-2012** (PFD_avg).

**Requirements.**
1. Rename the UI labels (both `kb_window.py` equipment form and `inspector_panel.py`) to GOST-style Russian with the international abbreviation kept in parentheses for recognition:
   - «Уровень SIL:» → «Уровень полноты безопасности (SIL):»
   - «PFD контура:» → «Вероятность отказа по запросу (PFD) контура:» (tooltip may add «средняя вероятность опасного отказа по запросу, PFD_avg, ГОСТ Р МЭК 61508-6»)
   - «λ_DU, ч⁻¹:» → «Интенсивность опасных необнаруживаемых отказов (λ_DU), ч⁻¹:»
   - «T_тест защит, мес:» → «Периодичность проверок защит (T_тест), мес:»
   - «Резервирование:» stays (values `1oo1/1oo2/2oo3` stay as-is).
   Form widths may need adjusting — labels must not be elided; keep the two-column form tidy.
2. SIL combo items must show ranges with REAL superscripts (see Task 2 renderer or Unicode `10⁻²…10⁻¹`), e.g. «SIL 1: PFD 10⁻²…10⁻¹» / «Нет». Do not keep `10^` carets anywhere in the UI.
3. The pedal checkbox label: KB record title «SIL системы ПАЗ (реле/клапаны)» may stay (it is data), but where the UI composes its own caption, prefer «ПАЗ по уровню полноты безопасности (SIL, реле/клапаны)». Do not break `pm-sil-paz` id or `pedals` keys.
4. Sweep the whole UI for other anglicism leaks of this family (tooltips in `inspector_panel.py`, `kb_window.py`, README): «PFD контура по МЭК 61508…» → cite «ГОСТ Р МЭК 61508». UI never uses the bare word «барьер» — where tooltips say «барьер ПАЗ», say «защита ПАЗ» or «барьер безопасности» only in normative citations inside tooltips is acceptable, but prefer the established vocabulary.
5. Update README.md terms section, `smoke_test.py`/`gesture_test.py` assertions that reference the old labels (there are asserts on KB texts; search «SIL», «PFD» in tests).

**Acceptance:** both forms show the GOST labels; no `10^` carets in any UI; tests updated and green; `qa_window.png` regenerated showing the equipment form.

---

## TASK 2. Native LaTeX-style math rendering across the GUI

**Problem.** Math is faked with plain-text conventions: `λ_DU`, `Q_исх = `, `P(ДА) = 0,035`, `F_вых = F_вх·PFD`, `PFD_avg ≈ λ_DU · T_тест / 2`, `F_итог = λ_баз · ∏ P`, `λ_итог = λ_баз · k`, `10^…` carets, `ΣQ`. The user asks: the program must natively render such notation in proper mathematical typography, e.g. «лямбда_DU, ч^-1» becomes λ with subscript DU and a real −1 exponent on the unit — everywhere.

**Requirements.**
1. Create module `eta\ui\math_text.py` — a tiny, dependency-free LaTeX-subset renderer (suggestion; integrate with `theme.py` fonts):
   - Input: a practical mini-notation. Support: Greek letters (`\lambda`, `\sigma`, `\Sigma`, `\prod`, …) and the Unicode Greek already used (`λ`, `Σ`, `∏`); subscripts/superscripts `_{...}`, `^{...}`, single-char `_x`/`^x`; operators `\cdot`, `\times`, `\approx`, `\le`, `\ge`, `\pm`; Cyrillic inside math (indices like `T_тест`, `λ_баз`); mixed text runs.
   - Backend A (widgets): produce Qt rich-text HTML (`<sub>`, `<sup>`, `<i>` for variables optional — keep it restrained, Swiss style) for `QLabel` (incl. form labels via `setLabelText`? — QFormLayout rows use `QLabel`, so labels can be rich), `QToolTip`, `QCheckBox`/button texts where applicable. For `QComboBox` items rich text is not native — either use Unicode superscripts (preferred, e.g. `10⁻²…10⁻¹`) or a `QStyledItemDelegate` painting via Backend B; pick ONE approach and use it consistently for combos.
   - Backend B (QPainter): produce laid-out runs `[(text, dx, dy, font, )...]` for `render.py` (canvas nodes, callouts, matrix header) and PDF export; sub/sup at ~0.65× size, baseline shift ±~0.35×; provide `math_width(runs, base_font)` measured with `QFontMetricsF` so layout math stays exact.
2. Introduce a single source of truth for composed strings: helper `math(text) -> str/HTML` for widgets and `paint_math(painter, x, y, text, font, color)` / `math_size(text, font)` for painting. Refactor the composition points to go through it:
   - `layout.py::_node_texts` — badges `PFD = … · F_вых = F_вх·PFD`, `Q_исх = …`/`Q = …` (`q_text` measured in `_measure` — must use the new `math_size` so smoke width assertions stay meaningful);
   - `layout.py` edge callouts `P(ДА) = …`, `PFD = …`, `НЕТ · P = …` (`draw_edge_label` in `render.py`);
   - `matrix.py` summary line `F_итог = λ_баз · ∏ P` and invariant text;
   - `inspector_panel.py` / `kb_window.py` form labels and tooltips (λ_DU, T_тест, PFD_avg formula in tooltip);
   - SIL combos (Task 1 ranges);
   - generator/doc texts where formulas appear (e.g. «Сработка ПАЗ (SIL)» node badges).
3. Storage stays plain: do NOT rewrite the KB JSON content — rendering is a display-layer concern (`property_modifiers.formula` strings like `λ_итог = λ_баз · k, k = 0,7` are displayed through the renderer as-is; the mini-notation parser must therefore also accept the existing Unicode style with `·`, `≈`, `⁻¹`). No data migration.
4. WYSIWYG: canvas and PDF must render identically (same Backend B runs). Matrix view and doc view included.
5. Keep it tasteful: body text remains regular UI font; only formulas get math typography. Node height/width math must account for the new rendering (update `_measure`), and the Task 4 layout constants interplay must be re-checked after both tasks land.

**Acceptance:** the equipment form label shows λ with subscript DU and unit `ч⁻¹` typographically correct; SIL combos show superscript ranges; canvas node meta `Q_исх = 2,2·10⁻² год⁻¹`, badge `PFD = 1·10⁻² · F_вых = F_вх·PFD` and callout `P(ДА) = 0,035` render with true sub/superscripts on screen and in `qa_export_a3.pdf` (verify page render); matrix summary line correct; `smoke_test.py` width assertions still meaningful (measure via `math_size`); new unit tests for the parser (sub, sup, nested-free, greek, mixed Cyrillic, `·`, fallback for unknown macros — render literally).

---

## TASK 3. Unsaved-changes guard when closing the «База знаний» window

**Problem.** The KB window edits mutate `kb.data` immediately («правки применяются сразу в память»); only «Сохранить» persists atomically. There is no «Закрыть»/«Отмена» button and no `closeEvent` on `KnowledgeBaseWindow` — if the user accidentally toggles a pedal checkbox (e.g. «Аварийный дренаж / слив») and closes via ✕, the in-memory edits silently survive (and any later save persists them). The user demands an explicit guard.

**Requirements.**
1. Add `closeEvent` to `KnowledgeBaseWindow`: if `self._dirty_count > 0`, show `QMessageBox` (icon Question, window title «База знаний», text «Несохранённых правок: N. Сохранить их перед закрытием?») with three buttons:
   - «Сохранить» → `self._save_all()` (existing atomic save + reload + `kb_reloaded`), then accept the close;
   - «Не сохранять» → `self._reload_from_file()` (discard: revert in-memory data from disk, emit `kb_reloaded` so the model/scene recalc back), then accept;
   - «Отмена» → `e.ignore()` (window stays).
   If `_dirty_count == 0`, close silently.
2. Add a bottom «Закрыть» button (standard, not `primary`) next to «Перечитать из файла»/«Сохранить» that calls `self.close()` — the same guarded path.
3. App-quit path: `MainWindow.closeEvent` must route through the KB window guard when it is open with unsaved edits (close KB window first; if the user cancels, abort the app quit too).
4. Verify the discard path REALLY reverts everything the tabs mutate in memory: event editors (`EventsTab`, `PendingTab`), `ValuesTab`, `PresetsTab`, `EquipmentLibraryTab` props/pedals. If some tab caches copies (e.g. local form state), rebuild/refresh them from reloaded `kb` after `_reload_from_file()`. Reproduce the user's exact scenario in a test: open KB → «По оборудованию» → tick a pedal checkbox → ✕ → «Не сохранять» → assert JSON on disk unchanged, checkbox state reverted after reopen, `_dirty_count == 0`.
5. Keep window non-modal behavior, `kb_reloaded` semantics, and the existing «Сохранить» flow unchanged. Tests: extend `gesture_test.py` KB sections with the three-branch dialog scenario (mock/`QTimer` or direct `closeEvent` invocation offscreen); update `visual_qa_runner.py` if the bottom bar layout changes (new button).

**Acceptance:** three-way guard on ✕ and «Закрыть»; discard fully reverts memory + UI; cancel keeps the window; app quit guard works; tests green; `qa_window.png` reviewed.

---

## TASK 4. Automatic compaction of generated event trees (layout engine)

**Problem.** Trees generated from equipment/scenario libraries sometimes lay out very loosely and even self-intersect/overlap. Screenshot 2 (reactor tree): ~450–600 px empty horizontal «bridges» between a parent and its children, uneven vertical spread, canvas used to less than half. Root causes in `eta\core\layout.py::compute_layout`:
- Column pitch is global: `x += w + HGAP` with `HGAP = 176` and per-level `w = max node width + 16`; narrow columns still leave huge gaps (bridge ≈ HGAP + centering slack), and `mid_x` clamps to `0.6·HGAP ≈ 106 px`, so the vertical trunk sits far from the child.
- Vertical slots are a uniform grid: `row_h = max_node_h + VGAP_ROW` for EVERY leaf (tallest node dictates all rows) — wasted space.
- Parent Y = mean of child centers; no contour packing, no branch-order guarantee; with `manual_pos` nodes and wide callouts, trunks can cross other parents' callouts / nodes.

**Requirements — implement the following algorithm (user-approved plan, adapted to Kuji vocabulary: «callout box» = плашка ДА/НЕТ·P on an edge; «port» = пин).**

*Step 1 — X coordinates (tight, uniform, callout-proportional):*
- For each column (echelon), pitch to the next column = `max(node widths in this column) + gap`, where `gap = callout_w_max(next column's incoming edges) + 2·PAD`, `PAD = 8–12 px`. The horizontal distance parent→child must always be tight, uniform and strictly proportional to the callout width — the 600 px empty bridge must disappear. Keep `MIN_COL_W` only as the echelon-header minimum; global `HGAP` stops driving ETA pitch (keep it for FTA columns / as a sane floor). Recompute `mid_x`/`X_bend` per Step 3.

*Step 2 — Y coordinates (strict ordering + bottom-up contour compaction, Reingold–Tilford):*
1. Strict branch ordering (no self-intersections): for every parent, children are ordered by port: the child on the top port (green, upper callout) is ALWAYS placed above the child on the bottom port; sort consistently and never let a top-port child end below a bottom-port child. This guarantees zero edge crossings for tree structures.
2. Bottom-up post-order traversal with contour profiles. For each node `u`, effective vertical footprint:
   `H_eff(u) = max(H_node(u), H_top_callout(u) + H_bottom_callout(u) + port_gap)`.
   For each subtree `T(u)` maintain per-depth contours: `Top[d]` (min Y at depth d) and `Bottom[d]` (max Y + H_eff at depth d). Leaf: relative Y = 0. Internal node with ordered children c₁…c_k: pack each next child beneath the previous combined contour:
   `shift(c_i) = max over shared depths d of ( Bottom_{c1..ci-1}[d] − Top_{ci}[d] ) + ΔY_min`, with `ΔY_min = 28–36 px` (replaces the uniform `row_h` grid; keep `VGAP_ROW` as the ceiling/fallback).
3. Parent vertical centering on child input ports: `Y(u) = (Y_in(c₁) + Y_in(c_k))/2 − H_node(u)/2`. If a node has a single visible child (straight continuation, e.g. «Воспламенения нет» → «Отложенное воспламенение»), align the child to the parent's active port Y so the connector is a straight line without doglegs; snap to a 1-segment straight horizontal edge when `|Y_out − Y_in| < 4 px`.

*Step 3 — callouts & orthogonal routing:*
1. Callout anchoring: each branch callout sits immediately right of its output port: `X = X(u) + W_node(u) + 8 px`, top callout just above the top port line, bottom callout just below the bottom port line, never overlapping the node, sibling callouts, or each other.
2. Z-routing (3-segment polyline): vertical trunk AFTER the callout: `X_bend = X(u) + W_node(u) + W_callout + 16 px`; route `(X_port_out, Y_port_out) → (X_bend, Y_port_out) → (X_bend, Y_port_in) → (X_port_in, Y_port_in)`; straight-line snap per Step 2.3.
3. Final bounding-box collision audit (safety pass): after placement, check all pairs — node∩node, node∩callout, callout∩callout, edge-segment∩(foreign node/callout). On violation, apply deterministic push-apart (widen gap / shift subtree down) and re-run the audit, bounded iterations; expose `Layout.collisions` (empty list on success) for tests.

**Constraints:** keep hidden favorable fractions unplaced; keep `manual_pos` honored (manual nodes skip compaction but are included in the audit); keep the FTA side logic (phases centered on the root) unless the audit flags collisions; canvas and PDF stay WYSIWYG; `row_cuts` (PDF row slicing) must be recomputed for the new geometry.

**Tests/QA:** extend `gesture_test.py` with a compaction suite on a generated deep/wide tree (reuse `visual_qa_runner.build_mock` ideas): assert (a) every parent→child horizontal gap ≤ `callout_w + 2·PAD + ε`; (b) `Layout.collisions == []`; (c) branch-order invariant (top-port child above bottom-port child for every split); (d) single-visible-child edges are straight; (e) no node overlap after manual drags + relayout. Regenerate `qa_artifacts` and visually inspect `qa_canvas.png`/`qa_sheet.png`.

---

## TASK 5. Pin semantics and edge anchoring bugs (Screenshot 3)

**User-reported symptoms.**
1. Edges come out of the node border BETWEEN the two circles («стрелочки выходят не из кружочков, а между ними») — arrows must start/end exactly on the pin circles.
2. Clicking a RIGHT pin opens «Промежуточные события – встраиваются в цепочку, частоты пересчитываются» and the list effectively always shows the same single row «Взрывное сгорание пылевоздушного облака» regardless of the parent node, while the user expects that from that pin the ONLY continuation is the «Сценарий N» node.
3. Dragging from a LEFT green pin «breaks the canvas»: extra nodes appear WITHOUT pins at all, arrows exit from node middles.

**Root causes found (verify, then fix).**
1. `layout.py` ETA edges use center anchors: `pts = [QPointF(p_right, p_cy), …]` with `p_cy/c_cy = rect.center().y()` (~lines 352–363), while pins live at 32 %/68 % of node height (`canvas.py::_pin_centers`). The polyline never touches the pins.
2. The picker content comes from `Validator.compatible_barriers(node)` (`validation.py:104`): filters are (i) `stage_level` strictly above the node's, (ii) `incompatible_tags` vs `path_tags`, (iii) `required_parent_tags` ⊆ `path_tags`. The KB record `b-dust-blast` («Взрывное сгорание пылевоздушного облака», `stage_level 4.5`, `required_parent_tags: ["ignited"]`, tags `dust`) is often the ONLY survivor for late-stage dust chains — hence the same lone row. Additionally, for nodes whose split is `SPLIT_SCENARIO` («Сценарий N» split), offering intermediate events at all is wrong — the only legal continuation is the scenario terminal node.

**Requirements.**
1. **Edge endpoints on pins.** ETA edges must start exactly at the source pin center (upper callout branch → upper right pin; lower branch → lower right pin — reconcile the pin naming/colors «ДА/НЕТ» with edge label semantics; if the pin color↔branch mapping contradicts today, fix it consistently across `_pin_centers`, tooltips, and tests) and end at the child's left pin matching its row (upper row → `left-yes`, lower → `left-no`; FTA edges keep center anchors — FTA nodes have no pins). Arrowheads still point into the child. Update the Task 4 collision audit to include pin circles implicitly (they sit on endpoints). `_pin_centers` geometry stays the single source of truth — layout must import/reuse it (move it to a shared location if cleaner, e.g. `theme.py` or `layout.py`, and keep `canvas.py` importing from there).
2. **Context-correct right-pin menu.**
   - Fix the degenerate `compatible_barriers` UX: when the list has exactly one candidate because of over-strict filtering, that is legitimate — but verify with several nodes at different levels that the filter is not systematically collapsing to `b-dust-blast` (check `stage_level` monotonicity blocking and `required_parent_tags` breadth; if most intermediate events are unreachable in practice, loosen the filter per KB semantics — e.g. allow `stage_level` equal-or-higher only for the physical split kinds, or enrich `required_parent_tags` coverage — and document the rule).
   - For a node whose split `kind == SPLIT_SCENARIO` (or a node that already precedes a scenario terminal), the right-pin click must NOT offer intermediate events: either it directly creates/links the «Сценарий N» terminal (the only legal child) or shows an explanatory tooltip («Узел уже завершается сценарием — добавление промежуточных событий недоступно»). Match how `hierarchy_panel.py`/`objects.alloc_scenario_title` build scenario nodes.
   - Picker ordering: relevance (compatibility score) first, then title — `b-dust-blast` must not be a universal first choice.
3. **Left-pin drag must not break anything.** `_pin_link_allowed()` must return True only for `right-yes` (build unfavorable branches to the right); `left-yes` behaves like red pins: drag gesture suppressed with tooltip «Левые пины – наращивание дерева отказов (FTA) кликом; связь тянется только от правого зелёного пина». Short click on left pins keeps opening the causes picker (existing correct behavior). Audit `_apply_cause_from_picker` + `add_fta_cause` for the reported «nodes without pins / arrows from the middle» state: FTA `gate`/`cause` nodes legitimately have no pins (`show_pins` only for kinds `init`/`branch`) — so any path that attaches an FTA node into an ETA chain, or creates detached nodes, is a bug; add validation so a dropped link can never mutate the model outside its intended side (ETA right / FTA left).
4. **Regression tests** (`gesture_test.py`): (a) build a scenario node → click right pin → assert the picker does not open or the created child is the «Сценарий N» terminal; (b) simulate drag from `left-yes` (`_begin_pin_press` + move + `_finish_pin` on empty scene / on a node) → assert model unchanged; (c) for a two-branch split assert each edge's first point == corresponding `_pin_centers` point of the parent and last point == the child's left pin; (d) icons assertion still passes (`_assert_icons`).

---

## TASK 6. Rename the section header «ПЕДАЛЬКИ – БАРЬЕРЫ И МОДИФИКАТОРЫ» to scientific / fire-technical Russian

**Problem.** The uppercase caption above the two-column checkbox list of protective measures in the equipment properties form reads «ПЕДАЛЬКИ – БАРЬЕРЫ И МОДИФИКАТОРЫ» (exact locations: `eta\ui\kb_window.py` line ~1317 `cap_pedals = QLabel("ПЕДАЛЬКИ – БАРЬЕРЫ И МОДИФИКАТОРЫ")` in `EquipmentLibraryTab`, and `eta\ui\inspector_panel.py` line ~281 `_caption("ПЕДАЛЬКИ – БАРЬЕРЫ И МОДИФИКАТОРЫ")` in the main-window equipment form). «Педальки» is internal developer slang, «барьеры» violates the project's own terminology rule (§0: the word «барьер» must not appear as a UI term). The checkboxes under it mix two families: counter-accident protections that add ETA chain links with PFD (SIL-ПАЗ, вентиляция, дренаж, датчики утечки, резерв) and λ-modifiers that scale the base failure intensity (износ, герметичность, взрывозащищённое исполнение, виброконтроль).

**Requirements.**
1. Rename the caption in BOTH places to normative Russian phrasing, e.g. «ПРОТИВОАВАРИЙНЫЕ ЗАЩИТЫ И МОДИФИКАТОРЫ ИНТЕНСИВНОСТИ ОТКАЗОВ» (or «ЗАЩИТНЫЕ МЕРЫ И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ» — pick one, use the vocabulary of ГОСТ Р МЭК 61508 / ФНП / Методика № 533; keep it under one line at current form width, style `QLabel#caption` with letter-spacing as other captions). Use the same string constant in both files (define it once, e.g. in `eta\ui\theme.py` or a shared constants spot near `EQUIPMENT_FILTER` vocabulary — do not duplicate literals).
2. Internal names stay: the `pedals` props key, `PEDALS` tuple in `kb_window.py`, `property_modifiers` ids (`pm-*`), `EquipmentLibraryTab.PEDALS`, and all test references to `pedals` are NOT renamed — this is a display-layer caption change only.
3. Sweep the UI for other occurrences of the words «педальки/педалька» and «барьер(ы)» visible to users (tooltips, README phrases describing the UI, status texts). Developer comments in code may keep «педальки» if it refers to the `pedals` key, but user-visible strings must not.
4. Update `gesture_test.py` / `smoke_test.py` assertions that match the old caption (search «ПЕДАЛЬКИ», «БАРЬЕРЫ»); update README if it quotes the caption.

**Acceptance:** both forms (KB window «По оборудованию» and the main-window inspector) show the new scientific caption; no user-visible «педальки»/«барьеры» remain anywhere; tests green; `qa_window.png` regenerated and reviewed.

---

## FINAL DELIVERABLES OF THE SESSION

1. All six tasks implemented, `smoke_test.py` + `gesture_test.py` green (new assertions included), `run_qa.cmd` artifacts regenerated and visually reviewed (note the review in the report).
2. Version bumped to `4.2.0` (`eta\__init__.py`); README.md updated (terminology, math rendering, KB close guard, compaction, pin behavior).
3. `old prompts (done prompts)\REPORT_SESSION_8.md` in English: per-task summary, files touched, algorithm notes (esp. the compaction constants chosen: PAD, ΔY_min, X_bend rules), test results, screenshot references, known issues (incl. the §1 font assertion status).
4. Order of work: Task 3 (small, isolated) → Task 6 (trivial caption) → Task 1 → Task 2 (renderer used by Task 1 combos) → Task 4 → Task 5 (depends on Task 4's audit + pin-anchored routing). Adjust if dependencies dictate, but keep each task's tests passing before moving on.
