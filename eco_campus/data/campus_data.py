"""
База данных узлов графа и контейнеров кампуса РУДН.

Все координаты проверены по Яндекс.Картам.
Миклухо-Маклая, 6 (главный корпус): 55.652014, 37.499372
Миклухо-Маклая, 4 (спорткомплекс): 55.651999, 37.495410
Подольское ш., 8с5 (ФИИ): 55.714460, 37.624310
"""

from eco_campus.core.models import Container, Coordinates, WasteType

CAMPUS_NODES: dict[str, dict] = {
    # ── Основной кампус ул. Миклухо-Маклая ──
    "main_entrance": {
        "display": "Главный вход РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6520, 37.4994),
    },
    "main_building": {
        "display": "Главный корпус РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6523, 37.4990),
    },
    "library": {
        "display": "Научная библиотека РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6526, 37.4985),
    },
    "canteen": {
        "display": "Студенческая столовая РУДН",
        "coords": Coordinates(55.6530, 37.4980),
    },
    "building_8": {
        "display": "Корпус РУДН (Миклухо-Маклая, 8к2)",
        "coords": Coordinates(55.6538, 37.4974),
    },
    "building_9": {
        "display": "Корпус РУДН (Миклухо-Маклая, 9)",
        "coords": Coordinates(55.6545, 37.4968),
    },
    "building_10": {
        "display": "Корпус РУДН (Миклухо-Маклая, 10)",
        "coords": Coordinates(55.6552, 37.4960),
    },
    "interclub": {
        "display": "Интерклуб РУДН",
        "coords": Coordinates(55.6558, 37.4952),
    },
    "sports_complex": {
        "display": "Спортивный комплекс РУДН (Миклухо-Маклая, 4)",
        "coords": Coordinates(55.6520, 37.4954),
    },
    "medical_center": {
        "display": "Медицинский центр РУДН",
        "coords": Coordinates(55.6516, 37.4970),
    },
    "dorm_complex": {
        "display": "Комплекс общежитий (Миклухо-Маклая, 3)",
        "coords": Coordinates(55.6560, 37.4940),
    },
    "dorm_north": {
        "display": "Общежития — северный блок",
        "coords": Coordinates(55.6572, 37.4928),
    },
    "park": {
        "display": "Парк кампуса РУДН",
        "coords": Coordinates(55.6564, 37.4935),
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
    ("main_building", "library", 60),
    ("main_building", "canteen", 80),
    ("library", "canteen", 50),
    ("canteen", "building_8", 120),
    ("canteen", "medical_center", 80),
    ("building_8", "building_9", 80),
    ("building_8", "building_10", 150),
    ("building_9", "building_10", 80),
    ("building_10", "interclub", 130),
    ("building_10", "dorm_complex", 250),
    ("interclub", "dorm_complex", 140),
    ("dorm_complex", "dorm_north", 130),
    ("dorm_complex", "park", 100),
    ("dorm_north", "park", 100),
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
        location_name="main_entrance",
        coordinates=Coordinates(55.6520, 37.4994),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.METAL],
        working_hours="08:00-22:00",
        description="Раздельные контейнеры у КПП главного входа РУДН",
    ),
    Container(
        container_id="c02",
        name="Экопункт у библиотеки",
        location_name="library",
        coordinates=Coordinates(55.6526, 37.4985),
        accepted_types=[WasteType.PAPER, WasteType.ELECTRONICS],
        working_hours="09:00-20:00",
        description="Приём макулатуры и старых учебников",
    ),
    Container(
        container_id="c03",
        name="Экопункт у столовой",
        location_name="canteen",
        coordinates=Coordinates(55.6530, 37.4980),
        accepted_types=[WasteType.PLASTIC, WasteType.GLASS, WasteType.ORGANIC, WasteType.METAL],
        working_hours="07:00-23:00",
        description="Основная точка рядом со студенческой столовой",
    ),
    Container(
        container_id="c04",
        name="Экопункт у общежитий",
        location_name="dorm_complex",
        coordinates=Coordinates(55.6560, 37.4940),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.GLASS, WasteType.METAL],
        working_hours="Круглосуточно",
        description="Доступен круглосуточно для жителей общежитий",
    ),
    Container(
        container_id="c05",
        name="Экопункт в парке кампуса",
        location_name="park",
        coordinates=Coordinates(55.6564, 37.4935),
        accepted_types=[WasteType.MIXED, WasteType.ORGANIC],
        working_hours="08:00-21:00",
        description="Контейнеры в зелёной зоне кампуса",
    ),
    Container(
        container_id="c06",
        name="Экопункт у спорткомплекса",
        location_name="sports_complex",
        coordinates=Coordinates(55.6520, 37.4954),
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
        description="Сбор электронного мусора и батареек — 150м от корпуса ФИИ, Подольское ш., 8с5",
    ),
]
