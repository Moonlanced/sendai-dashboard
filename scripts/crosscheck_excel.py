"""Cross-check the PDF extraction against the city's Excel version of each report.

The Excel layouts differ between years, so instead of parsing them this checks,
for each report, that every number extracted from that same report's PDF for its
own year (visitors, overnight stays, each district where printed, foreign guests,
each country) also appears somewhere in the matching workbook (±1 for rounding).

Writes data/processed/excel_crosscheck.csv. Any missing value -> non-zero exit.
Run after scripts/extract.py.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

import openpyxl
import xlrd

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "raw" / "archive"
OUT = ROOT / "data" / "processed"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract import REPORT_YEAR, parse  # noqa: E402

RAW = ROOT / "data" / "raw"


def workbook_numbers(path: Path) -> list[float]:
    nums: list[float] = []
    if path.suffix == ".xls":
        book = xlrd.open_workbook(path)
        for sh in book.sheets():
            for r in range(sh.nrows):
                nums += [float(v) for v in sh.row_values(r) if isinstance(v, (int, float))]
    else:
        wb = openpyxl.load_workbook(path, data_only=True)
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                nums += [float(v) for v in row if isinstance(v, (int, float)) and not isinstance(v, bool)]
    return nums


def main() -> int:
    rows, missing = [], []
    for label, year in REPORT_YEAR.items():
        path = next((p for p in (ARCHIVE / f"{label}.xlsx", ARCHIVE / f"{label}.xls") if p.exists()), None)
        if path is None:
            missing.append(f"{label}: no Excel file (run: python scripts/download.py --all)")
            continue
        nums = workbook_numbers(path)
        rep = parse(RAW / f"{label}.pdf")
        expected = {"visitors": rep.visitors.get(year), "foreign_stays": rep.foreign_total.get(year)}
        expected |= {f"stays:{d}": v for (y, d), v in rep.stays.items() if y == year}
        expected |= {f"foreign:{c}": v for (y, c), v in rep.countries.items() if y == year}
        found = 0
        for key, val in expected.items():
            if not val:
                continue
            v = float(val)
            if any(abs(n - v) <= 1 for n in nums):
                found += 1
            else:
                missing.append(f"{label} {year} {key} = {v:,.0f} not found in {path.name}")
        rows.append([label, year, path.name, found, len([v for v in expected.values() if v])])

    with open(OUT / "excel_crosscheck.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["report", "year", "excel_file", "values_found", "values_checked"])
        w.writerows(rows)
    if missing:
        print("EXCEL CROSS-CHECK FAILED:\n  " + "\n  ".join(missing), file=sys.stderr)
        return 1
    total = sum(r[3] for r in rows)
    print(f"ok: {total} values from {len(rows)} reports all found in the matching Excel files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
