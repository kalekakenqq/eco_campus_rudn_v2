"""
Unit-тесты для доменных моделей и иерархии исключений EcoCampus.
"""

import pytest

from eco_campus.core.exceptions import (
    ClassificationError,
    ContainerNotFoundError,
    InvalidWasteTypeError,
    LocationNotFoundError,
    NoRouteError,
)
from eco_campus.core.models import (
    ClassificationResult,
    Container,
    Coordinates,
    Route,
    RouteStep,
    WasteType,
)


class TestCoordinates:
    def test_valid_coordinates_created(self) -> None:
        coords = Coordinates(55.6492, 37.4843)
        assert coords.lat == 55.6492
        assert coords.lon == 37.4843

    def test_invalid_latitude_raises(self) -> None:
        with pytest.raises(ValueError):
            Coordinates(lat=91.0, lon=37.0)

    def test_invalid_longitude_raises(self) -> None:
        with pytest.raises(ValueError):
            Coordinates(lat=55.0, lon=181.0)

    def test_boundary_values_accepted(self) -> None:
        Coordinates(lat=90.0, lon=180.0)
        Coordinates(lat=-90.0, lon=-180.0)

    def test_coordinates_are_immutable(self) -> None:
        coords = Coordinates(55.0, 37.0)
        with pytest.raises(Exception):
            coords.lat = 56.0  # type: ignore[misc]


class TestWasteType:
    def test_all_types_have_labels(self) -> None:
        for wt in WasteType:
            assert wt.label(), f"WasteType.{wt.name} не имеет метки"

    def test_plastic_label_in_russian(self) -> None:
        assert "Пластик" in WasteType.PLASTIC.label()

    def test_electronics_label_in_russian(self) -> None:
        assert "Электроника" in WasteType.ELECTRONICS.label()

    def test_value_from_string(self) -> None:
        wt = WasteType("plastic")
        assert wt == WasteType.PLASTIC


class TestContainer:
    @pytest.fixture
    def sample_container(self) -> Container:
        return Container(
            container_id="test_01",
            name="Тестовый контейнер",
            location_name="main_entrance",
            coordinates=Coordinates(55.6492, 37.4843),
            accepted_types=[WasteType.PLASTIC, WasteType.PAPER],
            working_hours="09:00-21:00",
        )

    def test_accepts_correct_type(self, sample_container: Container) -> None:
        assert sample_container.accepts(WasteType.PLASTIC) is True
        assert sample_container.accepts(WasteType.PAPER) is True

    def test_rejects_wrong_type(self, sample_container: Container) -> None:
        assert sample_container.accepts(WasteType.GLASS) is False
        assert sample_container.accepts(WasteType.ELECTRONICS) is False

    def test_default_is_active(self, sample_container: Container) -> None:
        assert sample_container.is_active is True

    def test_can_be_deactivated(self, sample_container: Container) -> None:
        sample_container.is_active = False
        assert sample_container.is_active is False


class TestRoute:
    @pytest.fixture
    def sample_route(self) -> Route:
        container = Container(
            container_id="c_test",
            name="Тестовый экопункт",
            location_name="canteen",
            coordinates=Coordinates(55.6512, 37.4831),
            accepted_types=[WasteType.PLASTIC],
            working_hours="07:00-23:00",
        )
        return Route(
            target_container=container,
            waste_type=WasteType.PLASTIC,
            steps=[
                RouteStep("a", "b", 100.0, "Идите от A к B"),
                RouteStep("b", "c", 150.0, "Идите от B к C"),
            ],
            total_distance_meters=250.0,
            estimated_minutes=3.125,
        )

    def test_summary_contains_container_name(self, sample_route: Route) -> None:
        assert "Тестовый экопункт" in sample_route.summary()

    def test_summary_shows_distance_in_meters(self, sample_route: Route) -> None:
        assert "250" in sample_route.summary()

    def test_summary_shows_km_for_long_routes(self) -> None:
        container = Container(
            container_id="c_far",
            name="Дальний экопункт",
            location_name="fii_building",
            coordinates=Coordinates(55.6891, 37.6102),
            accepted_types=[WasteType.ELECTRONICS],
            working_hours="09:00-19:00",
        )
        route = Route(
            target_container=container,
            waste_type=WasteType.ELECTRONICS,
            total_distance_meters=1500.0,
            estimated_minutes=18.75,
        )
        assert "км" in route.summary()


class TestExceptions:
    def test_location_not_found_has_correct_code(self) -> None:
        exc = LocationNotFoundError("unknown_node")
        assert exc.code == "LOCATION_NOT_FOUND"
        assert "unknown_node" in exc.message

    def test_container_not_found_has_correct_code(self) -> None:
        exc = ContainerNotFoundError("Стекло")
        assert exc.code == "CONTAINER_NOT_FOUND"
        assert "Стекло" in exc.message

    def test_no_route_contains_both_nodes(self) -> None:
        exc = NoRouteError("point_a", "point_b")
        assert "point_a" in exc.message
        assert "point_b" in exc.message

    def test_invalid_waste_type_has_correct_code(self) -> None:
        exc = InvalidWasteTypeError("unknown_type")
        assert exc.code == "INVALID_WASTE_TYPE"
        assert "unknown_type" in exc.message

    def test_classification_error_has_correct_code(self) -> None:
        exc = ClassificationError("непонятный текст")
        assert exc.code == "CLASSIFICATION_ERROR"

    def test_all_exceptions_inherit_from_base(self) -> None:
        from eco_campus.core.exceptions import EcoCampusError
        assert issubclass(LocationNotFoundError, EcoCampusError)
        assert issubclass(ContainerNotFoundError, EcoCampusError)
        assert issubclass(NoRouteError, EcoCampusError)


class TestClassificationResult:
    def test_confident_above_threshold(self) -> None:
        result = ClassificationResult(
            waste_type=WasteType.PLASTIC,
            confidence=0.8,
            matched_keywords=["бутылка", "пластик"],
        )
        assert result.is_confident(threshold=0.5) is True

    def test_not_confident_below_threshold(self) -> None:
        result = ClassificationResult(
            waste_type=WasteType.MIXED,
            confidence=0.3,
            matched_keywords=[],
        )
        assert result.is_confident(threshold=0.5) is False
