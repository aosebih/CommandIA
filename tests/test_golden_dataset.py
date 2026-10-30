"""
Golden dataset runner.

Unlike the rest of the suite, this test talks to the real Gemini API, so it
is opt-in: set COMMANDIA_GOLDEN=1 to run it. It is the regression net for
prompt changes and model upgrades, and it is the test that would have caught
the "no language key" and "model 404" bugs.

    COMMANDIA_GOLDEN=1 pytest tests/test_golden_dataset.py -v
"""
import json
import os
from pathlib import Path

import pytest

DATASET = Path(__file__).resolve().parent / "golden_dataset.json"

pytestmark = pytest.mark.skipif(
    os.environ.get("COMMANDIA_GOLDEN") != "1",
    reason="Golden dataset needs the real API: set COMMANDIA_GOLDEN=1",
)


def load_cases():
    with DATASET.open("r", encoding="utf-8") as handle:
        return json.load(handle)["cases"]


@pytest.mark.parametrize("case", load_cases(), ids=lambda case: case["id"])
def test_golden_case(case):
    from ai.ai_service import AIService

    service = AIService()
    conversation_id = None

    for index, turn in enumerate(case["turns"]):
        result = service.process_message(
            user_message=turn["message"],
            conversation_id=conversation_id,
        )
        conversation_id = result["conversation_id"]
        expected = turn["expected"]
        label = f"turn {index}: {turn['message']!r}"

        assert result.get("error") is None, f"{label} -> {result.get('error')}"
        assert "language" in result, f"{label} -> missing language key"

        if "state" in expected:
            assert result["state"] == expected["state"], label
        if "language" in expected:
            assert result["language"] == expected["language"], label
        if "missing_fields" in expected:
            assert result["missing_fields"] == expected["missing_fields"], label
        if "order_status" in expected:
            assert result["extracted_data"]["order_status"] == expected["order_status"], label
        for field, value in expected.get("collected_fields", {}).items():
            assert result["collected_fields"].get(field) == value, f"{label} -> {field}"
