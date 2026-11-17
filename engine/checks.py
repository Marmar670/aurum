"""Aurum accounting checks: does the statement add up?

The loader (engine/loader.py) checks a file's structure. This module checks
the accounting:

- required line items are present
- every subtotal equals the lines it is built from
- total assets equal total liabilities plus equity
- retained earnings grows by each month's net income
- expense lines are never negative
- no line jumps or drops unusually from one month to the next

Every check returns Finding objects. A Finding is the same shape as the
loader's Problem, so the two lists can be combined into one report.

Design rule: report the root cause, not the ripple. When a number is already
known to be wrong in a month, any total built from it is not re-checked for
that month. One mistake gives one finding, not a chain of them.

Run it from the project folder like this:

    python -m engine.checks data/sample/errors/E05_income_statement_wrong_subtotal.csv
    python -m engine.checks <balance sheet csv> <income statement csv>
"""

import math
import sys
from datetime import datetime

from engine.loader import PERIOD_FORMAT, Problem, load_statement

# Findings use the same record as the loader's problems.
Finding = Problem

# Differences smaller than this are treated as rounding, not errors.
TOLERANCE = 1.0

# How each subtotal is built. Each entry is (subtotal, [(line, sign), ...]).
# Sign +1 means the line is added and -1 means it is subtracted.
# Entries are listed top to bottom, in the order they appear on the statement.
INCOME_STATEMENT_RULES = [
    ("Gross Profit", [("Sales Revenue", 1), ("Cost of Goods Sold", -1)]),
    ("Total Operating Expenses", [
        ("Wages and Salaries", 1), ("Rent", 1), ("Utilities", 1),
        ("Marketing", 1), ("Insurance", 1), ("Depreciation", 1),
    ]),
    ("Operating Income", [("Gross Profit", 1), ("Total Operating Expenses", -1)]),
    ("Income Before Tax", [("Operating Income", 1), ("Interest Expense", -1)]),
    ("Net Income", [("Income Before Tax", 1), ("Income Tax Expense", -1)]),
]

BALANCE_SHEET_RULES = [
    ("Total Current Assets", [
        ("Cash", 1), ("Accounts Receivable", 1), ("Inventory", 1), ("Prepaid Expenses", 1),
    ]),
    ("Total Assets", [
        ("Total Current Assets", 1), ("Equipment", 1), ("Accumulated Depreciation", 1),
    ]),
    ("Total Current Liabilities", [("Accounts Payable", 1), ("Income Tax Payable", 1)]),
    ("Total Liabilities", [("Total Current Liabilities", 1), ("Bank Loan", 1)]),
    ("Total Equity", [("Owner's Capital", 1), ("Retained Earnings", 1)]),
    ("Total Liabilities and Equity", [("Total Liabilities", 1), ("Total Equity", 1)]),
]

# Lines that are costs. A cost should never be a negative number.
EXPENSE_LINES = [
    "Cost of Goods Sold", "Wages and Salaries", "Rent", "Utilities", "Marketing",
    "Insurance", "Depreciation", "Interest Expense", "Income Tax Expense",
]

# A month-to-month change counts as unusual when the new value is at least
# SWING_FACTOR times larger or smaller than the old one, and the change is at
# least SWING_MINIMUM dollars (so tiny lines do not trigger false alarms).
SWING_FACTOR = 3.0
SWING_MINIMUM = 500.0


# ---------- small helpers ----------

def statement_type(table):
    """Return 'balance_sheet' or 'income_statement' based on the line items."""
    if "Total Assets" in table.index or "Total Liabilities and Equity" in table.index:
        return "balance_sheet"
    return "income_statement"


def rules_for(table):
    if statement_type(table) == "balance_sheet":
        return BALANCE_SHEET_RULES
    return INCOME_STATEMENT_RULES


def value(table, line, period):
    """The number in one cell, or None if the line is absent or the cell is empty."""
    if line not in table.index or period not in table.columns:
        return None
    number = table.at[line, period]
    if number is None or (isinstance(number, float) and math.isnan(number)):
        return None
    return float(number)


def previous_period(period):
    """The month before a label like 'Mar 2026', as a label ('Feb 2026')."""
    date = datetime.strptime(period, PERIOD_FORMAT)
    if date.month == 1:
        date = date.replace(year=date.year - 1, month=12)
    else:
        date = date.replace(month=date.month - 1)
    return date.strftime(PERIOD_FORMAT)


def money(amount):
    return f"{amount:,.0f}"


def known_bad(problems):
    """Cells already reported as wrong, as a set of (line, period) pairs."""
    return {(p.line_item, p.period) for p in problems if p.line_item and p.period}


# ---------- the checks ----------

def check_required_lines(table):
    """Every line the rules depend on must be present."""
    findings = []
    needed = []
    for subtotal, parts in rules_for(table):
        for line in [subtotal] + [line for line, _ in parts]:
            if line not in needed:
                needed.append(line)
    for line in needed:
        if line not in table.index:
            findings.append(Finding(
                "missing_line_item", line, "",
                f"The required line item {line} is missing.",
            ))
    return findings


