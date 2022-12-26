import pytest
from deep_translator import GoogleTranslator

testdata = [
    ('abalanzó', 'es', 'en', 'pounced'),
    ('heiligen', 'de', 'en', 'sanctify'),
    ('sanctify', 'en', 'de', 'heiligen'),
    ('heiligen', 'de', 'es', 'santificar'),
]


@pytest.mark.parametrize('word,source,target,translation', testdata)
def test_googletranslate(word: str, source: str, target: str, translation: str) -> None:
    assert GoogleTranslator(source=source, target=target).translate(word) == translation
