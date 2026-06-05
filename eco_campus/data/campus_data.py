"""
База данных узлов графа и контейнеров кампуса РУДН.

Координаты зданий основаны на реальном расположении объектов.
Основной кампус: ул. Миклухо-Маклая, 6 (55.6492, 37.4843)
Корпус ФИИ-1: Подольское ш., 8с5 (55.6891, 37.6102)
Корпус ФИИ-2: Ленинский пр., 95 (55.6612, 37.5234)
"""

from eco_campus.core.models import Container, Coordinates, WasteType

CAMPUS_NODES: dict[str, dict] = {
    # ── Основной кампус (Миклухо-Маклая) ──
    "main_entrance": {
        "display": "Главный вход РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6492, 37.4843),
    },
    "main_building": {
        "display": "Главный корпус РУДН (Миклухо-Маклая, 6)",
        "coords": Coordinates(55.6501, 37.4838),
    },
    "building_8": {
        "display": "Корпус АТИ (Миклухо-Маклая, 8к2)",
        "coords": Coordinates(55.6518, 37.4821),
    },
    "building_10": {
        "display": "Корпус 10/2",
        "coords": Coordinates(55.6534, 37.4809),
    },
    "building_5": {
        "display": "Корпус 5",
        "coords": Coordinates(55.6525, 37.4815),
    },
    "library": {
        "display": "Научная библиотека РУДН",
        "coords": Coordinates(55.6508, 37.4852),
    },
    "interclub": {
        "display": "Интерклуб РУДН",
        "coords": Coordinates(55.6545, 37.4798),
    },
    "canteen": {
        "display": "Студенческая столовая РУДН",
        "coords": Coordinates(55.6512, 37.4831),
    },
    "sports_complex": {
        "display": "Спортивный комплекс РУДН",
        "coords": Coordinates(55.6498, 37.4862),
    },
    "medical_center": {
        "display": "Медицинский центр РУДН",
        "coords": Coordinates(55.6503, 37.4857),
    },
    "dorm_complex": {
        "display": "Комплекс общежитий (Миклухо-Маклая, 3)",
        "coords": Coordinates(55.6558, 37.4787),
    },
    "dorm_north": {
        "display": "Общежития — северный блок",
        "coords": Coordinates(55.6571, 37.4778),
    },
    "park": {
        "display": "Парк кампуса РУДН",
        "coords": Coordinates(55.6562, 37.4772),
    },
    # ── Корпуса ФИИ ──
    "fii_building": {
        "display": "Корпус ФИИ (Подольское ш., 8с5)",
        "coords": Coordinates(55.6891, 37.6102),
    },
    "fii_leninsky": {
        "display": "Корпус ФИИ (Ленинский пр-т, 95)",
        "coords": Coordinates(55.6612, 37.5234),
    },
    "fii_tulskaya": {
        "display": "Корпус ФИИ (ул. Тульская)",
        "coords": Coordinates(55.7198, 37.6298),
    },
    # ── Точки сбора (отдельные ноды рядом с корпусами) ──
    "eco_fii_podolsk": {
        "display": "Экопункт у ФИИ (Подольское ш.)",
        "coords": Coordinates(55.6893, 37.6115),
    },
    "eco_fii_leninsky": {
        "display": "Экопункт у ФИИ (Ленинский пр-т)",
        "coords": Coordinates(55.6615, 37.5245),
    },
}