def check_subtotals(table, already_flagged):
    """Every subtotal must equal the sum of its lines, month by month."""
    findings = []
    flagged = set(already_flagged)
    for period in table.columns:
        for subtotal, parts in rules_for(table):
            reported = value(table, subtotal, period)
            if reported is None:
                continue
            # Skip if any part is already known to be wrong this month (root cause rule).
            if any((line, period) in flagged for line, _ in parts):
                flagged.add((subtotal, period))
                continue
            # A part that is blank or missing cannot be checked; it was already reported.
            if any(value(table, line, period) is None for line, _ in parts):
                flagged.add((subtotal, period))
                continue
            expected = sum(sign * value(table, line, period) for line, sign in parts)
            if abs(reported - expected) > TOLERANCE:
                findings.append(Finding(
                    "subtotal_mismatch", subtotal, period,
                    f"{subtotal} for {period} is {money(reported)}, "
                    f"but its lines add up to {money(expected)} "
                    f"(difference of {money(reported - expected)}).",
                ))
                flagged.add((subtotal, period))
    return findings


def check_balance(table, already_flagged):
    """Total Assets must equal Total Liabilities and Equity."""
    findings = []
    if statement_type(table) != "balance_sheet":
        return findings
    for period in table.columns:
        if ("Total Assets", period) in already_flagged or \
           ("Total Liabilities and Equity", period) in already_flagged:
            continue
        assets = value(table, "Total Assets", period)
        claims = value(table, "Total Liabilities and Equity", period)
        if assets is None or claims is None:
            continue
        if abs(assets - claims) > TOLERANCE:
            findings.append(Finding(
                "balance_mismatch", "Total Assets", period,
                f"The balance sheet does not balance in {period}: "
                f"Total Assets is {money(assets)} but Total Liabilities and Equity "
                f"is {money(claims)} (difference of {money(assets - claims)}).",
            ))
    return findings


def check_retained_earnings(balance_sheet, income_statement):
    """Each month, Retained Earnings should grow by exactly that month's Net Income.

    The first month is skipped because the opening balance is not in the file.
    This assumes no owner withdrawals or dividends, which is true for the sample data.
    """
    findings = []
    for period in balance_sheet.columns:
        before = previous_period(period)
        if before not in balance_sheet.columns:
            continue
        current = value(balance_sheet, "Retained Earnings", period)
        prior = value(balance_sheet, "Retained Earnings", before)
        net_income = value(income_statement, "Net Income", period)
        if current is None or prior is None or net_income is None:
            continue
        change = current - prior
        if abs(change - net_income) > TOLERANCE:
            findings.append(Finding(
                "retained_earnings_mismatch", "Retained Earnings", period,
                f"Retained Earnings changed by {money(change)} in {period}, "
                f"but Net Income for {period} was {money(net_income)} "
                f"(difference of {money(change - net_income)}).",
            ))
    return findings


def check_negative_expenses(table):
    """A cost line should never be negative."""
    findings = []
    for line in EXPENSE_LINES:
        for period in table.columns:
            amount = value(table, line, period)
            if amount is not None and amount < 0:
                findings.append(Finding(
                    "negative_expense", line, period,
                    f"{line} is negative ({money(amount)}) in {period}. "
                    f"Costs are normally positive, so this may be a sign error.",
                ))
    return findings


def check_unusual_changes(table):
    """Flag a line that jumps or drops sharply from one month to the next.

    Only ordinary lines are checked, not subtotals, so one unusual line gives
    one finding. A line that returns to normal right after a flagged month is
    not flagged again.
    """
    findings = []
    subtotals = {subtotal for subtotal, _ in rules_for(table)}
    flagged = set()
    for line in table.index:
        if line in subtotals:
            continue
        for period in table.columns:
            before = previous_period(period)
            if before not in table.columns or (line, before) in flagged:
                continue
            old = value(table, line, before)
            new = value(table, line, period)
            if old is None or new is None or old <= 0 or new <= 0:
                continue  # blanks and negatives are handled by other checks
            factor = new / old
            if abs(new - old) >= SWING_MINIMUM and (factor >= SWING_FACTOR or factor <= 1 / SWING_FACTOR):
                direction = "rose" if new > old else "fell"
                findings.append(Finding(
                    "unusual_change", line, period,
                    f"{line} {direction} from {money(old)} in {before} to "
                    f"{money(new)} in {period} (about {factor:.1f} times). "
                    f"Check for a typing error such as an extra zero.",
                ))
                flagged.add((line, period))
    return findings


# ---------- run everything ----------

def analyze(path, income_statement_path=None):
    """Load a statement and run every check on it.

    For a balance sheet, pass the matching income statement as well so that
    retained earnings can be checked against net income.

    Returns (table, findings), where findings includes the loader's problems.
    """
    table, findings = load_statement(path)
    if table.empty:
        return table, findings

    findings += check_required_lines(table)
    findings += check_subtotals(table, known_bad(findings))
    findings += check_balance(table, known_bad(findings))
    findings += check_negative_expenses(table)
    findings += check_unusual_changes(table)

    if statement_type(table) == "balance_sheet" and income_statement_path:
        income_table, _ = load_statement(income_statement_path)
        findings += check_retained_earnings(table, income_table)

    return table, findings


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python -m engine.checks <statement csv> [income statement csv]")
        sys.exit(1)
    income_path = sys.argv[2] if len(sys.argv) == 3 else None
    _, findings = analyze(sys.argv[1], income_path)
    if findings:
        print(f"{len(findings)} finding(s):")
        for finding in findings:
            print(f"  {finding}")
    else:
        print("No problems found. The statement adds up.")


if __name__ == "__main__":
    main()
