# PROMPT: Kuji – Session 9. Modern animated tooltips, icon redesign, free-form bow-tie left wing (И/ИЛИ/НЕ logic nodes), live formula inputs, bezier edges

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` — do NOT rename it) — a constructor of hybrid bow-tie logic trees (FTA + ETA) per Order of the Ministry of Emergency Measures of Russia № 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–8 are done (v4.2.0). Read before starting:
`old prompts (done prompts)\6 next-session-prompt.md` (sections 0–5: code map, style rules, pitfalls), `7 next-session-prompt.md` (KB enrichment), `8 next-session-prompt.md` (math renderer, compaction, pins, KB close guard), and `REPORT_SESSION_*.md` (especially REPORT_SESSION_8.md). Everything described there works and is covered by tests — do not break it without need.

---

## 0. QUESTIONS-FIRST PROTOCOL (HARD GATE — read before writing any code)

**Principle #1 from the user: «Better to ask 10 times than to mess up once.»**

1. After reading this prompt and the referenced reports, compile a **numbered list of clarifying questions** covering every point you find ambiguous, doubly-meaning, or missing an association with a concrete object/screen.
2. Send the list to the user and **WAIT for answers** before implementing. Do not start coding Task 3 (the tree algorithm rework) on assumptions — it is the mathematical core of the application.
3. Small, mechanical, low-risk items (icon resizing, tooltip widget skeleton behind a flag) may proceed in parallel while waiting, but nothing that changes the model, KB semantics, or file formats.
4. A starter list of known ambiguities is given in §10 of this prompt — extend it, don't limit yourself to it.

## 0b. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report — in English.
- **Application UI language: RUSSIAN** — unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menus, messages, badges, statuses) must be in Russian.
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- UI terminology follows the established vocabulary: «Ключевое / инициирующее событие» (center), «Причины отказов» (left-wing antecedent events), «Промежуточные события» (right wing), «Конечный сценарий» / «Сценарий N», «База знаний», «логический элемент И/ИЛИ/НЕ». The words «гейт» must NOT appear as a UI term; fire-automation systems (АПС/СОУЭ/СПДЗ/АУПТ) stay excluded everywhere. Port/pin vocabulary: «пин „ДА/НЕТ“». In normative citations inside tooltips, «барьер безопасности» is acceptable (already used in the KB `tooltip` texts).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README. Never «—» (em dash).

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` — Python 3.14.3, PySide6 6.12.0 (QtSvg, QtPdf available) |
| Entry point | `main.py`; launcher `run_app.cmd` |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (sets `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:\Windows\Fonts`); artifacts land in `qa_artifacts\` (`qa_window.png` — main window + doc pop-out + KB window on «По оборудованию», `qa_kb_pending.png`, `qa_canvas.png`, `qa_matrix.png`, `qa_docview.png`, `qa_sheet.png`, `qa_export_a3.pdf`, `qa_stats.json`; session-8 tooltip proofs: `qa_paz_tooltip.png`, `qa_vent_tooltip.png`, `qa_vibro_tooltip.png`, `qa_wear_tooltip.png`) |
| Core tests | `smoke_test.py` (core math/layout invariants; 27 OK blocks), `gesture_test.py` (full UI acceptance, offscreen, ends with `GESTURES PASSED`; 31 scenarios) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` — sections: meta, echelons, fta_gates, initiating_events, barrier_events, cause_events, cause_notes, pending_events, value_library, presets, property_modifiers, equipment_library |
| App version | `eta\__init__.py` → `__version__ = "4.2.0"` — this session bumps to **5.0.0** (major change of the tree-building model); status bar shows it via `main_window.py` |
| Session reports | write `old prompts (done prompts)\REPORT_SESSION_9.md` (English) at the end |
| Reference docs | `literature\Методика_533_RAG_final.md`, `literature\2 ГОСТ 12.1.004-91_distil.md`, `literature\БЗ_отказы_оборудования_и_антагонисты.md` |
| KB-JSON editing rule | NEVER edit `knowledge_base.json` via pwsh `Get-Content/Set-Content/-replace` (PowerShell corrupts Cyrillic). Mass edits: temporary Python script over `read_bytes()/write_bytes()` or explicit utf-8 `io.open` round-trip with verification (`json.loads` before and after, unique anchor line, length delta check), delete the script afterwards. Inline `python -c` in pwsh also breaks on quotes — write a file. |

## 2. STATE AFTER SESSION 8 (v4.2.0) — what already exists, all tested

