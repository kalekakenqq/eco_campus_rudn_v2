"""
База данных узлов графа и контейнеров кампуса РУДН.

Координаты выверены по OpenStreetMap / Яндекс.Картам.
Главный вход РУДН (Миклухо-Маклая, 6): 55.6520, 37.4993

Архитектура графа:
  - Узлы локаций (main_entrance, canteen ...) — точки где стоит пользователь
  - Узлы контейнеров (c01_node, c02_node ...) — точки где стоит контейнер
  - Контейнерный узел всегда на >=40м от ближайшей локации → расстояние всегда > 0
"""

from eco_campus.core.models import Container, Coordinates, WasteType

# ── Публичные локации (показываются пользователю как стартовые точки) ──
CAMPUS_NODES: dict[str, dict] = {
    "main_entrance": {
        "display": "Главный вход РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6520, 37.4993),
    },
    "main_building": {
        "display": "Главный корпус РУДН",
        "coords": Coordinates(55.6524, 37.4988),
    },
    "library": {
        "display": "Научная библиотека РУДН",
        "coords": Coordinates(55.6534, 37.4979),
    },
    "canteen": {
        "display": "Студенческая столовая РУДН",
        "coords": Coordinates(55.6530, 37.4975),
    },
    "building_8": {
        "display": "Корпус РУДН (Миклухо-Маклая, 8к2)",
        "coords": Coordinates(55.6541, 37.4970),
    },
    "building_9": {
        "display": "Корпус РУДН (Миклухо-Маклая, 9)",
        "coords": Coordinates(55.6548, 37.4963),
    },
    "building_10": {
        "display": "Корпус РУДН (Миклухо-Маклая, 10)",
        "coords": Coordinates(55.6555, 37.4957),
    },
    "interclub": {
        "display": "Интерклуб РУДН",
        "coords": Coordinates(55.6561, 37.4950),
    },
    "sports_complex": {
        "display": "Спортивный комплекс РУДН (Миклухо-Маклая, 4)",
        "coords": Coordinates(55.6519, 37.4955),
    },
    "medical_center": {
        "display": "Медицинский центр РУДН",
        "coords": Coordinates(55.6516, 37.4972),
    },
    "dorm_complex": {
        "display": "Комплекс общежитий (Миклухо-Маклая, 3)",
        "coords": Coordinates(55.6579, 37.4955),
    },
    "dorm_north": {
        "display": "Общежития — северный блок",
        "coords": Coordinates(55.6590, 37.4943),
    },
    "park": {
        "display": "Парк кампуса РУДН",
        "coords": Coordinates(55.6570, 37.4962),
    },
    "fii_building": {
        "display": "Корпус ФИИ (Подольское ш., 8с5)",
        "coords": Coordinates(55.7145, 37.6243),
    },
}

# ── Внутренние узлы (контейнеры + служебные) — не показываются пользователю ──
_INTERNAL_NODES: dict[str, dict] = {
    # Контейнерные узлы — всегда минимум 40м от ближайшей публичной локации
    "c01_node": {
        "display": "Экопункт у главного входа",
        "coords": Coordinates(55.6521, 37.4985),   # 40м от main_entrance
    },
    "c02_node": {
        "display": "Экопункт у библиотеки",
        "coords": Coordinates(55.6537, 37.4976),   # 40м от library
    },
    "c03_node": {
        "display": "Экопункт у столовой",
        "coords": Coordinates(55.6533, 37.4971),   # 45м от canteen
    },
    "c04_node": {
        "display": "Экопункт у общежитий",
        "coords": Coordinates(55.6583, 37.4951),   # 50м от dorm_complex
    },
    "c05_node": {
        "display": "Экопункт в парке",
        "coords": Coordinates(55.6574, 37.4958),   # 50м от park
    },
    "c06_node": {
        "display": "Экопункт у спорткомплекса",
        "coords": Coordinates(55.6522, 37.4950),   # 40м от sports_complex
    },
    "c07_node": {
        "display": "Экопункт ФИИ",
        "coords": Coordinates(55.7148, 37.6250),   # 80м от fii_building
    },
}

CAMPUS_NODES_ALL = {**CAMPUS_NODES, **_INTERNAL_NODES}

