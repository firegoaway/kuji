# PROMPT: Kuji – Session 10. Switch controls, FULL PARADIGM REWORK of the event-tree calculation into 5 base scenario types (node-class model), hierarchy cleanup, KB rework, «Логическое дерево событий» terminology, export report, compact small-tree layout

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` — do NOT rename it) — a constructor of logic event trees per Order of the Ministry of Emergency Measures of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–9 are done (v5.0.0). Read before starting:
`old prompts (done prompts)\REPORT_SESSION_9.md` (left wing with И/ИЛИ/НЕ, ghost scenarios, formula frequencies, bezier edges, modern tooltips, icon palette, format 4) and, for deeper history, `REPORT_SESSION_5.md`…`REPORT_SESSION_8.md`. Everything described there works and is covered by tests — do not break it without need. Session 10 is another MAJOR paradigm change: the user states the event-tree calculation algorithm is broken/overcomplicated and must be simplified to a minimum of actions.

---

## 0. QUESTIONS PROTOCOL (HARD GATE — read before writing any code)

**Principle #1 from the user: «Better to ask 10 times than to mess up once.»**

1. Questions are asked **incrementally, per task, as work progresses** — NOT as one giant upfront list. When you are about to start a task (or a risky part of it) and you meet an ambiguity, double meaning, or a statement not associated with a concrete object/screen — STOP that task, formulate a SHORT numbered list of questions about exactly that task, send it, and WAIT for answers. Do not implement that task on assumptions.
2. **Task 1 has a mandatory comprehension gate**: read the two reference documents (§1) from beginning to end FIRST, then send your questions about the calculation paradigm BEFORE touching the model/KB. Task 1 is the mathematical core of the application; everything else depends on it.
3. While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items (e.g. Task 0 switch controls behind a flag, Task 4 terminology sweep) — but nothing that changes the model semantics, KB structure, or file formats.
4. A starter list of known ambiguities is given in §12 — extend it per task, don't limit yourself to it.

## 0b. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report — in English.
- **Application UI language: RUSSIAN** — unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menus, messages, badges, node titles, statuses) must be in Russian.
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- UI terminology: this session REPLACES the term «галстук-бабочка» with **«Логическое дерево событий»** everywhere (Task 4). Keep the established vocabulary otherwise: «Ключевое / инициирующее событие», «Причины отказов», «Промежуточные события», «Конечный сценарий», «Сценарий N», «База знаний», «логический элемент И/ИЛИ/НЕ», «пин „ДА/НЕТ“». The words «гейт» must NOT appear as a UI term; fire-automation systems (АПС/СОУЭ/СПДЗ/АУПТ) stay excluded everywhere. In normative citations inside tooltips, «барьер безопасности» is acceptable.
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README. Never «—» (em dash).

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` — Python 3.14.3, PySide6 6.12.0 (QtSvg, QtPdf available) |
| Entry point | `main.py`; launcher `run_app.cmd` |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (sets `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:\Windows\Fonts`); artifacts land in `qa_artifacts\` (`qa_window.png`, `qa_canvas.png`, `qa_matrix.png`, `qa_docview.png`, `qa_sheet.png`, `qa_export_a3.pdf`, `qa_icons_palette.png`, `qa_tooltip_modern.png`, `qa_stats.json`, pedal tooltip proofs `qa_paz_tooltip.png` etc.) |
| Core tests | `smoke_test.py` (29 OK blocks), `gesture_test.py` (32 scenarios, offscreen, ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` — sections: meta, echelons, fta_gates (И/ИЛИ/НЕ), initiating_events, barrier_events, cause_events, cause_notes, pending_events, value_library, presets, property_modifiers, equipment_library; `meta.version` = «5.0» |
| App version | `eta\__init__.py` → `__version__ = "5.0.0"` — this session bumps to **6.0.0** (major paradigm change); status bar shows it via `main_window.py` |
| Session reports | write `old prompts (done prompts)\REPORT_SESSION_10.md` (English) at the end |
| In-project reference docs | `literature\Методика_533_RAG_final.md`, `literature\2 ГОСТ 12.1.004-91_distil.md`, `literature\БЗ_отказы_оборудования_и_антагонисты.md` |
| **NEW external reference docs (Task 1 — MANDATORY, read fully, от и до)** | `D:\WorkD\FIREGOAWAY\GitHub\HermesRAG\Расчет частот возникновения пожара\БАЗА ЗНАНИЙ\1 Методология расчета частот возникновения пожара для нужд Методики 533.md` and `D:\WorkD\FIREGOAWAY\GitHub\HermesRAG\Расчет частот возникновения пожара\БАЗА ЗНАНИЙ\ДЛЯ ОТЛАДКИ\Пример расчёта частов возникновения пожара для кондитерского цеха.md` (exact folder: `…\БАЗА ЗНАНИЙ\ДЛЯ ОТЛАДКИ\Пример расчёта частот для кондитерского цеха.md`) |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` or explicit utf-8 `io.open` round-trip with verification (`json.loads` before and after, unique anchor line, length delta check, no em-dash), delete the script afterwards. Inline `python -c` in pwsh also breaks on quotes — write a file. |

**Warning about the worked example:** the confectionery-shop document contains typos and copy-paste errors — e.g. in the final scenario-frequency formula the symbol written is `Q_ИЗ` while the value is actually taken from `Q_П`, and there are other similar slips. The document is a DEBUG DRAFT: extract the CONCEPT and the calculation motive, not the literal symbols. Cross-check numbers against `1 Методология расчета частот возникновения пожара для нужд Методики 533.md` and the Методика № 533 tables (П1.x, П2.x).

## 2. STATE AFTER SESSION 9 (v5.0.0) — what exists, all tested

- **Left wing = free-form causal chain** (`eta\core\model.py`): antecedent `FtaNode`s (kind «cause», own `children` = their antecedents, `combine` И/ИЛИ/НЕ + `combine_p` P_усл live ON the node); ETA `Node.left: list[FtaNode]` + `left_combine`. Phase machinery (ГС/ИЗ slots, `FtaSide`) is deleted. APIs: `add_antecedent/move_antecedent/remove_antecedent`, `set_combine/cycle_combine/set_combine_p`, `combine_allowed`, `next_combine` (И→ИЛИ→НЕ→И; НЕ only with exactly 1 input).
- **Branch math**: `_branches_of` (И = cartesian product, cap 8; ИЛИ = concatenation — each «self-sufficient» initial branch is its own scenario; НЕ = inhibitor `Q·(1−P_усл)`, prob input → `1−P`). Visible tree flows along branch 1; extra branches become **ghost terminals** «Сценарий N+k» (dashed, no arrows, under the real terminal; linear Q rescale). `fta_center_q` = union (Σ for frequencies > 1 год⁻¹).
- **Serialization format 4** (`eta\core\serializer.py`): `left`/`left_combine` on the root; migration of formats 1–3 («fta» phases → antecedent chains, conjunction preserved); lightning `q_init=6` migrates to formula mode.
- **Formula frequencies** (`eta\core\formulas.py` + `formula_spec` in KB `c-iz-lightning`): `N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶`, `Q = N_у.м·(1−η)`; area mode `N_у.м = F_тер·n_у`; territory property `strike_area_km2` with км²↔м² switcher; inspector `_append_formula_editor` (variables editable, Q read-only).
- **Layout** (`eta\core\layout.py`): antecedents in echelon columns by KB `level`; `BadgeGeo` logic badges near first input arrow (И/НЕ above, ИЛИ in-line; grey lock at 1 input); ghost NodeGeos; pin masks (`pins_left/right` — terminal has no right pins, initial antecedent no left pins); **bezier edges** (`EdgeGeo.c1/c2`, horizontal tangents at pins, fan-out 12 px, straight 2-point continuations, `sample_points()` 16-seg sampling for the collision audit).
- **Canvas** (`eta\ui\canvas.py`): antecedent picker from left pins (causes + И/ИЛИ/НЕ), drag-reparent from antecedent right pin (`check_move`), double-click badge cycling, insertion above terminal via PARENT's right pin, context menus with icons, domino links bezier.
- **Modern tooltips** (`eta\ui\modern_tooltip.py`): installed in `main.py`; system QToolTip suppressed; canvas routed via `scene_tip`/`hide_scene_tip` (the only `QToolTip.showText` in the repo is the adapter fallback); dark panel, header/formula/source line classification, dwell 400 ms, offscreen/`KUJI_NO_ANIMATION` instant seam.
- **Icons** (`eta\ui\icons.py` + `ICON_PALETTE` in `theme.py`): per-glyph colors, stroke 2.2, 22/24 px, active = lightened own color; `qa_icons_palette.png` swatch.
- **Terminology**: UI says «Левое крыло», «Причины отказов», GOST labels; «педальки»/«барьеры» are not user-visible; caption `theme.PEDALS_CAPTION = "ЗАЩИТНЫЕ МЕРЫ И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ"`.
- Equipment may sit under Room/Area (normal) or directly under Territory (session-9 «outdoor installation», `props.is_outdoor`) — **superseded by Task 2 this session**.
- One «Применить на холсте» button in KB «Библиотека типовых сценариев → По оборудованию» with selection-based logic (`main_window._apply_library_equipment`) — **reworked by Task 3**.

## 3. CODE MAP (v5.0.0; extend, don't break)

- `main.py` — entry: `QApplication`, global `QSS`, `install_scroll_wide`, `install_modern_tooltips`, `MainWindow(kb)`.
- `eta\core\model.py` — `TreeModel` (see §2). ETA side unchanged: `add_split` (barrier insert / physical split / scenario terminal `add_scenario_split`), `scenarios()` (now incl. ghost rows with `"ghost": True`), `safe_termination_summary`, threshold, `_retag_subtree`.
- `eta\core\formulas.py` — formula registry (currently `lightning` only).
- `eta\core\objects.py` — hierarchy kinds: territory/building/compartment/room/area/equipment (`PARENT_RULES`, `KIND_TITLES`, `DEFAULT_PROPS`, `alloc_scenario_title`); territory has `strike_area_km2`. **Task 2 reworks this.**
- `eta\core\generator.py` — `generate_equipment_chain` (minimal scenario mode + pedal barriers), `paz_pfd`, `vent_residual_p`, `lightning_*`, `apply_lightning_protection` (formula-aware).
- `eta\core\validation.py` — rewritten in session 9: left-wing rules (target = root/antecedent only; duplicate per path; cycles; `check_gate_set` НЕ=1 input) + right-wing `check_barrier` (stage monotonicity, tags). **Task 1 will replace most of this.**
- `eta\core\layout.py` — `compute_layout` (compaction, badges, ghosts, pin masks, bezier, sampled audit) — shared by canvas AND PDF (WYSIWYG is sacred).
- `eta\core\matrix.py` — scenario matrix (rows incl. ghosts; И/ИЛИ/НЕ cause cells; union note). `eta\ui\matrix_view.py` renders it.
- `eta\core\serializer.py` — format 4 + migrations. `eta\core\domino.py` — external fire as ИЛИ antecedent into the center.
- `eta\ui\canvas.py` — `TreeCanvas` (gestures mixin), `NodeItem` (pin masks), `EdgeItem` (sampled shape), `BadgeItem`, domino items, pickers/menus/DnD.
- `eta\ui\render.py` — `draw_node/draw_edge (bezier + tangent arrowhead)/draw_badge` shared by canvas and PDF.
- `eta\ui\inspector_panel.py` — node/edge forms; `_append_combine_editor` (И/ИЛИ/НЕ + P_усл); `_append_formula_editor`; `_props_form` (pedal checkboxes via `add_pedal` — **Task 0 converts these to switches**; territory F_тер block; building lightning block; **Task 6 removes the inherited-props dump and path line**).
- `eta\ui\kb_window.py` — «База знаний» window; `EquipmentLibraryTab` (list + props form + pedal checkboxes + single `btn_apply` «Применить на холсте»); `PresetsTab`; pending tab; close guard.
- `eta\ui\hierarchy_panel.py` — horizontal toolbar (6 glyph buttons incl. «Добавить ключевое/инициирующее событие» active at Room/Area), F2 rename, DnD domino marker, `InitPickerDialog`. **Tasks 2–3 rework this.**
- `eta\ui\event_picker.py` — `EventPickerPopup` (search + funnel filter pedals — Task 0 converts filter pedals to switches too).
- `eta\ui\theme.py` — palette, `ICON_PALETTE`, sizes/strokes, pin geometry, `PEDALS_CAPTION`, math re-exports, global `QSS` (incl. legacy `QToolTip` fallback block).
- `eta\export\pdf_export.py` — vector A3/A2 from doc_scene; matrix sheets `_draw_matrix_sheets` (fixed column widths — **Task 5 reworks scaling/report**).
- Tests: `smoke_test.py` (29 blocks), `gesture_test.py` (32 scenarios). Both will need LARGE rewrites for the new paradigm — rewrite the affected blocks as you go, keep suites green after every task.

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py`; any visual change must go through both automatically — never fork geometry.
2. KB JSON edits are data edits via byte-safe Python scripts only (§1); UI terminology changes must not rename internal ids/keys (`pedals`, `sil`, `b-*`, `pm-*`, `c-*`, `eq-lib-*`…) unless a task explicitly says so; Task 1 DOES rebuild most KB sections — design the new schema explicitly, keep backward loading or provide migration (ask the user which, §12).
3. No new external dependencies; PySide6-native only (custom switch = QPainter/QWidget or QAbstractButton subclass — no QtQuick).
4. Style: flat Swiss-utilitarian base with the two session-9 amendments (colorful glyphs, dark animated tooltips) — new switch control must live in `theme.py`/one module, QSS-driven, no ad-hoc colors.
5. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) and keep them green; update assertions; add regression tests per task. Run `run_qa.cmd` and visually review regenerated artifacts before declaring the task done (glm-5.3-flash vision passes, ≤4 iterations, with context specs). Animations must not break offscreen tests (instant seams already exist).
6. Manual smoke with `run_app.cmd` is the user's habit — the app must start cleanly.
7. Keep working features working unless a task explicitly removes them (Task 1 removes a lot — enumerate removals in the report).

