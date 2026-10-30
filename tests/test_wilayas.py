"""Wilaya reference data."""
import pytest

from ai.wilayas import WILAYA_CODE_TO_NAME, get_wilaya_name


def test_69_wilayas():
    assert len(WILAYA_CODE_TO_NAME) == 69


def test_alger_is_wilaya_16():
    assert get_wilaya_name(16) == "Alger"


@pytest.mark.parametrize("code", [1, 16, 31, 58, 69])
def test_known_wilayas(code):
    assert get_wilaya_name(code) is not None


@pytest.mark.parametrize("code", [0, 70, 99, -1, None, "abc"])
def test_unknown_wilayas(code):
    assert get_wilaya_name(code) is None
