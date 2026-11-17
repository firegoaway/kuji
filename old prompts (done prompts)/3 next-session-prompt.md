# PROMPT: Freq ETA — единые жесты окна документа, опциональный порог отсечения, сворачиваемая палитра, память интерфейса

Ты — Senior Desktop Application Engineer (PySide6/Qt6). Продолжаешь развитие ГОТОВОГО проекта «Freq» — конструктора логических деревьев событий (ETA) по Приказу МЧС России № 533. Всё, описанное ниже в разделах «Состояние» и «Карта кода», УЖЕ РАБОТАЕТ и покрыто тестами — это твоя стартовая база, её не надо заново исследовать и нельзя ломать. Твоя задача — четыре точечные доработки UX (Задачи 1–4).

---

## 0. СОСТОЯНИЕ ПРОЕКТА (фиксация на 07.11.2026)

- Реализовано и зелёное: математическое ядро (инварианты ΣP=1, ΣQ=Q_исх), Smart Linking, авто-раскладка (tidy-tree + колонки эшелонов + Manhattan), PDF A3/A2 векторный (WYSIWYG), поэлементная интерактивная сцена, жесты вьюпорта (зум/панорама/рамка/перетаскивание узлов с `manual_pos`), окно документа над вьюпортом (пока с прокруткой, не зумом — меняется в Задаче 1), сплиттеры + QSettings (геометрия окна, состояния сплиттеров), Visual QA-петля glm-5.3-flash.
- Тесты на момент передачи: `smoke_test.py` — PASS; `gesture_test.py` — PASS (12 сценариев); `run_qa.cmd` — артефакты собираются, вердикт vision `"pass": true` (2 итерации из 4).
- Версия окружения: Python 3.14.3 + PySide6 6.12.0 (embed, внутри проекта).

## 1. АБСОЛЮТНЫЕ ПУТИ И КОМАНДЫ (рабочая шпаргалка)

