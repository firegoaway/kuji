# PROMPT: Kuji – Session 18. Interface memory + real-layout shortcuts + report text cleanup + «База данных» + sources registry + unified DOCX export + last-folder memory + DB help

You are a Senior Desktop Application Engineer (PySide6/Qt 6). You continue developing the FINISHED, test-covered application «Kuji» (project folder is historically `Freq` – do NOT rename it) – a constructor of logical event trees per Order of the Ministry of Emergency Situations of Russia No. 533 («Методика МЧС России № 533»).

**Precondition:** sessions 1–17 are done (v6.6.0). Read before starting: `old prompts (done prompts)\REPORT_SESSION_17.md` (П1.1 multiplier, matrix renames, inspector cleanup, latin_keys + undo/clipboard, bigger tree + fit cap, rubber band/group ops, hybrid PDF with Q_В). Everything described there works and is covered by tests – do not break it without need. Session 18 is a **defect-fix + export-rework session**: thirteen tasks, ending with the FULL REPLACEMENT of the PDF export by a single DOCX report generated through an embedded pandoc. All design decisions below were confirmed by the customer in a Q&A round (marked LOCKED) – they are normative for you; do not re-open them. Ask questions per §0 when a task or part of it is ambiguous.

---

## 0. LANGUAGE & COMMUNICATION PROTOCOL (strict)

