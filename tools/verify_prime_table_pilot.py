"""Independent arithmetic checks for the Handbook's PDF pages 31–39.

Run locally with the user's source PDF; no reference PDF belongs in the repo.
Checks detect displaced cells and missing rows without repairing source values.
"""
import argparse
from math import isqrt
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ingestion.table_layout import extract_pdf_table_layouts


def smallest_factor(number):
    for divisor in range(2, isqrt(number) + 1):
        if number % divisor == 0:
            return divisor
    return None


def verify_layouts(layouts):
    errors = []
    exceptions = []
    factor_cell_count = 0
    prime_cell_count = 0
    by_page = {layout["page_number"]: layout for layout in layouts}
    if len(layouts) != 9 or set(by_page) != set(range(31, 40)):
        errors.append("Expected exactly one recovered table per PDF page 31–39.")
    for page in range(31, 39):
        table = by_page.get(page)
        if table is None:
            continue
        grid = table["grid"]
        bases = list(range((page - 31) * 1200, (page - 30) * 1200, 100))
        expected_header = ["From\nTo"] + [f"{base}\n{base + 100}" for base in bases]
        if not grid or grid[0] != expected_header:
            errors.append(f"Page {page}: column-range headers do not match.")
            continue
        offsets = ([1, 2] + list(range(3, 100, 2)) if page == 31
                   else list(range(1, 100, 2)))
        if len(grid) != len(offsets) + 1 or any(len(row) != 13 for row in grid):
            errors.append(f"Page {page}: row or column count does not match.")
            continue
        for row_number, (offset, row) in enumerate(zip(offsets, grid[1:]), start=2):
            if row[0] != str(offset):
                errors.append(f"Page {page}, row {row_number}: row label displaced.")
            for column_number, (base, value) in enumerate(zip(bases, row[1:]), start=2):
                number = base + offset
                factor_cell_count += 1
                if number == 1:
                    if value != "P":
                        errors.append("Source convention at 1 was changed.")
                    exceptions.append({"page": page, "number": 1, "printed_value": value,
                                       "note": "Preserved source notation; 1 is not prime."})
                    continue
                factor = smallest_factor(number)
                expected = "P" if factor is None else str(factor)
                if value != expected:
                    errors.append(f"Page {page}, row {row_number}, column {column_number}: "
                                  f"{number} has {value!r}, expected {expected!r}.")
    table = by_page.get(39)
    if table:
        grid = table["grid"]
        if len(grid) != 68 or any(len(row) != 14 for row in grid):
            errors.append("Page 39: expected 68 rows and 14 columns.")
        try:
            actual = [int(value) for row in grid for value in row]
            prime_cell_count = len(actual)
            expected = {number for number in range(9551, 18692)
                        if smallest_factor(number) is None}
            if set(actual) != expected or len(actual) != len(expected):
                errors.append("Page 39: prime list has missing, duplicated, or non-prime values.")
            for column in zip(*grid):
                values = [int(value) for value in column]
                if values != sorted(values):
                    errors.append("Page 39: a column is not in source reading order.")
        except ValueError:
            errors.append("Page 39: a cell is not an integer.")
    return {"passed": not errors, "table_count": len(layouts),
            "factor_cell_count": factor_cell_count, "prime_cell_count": prime_cell_count,
            "exceptions": exceptions, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_pdf")
    args = parser.parse_args()
    report = verify_layouts(extract_pdf_table_layouts(args.source_pdf, range(31, 40)))
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
