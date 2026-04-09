# Инструкция для агентов: Prophetic Timeline

## О проекте

Интерактивная диорама-таймлайн. Два экрана:

1. **Панорама** — вступительный экран, фон + кликабельные объекты → каждый ведёт в сцену
2. **Таймлайн** — горизонтальная лента 3D-сцен, листается свайпом/стрелками

Сервер запускается: `npm start` в `/Users/pavlopopravkin/www/uuk-timeline/`
Админка: `http://localhost:3000/admin`
Просмотр: `http://localhost:3000`

---

## CLI для агентов

Установлен CLI-инструмент `uuk-timeline` для управления таймлайном без браузера:

```bash
# Установка (однократно)
pip install -e /Users/pavlopopravkin/www/uuk-timeline/agent-harness/

# Примеры
uuk-timeline scenes list
uuk-timeline scene add --title "Рождество" --year "Рожд." --night
uuk-timeline element add-text 5 --text "Благовещение" --font "'Cormorant Garamond', serif" --size 6
uuk-timeline panorama get
uuk-timeline apply-json --stdin   # принимает полный JSON документ из stdin
```

Полная документация CLI: `agent-harness/cli_anything/uuk_timeline/skills/SKILL.md`

Все команды возвращают JSON. Используй `--server URL` для нестандартного адреса сервера.

---

## Файлы данных

| Файл | Назначение |
|------|-----------|
| `scenes.json` | Активный набор сцен |
| `panorama.json` | Активная панорама |
| `scenes.<name>.json` | Сохранённый пресет сцен |
| `panorama.<name>.json` | Сохранённый пресет панорамы |

---

## Структура `scenes.json`

```json
{
  "name": "Название пресета",
  "scenes": [ /* массив сцен */ ]
}
```

### Поля одной сцены

