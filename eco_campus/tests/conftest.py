"""
Общие фикстуры для тестов EcoCampus.
"""

import pytest

from eco_campus.core.models import Container, Coordinates, WasteType
from eco_campus.core.router import CampusRouter


@pytest.fixture(scope="session")
def campus_router() -> CampusRouter:
    """Инициализирует маршрутизатор один раз на всю сессию тестов."""
    return CampusRouter()


@pytest.fixture
def plastic_container() -> Container:
    """Возвращает тестовый контейнер для пластика."""
    return Container(
        container_id="fixture_01",
        name="Тестовый контейнер для пластика",
        location_name="main_entrance",
        coordinates=Coordinates(55.6492, 37.4843),
        accepted_types=[WasteType.PLASTIC],
        working_hours="09:00-21:00",
        description="Фикстура для тестов",
    )


@pytest.fixture
def multi_type_container() -> Container:
    """Возвращает тестовый контейнер для нескольких типов отходов."""
    return Container(
        container_id="fixture_02",
        name="Многотипный тестовый контейнер",
        location_name="canteen",
        coordinates=Coordinates(55.6512, 37.4831),
        accepted_types=[
            WasteType.PLASTIC,
            WasteType.GLASS,
            WasteType.METAL,
            WasteType.ORGANIC,
        ],
        working_hours="07:00-23:00",
        description="Фикстура для тестов",
    )
