"""Extract Sendai mobility data into tidy CSVs.

Input  (scripts/mobility_download.py): data/raw/mobility/{yearbook,subway,airport}/
Output: data/processed/mobility/
  transit_fy.csv     city bus and subway: passengers per fiscal year, FY2006–  (仙台市統計書)
  jr_stations_fy.csv JR stations in Sendai: average daily boardings per fiscal year, FY2007–  (仙台市統計書)
  subway_stations_fy.csv  subway boardings per station and fiscal year, FY2007–  (交通局)
  airport_cy.csv     Sendai Airport passengers per calendar year, domestic / international  (国土交通省)
  revisions.csv      every value a newer source edition changed (newest wins)
  checks.csv         every check run, passed True/False

Tables are found by their titles, not by file or sheet name, because the yearbook's
files were named five different ways between 2011 and 2025. Each edition repeats
several past years, so overlapping years are compared across editions.

Hard failures (non-zero exit, nothing written): a table that can't be found, or a
row whose numbers can't be read. Arithmetic that doesn't add up in the source is
logged in checks.csv (passed=False) and printed, not hidden.
"""
from __future__ import annotations

import calendar
import csv
import re
import sys
import unicodedata
import warnings
from collections import defaultdict
from pathlib import Path

import openpyxl
import xlrd

warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "mobility"
OUT = ROOT / "data" / "processed" / "mobility"
ERA = {"平成": 1988, "令和": 2018, "昭和": 1925}
FIRST_JR_FY = 2007  # before FY2007 仙台 included Shinkansen passengers and 総数 included unmanned stations

# Check results that don't add up but have a documented explanation. They stay in
# checks.csv with passed="explained" and the reason, so nothing is hidden.
EXPLAINED = {
    "subway FY2010:": "average over 362 operating days: service suspended after the 11 March 2011 earthquake",
    "bus FY2016:": "source error: the printed daily average divides by 366 days, but FY2016 (Apr 2016–Mar 2017) has 365",
    "subway FY2016:": "source error: the printed daily average divides by 366 days, but FY2016 (Apr 2016–Mar 2017) has 365",
    "JR FY2007:": "the table's own footnote: totals up to FY2007 include unmanned stations",
}


def explain(check: list) -> list:
    """Turn a failed check into passed='explained' when it has a documented reason."""
    if check[2] is False:
        reason = next((r for k, r in EXPLAINED.items() if check[1].startswith(k)), None)
        if reason:
            return [check[0], check[1], "explained", f"{check[3]} — {reason}"]
    return check


class ExtractionError(Exception):
    pass


def flat(x) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(x))) if x is not None else ""


def number(x) -> float | None:
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    s = flat(x).replace(",", "")
    return float(s) if re.fullmatch(r"-?\d+(\.\d+)?", s) else None


def sheets(path: Path):
    """Yield (sheet name, rows as lists) for .xls / .xlsx / .xlsm."""
    if path.suffix.lower() == ".xls":
        book = xlrd.open_workbook(path)
        for sh in book.sheets():
            yield sh.name, [sh.row_values(r) for r in range(sh.nrows)]
    else:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            yield ws.title, [list(r) for r in ws.iter_rows(values_only=True)]


def edition_year(label: str) -> int:
    m = re.match(r"(令和|平成)(\d+|元)年版", label)
    if not m:
        raise ExtractionError(f"cannot read edition year from folder {label!r}")
    return ERA[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2)))


def fy_label(text: str) -> int | None:
    m = re.fullmatch(r"(平成|令和|昭和)(\d+|元)年度", flat(text))
    return ERA[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2))) if m else None


def find_tables(must: list[str]):
    """Yield (edition label, edition year, file, sheet, rows) for yearbook sheets whose
    first 8 rows contain every string in `must`."""
    for ed_dir in sorted((RAW / "yearbook").iterdir(), key=lambda p: edition_year(p.name)):
        for path in sorted(ed_dir.iterdir()):
            if path.suffix.lower() not in (".xls", ".xlsx"):
                continue
            for name, rows in sheets(path):
                head = "".join(flat(c) for r in rows[:8] for c in r if isinstance(c, str))
                if all(m in head for m in must):
                    yield ed_dir.name, edition_year(ed_dir.name), path.name, name, rows


class Merger:
    """Newest edition wins; every overridden value is recorded."""

    def __init__(self, table: str, revisions: list):
        self.table, self.revisions = table, revisions
        self.values: dict = {}
        self.source: dict = {}

    def add(self, key, value: float, source: str) -> None:
        if key in self.values and abs(self.values[key] - value) > 0.5:
            self.revisions.append([self.table, key, self.values[key], self.source[key], value, source])
        self.values[key], self.source[key] = value, source


