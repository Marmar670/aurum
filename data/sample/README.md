# Aurum sample data

Sample statements for Prairie Bean Coffee Co., a fictional small business invented for testing. No real company data is used. Amounts are in Canadian dollars and cover January to June 2026.

## Folders

- `clean/` holds a correct income statement and balance sheet. The engine should report no problems here.
- `errors/` holds ten copies, each with exactly one mistake planted on purpose.
- `planted_errors.csv` is the same answer key in a form the tests can read.

## How the clean statements fit together

- Gross Profit equals Sales Revenue minus Cost of Goods Sold.
- Total Assets equals Total Liabilities and Equity in every month.
- Retained Earnings rises each month by exactly that month's Net Income. Opening Retained Earnings at the end of December 2025 was 12,000.
- Accumulated Depreciation is stored as a negative number.

## Answer key: the ten planted errors

| ID | File | Period | What was changed | What the engine should flag |
| --- | --- | --- | --- | --- |
| E01 | `E01_balance_sheet_unbalanced.csv` | Mar 2026 | Inventory overstated by 1,500. Asset totals include the extra amount. | Total Assets does not equal Total Liabilities and Equity (difference of 1,500). |
| E02 | `E02_balance_sheet_missing_line.csv` | All months | The Accounts Payable row was deleted. Totals were left as they were. | Required line item is missing, and Total Current Liabilities does not equal the sum of its lines. |
| E03 | `E03_income_statement_missing_value.csv` | Apr 2026 | The Rent cell is blank. | Missing value in Rent for Apr 2026. |
| E04 | `E04_income_statement_expense_spike.csv` | May 2026 | Utilities entered as 9,200 instead of 920 (an extra zero). Totals include the wrong amount. | Unusual month to month change in Utilities (about ten times the prior month). |
| E05 | `E05_income_statement_wrong_subtotal.csv` | Feb 2026 | Gross Profit typed as 29,670 instead of 26,970 (two digits swapped). | Gross Profit does not equal Sales Revenue minus Cost of Goods Sold. |
| E06 | `E06_income_statement_sign_error.csv` | Jun 2026 | Marketing entered as -650 instead of 650. Totals include the wrong amount. | Negative value in an expense line (Marketing). |
| E07 | `E07_income_statement_duplicate_line.csv` | All months | The Rent row appears twice. Totals were left as they were. | Duplicate line item (Rent), and Total Operating Expenses does not equal the sum of its lines. |
| E08 | `E08_balance_sheet_retained_earnings.csv` | Jun 2026 | 3,000 moved out of Retained Earnings and into Bank Loan. The sheet still balances. | Change in Retained Earnings does not equal Net Income for the month. |
| E09 | `E09_income_statement_text_in_number.csv` | Mar 2026 | Insurance typed as 35O, with the letter O in place of the final zero. | Non-numeric value in Insurance for Mar 2026. |
| E10 | `E10_balance_sheet_duplicate_period.csv` | Apr 2026 | The Apr 2026 column is labelled Mar 2026, so Mar appears twice and Apr is missing. | Duplicate period header (Mar 2026) and missing period (Apr 2026). |

E08 is checked by reading the error file together with `clean/income_statement.csv`.
