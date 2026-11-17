# SESSION 11 REPORT – Kuji 6.1.0

Date: 10.11.2026. Base: v6.0.0 (sessions 1–10 + 10.1 polish).
Subject: polish session per the confirmed task list – KB window bottom
bar + normative-language overhaul of «Защитные средства» (KB v6.1),
true per-pixel smooth scrolling, sub-tabs for the typical-frequency
tables, templates-tab selection design (empty badge + card highlight),
and the «СОСТАВ ШАБЛОНА» bold-text fix. All five tasks were implemented
without reopening any locked decision; no clarifying questions were
needed (the only open item – numeric values looking wrong for new
wording – never triggered: no numeric field was touched).

**Acceptance:** `smoke_test.py` – PASS (18 blocks, KB block extended
with the session-11 canon checks); `gesture_test.py` – PASS (13 blocks:
12 existing + new block 12 «per-pixel wheel scrolling»); `run_qa.cmd` –
PASS, artifacts regenerated (qa_kb_templates, qa_kb_measures,
qa_kb_tables, qa_kb_tables2 among them) and vision-reviewed. Version →
**6.1.0**; KB `meta.version` → **«6.1»** (content revision, schema
unchanged).

## Task 1a – KB window bottom bar

* `eta/ui/kb_window.py::KBWindow`: the bottom bar is now
  `[stretch] [Сохранить (primary, blue)] [Закрыть]`. The far-left
  «Закрыть» and the dead «Перечитать» button are removed. Closing still
  runs the dirty-guard path (`_ask_close_guard` via `closeEvent`) – the
  test seam is untouched. `_reload_all()` stays as an internal method
  (docstring updated; now called from `_save_all()`), so a future
  «Перечитать» menu action can reuse it. No dead button remains.

## Task 1b/1c – normative rewrite of `property_modifiers` (KB v6.1)

Method: one-shot byte-safe Python script (`read_bytes` → `json.loads`
→ patch 13 records → `json.dumps` → `write_bytes`; unique
`"property_modifiers"` anchor verified; re-parsed after edit; no em-dash
assertion; no «;» in any rewritten text field; script deleted after
use). `meta.version` → «6.1». 50 field replacements across 13 records;
file 68 535 → 64 962 bytes. Numeric fields (`k`, `p_success`,
`ranges`, `default_pfd`, `lambda_du_h`, `eta_levels`, `branches`) and
all ids/keys untouched.

Rendering: `_MeasuresTab._note()` now assembles the canon line
`формула (пункт/формула источника) – краткое описание` (source omitted →
parentheses omitted), then `math_html_lines` wraps it (subscripts still
render). `_coef()` coefficient strings de-jargonized (see below).

### Exact before → after strings (all 50 replacements)

**pm-drain** (title unchanged «Аварийный дренаж / слив»)
* formula: `F_вых = F_вх · PFD, PFD = 0,05` → `F_вых = F_вх · k_др, k_др = 0,05`
* source: `ГОСТ Р 12.3.047-98, прил. Э, п. Э.4.5 (Рбл = 0,95 – системы блокирования/аварийного сброса; качественная норма устройства аварийного слива – ГОСТ 12.1.004-91 п. 2.4, ГОСТ Р 12.3.047-98 п. 6.5)` → `ГОСТ Р 12.3.047-98, прил. Э, п. Э.4.5`
* notes: `Дренаж сокращает вовлекаемую массу (k_m ≈ 0,3–0,6 – engineering); в цепочке учитывается барьером прекращения/лимитации.` → `снижение частоты развития аварии при устройстве аварийного слива. Принятая вероятность срабатывания систем блокирования и аварийного сброса – 0,95`
* tooltip: (absent) → `Аварийный слив сокращает количество горючего вещества, участвующего в аварии. Вероятность срабатывания систем блокирования и аварийного сброса принята 0,95 (ГОСТ Р 12.3.047-98, прил. Э, п. Э.4.5).`
* Rendered note (target example from the task – achieved):
  `F_вых = F_вх · k_др, k_др = 0,05 (ГОСТ Р 12.3.047-98, прил. Э, п. Э.4.5) – снижение частоты развития аварии при устройстве аварийного слива. …`

