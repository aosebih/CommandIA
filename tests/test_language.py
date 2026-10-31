"""Language detection and the mirror rule."""
import pytest

from ai_brain import AIBrain


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Bonjour, quel est le prix de ce produit ?", "french"),
        ("Bonjour, quel est le prix de ce produit ? 2500 DA", "french"),
        ("Chcine le prix", "french"),
        ("Merci beaucoup", "french"),
        ("3500 DA", "french"),
        ("Rani bghit nchri had produit", "franco_arabic"),
        ("Ismi Ahmed Benali", "franco_arabic"),
        ("Numero ta3i 0550123456", "franco_arabic"),
        ("Ana men Alger", "franco_arabic"),
        ("Chehal thmen had l3iba?", "franco_arabic"),
        ("Hello, is this available in stock?", "english"),
        ("I want to buy it now", "english"),
        ("Thank you very much", "english"),
    ],
)
def test_detect_language(brain, text, expected):
    assert brain._detect_language(text) == expected


def test_detect_language_arabic_script(brain):
    # Arabic script must be detected as darija, not French.
    assert brain._detect_language("\u0634\u062d\u0627\u0644 \u062b\u0645\u0646 \u0647\u0627\u062f\u0627\u0644\u0645\u0646\u062a\u062c\u061f") == "darija"


def test_detect_language_empty_defaults_to_franco_arabic(brain):
    # The target market is Algerian: an unclassifiable message falls back to
    # Franco-Arabic rather than French.
    assert brain._detect_language("") == "franco_arabic"


def test_mirror_rule_locks_language_on_first_turn(make_service):
    """The reply language must mirror the customer's first message."""
    from tests.conftest import extraction_payload

    service = make_service([extraction_payload() for _ in range(3)])
    conversation_id = None
    for message in ["Bonjour quel est le prix", "Rani bghit nchri", "Hello do you ship"]:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]
        assert result["language"] == "french"


def test_mirror_rule_switches_when_first_turn_is_darija(make_service):
    from tests.conftest import extraction_payload

    service = make_service([extraction_payload() for _ in range(3)])
    conversation_id = None
    for message in ["Rani bghit nchri had produit", "Bonjour"]:
        result = service.process_message(user_message=message, conversation_id=conversation_id)
        conversation_id = result["conversation_id"]
        assert result["language"] == "franco_arabic"