---

## TASK 0. DESIGN: replace checkboxes with short switches (toggle controls)

**Problem.** All boolean options today are `QCheckBox`es: the protective-measures pedals in the object properties form (`inspector_panel.py::add_pedal`), the same pedals in the KB equipment form (`kb_window.py` EquipmentLibraryTab), and the filter «pedals» in `EventPickerPopup`. The user wants compact, beautiful **switches** (iOS/Android-style toggles), and **everything that only makes sense when a checkbox is ON must be HIDDEN when it is OFF** (conditional fields, e.g. «Категория защиты» appears only when «Молниезащита здания» is on — see Task 1 for the lightning case; «Кратность воздухообмена A» only when ventilation is on — this already exists, keep the pattern and extend it everywhere).

**Requirements.**
1. New reusable widget (e.g. `eta\ui\switch.py`): a short horizontal switch ~28–34 px wide, flat Swiss style, ACCENT track when on, neutral border track when off, white knob, subtle 120–150 ms slide (instant under offscreen/`KUJI_NO_ANIMATION`). API compatible with `QCheckBox` usage sites: `toggled(bool)` signal, `isChecked()/setChecked()`, `setToolTip()`. Consider subclassing `QAbstractButton` so `findChildren()` patterns in tests keep working, or keep a thin compatibility wrapper; update tests accordingly.
2. Replace: all `add_pedal` checkboxes (inspector + KB equipment form), the ventilation A-field visibility owner, lightning block controls, `EventPickerPopup` filter pedals, and any other `QCheckBox` that acts as a boolean toggle in the properties/filter UI. Checkboxes inside dialogs with plain yes/no semantics (e.g. record editors) may stay — ask if in doubt.
3. Conditional visibility rule (binding): fields that only apply when a switch is ON must be shown/hidden live with the switch state. Audit every pedal-driven field; make the mapping data-driven where possible (a small registry `{pedal_key: [field_names]}`).
4. Internal keys (`pedals` dict) stay unchanged — display-layer only.
5. Tests: gesture assertions referencing `QCheckBox`/`pedal_boxes` updated; add a visibility-toggle regression (switch off → dependent field hidden). QA screenshots reviewed.