- **Reasoning, reporting, and ALL communication with the user: ENGLISH.** Every message, plan, status update, question list, and the session report – in English.
- **Questions to the user: RUSSIAN only**, well-formed, expanded, proper normative Russian with correct sentence structure and etiquette (this overrides English for question lists; it is the single exception). If the user did not understand a question, REPHRASE it properly instead of repeating.
- **Application UI language: RUSSIAN** – unchanged. All user-facing strings you add or edit (labels, buttons, tooltips, menu items, messages, report texts) must be in normative Russian engineering style (§5 canon).
- **Code comments and docstrings: RUSSIAN**, matching the existing style of the codebase (see any file in `eta\`).
- Dashes: ONLY the short en-dash «–» (U+2013) in code strings/JSON/README/report texts. Never «—» (em dash).
- Questions protocol (HARD GATE): ask **incrementally, per task, as work progresses**, NOT as one giant upfront list. When a task or part of it is ambiguous, has no concrete object, or carries double meaning – STOP that task, formulate a SHORT numbered question list in Russian about exactly that task, send it, and WAIT. Do not implement on assumptions. Principle #1 from the customer: «Лучше 10 раз спросить и переспросить, чем 1 раз накосячить.» While waiting for answers on one task you MAY proceed with independent, mechanical, low-risk items. All LOCKED decisions below must NOT be re-asked.
- **Manual verification loop is part of this session (Task 2):** the customer starts the app himself via `run_app.cmd` – you NEVER launch `run_app.cmd` in automated batches. When a task requires real-desktop feedback, prepare the instrumentation, then ask the customer (in Russian) to run a short scripted check and report what he sees.

## 1. ENVIRONMENT & ABSOLUTE PATHS (memorize, do not re-discover)

| What | Where |
|---|---|
| Project root | `D:\ProgrammzD\GraphiczD\Freq` |
| Python (embedded, use it for everything) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` – Python 3.14.3, PySide6 6.12.0 |
| Entry point | `main.py`; launcher `run_app.cmd` (manual start is the USER's habit – never launch it in automated batches) |
| Headless visual QA | `run_qa.cmd` → `visual_qa_runner.py` (offscreen; artifacts in `qa_artifacts\`) |
| Core tests | `smoke_test.py` (23 blocks), `gesture_test.py` (52 blocks; offscreen; ends with `GESTURES PASSED`) |
| Knowledge base (data) | `eta\knowledge\knowledge_base.json` – `meta.version` becomes **«6.2»** this session (Task 9 adds a sources registry). NEVER edit the KB via pwsh string cmdlets, only temporary Python scripts over `read_bytes()/write_bytes()`, deleted after use. |
| App version | `eta\__init__.py` → `__version__ = "6.6.0"` – this session bumps to **6.7.0** (feature session). The gesture test asserts the substring «6.6» in block 1 – UPDATE it to «6.7». |
| Session report | write `old prompts (done prompts)\REPORT_SESSION_18.md` (English) at the end |
| pandoc source (LOCKED) | `D:\ProgrammzD\UtilitiezD\Pandoc\pandoc.exe` – pandoc 3.4, standalone (218 MB). COPY it into `runtime\pandoc\pandoc.exe`; the app calls ONLY the embedded copy, never the external path. |
| DOCX template donor (LOCKED) | `D:\TrashD\(К1) Ф3.6, ФОК Донецк.docx` (2 MB; also `.pdf`, 44 pages, for visual reference) – GOST Р 21.101 frames + stamps in headers/footers, Times New Roman, blue headings #2E74B5, sectPr page setup. Use it ONCE to derive `eta\export\reference.docx` (Task 11); after that the app is fully autonomous, `D:\TrashD\` is never needed at runtime. |
| docx→PDF for QA | MS Word is installed on this machine (COM ProgID `Word.Application` works); LibreOffice is NOT. QA converts generated .docx → PDF via Word COM (headless), renders pages to PNG for vision review. |
| Dead code note | `eta\core\formulas.py` is a legacy reference module imported NOWHERE. Do not wire it in. |

## 2. STATE AFTER SESSION 17 (v6.6.0) – what exists, all tested

- **Paradigm (invariant):** five scenario types (ТГМ/ГГ/ГЖ/ЛВЖ/Пыль); fixed 5-node tree; `Q_сценария = Q_вещество·Q_ОК·Q_ГС·Q_ИЗ·P_типа`, `Q_участок,k = Σ·Kσ`; format 5. П1.1/direct causes multiply λ by the owner's own F/L/V (`CalcContext.p11_site_value`, piece `(4·10⁻⁵·86)`); П1.2/П1.3/П1.4 untouched.
- **Shortcuts/undo/clipboard:** `eta\ui\latin_keys.py` (ЙЦУКЕН→QWERTY table; `latin_key()`; app-level `LatinKeyFilter` converting Ctrl/Alt + Cyrillic key to the Latin positional event; installed once per QApplication with a strong module ref). Shared «Правка» actions (Отменить Ctrl+Z / Вернуть Ctrl+Y / Копировать Ctrl+C / Вставить Ctrl+V) in `main_window._ensure_edit_actions` – ONE QAction set on the QApplication, ApplicationShortcut, dispatched via `_edit_target()` (newest visible MainWindow); snapshot undo depth 50 (`_undo_push` base-coalescing). Existing explicit twins: Ctrl+E/У (export), Ctrl+Q/Й (quit), Ctrl+D/В (doc window), Alt+A/Ф («Показать всё»). NOTE (measured in session 17): the Qt shortcut dispatcher matches events of the ACTIVE window only – offscreen tests must `QApplication.setActiveWindow(w)` before key presses.
- **Canvas:** rubber-band ЛКМ selection (QRubberBand rgba(59,130,246,0.12) + #3B82F6), Ctrl/Shift toggle, group drag (`_commit_node_drag(items, delta)`), group Delete seam `_confirm_trees_delete`; **Space+ЛКМ pan** implemented via the CANVAS VIEWPORT eventFilter (`_space_held`, KeyPress/KeyRelease Space) – works when the canvas has focus; `FIT_PAD_PX = 48`, `FIT_MAX_ZOOM = 1.5`; bigger typography (F_TITLE 14 / F_META 11 / F_FORMULA 14, PAD_V 16, NODE_INSET 13, min node height 56, edges 2.0).
- **PDF export (REMOVED this session by Task 11):** `eta\export\pdf_export.py` – `build_report_document` (QTextDocument+HTML: title «ОТЧЁТ О РАСЧЁТЕ ЧАСТОТЫ ВОЗНИКНОВЕНИЯ ПОЖАРА», subtitle «Объект расчёта: …», project/date line, sections 1–4, source cells in `[...]` brackets, Kσ + «Огненный шар» on one line), `export_matrix` (shaded header, measured rows, `Q_В` totals), `export_schematic`; all painted by ONE QPainter (QPdfWriter traps measured: post-paint `setPageLayout` rewrites all MediaBoxes; a second painter session rewrites the file). Dialog: `eta\ui\dialogs.py` `PdfExportDialog` (size_combo A3/A2 landscape, mode_combo «Содержимое», `sw_report` toggle, path defaults to Desktop when no project path).
- **Window memory today:** `MainWindow._restore_ui` restores geometry + main splitter from QSettings keys `ui/geometry`, `ui/splitter`; BOTH are saved ONLY in `MainWindow.closeEvent`. Doc window geometry `ui/doc_geometry` and KB window `ui/kb_geometry` are saved on their close. Child windows contain NO inner QSplitters.
- **File dialogs today:** `_save_project`/`_open_project_dialog` call QFileDialog without an explicit dir; `_export_pdf` passes `start_dir = dirname(project)` else empty → the dialog falls back to Desktop (screenshot №2).
- **KB:** `eta\core\kb.py` accessors; `eta\ui\kb_window.py` tabs; every ГС/ИЗ/коэффициент record carries a plain `source` STRING («Приказ МЧС России № 533, прил. № 1, табл. П1.3/П1.4», «ГОСТ 12.1.004-91, прил. 3, табл. 9», …). Report source list today is auto-derived short lines (`_tree_sources` in pdf_export.py).
- **Report text rules already LOCKED in session 17 that CARRY OVER into the new DOCX:** Q_В notation everywhere; «Исполнитель/Дата» never printed in the text; only the type-relevant site parameter (S/L/V); flow-scope suffixes on ГС rows; matrix headers «№, Участок (установка), Тип сценария, Сценарий пожара, Q, год⁻¹, Формула».
- **Tests/QA:** smoke 23 blocks, gestures 52 blocks, both green; `qa_artifacts\` incl. `qa_matrix2.png`; `visual_qa_runner.py` produces the `qa_pdf_*` set (will be replaced, Task 11).

## 3. CODE MAP (extend, don't break)

- Task 1 (panel memory): `eta\ui\main_window.py` (`closeEvent` saves `ui/geometry`+`ui/splitter`; `_restore_ui` restores; `self.splitter` is the single main QSplitter; doc window `ui/doc_geometry` in `_on_doc_window_closed`; kb geometry in `_open_kb_window`). Give the main splitter an `objectName`; add save-on-`splitterMoved` (debounced QTimer ~300 ms) so the state survives ANY exit path; restore after widgets are built; child windows keep saving geometry on close (their sizes are the only movable «panels» there – no inner splitters exist).
- Task 2 (real-layout shortcuts + Space): `eta\ui\latin_keys.py`; `eta\ui\main_window.py` `_build_actions` (twins, contexts); `eta\ui\canvas.py` viewport eventFilter (`_space_held`) and `mousePressEvent` Space branch. Real-Windows facts measured by the customer: Alt+Ф does NOT open the «Файл» menu; Ctrl+N/O work in BOTH layouts; Alt+A, Ctrl+E/У, Ctrl+D/В do NOT work in the Russian layout; Space+ЛКМ does not pan in EITHER layout. Offscreen QTest equivalents DO pass – so the divergence is in real Windows event delivery (possible causes to verify by instrumentation: on real Windows Qt may deliver letter keys with Latin `key()` + Cyrillic `text()`, or Cyrillic `key()`; Alt+letter may be eaten by QPA/ShortcutOverride before app filters; Space reaches only the FOCUSED widget – the canvas viewport filter never sees it when focus sits in the hierarchy/inspector).
- Tasks 3–7 (report text): the PDF pipeline is deleted by Task 11 – implement these rules in the NEW DOCX builder (`eta\export\report_docx.py`, see Task 11): title «Расчет частоты возникновения пожара»; no «Объект расчёта:» line; no «Проект «…» · date» line; source column without brackets (empty → «–»); Kσ and «Огненный шар» as separate lines, fireball line only when enabled.
- Task 8 (rename): grep «База знаний/Базы знаний/Базу знаний/Базе знаний» across `eta\` UI strings + tests + README; replace with «База данных/Базы данных/Базу данных/Базе данных» in matching cases. Internal names stay: `kb.py`, `kb_window.py`, `knowledge_base.json`, class names.
- Task 9 (sources registry): `eta\core\kb.py` (new section `sources: [{id, title}]` in the KB JSON; migration on load: collect existing distinct non-empty `source` strings from gs/iz/modifier records into the registry with generated ids, rewrite each record's `source` to the id, keep the string as the entry title; `meta.version` «6.1»→«6.2»; byte-safe scripts only); `eta\ui\kb_window.py` (new «Источники» tab: table id/наименование, add/edit/delete via the existing editor patterns, in-use warnings like templates have); source pickers in the ГС/ИЗ/меры editors become combos over the registry (existing records keep working). Serializer untouched (KB is data, not the project file).
- Tasks 10–11 (export): `eta\ui\dialogs.py` (rework the dialog: remove `mode_combo` «Содержимое» and `sw_report`; size_combo becomes 6 entries – «ISO A4 – 210 × 297 мм (книжная)», «ISO A4 – 297 × 210 мм (альбомная)», «ISO A3 – 297 × 420 мм (книжная)», «ISO A3 – 420 × 297 мм (альбомная)», «ISO A2 – 420 × 594 мм (книжная)», «ISO A2 – 594 × 420 мм (альбомная)»; default path `*.docx`); `eta\export\report_docx.py` (NEW: builds the document content and drives pandoc); keep `eta\ui\canvas.py` `doc_scene` rendering (PNG source); `eta\export\pdf_export.py` DELETED together with all its callers (`_export_pdf` in main_window re-targeted; matrix/schematic rendering helpers may be reused for images); `visual_qa_runner.py` replaces `qa_pdf_*` with docx-derived artifacts.
- Task 12 (last-folder memory): one QSettings key `ui/last_dir`; updated on every successful save/open/export dialog; prefill `_save_project`, `_open_project_dialog`, and the export dialog path field with it (fallback: project dir → Desktop).
- Task 13 (DB help): `eta\ui\kb_window.py` (bottom button row with «Закрыть»), `eta\ui\icons.py` (vector glyph machinery + `ICON_PALETTE` – smoke checks coverage), `eta\ui\math_text.py` + `theme.math` (the ACTUAL formula mini-notation the help text must document), `eta\core\numfmt.py` (`parse_eng` caret syntax `1,02^-6`).

## 4. SESSION RULES

1. Suggested order: **1 → 2 → 12 → 8 → (3+4+5+6+7 as part of 11's builder) → 9 → 13 → 10 → 11**. Tasks 3–7 have no standalone existence after the PDF removal – implement them directly in the DOCX builder and verify via its tests/QA. After EVERY task: run `smoke_test.py` and `gesture_test.py` green (update assertions that reference changed behavior); run `run_qa.cmd` and vision-review (glm-5.3-flash, ≤4 iterations per artifact, crop + 2× upscale) the affected artifacts.
2. New external dependencies: NONE beyond the embedded `runtime\pandoc\pandoc.exe` (pandoc is an external binary, not a Python package; do not pip-install anything).
3. Style: flat Swiss-utilitarian in the app UI; new visuals via `theme.py`; no shadows/gradients. The DOCX follows the GOST reference template (Task 11), not the app theme.
4. Modal dialogs block offscreen tests: every NEW confirmation is a seam; menus testable without `exec`.
5. `run_app.cmd` manual start is the user's habit – never launch it in automated batches; the app must start cleanly.
6. Questions per §0 only; LOCKED decisions not re-asked.
7. Format-5 compatibility: no project-file format changes. The KB JSON grows the `sources` section (version «6.2») with automatic migration on load – old KB files open transparently.
8. QSettings in tests: hermetic ini (`qa_artifacts\_settings`), as today.

## 5. UI-TEXT STYLE CANON (session 11, applies to all new/changed strings)

- Concise normative Russian engineering language; no jargon; periods, never «;» in prose; en-dash «–» only.
- Russian term first, Latin abbreviation in parentheses.
- The word «барьер» is banned in UI/data (use «защитное средство» / «противоаварийная защита»).
- Reference numbers only from existing KB `source` strings or `literature\`; never invent.
- Numbers shown to the user: engineering notation («9·10⁻⁵», comma mantissa, Unicode superscripts).

---

## TASK 1. PANEL/SPLITTER MEMORY (main window + child windows)

Defect: the interface «does not remember» how the user resized the panels of the main window between runs; child window sizes also reset on reopen.
1. Give the main QSplitter an `objectName` (e.g. `mainSplitter`). Persist `saveState()` + window `saveGeometry()` to QSettings not only in `closeEvent` but ALSO on `splitterMoved` with a ~300 ms debounce QTimer (survives ANY exit path, including crashes and killing the process while a modal blocks close). Restore in `_restore_ui` after the widgets exist (validate bytes; keep today's fallback `setSizes([320, 500, 360])`).
2. Child windows (Документ, База данных) contain no inner splitters – their «panels» are the window geometry itself. Keep saving `ui/doc_geometry` / `ui/kb_geometry` on close (already present) and ADD a save when hidden via any path; verify restore-on-reopen works from a SECOND process run (tests use the hermetic ini).
3. Tests: gesture block – resize the main splitter (`setSizes` different from default), force-save (call the debounced slot directly), construct a NEW MainWindow over the same hermetic QSettings, assert `sizes()` round-trip; same for the doc window geometry. No real timers needed – invoke the debounced slot synchronously.
4. QA: qa_window unchanged visually; no vision pass required beyond a sanity look.

## TASK 2. REAL-LAYOUT SHORTCUTS (Alt+A, Ctrl+E, Ctrl+D) + Space+ЛКМ PAN

Defects measured by the customer ON THE REAL DESKTOP (via run_app.cmd; Alt+Ф does NOT open «Файл»; Ctrl+N/O work in both layouts): Alt+A / Alt+Ф, Ctrl+E / Ctrl+У, Ctrl+D / Ctrl+В do not fire in the Russian layout; Space+ЛКМ does not pan in either layout. Offscreen QTest analogues PASS – the divergence is real-Windows delivery.
1. **Instrument first (mandatory):** add a tiny debug hook to `latin_keys.py` + the canvas viewport filter: when env var `KUJI_DEBUG_KEYS=1`, append every KeyPress/KeyRelease it sees to `qa_artifacts\key_debug.log` (key(), nativeVirtualKey(), text(), modifiers(), focusWidget class, whether converted/accepted). Ask the customer (Russian, short numbered instructions) to: set the variable, start via run_app.cmd, switch to the Russian layout, press the four failing combos + Space over the canvas, close, and say the log is ready. Read the log; write the observed delivery shape into the session report BEFORE changing code.
2. Fix per the observed evidence. Expected shapes (verify, don't assume): (a) real Windows delivers Cyrillic letter keys with Latin `key()` + Cyrillic `text()` → extend the filter to ALSO convert when `text()` is Cyrillic while `key()` is a Latin letter (map by the same ЙЦУКЕН table using `text()[0]`); (b) Alt+letter eaten by QPA/ShortcutOverride → handle ShortcutOverride in the filter or deliver the synthetic event directly to the target action; (c) Space reaches only the focused widget → move Space tracking to an APPLICATION-level watch (the existing `LatinKeyFilter` or a sibling app filter): any Space press/release while no text editor (QLineEdit/QTextEdit/QPlainTextEdit/QAbstractSpinBox editor) has focus toggles the canvas pan readiness; the canvas reads that global flag (keep the viewport filter for the focused-canvas case). Keep `isAutoRepeat()` handling for Space.
3. Do NOT remove the offscreen tests (blocks 21/50/51 stay green); ADD a gesture block asserting the NEW paths: `text()`-based conversion (synthesize QKeyEvent with Latin key + Cyrillic text), application-level Space pan while focus sits in the hierarchy tree.
4. Manual confirmation loop: after the fix, ask the customer to repeat the four checks via run_app.cmd and confirm in chat; record his verdict in the report.

## TASK 3. REPORT TITLE (applies to the DOCX builder, Task 11)

The document title becomes **«Расчет частоты возникновения пожара»** (sentence case, exactly this string – it doubles as the title-page heading at 18 pt and the top of the document model). The old ALL-CAPS «ОТЧЁТ О РАСЧЁТЕ ЧАСТОТЫ ВОЗНИКНОВЕНИЯ ПОЖАРА» disappears everywhere (builder strings, tests, README). The title is followed immediately by the TOC page (no subtitle, no meta lines – see Tasks 5–6).

## TASK 4. Kσ AND «ОГНЕННЫЙ ШАР» LINES (DOCX builder)

In «Параметры расчета»: `Коэффициент безопасности Kσ = <значение>` on its own line (no trailing «;»). On the next line, ONLY when the switch is enabled: `Огненный шар: включен` (no quotes around «Огненный шар»; spelling exactly «включен»). When disabled the line is omitted entirely. Tests: fireball off → line absent; on → present.

## TASK 5. REMOVE «Объект расчёта: …» (DOCX builder)

The subtitle line `Объект расчёта: <владелец> – <тип сценария>` is removed completely. Owner/scenario identity is expressed ONLY by the section hierarchy (Task 11 structure).

## TASK 6. REMOVE the project/date meta line (DOCX builder)

The line `Проект «…» · ДД.ММ.ГГГГ` is removed. The ONLY permitted meta text is the title-page line **«Куджи v<version> от dd.mm.yyyy»** (12 pt) under the title (LOCKED; `__version__` from `eta\__init__.py`, date = export date, format dd.mm.yyyy).

## TASK 7. NO SQUARE BRACKETS IN THE SOURCE COLUMN (DOCX builder)

In the «Исходные данные» table, column «Источник»: plain text of the registry entry title, no `[...]`. Empty/absent source → an en-dash «–» alone. (Screenshot №1 showed `[Приказ МЧС России № 533, прил. № 1, табл. П1.3/П1.4]` etc.)

## TASK 8. «БАЗА ЗНАНИЙ» → «БАЗА ДАННЫХ» (UI rename)

All user-visible occurrences in all cases (menu item, window title, buttons, tooltips, status messages, README, tests) → «База данных/Базы данных/Базу данных/Базе данных». Internal module/file/class names and the KB JSON structure unchanged. Grep first, list every occurrence in the report.

## TASK 9. SOURCES REGISTRY IN «БАЗА ДАННЫХ» (LOCKED design)

1. KB JSON gains a top-level `sources` section: `{"version": "6.2", "sources": [{"id": "src-...", "title": "Приказ МЧС России № 533, прил. № 1, табл. П1.1"}, ...]}`. On load, if the section is missing (old KB), migrate: collect distinct non-empty `source` strings from ГС/ИЗ/меры records, create registry entries (generated ids), rewrite each record's `source` field to the entry id, bump `meta.version` to «6.2». Byte-safe temporary scripts for the checked-in file; runtime migration must also work for user-opened old files without writing them back silently.
2. «База данных» window: new **«Источники»** tab – a table (наименование), add/edit/delete with the existing editor patterns and in-use warnings (a source referenced by records cannot be silently deleted). Editors of ГС/ИЗ/меры records: the source field becomes a combo over the registry (+ a quick «добавить источник…» affordance is allowed but optional).
3. **Report section «Нормативные ссылки и справочные данные» (LOCKED вариант Б):** print ONLY the registry entries attached to records that PARTICIPATE in the calculation of this project (dedup, numbered `1.`, `2.`, …, no brackets). Automatically derived table references (табл. П1.1, П2.1, ГОСТ табл. 9 …) are NO LONGER printed; if a methodics table is used but no registry entry is bound to any participating record, that table is SKIPPED (customer's explicit ruling). The old `_tree_sources` auto-block dies with the PDF.
4. Tests: smoke (registry migration dedup; record→id rewrite; variant-Б list building incl. the skip case); gesture (add a source in the «Источники» tab, bind it to a used cause, export → the entry appears in the report; unbind → absent).

## TASK 10. EXPORT FORMATS: A4/A3/A2 × PORTRAIT/LANDSCAPE (LOCKED)

The export dialog's «Формат листа» combo offers exactly six entries: ISO A4 book, ISO A4 album, ISO A3 book, ISO A3 album, ISO A2 book, ISO A2 album (labels in the established style «ISO A3 – 420 × 297 мм (альбомная)» etc.). The choice defines the PAGE SIZE of the rendered schema images embedded in the DOCX (Task 11). The old A3/A2-landscape-only PDF list disappears with the PDF.

## TASK 11. UNIFIED DOCX EXPORT VIA EMBEDDED PANDOC (LOCKED – replaces PDF completely)

**One project = one DOCX. The PDF export as a product is REMOVED entirely** (dialog mode combo «Содержимое», the `sw_report` toggle, `pdf_export.py`, `qa_pdf_*` artifacts, and all PDF-text test blocks are deleted/replaced; `Ctrl+E` now opens the new export dialog; the internal `doc_scene`/matrix rendering machinery is REUSED for images). The dialog keeps only: «Формат листа» (Task 10), the path field («Обзор…», default `*.docx`, Task 12 memory), «Экспортировать»/«Отмена».

1. **Embedded pandoc:** copy `D:\ProgrammzD\UtilitiezD\Pandoc\pandoc.exe` → `runtime\pandoc\pandoc.exe` (do it once with a script; never depend on `D:\ProgrammzD\`). The export runs `runtime\pandoc\pandoc.exe` with `--reference-doc=eta\export\reference.docx` over a generated Markdown/HTML intermediate. If pandoc is missing, the dialog shows a clear Russian error.
2. **`reference.docx` derived from the GOST donor ONCE (build-time, not per export):** starting from `D:\TrashD\(К1) Ф3.6, ФОК Донецк.docx`, keep styles.xml (Times New Roman body, blue headings #2E74B5 levels 1–3 + italic sub-styles), page setup (sectPr) and headers/footers WITH the GOST frames and the small bottom stamps, strip the foreign project body (document.xml) to an empty body. Document how the template was produced in the report; commit `eta\export\reference.docx`.
3. **Document structure (LOCKED):**
   - **Title page** (from the reference title-page frame): heading **«Расчет частоты возникновения пожара»** 18 pt + beneath it **«Куджи v<version> от dd.mm.yyyy»** 12 pt. Nothing else (no stamp fields to fill).
   - **Оглавление:** a REAL Word TOC field (updatable via right-click → «Обновить поле») – insert the field in the docx post-processing step (pandoc output + a small OOXML injection into document.xml, or an equivalent approach you validate); do NOT try to pre-populate page numbers – the customer updates the field himself.
   - **«Нормативные ссылки и справочные данные»** – per Task 9 (variant Б).
   - **«Расчет частоты возникновения пожара»** – hierarchy following the OBJECT tree, branches without расчётные участки/установки omitted: `Территория «name»` → `Здание «name»` → `Помещение «name»` → `Участок «name»` → `Параметры расчета` (the parameter table `Параметр | Значение` in the reference style: only the type-relevant S/L/V line, функциональное назначение, молниезащита, вероятности присутствия, Kσ (Task 4 rules), «Огненный шар: включен» only when on) and `Исходные данные` (table `Событие | Величина | Источник`, no brackets, «–» for empty, flow-scope suffixes on ГС rows) → `Результаты расчета` (substituted formula lines `Q_j = … = … год⁻¹` in engineering notation + `Q_В = Σ Q_i · Kσ = … год⁻¹`, then the sum across all owners). `Наружная установка «name»` hangs directly under `Территория` with the same `Параметры расчета`/`Результаты расчета`. Heading levels mirror the depth (H2 territory → H5 участок blocks; sub-blocks as styled headings per the template).
   - **«Логическое дерево событий»** – for EACH расчётный участок/наружная установка (LOCKED): ONE schema image (all its trees together, rendered from `doc_scene` to PNG ~300 DPI, fitted to the chosen page format width) and ONE matrix table (Word table, headers from `matrix.py`, all scenario rows of that owner, totals row `Q_В = …`; the current measured-row/wrap logic is reused conceptually – Word wraps natively).
   - No «Объект расчёта», no project/date line, no «Исполнитель/Дата» IN THE TEXT (the GOST stamps coming from the template headers/footers stay as the donor has them).
4. **Version/date line** on the title page reads `__version__` live.
5. **Tests:** gesture – export a demo project; assert the .docx exists and is a valid zip; unzip `word/document.xml` and assert: the title strings, the TOC field presence, heading texts for each hierarchy level present, «Огненный шар» conditional logic, no `[` around a known source, `Q_В` present, the schema images count = owners count. Smoke – the builder's content model (pure functions: structure tree from objects+trees, sources list per variant Б). Replace old PDF blocks (36's PDF part, 52) accordingly.
6. **QA:** `visual_qa_runner.py` exports the demo DOCX, converts it to PDF via Word COM (headless `Word.Application` … `ExportAsFixedFormat`), renders pages (the QPdfDocument render path may be reused) to `qa_docx_page1.png` (+ 2–3 more pages incl. the sources page and a schema page). Vision review: GOST frame present, blue headings, clean tables, readable schema images, TOC page present. Word COM in offscreen runs: keep the QA step guarded (skip gracefully with a warning if COM is unavailable), because COM needs an interactive desktop session.
7. The status-bar hint after export: «DOCX: <path>».

## TASK 12. LAST-FOLDER MEMORY FOR ALL FILE DIALOGS (LOCKED)

One QSettings key `ui/last_dir`, updated after every successful save/open/export (the folder of the chosen path). `_save_project`, `_open_project_dialog`, and the export dialog prefill from it (fallback chain: last_dir → project dir → Desktop). Applies across restarts. Tests: gesture – set the hermetic ini value, open the export dialog, assert the prefilled folder; save a project via the seam, assert the key updated. QA: screenshot №2 defect gone.

## TASK 13. HELP BUTTON «?» IN «БАЗА ДАННЫХ»

Next to the «Закрыть» button in the «База данных» window add a round «?» icon button; clicking it opens an information window with a SHORT instruction on using the «База данных», including the basics of editing and FORMULA FORMATTING so that formula entries look like mathematical formulas.
1. **Button:** a vector glyph in the existing `icons.py` style (circle + «?», ICON_STROKE, registered in `ICON_PALETTE` – the smoke icon-coverage block must accept it), flat canon, tooltip «Справка по работе с базой данных», placed to the LEFT of «Закрыть» in the bottom button row.
2. **Window:** a simple modal information dialog (or non-modal window – your call, flat canon); the CONTENT is built by a testable seam function `_help_text() -> str` (HTML via `theme.math`/`math_text` where formulas are shown), so tests never touch `exec`. Title «Справка: База данных». Width comfortable for reading (~560–640 px), scrolling allowed.
3. **Content (Russian, canon, SHORT – one screenful, numbered sections):** (1) что такое «База данных»: вкладки, записи, счетчики использования, предупреждения при удалении занятых записей; (2) добавление/редактирование/удаление записей и источников (включая новую вкладку «Источники» из Задачи 9); (3) **форматирование формульных записей** – the ACTUAL mini-notation supported by the app, documented from the real code (`math_text.py`/`theme.math`: subscripts like `F_зд`, `N_у.м`; superscripts; «·» multiplication dot; engineering numbers with comma mantissa «9·10⁻⁵»; the caret syntax `1,02^-6` accepted by numeric editors via `numfmt.parse_eng`) with «before → after» examples – EVERY example must be verified by calling `math()`/`parse_eng()` in the smoke test, never invent notation that the renderer does not support; (4) как записи попадают в расчет и отчет (выбор причин в инспекторе, реестр источников → раздел «Нормативные ссылки и справочные данные»).
4. Inventory first: read `math_text.py` and list what it actually converts (subscripts `_x`, which tokens map to `<sub>`), then write the help text to match reality exactly.
5. Tests: smoke – `_help_text()` is non-empty, contains the section headings, and every formula example it shows round-trips through `math()` producing the promised markup; gesture – the «?» button exists next to «Закрыть», `_help_text()` contains «Источник» and a verified formula example; the dialog opens via the seam (no exec).
6. QA: open the help in `visual_qa_runner.py`, save `qa_kb_help.png`, vision review (readable, math renders as formulas, no overflow).

---

## 6. LOCKED DECISIONS (Q&A round before this session – normative, not to re-ask)

1. (T11) One project = ONE DOCX; the PDF export is fully abolished; the format selector sizes the embedded schema images only.
2. (T11) Embedded pandoc = a copy of `D:\ProgrammzD\UtilitiezD\Pandoc\pandoc.exe` (3.4) into `runtime\pandoc\pandoc.exe`.
3. (T11) Title page: YES, simplified – «Расчет частоты возникновения пожара» 18 pt + «Куджи v… от dd.mm.yyyy» 12 pt; then the TOC. No stamp fields to fill.
4. (T2) Failures confirmed on the real desktop via run_app.cmd; Alt+Ф does NOT open «Файл»; Ctrl+N/O work in both layouts. Diagnose with instrumented logging before fixing.
5. (T12) All save/open/export dialogs remember the last folder, persisted across restarts.
6. (T9) Sources registry in «База данных» with auto-migration of existing `source` strings (dedup), KB `meta.version` → «6.2».
7. (T9) Report section «Нормативные ссылки и справочные данные» = ONLY registry entries bound to records used in the calculation (variant Б); used-but-unbound methodics tables are SKIPPED.
8. (T11) TOC = a real Word field updated by the user (right-click → «Обновить поле»); no pre-computed page numbers.
9. (T11) Export dialog after the rework: «Формат листа» (6 combos) + path + «Экспортировать»; no «Содержимое», no report toggle.
10. (T11) Per расчётный участок/наружная установка: ONE schema image (all its trees) + ONE matrix table (all its rows + Q_В total).

## 7. FINAL DELIVERABLES

1. All thirteen tasks implemented; `smoke_test.py` + `gesture_test.py` green (updated blocks: version «6.7»; «База данных» strings; PDF blocks replaced by DOCX blocks; new blocks for splitter memory, real-layout key paths incl. text()-based conversion and app-level Space pan, sources registry, formats combo, last-folder memory, DOCX structure, DB help).
2. Version → **6.7.0**; KB `meta.version` → **«6.2»** (with migration); README updated (panel memory, shortcuts/Space fixes, «База данных», sources registry, unified DOCX export incl. pandoc embedding and the GOST template, formats, last-folder memory; PDF-export sections removed).
3. `eta\export\reference.docx` committed; `runtime\pandoc\pandoc.exe` present (note in the report how both were produced; do NOT commit the pandoc binary into any repository – it lives only in the working tree).
4. `old prompts (done prompts)\REPORT_SESSION_18.md` (English): per-task root causes (especially the REAL-Windows key-delivery findings from the instrumented log and the customer's manual confirmation verdict), files touched, before→after for every changed user-facing string, the DOCX pipeline description (template derivation, pandoc invocation, TOC field injection, image rendering, Word COM QA), test/QA evidence, known issues.

## 8. KNOWN PITFALLS (do not step on these again)

- Real Windows ≠ offscreen QTest for key events: delivery shape must be measured (Task 2 log) before fixing; keep both test paths green.
- Qt shortcut dispatcher matches events of the ACTIVE window only – offscreen key tests need `QApplication.setActiveWindow(w)` (session-17 lesson).
- QShortcutMap ambiguity: ApplicationShortcut actions created per-window multiply and fire the wrong window – the «Правка» actions are ONE shared set on the QApplication; keep new global actions in that pattern (`_ensure_edit_actions` + `_edit_target`).
- QPdfWriter traps (historical now that PDF dies, relevant while qa renders PDFs via Word): one painter per document; `setPageLayout` after painted pages rewrites all MediaBoxes.
- QFontMetricsF under a scaled painter returns LOGICAL pixels (= mm at ×10) – do not multiply/divide by 10 (session-17 matrix lesson; matters for the PNG DPI rendering too).
- `QTextDocument.print_` in PySide6 (underscore); a second painter session on a QPdfWriter rewrites the file.
- Word COM needs an interactive session – guard the QA conversion; never block offscreen runs on COM.
- Pandoc must run from the EMBEDDED path `runtime\pandoc\pandoc.exe` (no PATH dependency, no `D:\ProgrammzD\` at runtime); a missing binary is a clear Russian message, never a crash.
- DOCX is a zip: post-process `word/document.xml` with byte-safe Python (never pwsh string cmdlets); preserve encoding; validate by reopening as a zip after injection.
- QSettings in tests: hermetic ini; splitter save uses debounced timers – in tests invoke the slot synchronously, do not wait real time.
- Stale QTreeWidgetItem references: re-fetch rows after every rebuild; itemAt check before clicking; clamp click X into the viewport.
- Marquee/press points must be verified against item geometry (start on EMPTY space; the annotation plate occupies the space above a tree).
- Space hold = keyPress+keyRelease (keyClick resets the flag); `isAutoRepeat()` must not toggle the flag.
- Cyrillic/KB edits: byte-safe temporary Python scripts only; no em-dash anywhere; KB `meta.version` is bumped ONCE («6.2») with load-time migration for old files.
- `run_app.cmd` manual start is the user's habit – never launch it in automated batches; every manual verification loop is a short numbered Russian instruction to the customer.
