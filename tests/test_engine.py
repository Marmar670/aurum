"""Automated tests for the Aurum engine. Run them with:  pytest"""

import pytest

from engine.evaluate import CLEAN_BALANCE, CLEAN_INCOME, EXPECTED, evaluate, run_file
from engine.loader import load_statement
from engine.ratios import compute_ratios

CLEAN_RESULTS, ERROR_RESULTS = evaluate()


@pytest.mark.parametrize("path", [CLEAN_INCOME, CLEAN_BALANCE])
def test_clean_statements_have_no_findings(path):
    assert run_file(path) == []


@pytest.mark.parametrize("error_id, name, caught, findings", ERROR_RESULTS)
def test_planted_error_is_caught(error_id, name, caught, findings):
    checks = [f.check for f in findings]
    assert EXPECTED[error_id] in checks, f"{error_id} not caught; found {checks}"


def test_ratios_match_hand_calculation():
    income, _ = load_statement(CLEAN_INCOME)
    balance, _ = load_statement(CLEAN_BALANCE)
    ratios = compute_ratios(income, balance)
    # January, worked out by hand from the clean files:
    assert ratios.at["Gross Margin", "Jan 2026"] == pytest.approx(26040 / 42000)
    assert ratios.at["Net Margin", "Jan 2026"] == pytest.approx(5113 / 42000)
    assert ratios.at["Current Ratio", "Jan 2026"] == pytest.approx(28790 / 8677)
    assert ratios.at["Debt to Equity", "Jan 2026"] == pytest.approx(67677 / 37113)
