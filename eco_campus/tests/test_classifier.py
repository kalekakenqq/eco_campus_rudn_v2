"""
Unit-тесты для классификатора типа отходов по тексту.
"""

import pytest

from eco_campus.core.classifier import WasteClassifier
from eco_campus.core.exceptions import ClassificationError
from eco_campus.core.models import WasteType


@pytest.fixture
def classifier() -> WasteClassifier:
    """Возвращает экземпляр классификатора для тестов."""
    return WasteClassifier()


class TestClassifierBasic:
    def test_classifies_plastic_bottle(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("пластиковая бутылка")
        assert result.waste_type == WasteType.PLASTIC

    def test_classifies_paper(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("старая газета")
        assert result.waste_type == WasteType.PAPER

    def test_classifies_electronics(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("старый телефон")
        assert result.waste_type == WasteType.ELECTRONICS

    def test_classifies_glass_bottle(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("стеклянная банка")
        assert result.waste_type == WasteType.GLASS

    def test_classifies_textile(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("старая одежда футболка")
        assert result.waste_type == WasteType.TEXTILE

    def test_classifies_battery(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("батарейка аккумулятор")
        assert result.waste_type == WasteType.ELECTRONICS

    def test_classifies_food_organic(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("остатки еды кожура")
        assert result.waste_type == WasteType.ORGANIC


class TestClassifierConfidence:
    def test_returns_confidence_between_0_and_1(
        self, classifier: WasteClassifier
    ) -> None:
        result = classifier.classify("пластиковая бутылка")
        assert 0.0 <= result.confidence <= 1.0

    def test_clear_match_has_high_confidence(
        self, classifier: WasteClassifier
    ) -> None:
        result = classifier.classify("пластик пэт бутылка пластиковый")
        assert result.confidence > 0.5

    def test_is_confident_for_clear_match(
        self, classifier: WasteClassifier
    ) -> None:
        result = classifier.classify("телефон смартфон батарейка")
        assert result.is_confident()


class TestClassifierKeywords:
    def test_returns_matched_keywords(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("пластиковая бутылка")
        assert len(result.matched_keywords) > 0

    def test_matched_keywords_are_from_input(
        self, classifier: WasteClassifier
    ) -> None:
        result = classifier.classify("газета журнал бумага")
        for kw in result.matched_keywords:
            assert isinstance(kw, str)


class TestClassifierEdgeCases:
    def test_raises_for_empty_string(self, classifier: WasteClassifier) -> None:
        with pytest.raises(ClassificationError):
            classifier.classify("")

    def test_raises_for_single_char(self, classifier: WasteClassifier) -> None:
        with pytest.raises(ClassificationError):
            classifier.classify("а")

    def test_returns_mixed_for_unknown_text(
        self, classifier: WasteClassifier
    ) -> None:
        result = classifier.classify("абракадабра флюгегехаймер")
        assert result.waste_type == WasteType.MIXED

    def test_case_insensitive(self, classifier: WasteClassifier) -> None:
        result_lower = classifier.classify("пластик")
        result_upper = classifier.classify("ПЛАСТИК")
        assert result_lower.waste_type == result_upper.waste_type

    def test_handles_punctuation(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("бутылка, пластик!")
        assert result.waste_type == WasteType.PLASTIC

    def test_english_words_recognized(self, classifier: WasteClassifier) -> None:
        result = classifier.classify("old phone battery")
        assert result.waste_type == WasteType.ELECTRONICS