# ------------------------------------------------------------- city bus and subway
def transit(checks: list, revisions: list) -> list[list]:
    m = Merger("transit", revisions)
    found = 0
    for label, _ey, fname, sheet, rows in find_tables(["市営バス及"]):
        found += 1
        mode, era, year, annual = None, None, None, False
        for r in rows:
            cells = [c for c in r if c not in (None, "")]
            if not cells:
                continue
            head = flat(cells[0])
            if head in ("市営バス",):
                mode, annual = "bus", True
                continue
            if head in ("市営地下鉄", "地下鉄"):
                mode, annual = "subway", True
                continue
            if mode is None:
                continue
            fy = fy_label(cells[0])
            if fy is not None:
                era, year, annual = flat(cells[0])[:2], fy, True
            elif annual and number(cells[0]) is not None and year is not None:
                year += 1
            elif re.fullmatch(r"(平成|令和)(\d+|元)年", head):  # monthly rows start
                annual = False
                continue
            else:
                continue
            if not annual:
                continue
            n = [number(c) for c in cells[1:]]
            if len(n) < 8 or n[2] is None or n[7] is None:
                raise ExtractionError(f"{label} {fname}:{sheet} {mode} FY{year}: row not readable: {cells}")
            passengers, daily = n[2], n[7]
            days = 366 if calendar.isleap(year + 1) else 365
            ok = abs(passengers / days - daily) <= 1
            # the subway's FY2015 average is over the year, though the 東西線 opened in December
            checks.append([f"{label} {fname}:{sheet}", f"{mode} FY{year}: passengers / {days} days == daily average",
                           ok, f"{passengers / days:,.0f} vs {daily:,.0f}"])
            m.add((mode, year), passengers, label)
    if not found:
        raise ExtractionError("市営バス及び地下鉄 table not found in any yearbook edition")
    return [[y, mode, int(v), m.source[(mode, y)]] for (mode, y), v in sorted(m.values.items(), key=lambda kv: (kv[0][1], kv[0][0]))]


# ------------------------------------------------------------- JR stations
def jr(checks: list, revisions: list) -> list[list]:
    m = Merger("jr_stations", revisions)
    found = 0
    for label, _ey, fname, sheet, rows in find_tables(["旅客輸送状況"]):
        if "貨物" in "".join(flat(c) for r in rows[:3] for c in r if isinstance(c, str)):
            continue
        found += 1
        years: list[int | None] | None = None
        table: dict[str, list] = {}
        for r in rows:
            cells = [c for c in r if c not in (None, "")]
            if not cells:
                continue
            head = flat(cells[0])
            if head == "駅名":
                years = [fy_label(c) for c in cells[1:]]
                continue
            if years is None or head.startswith("資料") or head.startswith("(うち") or head.startswith("（うち"):
                continue
            if head.startswith("(別") or head.startswith("（別"):
                continue
            vals = [number(c) for c in cells[1:1 + len(years)]]
            if not any(v is not None for v in vals):
                continue
            table[head] = vals
        if years is None or "総数" not in table:
            raise ExtractionError(f"{label} {fname}:{sheet}: JR table header or 総数 not found")
        stations = [s for s in table if s not in ("総数",) and not s.startswith("新幹線")]
        for i, y in enumerate(years):
            if y is None or y < FIRST_JR_FY:
                continue
            col = [table[s][i] for s in stations]
            total = table["総数"][i]
            if total is not None and None not in col:
                ok = abs(sum(col) - total) <= 1
                checks.append([f"{label} {fname}:{sheet}", f"JR FY{y}: stations sum == 総数", ok,
                               f"{sum(col):,.0f} vs {total:,.0f}"])
            for s in list(table):
                v = table[s][i]
                if v is not None and v > 0:
                    m.add((y, s), v, label)
    if not found:
        raise ExtractionError("JR 旅客輸送状況 table not found in any yearbook edition")
    return [[y, s, int(v), m.source[(y, s)]] for (y, s), v in sorted(m.values.items())]


# ------------------------------------------------------------- subway stations (交通局 file)
def subway_stations(checks: list) -> list[list]:
    path = RAW / "subway" / "subway_passengers.xlsx"
    out = []
    for _name, rows in sheets(path):
        line, cols = None, None
        for r in rows:
            texts = [flat(c) for c in r]
            if any(t.startswith("【南北線") for t in texts):
                line, cols = "南北線", None
                continue
            if any(t.startswith("【東西線") for t in texts):
                line, cols = "東西線", None
                continue
            if any(t.startswith("【総計") for t in texts):
                line = None
                continue
            if line is None:
                continue
            if texts and texts[0] == "駅名":
                cols = {i: fy_label(c) for i, c in enumerate(r) if fy_label(c)}
                continue
            if cols is None or not texts or not texts[0] or texts[0] == "乗車人員":
                continue
            station = re.sub(r"[()（）]", lambda x: "（" if x.group() in "(（" else "）", texts[0])
            for i, y in cols.items():
                v = number(r[i]) if i < len(r) else None
                if v is not None:
                    out.append([y, line, station, int(v)])
    if not out:
        raise ExtractionError("subway_passengers.xlsx: no station rows found")
    # check: stations (incl. transfer counts) add up to each line's 総数
    by = defaultdict(lambda: defaultdict(dict))
    for y, line, st, v in out:
        by[(line, y)][st] = v
    for (line, y), d in sorted(by.items()):
        if "総数" in d:
            s = sum(v for k, v in d.items() if k != "総数")
            checks.append(["subway_passengers.xlsx", f"{line} FY{y}: stations sum == 総数", abs(s - d["総数"]) <= 1,
                           f"{s:,} vs {d['総数']:,}"])
    return out