| Что | Путь / команда |
|---|---|
| Корень проекта | `D:\ProgrammzD\GraphiczD\Freq` |
| Интерпретатор (единственный!) | `D:\ProgrammzD\GraphiczD\Freq\runtime\python\python.exe` |
| Запуск GUI | `D:\ProgrammzD\GraphiczD\Freq\run_app.cmd` |
| Visual QA (offscreen) | `D:\ProgrammzD\GraphiczD\Freq\run_qa.cmd` (сам ставит `QT_QPA_PLATFORM=offscreen`, `QT_QPA_FONTDIR=C:\Windows\Fonts`) |
| Тест ядра | `runtime\python\python.exe smoke_test.py` |
| Тест жестов (живые события мыши) | `$env:QT_QPA_PLATFORM='offscreen'; $env:QT_QPA_FONTDIR='C:\Windows\Fonts'; runtime\python\python.exe gesture_test.py` |
| Артефакты QA | `D:\ProgrammzD\GraphiczD\Freq\qa_artifacts\` — `qa_window.png` (всё окно), `qa_canvas.png` (вьюпорт), `qa_docview.png` (окно документа), `qa_sheet.png` (лист 2×), `qa_export_a3.pdf` + `qa_pdf_page1.png`/`qa_pdf_page9.png`, `qa_stats.json` |
| База знаний | `D:\ProgrammzD\GraphiczD\Freq\eta\knowledge\knowledge_base.json` (правится вручную, приложение подхватывает на старте) |
| Проекты пользователя | `*.etajson` (JSON, формат `{"app":"eta-533","format":1,"name","threshold","trees":[...]}`) |

Визуальная проверка артефактов — через vision-модель **glm-5.3-flash** (строгий промпт Principal UI/UX Engineer, ответ строго JSON `{"pass": bool, "issues": [...]}`), до 4 итераций до `"pass": true`.

## 2. КАРТА КОДА (что где лежит и как называется)

### `eta/core/model.py` — ядро (не ломать; разрешённые расширения — см. Ограничения)
- `SAFE/HAZARD/CUTOFF` — статусы листьев. `SplitSpec` (p_success, favorable/unfavorable_label, stage_level, value_tag, source, justification).
- `Node`: `id` (hex10), `kind "init"|"branch"`, `title`, `level` (эшелон события, СОЗДАВШЕГО узел), `q`, `branch_label/branch_p/branch_success`, `path_tags: frozenset`, `split`, `children [success, failure]`, `q_spec`, `cut_off`, `status`, `scenario_no`, `manual_pos: (x,y)|None`.
- `TreeModel(QObject)`: сигнал **`changed`** (любая правка → `recalculate()` → emit); методы `add_root(tmpl)`, `add_split(node, tmpl)` (автобифуркация P/1−P, возвращает success-ветвь), `remove_subtree`, `set_split_p(node, p, ...)`, `set_root_q`, `set_node_title`, **`set_threshold(value: float)`** ← расширяется в Задаче 2, `reset_manual_positions()`, `all_nodes()`, `node_by_id()`, `leaves()`, `scenarios()` (список dict: `no/path/q/status/status_text`, сортировка hazard-first по Q↓), `total_hazard_q()`, `apply_preset(preset)`, `clear()`. Поле `threshold: float = kb.meta["default_cutoff"]` (в БЗ = 1e-8) ← меняется в Задаче 2.

### `eta/core/layout.py` — геометрия (общая для экрана и PDF)
- **`compute_layout(model, kb) -> Layout`**: `columns: list[Column(level,x,width,title)]` (6 колонок 0–5, x слева направо), `header_rect`, `node_geos: dict[id -> NodeGeo]` (`rect`, `title_lines`, `q_text`, `badge`, `status`, `kind`, `cut_off`, `is_leaf`), `edge_geos: list[EdgeGeo]` (`parent_id, child_id, points` — 4 QPointF Manhattan, `label: LabelGeo(rect,line1,line2,success)`, `cut_off, success`), `scene_rect`, `tree_bottom`, `row_cuts` (границы строк для PDF-тайлинга).
- Особенности: `manual_pos` перекрывает позицию узла, НЕ влияя на tidy-центры остальных; метка ветви перетащенного узла уходит к вертикальному сегменту; при зазоре ≤ 48 px `mid_x = p_right + 24`; `scene_rect`/`row_cuts`/`tree_bottom` учитывают ручные позиции.

### `eta/ui/render.py` — ОБЩИЙ рендерер (экран и PDF — один код, WYSIWYG)
- `RenderState` (`selected_node`, `selected_edge`, `selected_nodes: set` — рамочный выбор, `hover_node`, `hover_valid`, `mono_values`).
- Функции (публичные, ими красятся items): `draw_diagram`, `draw_column_grid`, `draw_header`, `draw_edge`, `draw_edge_label` (метки P — верхний слой, белая плашка), `draw_node`.

### `eta/ui/canvas.py` — сцены + жесты вьюпорта
- Константы: `MIME_TEMPLATE`, z-слои `Z_BG<Z_GRID<Z_HEADER<Z_EDGE<Z_NODE<Z_LABEL<Z_HINT`, зум `ZOOM_STEPS=6`, `ZOOM_PER_STEP=1.035`, `ZOOM_MS=130`, `MIN_SCALE=0.05`, `MAX_SCALE=8.0`, `MOVE_THRESHOLD_PX=4`.
- Items: `NodeItem` (pos = верхний левый угол `geo.rect`; флаги Movable|Selectable|SendsGeometryChanges; `set_geo()`), `EdgeItem` (`set_edge()`, shape — «толстая» полилиния ±7px), `EdgeLabelItem`, `HeaderItem`, `GridItem`, `SheetBackgroundItem`, `HintItem` (плашка причины запрета при DnD).
- **`DiagramController(model, kb)`**: строит из ОДНОЙ раскладки ДВЕ сцены — `work_scene` (вьюпорт, БЕЗ шапки) и `doc_scene` (лист: фон+сетка+`HeaderItem`+дерево; ИМЕННО она передаётся в PDF). Методы: `rebuild()` (полная пересборка, подключена к `model.changed`), `sync_positions()`, `apply_manual_positions(mapping)` (drag: `manual_pos` → пересчёт раскладки на лету), `content_rect()`, `node_at()/edge_at()` (хит-тест), `set_selection()/set_edge_selection()/clear_selection()`, `set_drag_hover()`, флаг **`freeze_scene_rect`** (при drag sceneRect заморожен — иначе граница контента «уводит» карту под курсором; НЕ УДАЛЯТЬ).
- **`TreeCanvas(QGraphicsView)`**: сигналы `node_selected(Node|None)`, `edge_selected(parent, child)`; состояния `IDLE/PANNING/RUBBER/MOVING_NODE`; `wheelEvent` → `_animate_zoom(total)` (плавный зум к курсору); СКМ-панорама через значения скрытых скроллбаров; ЛКМ: `_begin_node_press` (Ctrl/Shift — переключение в выделении, групповое перетаскивание, дельта через обратный масштаб, НЕ mapToScene), `_begin_rubber/_finish_rubber` (QRubberBand, Ctrl — добавить к выделению); `contextMenuEvent` (барьеры/удаление/сброс позиции); DnD: `dragEnter/Move/Leave/dropEvent` (валидатор → `add_split` → `select_node` + `center_on_node`); `fit_tree()` (cap 1.15), `select_node()`, `clear_selection()`.

### `eta/ui/docview.py` — окно документа (меняется в Задаче 1)
- `DocumentView(controller)`: сцена `controller.doc_scene`; NoDrag; скроллбары AsNeeded; сейчас `wheelEvent` = вертикаль, Shift+колесо = горизонталь, зума нет; `fit_width()` («вписать по ширине», кнопка в шапке окна документа); `_on_model_changed` пере-вписывает при изменении ширины листа; ЛКМ/ПКМ inert.

### `eta/ui/main_window.py` — компоновка
- `THRESHOLDS = [1e-6…1e-12]` + `THRESHOLD_LABELS` (строка ~22) ← расширяется в Задаче 2.
- `MainWindow(kb, restore_ui=True)`: `split_h` (палитра ≥240 | центр | инспектор ≥320, stretch центра 1) → центр = `split_v` (окно документа ≥120 над `canvas` ≥300, stretch вьюпорта 1); `self.canvas = TreeCanvas(model, kb)`, `self.doc_view = DocumentView(canvas.controller)`; тулбар: Новый/Открыть/Сохранить/Показать всё/**Авто-раскладка**/порог (`threshold_combo`)/Экспорт PDF — собирается в `_build_toolbar()`; `_export_pdf` берёт `canvas.controller.layout` и `canvas.controller.doc_scene`; `_update_status` — статус-бар; QSettings: `_restore_geometry()` (геометрия, до show), `showEvent()` (СПЛИТТЕРЫ — только после первого показа!), `_save_geometry()` в `closeEvent`; `_persist_ui=False` у QA (параметр `restore_ui=False`).
- Связи: `canvas.node_selected → inspector.show_node/show_empty`, `canvas.edge_selected → inspector.show_edge`, `palette.add_init_requested → _add_init`, `palette.preset_applied → _apply_preset`, `inspector.goto_node_requested → _goto_node` (select + center_on_node), `model.changed → _update_status`.

### `eta/ui/palette_panel.py` — палитра (меняется в Задача 3)
- `GROUP_TITLES` (ключи `"init"`, `1…5`); `EventCard` (drag по `MIME_TEMPLATE`, двойной клик → `activated`); `GroupHeader(QLabel)`; `PalettePanel`: поиск (`search.textChanged → _refill`, фильтр по title/tags), пресеты (кнопки из `kb.presets`), `QScrollArea` + `container` с `content` QVBoxLayout; `_refill()` пересобирает группы: init-события + `kb.barriers` сгруппированные по `stage_level` 1–5; сигналы `add_init_requested`, `preset_applied`.

### `eta/ui/inspector_panel.py` — инспектор
- `InspectorPanel(model, kb)`: `tabs` (QTabWidget): «Инспектор» = `inspector_scroll` (QScrollArea с `#inspectorForm`, форма строится в `form_host`: название, Q_исх (режимы freq_mode), редактор барьера (P + значения из `kb.values_for_tag(value_tag)` по двойному клику, обоснование), инфо листа) и «Сценарии» (сводка ΣQ + QTableWidget №/сценарий/Q_j/статус, `refresh()` на `model.changed`); сигнал `goto_node_requested`. Активная вкладка — `tabs.setCurrentIndex(...)` (для Задачи 4).