**pm-venting** (title unchanged «Вытяжная / аварийная вентиляция»)
* formula: `P_ост = 1/(A·T + 1), A – кратность воздухообмена, ч⁻¹; T – продолжительность поступления, ч` → `P_ост = 1/(A·T + 1)` (variable decoding purged)
* source: `Формула-якорь К = А·Т + 1 (делитель массы) – ГОСТ Р 12.3.047-98, прил. А, п. А.2.5, ф. (А.13); вероятностная трактовка – engineering-estimate (прямой нормативной P_ВОК(A) нет)` → `ГОСТ Р 12.3.047-98, прил. А, п. А.2.5, ф. (А.13)`
* notes: `При включении педальки открывается поле «Кратность воздухообмена A, ч⁻¹» (рекомендуемые условия кредитования АВ – резервные вентиляторы + автопуск по ПДВК, ГОСТ Р 12.3.047-98 А.2.5).` → `снижение условной вероятности сохранения взрывоопасной концентрации при работе аварийной вентиляции. Вероятностная трактовка делителя массы – инженерная оценка`
* tooltip: 1 600-char pedagogical text (contained «формула-якорь», «барьер безопасности», variable decoding) → `Аварийная вентиляция уменьшает массу поступивших паров и газов в объеме помещения. Делитель массы A·T + 1 принят по ГОСТ Р 12.3.047-98 (прил. А, п. А.2.5, формула А.13). Кратность снижения массы консервативно приравнена к кратности снижения вероятности образования горючей среды.`

**pm-leak-detectors** (title unchanged «Датчики утечки / газоанализаторы»)
* formula: `F_вых = F_вх · PFD, PFD = 0,2 (D = 0,8)` → `F_вых = F_вх · PFD, PFD = 0,2`
* source: `Прямого D для систем обнаружения утечек нет – Методика № 533 п. 41(а) требует учитывать без значений; нормативный аналог D = 0,8 – табл. П2.2 Прил. № 2 (сигнализация вне зданий с контролем); λ_DU 10⁻⁷…10⁻⁶ ч⁻¹ – engineering (МЭК 61508-6)` → `Приказ МЧС России № 533, прил. № 2, табл. П2.2`
* notes: `Раннее обнаружение до воспламенения: запуск ПАЗ/вентиляции.` → `снижение частоты развития аварии при раннем обнаружении утечки. Вероятность обнаружения принята по нормативному аналогу для сигнализации загазованности`
* tooltip: (absent) → `Газоанализаторы обеспечивают раннее обнаружение утечки до воспламенения и запуск противоаварийной защиты. Вероятность обнаружения – по аналогу из табл. П2.2 прил. № 2 к Приказу МЧС России № 533.`

**pm-vibro** (title unchanged «Контроль температуры / вибрации»)
* source: `engineering-estimate: мониторинг состояния переводит деградационные отказы в планируемые остановы (согласуется с ГОСТ 12.1.004-91 п. 7.9 – контроль нагрева подшипников); нормативного k нет` → `ГОСТ 12.1.004-91, п. 7.9`
* notes: `Для вращающегося оборудования; статическое – k = 1.` → `снижение частоты отказов вращающегося оборудования при непрерывном контроле технического состояния. Значение коэффициента – инженерная оценка`
* tooltip: 1 800-char pedagogical text → `Непрерывный мониторинг температуры и вибрации выявляет деградационные отказы на ранней стадии и позволяет перевести оборудование в плановый останов. Снижение частоты отказов учитывается коэффициентом 0,7 как инженерная оценка. Требования к контролю нагрева узлов трения – ГОСТ 12.1.004-91, п. 7.9.`

