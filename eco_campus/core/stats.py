"""
Сервис сбора статистики запросов EcoCampus.

Хранит в памяти счётчики маршрутов, популярных типов отходов
и локаций. Данные сбрасываются при перезапуске сервера.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime

from eco_campus.core.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class StatsService:
    """Сервис сбора и хранения статистики запросов."""

    total_routes: int = 0
    waste_type_counter: Counter = field(default_factory=Counter)
    location_counter: Counter = field(default_factory=Counter)
    started_at: datetime = field(default_factory=datetime.now)

    def record_route(self, waste_type: str, location: str) -> None:
        """
        Фиксирует новый запрос маршрута.

        Args:
            waste_type: Человекочитаемое название типа отходов.
            location: Идентификатор стартовой локации.
        """
        self.total_routes += 1
        self.waste_type_counter[waste_type] += 1
        self.location_counter[location] += 1
        logger.debug("Статистика обновлена: всего маршрутов %d", self.total_routes)

    def top_waste_types(self, n: int = 3) -> list[dict]:
        """Возвращает топ-N популярных типов отходов."""
        return [
            {"waste_type": wt, "count": count}
            for wt, count in self.waste_type_counter.most_common(n)
        ]

    def top_locations(self, n: int = 3) -> list[dict]:
        """Возвращает топ-N популярных стартовых локаций."""
        return [
            {"location": loc, "count": count}
            for loc, count in self.location_counter.most_common(n)
        ]

    def co2_saved_kg(self) -> float:
        """
        Рассчитывает примерный объём сэкономленных выбросов CO₂ в кг.

        Методология: согласно данным EPA и EEA, отправка 1 кг смешанных
        отходов на полигон генерирует ~2.5 кг CO₂-эквивалента (метан +
        транспорт). Средний вес одного визита к экопункту — ~0.3 кг.
        Итого: 1 маршрут ≈ 0.75 кг сэкономленного CO₂.
        """
        CO2_PER_ROUTE_KG = 0.75
        return round(self.total_routes * CO2_PER_ROUTE_KG, 2)

    def summary(self) -> dict:
        """Возвращает сводку статистики использования сервиса."""
        uptime = datetime.now() - self.started_at
        hours = int(uptime.total_seconds() // 3600)
        minutes = int((uptime.total_seconds() % 3600) // 60)
        return {
            "total_routes": self.total_routes,
            "uptime": f"{hours}ч {minutes}мин",
            "top_waste_types": self.top_waste_types(),
            "top_locations": self.top_locations(),
            "started_at": self.started_at.strftime("%d.%m.%Y %H:%M"),
            "co2_saved_kg": self.co2_saved_kg(),
        }

stats_service = StatsService()