### `eta/core/serializer.py`
- `save_project/load_project`; узел → dict (`manual_pos` как `[x,y]`, если задан); `threshold` — число ← в Задаче 2 добавить None (null). Старые проекты: поле отсутствует → брать из файла/дефолт.

### `eta/core/kb.py` + `knowledge_base.json`
- `KnowledgeBase()`: `meta` (в т.ч. `default_cutoff: 1e-8`), `echelons` (0–5: title/short), `initiating_events`, `barrier_events` (stage_level, tags, p_success, p_source, value_tag, required_parent_tags, incompatible_tags, on_success_tags/on_failure_tags, favorable/unfavorable_label), `value_library`, `presets` (`init` + `barriers`). Методы: `initiating_by_id`, `barrier_by_id`, `values_for_tag`, `echelon_title/short`.

### `eta/export/pdf_export.py` + `eta/ui/dialogs.py`
- `ExportSpec(path, size_id "A3"|"A2", fit_one_page, min_pt=8)`; `plan_export(scene_rect, spec, columns_x, row_cuts, n_rows)`; **`export_pdf(scene, layout, model, spec)`** — сцена = `controller.doc_scene`; тайлинг: колонки не режутся, вертикаль — по `row_cuts`; легенда на каждом листе, итоговая таблица на последнем; гарантия кегля ≥ 8 pt. `PdfExportDialog(layout, parent, suggested_name)` — предрасчёт листов/кегля.

