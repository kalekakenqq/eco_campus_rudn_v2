"""
Интеграционные тесты для REST API EcoCampus.

Проверяют корректность работы всех эндпоинтов, включая
коды ответов, структуру данных и обработку ошибок.
"""

import pytest
from fastapi.testclient import TestClient

import eco_campus.api.app as api_module
from eco_campus.api.app import app
from eco_campus.core.router import CampusRouter


@pytest.fixture(scope="module")
def client() -> TestClient:
    """Создаёт тестовый клиент с инициализированным маршрутизатором."""
    api_module._router = CampusRouter()
    with TestClient(app) as c:
        yield c


class TestApiInfoEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api")
        assert resp.status_code == 200

    def test_response_contains_service_name(self, client: TestClient) -> None:
        data = client.get("/api").json()
        assert "EcoCampus" in data["service"]

    def test_response_contains_version(self, client: TestClient) -> None:
        data = client.get("/api").json()
        assert "version" in data


class TestLocationsEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/locations")
        assert resp.status_code == 200

    def test_returns_non_empty_list(self, client: TestClient) -> None:
        data = client.get("/locations").json()
        assert len(data) > 0

    def test_each_location_has_required_fields(self, client: TestClient) -> None:
        location = client.get("/locations").json()[0]
        assert "node_id" in location
        assert "display_name" in location
        assert "lat" in location
        assert "lon" in location

    def test_display_names_are_non_empty(self, client: TestClient) -> None:
        for loc in client.get("/locations").json():
            assert loc["display_name"], f"Пустой display_name у {loc['node_id']}"


class TestWasteTypesEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/waste-types")
        assert resp.status_code == 200

    def test_returns_non_empty_list(self, client: TestClient) -> None:
        data = client.get("/waste-types").json()
        assert len(data) > 0

    def test_each_type_has_value_and_label(self, client: TestClient) -> None:
        for item in client.get("/waste-types").json():
            assert "value" in item
            assert "label" in item
            assert item["label"]


class TestContainersEndpoint:
    def test_returns_all_containers(self, client: TestClient) -> None:
        resp = client.get("/containers")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_filter_by_plastic_returns_results(self, client: TestClient) -> None:
        resp = client.get("/containers?waste_type=plastic")
        assert resp.status_code == 200
        assert len(resp.json()) > 0

    def test_filter_by_invalid_type_returns_422(self, client: TestClient) -> None:
        resp = client.get("/containers?waste_type=unknown_type")
        assert resp.status_code == 422

    def test_container_has_required_fields(self, client: TestClient) -> None:
        container = client.get("/containers").json()[0]
        for field in ("container_id", "name", "accepted_types", "lat", "lon", "working_hours"):
            assert field in container

    def test_accepted_types_are_non_empty(self, client: TestClient) -> None:
        for c in client.get("/containers").json():
            assert len(c["accepted_types"]) > 0


class TestRouteEndpoint:
    def test_valid_route_returns_200(self, client: TestClient) -> None:
        resp = client.get("/route?from_location=main_entrance&waste_type=plastic")
        assert resp.status_code == 200

    def test_route_has_container_info(self, client: TestClient) -> None:
        data = client.get("/route?from_location=main_building&waste_type=paper").json()
        assert "container" in data
        assert data["container"]["name"]

    def test_route_has_steps(self, client: TestClient) -> None:
        data = client.get("/route?from_location=building_8&waste_type=paper").json()
        assert "steps" in data

    def test_route_has_eco_tip(self, client: TestClient) -> None:
        data = client.get("/route?from_location=main_entrance&waste_type=plastic").json()
        assert "eco_tip" in data
        assert len(data["eco_tip"]) > 0

    def test_route_distance_is_non_negative(self, client: TestClient) -> None:
        data = client.get("/route?from_location=library&waste_type=paper").json()
        assert data["total_distance_meters"] >= 0

    def test_route_minutes_is_non_negative(self, client: TestClient) -> None:
        data = client.get("/route?from_location=canteen&waste_type=glass").json()
        assert data["estimated_minutes"] >= 0

    def test_unknown_location_returns_404(self, client: TestClient) -> None:
        resp = client.get("/route?from_location=mars&waste_type=plastic")
        assert resp.status_code == 404

    def test_unknown_waste_type_returns_422(self, client: TestClient) -> None:
        resp = client.get("/route?from_location=main_entrance&waste_type=moonrocks")
        assert resp.status_code == 422

    def test_route_summary_is_non_empty(self, client: TestClient) -> None:
        data = client.get("/route?from_location=main_entrance&waste_type=metal").json()
        assert len(data["summary"]) > 0


class TestStatsEndpoint:
    def test_returns_200(self, client: TestClient) -> None:
        resp = client.get("/stats")
        assert resp.status_code == 200

    def test_has_required_fields(self, client: TestClient) -> None:
        data = client.get("/stats").json()
        assert "total_routes" in data
        assert "uptime" in data
        assert "top_waste_types" in data
        assert "top_locations" in data

    def test_total_routes_is_integer(self, client: TestClient) -> None:
        data = client.get("/stats").json()
        assert isinstance(data["total_routes"], int)


class TestEcoTipEndpoint:
    def test_returns_tip_for_valid_type(self, client: TestClient) -> None:
        resp = client.get("/eco-tip?waste_type=plastic")
        assert resp.status_code == 200
        data = resp.json()
        assert "tip" in data
        assert len(data["tip"]) > 0

    def test_returns_422_for_invalid_type(self, client: TestClient) -> None:
        resp = client.get("/eco-tip?waste_type=unknown")
        assert resp.status_code == 422

    def test_tip_changes_between_calls(self, client: TestClient) -> None:
        tips = set()
        for _ in range(10):
            data = client.get("/eco-tip?waste_type=plastic").json()
            tips.add(data["tip"])
        assert len(tips) > 1


# ── Тесты /admin панели ──────────────────────────────────────────

def test_admin_no_auth(client: TestClient) -> None:
    """Без авторизации /admin возвращает 401."""
    resp = client.get("/admin")
    assert resp.status_code == 401


def test_admin_wrong_password(client: TestClient) -> None:
    """Неверный пароль — 401."""
    resp = client.get("/admin", auth=("admin", "wrong"))
    assert resp.status_code == 401


def test_admin_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Верные учётные данные — 200 и HTML с ключевыми элементами."""
    import eco_campus.api.app as app_module
    monkeypatch.setattr(app_module, "ADMIN_USER", "admin")
    monkeypatch.setattr(app_module, "ADMIN_PASS", "ecocampus2024")
    resp = client.get("/admin", auth=("admin", "ecocampus2024"))
    assert resp.status_code == 200
    assert "EcoCampus" in resp.text
    assert "Панель администратора" in resp.text
    assert "CO" in resp.text