# ------------------------------------------------------------- Sendai Airport (国土交通省)
def airport(checks: list, revisions: list) -> list[list]:
    m = Merger("airport", revisions)
    files = sorted(p for p in (RAW / "airport").iterdir() if p.suffix.lower() in (".xls", ".xlsx", ".xlsm"))
    if not files:
        raise ExtractionError("no airport files")
    for path in files:
        for _name, rows in sheets(path):
            start = next((i for i, r in enumerate(rows)
                          if any(flat(c).startswith("空港名") for c in r)
                          and any(flat(c).startswith("仙台") for c in r)), None)
            if start is None:
                continue
            era, prev, block = "平成", None, []
            for r in rows[start + 1:start + 40]:
                cells = [c for c in r if c not in (None, "")]
                # older files put a marker (○) before the year label
                if cells and flat(cells[0]) in ("○", "◯"):
                    cells = cells[1:]
                if not cells:
                    if block:
                        break  # first block = calendar years (暦年); the second is fiscal years
                    continue
                lab = flat(cells[0])
                if not re.fullmatch(r"\d+|元", lab):
                    continue
                if lab == "元":
                    era = "令和"
                y = ERA[era] + (1 if lab == "元" else int(lab))
                if block and y <= prev:
                    break  # older files have no blank row: the fiscal-year block starts when the year restarts
                if prev is not None and y != prev + 1:
                    raise ExtractionError(f"{path.name}: airport years not consecutive ({prev} -> {y})")
                prev = y
                n = [number(c) for c in cells[1:]]
                i_on, i_off, i_tr, i_sub, d_on, d_off, d_sub, total = n[3:11]
                ok = abs(i_on + i_off + i_tr - i_sub) <= 1 and abs(d_on + d_off - d_sub) <= 1 and abs(i_sub + d_sub - total) <= 1
                checks.append([path.name, f"airport {y}: on + off = subtotal, intl + domestic = total", ok,
                               f"{i_sub:,.0f} + {d_sub:,.0f} = {total:,.0f}"])
                block.append(y)
                m.add((y, "international"), i_sub, path.name)
                m.add((y, "domestic"), d_sub, path.name)
            if not block:
                raise ExtractionError(f"{path.name}: Sendai block found but no year rows")
            break
        else:
            raise ExtractionError(f"{path.name}: no Sendai Airport block")
    years = sorted({y for y, _ in m.values})
    return [[y, int(m.values[(y, "domestic")]), int(m.values[(y, "international")]),
             int(m.values[(y, "domestic")] + m.values[(y, "international")])] for y in years]


def write(name: str, header: list[str], rows: list[list]) -> None:
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    checks, revisions = [], []
    try:
        t = transit(checks, revisions)
        j = jr(checks, revisions)
        s = subway_stations(checks)
        a = airport(checks, revisions)
    except (ExtractionError, FileNotFoundError) as e:
        print(f"MOBILITY EXTRACTION FAILED: {e}", file=sys.stderr)
        return 1
    checks = [explain(c) for c in checks]
    OUT.mkdir(parents=True, exist_ok=True)
    write("transit_fy.csv", ["fiscal_year", "mode", "passengers", "source_edition"], t)
    write("jr_stations_fy.csv", ["fiscal_year", "station", "daily_boardings", "source_edition"], j)
    write("subway_stations_fy.csv", ["fiscal_year", "line", "station", "boardings"], s)
    write("airport_cy.csv", ["year", "domestic", "international", "total"], a)
    write("revisions.csv", ["table", "key", "old", "old_source", "new", "new_source"], revisions)
    write("checks.csv", ["source", "check", "passed", "detail"], checks)
    bad = [c for c in checks if c[2] is False]
    explained = {c[1].split(":")[0] for c in checks if c[2] == "explained"}
    print(f"ok: transit FY{t[0][0]}–{t[-1][0]}, JR FY{j[0][0]}–{j[-1][0]}, subway stations FY{s[0][0]}–{max(r[0] for r in s)}, "
          f"airport {a[0][0]}–{a[-1][0]}; {len(checks)} checks, {len(bad)} unexplained, "
          f"explained: {', '.join(sorted(explained)) or 'none'}; {len(revisions)} revisions")
    for c in bad:
        print(f"CHECK  {c[0]}: {c[1]} ({c[3]})")
    for r in revisions:
        print(f"REVISED {r[0]} {r[1]}: {r[2]:,.0f} ({r[3]}) -> {r[4]:,.0f} ({r[5]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
