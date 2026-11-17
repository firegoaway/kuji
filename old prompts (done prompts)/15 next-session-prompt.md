# PROMPT: Kuji – Session 15. Site values into Q + cause dependencies in the hierarchy + formula typography + node-clipping FINAL fix + flow-scoped causes

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia No. 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–14 are done (v6.4.2: five-type paradigm, KB v6.1 with editable libraries, territory root-only + damaged-file auto-repair, working real-mouse Ctrl/Shift multi-select, collapsed state persistence, ТГМ area/type cascade «участок → помещение → здание» with «– наследуется –», node state colors, engineering notation everywhere + caret input, П1.2 area-on-м² rule, GS causes unfiltered by участок type, canvas hover fix). Read before starting: `old prompts (done prompts)\REPORT_SESSION_14.md` (with its 14/1 and 14/2 addenda; `REPORT_SESSION_13.md` for deeper history). Everything described there works and is covered by tests – do not break it without need. Session 15 is an **engine-propagation + hierarchy-interaction + typography session**: eleven tasks. All design decisions below were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them. Ask questions per §0 when a task or part of it is ambiguous.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report – in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian with correct sentence structure and etiquette (this overrides English for question lists; it is the single exception). If the user did not understand a question, REPHRASE it properly instead of repeating.
- **Application UI language: RUSSIAN** – unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, node texts, messages) must be in normative Russian engineering style (§5 canon).
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
| Core tests | `smoke_test.py` (21 blocks), `gesture_test.py` (blocks 1–19 + 20–29 + 30–38; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – sections: meta (`version` «6.1»), scenario_types (5; titles carry «пожара/взрыва» and parenthetical decodings – Task 7 edits them), gs_causes (68), iz_causes (15), fire_types (8), p21 (per-flow per-medium conditional probabilities), flow_titles (`small` «скорость сгорания < 1 кг/с», `mid` «1–50», `big` «> 50», `rupt` «полный разрыв»), p13 (10), p14 (8), equipment_templates (16; Task 10 makes them editable), property_modifiers (13). Backup: `knowledge_base_v5.json` (keep). `meta.version` stays «6.1» unless a schema change becomes unavoidable (data-title edits are NOT schema changes). |
| Methodology sources | `literature\`: «1 Методология расчета частот возникновения пожара для нужд Методики 533.md», «2 ГОСТ 12.1.004-91_distil.md», «Методика_533_RAG_final.md», «Пример расчёта частот для кондитерского цеха.md» and others – Task 8.4 requires reading them |
| App version | `eta\__init__.py` → `__version__ = "6.4.2"` – this session bumps to **6.5.0**. Status bar shows the version; gesture test asserts it (update the assertion if needed – it currently checks the substring «6.4»). |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_15.md` (English) at the end |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` with verification, delete the script afterwards. Inline `python -c` in pwsh breaks on quotes – write a file. This session DOES edit KB data (scenario titles, template records, possibly flow titles) – follow the rule. |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE. Do not wire it in. |

## 2. STATE AFTER SESSION 14 (v6.4.2) – what exists, all tested

- **Paradigm (invariant):** five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree «Наличие вещества / Наличие ОК → ГС → ИЗ → Возникновение»; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5.
- **ТГМ multiplier (session 14):** `CalcContext.tgm_chain` = per-level OWN props (участок → помещение → здание; outdoor = [self]), built by `objects.tgm_levels(owner)`; F = first explicit `area_m2` in the chain; **the участок level participates ONLY when its `site_type` == «area» (м²)** – Task 1 changes this; type = nearest explicit `p13_type`/`p14_type` (per effective F), building keeps materializing, room/участок show «– наследуется –» (variant (а): only the chosen value is stored). Compat: `tgm_chain=None` → `[building_props]`.
- **П1.2 multiplier (session 14/1, LOCKED):** `CalcContext.p12_value(explicit)` – explicit `len_m` on the GS node wins; on a «м²» участок the multiplier is the (possibly inherited) ПЛОЩАДЬ (м²); linear участки use `length_m`. Formula note shows the unit («× 800 м² (П1.2)»).
- **GS causes (session 14/1, LOCKED):** the picker «Добавить причину…» (`InspectorPanel._cause_records`) and the validator use `kb.gs_for(scenario_type)` WITHOUT a site-kind filter – all causes of the scenario type on ANY участок; equipment templates apply their full GS list without hiding; `kb.gs_for(stype, site_kind)` remains for tests.
- **Hierarchy:** territory root-only + `load_from_dict` auto-repair (nested territories lifted to root, report dict returned; `MainWindow._load_project_data` shows the status message); 7-button toolbar («Добавить дерево» violet); expansion state preserved across rebuilds (`_capture_expansion`/`_apply_expansion`), new участки/установки added COLLAPSED, persisted in the format-5 ui dict (`hierarchy_collapsed`, `hierarchy_groups_collapsed`); real Ctrl/Shift multi-select (selection never rebuilds the tree; `_on_select` never calls `setCurrentItem`); Delete = only the selection (batch window); under each owner sits «Группа сценариев» → scenario-type row → grouped display rows (Task 3 removes all three levels in favor of causes).
- **Cause routing defect (Task 9, suspected – verify):** `MainWindow._current_tree()` returns `trees[0] if len(trees) == 1 else None` (or the selected-scenario tree) – with 2+ trees on one owner, `_add_gs_cause/_add_iz_cause/_remove_gs_cause/_remove_iz_cause` silently no-op although the inspector shows the clicked node's form (`inspector._tree` knows the right tree).
- **Canvas/PDF:** shared `compute_layout` (layout.py) + `render.py`; node body «Всего: N …» + «ΣQ = …»; node states: GS/IZ with ≥1 cause → border #2563EB/fill #EFF6FF; «Возникновение» validator-clean → #7C3AED/#F5F3FF (computed once per tree in `_layout_tree` via `check_tree`); annotation node «{owner} · {scenario title}» per tree; node drag with persisted `node_offsets`; hover tooltips work (`QPointF(mapFromScene(...)).toPoint()` – PySide6 returns QPoint from mapFromScene; NEVER call `.toPoint()` on a bare `mapFromScene` result).
- **Number formatting:** `eta/core/numfmt.py` – `fmt_q` («3,24·10⁻⁶»), `fmt_num` (engineering when %g would show an exponent, comma otherwise), `parse_eng` (e-notation AND caret `m^e` = m×10^e). Matrix Q column uses fmt_q; model formula strings use fmt_num; `theme.parse_sci` delegates to `parse_eng`; KB `_NumberEditor` hint names both notations.
- **Formulas today (Task 4 changes):** matrix rows (refs stripped by `matrix._TABLE_REF`): `Q = 1·1·[a₁·F = 2,2·10⁻⁴·1200]·1−e^ (−3,2·10⁻⁶)`; the PDF report shows the same formula WITH refs; P₂₁ pieces like `P₂₁=0,005`.
- **Inspector:** object forms (building/room/area/outdoor/territory/compartment; «показано = записано» with the ONE exception: room/участок area+type inherited variant (а)); presence form; cause blocks; pedal blocks; `set_owner_getter`; commit-on-leave via Leave event filter.
- **KB window:** tabs «Шаблоны оборудования» (TemplatesTab – READ-ONLY cards + «СОСТАВ ШАБЛОНА» details; «Применить на холсте» only with a selected участок/установка; Task 10 makes it editable), «Горючие среды (ГС)», «Источники зажигания (ИЗ)» (editable libraries, `kb.reindex()` on every mutation), «Таблица типовых режимов пожара» (read-only 8 rows), «Таблицы типовых частот» (П1.3/П1.4/П2.1 sub-tabs), «Защитные средства» (4 columns, coefficient edits drive the engine); bottom bar `[Добавить запись] [Удалить запись]` LEFT, `[Сохранить] [Закрыть]` RIGHT (record buttons hidden on read-only tabs).
- **Tests/QA:** both suites green (smoke 21 blocks incl. cascade/repair/parser; gesture 38 blocks incl. real-mouse multi-select, expansion persistence, states, engineering notation, hover regression); QA artifacts current through v6.4.2.

## 3. CODE MAP (extend, don't break)

- `eta\core\objects.py` – Task 1 (`tgm_levels`: участок participates for ALL site types with its SITE_FIELD value), Task 3.4 (reparent API with PARENT_RULES validation).
- `eta\core\model.py` – Task 1 (tgm_multiplier takes the участок's own value by type), Task 3.3 (cause dependency chains: per-cause parent pointers, scenario generation products chains, serialization), Task 4 (formula strings: substituted numbers, `exp()`, `Q_j`), Task 8 (GS cause flow scope: `GSCause.flow`, FLOWS filtered per cause, duplicate same-ref different-flow allowed).
- `eta\core\numfmt.py` – Task 4 (helpers for the substituted formula format; single source).
- `eta\core\matrix.py` / `eta\ui\main_window.py::_refresh_matrix` – Task 4 (Q_j subscripts; no refs anywhere near formulas).
- `eta\core\layout.py` / `eta\ui\render.py` – Task 5 (the FINAL clipping fix lives in the shared geometry pipeline: dynamic per-line metrics via QFontMetricsF tightBoundingRect/TextDontClip, safety paddings 16–20 px horizontal and 12–16 px vertical, prepareGeometryChange semantics on the canvas side, pin/edge positions derive from the same rects); Task 7 (annotation text uses the renamed scenario titles automatically).
- `eta\ui\hierarchy_panel.py` – Task 3 (new tree model under owners: scenario row → cause rows; drag-and-drop for causes, objects, trees; click behavior), Task 3.1 («Группа сценариев» removal).
- `eta\ui\inspector_panel.py` – Task 1/2 (immediate propagation), Task 6 (outdoor site-type selector + value field), Task 11 (label renames «Функциональное назначение …», «T_ТО», combo popup width rule).
- `eta\ui\main_window.py` – Task 9 (`_current_tree` routing → the inspector's tree), Task 3 (DnD wiring, cause-click selection), Task 1/2 (refresh wiring), Task 10 (template usage counts).
- `eta\ui\kb_window.py` – Task 10 (editable TemplatesTab + bottom-left buttons), Task 8 (GS library exploded rows), Task 11 (labels).
- `eta\export\pdf_export.py` – Task 4 (substituted formulas, Q_j, refs in a separate compact sources block near the tree/under the results), Task 7 (titles).
- `eta\knowledge\knowledge_base.json` – Task 7 (scenario_types titles/fire_node_title), Task 8 (flow-scoped library rows derive from data; possibly flow_titles wording after the 8.4 verification), Task 10 (equipment_templates editable data) – byte-safe scripts only.
- Tests: `smoke_test.py`, `gesture_test.py` – update/add per task list; `visual_qa_runner.py` – add shots where valuable (new hierarchy look, cause nesting, template editor, flow-exploded picker, formula strings, un-clipped nodes).
- Do not touch: `eta\ui\gestures.py` (except if Task 5 requires pin sync – carefully), `eta\ui\scroll.py`, `eta\ui\switch.py`, `eta\core\formulas.py` (dead).

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py` – never fork geometry or colors. Task 5 changes go through the shared pipeline once.
2. No new external dependencies; PySide6-native only.
3. Style: flat Swiss-utilitarian; new visuals via `theme.py`; `outline: none` everywhere focus rectangles could appear.
4. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green – update assertions that reference changed strings/behaviors (grep the tests first); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop+2× upscale for pixel truth) the affected artifacts before declaring the task done. Animations must not break offscreen tests.
5. Manual smoke with `run_app.cmd` is the user's habit – the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
6. Questions per §0 only; LOCKED decisions below are NOT to be re-asked.
7. Modal dialogs block offscreen tests: use/extend the existing seams (`_ask_close_guard`, `_confirm_delete`, `_confirm_multi_delete`, `_confirm_delete_rec`, patched `exec` capture, `_set_number/_set_note`, `_cause_records`) – do not break them; new flows need seams too.
8. Suggested order: 9 (mechanical defect) → 1+2 → 6 → 11 → 7 → 4 → 5 → 8 → 3 (the biggest) → 10. Task 3 changes serialization – do it last among the structural ones and migrate carefully.
9. Format-5 compatibility: old files (incl. files saved by ≤6.4.2) must load; new optional fields degrade gracefully.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses: «уровень полноты безопасности (SIL)».
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Math in labels/tooltips via the project mini-notation (`math()`, `math_html_lines`); raw HTML escaped; QTableWidgetItem cells render NO HTML; rich cells are QLabel cell widgets. Subscripts like «Q_j» render as Q with subscript j; «T_ТО» renders as T with subscript ТО – NEVER literal «$T_{ТО}$» or «T_{ТО}» in UI strings.
- Numbers shown to the user: ALWAYS engineering notation («9·10⁻⁵», comma mantissa, Unicode superscripts) – never `9e-05`.

