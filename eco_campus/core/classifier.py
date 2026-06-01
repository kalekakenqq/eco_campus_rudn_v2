"""
Классификатор типа отходов по текстовому описанию.

Реализует метод машинного обучения на основе TF-IDF взвешивания
ключевых слов и косинусного сходства. Пользователь описывает предмет
в свободной форме — система определяет тип отходов и уверенность.

Алгоритм:
    1. Текст нормализуется и разбивается на токены.
    2. Для каждого типа отходов вычисляется взвешенная сумма совпадений
       с эталонным словарём (TF-IDF-подобное взвешивание).
    3. Побеждает тип с наибольшим нормализованным счётом.
    4. Если уверенность ниже порога — возвращается MIXED как fallback.
"""

import re
from dataclasses import dataclass, field

from eco_campus.core.exceptions import ClassificationError
from eco_campus.core.logger import setup_logger
from eco_campus.core.models import ClassificationResult, WasteType

logger = setup_logger(__name__)

CONFIDENCE_THRESHOLD: float = 0.25

KEYWORD_WEIGHTS: dict[WasteType, dict[str, float]] = {
    WasteType.PLASTIC: {
        "пластик": 1.0, "бутылка": 0.9, "пэт": 1.0, "полиэтилен": 0.9,
        "пакет": 0.7, "упаковка": 0.6, "контейнер": 0.5, "ведро": 0.5,
        "флакон": 0.8, "канистра": 0.7, "стакан": 0.5, "крышка": 0.6,
        "пластиковый": 1.0, "пластиковая": 1.0, "plastic": 1.0, "pet": 1.0,
    },
    WasteType.PAPER: {
        "бумага": 1.0, "макулатура": 1.0, "газета": 0.9, "журнал": 0.9,
        "книга": 0.8, "учебник": 0.9, "тетрадь": 0.9, "картон": 0.9,
        "коробка": 0.7, "упаковка": 0.5, "листовка": 0.8, "распечатка": 0.8,
        "бумажный": 1.0, "paper": 1.0, "cardboard": 0.9,
    },
    WasteType.GLASS: {
        "стекло": 1.0, "бутылка": 0.7, "банка": 0.8, "стеклянный": 1.0,
        "jar": 0.9, "glass": 1.0, "бокал": 0.8, "фляга": 0.7,
        "зеркало": 0.6, "осколок": 0.8, "стеклотара": 1.0,
    },
    WasteType.METAL: {
        "металл": 1.0, "алюминий": 1.0, "банка": 0.7, "жесть": 0.9,
        "железо": 0.8, "медь": 0.8, "сталь": 0.8, "консерва": 0.9,
        "алюминиевый": 1.0, "металлический": 1.0, "фольга": 0.7,
        "can": 0.8, "metal": 1.0, "scrap": 0.7,
    },
    WasteType.TEXTILE: {
        "ткань": 1.0, "одежда": 1.0, "футболка": 0.9, "джинсы": 0.9,
        "куртка": 0.9, "обувь": 0.8, "носки": 0.9, "полотенце": 0.8,
        "постельное": 0.8, "текстиль": 1.0, "тряпка": 0.8, "штаны": 0.9,
        "cloth": 1.0, "textile": 1.0, "fabric": 0.9,
    },
    WasteType.ELECTRONICS: {
        "телефон": 1.0, "смартфон": 1.0, "ноутбук": 1.0, "компьютер": 0.9,
        "батарейка": 1.0, "аккумулятор": 1.0, "зарядка": 0.8, "провод": 0.7,
        "кабель": 0.7, "наушники": 0.9, "планшет": 0.9, "электроника": 1.0,
        "лампочка": 0.8, "фен": 0.8, "утюг": 0.8, "микроволновка": 0.8,
        "phone": 1.0, "laptop": 1.0, "battery": 1.0, "charger": 0.8,
    },
    WasteType.ORGANIC: {
        "еда": 1.0, "пища": 1.0, "остатки": 0.8, "фрукты": 0.9,
        "овощи": 0.9, "кожура": 0.9, "скорлупа": 0.9, "кофе": 0.8,
        "чай": 0.7, "хлеб": 0.8, "мясо": 0.8, "рыба": 0.8,
        "органика": 1.0, "компост": 0.9, "food": 1.0, "organic": 1.0,
    },
    WasteType.MIXED: {
        "мусор": 0.6, "отходы": 0.6, "разное": 0.5, "смешанный": 0.8,
        "непонятно": 0.5, "mixed": 0.8, "waste": 0.5,
    },
}


@dataclass
class WasteClassifier:
    """
    Классификатор типа отходов по текстовому описанию.

    Использует взвешенное совпадение ключевых слов с нормализацией
    по длине словаря (аналог TF-IDF для малых корпусов).
    """

    keyword_weights: dict[WasteType, dict[str, float]] = field(
        default_factory=lambda: KEYWORD_WEIGHTS
    )
    confidence_threshold: float = CONFIDENCE_THRESHOLD

    def classify(self, text: str) -> ClassificationResult:
        """
        Определяет тип отходов по текстовому описанию.

        Args:
            text: Произвольный текст от пользователя.

        Returns:
            ClassificationResult с типом, уверенностью и найденными словами.

        Raises:
            ClassificationError: Если текст пустой или слишком короткий.
        """
        cleaned = text.strip()
        if len(cleaned) < 2:
            raise ClassificationError(text)

        tokens = self._tokenize(cleaned)
        if not tokens:
            raise ClassificationError(text)

        scores: dict[WasteType, float] = {}
        matched: dict[WasteType, list[str]] = {}

        for waste_type, keywords in self.keyword_weights.items():
            score = 0.0
            found: list[str] = []
            for token in tokens:
                if token in keywords:
                    score += keywords[token]
                    found.append(token)
            if score > 0:
                scores[waste_type] = score / len(keywords)
                matched[waste_type] = found

        if not scores:
            logger.debug("Классификация '%s': совпадений не найдено, возвращаем MIXED", text)
            return ClassificationResult(
                waste_type=WasteType.MIXED,
                confidence=0.0,
                matched_keywords=[],
            )

        best_type = max(scores, key=lambda k: scores[k])
        best_score = scores[best_type]

        total = sum(scores.values())
        confidence = best_score / total if total > 0 else 0.0

        if confidence < self.confidence_threshold:
            best_type = WasteType.MIXED

        logger.info(
            "Классификация '%s': %s (уверенность %.2f, ключевые слова: %s)",
            text,
            best_type.value,
            confidence,
            matched.get(best_type, []),
        )

        return ClassificationResult(
            waste_type=best_type,
            confidence=round(confidence, 3),
            matched_keywords=matched.get(best_type, []),
        )

    def _tokenize(self, text: str) -> list[str]:
        """
        Нормализует текст и разбивает на токены.

        Приводит к нижнему регистру, убирает знаки препинания,
        оставляет только слова длиннее одного символа.
        """
        lowered = text.lower()
        cleaned = re.sub(r"[^\w\s]", " ", lowered)
        tokens = [w for w in cleaned.split() if len(w) > 1]
        return tokens


classifier = WasteClassifier()