### `eta/ui/theme.py`
- Палитра: APP_BG #F8FAFC, PANEL_BG #FFFFFF, BORDER #CBD5E1, ACCENT #2563EB, SAFE #16A34A, HAZARD #DC2626, CUTOFF #94A3B8; кегли F_TITLE/F_META/F_MONO/F_HEADER/F_SMALL; сетка PAD_H/PAD_V/MARGIN/HEADER_H/HGAP/VGAP_ROW; `ui_font()/mono_font()`, `fmt_prob/fmt_q/fmt_q_full`, `parse_prob/parse_sci`; QSS (в т.ч. `QSplitter::handle` 6px с hover/pressed, `#panel`, `#inspectorForm`, `QComboBox[inactive="true"]` — добавить в Задаче 2).

### Тесты (обновлять вместе с кодом!)
- `smoke_test.py`: инварианты пресета, валидатор, реактивный P, раскладка (4 точки на ребро, колонки по возрастанию), сериализация. **Строка `assert model.threshold == 1e-8` — обновить в Задаче 2.**
- `gesture_test.py`: 12 сценариев через `QApplication.sendEvent(..., QMouseEvent/QWheelEvent)` в `win.canvas.viewport()` + `pump(ms)` (анимации идут по стен-часам — нужен sleep-цикл): 1 плавный зум, 2 колесо не скроллит (проверка на клампе 8.0), 3 СКМ, 4 клик-выбор, 5 drag (ожидание через обратный масштаб), 6 авто-раскладка, 7 рамка, 8 клик по ветви (точка `p_right+10, p_cy`), 9 окно документа (колесо/Shift) ← ПЕРЕПИСАТЬ в Задаче 1, 10 сериализация manual_pos, 11 пустой проект (вьюпорт чист: в work_scene только HintItem z=6), 12 QSettings (отдельное имя приложения, размер под клампинг offscreen-экрана 800×800).
- `visual_qa_runner.py`: `MainWindow(kb, restore_ui=False)` + 2 пресета + `b-sps`/`b-soue` (38 узлов) → снимки → PDF → `qa_stats.json`.

