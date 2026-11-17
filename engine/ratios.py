"""Aurum ratios: the key financial ratios, month by month.

These are the numbers the AI agent will explain later. Python computes them
here so the AI never has to do arithmetic itself.

Run it from the project folder like this:

    python -m engine.ratios data/sample/clean/income_statement.csv data/sample/clean/balance_sheet.csv
"""

import sys

import pandas as pd

from engine.loader import load_statement

# Each ratio is (name, top line, top statement, bottom line, bottom statement, what it means).
RATIOS = [
    ("Gross Margin", "Gross Profit", "income", "Sales Revenue", "income",
     "Share of each sales dollar left after the cost of the goods sold."),
    ("Net Margin", "Net Income", "income", "Sales Revenue", "income",
     "Share of each sales dollar kept as profit after every expense."),
    ("Current Ratio", "Total Current Assets", "balance", "Total Current Liabilities", "balance",
     "Short-term assets for each dollar of short-term debt. Above 1 means bills can be covered."),
    ("Debt to Equity", "Total Liabilities", "balance", "Total Equity", "balance",
     "Dollars borrowed for each dollar the owner has in the business."),
]

PERCENT_RATIOS = {"Gross Margin", "Net Margin"}


def compute_ratios(income_statement, balance_sheet):
    """Return a table with one row per ratio and one column per month.

    A ratio is left empty for a month when either number is missing or the
    bottom number is zero.
    """
    tables = {"income": income_statement, "balance": balance_sheet}
    periods = [p for p in income_statement.columns if p in balance_sheet.columns]
    rows = {}
    for name, top, top_from, bottom, bottom_from, _ in RATIOS:
        row = {}
        for period in periods:
            try:
                numerator = tables[top_from].at[top, period]
                denominator = tables[bottom_from].at[bottom, period]
            except KeyError:
                row[period] = None
                continue
            if pd.isna(numerator) or pd.isna(denominator) or denominator == 0:
                row[period] = None
            else:
                row[period] = numerator / denominator
        rows[name] = row
    result = pd.DataFrame.from_dict(rows, orient="index")
    result.index.name = "Ratio"
    return result


def format_ratios(ratios):
    """The ratio table as text, with margins shown as percentages."""
    shown = ratios.copy().astype(object)
    for name in shown.index:
        for period in shown.columns:
            number = ratios.at[name, period]
            if pd.isna(number):
                shown.at[name, period] = "n/a"
            elif name in PERCENT_RATIOS:
                shown.at[name, period] = f"{number:.1%}"
            else:
                shown.at[name, period] = f"{number:.2f}"
    return shown.to_string()


def main():
    if len(sys.argv) != 3:
        print("Usage: python -m engine.ratios <income statement csv> <balance sheet csv>")
        sys.exit(1)
    income, _ = load_statement(sys.argv[1])
    balance, _ = load_statement(sys.argv[2])
    print(format_ratios(compute_ratios(income, balance)))
    print()
    for name, *_, meaning in RATIOS:
        print(f"{name}: {meaning}")


if __name__ == "__main__":
    main()