- **Math renderer** `eta\ui\math_text.py`: mini-notation (Greek macros, `_{…}`, `^…`, Cyrillic subscripts `T_тест`, `\cdot`, `\approx`, literal fallback for unknown macros) with two backends: `math()` → `<sub>/<sup>` HTML for labels/tooltips; `paint_math()/math_size()/math_height()/math_wrap()` for canvas+PDF (scripts at ×0.65 size, ±0.35 em baseline shift). `math_html_lines(text, wrap_chars=88)` renders multi-line hints with soft wrap. Re-exported via `eta\ui\theme.py` (single entry point).
- **Long KB tooltips**: `property_modifiers` records may carry a `"tooltip"` field (full Russian explanations); `pm-sil`, `pm-venting`, `pm-vibro`, `pm-wear` have them. `inspector_panel.pedal_tip()` and the `kb_window` pedal tooltip prefer `mod["tooltip"]` (fallback: title–formula–source); checkboxes set `toolTipDuration(60_000)`.
- **Layout compaction** (`eta\core\layout.py`): callout-proportional column pitch (`PAD_COL=10`, floor 48; `HGAP=176` kept for FTA columns), effective-column contour packing (`eff_col(child) = max(level, parent's)`, diagonal stacking of same-column chain links, `DY_MIN=30`), «ДА» branch always above «НЕТ», straight 2-point edges for single-child continuations (`STRAIGHT_SNAP=4`), uniform per-column trunk corridor for same-column stacks, final collision audit (`Layout.collisions`, empty on clean trees; deterministic push-apart for manual nodes).
- **Pins**: geometry single-sourced in `theme.py::pin_centers()` (`PIN_Y_TOP=0.32`, `PIN_Y_BOT=0.68`, `PIN_R`, `PIN_HIT_R`); ETA edges start/end exactly on pin circles; unfavorable branch («ДА») leaves the TOP GREEN `right-yes`, favorable («НЕТ») the bottom red; left-pin drags are suppressed with an explanatory tooltip; a scenario-split node's right pin does not offer intermediate events («Узел уже завершается сценарием…»); picker relevance ordering in `canvas.py::_ordered_barriers` (dust continues dust, alien media last).
- **KB unsaved-changes guard**: `KnowledgeBaseWindow.closeEvent` + `_ask_close_guard()` seam («Сохранить / Не сохранять / Отмена»), «Закрыть» button, app-quit routing in `MainWindow.closeEvent`.
- **GOST terminology**: SIL/PFD/λ_DU/T_тест labels, `theme.sil_combo_item()` («SIL 1: PFD 10⁻²…10⁻¹», no `10^` carets), `PEDALS_CAPTION = "ЗАЩИТНЫЕ МЕРЫ И ПОПРАВОЧНЫЕ КОЭФФИЦИЕНТЫ"`.
- **Tag accumulation fixed**: `model._retag_subtree` keeps a node's own incoming tags (children recomputed from them) — `required_parent_tags` chains (e.g. dust-cloud) now accumulate correctly.

## 3. CODE MAP (what lives where; all tested — extend, don't break)

