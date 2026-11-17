# PROMPT: Kuji – Session 11. KB «Защитные средства» language & layout cleanup (normative Russian engineering style), per-pixel smooth scrolling, sub-tabs for typical-frequency tables, template-tab selection design, bold-text fix

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` — do NOT rename it) — a constructor of logical event trees per Order of the Ministry of Emergency Measures of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–10 are done (v6.0.0 + the 10.1 UX-polish round). Read before starting:
`old prompts (done prompts)\REPORT_SESSION_10.md` (five-type paradigm: invariant trees «Наличие вещества / Наличие ОК → ГС / ИЗ → Возникновение пожара/взрыва», KB v6.0, format 5, switches, section blocks, wide combos, report sheet). Everything described there works and is covered by tests — do not break it without need. Session 11 is a **polish session**: five tasks, mostly inside the «База знаний» window and the scrolling layer. Precise decisions for every task were already confirmed by the customer in a Q&A round — they are normative for you and are restated below; do not re-open them.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report — in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian (this overrides English for question lists; it is the single exception).
- **Application UI language: RUSSIAN** — unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, table cells, notes, messages) must be in normative Russian engineering style (see Task 1 style rules).
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README. Never «—» (em dash).
- Questions protocol (HARD GATE): ask **incrementally, per task, as work progresses**, NOT as one giant upfront list. When a task or part of it is ambiguous, has no concrete object, or carries double meaning — STOP that task, formulate a SHORT numbered question list in Russian about exactly that task, send it, and WAIT. Do not implement on assumptions. Principle #1 from the customer: «Better to ask 10 times than to mess up once.» While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items — but nothing that changes data semantics or file formats. All decisions already locked in this prompt (§2, tasks) must NOT be re-asked.

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` — Python 3.14.3, PySide6 6.12.0 |
| Entry point | `main.py`; launcher `run_app.cmd` |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`: qa_window, qa_canvas, qa_matrix, qa_docview, qa_sheet, qa_inspector_fire, qa_inspector_building, qa_switches, qa_kb_templates, qa_kb_measures, qa_kb_tables, qa_pdf_page1, qa_pdf_matrix_page1, qa_pdf_report, qa_stats.json) |
| Core tests | `smoke_test.py` (18 blocks), `gesture_test.py` (12 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` — sections: meta, scenario_types (5), gs_causes (68), iz_causes (15), fire_types (8), p21, flow_titles, p13 (10), p14 (8), equipment_templates (16), property_modifiers (13, each with `target`: gs/iz/room/building); `meta.version` = «6.0». Old-format backup: `knowledge_base_v5.json` (keep). |
| App version | `eta\__init__.py` → `__version__ = "6.0.0"` — this session bumps to **6.1.0**; KB `meta.version` bumps to **«6.1»** (content revision, no schema change). Status bar shows the version. |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_11.md` (English) at the end |
| Normative literature (in-project, for source-number lookup ONLY) | `literature\` — `Методика_533_RAG_final.md`, `2 ГОСТ 12.1.004-91_distil.md`, `3 СП 12.13130.2009.md`, `БЗ_отказы_оборудования_и_антагонисты.md` |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` or explicit utf-8 `io.open` round-trip with verification (`json.loads` before and after, unique anchor line, length delta check, no em-dash), delete the script afterwards. Inline `python -c` in pwsh also breaks on quotes — write a file. |

