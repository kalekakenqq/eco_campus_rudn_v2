"""
Модуль прогнозирования загруженности экопунктов.

Использует линейную регрессию (scikit-learn) для предсказания
ожидаемого числа посетителей по часу дня. Модель обучается на
синтетических данных, отражающих типичный суточный ритм кампуса:
пик утром (9-11), спад днём, второй пик вечером (17-19).
"""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import PolynomialFeatures

from eco_campus.core.logger import setup_logger

logger = setup_logger(__name__)


# ---------------------------------------------------------------------------
# Синтетические обучающие данные
# Основаны на типичном суточном ритме студенческого кампуса:
#   - утренний пик: 8-11 (пары начинаются)
#   - спад: 12-13 (обед, все уходят)
#   - дневная активность: 14-16
#   - вечерний пик: 17-19 (конец пар)
#   - спад: 20-23
# ---------------------------------------------------------------------------
_TRAINING_DATA: list[tuple[int, float]] = [
    (6, 1.0), (7, 3.0), (8, 8.0), (9, 14.0), (10, 16.0),
    (11, 14.0), (12, 9.0), (13, 7.0), (14, 11.0), (15, 13.0),
    (16, 12.0), (17, 15.0), (18, 13.0), (19, 9.0), (20, 5.0),
    (21, 3.0), (22, 1.5), (23, 0.5),
]


class LoadPredictor:
    """
    Предсказывает загруженность экопунктов по часу дня.

    Использует полиномиальную регрессию степени 6 для аппроксимации
    двугорбой суточной кривой посещаемости.
    """

    def __init__(self) -> None:
        self._model: Pipeline = self._train()
        logger.info("LoadPredictor инициализирован, модель обучена")

    def _train(self) -> Pipeline:
        """Обучает модель на синтетических данных суточного ритма."""
        hours = np.array([h for h, _ in _TRAINING_DATA]).reshape(-1, 1)
        loads = np.array([v for _, v in _TRAINING_DATA])

        pipeline = Pipeline([
            ("poly", PolynomialFeatures(degree=6, include_bias=False)),
            ("regressor", LinearRegression()),
        ])
        pipeline.fit(hours, loads)

        r2 = pipeline.score(hours, loads)
        logger.debug("Модель обучена, R²=%.4f", r2)
        return pipeline

    def predict_hour(self, hour: int) -> float:
        """
        Предсказывает загруженность для заданного часа.

        Args:
            hour: Час дня от 0 до 23.

        Returns:
            Ожидаемое число посетителей (не менее 0).
        """
        if not 0 <= hour <= 23:
            raise ValueError(f"Час должен быть от 0 до 23, получено: {hour}")
        x = np.array([[hour]])
        prediction = float(self._model.predict(x)[0])
        return max(0.0, round(prediction, 1))

    def predict_day(self) -> list[dict]:
        """
        Возвращает прогноз загруженности на все часы суток.

        Returns:
            Список словарей {hour, load, label} для каждого часа 0-23.
        """
        result = []
        for hour in range(24):
            load = self.predict_hour(hour)
            result.append({
                "hour": hour,
                "load": load,
                "label": self._load_label(load),
            })
        return result

    def best_hours(self, top_n: int = 3) -> list[dict]:
        """
        Возвращает топ-N часов с наименьшей загруженностью.

        Args:
            top_n: Количество рекомендуемых часов.

        Returns:
            Отсортированный список лучших часов для посещения.
        """
        day = self.predict_day()
        # Фильтруем только рабочие часы (7:00-22:00)
        working = [h for h in day if 7 <= h["hour"] <= 22]
        return sorted(working, key=lambda x: x["load"])[:top_n]

    @staticmethod
    def _load_label(load: float) -> str:
        """Переводит числовое значение загруженности в текстовую метку."""
        if load < 4:
            return "Свободно"
        if load < 9:
            return "Умеренно"
        if load < 13:
            return "Оживлённо"
        return "Пик"

    @property
    def model_info(self) -> dict:
        """Возвращает метаданные модели для API."""
        regressor: LinearRegression = self._model.named_steps["regressor"]
        hours = np.array([h for h, _ in _TRAINING_DATA]).reshape(-1, 1)
        loads = np.array([v for _, v in _TRAINING_DATA])
        return {
            "algorithm": "Polynomial Linear Regression",
            "degree": 6,
            "r2_score": round(float(self._model.score(hours, loads)), 4),
            "training_samples": len(_TRAINING_DATA),
            "features": ["hour_of_day"],
            "target": "expected_visitors",
        }


# Синглтон — модель обучается один раз при старте приложения
load_predictor = LoadPredictor()
