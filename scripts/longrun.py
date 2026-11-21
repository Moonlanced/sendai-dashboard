from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "data" / "raw" / "archive"
OUT = ROOT / "data" / "processed"

FW = str.maketrans("０１２３４５６７８９", "0123456789")
ERA = {"昭和": 1925, "平成": 1988, "令和": 2018}

# Changes in how the city counts, stated in the workbooks' footnotes.
BREAKS = {
    1996: "宿泊者数の調査方法を変更（全国観光統計基準に準拠） / Overnight-stay survey method changed",
    2010: "観光庁の共通基準を導入（観光地点の追加・集計方法の変更） / National common standard adopted",
}


def year_of(label: str) -> int:
    m = re.fullmatch(r"(昭和|平成|令和)([0-9０-９]+|元)年", str(label).strip())
    if not m:
        raise ValueError(f"not an era year: {label!r}")
    n = m.group(2).translate(FW)
    return ERA[m.group(1)] + (1 if n == "元" else int(n))


def read(path: Path) -> dict[int, tuple[float, str]]:
    ws = openpyxl.load_workbook(path, data_only=True).worksheets[0]
    out: dict[int, tuple[float, str]] = {}
    for row in ws.iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        if len(cells) >= 2 and isinstance(cells[1], (int, float)):
            out[year_of(cells[0])] = (float(cells[1]), str(cells[2]).replace("\n", " ") if len(cells) > 2 else "")
    if not out:
        raise ValueError(f"{path.name}: no year rows found")
    return out


def main() -> int:
    try:
        vis = read(ARCHIVE / "longrun_visitors.xlsx")
        sty = read(ARCHIVE / "longrun_stays.xlsx")
    except (FileNotFoundError, ValueError) as e:
        print(f"LONG-RUN FAILED: {e}\n(run: python scripts/download.py --all)", file=sys.stderr)
        return 1

    # cross-check with the series built from the annual PDF reports
    with open(OUT / "annual.csv", encoding="utf-8") as f:
        annual = {int(r["year"]): r for r in csv.DictReader(f)}
    errors = []
    for y, r in annual.items():
        for name, series, field in (("visitors", vis, "visitors"), ("stays", sty, "overnight_stays")):
            if y in series and r[field]:
                if abs(series[y][0] - float(r[field])) > 1:
                    errors.append(f"{y} {name}: workbook {series[y][0]:,.0f} vs PDF reports {float(r[field]):,.0f}")
    if errors:
        print("LONG-RUN MISMATCH:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    years = sorted(set(vis) | set(sty))
    with open(OUT / "longrun.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["year", "visitors", "overnight_stays", "note", "method_break"])
        for y in years:
            notes = [n for n in (vis.get(y, (0, ""))[1], sty.get(y, (0, ""))[1]) if n]
            w.writerow([y, round(vis[y][0]) if y in vis else None, round(sty[y][0]) if y in sty else None,
                        " / ".join(dict.fromkeys(notes)), BREAKS.get(y, "")])
    overlap = len([y for y in annual if y in vis])
    print(f"ok: long-run {years[0]}–{years[-1]}; {overlap} overlapping years match the PDF reports")
    return 0


if __name__ == "__main__":
    sys.exit(main())