```json
{
  "id": 0,
  "title": "Заголовок сцены",
  "subtitle": "Цитата или короткое описание",
  "date": "Дата или период (произвольный текст)",
  "year": "Метка на таймлайне — макс 8–10 символов",
  "bg": "/uploads/вариации_2K_202603191339-2.jpg",
  "bg_video": "https://www.youtube.com/watch?v=XXXXXXXXXXX",
  "night": true,
  "elements": [ /* массив элементов — см. ниже */ ]
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | number | Порядковый номер (0, 1, 2…) |
| `title` | string | Заголовок — крупно на экране |
| `subtitle` | string | Цитата или описание |
| `date` | string | Полная дата / период |
| `year` | string | Короткая метка таймлайна |
| `bg` | string | Путь к фоновому изображению |
| `bg_video` | string | YouTube URL — используется вместо `bg` если задан |
| `night` | boolean | `true` = тёмная сцена со звёздами |
| `elements` | array | Все объекты сцены (изображения и тексты) |

> Если задан `bg_video`, фоновая картинка `bg` игнорируется.

---

## Элементы сцены (`elements`)

Два типа: **изображение** (по умолчанию) и **текст** (`type: "text"`).

### Изображение

```json
{
  "src": "/uploads/0009.png",
  "x": 0.35,
  "bottom": 0.05,
  "h": 75,
  "w": 0,
  "parallax": 1.0,
  "flip": false,
  "softEdge": 0,
  "anim": "float",
  "content": "<h3>Заголовок</h3><p>HTML при клике на объект</p>"
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `src` | string | Путь к PNG/JPG |
| `x` | 0–1 | Горизонтальная позиция якоря: 0 = левый край, 1 = правый |
| `bottom` | 0–1 | Отступ снизу как доля высоты сцены (0 = у земли, 0.5 = середина) |
| `h` | 0–100 | Высота в % от высоты сцены; 0 = авто |
| `w` | 0–100 | Ширина в % от ширины сцены; 0 = авто |
| `parallax` | 0–2 | Сила параллакс-масштабирования при листании (0 = нет, 1 = нормальный, 2 = сильный) |
| `flip` | boolean | Горизонтальное зеркалирование |
| `softEdge` | 0–100 | Размытие краёв (0 = нет) |
| `anim` | string | `"float"` — покачивание, иначе статика |
| `content` | string | HTML-контент для детальной панели при клике (необязательно) |

**Правила позиционирования:**
- `x`: левый объект ~0.15–0.30, центральный ~0.45–0.55, правый ~0.65–0.80. Не ставь у края (0.0 или 1.0) — обрежется.
- `bottom`: основные фигуры у земли → 0–0.05. Летящие/небесные → 0.2–0.5.
- `h`: главный объект ~70–90, средний ~50–65, мелкий декор ~25–45.
- `parallax`: смысловые объекты (ближний план) → 1.0–1.5. Дальний план/фоновые → 0–0.5.

### Текст (`type: "text"`)

```json
{
  "type": "text",
  "text": "Текст который отображается на сцене",
  "font": "Georgia, serif",
  "fontSize": 4,
  "fontWeight": 400,
  "fontStyle": "normal",
  "color": "#f5e6c8",
  "opacity": 1,
  "textAlign": "left",
  "letterSpacing": 0.05,
  "lineHeight": 1.2,
  "textShadow": "0 2px 16px rgba(0,0,0,0.9),0 0 40px rgba(0,0,0,0.7)",
  "textTransform": "",
  "maxWidth": 0,
  "x": 0.5,
  "bottom": 0.62,
  "parallax": 0.5
}
```

| Поле | Тип | Описание |
|------|-----|----------|
| `type` | `"text"` | Обязательно — отличает от изображения |
| `text` | string | Содержимое (поддерживает `\n`) |
| `font` | string | CSS font-family. Только кириллические шрифты (см. ниже) |
| `fontSize` | 0.5–12 | Размер в % от высоты сцены (vh-единицы) |
| `fontWeight` | 100–900 | Жирность |
| `fontStyle` | `"normal"` / `"italic"` | Начертание |
| `color` | CSS-цвет | Цвет текста |
| `opacity` | 0–1 | Прозрачность |
| `textAlign` | `"left"` / `"center"` / `"right"` | Выравнивание |
| `letterSpacing` | число em | Межбуквенный интервал (0.05–0.3 для заголовков) |
| `lineHeight` | число | Межстрочный интервал (1.0–1.8) |
| `textShadow` | CSS | Тень текста |
| `textTransform` | `""` / `"uppercase"` | Регистр |
| `maxWidth` | 0–80 | Ширина в vw; **0 = авто** (ширина по содержимому, без переноса) |
| `x` | 0–1 | Горизонтальная позиция |
| `bottom` | 0–1 | Вертикальная позиция |
| `parallax` | 0–2 | Параллакс-масштаб |

**Важно:** при `maxWidth > 0` текст переносится, `textAlign` рекомендуется `"center"`.  
При `maxWidth = 0` (по умолчанию) текст в одну строку, ширина = ширина текста.

#### Доступные кириллические шрифты

| Шрифт | CSS значение | Стиль |
|-------|-------------|-------|
| Georgia | `Georgia, serif` | Классика |
| PT Serif | `'PT Serif', serif` | Газетный |
| Lora | `'Lora', serif` | Элегантный |
| Merriweather | `'Merriweather', serif` | Читабельный |
| Philosopher | `'Philosopher', serif` | Философский |
| Cormorant Garamond | `'Cormorant Garamond', serif` | Утончённый |
| EB Garamond | `'EB Garamond', serif` | Классический |
| Spectral | `'Spectral', serif` | Современная антиква |
| Crimson Text | `'Crimson Text', serif` | Книжный |
| Playfair Display | `'Playfair Display', serif` | Дисплейный журнальный |
| Roboto | `'Roboto', sans-serif` | Нейтральный |
| Roboto Condensed | `'Roboto Condensed', sans-serif` | Узкий нейтральный |
| PT Sans | `'PT Sans', sans-serif` | Классика без засечек |
| PT Sans Narrow | `'PT Sans Narrow', sans-serif` | Узкий |
| Montserrat | `'Montserrat', sans-serif` | Геометрический |
| Nunito | `'Nunito', sans-serif` | Мягкий |
| Exo 2 | `'Exo 2', sans-serif` | Технологичный |
| Comfortaa | `'Comfortaa', cursive` | Округлый |
| Golos Text | `'Golos Text', sans-serif` | Современный русский |
| Russo One | `'Russo One', sans-serif` | Жирный дисплейный |
| Yeseva One | `'Yeseva One', serif` | Декоративный |
| Unbounded | `'Unbounded', sans-serif` | Широкий современный |
| Oswald | `'Oswald', sans-serif` | Вытянутый |

#### Пресеты `textShadow`

```
"0 2px 16px rgba(0,0,0,0.9),0 0 40px rgba(0,0,0,0.7)"   // тёмное свечение
"0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)" // золотое свечение
"0 1px 3px rgba(0,0,0,0.8)"                               // тонкая тень
"0 0 20px rgba(255,255,255,0.4),0 2px 12px rgba(0,0,0,0.8)" // белое свечение
```

---

## Доступные изображения в `/uploads/`

### Основные объекты (смысловые)
| Файл | Образ |
|------|-------|
| `0001.png` | Слово / Начало / Свет |
| `0002.png` | Сияние / Первый свет |
| `0003.png` | Вода и земля |
| `0004.png` | Растение / Жизнь |
| `0005.png` | Облако / Небо |
| `0006.png` | Храм / Здание |
| `0007.png` | Небесное тело / Планета |
| `0008.png` | Человек / Фигура |
| `0009.png` | Ангел / Посланник |
| `0010.png` | Скрижаль / Закон |
| `0011.png` | Огонь / Жертва |
| `0012.png` | Звезда |
| `0013.png` | Дерево жизни |
| `0014.png` | Пророк |
| `0015.png` | Крест / Голгофа |
| `0016.png` | Воскресение |
| `0017.png` | Дух / Пламень |
| `0018.png` | Город / Иерусалим |
| `0019.png` | Книга / Слово |
| `0020.png` | Новый мир |

### Декоративные элементы
- `3D Glass Flowers (1).png` … `(25).png` — стеклянные цветы, используются как декор переднего плана

### Именованные объекты
| Файл | Описание |
|------|----------|
| `1775326068808_AdamEvewithThreeOnFront.png` | Адам и Ева с деревом |
| `1775332778823_GrehAdamEve.png` | Адам и Ева (грехопадение) |
| `1775332778814_GrehBackground.png` | Фон грехопадения |
| `1775333598243_GrehBg.jpg` | Тёмный фон |
| `1775333598232_Jerusalem.jpg` | Иерусалим |
| `1775340501597_photo_...jpg` | Пейзаж |
| `1775340501605_Generative_Fill_2.png` | Генеративная иллюстрация |
| `1775340501613_Layer_3.png` | Слой 3 |
| `1775340501620_Layer_2.png` | Слой 2 |
| `1775340501626_NoIst.png` | Фигура |

### Фоны
| Файл | Настроение |
|------|-----------|
| `/uploads/вариации_2K_202603191339-2.jpg` | Ночь, тайна, начало, суд |
| `/uploads/вариации_2K_202603191339.jpg` | Тёмная глубина, Голгофа |
| `/uploads/вариации_2K_202603191339-3.jpg` | Свет, природа, жизнь |
| `/uploads/1775333598203_GrehGorBG.png` | Гора, мистика |

---

## Структура `panorama.json`

```json
{
  "name": "Название",
  "background": "/uploads/вариации_2K_202603191339-2.jpg",
  "elements": [
    {
      "id": "elem-cross",
      "src": "/uploads/0015.png",
      "x": 55,
      "y": 12,
      "width": 16,
      "sceneId": 27,
      "anim": "zoom"
    }
  ],
  "clickAreas": [
    {
      "sceneId": 27,
      "x": 50,
      "y": 5,
      "width": 18,
      "height": 38
    }
  ]
}
```

### Объекты панорамы (`elements`)

Все координаты — в **процентах от размера экрана (0–100)**.

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | string | Уникальный идентификатор |
| `src` | string | Путь к изображению |
| `x` | 0–100 | Горизонтальная позиция центра объекта (%) |
| `y` | 0–100 | Вертикальная позиция центра объекта (%) |
| `width` | 0–100 | Высота объекта в % от высоты экрана (`vh`) |
| `sceneId` | number | ID сцены для перехода при клике (необязательно) |
| `anim` | `"float"` / `"zoom"` / null | Анимация |

### Зоны клика (`clickAreas`)

Невидимые прямоугольники, также в **процентах**.

| Поле | Тип | Описание |
|------|-----|----------|
| `sceneId` | number | ID сцены для перехода |
| `x` | 0–100 | Левый край зоны |
| `y` | 0–100 | Верхний край зоны |
| `width` | 0–100 | Ширина зоны |
| `height` | 0–100 | Высота зоны |

> Обычно на каждый объект делается одна `clickArea` чуть крупнее самого объекта.

---

## API

```bash
# Получить сцены
GET  /api/scenes

# Обновить сцены (полная замена)
PUT  /api/scenes
Body: { "name": "...", "scenes": [...] }

# Получить панораму
GET  /api/panorama

# Обновить панораму
PUT  /api/panorama
Body: { "name": "...", "background": "...", "elements": [...], "clickAreas": [...] }

# Список пресетов
GET  /api/presets

# Загрузить пресет
POST /api/presets/:name/load

# Сохранить текущее как пресет
POST /api/presets/:name/save

# Список загруженных изображений
GET  /api/library

# Загрузить изображение
POST /api/upload
Body: multipart/form-data, поле "file"

# Поиск стоковых изображений (требует API ключ)
GET  /api/image-search?q=angel&source=pexels&per_page=12
# source: "pexels" (нужен PEXELS_API_KEY) | "pixabay" (нужен PIXABAY_API_KEY)
# Возвращает: { results: [{ id, url, thumb, width, height, description, author, page_url }] }

# Скачать изображение по URL в uploads
POST /api/image-fetch                        [требует auth]
Body: { "url": "https://...", "filename": "optional_name" }
# Возвращает: { ok: true, path: "/uploads/..." }

# Вырезать фон (AI)
POST /api/remove-bg                          [требует auth]
Body: { "src": "/uploads/file.jpg", "model": "u2net", "points": "x,y;x2,y2,0", "rect": "" }
# model: u2net | u2net_human_seg | isnet-general-use | silueta
# points: опционально, активирует SAM (точки через ; )
# Возвращает: { ok: true, path: "/uploads/file_no_bg_TIMESTAMP.webp" }
```

---

## Автономное создание сцен

### Быстрый старт (одна команда)

```bash
# Установить API ключ (один раз, бесплатно на pexels.com)
export PEXELS_API_KEY=your_key_here

# Создать одну сцену
python3 build_scene.py "Angel appearing to shepherd"

# Создать несколько сцен
python3 build_scene.py "Noah's flood" --scenes 3

# Проверить без сохранения
python3 build_scene.py "Crucifixion at Golgotha" --dry-run

# Опции
python3 build_scene.py --help
```

### CLI команды для пошаговой работы

```bash
# 1. Поиск картинок
uuk-timeline image search -q "angel wings white background" --per-page 10

# 2. Скачать выбранную картинку
uuk-timeline image fetch --url "https://images.pexels.com/photos/1234/photo.jpeg"

# 3. Вырезать фон
uuk-timeline image cutout --src /uploads/1234_photo.jpeg --model u2net

# 4. Для людей/фигур
uuk-timeline image cutout --src /uploads/person.jpg --model u2net_human_seg

# 5. Указать точку на нужном объекте (SAM)
uuk-timeline image cutout --src /uploads/scene.jpg --point 450,300

# 6. Добавить сцену с результатом
uuk-timeline scene add --title "Благовещение" --year "Благов." --night
uuk-timeline element add 0 \
  --src /uploads/result_no_bg_123.webp \
  --x 0.3 --bottom 0 --h 75 --parallax 1.2 --anim float
```

### Переменные окружения

| Переменная | Описание |
|-----------|----------|
| `PEXELS_API_KEY` | Ключ Pexels (бесплатно: pexels.com/api) |
| `PIXABAY_API_KEY` | Ключ Pixabay (бесплатно: pixabay.com/api) |
| `UUK_SERVER` | URL сервера (по умолчанию http://localhost:3000) |
| `UUK_ADMIN_USER` | Логин (по умолчанию timelineAdmin) |
| `UUK_ADMIN_PASS` | Пароль (по умолчанию из server.js) |

### Советы агенту

1. **Запросы на английском** дают лучшие результаты в Pexels/Pixabay.
2. **Для людей и фигур** → `--model u2net_human_seg`; для чётких краёв → `isnet-general-use`.
3. **Если первый результат поиска плохой** — используй несколько разных запросов и выбери лучший `url` из `results`.
4. **Проверяй результат** через `uuk-timeline scenes list` после создания.
5. **Фоны** — используй готовые из `/uploads/` (см. таблицу выше), не скачивай новые.
6. **`build_scene.py`** делает всё автоматически; используй пошаговые CLI команды только если нужен контроль над каждым шагом.

---

## Примеры

### Сцена с изображениями и текстом

```json
{
  "id": 17,
  "title": "Благовещение",
  "subtitle": "«Радуйся, Благодатная! Господь с Тобою» — Луки 1:28",
  "date": "~7–5 лет до н.э.",
  "year": "Благовестие",
  "bg": "/uploads/вариации_2K_202603191339-2.jpg",
  "night": true,
  "elements": [
    {
      "src": "/uploads/0009.png",
      "x": 0.28,
      "h": 78,
      "bottom": 0,
      "parallax": 1.2,
      "anim": "float",
      "content": "<h3>Архангел Гавриил</h3><p>Посланник Бога, принёсший Марии весть о рождении Спасителя.</p>"
    },
    {
      "src": "/uploads/0012.png",
      "x": 0.68,
      "h": 45,
      "bottom": 0.2,
      "parallax": 0.8,
      "anim": "zoom"
    },
    {
      "type": "text",
      "text": "Благовещение",
      "font": "'Cormorant Garamond', serif",
      "fontSize": 6,
      "fontWeight": 300,
      "fontStyle": "italic",
      "color": "#f0d880",
      "opacity": 0.85,
      "textAlign": "left",
      "letterSpacing": 0.15,
      "lineHeight": 1.2,
      "textShadow": "0 0 30px rgba(240,200,80,0.5),0 2px 20px rgba(0,0,0,0.9)",
      "textTransform": "",
      "maxWidth": 0,
      "x": 0.5,
      "bottom": 0.72,
      "parallax": 0.4
    },
    {
      "src": "/uploads/3D Glass Flowers (5).png",
      "x": 0.05,
      "h": 55,
      "bottom": 0,
      "anim": "float"
    }
  ]
}
```

### Пример PUT /api/scenes

```bash
curl -X PUT http://localhost:3000/api/scenes \
  -H "Content-Type: application/json" \
  -d '{"name":"Моя история","scenes":[...]}'
```

---

## Советы

1. **`elements` — единый массив** для всего: изображений и текстов. Порядок = порядок отрисовки (первый = дальний план).

2. **`parallax`**: дальние фоновые объекты → 0–0.5. Средний план → 0.8–1.2. Передний план → 1.5–2.0. Текст → 0.3–0.6.

3. **`night: true`** включает звёзды — используй для ночных, таинственных и мрачных сцен.

4. **`bg_video`** перекрывает `bg` — используй оба поля (на случай, если видео не загружается).

5. **Текст на сцене**: `maxWidth: 0` = одна строка авто-ширина. `maxWidth: 35` = блок шириной 35vw с переносом.

6. **Панорама**: `elements` — видимые объекты с анимацией. `clickAreas` — невидимые зоны. Лучше иметь оба для каждой точки входа.

7. **`year` на таймлайне** — максимум 8–10 символов. При большом количестве сцен метки скрываются и видна только активная.

8. **Декоративные цветы** (`3D Glass Flowers`) ставь в начало или конец `elements`, `x` у краёв экрана (0.02–0.12 или 0.82–0.95), `bottom: 0`.