## TASK 1. FULL REWORK of the event-tree calculation: 5 base scenario types, node-class model (THE CORE — questions gate FIRST)

**User's verdict: the current ETA algorithm is broken/overcomplicated; simplify to a MINIMUM of user actions.** The new paradigm: the user does NOT place individual events on the canvas. The canvas hosts a fixed set of NODE CLASSES per scenario type; concrete event varieties are chosen in the object properties panel (right side) from dropdowns. The knowledge base is «nerfed» (collapsed) to exactly five base scenario types:

1. Сценарий пожара ТГМ (твердые горючие материалы)
2. Сценарий пожара/взрыва ГГ (горючие газы)
3. Сценарий пожара/взрыва ГЖ (горючие жидкости)
4. Сценарий пожара/взрыва ЛВЖ (легковоспламеняющиеся жидкости)
5. Сценарий пожара/взрыва Пыли

Everything else in the KB (other categories, equipment-specific chains, presets not matching these five) is DELETED.

**Step 1 (mandatory): read both reference documents from §1 end-to-end.** Extract: the calculation concept per scenario type, the classification of fire/explosion types for gases/liquids/dusts per Методика № 533 (дефлаграция, детонация, взрывное горение и т.д. — by which attributes the classification is built), the worked ТГМ example's number flow, and the role of object properties (areas, lightning protection). Mind the typos (e.g. `Q_ИЗ` written where `Q_П` is used). Then send your questions (§0) and WAIT.