**Task 1 style canon (confirmed by the customer, normative for the whole session):**
- «Примечание» texts: concise normative Russian engineering language. Rephrase jargon like «формула-якорь», «барьер», «горячий/холодный резерв», «по схеме голосования».
- Do NOT use «;» in prose. Use a period and start a new sentence.
- No variable decodings («где A – кратность…») inside table notes. Format: `формула (номер пункта или номер формулы источника) – краткое описание того, что формула даёт расчёту частот`. Numbers in parentheses come ONLY from the existing `source` string of the KB record; if absent — search the project `literature\` folder for the precise reference; if still absent — omit the parentheses entirely. NEVER invent reference numbers.
- SIL/PFD style: Russian term first, Latin abbreviation in parentheses after it — «уровень полноты безопасности (SIL)», «вероятность отказа по запросу (PFD)». Same pattern for any other Latin term with an established Russian equivalent.
- The word «барьер» in app UI/data: replace with «защитное средство» or «противоаварийная защита» depending on context (in normative citations inside tooltips «барьер безопасности» remains acceptable ONLY when quoting the source verbatim).
- Prefer widely established mathematical/physical terminology.

## 2. STATE AFTER SESSION 10 (v6.0.0 + 10.1 polish) — what exists, all tested

- **Paradigm**: five invariant scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree per type; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; scenarios enumerated combinatorially (all расход ranges × each release); format 5 clean break (formats 1–4 rejected with «Формат проекта устарел»).
- **KB window** (`eta\ui\kb_window.py`): tabs «Шаблоны оборудования» (cards + details pane «СОСТАВ ШАБЛОНА» + bottom bar: btn_close «Закрыть» far-left, stretch, btn_reload «Перечитать», btn_save «Сохранить» right), «Разновидности ГС», «Разновидности ИЗ», «Типы горения» (editable `_TableTab`s with wrap85 + auto-fit), «Таблицы типовых частот» (`MethodTablesTab`: three stacked read-only tables П1.3/П1.4/П2.1, stretch columns), «Защитные средства» (`_MeasuresTab`: read-only table «Наименование средства | Коэффициент | Примечание», notes as QLabel cell widgets with `math_html_lines` rich text and manual row heights via `_apply_row_heights`, showEvent/resizeEvent hooks).
- **Scrolling** (`eta\ui\scroll.py`): app-wide `ScrollWideFilter` — Shift+wheel horizontal; plain wheel animated via `QVariantAnimation` (`SMOOTH_MS = 150`, `SMOOTH_NOTCH_PX = 60`, OutCubic, retargetable per scrollbar, strong refs kept). TreeCanvas/DocumentView excluded (they zoom).
- **Inspector** (`eta\ui\inspector_panel.py`): object forms as section blocks (`_section` = HLine + caption + spacing from `eta\ui\controls.py`), single auto-switching «Тип (П1.3)/(П1.4)» combo (switches at F > 10 000 м²), «Молниезащита» switch gates «Категория защиты» + габариты S/L/H; room «СРЕДСТВА ПРОТИВОАВАРИЙНОЙ ЗАЩИТЫ» block (Аварийная вентиляция + A-поле); area «ТИП» / «ЗНАЧЕНИЕ» blocks; commit-on-leave (eventFilter Leave → clearFocus); math labels via mini-notation `F_зд`, `N_у.м`, `K_σ` (`theme.math`).
- **Hierarchy** (`eta\ui\hierarchy_panel.py`): 6-button toolbar spread evenly; «Группа сценариев» under each Участок/установка; selection survives rebuild (`_current_marker`/`_restore_selection`; `select_object` syncs the tree current item); ElideNone + horizontal scrollbar (no «…»).
- **Controls** (`eta\ui\controls.py`): `wide_combo` (popup 2× button width, word-wrap items, 4 px spacing), `HLine`, `section_header`, `wrap85` (85-char word wrap), `HtmlDelegate`.
- **Theme** (`eta\ui\theme.py`): `PEDALS_CAPTION = "ЗАЩИТНЫЕ СРЕДСТВА И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ"`; QSS has `outline: none` for QTabBar/lists/tables (no dotted focus rectangles) and `QLabel#targetBadge` (rounded gray badge for «Цель: …»).
- **Templates tab**: `_TemplateCard` QFrame#kbCard with word-wrapped title+meta; details QLabel built as `f"<b>{rec['title']}</b><br>{st title}<br><br>Разновидности ГС:<br>{bullets}…"`. Selection state exists only as `selected_id`; cards carry NO visual selection styling. The `hint` QLabel#targetBadge shows «Цель: …» or empty text — an empty bordered pill remains visible when no owner is selected.
- **Tests/QA**: both suites green; QA artifacts current; vision-reviewed (qa_kb_measures, qa_kb_tables, qa_kb_templates, qa_inspector_building all PASS with known minor notes).

## 3. CODE MAP (v6.0.1-ish; extend, don't break)