**pm-reserve** (LOCKED rename)
* title: `Наличие резерва (горячий/холодный)` → `Резервирование противоаварийной защиты`
* formula: `1oo1: PFD; 1oo2: PFD²; 2oo3: 3·PFD² − 2·PFD³ (биномиальная схема голосования)` → `1oo2: PFD_сист = PFD². 2oo3: PFD_сист = 3·PFD² − 2·PFD³`
* source: `ГОСТ Р МЭК 61508-6-2012 (МЭК 61508-6:2010), прил. B, п. B.3.2.2 (осреднённые формы с поправкой на общую причину β); мгновенные значения – теория надежности (независимые каналы)` → `ГОСТ Р МЭК 61508-6-2012, прил. B, п. B.3.2.2`
* notes: `Перестраивает логику защитной автоматики: 1oo2 → PFD_сист = PFD²; 2oo3 → 3·PFD² − 2·PFD³. Поле «Степень резервирования».` → `пересчет вероятности отказа по запросу (PFD) при резервировании каналов защиты. Схема 1 из 2 – защита отказывает только при отказе обоих каналов (квадрат вероятности отказа по запросу). Схема 2 из 3 – срабатывание по большинству каналов (три квадрата минус два куба той же вероятности)`
* tooltip: (absent) → `Резервирование каналов противоаварийной защиты снижает вероятность отказа по запросу (PFD). Схема 1 из 2 отказывает только при отказе обоих каналов. Схема 2 из 3 срабатывает по большинству каналов. Формулы – по ГОСТ Р МЭК 61508-6-2012, прил. B, п. B.3.2.2.`

**pm-wear** (title unchanged «Износ (превышен срок службы)»)
* formula: `λ_итог = λ_баз · k, k = 2…5 (по умолчанию 2)` → `λ_итог = λ_баз · k, k = 2…5`
* source: `engineering-estimate: рост λ(t) на участке износа (кривая ванны; ГОСТ 27.002-2015 – λ непостоянна); OREDA/SINTEF фиксируют рост отказов за пределами useful life; нормативного k нет` → `ГОСТ 27.002-2015`
* notes: `Поле «Коэффициент износа k» (2…5).` → `повышение частоты отказов при эксплуатации оборудования за пределами назначенного срока службы. Интенсивность отказов на участке износа возрастает, значение коэффициента – инженерная оценка`
* tooltip: 1 800-char pedagogical text → `При превышении назначенного срока службы оборудование переходит в фазу интенсивного износа, и частота аварийных отказов повышается коэффициентом от 2 до 5 (по умолчанию 2). Непостоянство интенсивности отказов на жизненном цикле – ГОСТ 27.002-2015.`

**pm-hermetic**
* title: `Герметичное исполнение / антикоррозийная защита` → `Герметичное исполнение / антикоррозионная защита` (normative spelling)
* formula: `λ_итог = λ_баз · k, k = 0,5 (трубопроводы: k_кпз = 0,16 – норматив)` → `λ_итог = λ_баз · k, k = 0,5`
* source: `engineering-estimate (консервативная середина 0,07–0,3 нормативных k исполнения); нормативный аналог – Приказ МЧС России № 533, прил. № 6, табл. П6.2: k_кпз = 0,16 (улучшенная защита от коррозии) и k_бд = 0,07 (улучшенные материалы + контроль)` → `Приказ МЧС России № 533, прил. № 6, табл. П6.2`
* notes: `Герметичные/бесфланцевые соединения, двойные уплотнения, ЭХЗ.` → `снижение частоты разгерметизации при герметичных соединениях и улучшенной защите от коррозии. Значение коэффициента – инженерная оценка по диапазону нормативных аналогов`
* tooltip: (absent) → `Герметичные и бесфланцевые соединения, двойные уплотнения и улучшенная защита от коррозии снижают частоту разгерметизации. Нормативные аналоги коэффициента для улучшенной защиты от коррозии – табл. П6.2 прил. № 6 к Приказу МЧС России № 533.`

