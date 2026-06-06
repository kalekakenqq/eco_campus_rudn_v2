"""
База данных узлов графа и контейнеров кампуса РУДН.

Координаты выверены по OpenStreetMap / Яндекс.Картам.
Главный вход РУДН (Миклухо-Маклая, 6): 55.6520, 37.4993
Спорткомплекс (Миклухо-Маклая, 4):     55.6519, 37.4955
Корпус ФИИ (Подольское ш., 8с5):        55.7145, 37.6243
"""

from eco_campus.core.models import Container, Coordinates, WasteType

CAMPUS_NODES: dict[str, dict] = {
    # ── Основной кампус ул. Миклухо-Маклая ──
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
    # ── Корпус ФИИ ──
    "fii_building": {
        "display": "Корпус ФИИ (Подольское ш., 8с5)",
        "coords": Coordinates(55.7145, 37.6243),
    },
}

# Служебные узлы (не показываются пользователю как локации)
_INTERNAL_NODES: dict[str, dict] = {
    "eco_fii_podolsk": {
        "display": "Экопункт у ФИИ (Подольское ш.)",
        "coords": Coordinates(55.7148, 37.6250),
    },
}

# Объединяем для построения графа
CAMPUS_NODES_ALL = {**CAMPUS_NODES, **_INTERNAL_NODES}

CAMPUS_EDGES: list[tuple[str, str, float]] = [
    # Основной кампус
    ("main_entrance", "main_building", 50),
    ("main_entrance", "sports_complex", 180),
    ("main_entrance", "medical_center", 120),
    ("main_building", "library", 100),
    ("main_building", "canteen", 80),
    ("library", "canteen", 60),
    ("canteen", "building_8", 120),
    ("canteen", "medical_center", 80),
    ("building_8", "building_9", 80),
    ("building_8", "building_10", 150),
    ("building_9", "building_10", 80),
    ("building_10", "interclub", 130),
    ("building_10", "dorm_complex", 280),
    ("interclub", "dorm_complex", 160),
    ("dorm_complex", "dorm_north", 130),
    ("dorm_complex", "park", 100),
    ("dorm_north", "park", 110),
    ("sports_complex", "medical_center", 80),
    ("sports_complex", "main_entrance", 180),
    # Корпус ФИИ (далеко от основного кампуса)
    ("fii_building", "main_entrance", 9500),
    ("fii_building", "eco_fii_podolsk", 150),
]

CONTAINERS: list[Container] = [
    Container(
        container_id="c01",
        name="Экопункт у главного входа",
        location_name="main_building",
        coordinates=Coordinates(55.6524, 37.4988),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.METAL],
        working_hours="08:00-22:00",
        description="Раздельные контейнеры у главного корпуса РУДН",
    ),
    Container(
        container_id="c02",
        name="Экопункт у библиотеки",
        location_name="library",
        coordinates=Coordinates(55.6534, 37.4979),
        accepted_types=[WasteType.PAPER, WasteType.ELECTRONICS],
        working_hours="09:00-20:00",
        description="Приём макулатуры и старых учебников",
    ),
    Container(
        container_id="c03",
        name="Экопункт у столовой",
        location_name="canteen",
        coordinates=Coordinates(55.6530, 37.4975),
        accepted_types=[WasteType.PLASTIC, WasteType.GLASS, WasteType.ORGANIC, WasteType.METAL],
        working_hours="07:00-23:00",
        description="Основная точка рядом со студенческой столовой",
    ),
    Container(
        container_id="c04",
        name="Экопункт у общежитий",
        location_name="dorm_complex",
        coordinates=Coordinates(55.6579, 37.4955),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.GLASS, WasteType.METAL],
        working_hours="Круглосуточно",
        description="Доступен круглосуточно для жителей общежитий",
    ),
    Container(
        container_id="c05",
        name="Экопункт в парке кампуса",
        location_name="park",
        coordinates=Coordinates(55.6570, 37.4962),
        accepted_types=[WasteType.MIXED, WasteType.ORGANIC],
        working_hours="08:00-21:00",
        description="Контейнеры в зелёной зоне кампуса",
    ),
    Container(
        container_id="c06",
        name="Экопункт у спорткомплекса",
        location_name="sports_complex",
        coordinates=Coordinates(55.6519, 37.4955),
        accepted_types=[WasteType.PLASTIC, WasteType.TEXTILE, WasteType.METAL],
        working_hours="07:00-22:00",
        description="Приём спортивной одежды и инвентаря",
    ),
    Container(
        container_id="c07",
        name="Экопункт ФИИ (Подольское ш.)",
        location_name="eco_fii_podolsk",
        coordinates=Coordinates(55.7148, 37.6250),
        accepted_types=[WasteType.ELECTRONICS, WasteType.PAPER, WasteType.PLASTIC],
        working_hours="09:00-19:00",
        description="Сбор электронного мусора и батареек — 150м от корпуса ФИИ",
    ),
]
