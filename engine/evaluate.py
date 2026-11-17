"""Aurum evaluation: run the engine on every sample file and score it.

This is the demo command. It answers one question: does the engine catch
every planted error without raising false alarms on the clean files?

Run it from the project folder like this:

    python -m engine.evaluate
"""

import csv
import os

from engine.checks import analyze
from engine.loader import load_statement
from engine.ratios import compute_ratios, format_ratios

SAMPLE = os.path.join("data", "sample")
CLEAN_INCOME = os.path.join(SAMPLE, "clean", "income_statement.csv")
CLEAN_BALANCE = os.path.join(SAMPLE, "clean", "balance_sheet.csv")

# The finding the engine must produce for each planted error to count as caught.
EXPECTED = {
    "E01": "balance_mismatch",
    "E02": "missing_line_item",
    "E03": "missing_value",
    "E04": "unusual_change",
    "E05": "subtotal_mismatch",
    "E06": "negative_expense",
    "E07": "duplicate_line_item",
    "E08": "retained_earnings_mismatch",
    "E09": "non_numeric_value",
    "E10": "duplicate_period",
}


def run_file(path):
    """Analyze one file. Balance sheets are paired with the clean income statement."""
    companion = CLEAN_INCOME if "balance_sheet" in os.path.basename(path) else None
    _, findings = analyze(path, companion)
    return findings


def planted_errors():
    """Read the answer key: a list of (id, file name) pairs."""
    with open(os.path.join(SAMPLE, "planted_errors.csv"), newline="", encoding="utf-8") as file:
        return [(row["id"], row["file"]) for row in csv.DictReader(file)]


def evaluate():
    """Run every sample file. Returns (clean results, error results)."""
    clean = []
    for path in (CLEAN_INCOME, CLEAN_BALANCE):
        clean.append((os.path.basename(path), run_file(path)))

    errors = []
    for error_id, name in planted_errors():
        findings = run_file(os.path.join(SAMPLE, "errors", name))
        caught = any(f.check == EXPECTED[error_id] for f in findings)
        errors.append((error_id, name, caught, findings))
    return clean, errors


def main():
    clean, errors = evaluate()

    print("AURUM ENGINE EVALUATION")
    print("=" * 60)
    print()
    print("Clean statements (should have no findings):")
    false_alarms = 0
    for name, findings in clean:
        false_alarms += len(findings)
        status = "OK" if not findings else f"{len(findings)} FALSE ALARM(S)"
        print(f"  {name:<40} {status}")
        for finding in findings:
            print(f"      {finding}")

    print()
    print("Planted errors (each should be caught):")
    caught_count = 0
    for error_id, name, caught, findings in errors:
        caught_count += caught
        print(f"  {error_id}  {'CAUGHT' if caught else 'MISSED'}  {name}")
        for finding in findings:
            print(f"        {finding.message}")

    print()
    print("=" * 60)
    print(f"Planted errors caught: {caught_count} of {len(errors)}")
    print(f"False alarms on clean statements: {false_alarms}")

    print()
    print("Key ratios for the clean statements:")
    income, _ = load_statement(CLEAN_INCOME)
    balance, _ = load_statement(CLEAN_BALANCE)
    print(format_ratios(compute_ratios(income, balance)))


if __name__ == "__main__":
    main()