**Step 2 — the node model.** For EACH of the five scenario types the canvas offers exactly these node classes (the user picks a NODE OF A CLASS, not an event):

- **Нода «Наличие <вещества>»** (ТГМ / ГГ / ГЖ / ЛВЖ / Пыль) — presence node. Single property for now (delete all other properties of this node): «время присутствия» OR «частота присутствия» — the user chooses which mode via a dropdown in the properties panel; default value = 1. (Ask: «время присутствия» unit semantics — hours/year? fraction of time? per the methodology doc.)
- **Нода «Наличие окислителя (ОК)»** — same single property (время/частота присутствия via dropdown), default = 1. One property only.
- **Нода «Образование горючей среды (ГС)»** — class node; in the properties panel the user selects the concrete event VARIETY from a dropdown: the list of key/initiating events that lead ONLY to the appearance of ГС (разгерметизация и т.п. — i.e. the KB's release-type initiating events).
- **Нода «Появление источника зажигания (ИЗ)»** — same, dropdown of events leading ONLY to ИЗ appearance (удары молнии, статическое электричество, всевозможные отказы и т.п.).
- **Нода «Возникновение пожара»** — aggregates: sums the frequencies of ALL scenarios formed by all initial events. The principle «сколько начальных событий, столько и сценариев» is preserved, plus GROUPING with frequency summation:
  - ТГМ: only one fire type (пожар по поверхности) → number of scenarios = number of initial events.
  - ГГ (and ЛВЖ/ГЖ/Пыль): several fire/explosion types exist (дефлаграция, детонация, взрывное горение и пр. — take the exact classification from Методика № 533 / the methodology doc) → the final scenario count depends on BOTH the number of initial events AND the number of key event varieties.
  - **Speed/flow categories (1–50 кг/с и т.д.) are NO LONGER user choices — remove them.** Each burning rate is a PROPERTY of the «Возникновение пожара» node, shown ONLY there, and rendered as node text lines, e.g.:
    «Разгерметизация 12.5 мм – скорость сгорания <1 кг/с»
    «Разгерметизация 12.5 мм – скорость сгорания 1–50 кг/с» …
  - The program must NOT check physical plausibility (whether a 12.5 mm hole can give 300 kg/s) — it checks only the MATHEMATICAL EXISTENCE of the possibility of such a scenario (the combinatorics produces the line; the ENGINEER validates the physical scenario in another program).
  - ALL apparatus/object properties that influence the calculation (territory area, building/area attributes, apparatus parameters) are attached to the «Возникновение пожара» node and accounted for THERE. Building lightning protection («Молниезащита здания» + «Категория защиты» dropdown which appears ONLY when the switch is on) is accounted for in the «Возникновение пожара» node calculation and ONLY there.

**Transition states of substances are NOT considered.** The program does not model ТГМ → взрывоопасная пылевая взвесь transitions; the engineer/user knows this and adds a SEPARATE dust scenario for the same area/installation if needed.

**No free placement of начальные/ключевые/инициирующие события on the canvas — they live inside the nodes (dropdowns).** The full node list is above; NO other nodes exist. Rework the «Библиотека типовых сценариев» and the whole База Знаний to this paradigm (five types, their event-variety dropdown sources, the rate properties of «Возникновение пожара»).

**Model/KB/format consequences (design explicitly, ask before doing):** how the session-9 left wing/combiners/ghosts map onto the new chain Наличие→ГС/ИЗ→Возникновение пожара (the И/ИЛИ/НЕ machinery may reduce to the fixed structure above — propose what survives); new serialization format 5 + migration or a clean break for session-9 projects; what happens to `smoke`/`gesture` blocks tied to the old paradigm (rewrite); what remains of domino, matrix, PDF; whether «Сценарий N» terminals remain as the grouping output. The old И/ИЛИ/НЕ badges may become unnecessary — ask.

## TASK 2. HIERARCHY: no apparatus in the tree; new kind «Наружная установка»

The left hierarchy window must contain ONLY: Территория, Здание, Пожарный отсек, Помещение, Участок — plus a NEW kind **«Наружная установка»**, child of Территория, on the SAME level as Здание. No equipment/apparatus items in the tree. The toolbar buttons and `PARENT_RULES`/`KIND_TITLES` in `eta\core\objects.py` change accordingly (this supersedes session-9's «equipment under territory with `is_outdoor`» — make «Наружная установка» a first-class container kind). Where do scenario trees attach now — to Участок, Помещение, and Наружная установка directly? What happens to `alloc_scenario_title` numbering when an installation is deleted? Ask (§12).

## TASK 3. NO scenario creation directly from the KB

Remove the flows that spawn trees straight from the knowledge base window regardless of selection. The only flow: the user builds Территория → Здание → Помещение → Участок (or Наружная установка), then WITH AN УЧАСТОК (or installation) SELECTED either double-clicks LMB an apparatus record in the KB («Библиотека типовых сценариев» equipment list) or selects it and presses «Применить на холсте» — this spawns the template event tree per Task 1's лекала. Enforce the selection precondition with a clear Russian tooltip otherwise. Update `main_window._apply_library_equipment`, `kb_window.EquipmentLibraryTab`, hierarchy button set, and tests (gesture scenarios 21/25/32).

## TASK 4. TERMINOLOGY: remove «галстук-бабочка» everywhere

The concept is no longer a bow-tie — the single term is **«Логическое дерево событий»**. Sweep the WHOLE repo: UI strings, PDF headers/legends (`pdf_export.py` header «Гибридное дерево «галстук-бабочка» (FTA + ETA)»), docstrings, README, test assertions, `qa` context specs. Keep internal identifiers (class names like `TreeModel`, file names) unless trivially safe to rename — display layer first; ask if a rename of e.g. PDF titles/footers wording should also drop «FTA + ETA».

## TASK 5. EXPORT: matrix must fill the page width; add a textual report sheet

**Problem.** For small trees the landscape export's matrix sheet shows a tiny matrix crammed in a corner with ~80 % of the page empty. Fix in `eta\export\pdf_export.py::_draw_matrix_sheets`: when the tree/matrix is small, scale the matrix to AT LEAST the full usable page WIDTH (columns stretch, font may grow up to a sane cap), and place the main textual conclusions BELOW it.

Design a standard report sheet for matrices and trees drawing on `1 Методология расчета частот возникновения пожара для нужд Методики 533.md` and `Пример расчёта частот для кондитерского цеха.md` (e.g. per-scenario frequency table with sources, initial/key event varieties, rate properties, the grouping formula `Q_возник = Σ Q_сценариев`, invariant lines, object parameters used — territory area, lightning protection level/η, etc.). Propose the report layout to the user as a question before implementing (it is a deliverable document, taste matters). Both matrix and schematic modes must benefit; WYSIWYG rules apply.

## TASK 6. PROPERTIES PANEL CLEANUP

In the object properties window (right panel, `inspector_panel.py::show_object_context`):
1. Remove the raw dump lines like `pedals = {}` (they come from the «УНАСЛЕДОВАННЫЕ СВОЙСТВА» block printing raw keys/values).
2. Remove the «Путь: Территория → Здание → …» line entirely.
3. Remove the whole «УНАСЛЕДОВАННЫЕ СВОЙСТВА» section (inherited properties display) — the user explicitly does not want it.
Effective values still cascade internally (`effective_properties/effective_pedals`) — only the DISPLAY is removed. Update tests that assert these strings.

## TASK 7. LAYOUT: compact canvas for small trees (user screenshot)

**Problem (user's screenshot).** With only 2–3 nodes on the canvas (e.g. the minimal scenario tree [Разгерметизация аппарата…] → [Сценарий 1]) the boxes sit at the extreme left and extreme right of a full-width canvas — an ~80 % empty gap in the middle, crossed by one lonely connector. Root cause: `compute_layout` assigns a full column per echelon level (0…5, `MIN_COL_W = 170` + per-column pitch) even when intermediate levels contain NO nodes, so the terminal in level 5 lands far away from the root in level 0. On the screenshot there are even no echelon headers/grid visible — just the spread boxes.

**Requirements.**
1. Empty-column compaction: echelon columns that contain zero nodes must NOT consume horizontal pitch — collapse them entirely (pack occupied columns tightly) so a 2-node tree occupies a compact region with normal gaps (the session-8 callout-proportional pitch still applies between OCCUPIED columns). The echelon header strip and dotted column grid must stay consistent with the actual drawn columns — decide and ASK (§12): drop headers of empty columns entirely, or keep the full echelon header row for chronology reference while columns themselves are packed?
2. Vertical compaction for small trees: with 2–3 nodes there must be no giant vertical padding either; the tree block stays centered/top-aligned as today but without inflated scene margins.
3. The canvas «fit» behaviors (`fit_tree`, sticky scene-rect) should present the compact tree at a readable zoom, not a tiny cluster lost in white — verify the initial view after spawning a minimal scenario tree.
4. WYSIWYG preserved: canvas and PDF use the same packed layout (`compute_layout`); the PDF row/column tiling logic (`pdf_export._make_tiles`, `row_cuts`) must be re-checked against collapsed columns.
5. Straight 2-point continuation edges, pin endpoints, badges, ghosts — all session-8/9 invariants must survive compaction; the collision audit stays clean.
6. Tests: add a smoke block — build minimal trees of 2 and 3 nodes; assert occupied-column pitch is compact (e.g. `col[i+1].x - col[i].x ≤ node_w + max_gap`, no column with zero nodes between occupied ones unless explicitly kept for headers), scene width is within a sane bound vs. node count, audit clean; update the compaction block's gap assertions. QA: regenerate and visually review a minimal-tree screenshot (add one to `visual_qa_runner.py` if missing).

---

## 12. STARTER AMBIGUITIES (ask per task, as you reach it — extend freely)

1. (T1) «Время присутствия» vs «частота присутствия»: units and formulas for each mode (per the methodology doc)? Is «default = 1» a probability 1 (always present)?
2. (T1) The exact fire/explosion classification per substance type from Методика № 533 (газ: дефлаграция/детонация/взрывное горение…? liquid? dust?) — confirm the list you extracted from the docs before wiring scenario counts.
3. (T1) Scenario math confirmation: is `Q_сценария = Q_наличие_вещества · Q_ОК · Q_ГС-разновидность · Q_ИЗ-разновидность · (rate/тип пожара factor)` per line, and «Возникновение пожара» = Σ over all lines? (Mirrors the confectionery example's Q_П flow — confirm against the doc.)
4. (T1) Do session-9 projects (format 4) migrate to the new model, or is a clean break acceptable? Same for KB: full rewrite of `knowledge_base.json` in place?
5. (T1) Do the И/ИЛИ/НЕ badges/combining UI survive anywhere (e.g. multiple ГС varieties under one ГС node?), or is the structure strictly fixed (one variety per node instance, more varieties = more nodes/scenarios)?
6. (T1) Where do apparatus properties (SIL/PFD/λ_DU, environment category…) attach now — everything on «Возникновение пожара»? Which of them still influence the math at all after the nerf?
7. (T2) What may live under «Наружная установка» — scenario trees directly, or its own «Участок»-like children? May Помещение exist without Здание inside an installation?
8. (T3) When nothing is selected or a non-Участок is selected: disable the KB apply button with tooltip, or show a message on click?
9. (T5) Report sheet layout proposal (columns, which conclusions, invariants, sources) — present a sketch before implementing.
10. (T1/T5) Do domino cascades, matrix view, and hidden-share invariants survive the paradigm change in their current form?
11. (T7) When intermediate echelon columns are empty: drop their headers/grid entirely, or keep the full echelon header strip for chronology reference while the columns themselves are packed?

## 13. FINAL DELIVERABLES

1. Questions asked and answered per task BEFORE its implementation (§0).
2. All seven tasks implemented; `smoke_test.py` + `gesture_test.py` green (blocks/scenarios rewritten for the new paradigm as needed); `run_qa.cmd` regenerated and visually reviewed.
3. Version → **6.0.0**; KB `meta.version` bumped; README rewritten for the new paradigm.
4. `old prompts (done prompts)\REPORT_SESSION_10.md` in English: per-task summary, files touched, the new calculation math (with formulas and sources from the two reference docs), KB schema before/after, migration decisions, test results, screenshot references, known issues.

## 14. KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only (see §1); never pwsh string cmdlets; delete scripts after use.
- Modal dialogs block offscreen tests (`QMessageBox.exec`, `QDialog.exec`): use testable seams (`_ask_close_guard`, `_ask_rename`, `_confirm_for`, picker monkeypatching) — extend that pattern to any new dialogs.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`) — HKCU writes are denied in the sandbox.
- PySide6 GC: app-level event filters must hold a strong module-level reference (`scroll.py::_ACTIVE_FILTER`, `modern_tooltip.py::_ACTIVE`).
- Offscreen: `QT_QPA_FONTDIR=C:\Windows\Fonts` mandatory; `FT_New_Face failed...` and «plugin does not support raise()/propagateSizeHints()/setting window opacity» are harmless stderr noise; long runs: background jobs with unbuffered output (`python -u`), never leave a modal open in a test.
- Do NOT launch `run_app.cmd` inside automated batches (it opens the GUI and blocks the job) — the user runs it manually.
- Tooltip content assertions compare against `<br>`-flattened text (soft-wrap may split phrases).
- Style rule: short dash «–» only; tests assert no «—» in the KB JSON.
- Inline `python -c` in pwsh breaks on quotes — always write a script file.
- Badge/tooltip: Qt rich text does NOT support `border-left` on spans — formula strips use `background-color`.