---

## TASK 1. УЧАСТОК TYPE SWITCH MUST FEED THE CALCULATION (screenshot №1)

**Defect:** with a ТГМ tree on an участок, switching «Выберите тип» to «линейный объект (м)» or «аппарат/установка (м³)» changes only the visible field; the «Возникновение пожара» node frequency and the matrix do not react.

**Root cause (diagnosed):** `objects.tgm_levels` includes the участок level only when `site_type == "area"` – for linear/apparatus участки the ТГМ multiplier F falls back to помещение/здание, so the участок value has no path into the ТГМ math at all.

**Requirements (LOCKED, вариант А):** the ТГМ multiplier takes the участок's OWN value by its site type as the FIRST level of the cascade: «участок (м²)» → `area_m2`, «линейный объект (м)» → `length_m`, «аппарат/установка (м³)» → `volume_m3` (i.e. a₁·значение; for linear/apparatus участки the value substitutes F directly – a deliberate customer decision, dimensionality accepted). Помещение → здание remain the fallback levels as today; the effective type resolution (П1.3/П1.4 switch at F > 10 000) uses this new effective F. Outdoor installations follow Task 6. Update `tgm_levels` + `tgm_multiplier` + the `tgm_view` helper + smoke/gesture cascade tests; the confectionery example stays valid (area-kind участок).

