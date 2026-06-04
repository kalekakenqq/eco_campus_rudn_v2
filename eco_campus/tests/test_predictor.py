"""
Тесты для модуля прогнозирования загруженности экопунктов.
"""

import pytest

from eco_campus.core.predictor import LoadPredictor, load_predictor


class TestLoadPredictor:
    """Тесты для LoadPredictor."""

    def test_singleton_exists(self) -> None:
        """Синглтон load_predictor инициализируется при импорте."""
        assert load_predictor is not None
        assert isinstance(load_predictor, LoadPredictor)

    def test_predict_hour_returns_float(self) -> None:
        """predict_hour возвращает неотрицательное число."""
        predictor = LoadPredictor()
        result = predictor.predict_hour(10)
        assert isinstance(result, float)
        assert result >= 0.0

    def test_predict_hour_peak_returns_value(self) -> None:
        """predict_hour возвращает значение для пикового часа."""
        predictor = LoadPredictor()
        result = predictor.predict_hour(10)
        assert result >= 0.0

    def test_predict_hour_invalid_raises(self) -> None:
        """predict_hour бросает ValueError при неверном часе."""
        predictor = LoadPredictor()
        with pytest.raises(ValueError):
            predictor.predict_hour(25)
        with pytest.raises(ValueError):
            predictor.predict_hour(-1)

    def test_predict_day_returns_24_hours(self) -> None:
        """predict_day возвращает прогноз на 24 часа."""
        predictor = LoadPredictor()
        result = predictor.predict_day()
        assert len(result) == 24
        assert all("hour" in h and "load" in h and "label" in h for h in result)

    def test_predict_day_hours_sequential(self) -> None:
        """Часы идут последовательно от 0 до 23."""
        predictor = LoadPredictor()
        hours = [h["hour"] for h in predictor.predict_day()]
        assert hours == list(range(24))

    def test_best_hours_count(self) -> None:
        """best_hours возвращает запрошенное количество часов."""
        predictor = LoadPredictor()
        assert len(predictor.best_hours(3)) == 3
        assert len(predictor.best_hours(1)) == 1

    def test_best_hours_within_working_time(self) -> None:
        """Рекомендованные часы в пределах 7:00-22:00."""
        predictor = LoadPredictor()
        for h in predictor.best_hours():
            assert 7 <= h["hour"] <= 22

    def test_best_hours_sorted_by_load(self) -> None:
        """Рекомендованные часы отсортированы по возрастанию загруженности."""
        predictor = LoadPredictor()
        loads = [h["load"] for h in predictor.best_hours(5)]
        assert loads == sorted(loads)

    def test_load_label_values(self) -> None:
        """_load_label возвращает одно из четырёх значений."""
        predictor = LoadPredictor()
        valid = {"Свободно", "Умеренно", "Оживлённо", "Пик"}
        for hour in range(24):
            load = predictor.predict_hour(hour)
            assert predictor._load_label(load) in valid

    def test_model_info_structure(self) -> None:
        """model_info содержит ключевые поля."""
        predictor = LoadPredictor()
        info = predictor.model_info
        assert "algorithm" in info
        assert "r2_score" in info
        assert "training_samples" in info
        assert info["r2_score"] > 0.6  # Полином 6-й степени на синтетических данных

    def test_all_loads_non_negative(self) -> None:
        """Все прогнозы неотрицательны."""
        predictor = LoadPredictor()
        for hour in range(24):
            assert predictor.predict_hour(hour) >= 0.0