**pm-exproof** (title unchanged «Взрывозащищённое исполнение»)
* formula: `блокировщик сценариев: ветви воспламенения и взрыва отсекаются/сереют (CUTOFF)` → `λ_эл = 0`
* source: `engineering-estimate по назначению исполнения (ГОСТ 31610.0 – исключение ИЗ внутри оболочки); вероятность появления ИЗ снижается до пренебрежимой` → `ГОСТ 31610.0` (exact part not present in the existing source nor in `literature\`, so per rule 1c only the short designation is kept)
* notes: `При генерации цепочки ветви «мгновенное/отложенное воспламенение», «взрыв ТВС» не создаются.` → `исключение электрических источников зажигания. Электрооборудование во взрывозащищенном исполнении не способно воспламенить окружающую среду`

**pm-sil**
* title: `SIL системы ПАЗ (реле/клапаны)` → `ПАЗ по уровню полноты безопасности (SIL)` (Russian term first, Latin in parentheses)
* formula: `PFD по уровню SIL (низкая частота запросов); по умолчанию – верхняя (консервативная) граница диапазона; барьер ПАЗ: F_вых = F_вх · PFD_голосование` → `F_вых = F_вх · PFD`
* source: `ГОСТ Р МЭК 61508-1-2012 (МЭК 61508-1:2010), табл. 2: SIL 1 10⁻²≤PFD<10⁻¹; SIL 2 10⁻³≤PFD<10⁻²; SIL 3 10⁻⁴≤PFD<10⁻³; SIL 4 10⁻⁵≤PFD<10⁻⁴` → `ГОСТ Р МЭК 61508-1-2012, табл. 2`
* notes: `Значение PFD редактируемо; поле «Степень резервирования» уточняет (1oo2 → PFD², 2oo3 → 3P²−2P³).` → `снижение частоты развития аварии системой противоаварийной защиты. Вероятность отказа по запросу (PFD) принимается по уровню полноты безопасности (SIL), консервативно – верхняя граница диапазона. При резервировании каналов значение пересчитывается по схеме резервирования`
* tooltip: 1 900-char pedagogical text → `Система противоаварийной защиты работает в режиме редких запросов. Ее эффективность оценивается вероятностью отказа по запросу (PFD) по уровню полноты безопасности (SIL) из табл. 2 ГОСТ Р МЭК 61508-1-2012. При отсутствии точных данных принимается верхняя граница диапазона.`

**pm-ttest**
* title: `Периодичность ТО защит T_тест` → `Периодичность проверок защитных средств (T_тест)`
* formula: `PFD_avg ≈ λ_DU · T_тест / 2 (λ_DU – опасные необнаруживаемые отказы, ч⁻¹; T_тест, ч); итоговый PFD барьера = max(PFD_SIL_голосование, PFD_avg) – консервативно` → `PFD_сист = max(PFD_SIL, PFD_avg). PFD_avg ≈ λ_DU · T_тест/2`
* source: `ГОСТ Р МЭК 61508-6-2012, прил. B, п. B.3.2.2.1 (архитектура 1oo1); верификация exida: λ_DU = 2,24·10⁻⁹/ч, T = 8760 ч → PFD_avg = 9,8·10⁻⁶; типовые λ_DU клапан+привод+соленоид ~10⁻⁶/ч – engineering` → `ГОСТ Р МЭК 61508-6-2012, прил. B, п. B.3.2.2.1`
* notes: `λ_DU редактируем (10⁻⁷…10⁻⁶/ч – полевые приборы); T_тест в месяцах.` → `средняя вероятность отказа по запросу (PFD) за интервал между проверками. В расчет принимается наибольшее из значений по уровню полноты безопасности (SIL) и по периодичности проверок`

**pm-env-cat** (title unchanged «Категория взрывопожароопасной среды»)
* formula: `определяет наличие ветвей физической развилки (генератор цепочки); «Негорючая» – блокировщик ветвей горения` → `P_воспл(Q_расход, среда)` (the old text described the removed v5 chain generator)
* source: `Приказ МЧС России № 533, Прил. № 2, табл. П2.1 (вероятности по виду среды и расходу); ГОСТ 12.1.004-91 (категории помещений)` → `Приказ МЧС России № 533, прил. № 2, табл. П2.1`
* notes: `Вероятности ветвей – табл. П2.1 по категории расхода.` → `выбор столбца условных вероятностей воспламенения по категории расхода и среды. Для негорючей среды ветви горения исключаются из расчета`

**pm-lightning** (title unchanged «Молниезащита здания»)
* formula: `Q_пораж = N_у.м · (1 − η_МЗ); N_у.м = (S+6H)(L+6H)·n_у·10⁻⁶ – ожидаемое число ударов молнии в здание (S, L – размеры в плане, м; H – наибольшая высота, м; n_у – плотность ударов, км⁻²·год⁻¹); влияет на причину «Прямой удар молнии» (c-iz-lightning) фазы ИЗ деревьев оборудования внутри здания` → `Q_пораж = N_у.м · (1 − η_МЗ), N_у.м = (S + 6H)·(L + 6H)·n_у·10⁻⁶`
* source: `N_у.м – ГОСТ 12.1.004-91, прил. 3, п. 3.1.3 и табл. 3 (n_у = 3/6/9/12 при 20–40/…); η_МЗ – СО 153-34.21.122-2003, табл. 2.2 (надёжность защиты I/II/III/IV = 0,98/0,95/0,90/0,80); ср. РД 34.21.122-87 … и МЭК 62305-2 …; Q = N·(1−η) – engineering-аппроксимация …` → `ГОСТ 12.1.004-91, прил. 3, п. 3.1.3 (N_у.м). СО 153-34.21.122-2003, табл. 2.2 (η_МЗ)`
* notes: `Размеры здания S/L/H задаются в свойствах здания; при их отсутствии – только множитель (1 − η).` → `снижение частоты поражения здания молнией с учетом надежности молниезащиты. Надежность защиты по категориям I–IV: 0,98, 0,95, 0,90, 0,80`

**pm-temp-selfign** (title unchanged «Самовоспламенение при T_раб ≥ T_самовоспл»)
* formula: `P(мгновенного воспламенения) = 1 при T_раб ≥ T_самовоспл (P_успеха «нет воспламенения» = 0)` → `P_мгн.воспл = 1`
* source: `Приказ МЧС России № 533, Прил. № 2, п. 3: выход вещества, нагретого до температуры самовоспламенения и выше, – мгновенное воспламенение с условной вероятностью 1; безопасный порог 0,8·T_св – ГОСТ 12.1.004-91, разд. 2, п. 2.3` → `Приказ МЧС России № 533, прил. № 2, п. 3`
* notes: `T_самовоспл – свойство вещества (справочник), по умолчанию 450 °C.` → `выход вещества, нагретого до температуры самовоспламенения и выше, сопровождается мгновенным воспламенением с условной вероятностью 1`

### Coefficient column (`_MeasuresTab._coef`, kb_window.py)

* `1 − 0,95 (PFD барьера)` / `1 − 0,8 (PFD барьера)` → `1 − 0,95 (вероятность отказа по запросу)` / `1 − 0,8 (вероятность отказа по запросу)` (task-1b pattern rule).
* voting: `по схеме голосования` → `по схеме резервирования` (LOCKED).
* sil: `PFD по уровню SIL` → `по уровню полноты безопасности (SIL)`.
* p_success == 0.0 (pm-temp-selfign): the pattern «1 − 0 (PFD барьера)» was
  factually wrong (there is no protection failing here – ignition is
  certain); special-cased to `P_воспл = 1` (math notation). Flagged as a
  wording decision, no numeric change.
* `PFD_avg ≈ λ_DU·T/2` kept – a standard symbol inside a formula.
* lambda_k values stay numeric (`0,7`, `2`, `0,5`) per 1b/1c.

## Task 2 – true per-pixel smooth scrolling

Root cause confirmed: `QTableWidget/QTreeView/QListView` default
`verticalScrollMode = ScrollPerItem` snapped the animated wheel to row
boundaries.

* New `_pixel_scroll()` helper (kb_window.py) sets
  `ScrollPerPixel` vertical + horizontal and `setSingleStep(20)`; applied
  to: all KB tables (`_TableTab`, `_MeasuresTab`, all three
  `MethodTablesTab` tables) in constructors and after every reload;
  the matrix `QTableWidget` (main_window.py); the hierarchy `QTreeWidget`
  (hierarchy_panel.py); the cause-picker `QListWidget`
  (inspector_panel.py); the `wide_combo()` popup `QListView`
  (controls.py).
* `_keep_scroll_pos()` (kb_window.py): `_TableTab.reload()` and
  `_MeasuresTab.reload()` capture the scrollbar value before the content
  reset and restore it clamped to the new range – no jump on reload.
* `SMOOTH_MS = 150` / `SMOOTH_NOTCH_PX = 60` / OutCubic / retarget-on-
  consecutive-ticks logic left as is (verified retargeting still works –
  the filter's `_smooth` dict logic untouched); with per-pixel mode the
  60 px/notch now interpolates through intermediate pixels.
* Shift+wheel horizontal and the TreeCanvas/DocumentView zoom
  exclusions untouched (scroll.py not modified).
* **Verification evidence** (gesture_test block 12): a real
  `QWheelEvent` (angleDelta −120) sent to the GS table viewport through
  the installed app filter produced observed scrollbar values
  `[0, 22, 31, 41, 49, 54, …]` – intermediate non-row-multiple pixels
  during the animation, asserted programmatically (≥4 distinct values,
  strictly-between values present, non-multiples of row height, final
  > 40). All KB tables + matrix + hierarchy asserted `ScrollPerPixel`.

## Task 3 – «Таблицы типовых частот» sub-tabs

`MethodTablesTab` rebuilt: outer caption kept, content is now a nested
`QTabWidget` (objectName `kbSubTabs`, compact QSS in theme.py:
5×12 padding, 11 px font, flat, `outline: none` inherited) with three
sub-tabs (LOCKED names): «П1.3 – частоты пожаров», «П1.4 – при
F > 10 000 м²», «П2.1 – условные вероятности воспламенения». Each page:
rich-text caption + table filling the page (stretch columns, per-pixel
scroll). Headers de-duplicated («Тип здания/помещения | a₁, м⁻²·год⁻¹»,
«… | a | b», «Расход | Среда | Мгновенное | Последующее | С изб.
давлением»). The П1.4 caption formula is now exactly `Q = a·F^b` via
`math()` (`^b` → real superscript); the leftover
«Q = a·F·F…·b, точнее a·F^b» is gone. Read-only nature preserved.
QA: `qa_kb_tables.png` (sub-tab 1) + new `qa_kb_tables2.png` (sub-tab 2).

## Task 4 – templates tab design

* Empty badge: `TemplatesTab.hint` is created hidden;
  `set_owner_available()` ends with `hint.setVisible(bool(hint.text()))`
  – the pill exists ONLY with an active selection («Цель: …»).
* Card selection: `_TemplateCard` gets `WA_StyledBackground` +
  `selected=false` property; `_mark_selected()` sets `selected=true` on
  the `selected_id` card (false elsewhere) with unpolish/polish; called
  from `_on_card`, `_on_card_dbl`, and `rebuild_cards()` (selection
  survives search filtering). New `scroll_to_selected()`
  (ensureWidgetVisible) brings the selected card into view (used by the
  QA runner; available for post-filter UX). QSS in theme.py:
  `QFrame#kbCard` base (1 px BORDER, radius 8, PANEL_BG), `:hover`
  (border #94A3B8, APP_BG), `[selected="true"]` (ACCENT border + 3 px
  left, #EFF6FF fill). Details pane and paddings unchanged otherwise.
* gesture-test compatibility preserved: `_on_card` no longer touches the
  passed card object itself (marking iterates real card widgets), so the
  test's lightweight stub card still works.

## Task 5 – «СОСТАВ ШАБЛОНА» all-bold fix

Root cause (confirmed by KB grep, no live repro needed beyond it):
template/cause titles contain a raw `<` – «Резервуар ЛВЖ/ГЖ < 450 м³»,
«…отверстие 25 мм… < 450 м³ …». QLabel's auto rich-text detection saw
the leading `<b>…</b>`, then the parser mis-handled the bare `<` inside
the title, so the `</b>` never closed and everything after rendered
bold. Fix (kb_window.py): every interpolated KB string in the details
pane and card tooltip/labels is `html.escape()`d; `details` uses
explicit `setTextFormat(RichText)` (and PlainText for the placeholder);
section labels «Разновидности ГС/ИЗ:» are explicit
`<span style="font-weight:600">`, bullets normal weight – only the
title line is `<b>`. QA shot `qa_kb_templates.png` now selects exactly
`eq-tank-small` («Резервуар ЛВЖ/ГЖ < 450 м³») to vision-verify the fix
on the worst-case record.

## Files touched (session 11)

eta/__init__.py (6.1.0) · eta/knowledge/knowledge_base.json (v6.1,
50 field rewrites + meta.version; byte-safe script, deleted) ·
eta/ui/kb_window.py (Tasks 1a/1b-render/2/3/4/5) ·
eta/ui/theme.py (QSS: kbCard + kbSubTabs) ·
eta/ui/main_window.py (matrix per-pixel) ·
eta/ui/hierarchy_panel.py (tree per-pixel) ·
eta/ui/inspector_panel.py (picker per-pixel) ·
eta/ui/controls.py (combo popup per-pixel) ·
smoke_test.py (KB 6.1 + canon block) ·
gesture_test.py (v6.1 assert + block 12 wheel scroll) ·
visual_qa_runner.py (new switch titles, eq-tank-small selection shot,
sub-tab captures) · README.md (version line, KB section, scrolling
bullet) · qa_artifacts (regenerated).

## Test results / Visual QA

* smoke_test.py – PASS, 18 blocks; block 1 extended: KB 6.1, no «;» in
  modifier texts, jargon blacklist («барьер», «якорь», «голосования»,
  «PFD барьера», «горячий/холодный») absent, locked titles asserted.
* gesture_test.py – PASS (exit 0), 13 blocks (new block 12 per-pixel
  wheel scrolling with intermediate-value assertions; observed scrollbar
  values across runs: 0 → 17 → 31/32 → 41/42 → 49 → 54/55 → … –
  intermediate non-row-multiple pixels during the 150 ms OutCubic
  animation).
* run_qa.cmd – PASS (run after the last code change); artifacts
  regenerated and vision-reviewed with glm-5.3-flash (2× crops for
  pixel truth):
  - qa_kb_templates.png – PASS: exactly one card «Резервуар ЛВЖ/ГЖ
    < 450 м³» highlighted (blue border + 3 px left bar + light-blue
    fill), matching the details pane; badge «Цель: Участок 1» non-empty;
    dialog bottom-right = «Сохранить» (primary) + «Закрыть», no
    «Перечитать»; only the title line bold (worst-case «<» record).
  - qa_kb_measures.png + bottom-rows 2× grab – PASS: canon notes
    «формула (источник) – описание», no «;», no jargon, real
    sub/superscripts in Примечание (λ_DU, N_у.м, 10⁻⁶), coefficients
    «1 − 0,95/0,8 (вероятность отказа по запросу)», «по схеме
    резервирования», «по уровню полноты безопасности (SIL)»,
    «η = 0,98…0,80», «PFD_avg ≈ λ_DU·T/2», «P_воспл = 1», «–».
  - qa_kb_tables.png / qa_kb_tables2.png – PASS: three sub-tabs with
    the locked names, П1.3 table filling the page, П1.4 caption
    «При F > 10 000 м² (Q = a·Fᵇ)» with a REAL raised superscript b.
  - qa_switches.png – PASS: new titles «Резервирование противоаварийной
    защиты» (disabled sample) and «ПАЗ по уровню полноты безопасности
    (SIL)»; «Наличие резерва (горячий/холодный)» gone.
* Vision-loop fixes made during QA (both re-verified):
  1. `_coef()` previously passed `math()` HTML into a plain
     QTableWidgetItem → raw `<sub>` tags showed as text in the
     «Коэффициент» column (pre-existing since session 10.1, surfaced by
     the canon pass). Fixed: plain mini-notation strings for the
     `pfd_avg` and temp-selfign cases.
  2. The first qa_kb_templates shot had the selected card below the
     fold (marking was correct – programmatic probe confirmed only
     eq-tank-small carried selected=true). Added
     `TemplatesTab.scroll_to_selected()` (ensureWidgetVisible) and the
     QA runner now calls it, so the shot shows highlight + details
     together.

## Known issues / notes

* Coefficient column for pm-temp-selfign deliberately shows `P_воспл = 1`
  instead of the «1 − 0 (…)» pattern (factually wrong wording);
  documented here in case the customer prefers the strict pattern.
* `QSettings`-based UI state and all serialization/format-5 behavior
  untouched; smoke/gesture suites pass unchanged apart from the listed
  assertion updates.
* The removed «Перечитать» button's functionality still exists as
  `KBWindow._reload_all()` (internal, used after save) if it is ever
  wanted as a menu action.
* No numeric KB values were changed; if the customer later finds a
  numeric value inconsistent with the new wording, it is a separate
  decision (§12.5 protocol – not triggered this session).