- `main.py` — entry: `QApplication`, global `app.setStyleSheet(QSS)`, `install_scroll_wide`, `MainWindow(kb)`.
- `eta\core\model.py` — `TreeModel`, `Node`/`FtaNode`, `SplitSpec`, `SPLIT_BARRIER/SPLIT_PHYSICAL/SPLIT_SCENARIO`, `GATE_AND/GATE_OR`, `PHASE_GS/PHASE_IZ` + `FtaSide` (the OLD left wing: phase chains, slots −5…−1, `fta_center_q = Q_ГС·Q_ИЗ`), `add_root/add_split/add_fta_phase/add_fta_cause/add_fta_subgate/add_scenario_split/scenario_terminal_of`, `set_split_p`, `_retag_subtree`, `scenarios()`, `safe_termination_summary()`, hidden favorable shares (`is_hidden_safe`), invariant ΣQ_неблаг + ΣQ_скрытых = λ_баз.
- `eta\core\objects.py` — hierarchy Территория→Здание→Пожарный отсек→Помещение→Участок→Оборудование; `alloc_scenario_title()` («Сценарий N», counter survives deletions); `effective_properties/effective_pedals`; area property for per-area frequencies lives on the Участок/Помещение object.
- `eta\core\generator.py` — `generate_equipment_chain()`, `SIL_DEFAULT_PFD`, `voting_pfd`, `pfd_avg`, `vent_residual_p`; **lightning**: `lightning_k_scale`, `apply_lightning_protection`, `lightning_eta` (N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶, η by protection level I–IV per СО 153-34.21.122-2003) — relevant to Task 4.
- `eta\core\layout.py` — `compute_layout(model, kb) -> Layout` (compaction engine, see §2), shared by canvas AND PDF (WYSIWYG is sacred).
- `eta\core\validation.py` — `Validator.check/check_barrier/check_fta/check_center_gate/compatible_barriers/compatible_causes/compatible_subgates`.
- `eta\core\matrix.py` — scenario matrix (ДА/НЕТ/И/ИЛИ cells, invariant note) — rendered in `matrix_view.py` (QLabel summary through `math()`) and the PDF matrix page.
- `eta\core\kb.py` + `knowledge_base.json` — atomic save/reload, `kb_reloaded`; `property_modifiers` records may carry `tooltip`, `formula`, `source`, `ranges`, `k` etc.
- `eta\ui\theme.py` — palette (Swiss base: `ACCENT #2563EB`, `TEXT_PRIMARY #0F172A`, `HAZARD #DC2626`, `SAFE #16A34A`), fonts, size constants, `fmt_prob/fmt_q`, `sil_combo_item`, `pin_centers`, `PEDALS_CAPTION`, math re-exports, global `QSS` (incl. a plain `QToolTip {...}` block — will be superseded by Task 2).
- `eta\ui\icons.py` — `glyph_icon(name, active, size_px, color)` (code-drawn 24×24 glyphs, 1.6px strokes, HiDPI-aware), `apply_to_canvas_icon()` (SVG→QPixmap), `app_icon()` — Task 1 reworks these.
- `eta\ui\canvas.py` — `TreeCanvas` (gestures mixin `gestures.py`), `NodeItem` (pins, hover tooltips), `EdgeItem/EdgeLabelItem`, pin modes `IDLE/RUBBER/MOVING_NODE/PIN_PRESS/PIN_LINK`, `_open_pin_picker` (left → causes picker; right → relevance-ordered intermediates; scenario-split guard), `_ordered_barriers`, `_apply_cause_from_picker`, context menus `build_eta_menu/build_fta_menu` (every action has an icon — asserted by tests), DnD, domino.
- `eta\ui\render.py` — `draw_node/draw_edge/draw_edge_label` shared by canvas and PDF (math-painted since session 8).
- `eta\ui\math_text.py` — see §2.
- `eta\ui\event_picker.py` — `EventPickerPopup.pick(items, title, parent, pos, filter_groups=…)` (search + funnel category filters, ~9 rows) — Task 3 extends its item kinds.
- `eta\ui\kb_window.py` — «База знаний» window: tabs «Ключевые / инициирующие события», «Причины отказов», «Без частоты (требуют задания)», «Логические элементы», «Библиотека значений», «Библиотека типовых сценариев» (`LibraryTab` with sub-tabs `EquipmentLibraryTab` «По оборудованию» — has the single «Применить на холсте» button + `btn_apply`, `equipment_applied` signal — and `PresetsTab` «По сценариям»); close guard; GOST form labels; pedal tooltips incl. `tooltip` field support.
- `eta\ui\inspector_panel.py` — right panel: node/edge editors, object props form (SIL/PFD/λ_DU/T_тест, pedals with `pedal_tip()`), scenario table.
- `eta\ui\hierarchy_panel.py` — «ИЕРАРХИЯ ОБЪЕКТОВ», horizontal toolbar (6 glyph buttons incl. «Добавить ключевое/инициирующее событие»), F2 rename, DnD, `InitPickerDialog`.
- `eta\ui\main_window.py` — toolbar, doc pop-out window, status bar with version, `_apply_library_equipment` (Task 3.1 target), KB guard routing.
- `eta\export\pdf_export.py` — vector A3/A2 PDF from the SAME layout (schematic + matrix modes), math-rendered legend/footnotes.
- Tests: `smoke_test.py` (invariants, validator, compaction/pins/relevance blocks 13b/13c), `gesture_test.py` (31 scenarios incl. KB guard, GOST labels, tooltip content assertions — tooltips are compared against `<br>`-flattened text because soft-wrap may split phrases).

## 4. SESSION RULES

