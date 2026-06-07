# Как подключить EcoCampus к своему кампусу

EcoCampus — открытая платформа. Любой университет может развернуть свою копию за **один рабочий день**.

---

## 5 шагов для нового кампуса

### Шаг 1 — Форкнуть репозиторий

```bash
git clone https://github.com/kalekakenqq/eco_campus_rudn_v2.git my_campus
cd my_campus
```

### Шаг 2 — Описать граф кампуса

Открыть `eco_campus/data/campus_data.py` и заменить узлы и рёбра.

Каждый узел — точка на территории:

```python
CAMPUS_NODES = {
    "main_entrance": {
        "display": "Главный вход МГУ",
        "coords": Coordinates(55.7028, 37.5300),
    },
    # ... остальные узлы
}
```

Каждое ребро — пешеходный путь между узлами в метрах:

```python
CAMPUS_EDGES = [
    ("main_entrance", "library", 120),
    ("library", "canteen", 80),
    # ...
]
```

### Шаг 3 — Добавить экопункты

```python
CONTAINERS = [
    Container(
        container_id="c01",
        name="Экопункт у 1-го корпуса",
        location_name="c01_node",
        coordinates=Coordinates(55.7029, 37.5298),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER],
        working_hours="09:00-21:00",
        description="Контейнеры у входа в корпус 1",
    ),
]
```

### Шаг 4 — Настроить переменные окружения

Создать файл `.env` по образцу `.env.example`:

```
TELEGRAM_BOT_TOKEN=your_token_here
YANDEX_GPT_API_KEY=your_key_here
YANDEX_GPT_FOLDER_ID=your_folder_id
```

### Шаг 5 — Задеплоить

**Amvera.io (рекомендуется, бесплатный тариф):**

```bash
git add .
git commit -m "feat: кампус МГУ"
git push origin main
# Amvera подхватит автоматически
```

**Локально:**

```bash
pip install -r requirements.txt
bash start.sh
```

---

## Что не нужно менять

- Алгоритм Дейкстры — работает с любым графом автоматически
- TF-IDF классификатор — 1007 ключевых слов уже обучены
- ML предиктор загруженности — адаптируется под суточный ритм
- Весь REST API — документация на `/docs`
- Telegram-бот — только токен из @BotFather

---

## Тарифы B2B

| Размер кампуса | Стоимость в год |
|---|---|
| До 5 000 человек | 30 000 ₽ |
| До 30 000 человек | 80 000 ₽ |
| Корпорация / холдинг | 150 000 ₽ |

Контакт: открыть [Issues](https://github.com/kalekakenqq/eco_campus_rudn_v2/issues) или написать в Telegram [@rudn_eco_bot](https://t.me/rudn_eco_bot).

---

## API для интеграции

```
GET  /route?from_location=main_entrance&waste_type=plastic
GET  /classify?text=старый+телефон
GET  /predict/load?hour=14
GET  /containers
GET  /stats
POST /chat  {"message": "..."}
```

Полная документация: [/docs](https://eco-campus-rudn-scalevillain.amvera.io/docs)