- `main.py` — entry (QSS, `install_scroll_wide`, `install_modern_tooltips`, `migrate_qsettings`, `MainWindow(kb)`).
- `eta\core\model.py` — `Presence/GSCause/IZCause/ScenarioRow/CalcContext/TreeModel` (engine; `scenarios/total_q/display_lines`), ТГМ multiplier auto-switch `a₁·F ↔ a·F^b` at `TGM_AREA_LIMIT_M2`.
- `eta\core\kb.py` — KB accessors (gs_for, iz_all, fire_for, p13/p14_by_id, modifiers_for_target, save/reload).
- `eta\core\objects.py` — kinds territory/building/compartment/room/area/outdoor; `SITE_TYPES/SITE_FIELD`; `effective_site_type`.
- `eta\core\serializer.py` — format 5; `eta\core\validation.py`; `eta\core\layout.py` (5-node layout, `fmt_q`); `eta\core\matrix.py` (`build_matrix`).
- `eta\ui\main_window.py` — tree ownership, ctx_map, selection semantics, KB apply (`_apply_library_equipment` filters template causes by site kind), save/load, doc window, status bar.
- `eta\ui\canvas.py` / `render.py` / `docview.py` / `doc_window.py` / `hierarchy_panel.py` / `inspector_panel.py` / `kb_window.py` / `controls.py` / `switch.py` / `scroll.py` / `dialogs.py` / `theme.py` / `icons.py` / `modern_tooltip.py` / `gestures.py`.
- `eta\export\pdf_export.py` — `_Doc` single-painter (mm coordinates), schematic + full-width matrix + report sheet «Отчет о расчете частоты возникновения пожара» (toggle in dialog).
- Tests: `smoke_test.py` (18 blocks: KB integrity incl. `PEDALS` target checks, math vs confectionery example, П2.1 exactness, combinatorics, serialization, layout, switches, palette), `gesture_test.py` (12 blocks: window/menus, hierarchy + selection-survives assertion, Группа сценариев, canvas→inspector, cause add/remove, KB apply flow, switch visibility pairs, delete-dialog default/focus, cascade delete, format-5 round-trip, doc window, PDF matrix+report).

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py` — never fork geometry (not touched this session, but keep the invariant).
2. KB JSON edits are data edits via byte-safe Python scripts only (§1); do not rename internal ids/keys (`pm-*`, `b-*` gone, `gs-*`, `iz-*`, `ft-*`, `p13-*`, `p14-*`, `eq-*`); this session rewrites only human-readable strings (`title`, `formula`, `source`, `notes`, `tooltip` where present) in `property_modifiers` per the canon.
3. No new external dependencies; PySide6-native only.
4. Style: flat Swiss-utilitarian; new visuals via `theme.py` QSS (objectName-driven), no ad-hoc colors.
5. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) green — update assertions that reference renamed strings (e.g. «по схеме голосования», «Наличие резерва», tab labels — grep the tests); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact) the affected artifacts before declaring the task done. Animations must not break offscreen tests.
6. Manual smoke with `run_app.cmd` is the user's habit — the app must start cleanly. Do NOT launch `run_app.cmd` in automated batches.
7. Questions per §0 only; locked decisions below are NOT to be re-asked.

---

## TASK 1. KB WINDOW BOTTOM BAR + «Защитные средства» LANGUAGE OVERHAUL

**1a. Bottom bar buttons** (`eta\ui\kb_window.py::KBWindow` bottom layout). Current bar: «Закрыть» (far left), stretch, «Перечитать», «Сохранить». The customer reports «Перечитать» does nothing useful. Required final state: bottom-right group is exactly two buttons in this order: **«Сохранить» (primary, blue) then «Закрыть»**; the left-side «Закрыть» and the «Перечитать» button are removed. «Закрыть» closes the KB window via the existing dirty-guard path (`_ask_close_guard` on unsaved edits — keep it). If «Перечитать» behavior is genuinely wanted later it can return as a menu action — do not keep a dead button.

**1b. Normative rewrite of `property_modifiers` content** (persist into `knowledge_base.json` via a byte-safe script; `meta.version` → «6.1»). For EVERY modifier record rewrite `title`, `formula`, `source`, `notes` (and `tooltip` only if trivially rephrasable — long pedagogical tooltips may simply be dropped from the TABLE but must stay valid if kept; prefer shortening them to the canon too):
- Table note format per canon (§1): `формула (пункт/формула источника) – краткое описание привязки к расчёту частот`. Example target for «Аварийный дренаж / слив»: Коэффициент column stays numeric (see 1c), Примечание becomes: `F_вых = F_вх · k_др (ГОСТ Р 12.3.047-98, прил. Э, п. Э.4.5) – снижение частоты развития аварии при устройстве аварийного слива` — that is the pattern: formula, reference in parentheses, en-dash, one short purpose sentence. Periods, not semicolons. No variable decodings.
- Specific renames (confirmed):
  - «по схеме голосования» → **«по схеме резервирования»**.
  - «Наличие резерва (горячий/холодный)» → **«Резервирование противоаварийной защиты»**, note briefly explaining the schemes by essence: 1 из 2 — защита отказывает только при отказе обоих каналов (квадрат вероятности отказа по запросу); 2 из 3 — срабатывание по большинству каналов (три квадрата минус два куба той же вероятности). Normative wording, formulas through `math()` notation where rendered.
  - «барьер»/«барьер безопасности» → «защитное средство» / «противоаварийная защита» (UI and data; keep only inside verbatim normative quotes if any).
  - SIL/PFD phrasing → «уровень полноты безопасности (SIL)», «вероятность отказа по запросу (PFD)» everywhere in table text; coefficient strings like «1 − 0,95 (PFD барьера)» become «1 − 0,95 (вероятность отказа по запросу)».
  - Purge «формула-якорь» and similar coinages; prefer established math/physics terms.
- The `_MeasuresTab` coefficient column (`_coef`) and note builder (`_note`) consume these fields — after the data rewrite, re-check the rendered table (vision pass on a regenerated `qa_kb_measures.png`): no «;» runs in notes, no jargon, numbers in parentheses match the KB `source` strings, subscripts render.

**1c. Reference-number sourcing rule (locked):** numbers come ONLY from (in order) the record's existing `source` string → the project `literature\` folder (grep for the formula/point) → omitted. Never invented.

## TASK 2. TRUE PER-PIXEL SMOOTH SCROLLING (the current one still jumps whole cells)

**Problem:** despite the animated wheel filter (`scroll.py`), tables/trees still scroll in whole-row jumps and «skip cells entirely». Root cause: `QTableWidget`/`QTreeView`/`QListView` default `verticalScrollMode` is `ScrollPerItem` — the scrollbar unit is one row, so any animation snaps to row boundaries (and horizontal scrollbars step whole columns).
**Requirements:**
1. Set `ScrollMode.ScrollPerPixel` (vertical AND horizontal where applicable) on: all `QTableWidget`s in `kb_window.py` (including the read-only tables and `_MeasuresTab`), the matrix `QTableWidget` in `main_window.py`, the hierarchy `QTreeWidget`, all `QListWidget`s (cause picker, template card list scroll area already pixel-based), and the KB tables after every reload (mode survives content resets, but set it in constructors anyway).
2. With per-pixel mode, set sane `verticalScrollBar().setSingleStep(20)` so the animated filter's 60 px/notch moves in fine steps; tune `SMOOTH_NOTCH_PX`/`SMOOTH_MS` if needed for a fluid feel (~120–180 ms, OutCubic, retarget on consecutive wheel ticks — the existing animation logic already retargets; verify).
3. `resizeRowsToContents`/`resizeColumnsToContents` interplay: after any content reload in per-pixel mode the scrollbar range changes — ensure no position jumps on reload (keep current first-visible row where reasonable).
4. Keep Shift+wheel horizontal behavior; keep TreeCanvas/DocumentView exclusions (zoom).
5. Manual-feel verification in QA is limited — verify programmatically: simulate wheel events on a table (send `QWheelEvent` via `QApplication.sendEvent` to the viewport) and assert the scrollbar value passes through intermediate pixel values (not just row multiples) during animation; add this as a gesture-test block.

## TASK 3. «Таблицы типовых частот»: each table in its own SUB-TAB

Rework `eta\ui\kb_window.py::MethodTablesTab`: instead of three tables stacked in one scroll area, host a nested `QTabWidget` with three sub-tabs (confirmed names):
1. **«П1.3 – частоты пожаров»** — table «Тип здания/помещения | a₁, м⁻²·год⁻¹».
2. **«П1.4 – при F > 10 000 м²»** — table «Тип здания/помещения | a | b» (fix the caption formula text to a proper `a·F^b` rendering via `math()`; current «Q = a·F·F…·b, точнее a·F^b» is a leftover — make it «Q = a·F^b»).
3. **«П2.1 – условные вероятности воспламенения»** — table «Расход | Среда | Мгновенное | Последующее | С изб. давлением».
Each table fills its sub-tab's full area (stretch columns, per Task 2 per-pixel scrolling). Sub-tab bar: same flat style as the main tab bar, `outline: none` (no dotted focus), compact paddings. Keep the read-only nature. QA: regenerate and vision-review `qa_kb_tables.png` (now a sub-tab shot — capture sub-tab 1 and one more).

## TASK 4. «Шаблоны оборудования» TAB DESIGN

Two defects (screenshot 4):
1. **Empty badge (arrow 1):** the `hint` QLabel#targetBadge renders as an empty rounded pill when no Участок/Наружная установка is selected. Fix: hide the label entirely when there is no text (`hint.setVisible(bool(hint.text()))` in `set_owner_available` and after every update). The badge appears ONLY with an active selection showing «Цель: <имя>».
2. **Card selection styling (arrow 2):** clicking a template card gives no visual selection. Implement: on `_on_card` set the dynamic property `selected=true` on the clicked `QFrame#kbCard` and `false` on all others, then `style().unpolish(w)/polish(w)` (or `setAttribute(Qt.WA_StyledBackground)` + repolish loop) so the state applies live. Add QSS in `theme.py`: `QFrame#kbCard { border: 1px solid BORDER; border-radius: 8px; background: PANEL_BG; }`, `QFrame#kbCard:hover { border-color: #94A3B8; background: #F8FAFC; }`, `QFrame#kbCard[selected="true"] { border: 1px solid ACCENT; border-left: 3px solid ACCENT; background: #EFF6FF; }`. Also mark the card of the current `selected_id` on `rebuild_cards` (selection survives search filtering). Overall pass over the tab: consistent paddings, no clipped texts, details pane keeps working.