1. Canvas and PDF share `compute_layout` + `render.py`; any visual change must go through both automatically — never fork geometry. Task 5's bezier edges must be drawable by BOTH the canvas and `QPdfWriter` (vector path, no rasterization).
2. KB JSON edits are data edits; UI terminology changes must not rename internal ids/keys (`sil`, `sil_pfd`, `pedals`, `b-*`, `pm-*`, `c-*`…). Backward compatibility of loading old JSON and old `*.etajson` project files (formats 1–3) must hold; Task 3 likely needs a NEW format version — design the migration explicitly and test it.
3. No new external dependencies; everything is PySide6-native (animations via `QPropertyAnimation`/`QVariantAnimation` are in-scope).
4. Style: the base UI remains flat Swiss-utilitarian (`QSS` in `theme.py`), BUT this session amends the design system in two controlled ways: (a) toolbar/panel icons become LARGER and COLORFUL (Task 1); (b) tooltips are replaced by the new dark animated component (Task 2). Both amendments must live in `theme.py`/`icons.py`/new modules — no ad-hoc colors scattered in forms. Buttons by objectName (`primary`, `primaryOutline`); icons only via `icons.py`.
5. After EVERY task: run `smoke_test.py` and `gesture_test.py` (offscreen) and keep them green; update assertions to new expected strings/geometry; add regression tests per task. Run `run_qa.cmd` and visually review regenerated `qa_artifacts\*.png` before declaring done. Animations must not break offscreen tests: expose final-state seams (e.g. `show_instantly()`, animation duration 0 under `QT_QPA_PLATFORM=offscreen` or a test flag) so assertions don't depend on timers.
6. Manual smoke check with `run_app.cmd` is the user's habit — the app must start cleanly from it.
7. Keep all current features working: DnD from KB to canvas, «Применить на холсте» (to be split in Task 3.1), smart linking, «Сценарий N» flows, matrix/PDF export, QSettings restore, domino, lightning protection.

---

## TASK 1. Icon/glyph redesign: bigger, colorful, contrasting-but-harmonious

**Problem.** Toolbar/panel glyphs are small monochrome line icons (24×24 base, 1.6px strokes, `#475569`/ACCENT) — visually weak; buttons look empty.

**Requirements.**
1. Rework `eta\ui\icons.py`: increase glyph size to (near) button size (e.g. 20–22px visible glyph inside 28–32px buttons; left toolbar up to ~24–26px), thicker strokes (2.2–2.6px), and a curated COLOR palette per glyph family — high contrast, but harmonized (define an `ICON_PALETTE` in `theme.py` next to the base palette: e.g. territory/building/room/area/equipment get distinct earth/steel/teal/amber hues; scenario/lightning bolt = warm accent; ПАЗ/shield = green family; danger actions = red family; view toggles = blue family). Keep recognizability at a glance.
2. All glyph call sites must keep working: `glyph_icon(name, active, size_px, color)` signature may stay, but default `color=None` should now mean «the glyph's own palette color» (with an optional `active` state variant — brighter/darker). Audit every caller (`left_toolbar.py`, `hierarchy_panel.py`, context menus, `kb_window.py` apply buttons, `doc_window.py`, main toolbar) and pass appropriate sizes; `apply_to_canvas_icon()` (SVG→QSvgRenderer→QPixmap with devicePixelRatio) must produce crisp HiDPI pixmaps in the new sizes.
3. `app_icon()` («Qj» monogram) may get a subtle color refresh — keep it professional.
4. Tests: existing `_assert_icons` (context menus have icons) must stay green; add a smoke-able check that `ICON_PALETTE` covers every glyph name (no glyph falls back to default gray unintentionally — opt-out list for intentionally-neutral glyphs like zoom +/−).

**Acceptance:** buttons across the app show larger colorful glyphs; QA screenshots reviewed; tests green.

## TASK 2. Modern animated tooltips (replace ALL standard QToolTip usage)

**Problem.** Standard `QToolTip` boxes are plain, small, dated. The app's tooltip CONTENT is already rich (KB `tooltip` fields with formulas, `math_html_lines` with real sub/superscripts, GOST citations) — the presentation layer is the bottleneck.

**Reference spec from the user's AI-colleague (INSPIRATION ONLY — adapt to our stack; you decide the final architecture; do NOT follow it verbatim where it conflicts with the project's rules or testability):**

