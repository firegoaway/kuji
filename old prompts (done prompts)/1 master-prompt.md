[06.11.2026 15:39] ChatGPT + Claude + Nano Banana: Чтобы ИИ-агент (Cursor, Claude Code, Windsurf) написал рабочий инженерный инструмент, а не просто «рисовалку квадратиков», в промпте нужно жестко задать четыре вещи:
1. Топологию дерева событий (ETA): рост строго слева направо по уровням-барьерам, а не сверху вниз.
2. Математический инвариант: сумма условных вероятностей исходов из одного узла всегда равна 1, а частота конечного сценария считается как произведение базовой частоты на вероятности вдоль ветви:
Q_j = Q_{\text{исх}} \cdot \prod_{k=1}^{n} P_k
3. Матрицу совместимости (умные связи): каждому событию присваивается уровень (эшелон), чтобы пользователь физически не мог поставить «Сработку АУПТ» раньше «Образования горючей среды».
4. Векторный рендер под ГОСТ/СП: нативный экспорт в векторный PDF форматов A3 и A2 с автокомпоновкой узлов (алгоритм Dagre или Reingold-Tilford), чтобы ветки никогда не пересекались.
Ниже — готовый системный промпт. Скопируй его и отправь ИИ-агенту.
# ROLE & OBJECTIVE
Ты — Senior Desktop Application Architect и инженер по пожарной безопасности. 
Разработай десктопное приложение с графическим интерфейсом (GUI) для автоматизированного построения Деревьев событий (Event Tree Analysis, ETA) по Методике расчета пожарного риска (Приказ МЧС России № 533, Приложение № 2) с экспортом в векторный PDF форматов A3 и A2.

# TECH STACK
- Язык: Python 3.11+
- GUI и векторная сцена: PySide6 (Qt6) — использовать `QGraphicsScene`, `QGraphicsView` для интерактивного холста с поддержкой масштабирования (zoom/pan) и Drag-and-Drop.
- Экспорт в PDF: `QPdfWriter` / `QPagedPaintDevice` (строго векторный рендер без растрирования шрифтов и линий) с поддержкой преднастроенных листов ISO A3 (420x297 мм) и ISO A2 (594x420 мм), альбомная ориентация.
- Хранение базы знаний и проектов: локальный JSON / SQLite.

# CORE DOMAIN LOGIC (МЕТОДИКА № 533)
1. **Структура дерева (слева направо):**
   Дерево растет строго горизонтально слева направо по хронологическим эшелонам (уровням):
   - Уровень 0: Инициирующее событие (ИС) — содержит базовую частоту в год (`Q_init`, например `1.2e-3`).
   - Уровень 1: Выход вещества / образование горючей среды.
   - Уровень 2: Сработка систем противоаварийной защиты (ПАЗ / отсекающая арматура).
   - Уровень 3: Мгновенное воспламенение.
   - Уровень 4: Отложенное воспламенение / дрейф облака.
   - Уровень 5: Сработка систем пожарной автоматики (АУПТ, ВПВ, ПДЗ).
   - Уровень 6 (Листья дерева): Конечные исходы (Безопасный исход / Сценарий пожара № N с итоговой частотой `Q_j`).

2. **Автоматическая бифуркация и математика:**
   - Когда пользователь перетаскивает событие-барьер на узел, система автоматически создает развилку из двух ветвей:
     1) Благоприятное событие (Успех барьера / Отсутствие зажигания) с условной вероятностью `P`.
     2) Неблагоприятное событие (Отказ барьера / Зажигание) с условной вероятностью `1 - P`.
   - При изменении вероятности одной ветки вторая пересчитывается автоматически (`P_2 = 1.0 - P_1`).
   - Частота каждого узла и конечного сценария пересчитывается реактивно: произведение частоты инициирующего события на все условные вероятности вдоль пути от корня к листу.
   - Ветви с частотой ниже заданного порога отсечения (например, `1e-8`) визуально помечаются серым пунктиром как отсеченные («Не учитывается в расчете ОФП»).

3. **Умная валидация связей (Smart Linking):**
   - У каждого шаблона события в Базе Знаний есть параметр `stage_level` (от 0 до 5) и список `allowed_parents` / `incompatible_tags`.
   - При попытке перетащить событие на узел (Drop) система проверяет:
     - `new_event.stage_level > parent_node.stage_level`
     - логическую совместимость (например, нельзя добавить ветку «Отложенное воспламенение» после ветки «Мгновенное воспламенение произошло = Да»).