## 3. ПОТОКИ ДАННЫХ (как что работает)

1. **Правка модели** (палитра/DnD/инспектор/порог) → метод `TreeModel` → `recalculate()` → сигнал `changed` → `DiagramController.rebuild()` (обе сцены из одной раскладки) → `DocumentView._on_model_changed` (пере-fit при изменении ширины листа) + `InspectorPanel.refresh()` + `_update_status()`.
2. **Drag узла** (только вьюпорт): `apply_manual_positions` → `compute_layout` → `sync_positions` (лёгкий апдейт items, БЕЗ `model.changed`) → обе сцены обновлены мгновенно → на release разморозка sceneRect.
3. **PDF**: тулбар → `PdfExportDialog` (предрасчет через `plan_export`) → `export_pdf(controller.doc_scene, controller.layout, model, spec)`.
4. **QSettings** (`QSettings()`; организация задана в `main.py`: `setOrganizationName("GraphiczD")`, `setApplicationName("Freq ETA 533")`): запись — `closeEvent` (+ осмысленные моменты), чтение — геометрия в `__init__`, сплиттеры в первом `showEvent`.

Ключи QSettings: существующие `ui/geometry`, `ui/split_h`, `ui/split_v`; добавить в Задаче 4: `ui/threshold` (число или `"none"`), `ui/palette_groups` (список свёрнутых: `init`,`lvl1`…`lvl5`), `ui/inspector_tab` (int), `ui/doc_scale` (`"fit"` или число), `ui/last_dir` (строка).

## 4. ИЗВЕСТНЫЕ ГРАБЛИ (не наступай повторно)

- Offscreen: обязательно `QT_QPA_FONTDIR=C:\Windows\Fonts`; предупреждение `FT_New_Face failed with index 0 : 2` — БЕЗВРЕДНО, игнорировать.
- Offscreen-экран 800×800: `restoreGeometry` клампит размеры — в тестах не сравнивай абсолютные размеры окна; сплиттеры восстанавливай ТОЛЬКО после первого `showEvent`, иначе первая раскладка затирает.
- Долгий caption у окна документа без `setWordWrap(True)` раздувает минимальную ширину центральной зоны.
- Конструктор `QWheelEvent` в PySide6: `(pos, globalPos, pixelDelta, angleDelta, buttons, modifiers, phase, inverted)` — кнопки и модификаторы не перепутай.
- `mapToScene` во время drag ненадёжен (замороженный sceneRect) — дельта перетаскивания считается через обратный масштаб `transform().m11()`.
- Метки P обязаны оставаться верхним слоем (z `Z_LABEL`), белый фон плашки перекрывает линии.
- Запуск cmd-файлов из pwsh: `& "D:\...\run_qa.cmd"`; редирект `2>$null` в pwsh искажает `$LASTEXITCODE` — суди по текстовому выводу, а не коду.
- QA-раннер и тесты создают `MainWindow(restore_ui=False)` — не вводи побочные записи QSettings в этих режимах.

---

# ЗАДАЧА 1. ОКНО ДОКУМЕНТА — ТЕ ЖЕ ОРГАНЫ УПРАВЛЕНИЯ, ЧТО И ВО ВЬЮПОРТЕ

Просмотр листа с «чужой» прокруткой оказался неудобен. Приведи окно документа к единой матрице жестей вьюпорта.

