"""Extract City of Sendai population statistics into tidy CSVs.

Input  (scripts/population_download.py): data/raw/population/{monthly,age5,projection}/
Output: data/processed/population/
  pop_monthly.csv      population, men, women, households on the 1st of each month, 1999–
  vitals_monthly.csv   births and deaths in each month (Japanese + foreign residents where reported)
  age_groups.csv       population by 5-year age group, city and wards, 2003–
  age3.csv             0–14 / 15–64 / 65+ by area, 2003–
  projection.csv       city projection 2020–2070 (令和4年推計) by area and age group
  checks.csv           every consistency check run and its result

The old and new files order their columns differently, so columns are found by
structure, not position: the population total is the number that equals men +
women, and natural change is the number that equals births − deaths.

Hard checks (any failure -> non-zero exit, nothing written):
  * every monthly file yields all 5 wards and the city total, with total = men + women
  * the 5 wards add up to the city total (population, births, deaths, age groups)
  * every month from the first to the last file is present exactly once
  * births/deaths summed over each year equal the yearly totals printed in the newest file
  * projection: single-year ages (+ 年齢不詳 in 2020) add up to each year's total

Errors found in the source (a printed figure that contradicts the same file's other
figures) are logged in checks.csv with passed=False and the correct value is used.
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import openpyxl
import xlrd

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "population"
OUT = ROOT / "data" / "processed" / "population"

WARDS = ["青葉区", "宮城野区", "若林区", "太白区", "泉区"]
SUBS = ["宮城総合支所", "秋保総合支所"]  # sub-areas of 青葉区 / 太白区, not added to the city total
AREA_EN = {"仙台市": "Sendai (city)", "青葉区": "Aoba", "宮城野区": "Miyagino", "若林区": "Wakabayashi",
           "太白区": "Taihaku", "泉区": "Izumi", "宮城総合支所": "Miyagi area (Aoba)", "秋保総合支所": "Akiu area (Taihaku)"}
ERA = {"h": 1988, "r": 2018}


class CheckError(Exception):
    pass


def norm(label) -> str | None:
    """'うち宮城総合支所', ' 青　葉　区', '総  数', '仙   台   市   計' -> canonical area name."""
    if not isinstance(label, str):
        return None
    s = re.sub(r"\s+", "", unicodedata.normalize("NFKC", label)).removeprefix("うち")
    if s in ("総数", "仙台市計", "仙台市", "計", "年齢計"):
        return "仙台市"
    return s if s in WARDS or s in SUBS else None


def rows(path: Path):
    """Yield (sheet_name, [cell values]) for every row of an .xls or .xlsx file."""
    if path.suffix.lower() == ".xls":
        book = xlrd.open_workbook(path)
        for sh in book.sheets():
            for r in range(sh.nrows):
                yield sh.name, sh.row_values(r)
    else:
        wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
        for ws in wb.worksheets:
            for r in ws.iter_rows(values_only=True):
                yield ws.title, list(r)


def nums(cells) -> list[float]:
    return [float(c) for c in cells if isinstance(c, (int, float)) and not isinstance(c, bool)]


def first_text(cells) -> str | None:
    return next((c for c in cells if isinstance(c, str) and c.strip()), None)


def file_month(path: Path) -> tuple[int, int]:
    m = re.match(r"([hr])(\d\d)(\d\d)", path.stem.lower())
    if not m:
        raise CheckError(f"{path.name}: cannot read year/month from file name")
    return ERA[m.group(1)] + int(m.group(2)), int(m.group(3))


# ---------------------------------------------------------------- monthly files
def parse_monthly(path: Path):
    """-> (population {area: (total, men, women, households)},
           vitals {area: [births, deaths]},
           flags [(area, problem)])  # printed natural change != births − deaths

    Movement blocks come in two layouts, told apart by their column headers:
      old (1999–2009): 出生, 死亡, 転入, ...          -> births n[0], deaths n[1]
      new (2009–):     人口増加数, 自然増加数, 出生, 死亡, ... -> births n[2], deaths n[3]
    A file can hold several blocks (Japanese and foreign residents); they are added up.
    """
    pop: dict[str, tuple] = {}
    vit: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])
    flags: list[tuple[str, str]] = []
    section, layout = "pop", None
    for sheet, cells in rows(path):
        text = "".join(c for c in cells if isinstance(c, str))
        flat = re.sub(r"\s+", "", unicodedata.normalize("NFKC", text))
        if "推移" in flat:  # history tables at the end of a sheet are not per-area
            section, layout = "skip", None
        elif "推計人口" in flat and "動態" not in sheet:
            section = "pop"
        elif "異動" in flat or "動態" in flat:  # a block title: new block, layout from its header
            section, layout = "move", None
        elif "動態" in sheet and section == "pop":
            section = "move"
        if section == "move":
            if flat.startswith("出生死亡"):
                layout = "old"
            elif "自然増加数" in flat:
                layout = "new"
        area = norm(first_text(cells))
        if area is None:
            continue
        n = nums(cells)
        if section == "pop" and area not in pop:
            # total = men + women; households sit before (old layout) or after (new layout)
            for i in range(len(n) - 2):
                if n[i] > 1000 and n[i] == n[i + 1] + n[i + 2]:
                    hh = n[i - 1] if i == 1 else (n[i + 3] if len(n) > i + 3 else None)
                    pop[area] = (n[i], n[i + 1], n[i + 2], hh)
                    break
        elif section == "move" and layout == "new" and len(n) >= 4:
            vit[area][0] += n[2]
            vit[area][1] += n[3]
            if n[1] != n[2] - n[3]:
                flags.append((area, f"自然増加数 printed {n[1]:.0f}, births − deaths = {n[2] - n[3]:.0f}"))
        elif section == "move" and layout == "old" and len(n) >= 2 and area not in vit:
            vit[area] = [n[0], n[1]]
    return pop, dict(vit), flags


def monthly() -> tuple[list, list, list]:
    files = sorted(p for p in (RAW / "monthly").iterdir() if p.suffix.lower() in (".xls", ".xlsx"))
    if not files:
        raise CheckError("no monthly files — run scripts/population_download.py")
    pop_rows, vit_rows, checks, seen = [], [], [], {}
    for path in files:
        y, m = file_month(path)
        if (y, m) in seen:
            raise CheckError(f"{path.name}: month {y}-{m:02d} already read from {seen[(y, m)]}")
        seen[(y, m)] = path.name
        pop, vit, flags = parse_monthly(path)
        for area, problem in flags:
            checks.append([path.name, f"source typo? {area}", False, problem])
        missing = [a for a in ["仙台市"] + WARDS if a not in pop]
        if missing:
            raise CheckError(f"{path.name}: population rows not found for {missing}")
        wsum = sum(pop[w][0] for w in WARDS)
        if abs(wsum - pop["仙台市"][0]) > 0:
            raise CheckError(f"{path.name}: wards sum {wsum:,.0f} != city {pop['仙台市'][0]:,.0f}")
        for a, (t, men, women, hh) in pop.items():
            pop_rows.append([f"{y}-{m:02d}-01", a, AREA_EN[a], int(t), int(men), int(women), int(hh) if hh else None])
        # births/deaths in this file are for the previous month
        py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
        if all(a in vit for a in ["仙台市"] + WARDS):
            for k, what in ((0, "births"), (1, "deaths")):
                ws = sum(vit[w][k] for w in WARDS)
                ok = ws == vit["仙台市"][k]
                checks.append([path.name, f"{what}: wards sum == city", ok, f"{ws:.0f} vs {vit['仙台市'][k]:.0f}"])
                if not ok:
                    raise CheckError(f"{path.name}: {what} wards sum {ws:.0f} != city {vit['仙台市'][k]:.0f}")
            for a, (b, d) in vit.items():
                vit_rows.append([f"{py}-{pm:02d}", a, AREA_EN[a], int(b), int(d)])
        else:
            checks.append([path.name, "births/deaths found", False, "movement block not recognised; month left out"])
        checks.append([path.name, "population: wards sum == city", True, f"{wsum:,.0f}"])

    # continuity: every month between first and last exactly once
    months = sorted(seen)
    y, m = months[0]
    expected = []
    while (y, m) <= months[-1]:
        expected.append((y, m))
        y, m = (y, m + 1) if m < 12 else (y + 1, 1)
    gaps = [f"{y}-{m:02d}" for y, m in expected if (y, m) not in seen]
    if gaps:
        raise CheckError(f"monthly series has gaps: {gaps}")
    return pop_rows, vit_rows, checks


def annual_check(vit_rows: list[list]) -> list[list]:
    """Compare births/deaths summed from the monthly files with the yearly totals the
    city prints in its newest file (人口動態の推移). Any difference -> CheckError."""
    newest = max((p for p in (RAW / "monthly").iterdir() if p.suffix.lower() in (".xls", ".xlsx")),
                 key=lambda p: file_month(p))
    printed, in_history = {}, False
    for _, cells in rows(newest):
        flat = re.sub(r"\s+", "", unicodedata.normalize("NFKC", "".join(c for c in cells if isinstance(c, str))))
        if "動態の推移" in flat:
            in_history = True
            continue
        label = re.sub(r"\s+", "", first_text(cells) or "")
        m = re.fullmatch(r"(平成|令和)(\d+|元)年", label)
        n = nums(cells)
        if in_history and m and len(n) >= 4:
            y = ERA["h" if m.group(1) == "平成" else "r"] + (1 if m.group(2) == "元" else int(m.group(2)))
            printed[y] = (n[2], n[3])
    if not printed:
        raise CheckError(f"{newest.name}: yearly 人口動態の推移 table not found")
    summed = defaultdict(lambda: [0, 0])
    for month, area, _en, b, d in vit_rows:
        if area == "仙台市":
            summed[int(month[:4])][0] += b
            summed[int(month[:4])][1] += d
    checks = []
    for y, (b, d) in sorted(printed.items()):
        ok = summed[y] == [b, d]
        checks.append([newest.name, f"{y} births/deaths: monthly sum == printed yearly total", ok,
                       f"{summed[y][0]:,}/{summed[y][1]:,} vs {b:,.0f}/{d:,.0f}"])
        if not ok:
            raise CheckError(f"{y}: monthly births/deaths {summed[y]} != yearly table {b:.0f}/{d:.0f}")
    return checks


# ---------------------------------------------------------------- age files
AGE_GROUP = re.compile(r"^(\d+)[~～](\d+)$|^100歳以上$")  # NFKC turns ～ into ~


def age5() -> tuple[list, list, list]:
    groups, age3, checks = [], [], []
    for path in sorted((RAW / "age5").glob("*.xlsx")):
        m = re.search(r"([hr])(\d\d)(\d\d)", path.stem.lower())
        date = f"{ERA[m.group(1)] + int(m.group(2))}-{m.group(3)}-01"
        area_cols: list[str] = []
        totals: dict[str, float] = {}
        bands: dict[str, dict[str, float]] = defaultdict(dict)
        for _, cells in rows(path):
            texts = [c for c in cells if isinstance(c, str) and c.strip()]
            if not area_cols and len(texts) >= 6 and all(norm(t) for t in texts[1:7]):
                area_cols = [norm(t) for t in texts[1:7]]
                continue
            label = re.sub(r"\s+", "", unicodedata.normalize("NFKC", first_text(cells) or ""))
            n = nums(cells)
            if not area_cols or len(n) < 18:
                continue
            per_area = {a: n[3 * k] for k, a in enumerate(area_cols)}  # 総数 column of each area
            if label == "総数" and not totals:
                totals = per_area
            elif AGE_GROUP.match(label):
                for a, v in per_area.items():
                    bands[label].setdefault(a, v)
        if not area_cols or not totals:
            raise CheckError(f"{path.name}: age table not found")
        five = [g for g in bands if AGE_GROUP.match(g)]
        for a in area_cols:
            s = sum(bands[g][a] for g in five)
            if s != totals[a]:
                raise CheckError(f"{path.name} {a}: age groups sum {s:,.0f} != total {totals[a]:,.0f}")
            for g in five:
                groups.append([date, a, AREA_EN[a], g, int(bands[g][a])])
            u15 = sum(bands[g][a] for g in five if int(re.match(r"\d+", g).group()) < 15)
            o65 = sum(bands[g][a] for g in five if int(re.match(r"\d+", g).group()) >= 65)
            age3.append([date, a, AREA_EN[a], int(totals[a]), int(u15), int(totals[a] - u15 - o65), int(o65)])
        ws = sum(totals[w] for w in WARDS)
        if ws != totals["仙台市"]:
            raise CheckError(f"{path.name}: wards sum {ws:,.0f} != city {totals['仙台市']:,.0f}")
        checks.append([path.name, "age groups sum to totals; wards sum to city", True, f"{totals['仙台市']:,.0f}"])
    return groups, age3, checks


# ---------------------------------------------------------------- projections
def projection() -> tuple[list, list]:
    """Age groups are built from the single-year ages (■各歳別人口), which are the
    projection's base data. The city's own 3-group summary table is compared with
    them and every disagreement is logged in checks.csv (it is not used)."""
    out, checks = [], []
    sources = [("shoiraisuikeizinkou.xlsx", None)] + [("kusyouraizinkou.xlsx", w) for w in WARDS]
    for name, sheet in sources:
        wb = openpyxl.load_workbook(RAW / "projection" / name, data_only=True, read_only=True)
        ws = wb[sheet] if sheet else wb.worksheets[0]
        area = sheet or "仙台市"
        years, summary, ages, part = None, {}, {}, None
        for r in ws.iter_rows(values_only=True):
            cells = [c for c in r if c is not None]
            if not cells:
                continue
            first = re.sub(r"\s+", "", str(cells[0]))
            if first.startswith("■年齢3区分") or first.startswith("■年齢３区分"):
                part = "summary"
                continue
            if first.startswith("■各歳"):
                part = "single"
                continue
            if first.startswith("■"):
                part = None
                continue
            if isinstance(cells[0], str) and re.match(r"\d{4}年", cells[0]):
                ys = [int(c[:4]) for c in cells if isinstance(c, str) and re.match(r"\d{4}年", c)]
                years = years or ys
                if ys != years:
                    raise CheckError(f"{name} {area}: year headers differ between tables")
                continue
            values = nums(cells[1:])
            if part == "summary" and first in ("計", "年齢計", "0～14歳", "15～64歳", "65歳～"):
                summary.setdefault("計" if first == "年齢計" else first, values)
            elif part == "single":
                m = re.match(r"^(\d+)歳(以上)?$", first)
                if m:
                    ages[int(m.group(1))] = values
                elif first in ("計", "年齢計"):
                    summary.setdefault("single_total", values)
                elif first == "年齢不詳":
                    ages["unknown"] = values
        if not years or len(ages) < 100:
            raise CheckError(f"{name} {area}: single-year age table not found")
        for i, y in enumerate(years):
            def band(lo, hi):
                return sum(ages[a][i] for a in ages if a != "unknown" and lo <= a <= hi and i < len(ages[a]))
            u15, mid, o65 = band(0, 14), band(15, 64), band(65, 200)
            unknown = ages.get("unknown", [0])[i] if i < len(ages.get("unknown", [])) else 0
            total = summary["計"][i]
            if abs(u15 + mid + o65 + unknown - total) > 1:
                raise CheckError(f"{name} {area} {y}: single-year ages sum {u15 + mid + o65 + unknown:,.0f} != total {total:,.0f}")
            for label, derived in (("0～14歳", u15), ("15～64歳", mid), ("65歳～", o65)):
                printed = summary[label][i]
                if abs(printed - derived) > 1:
                    checks.append([f"{name}:{area}", f"source typo? {y} {label}", False,
                                   f"summary table prints {printed:,.0f}; single-year ages give {derived:,.0f}"])
            out.append([y, area, AREA_EN[area], round(total), round(u15), round(mid), round(o65),
                        "census" if y == 2020 else "projection"])
        checks.append([f"{name}:{area}", "single-year ages sum to total, 2020–2070", True, f"{len(years)} years"])
    # wards vs city: separate projections, so report the gap instead of failing
    by = defaultdict(dict)
    for y, a, *_rest in out:
        by[y][a] = _rest[1]
    for y in sorted(by):
        gap = by[y]["仙台市"] - sum(by[y][w] for w in WARDS)
        checks.append(["projection", f"{y}: city − sum of wards", abs(gap) <= 1, f"{gap:,.0f}"])
    return out, checks


def write(name: str, header: list[str], data: list[list]) -> None:
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(data)


def main() -> int:
    try:
        pop_rows, vit_rows, c1 = monthly()
        c1 += annual_check(vit_rows)
        groups, age3_rows, c2 = age5()
        proj, c3 = projection()
    except (CheckError, FileNotFoundError, KeyError) as e:
        print(f"POPULATION EXTRACTION FAILED: {e}", file=sys.stderr)
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    write("pop_monthly.csv", ["date", "area_jp", "area_en", "population", "men", "women", "households"], pop_rows)
    write("vitals_monthly.csv", ["month", "area_jp", "area_en", "births", "deaths"], vit_rows)
    write("age_groups.csv", ["date", "area_jp", "area_en", "age_group", "population"], groups)
    write("age3.csv", ["date", "area_jp", "area_en", "total", "age_0_14", "age_15_64", "age_65_plus"], age3_rows)
    write("projection.csv", ["year", "area_jp", "area_en", "total", "age_0_14", "age_15_64", "age_65_plus", "kind"], proj)
    write("checks.csv", ["file", "check", "passed", "detail"], c1 + c2 + c3)
    skipped = [c for c in c1 if c[2] is False]  # source typos and unread blocks, reported not hidden
    months = sorted({r[0] for r in pop_rows})
    print(f"ok: population {months[0]}…{months[-1]} ({len(months)} months); "
          f"births/deaths for {len({r[0] for r in vit_rows})} months; "
          f"age data {len({r[0] for r in age3_rows})} dates; projection {len({r[0] for r in proj})} years")
    for s in skipped:
        print(f"NOTE {s[0]}: {s[3]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
