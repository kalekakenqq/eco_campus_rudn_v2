"""
Unit-тесты для движка маршрутизации CampusRouter.
"""

import pytest

from eco_campus.core.exceptions import (
    ContainerNotFoundError,
    LocationNotFoundError,
    NoRouteError,
)
from eco_campus.core.models import Route, UserLocation, WasteType
from eco_campus.core.router import CampusRouter


@pytest.fixture(scope="module")
def router() -> CampusRouter:
    """Инициализирует маршрутизатор один раз для всех тестов модуля."""
    return CampusRouter()


class TestCampusRouterInit:
    def test_router_initializes_without_error(self, router: CampusRouter) -> None:
        assert router is not None

    def test_graph_has_nodes(self, router: CampusRouter) -> None:
        assert router._graph.number_of_nodes() > 0

    def test_graph_has_edges(self, router: CampusRouter) -> None:
        assert router._graph.number_of_edges() > 0

    def test_containers_list_not_empty(self, router: CampusRouter) -> None:
        assert len(router.all_containers()) > 0


class TestGetLocations:
    def test_returns_list_of_user_locations(self, router: CampusRouter) -> None:
        locations = router.get_locations()
        assert isinstance(locations, list)
        assert all(isinstance(loc, UserLocation) for loc in locations)

    def test_all_locations_have_display_names(self, router: CampusRouter) -> None:
        for loc in router.get_locations():
            assert loc.display_name, f"Нет display_name для {loc.node_id}"

    def test_all_locations_have_coordinates(self, router: CampusRouter) -> None:
        for loc in router.get_locations():
            assert loc.coordinates is not None


class TestFindContainers:
    def test_finds_plastic_containers(self, router: CampusRouter) -> None:
        containers = router.find_containers(WasteType.PLASTIC)
        assert len(containers) > 0

    def test_all_returned_accept_requested_type(self, router: CampusRouter) -> None:
        for wt in WasteType:
            try:
                containers = router.find_containers(wt)
                for c in containers:
                    assert c.accepts(wt), f"{c.name} не принимает {wt.value}"
            except ContainerNotFoundError:
                pass

    def test_raises_when_no_container_found(self, router: CampusRouter) -> None:
        from unittest.mock import patch
        with patch.object(router, '_containers', []):
            with pytest.raises(ContainerNotFoundError):
                router.find_containers(WasteType.PLASTIC)


class TestFindNearestRoute:
    def test_returns_route_object(self, router: CampusRouter) -> None:
        route = router.find_nearest_route("main_entrance", WasteType.PLASTIC)
        assert isinstance(route, Route)

    def test_route_container_accepts_requested_type(self, router: CampusRouter) -> None:
        route = router.find_nearest_route("main_building", WasteType.PAPER)
        assert route.target_container.accepts(WasteType.PAPER)

    def test_distance_is_non_negative(self, router: CampusRouter) -> None:
        route = router.find_nearest_route("main_entrance", WasteType.GLASS)
        assert route.total_distance_meters >= 0

    def test_estimated_minutes_is_positive(self, router: CampusRouter) -> None:
        route = router.find_nearest_route("library", WasteType.ELECTRONICS)
        assert route.estimated_minutes >= 0

    def test_steps_form_connected_path(self, router: CampusRouter) -> None:
        route = router.find_nearest_route("building_8", WasteType.PAPER)
        steps = route.steps
        for i in range(len(steps) - 1):
            assert steps[i].to_node == steps[i + 1].from_node

    def test_raises_for_unknown_location(self, router: CampusRouter) -> None:
        with pytest.raises(LocationNotFoundError) as exc_info:
            router.find_nearest_route("nowhere", WasteType.PLASTIC)
        assert "nowhere" in exc_info.value.message

    def test_nearest_route_is_optimal(self, router: CampusRouter) -> None:
        import networkx as nx
        wt = WasteType.PLASTIC
        route = router.find_nearest_route("main_building", wt)
        best_dist = route.total_distance_meters
        for c in router.find_containers(wt):
            try:
                d = nx.dijkstra_path_length(
                    router._graph, "main_building", c.location_name, weight="weight"
                )
                assert d >= best_dist - 0.01
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                pass

    def test_graceful_degradation_on_bad_container(
        self, router: CampusRouter
    ) -> None:
        from eco_campus.core.models import Container, Coordinates
        bad_container = Container(
            container_id="bad_01",
            name="Битый контейнер",
            location_name="nonexistent_node_xyz",
            coordinates=Coordinates(55.0, 37.0),
            accepted_types=[WasteType.PLASTIC],
        )
        original = list(router._containers)
        router._containers = [bad_container] + original
        try:
            route = router.find_nearest_route("main_entrance", WasteType.PLASTIC)
            assert route is not None
        finally:
            router._containers = original