[06.11.2026 15:39] ChatGPT + Claude + Nano Banana: - При наведении (Drag Hover) подсвечивать валидные узлы зеленым контуром, а невалидные — красным с всплывающей подсказкой причины запрета.
KNOWLEDGE BASE (ВСТРОЕННАЯ БАЗА ЗНАНИЙ)
Создай предзаполненный файл knowledge_base.json с типовыми событиями по Приказу МЧС № 533 и справочникам:
- Типовые инициирующие события по помещениям и оборудованию с табличными частотами.
- Типовые условные вероятности сработки/отказа барьеров (АУПТ, ПАЗ, наличие источника зажигания, мгновенное/отложенное воспламенение) с указанием источника (таблица/пункт Методики).
- Возможность в 1 клик применить значение из базы или ввести пользовательское с текстовым обоснованием.
UI / UX REQUIREMENTS (МИНИМУМ ДВИЖЕНИЙ)
1. Левая панель (Палитра событий и База знаний):
- Сгруппированные по эшелонам карточки событий с поиском и фильтром.
- Кнопки быстрых пресетов («Типовая ветка: Помещение с ГЖ», «Типовая ветка: Склад твердых ГМ») — строят готовый каркас дерева в 1 клик.
2. Центральный холст (Интерактивное дерево):
- Автоматическая раскладка (Auto-layout алгоритм без пересечения ребер): при добавлении/удалении узла дерево само раздвигает ветки по вертикали и выравнивает уровни по горизонтали (шапка с названиями эшелонов сверху, как в классическом ETA).
- На каждом узле и ребре крупно и читаемо отображаются: название события, условная вероятность P и накопленная частота ветви в экспоненциальном формате (1.5 × 10^-6 год^-1).
3. Правая панель (Инспектор узла и Сводка сценариев):
- Редактирование выбранного узла, выбор вероятности из справочника.
- Итоговая таблица всех терминальных сценариев (Сценарий 1..N, Итоговая частота Q_j, статус: В расчет ОФП / Безопасный / Отсечен по частоте).
PDF EXPORT ENGINE (A3 / A2 READY)
Реализуй модуль экспорта в PDF:
- Выбор формата листа (A3 или A2) и масштабирования «Вписать всё дерево на 1 лист с сохранением пропорций».
- Отрисовка шапки эшелонов в верхней части листа, четких ортогональных линий связей (Manhattan routing), рамок узлов, легенды и итоговой таблицы частот сценариев в правом нижнем углу.
- Гарантированная читаемость шрифтов при печати на A3/A2 (минимальный кегль в пересчете на печать — не менее 8 pt).
DELIVERABLES & EXECUTION PLAN
Действуй пошагово:
1. Сначала спроектируй архитектуру проекта и структуру knowledge_base.json.
2. Реализуй математическое ядро дерева, реактивный пересчет частот и валидатор связей (stage_level + правила совместимости).
3. Реализуй авто-раскладку дерева (Auto-layout) на QGraphicsScene с шапкой эшелонов.
4. Собери GUI с Drag-and-Drop и таблицей итоговых сценариев.
5. Реализуй векторный экспорт в PDF (A3/A2). Пиши полный, готовый к запуску код без заглушек TODO.
Как получить от ИИ-агента максимум с первого раза
- Не проси всё в одном сообщении, если агент сбоит на больших файлах. В конце промпта заложен план из 5 шагов — скажи агенту: «Выполни сначала шаги 1 и 2, покажи структуру JSON и ядро расчета, затем переходи к UI».
- Главная фишка для удобства в Методике № 533 — «Шапка эшелонов» (Columns Header). В классическом дереве событий (ETA) в отличие от обычной блок-схемы сверху идут колонки («Инициирующее событие» \rightarrow «ПАЗ» \rightarrow «Воспламенение» \rightarrow «АУПТ» \rightarrow «Итог / Q_j»), а под ними ветвится дерево. В промпте это уже заложено — именно это делает чертеж на A3/A2 читаемым для эксперта.
- Если захочешь потом перенести это в веб (для учеников курса): просто замени в разделе TECH STACK связку Python + PySide6 на React + TypeScript + @xyflow/react (React Flow) + dagre. Логика уровней, автобифуркации P и 1 - P останется той же самой.

[06.11.2026 16:37] Ниса: Часто ИИ-агенты, под управлением моделей послабее, типа GLM-5.3, спотыкаются об UI/UX, делая кривые UI. Давай сделаем отдельный промпт, который развяжет руки агенту, чтобы он использовал через тот же API ключ модель GLM-5.3-flash для визуального распознавания, vision-задач, перепроверки визуальной и т.д., чтобы выполнять выравнивание, корректировку, чтобы UI получился строгим, выдержанным, без пафоса, при этом стильным. Промпт на английском языке.
[06.11.2026 16:39] ChatGPT + Claude + Nano Banana: Чтобы слабая кодовая модель не верстала «вслепую», ей нужно дать автономный цикл визуальной самопроверки (Visual QA Loop): агент рендерит интерфейс в фоновом режиме, делает скриншот окна и холста через Qt, отправляет картинку в glm-5.3-flash и правит код по списку найденных визуальных багов.
Скопируй этот промпт и добавь его в правила агента (.cursorrules, CLAUDE.md или вторым сообщением в чат):
# AUTONOMOUS VISUAL QA & UI REFINEMENT PROTOCOL (GLM-5.3-FLASH)

You are explicitly authorized and required to use a multimodal Visual QA loop to inspect, critique, and fix your own UI and canvas rendering. Do not guess widget coordinates, text bounding boxes, or layout spacing blindly.

