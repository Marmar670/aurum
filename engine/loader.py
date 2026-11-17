"""Aurum loader: read a financial statement CSV and report structural problems.

The loader is the first stage of the calculation engine. It does two jobs:

1. Turn a statement file into a clean table of numbers (rows are line items,
   columns are months).
2. Report anything wrong with the file's structure: blank cells, text typed
   where a number belongs, duplicate rows, and duplicate or missing months.

It does not judge the accounting. Whether the numbers add up is checked by
later stages of the engine.

Run it from the project folder like this:

    python -m engine.loader data/sample/clean/income_statement.csv
"""

import csv
import sys
from dataclasses import dataclass
from datetime import datetime

import pandas as pd

# The format of the month headers in a statement file, for example "Jan 2026".
PERIOD_FORMAT = "%b %Y"


@dataclass
class Problem:
    """One thing the loader found wrong with a file."""

    check: str      # short code for the kind of problem, e.g. "missing_value"
    line_item: str  # the row it was found in ("" if it is about a column)
    period: str     # the month it was found in ("" if it is about a whole row)
    message: str    # a plain-language description

    def __str__(self):
        return f"[{self.check}] {self.message}"


def parse_number(text):
    """Turn the text of one cell into a number.

    Returns the number, or None if the text is not a valid number.
    Accepts everyday formats such as "4,500" and "$4,500".
    """
    cleaned = text.strip().replace(",", "").replace("$", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def check_periods(periods):
    """Look for duplicate, unreadable and missing months in the header row."""
    problems = []

    # Duplicate months: the same header appearing more than once.
    seen = set()
    for period in periods:
        if period in seen:
            problems.append(Problem(
                "duplicate_period", "", period,
                f"The period {period} appears more than once in the header.",
            ))
        seen.add(period)

    # Read each header as a date so the months can be compared.
    dates = []
    for period in seen:
        try:
            dates.append(datetime.strptime(period, PERIOD_FORMAT))
        except ValueError:
            problems.append(Problem(
                "unreadable_period", "", period,
                f"The header {period!r} is not a month like 'Jan 2026'.",
            ))

    # Missing months: walk from the earliest month to the latest, one month
    # at a time, and report any month that has no column.
    if dates:
        current, last = min(dates), max(dates)
        while current < last:
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
            if current not in dates:
                label = current.strftime(PERIOD_FORMAT)
                problems.append(Problem(
                    "missing_period", "", label,
                    f"The period {label} is missing from the header.",
                ))

    return problems


def load_statement(path):
    """Read a statement CSV file.

    Returns two things:
    - a table (pandas DataFrame) with one row per line item and one column
      per month, holding numbers. Cells that could not be read are left empty.
    - a list of Problem objects describing what is wrong with the file.
      An empty list means the file's structure is fine.
    """
    # utf-8-sig also handles files saved by Excel, which adds a hidden marker
    # at the start of the file.
    with open(path, newline="", encoding="utf-8-sig") as file:
        rows = [row for row in csv.reader(file) if any(cell.strip() for cell in row)]

    if not rows:
        return pd.DataFrame(), [Problem("empty_file", "", "", "The file has no content.")]

    header = [cell.strip() for cell in rows[0]]
    periods = header[1:]  # the first column holds the line item names
    problems = check_periods(periods)

    data = {}  # line item name -> {period: number}
    for row in rows[1:]:
        line_item = row[0].strip()

        if line_item in data:
            problems.append(Problem(
                "duplicate_line_item", line_item, "",
                f"The line item {line_item} appears more than once.",
            ))
            continue  # keep the first copy and skip the repeat

        values = {}
        for position, period in enumerate(periods, start=1):
            if period in values:
                continue  # a duplicate month column: keep the first one
            text = row[position] if position < len(row) else ""

            if text.strip() == "":
                problems.append(Problem(
                    "missing_value", line_item, period,
                    f"Missing value in {line_item} for {period}.",
                ))
                values[period] = None
                continue

            number = parse_number(text)
            if number is None:
                problems.append(Problem(
                    "non_numeric_value", line_item, period,
                    f"Non-numeric value {text.strip()!r} in {line_item} for {period}.",
                ))
            values[period] = number

        data[line_item] = values

    table = pd.DataFrame.from_dict(data, orient="index")
    table.index.name = "Line Item"
    return table, problems


def main():
    """Load the file named on the command line and print what was found."""
    if len(sys.argv) != 2:
        print("Usage: python -m engine.loader <path to statement csv>")
        sys.exit(1)

    table, problems = load_statement(sys.argv[1])

    print(table.to_string())
    print()
    if problems:
        print(f"{len(problems)} problem(s) found:")
        for problem in problems:
            print(f"  {problem}")
    else:
        print("No structural problems found.")


if __name__ == "__main__":
    main()