## TASK 2. IMMEDIATE RECALCULATION ON VALUE EDITS (screenshot №2)

**Defect:** editing «Длина, м» (50 → 51251) in the участок properties never changes ΣQ.

**Requirements (LOCKED):** recalculation is IMMEDIATE – every value change (type combo, value spin, area/type fields at every level) propagates to the «Возникновение» node, status bar, matrix and hierarchy rows on the spot (valueChanged wiring exists – verify each form; together with Task 1 the value must actually flow). No «apply on leave» for these fields; commit-on-leave may stay for other forms but must not delay Q.

## TASK 3. HIERARCHY RESTRUCTURE: CAUSES AS CHILDREN + DRAG-AND-DROP DEPENDENCIES + OBJECT/TREE REPARENTING (screenshot №3)

**3.1 Structure (LOCKED):** remove the «Группа сценариев» wrapper and the grouped display rows entirely. New layout under each owner (участок/наружная установка):

```
- Территория
- - Здание
- - - Помещение
- - - - Участок
- - - - - Сценарий пожара ТГМ            ← scenario row (one per tree; Task 7 renames)
- - - - - - Образование ГС: Пожар по поверхности   ← GS causes, prefixed
- - - - - - Отказ осветительных приборов            ← IZ causes, plain titles
- - - - - - ... и т.д., что добавил пользователь
```