> Custom `ModernTooltip` QWidget with `Qt.WindowFlags.ToolTip | FramelessWindowHint`, `WA_TranslucentBackground`, `WA_ShowWithoutActivating`; a global event-filter/mixin intercepting Enter/Leave without bloating widget classes. Dark premium slate/navy background (~#0f1219, 90–95% opacity, glassmorphic feel), rounded corners 8–12px, 1px glowing accent border (neon-cyan or project accent). Rich HTML/CSS content via QTextDocument or QPainter: headers, highlighted variables, left-bordered info-boxes for formulas; clean sans-serif stack (Segoe UI/Inter), line-height ~1.4, color-coding for variables/standards/sources. `QPropertyAnimation` with OutCubic/OutBack easing: fade-in 0.0→0.95, smooth fade-out; position offset ~+15/+15px from cursor, adjusted dynamically. Never allocate a tooltip per hover (cache per widget / lazy-load); animations must not block the GUI thread; must render `<sub>/<sup>`, Greek letters, `·` correctly. Scan the codebase for `.setToolTip(`/`.setToolTipDuration(` and route everything through the new layer.

**Requirements (binding).**
1. New module `eta\ui\modern_tooltip.py` (name your choice, but keep it in `eta\ui\`): one reusable tooltip component + an application-level hover controller (event filter installed like `install_scroll_wide` in `main.py`, strong reference kept — remember the GC pitfall). Content source remains the existing `setToolTip()` strings (plain/HTML/mini-notation) — do NOT rewrite tooltip content call sites; the controller reads `widget.toolTip()` on hover and renders it through `math_html_lines`-style rich text (reuse the math renderer for sub/sup; entity handling must survive Cyrillic, `&nbsp;`, `<sub>`, `<sup>`).
2. Visual language: dark translucent panel, rounded, 1px accent border, subtle glow; typographic hierarchy: bold header line (first line of the content), muted «Источник: …» lines, formula lines slightly larger and mono with real sub/superscripts; the current QSS `QToolTip` block stays as fallback for anything not yet routed. Blend the new style with the Swiss base (use the project ACCENT or a chosen neon accent defined ONCE in `theme.py`).
3. Animation: fade+slide-in (opacity 0→~0.95, ~8px rise, 120–180 ms, OutCubic), quick fade-out (~100 ms). Under `QT_QPA_PLATFORM=offscreen` or when a `KUJI_NO_ANIMATION` env/test flag is set, show instantly at final opacity/position (testability seam). The tooltip must reposition/retarget as the cursor moves between widgets without flicker; long tooltips (the 1500–1800-char KB explanations) must remain fully readable — bounded width, soft wrap (reuse/extend `math_html_lines`), grow downward, and respect screen edges.
4. QGraphicsScene support: `NodeItem` pin hovers and canvas hints currently use `QToolTip.showText` — route them through the same controller (a scene-aware adapter), including pin tooltips, edge labels' future hints, domino hints.
5. Performance: single shared tooltip instance retargeted per hover (no per-hover allocation), content caching keyed by widget + toolTip hash; no main-thread stalls (animations via QPropertyAnimation on the window opacity/pos; heavy rich text laid out once per show).
6. Tests: gesture scenarios assert tooltip CONTENT today via `widget.toolTip()` strings — keep that data source intact so those tests keep passing; add new tests for the controller (show/hide seams, offscreen instant mode, retarget). Extend `visual_qa_runner.py` to capture one rendered modern tooltip (e.g. hover the ПАЗ pedal programmatically and grab the tooltip window) into `qa_artifacts\qa_tooltip_modern.png`.

**Acceptance:** no standard flat QToolTip remains in interactive paths (a repo grep for `QToolTip.showText` shows only the adapter); KB long tooltips render beautifully with animated fade; tests green; QA screenshot reviewed.

## TASK 3. FULL REWORK of the tree-building algorithm: free-form bow-tie left wing with И/ИЛИ/НЕ logic nodes (THE CORE TASK — ask your questions FIRST)

**Problem.** The current left wing is the rigid `FtaSide` phase machinery (ГС/ИЗ phase chains in slots −5…−1, `Q_центра = Q_ГС·Q_ИЗ`, И/ИЛИ chosen per gate in a modal add-flow). The user cannot build the tree they think in. The new model is a free-form causal chain built directly from pins, with logic nodes hanging ON the arrows.

### 3.0 The canonical user pipeline (implement exactly this flow)

1. User adds «Территория 1».
2. On the territory the user can add an object «наружная установка 1» (outdoor installation). In «База знаний» → «Библиотека типовых сценариев» → «По оборудованию», SPLIT the single «Применить на холсте» button into TWO: **«Использовать на [иконка территории]»** (apply as an outdoor installation under a territory) and **«Использовать на [иконка участка]»** (apply as an installation on an area inside a building room) — icon-labeled buttons using the Task-1 colorful glyphs of territory/area. One outdoor installation may carry SEVERAL independent «Сценарий N» trees.
3. «Здание 1» → «Помещение 1» → «Участок 1».
4. On the area, the «Добавить ключевое/инициирующее событие» button → user picks e.g. «Пожар в здании: инструментально-механические цеха» → a «Сценарий 1» element appears under the area in the hierarchy; the canvas shows two nodes: **[Пожар…] → [Сценарий 1]**.

### 3.1 Node/pin semantics (bow-tie)

- **[Сценарий N]** is the terminal event of the RIGHT wing: it must have **NO right pins at all** (neither green nor red) — nothing can follow a final scenario. (Currently terminal nodes show pins — fix.)
- **[Пожар…] is the CENTER event** between the wings: green+red pins LEFT and RIGHT. Left = antecedent events (causes); right = consequence events (stages of the accident).
- Clicking the **LEFT GREEN pin** of the center opens the base of ANTECEDENT events («Причины отказов» — e.g. «Прямой удар молнии в объект (разряд атмосферного электричества)»). The chosen event becomes a node to the LEFT of the center, connected into the chain.
- **Initial (начальное) event**: an antecedent that has no antecedents of its own (e.g. «Прямой удар молнии…») — it gets **NO left pins**; right pins present. One tree has EXACTLY ONE initial event («одно начальное событие = один сценарий»); the unique start, unique center, unique end «Сценарий N».
- Intermediate antecedent nodes (e.g. **[Появление источника зажигания (ИЗ)]**) have pins on both sides; an arrow runs from a node's RIGHT GREEN pin to the next node's LEFT GREEN pin (only «ДА» arrows are drawn; left-wing links are causal, all treated as occurred).
- Sequential (serially connected) nodes are **always logical AND**: frequencies MULTIPLY along the chain. **Remove the И/ИЛИ choice from the properties panel of consequence-stage nodes** (it belongs only to logic nodes, see below). The pin event lists must offer not only event nodes but also LOGIC nodes И / ИЛИ / НЕ.

### 3.2 Logic nodes И / ИЛИ / НЕ hanging on arrows

- When the chain [начальное] → [следствие] exists (e.g. [Прямой удар молнии…] → [Появление ИЗ]), a small **logic node [И]** appears **above/next to the arrow** (anchored near the arrow's midpoint, following it). With a single input it is **GREY = locked**: double-click LMB does nothing, because a consequence of a single initial event has no alternative inputs.
- Adding a SECOND antecedent event into the same consequence (e.g. [Пожароопасный отказ единичного электрического изделия (короткое замыкание, перегрузка, искрение)] connected by dragging from its right green pin to [Появление ИЗ]) makes the logic node **colored = active**.
- **Double-click LMB** on an active logic node cycles **И → ИЛИ → НЕ → И**. The same cycling is available in the right properties panel via a dropdown («Тип логического элемента»).
- **И (AND)**: the node keeps hanging above the arrow; input frequencies multiply into the consequence (Q_out = ∏ Q_in). E.g. Q(молния) · Q(электроотказ) → Q(Появление ИЗ).
- **ИЛИ (OR)**: the node **instantly embeds INTO the arrow** (in-line), gains pins like a full logic node, and under the «Сценарий 1» node (right wing) a **dashed node [Сценарий 2]** appears — two independent events lead to two independent scenarios (Q_out = 1 − ∏(1 − Q_in); each input branch ultimately feeds its own scenario terminal — work out the exact bookkeeping with the user if needed).
- **НЕ (NOT)**: semantics not yet defined by the user — propose a sane engineering interpretation (e.g. an inhibitor input with conditional probability 1−P, complement for probability-type inputs) and CONFIRM with the user before implementing.
- The center-event frequency for per-area initiating events («Пожар в здании: …» series, `freq_mode=per_area`, tables П1.4 of Методика № 533) must be computed as **rate_per_m² × area of the Участок** (area is a property of the Area object; e.g. 4,2·10⁻⁶ год⁻¹·м⁻² × F_уч) — verify the whole chain end-to-end: the scenario frequency = product along the left wing into the center, then right-wing factors into «Сценарий N».

### 3.3 Model/KB/format consequences (design explicitly)

- This supersedes (or deeply reworks) the `FtaSide` ГС/ИЗ phase system, `add_fta_phase/add_fta_cause/add_fta_subgate`, `check_fta`, the FTA columns of `compute_layout`, the FTA part of the matrix, and `fta_center_q`. Decide (with the user) what happens to: old projects with ГС/ИЗ phases (migration path), the «Логические элементы» KB tab, the lightning `k_scale` mechanism (it scales cause `c-iz-lightning` — keep working), and the layout's FTA columns.
- The KB may need corrections (e.g. making sure the antecedent picker offers events like «Пожароопасный отказ единичного электрического изделия…», lightning, and the «Пожар в здании: …» per-area series with proper sources; add/adjust records per Методика № 533 tables — no invented numbers, cite tables).
- Serialization: new format version with migration from formats 1–3 (old FTA wings either converted to the new logic-node representation or preserved read-only — propose, ask).
- Matrix view and PDF summary must reflect the new semantics (AND-multiplication chains, OR-split scenarios — dashed «Сценарий 2» rows).

### 3.4 Tests

Extend `smoke_test.py` (math invariants: AND product, OR union, scenario split, per-area center frequency) and `gesture_test.py` (the FULL canonical pipeline of §3.0–3.2 driven through real pins/pickers/double-clicks; terminal has no right pins; initial has no left pins; grey→active logic node; cycling; dashed Scenario 2 on OR).

## TASK 4. Formula-driven frequency inputs (lightning as the pilot)

**Problem.** [Прямой удар молнии в объект] currently shows a hardcoded editable `Q, год⁻¹: 6` — the ГОСТ formula behind it (N_у.м = (S+6H)·(L+6H)·n_у·10⁻⁶, η by protection level, СО 153-34.21.122-2003; already implemented in `generator.py::lightning_*`) is bypassed.

**Requirements.**
1. In the node properties panel (and/or a dedicated formula section), expose the formula VARIABLES as editable fields with sensible mean defaults (building length L, width S, height H in m; strike density n_у, 1/(км²·год); lightning protection level I–IV → η). The resulting **Q is computed and READ-ONLY** (no free-form override; removing the arbitrary «6»).
2. Every variable/argument field gets a short tooltip (through the Task-2 tooltip layer, math-rendered: symbol, unit, meaning, source). The formula itself is shown as a math-rendered line (N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶; Q_пораж = N_у.м·(1−η)).
3. Generalize: introduce a small formula-input pattern (`formula fields spec` in the KB record or a UI helper) so other computed quantities (e.g. per-area center frequency with F_уч) can reuse it. Decide the storage (props of the object vs node q_spec) and keep serialization backward-compatible.
4. Tests: defaults compute the documented Q; changing a variable recomputes; Q field is not editable; tooltips present.

## TASK 5. Canvas edges: no merging, smooth bezier, live node-following (Blender-style)

**Problem.** (1) Parallel/adjacent arrows visually merge into one line. (2) Edges are orthogonal Manhattan polylines — the user wants smooth curves/bezier. (3) Nodes can be dragged anywhere, but edges re-route orthogonally — they must FOLLOW the nodes fluidly like Blender's node editor.

**Requirements.**
1. Replace ETA edge rendering with smooth **cubic bezier** paths: start/end exactly on the pin circles (existing anchoring), control points producing gentle horizontal S-curves (e.g. tangents leaving the source pin horizontally and entering the target pin horizontally). FTA/logic-node edges (Task 3) use the same system.
2. **Anti-merge**: when several edges share a pin or run in parallel, spread them (offset control points / slight curvature fan-out by index) so they remain visually distinct; arrowheads must not overlap callout boxes.
3. **Live following**: during node drag (`apply_manual_positions` path), recompute the bezier geometry in the same continuous update loop already used for Manhattan re-layout — edges must glide with the node (no full relayout per mouse-move; the geometry of the dragged node's edges updates from its new rect; the collision audit may run throttled/on-drop).
4. Callout (плашка) placement adapts to curves (anchor near the curve's first third); the compaction invariants from session 8 (parent→child gap ≤ callout + 2·PAD, branch order, audit) must stay valid — adapt the audit's segment∩rect checks to sampled bezier polylines.
5. **WYSIWYG**: `render.py::draw_edge` gains the bezier painter used identically by canvas and PDF (`QPdfWriter` supports QPainterPath natively). Straight-snap edges (single-child continuations) remain straight lines.
6. Tests: update all edge-geometry assertions (points[0]/points[-1] on pins still hold; add curve assertions: sampled polyline smoothness/no self-intersection; distinct-edges separation ≥ N px on shared-pin fans). QA screenshots reviewed.

## FINAL DELIVERABLES OF THE SESSION

1. Questions-first list produced and answered BEFORE Task 3 implementation (§0).
2. All five tasks implemented; `smoke_test.py` + `gesture_test.py` green (new assertions included); `run_qa.cmd` artifacts regenerated and visually reviewed (note the review in the report, incl. a `qa_tooltip_modern.png`).
3. Version bumped to **5.0.0** (`eta\__init__.py`); README.md updated (new tooltip system, icons, tree semantics, formula inputs, bezier edges).
4. `old prompts (done prompts)\REPORT_SESSION_9.md` in English: per-task summary, files touched, algorithm notes (math of И/ИЛИ/НЕ, migration decisions, bezier/anti-merge parameters), test results, screenshot references, known issues.
5. Order of work: Task 2 skeleton + Task 1 (independent, can start while questions are open) → question gate → Task 3 (core) → Task 4 → Task 5 (depends on Task 3's edge system). Adjust if dependencies dictate, but keep each task's tests passing before moving on.

## KNOWN PITFALLS (do not step on these again)

- Cyrillic file edits: byte-safe temporary Python scripts only (see §1); never pwsh string cmdlets; delete scripts after use.
- Modal dialogs block offscreen tests (`QMessageBox.exec`, `QDialog.exec`): use testable seams (`_ask_close_guard`, `_ask_rename`, `_confirm_for`, picker monkeypatching) — extend that pattern to any new dialogs.
- QSettings in tests: hermetic ini (`setDefaultFormat(IniFormat)` + `setPath`) — HKCU writes are denied in the sandbox.
- PySide6 GC: app-level event filters must hold a strong module-level reference (see `scroll.py::_ACTIVE_FILTER`).
- Offscreen: `QT_QPA_FONTDIR=C:\Windows\Fonts` mandatory; `FT_New_Face failed with index 0 : 2` and «plugin does not support raise()» are harmless stderr noise; long runs: use background jobs with unbuffered output (`python -u`), read the output file, and NEVER leave a modal open in a test (it hangs the run).
- Known pre-existing flake: gesture scenario 1 zoom-smoothness (`micro < 0.06`) is timing-sensitive — rerun before investigating.
- Tooltip content assertions compare against `<br>`-flattened text (soft-wrap may split phrases).
- Style rule: short dash «–» only; test asserts no «—» in the KB JSON.

## 10. STARTER QUESTIONS (extend freely; number your full list when asking)

1. НЕ semantics: inhibitor with 1−P? Complement of probability-type inputs only? What does НЕ output when an input is a FREQUENCY (год⁻¹) rather than a probability?
2. ИЛИ → «Сценарий 2»: does the second scenario inherit the SAME center event and right wing (two left-wing paths → two terminals), or does the whole right wing fork per OR-input? How are the two terminal frequencies booked (1−∏(1−Q_i) split vs per-branch products)?
3. Old projects with ГС/ИЗ phase wings: convert to logic-node chains automatically, keep as legacy read-only, or drop with a warning? Same question for the «Логические элементы» KB tab and `check_fta` rules (phase purity, slot levels).
4. Does the old `FtaSide` layout (FTA columns −5…−1, phases centered on the root) disappear entirely, or do logic-node chains still align to echelon columns (with `eff_col` compaction)?
5. Multiple independent «Сценарий N» under one outdoor installation: independent trees each with its own center event, or one shared center? How does the hierarchy panel group them?
6. For «Использовать на [иконка участка]» when no building/room/area exists yet: auto-create the chain (current behavior) or require an explicit selection?
7. Per-area center frequency: F_уч from the Area object only, or also allow overriding on the equipment/scenario object? What if the area property is unset (0 m²) — block the tree or use a default?
8. Lightning formula: which object owns the variables (the building vs the tree node)? The building already has lightning-protection fields (level I–IV, dimensions) — should the node reuse THEM (single source of truth) instead of node-local copies?
9. Bezier edges: any preference for curvature strength/spacing constants, or is «smooth, distinct, WYSIWYG» the only constraint?
10. Should the four existing long KB tooltips (ПАЗ/вентиляция/мониторинг/износ) get any visual re-layout inside the new tooltip component (e.g. formula info-boxes), or is the current text structure kept as-is behind the new skin?