## TASK 5. «СОСТАВ ШАБЛОНА» DETAILS PANE — all text bold

Screenshot 5 shows the details pane («СОСТАВ ШАБЛОНА», right side of the templates tab) rendering EVERYTHING bold — heading, scenario line, and every bullet — while the code only wraps the title in `<b>`. Diagnose and fix: likely cause is a `QLabel` rich-text parse quirk (the `<b>` tag interacting with the following plain lines or with `setTextFormat`) or an inherited bold font. Reproduce offscreen (select any template, grab the label, check `font().bold()`/`label.text()`), fix so that ONLY the template title line is bold; «Разновидности ГС:»/«Разновидности ИЗ:» may stay semibold as section labels (explicit `<b>` or `<span style="font-weight:600">`), bullets normal weight. Vision-verify on a regenerated `qa_kb_templates.png` shot with a selected card.

## 12. STARTER AMBIGUITIES (extend per task freely — locked items marked LOCKED)

1. (LOCKED) Notes rewrite persists into KB data; reference numbers only from existing sources → `literature\` → omit.
2. (LOCKED) «Резервирование противоаварийной защиты» + «по схеме резервирования» with the two scheme explanations.
3. (LOCKED) SIL/PFD as «термин (ABBR)».
4. (LOCKED) Sub-tab names as in Task 3.
5. (Open, minor) If during the data rewrite a modifier's semantic value (k, p_success, ranges) looks wrong for its new normative wording — do NOT change numeric values silently; collect a question list (Russian) and confirm.

## 13. FINAL DELIVERABLES

1. Questions asked per task BEFORE its implementation where genuinely ambiguous (§0); locked decisions not re-asked.
2. All five tasks implemented; `smoke_test.py` + `gesture_test.py` green (assertions updated for renamed strings and new behaviors — add the per-pixel scrolling block from Task 2); `run_qa.cmd` regenerated and vision-reviewed (kb tabs especially).
3. Version → **6.1.0**; KB `meta.version` → **«6.1»**; README «База знаний (v6.x)» section updated if wording changed materially.
4. `old prompts (done prompts)\REPORT_SESSION_11.md` (English): per-task summary, files touched, the exact before→after strings for every rewritten `property_modifiers` field, scrolling verification evidence, test results, screenshot references, known issues.

## 14. KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only (§1); never pwsh string cmdlets; delete scripts after use; no em-dash anywhere.
- Modal dialogs block offscreen tests (`QMessageBox.exec`, `QDialog.exec`): use testable seams (`_ask_close_guard`, `_confirm_delete`, patched `exec` capture) — extend, don't break.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`).
- PySide6 GC: app-level filters/animations keep strong module-level refs (`scroll.py::_ACTIVE_FILTER`, the `_smooth` dict on the filter).
- Offscreen: `QT_QPA_FONTDIR=C:\Windows\Fonts` mandatory; `FT_New_Face failed…` and «plugin does not support raise()/propagateSizeHints()» are harmless stderr noise; long runs as background jobs with `python -u`; never leave a modal open in a test.
- `QPdfWriter`: one QPainter per document, new pages ONLY via `newPage()` (repeated begin/end silently drops pages).
- QLabel has no `setTextWidth` (that is QTextDocument) — use `setFixedWidth` or explicit `<br>` from `math_html_lines`.
- Feeding raw HTML into `math()` escapes it — `math()` takes the project mini-notation (`F_зд`, `N_у.м`, `λ_DU`), not `<sub>` tags.
- QSS `outline: none` everywhere needed (tabs, lists, tables) — the customer rejects dotted focus rectangles anywhere.
- Table row heights with QLabel cell widgets: compute manually (`_apply_row_heights` pattern); `resizeRowsToContents` knows nothing about cell widgets.
- Vision QA reads downscaled images — for pixel-truth (subscripts, focus rings) crop and 2× upscale before asking glm-5.3-flash.