Обязательно (вариант A):
- колесо (без модификаторов) — ПЛАВНЫЙ зум к точке под курсором (та же анимация: 6 микрошагов × 1.035, 130 мс, якорь под курсором, клампы 0.05–8.0);
- СКМ + движение — панорама XY (`ClosedHandCursor`), зум не сбивается;
- ползунки прокрутки остаются (AsNeeded) как вспомогательный орган;
- ЛКМ окно документа НЕ редактирует (read-only: выбор/перетаскивание — только в рабочем вьюпорте); ПКМ — ничего; Shift+колесо можно оставить горизонтальной прокруткой как бонус;
- «Вписать по ширине» (кнопка в шапке) и начальный вписанный масштаб сохраняются; после ручного зума resize НЕ пере-вписывает (уже так — не сломай).

Реализация: выдели общее (плавный зум + СКМ-панорама) в переиспользуемый миксин `eta/ui/gestures.py` (`ViewportGestures`), подключи к `TreeCanvas` И `DocumentView` — без дублирования анимации. Обнови подпись окна («колесо — зум, СКМ — панорама»). PDF-экспорт не меняется: источник — `doc_scene`, WYSIWYG сохраняется. ПЕРЕПИШИ сценарий 9 в `gesture_test.py` (зум вместо прокрутки) и прогони весь файл.