Scenario rows are renamed per Task 7; the parenthetical decoding disappears (also from the canvas annotation, KB, PDF).

**3.2 Cause rows:** ALL user-added causes (GS and IZ) on one level under the scenario row; live-updated on add/remove. GS rows carry the prefix «Образование ГС: <название причины>»; IZ rows the plain title.

**3.3 Cause dependencies via drag-and-drop (LOCKED):** the user presses LMB on a cause row and drops it onto ANOTHER cause of the SAME list (ИЗ → ИЗ only, ГС → ГС only – mixing GS/IZ is not allowed). The target becomes the PARENT: the dropped cause is a consequence of the parent («Отказ кабельных линий» under «Удар молнии» = cable failure follows from the lightning strike). Chains of any depth are built exactly this way (customer's four-step example in the Q&A: lamp under cable; then cable under lightning → lightning → cable → lamp). Dropping a cause onto the scenario row detaches it back to top level.
- **Math (LOCKED, вариант А):** Q(зависимая ветвь) = Q(родитель) × Q(потомок) – an AND-gate; a dependent cause no longer contributes an independent scenario row; instead the parent chain contributes ONE combined row whose factor is the product along the chain (for ТГМ: q_sub·q_ox·(a₁·значение)·Π(1−exp(−λ_i)) along the chain; for ГГ/ГЖ/ЛВЖ: the chain product multiplies as the ИЗ-factor of the parent's scenario rows; several independent chains/roots at top level sum as today). The formula string shows the substituted product (Task 4 format); the matrix row name reflects the chain (e.g. «Удар молнии → Отказ кабельных линий»).
- **UI/UX:** during drag, valid drop targets highlight (same-list cause rows and the scenario row for detach), invalid targets give clear feedback (cursor/red frame) and the drop is rejected; after the drop the tree, canvas, inspector counts, matrix and Q update immediately. The dependency survives serialization (format 5: extend GS/IZ cause records with an optional parent reference or store the per-node cause tree; old files without it load flat) and the «Убрать» flow removes the cause with its children (confirm seam with the chain listed).
- **Click on a cause row (LOCKED):** the scenario's tree stays on the canvas; the inspector opens the corresponding node form (ГС or ИЗ) AND the canvas node gets the dashed selection as if it were clicked with LMB.

**3.4 Object reparenting via drag-and-drop (LOCKED):** участок → любое допустимое помещение, помещение → здание/отсек, здание → территория, наружная установка → территория. The WHOLE subtree (children, trees, their causes and dependencies) moves together. `PARENT_RULES` is enforced (territory – root only; the add-rules from the toolbar apply to drops); an invalid target highlights and the drop returns to origin. The selection follows the moved object; collapsed state and node offsets persist.

**3.5 Tree reparenting via drag-and-drop (LOCKED):** a scenario row may be dragged onto another owner (участок/установка) ONLY when the scenario type matches (ТГМ → ТГМ, ГГ → ГГ, …); otherwise the drop is rejected with feedback. The tree's owner_id changes; annotation texts follow.

## TASK 4. FORMULA TYPOGRAPHY: FULL SUBSTITUTION, exp(), Q_j (screenshot №4)

**Defect:** matrix formulas read `Q = 1·1·[a₁·F = 2,2·10⁻⁴·1200]·1−e^ (−3,2·10⁻⁶)` – symbolic labels («a₁·F =») sit mid-formula, and the «e^» power tower is ugly.

**Requirements (LOCKED):**
1. Formula strings everywhere (matrix, PDF report, node tooltips) are FULLY substituted numbers with grouping parentheses and the scenario index subscript: `Q₂ = 1·1·(2,2·10⁻⁴·1200)·(1−exp(−3,2·10⁻⁶))` – where j is the scenario's row number in the list (matrix № column; PDF rows numbered the same). `e^` → `exp(...)`; no symbolic names (a₁·F, P₂₁, N_у.м) inside the formula – only numbers; Q with subscript j via the mini-notation/superscript machinery (plain text fallback: «Q2»).
2. The PDF REPORT keeps NO references inside formulas; instead each report sheet carries a compact separate sources block under the results (e.g. «Источники: табл. П1.3 – множитель a₁·F; табл. 9 прил. 3 ГОСТ 12.1.004-91 – λ ИЗ; …») – laconic, one line per used table, derived from the same data (do not hand-maintain).
3. Numbers inside stay engineering notation (fmt_num); Task 3 chains multiply as products of their factors.

## TASK 5. NODE TEXT CLIPPING – FINAL FIX (screenshot №5; 4th attempt, customer is unhappy)

**Defect:** digits/letters/superscripts are still cut at node borders (e.g. the tail of «год⁻¹» and «10⁻⁶» in «ΣQ = 2,28·10⁻⁶ год⁻¹», tight «1,000» in presence nodes).

**Root-cause class (customer-provided technical guidance – follow it as normative):** past attempts tuned paddings/constants instead of fixing the Qt geometry computation. Required architectural fix:
1. Remove hard sizes: no hardcoded node width/height constants deciding text fit (MIN/MAX caps may remain as LAYOUT hints, but the text rect must be computed from real metrics).
2. Use exact font metrics: compute each line's real rect with `QFontMetricsF(font).tightBoundingRect(line)` or `boundingRect(QRectF(), Qt.TextDontClip, line)` (TextDontClip mandatory so superscripts like «10⁻⁶»/«год⁻¹» are not cut by height/right edge). Never `len(text)*const`, never integer `fontMetrics().width()`.
3. Final width = max line width + paddings with safety margins (≥16–20 px horizontal, ≥12–16 px vertical); keep the whole-word/syllable wrapping (wrap_words) as the FIRST stage, metrics as the DECIDING stage; the longest word still widens the node.
4. Synchronize `boundingRect()` (canvas items derive from NodeGeo.rect + margins), call `prepareGeometryChange()` where items mutate, and recompute pin positions/edge paths from the same rects so curves do not overlap the widened frames.
5. WYSIWYG: the fix lives in `compute_layout`/`render` once – canvas and PDF consume it. QA with 2× crops asserting no pixel of any glyph touches the node border (programmatic metrics assertions beat vision).
6. Report per the guidance: show the exact file/lines where the old rect math lived and how the new QRectF is computed.

## TASK 6. НАРУЖНАЯ УСТАНОВКА: SITE-TYPE SELECTOR (screenshot №6)

**Requirement (LOCKED):** the outdoor form gets the same «участок (м²) / линейный объект (м) / аппарат/установка (м³)» selector and a «ЗНАЧЕНИЕ» field as the участок form, with the SAME logic: the value by type feeds this installation's trees (the ТГМ multiplier a₁·значение per Task 1; П1.2 pipeline causes use the value by type via `p12_value` – outdoor stops being a special case: `tgm_levels` for outdoor = [its own value by site type]). The existing «Площадь, м²» field becomes the value field of type «участок (м²)»; existing projects keep their current `area_m2` (default 400) as type «участок (м²)» (migration: absent site_type on outdoor = «area»). The «Тип (П1.3/П1.4)» combo stays (renamed per Task 11).

## TASK 7. RENAMES: «ПОЖАР/ВЗРЫВ» → «ПОЖАР», DROP DECODINGS (Task 5.1 of the Q&A)

**Requirements (LOCKED):**
1. Everywhere the UI says «пожара/взрыва» / «Возникновение пожара/взрыва» it becomes «пожара» / «Возникновение пожара»: `scenario_types` titles («Сценарий пожара/взрыва ЛВЖ …» → «Сценарий пожара ЛВЖ»), `fire_node_title` («Возникновение пожара/взрыва» → «Возникновение пожара») – KB data edit via byte-safe script; canvas annotations, hierarchy rows, matrix «Тип сценария» column, PDF – all follow from the data. Status bar label «Q_возникновение» is already fine.
2. Remove the parenthetical decodings «(твердые горючие материалы)», «(горючие газы)», «(горючие жидкости)», «(легковоспламеняющиеся жидкости)», «(сжиженные газы)», «(пыли)» from scenario titles EVERYWHERE (KB titles, hierarchy, canvas annotation, KB window, PDF) – EXCEPT places where the text is normative (if a decoding is part of a normative source name, keep it there).
3. DO NOT touch normative fire-regime names from табл. П2.1: «Сгорание (взрыв) топливовоздушной смеси», «Сгорание (взрыв) пылевоздушной смеси – дефлаграция/детонация» etc. stay as is.

## TASK 8. FLOW-SCOPED GS CAUSES (screenshots №7 + rulings; Tasks 5.2–5.4 of the Q&A)

**8.1 Exploded rows (LOCKED):** in the picker «Добавить причину…» (inspector) AND in the KB library tab «Горючие среды (ГС)», each release-type GS cause is exploded into rows per скорость сгорания: «Аппарат (сосуд) под давлением: Разгерметизация, Отверстие 5 мм - Скорость сгорания < 1 кг/с (добавляет соответствующие сценарии)» … «…1–50 кг/с», «…> 50 кг/с»; «полное разрушение» is its own row (диапазон «полный разрыв»). Capitalize the sub-parts as shown («Разгерметизация, Отверстие 5 мм»).
**8.2 Independence (LOCKED):** each exploded row is an INDEPENDENT cause: the user may add several intervals of the same physical opening (two entries of «отверстие 5 мм» with different speeds); each entry generates ONLY its interval's scenarios; ALL fire regimes possible for that interval+medium per П2.1 appear automatically together (Факельное горение, Пожар-вспышка, Пожар пролива, Сгорание (взрыв) ТВС – the columns with P > 0). The user may also drag one GS cause under another GS cause (dependency per Task 3.3) – his choice.
**8.3 Causes without flow division (LOCKED):** direct П1.1 events, ТГМ-поверхность, dust (дефлаграция/детонация) stay ONE row without a speed suffix.
**8.4 Methodology verification (required):** re-verify the flow intervals against the sources in `literature\` (Методика 533 прил. 2 табл. П2.1; ГОСТ 12.1.004-91; the methodology distill) – confirm the intervals are exactly «< 1 кг/с», «1–50 кг/с», «> 50 кг/с», «полный разрыв» (mass flow rate groups) and that each interval attaches exactly the fire regimes the methodology prescribes per medium (gas / two-phase / liquid → jet/flash/vce/pool columns and their conditional probabilities in `kb.p21`). Fix data/attachment if discrepancies are found and document them in the report (quote the source lines). Check the «Огненный шар» special case stays separate.
**8.5 Engine/data:** `GSCause` gains an optional `flow` scope (small|mid|big|rupt|None); `TreeModel.scenarios` iterates only the cause's flow (None → all flows as today); duplicates of the same ref with different flows are allowed (update the duplicate validator check: same ref AND same flow is a duplicate); serialization round-trip; format 5 compatible.

## TASK 9. CAUSES CANNOT BE ADDED WHEN A SECOND TREE EXISTS (screenshot №8 of the defect batch)

**Defect:** on a наружная установка with an existing scenario tree (e.g. ГГ), after adding another scenario (e.g. Пыль), causes cannot be added into the second tree's ГС/ИЗ nodes – the inspector form opens (empty cause list, «Добавить причину…» present) but nothing lands.

**Suspected root cause (diagnosed – verify quickly):** `MainWindow._current_tree()` returns `trees[0] if len(trees) == 1 else None` (plus the selected-scenario branch) → with 2+ trees on the owner the cause add/remove handlers silently no-op.

**Requirement:** route all cause add/remove/pedal operations through the tree that owns the inspected node (the inspector already holds `self._tree` in `show_tree_node`) – pass the tree explicitly from the inspector signals or query the inspector's current tree; keep the test seams; also check the template-apply and KB-apply paths for the same class of bug. Regression test: two trees on one owner, add causes to the second tree via the picker seam.

## TASK 10. EDITABLE «ШАБЛОНЫ ОБОРУДОВАНИЯ» (screenshot with the KB annotations)

**Requirements (LOCKED):**
1. The right panel «СОСТАВ ШАБЛОНА» becomes an EDIT FORM for the selected template: «Название» (line edit), «Категория» (line edit), «Тип сценария» (one of the five), «Разновидности ГС» (list: add from the GS library picker incl. flow-scoped rows per Task 8, remove rows), «Разновидности ИЗ» (list: add/remove from the IZ library). Nothing else for now (customer confirmed; more may come later).
2. `[Добавить] [Удалить]` template buttons appear BOTTOM-LEFT of the KB window (uniform with the other library tabs – the customer explicitly declined the search-row variants). New template defaults: title «Новый шаблон оборудования», empty lists, category «Прочее», scenario type «gg» – document in the report.
3. Deleting a template warns with the usage count (trees created from it – reuse the `_usage` machinery); dirty-guard and «Сохранить» (kb.save) semantics as the other libraries; `kb.reindex()` after mutations; the «Применить на холсте» flow keeps working with the edited lists; card/details preview live-update.

## TASK 11. LABEL RENAMES + COMBO POPUP WIDTH RULE

1. **«T_тест» → «T_ТО»** everywhere (the measure-title label, tooltips, KB texts, tests): rendered via the mini-notation as T with subscript «ТО»; NEVER literal «$T_{ТО}$»/«T_{ТО}» in UI strings.
2. **«Тип (П1.3)» → «Функциональное назначение (П1.3)»** and **«Тип (П1.4)» → «Функциональное назначение (П1.4)»** everywhere: form labels (building/room/участок/outdoor), tooltips, validator notes, PDF report lines («тип П1.3:» → «функциональное назначение (П1.3):»), tests.
3. **Combo popup width (type combos and any long-item combo):** the dropped list sizes dynamically to the longest entry, capped so no line exceeds 85 characters; longer entries wrap by whole words, or by syllables with «–» (reuse `wrap_text85` machinery); the closed button keeps its current sizing (wide_combo rules unchanged for other combos).

---

## 6. LOCKED DECISIONS (Q&A rounds before this session – normative, not to re-ask)

1. (Task 1) ТГМ multiplier = a₁ × the участок's own value by its site type (вариант А) – linear/apparatus участки feed the multiplier with length/volume; помещение → здание remain the fallback cascade.
2. (Task 2) Recalculation on type/value changes is IMMEDIATE (on every change, not on leave).
3. (Task 3) Hierarchy children of a scenario = user-added causes (GS prefixed «Образование ГС:», IZ plain), one level; «Группа сценариев» and grouped rows are removed.
4. (Task 3.3) Cause drag-and-drop builds parent chains: dropped cause = consequence of the target; ONLY within the same cause list (ИЗ→ИЗ, ГС→ГС); math Q = Q(родитель) × Q(потомок); chains of any depth; drop on the scenario row detaches.
5. (Task 3.4/3.5) Objects reparent with their whole subtree under PARENT_RULES; trees move between owners only with matching scenario type.
6. (Task 3.6) Click on a cause row keeps the tree on canvas, opens the node's form in the inspector and dashed-selects the canvas node.
7. (Task 4) Formulas fully substituted, `exp()` instead of `e^`, grouping parentheses kept, subscript Q_j; the PDF report has no refs inside formulas – sources in a separate compact block.
8. (Task 5) The clipping fix follows the customer-provided technical guidance (metrics-driven geometry, TextDontClip, safety margins, prepareGeometryChange, pin sync) – architecture, not constants.
9. (Task 6) Outdoor gets the участок/линейный/аппарат selector with the same value logic; existing projects default to «участок (м²)».
10. (Task 7) «пожар/взрыв» → «пожар» and decoding removals everywhere EXCEPT normative names (П2.1 regime titles stay).
11. (Task 8) Exploded flow rows are independent causes; all regimes of the interval appear automatically; no-flow causes stay single-row; the KB GS library is exploded too; intervals to be re-verified against the methodology sources.
12. (Task 9) Cause operations must work for every tree of an owner (route via the inspected tree).
13. (Task 10) Templates become editable (name/category/scenario type/GS list/IZ list); [Добавить]/[Удалить] bottom-left, uniform.
14. (Task 11) «T_ТО» and «Функциональное назначение (П1.3/П1.4)» renames; combo popup width dynamic ≤85 chars with word/syllable wrap.

## 7. FINAL DELIVERABLES

1. Questions asked per task BEFORE its implementation where genuinely ambiguous (§0); locked decisions not re-asked.
2. All eleven tasks implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated; new blocks: immediate propagation incl. type switch, cause DnD dependency chains incl. math and serialization, object/tree reparenting, substituted formulas with Q_j and exp(), un-clipped node metrics (programmatic), outdoor selector, renames, flow-scoped causes incl. library, two-tree cause routing, template editor); `run_qa.cmd` regenerated and vision-reviewed (new hierarchy look with cause nesting, template editor, exploded picker, formula strings, node borders).
3. Version → **6.5.0** (KB `meta.version` stays «6.1»); README updated where behavior is user-visible.
4. `old prompts (done prompts)\REPORT_SESSION_15.md` (English): per-task summary, files touched, root causes with the exact fix, before→after strings for every changed user-facing label/tooltip/format, the 8.4 methodology verification quotes, test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Cyrillic file/KB edits: byte-safe temporary Python scripts only; never pwsh string cmdlets; delete scripts after use; no em-dash anywhere.
- Modal dialogs block offscreen tests: use the seams; new confirmations must be seams too.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: app-level filters/animations keep strong module-level refs; toolbar buttons use NoFocus.
- Delete delivery: tree/canvas VIEWPORT event filters; the tree filter is installed exactly ONCE; the rename editor owns Delete while editing.
- Selection ↔ rebuild coupling: never rebuild the tree on a selection change; never `expandAll()` blindly – preserve per-oid collapsed state; programmatic `setCurrentItem` on a hidden item expands its ancestors (Qt scrollTo).
- Real-mouse testing for multi-select/DnD: `QTest.mouseClick/mouseMove` on `visualItemRect` centers, `scrollToItem` first, clamp the click X into the viewport (wide name column); programmatic `setSelected` hides mouse-path bugs.
- `mapFromScene` returns QPoint in this PySide6 build – always wrap `QPointF(...).toPoint()`; `QEvent` is in QtCore, `QGraphicsSceneHoverEvent` in QtWidgets.
- «показано = записано» has exactly ONE exception (room/участок area + type inheritance); do not materialize those, do not break the others.
- Letter shortcuts need Latin+Cyrillic twins; QTest keyClick sends key CODES. The Alt+A/Alt+Ф twins print a harmless «Ambiguous shortcut overload» on Russian layout – known, keep.
- QTableWidgetItem renders NO HTML; rich cells are QLabel cell widgets; mini-notation for math; `html.escape` KB titles.
- One painter per QPdfWriter, new pages via `newPage()` only; PDF export uses `layout.scene_rect`; QPdfDocument holds the file until `close()`; `getAllText` injects stray spaces – compare space-insensitively.
- Offscreen QA: `QT_QPA_FONTDIR=C:\Windows\Fonts`; stderr noise is harmless; never leave a modal open in a test; a stray modal in the QA runner hangs it forever (keep add-flow preconditions valid).
- KB libraries: `kb.reindex()` after any direct data-list mutation; the real knowledge_base.json must never be modified by tests (snapshot/restore `kb.data` in memory).
- Vision QA reads downscaled images – crop and 2× upscale before asking glm-5.3-flash; programmatic checks beat vision estimates.
- WYSIWYG invariant: canvas and PDF both consume `compute_layout` + `render.py` – every geometry/color change goes through them once.
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches.