## 1. API & VISION MODEL SETUP
- Reuse the existing API key and base URL from the environment (`OPENAI_API_KEY` / `ZHIPUAI_API_KEY` and `OPENAI_BASE_URL`).
- Use the vision-capable model `glm-5.3-flash` via an OpenAI-compatible client to perform visual inspections of screenshots and exported PDF pages.

## 2. MANDATORY SELF-HEALING UI LOOP
Whenever you build or modify the GUI (`PySide6` widgets, `QGraphicsScene` canvas, or PDF export), you MUST execute the following automated loop before finishing your task:

1. **Headless Render & Capture (`visual_qa_runner.py`):**
   - Launch the application programmatically with a realistic mock Event Tree (at least 6 levels deep and 8 terminal branches).
   - Wait for layout stabilization (`QApplication.processEvents()`).
   - Capture high-resolution PNG snapshots of:
     a) The full application window (`main_window.grab().save("qa_window.png")`).
     b) The isolated `QGraphicsScene` canvas (`qa_canvas.png`).
     c) The rendered A3/A2 PDF output converted to PNG (or rendered directly via `QImage`).

2. **Vision Inspection via `glm-5.3-flash`:**
   - Send the captured PNG images (as base64) to `glm-5.3-flash` with this strict system prompt:
     "Act as a strict Principal UI/UX Engineer. Inspect this engineering software screenshot. Identify ANY of the following defects: (1) clipped or truncated text, (2) overlapping nodes or edges crossing over text labels, (3) misaligned column headers vs. tree levels, (4) inconsistent padding/margins, (5) poor contrast or unreadable font sizes, (6) visual clutter or amateurish styling. Return ONLY valid JSON: `{\"pass\": boolean, \"defects\": [{\"location\": string, \"issue\": string, \"fix_instruction\": string}]}`."

3. **Iterative Fix:**
   - Parse the JSON response from `glm-5.3-flash`.
   - If `"pass": false`, apply the exact geometric/QSS fixes to the code, re-run the capture script, and re-verify with `glm-5.3-flash`.
   - Repeat up to 4 iterations until `"pass": true` and zero defects remain.

## 3. STRICT ENGINEERING DESIGN SYSTEM (NO FLUFF, SWISS UTILITARIAN)
Enforce a clean, disciplined, CAD-grade aesthetic (inspired by Linear, Siemens NX, and Swiss typographic grids):

- **Zero Visual Clutter:** No gradients, no neon colors, no drop shadows, no rounded pill buttons, no decorative icons. Use flat surfaces and crisp `1px solid` structural borders.
- **Color Palette (High-Contrast Utilitarian Light Theme):**
  - App Background: `#F8FAFC`
  - Panel / Canvas Background: `#FFFFFF`
  - Structural Borders & Grid: `#CBD5E1` (1px solid)
  - Primary Text: `#0F172A`
  - Secondary / Metadata Text: `#475569`
  - Primary Accent (Selection / Active): `#2563EB`
  - Semantic Status ONLY on nodes/edges: Safe/Success `#16A34A`, Failure/Hazard `#DC2626`, Cut-off/Ignored branch `#94A3B8` (dashed line).
- **Typography & Numeric Discipline:**
  - UI Labels: System sans-serif (`Inter`, `Segoe UI`, or `Roboto`), `12px–13px`, medium weight for headers, regular for body.
  - Probabilities & Frequencies (`P`, `Q_j`): Strictly monospace (`JetBrains Mono`, `Consolas`, or `Courier New`) so scientific notation (`1.25 × 10⁻⁶`) aligns vertically down to the pixel.
[06.11.2026 16:39] ChatGPT + Claude + Nano Banana: - Spatial Grid & Geometry Invariants:
- Enforce an 8px spatial grid for all margins, paddings, and gaps (8px, 16px, 24px).
- Dynamic Node Sizing: Node width and height MUST be calculated dynamically from QFontMetrics.boundingRect() of the text + 16px horizontal padding and 12px vertical padding. Never hardcode fixed small rectangles that clip Russian text.
- Manhattan Edge Routing: Orthogonal lines only (90-degree bends). Probability labels on branches must sit in an opaque white pill/box (#FFFFFF background with 2px padding) or have a dedicated vertical offset (-14px above the horizontal segment) so lines never strike through numbers.
- Column Header Synchronization: The top Echelon Header bar MUST share the exact X coordinates of the corresponding tree depth levels on the canvas.
Что важно проверить при запуске
1. Переменная окружения: убедись, что в терминале, где работает агент, проброшен ключ (export OPENAI_API_KEY="твой_ключ" и export OPENAI_BASE_URL="https://open.bigmodel.cn/api/paas/v4/" — или тот эндпоинт, через который ты крутишь GLM).
2. Офскрин-рендер без мелькания окон: если агент работает на сервере или в песочнице без монитора, добавь ему короткую команду: использовать os.environ["QT_QPA_PLATFORM"] = "offscreen" внутри visual_qa_runner.py. Тогда он сможет делать скриншоты и гонять их через glm-5.3-flash полностью в фоне.