Опционально (вариант B, только если уложишься и не в ущерб A): переключатель «Лист / Матрица» в шапке окна документа. «Матрица» — дерево в табличном виде: колонки = эшелоны (заголовки те же, что у шапки листа: `kb.echelon_title`) + `Q_j` + статус; строки = терминальные сценарии (`model.scenarios()`, сортировка по Q↓); в ячейках метка ветви + P (моноширинно, `fmt_prob`), статус цветом (#16A34A/#DC2626/#94A3B8); клик по строке выбирает лист в инспекторе и вьюпорте. Матрица НЕ участвует в PDF. Не делаешь B — просто пропусти, A самодостаточен.

# ЗАДАЧА 2. ПОРОГ ОТСЕЧЕНИЯ — ОПЦИОНАЛЬНЫЙ («НЕТ» ПО УМОЛЧАНИЮ)

Где менять: `THRESHOLDS/THRESHOLD_LABELS` и `_build_toolbar()` в `eta/ui/main_window.py`; `TreeModel.threshold`/`set_threshold`/`_calc` в `eta/core/model.py`; QSS в `eta/ui/theme.py`; `smoke_test.py`; `eta/core/serializer.py`; `_update_status`.

- В комбобоксе первый пункт **«Нет»**, далее `1×10⁻² … 1×10⁻¹⁶` (15 значений, сгенерируй программно). Дефолт при запуске — «Нет» (если QSettings не вернули иное — Задача 4).
- Модель: `threshold: float | None`; `set_threshold(value: float | None)`; в `_calc` порог применяется только при не-None (None → `cut_off` всегда False, статус CUTOFF не возникает, все hazard-листья в расчёте ОФП). Инварианты не затрагиваются — это разрешённое расширение ядра.
- UX при «Нет»: комбобокс приглушённо-серый (текст #94A3B8) через динамическое свойство (например `setProperty("inactive", True)` + repolish + QSS-селектор `QComboBox[inactive="true"]`), но ОСТАЁТСЯ кликабельным — НЕ `setEnabled(False)`. Tooltip: «Порог отсечения неактивен (не применяется)». Подпись слева тоже можно приглушить.
- Статус-бар: «Порог: нет» / «Порог: 1×10⁻⁸».
- Сериализация: null ↔ «Нет»; старые проекты без поля порога открываются с порогом из файла.
- Обнови `smoke_test.py` (дефолт None + round-trip None→число→None) и, если нужно, легенду/сводку сценариев (при None строк «Отсечено» просто нет).

# ЗАДАЧА 3. ПАЛИТРА — РАСКРЫВАЮЩИЕСЯ ГРУППЫ ПО УРОВНЯМ

Где менять: `eta/ui/palette_panel.py` (`_refill()`, `GroupHeader`), QSS `theme.py`, память — Задача 4.

- Заголовок группы («Инициирующие события (уровень 0)», «Уровень 1 · Горючая среда», …) — кликабельный аккордеон: шеврон ▸/▾, название, счётчик карточек («8»); сворачивание скрывает карточки группы.
- Стиль Swiss Utilitarian: плоско, заголовок на #F8FAFC, 1px-граница, без скруглений/теней, курсор-рука на заголовке.
- Кнопки «Развернуть все» / «Свернуть все» в шапке палитры (компактные).
- Поиск: при непустом запросе группы с совпадениями авто-раскрываются; при очистке — возврат к сохранённому состоянию свёрнутости.
- Состояние групп переживает перезапуск (ключи `init`, `lvl1`…`lvl5`). Начальный дефолт — все развёрнуты.

# ЗАДАЧА 4. ПАМЯТЬ СОСТОЯНИЯ ИНТЕРФЕЙСА

Где менять: `eta/ui/main_window.py` (механизм QSettings уже есть — расширяй его), подключения в `palette_panel.py`/`inspector_panel.py`/`docview.py`.

Сохранять/восстанавливать (ключи см. раздел 3):
- геометрия окна + оба сплиттера (уже есть — не потеряй; сплиттеры после первого showEvent);
- порог отсечения (значение или «Нет»);
- свёрнутость групп палитры;
- активная вкладка инспектора;
- масштаб окна документа: `"fit"` или последний ручной коэффициент (применять после первого show, без скачков);
- последний каталог диалогов «Открыть…»/«Сохранить…»/«Экспорт PDF…» (стартовый каталог).

Требования: `restore_ui=False` по-прежнему отключает и чтение, и запись (QA/тесты детерминированы); запись — в `closeEvent` и в моменты выбора (порог/группа/вкладка); чтение — геометрия до show, остальное при первом показе.

# ПРИЁМКА (все пункты обязательны)

1. Окно документа: колесо — плавный зум к курсору (колесо НЕ прокручивает), СКМ — панорама без потери зума, «Вписать по ширине» работает; PDF/WYSIWYG не изменились.
2. Порог: дефолт «Нет», комбобокс серый но кликабельный; выбор из 1e-2…1e-16 мгновенно перекрашивает дерево и пересчитывает сценарии; ΣQ=Q_исх не зависит от порога; round-trip в `*.etajson`; статус-бар отражает.
3. Палитра: сворачивание в один клик, счётчики, «Развернуть/Свернуть все», авто-раскрытие при поиске, состояние переживает рестарт.
4. Память: всё из Задачи 4 восстанавливается после перезапуска (проверь тестом в духе сценария 12 `gesture_test.py` и вручную).
5. `smoke_test.py` — PASS (с обновлённым дефолтом порога); `gesture_test.py` — PASS (с переписанным сценарием 9).
6. `run_qa.cmd`: обновлённые `qa_window.png`, `qa_canvas.png`, `qa_docview.png`, страница PDF; визуальная проверка glm-5.3-flash (строгий промпт, JSON) — `"pass": true` (до 4 итераций).
7. В конце — краткий отчёт: что изменено, список файлов, результаты приёмки.

# ОГРАНИЧЕНИЯ

- Математическое ядро (`eta/core/model.py`) не менять, кроме разрешённых расширений: `manual_pos` (уже есть) и `threshold: None`. Валидатор и базу знаний не трогать.
- Архитектуру «один DiagramController → две сцены, PDF из doc_scene» сохранить; общий рендерер `render.py` — по-прежнему один для экрана и PDF.
- Стиль Swiss Utilitarian (`eta/ui/theme.py`): плоско, 1px-границы, моношрифт чисел, сетка 8px; никаких градиентов/теней/декоративных скруглений.
- Никаких TODO-заглушек: только полный работающий код.
- Работай из embed-окружения `runtime\python` (единственный интерпретатор проекта).

Порядок работы: (1) миксин жестов + окно документа (+ перепись сценария 9); (2) опциональный порог (+ smoke); (3) сворачиваемая палитра; (4) память состояния (инфраструктура по ходу, финальная проверка в конце); (5) приёмка + Visual QA. После каждой задачи гоняй оба теста.