CAMPUS_EDGES: list[tuple[str, str, float]] = [
    # Основной кампус
    ("main_entrance", "main_building", 100),
    ("main_entrance", "sports_complex", 180),
    ("main_entrance", "library", 150),
    ("main_building", "canteen", 90),
    ("main_building", "building_8", 200),
    ("main_building", "library", 120),
    ("building_8", "canteen", 100),
    ("building_8", "building_10", 180),
    ("building_8", "building_5", 120),
    ("building_10", "interclub", 130),
    ("building_10", "dorm_complex", 280),
    ("building_5", "building_10", 100),
    ("interclub", "dorm_complex", 150),
    ("dorm_complex", "dorm_north", 130),
    ("dorm_complex", "park", 100),
    ("dorm_north", "park", 100),
    ("canteen", "library", 110),
    ("canteen", "medical_center", 60),
    ("library", "sports_complex", 100),
    ("sports_complex", "medical_center", 70),
    ("sports_complex", "main_entrance", 180),
    # Корпуса ФИИ — связаны с основным кампусом
    ("fii_building", "main_entrance", 950),
    ("fii_leninsky", "main_entrance", 600),
    ("fii_leninsky", "fii_building", 1200),
    ("fii_tulskaya", "fii_building", 800),
    ("fii_tulskaya", "fii_leninsky", 900),
    # Экопункты ФИИ — отдельные ноды в 150-200м от корпусов
    ("fii_building", "eco_fii_podolsk", 150),
    ("fii_leninsky", "eco_fii_leninsky", 120),
    ("eco_fii_podolsk", "eco_fii_leninsky", 1100),
]

CONTAINERS: list[Container] = [
    Container(
        container_id="c01",
        name="Экопункт у главного входа",
        location_name="main_entrance",
        coordinates=Coordinates(55.6492, 37.4843),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.METAL],
        working_hours="08:00-22:00",
        description="Раздельные контейнеры у КПП главного входа",
    ),
    Container(
        container_id="c02",
        name="Экопункт у библиотеки",
        location_name="library",
        coordinates=Coordinates(55.6508, 37.4852),
        accepted_types=[WasteType.PAPER, WasteType.ELECTRONICS],
        working_hours="09:00-20:00",
        description="Приём макулатуры и старых учебников",
    ),
    Container(
        container_id="c03",
        name="Экопункт у столовой",
        location_name="canteen",
        coordinates=Coordinates(55.6512, 37.4831),
        accepted_types=[WasteType.PLASTIC, WasteType.GLASS, WasteType.ORGANIC, WasteType.METAL],
        working_hours="07:00-23:00",
        description="Основная точка рядом со студенческой столовой",
    ),
    Container(
        container_id="c04",
        name="Экопункт у общежитий",
        location_name="dorm_complex",
        coordinates=Coordinates(55.6558, 37.4787),
        accepted_types=[WasteType.PLASTIC, WasteType.PAPER, WasteType.GLASS, WasteType.METAL],
        working_hours="Круглосуточно",
        description="Доступен круглосуточно для жителей общежитий",
    ),
    Container(
        container_id="c05",
        name="Экопункт в парке кампуса",
        location_name="park",
        coordinates=Coordinates(55.6562, 37.4772),
        accepted_types=[WasteType.MIXED, WasteType.ORGANIC],
        working_hours="08:00-21:00",
        description="Контейнеры в зелёной зоне кампуса",
    ),
    Container(
        container_id="c06",
        name="Экопункт у спорткомплекса",
        location_name="sports_complex",
        coordinates=Coordinates(55.6498, 37.4862),
        accepted_types=[WasteType.PLASTIC, WasteType.TEXTILE, WasteType.METAL],
        working_hours="07:00-22:00",
        description="Приём спортивной одежды и инвентаря",
    ),
    Container(
        container_id="c07",
        name="Экопункт ФИИ (Подольское ш.)",
        location_name="eco_fii_podolsk",
        coordinates=Coordinates(55.6893, 37.6115),
        accepted_types=[WasteType.ELECTRONICS, WasteType.PAPER, WasteType.PLASTIC],
        working_hours="09:00-19:00",
        description="Сбор электронного мусора и батареек — 150м от корпуса ФИИ на Подольском ш., 8с5",
    ),
    Container(
        container_id="c08",
        name="Экопункт ФИИ (Ленинский пр-т)",
        location_name="eco_fii_leninsky",
        coordinates=Coordinates(55.6615, 37.5245),
        accepted_types=[WasteType.ELECTRONICS, WasteType.PAPER, WasteType.PLASTIC, WasteType.METAL],
        working_hours="09:00-20:00",
        description="Раздельный сбор — 120м от корпуса ФИИ на Ленинском проспекте, 95",
    ),
]