CAMPUS_EDGES: list[tuple[str, str, float]] = [
    # ── Основной кампус ──
    ("main_entrance",  "main_building",  50),
    ("main_entrance",  "sports_complex", 180),
    ("main_entrance",  "medical_center", 120),
    ("main_building",  "library",        100),
    ("main_building",  "canteen",        80),
    ("library",        "canteen",        60),
    ("canteen",        "building_8",     120),
    ("canteen",        "medical_center", 80),
    ("building_8",     "building_9",     80),
    ("building_8",     "building_10",    150),
    ("building_9",     "building_10",    80),
    ("building_10",    "interclub",      130),
    ("building_10",    "dorm_complex",   280),
    ("interclub",      "dorm_complex",   160),
    ("dorm_complex",   "dorm_north",     130),
    ("dorm_complex",   "park",           100),
    ("dorm_north",     "park",           110),
    ("sports_complex", "medical_center", 80),
    ("sports_complex", "main_entrance",  180),
    # ── Корпус ФИИ ──
    ("fii_building",   "main_entrance",  9500),
    # ── Контейнерные рёбра (локация → контейнер) ──
    ("main_entrance",  "c01_node",  40),
    ("main_building",  "c01_node",  30),
    ("library",        "c02_node",  40),
    ("canteen",        "c03_node",  45),
    ("building_8",     "c03_node",  95),
    ("dorm_complex",   "c04_node",  50),
    ("dorm_north",     "c04_node",  90),
    ("park",           "c05_node",  50),
    ("dorm_complex",   "c05_node",  130),
    ("sports_complex", "c06_node",  40),
    ("medical_center", "c06_node",  90),
    ("fii_building",   "c07_node",  80),
]

CONTAINERS: list[Container] = [
    Container(
        container_id="c01",
        name="Экопункт у главного входа",
        location_name="c01_node",
        coordinates=Coordinates(55.6521, 37.4985),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.METAL],
        working_hours="08:00-22:00",
        description="Раздельные контейнеры у главного корпуса РУДН",
    ),
    Container(
        container_id="c02",
        name="Экопункт у библиотеки",
        location_name="c02_node",
        coordinates=Coordinates(55.6537, 37.4976),
        accepted_types=[WasteType.PAPER, WasteType.ELECTRONICS],
        working_hours="09:00-20:00",
        description="Приём макулатуры и старых учебников",
    ),
    Container(
        container_id="c03",
        name="Экопункт у столовой",
        location_name="c03_node",
        coordinates=Coordinates(55.6533, 37.4971),
        accepted_types=[WasteType.PLASTIC, WasteType.GLASS, WasteType.ORGANIC, WasteType.METAL],
        working_hours="07:00-23:00",
        description="Основная точка рядом со студенческой столовой",
    ),
    Container(
        container_id="c04",
        name="Экопункт у общежитий",
        location_name="c04_node",
        coordinates=Coordinates(55.6583, 37.4951),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.GLASS, WasteType.METAL],
        working_hours="Круглосуточно",
        description="Доступен круглосуточно для жителей общежитий",
    ),
    Container(
        container_id="c05",
        name="Экопункт в парке кампуса",
        location_name="c05_node",
        coordinates=Coordinates(55.6574, 37.4958),
        accepted_types=[WasteType.MIXED, WasteType.ORGANIC],
        working_hours="08:00-21:00",
        description="Контейнеры в зелёной зоне кампуса",
    ),
    Container(
        container_id="c06",
        name="Экопункт у спорткомплекса",
        location_name="c06_node",
        coordinates=Coordinates(55.6522, 37.4950),
        accepted_types=[WasteType.PLASTIC, WasteType.TEXTILE, WasteType.METAL],
        working_hours="07:00-22:00",
        description="Приём спортивной одежды и инвентаря",
    ),
    Container(
        container_id="c07",
        name="Экопункт ФИИ (Подольское ш.)",
        location_name="c07_node",
        coordinates=Coordinates(55.7148, 37.6250),
        accepted_types=[WasteType.ELECTRONICS, WasteType.PAPER, WasteType.PLASTIC],
        working_hours="09:00-19:00",
        description="Сбор электронного мусора и батареек",
    ),
]
