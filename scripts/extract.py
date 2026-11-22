"""Extract tables from the City of Sendai 観光統計 PDFs into tidy CSVs.

Reads every data/raw/*.pdf, parses sections 1-3 (visitors, overnight stays,
foreign overnight guests by country, domestic origin shares), checks the
numbers, and writes data/processed/*.csv.

Checks (any failure -> non-zero exit, nothing written):
  * district stays add up to the published 計
  * countries add up to the published 総計
  * the country 総計 equals the foreign-guest total in the same report
  * origin shares add up to 100% (±0.3, the reports round to 0.1)
  * every header year parses and matches the report year

Also compares each printed 前年比 with the ratio of the printed counts and logs
any mismatch to data/processed/quality_flags.csv (a typo in the source, reported, not fixed).

When two reports give different values for the same year (later revisions),
the newest report wins and every difference is written to
data/processed/revisions.csv and printed. Revisions are expected; hiding them is not.
"""
from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"

FW = str.maketrans("０１２３４５６７８９", "0123456789")
ERA_BASE = {"平成": 1988, "令和": 2018}

# report file label -> calendar year the report ends on
REPORT_YEAR = {"H23": 2011, "H24": 2012, "H25": 2013, "H26": 2014, "H27": 2015, "H28": 2016, "H29": 2017,
               "H30": 2018, "R1": 2019, "R2": 2020, "R3": 2021, "R4": 2022, "R5": 2023, "R6": 2024, "R7": 2025}

DISTRICTS = ["旧仙台地区", "泉地区", "秋保地区", "宮城地区"]
DISTRICT_EN = {"旧仙台地区": "Central Sendai", "泉地区": "Izumi", "秋保地区": "Akiu", "宮城地区": "Miyagi (Sakunami)"}

COUNTRIES = [  # (label as printed, English)
    ("中国（台湾・香港除く）", "China (excl. Taiwan, HK)"),
    ("台湾", "Taiwan"),
    ("香港", "Hong Kong"),
    ("大韓民国", "South Korea"),
    ("タイ", "Thailand"),
    ("シンガポール", "Singapore"),
    ("その他アジア", "Other Asia"),
    ("アメリカ合衆国", "United States"),
    ("カナダ", "Canada"),
    ("その他中南米", "Other Americas"),
    ("ヨーロッパ", "Europe"),
    ("オーストラリア・ニュージーランド等", "Australia / NZ etc."),
    ("その他・不明", "Other / unknown"),
]

ORIGINS = [  # column order in the 居住地別 table
    ("宮城県内", "Within Miyagi"), ("北海道", "Hokkaido"), ("東北地方", "Tohoku (other)"),
    ("関東地方", "Kanto"), ("北陸・中部", "Hokuriku / Chubu"), ("近畿", "Kinki"),
    ("中国・四国", "Chugoku / Shikoku"), ("九州・沖縄", "Kyushu / Okinawa"), ("外国人", "Overseas"),
]


class ExtractionError(Exception):
    pass


def num(tok: str) -> float | None:
    tok = tok.replace(",", "").replace("%", "").translate(FW)
    if tok in ("更新予定", "-", "－", ""):
        return None
    try:
        return float(tok)
    except ValueError:
        return None


def era_year(era: str, n: str) -> int:
    n = n.translate(FW)
    return ERA_BASE[era] + (1 if n == "元" else int(n))


def years_inline(line: str) -> list[int]:
    """'令和２年 令和３年 …' or '平成２６年 …' -> [2020, 2021, …]"""
    return [era_year(e, n) for e, n in re.findall(r"(平成|令和)([０-９0-9]+|元)年", line)]


def years_split(era_line: str, year_line: str) -> list[int]:
    """Country table header split over two lines: '平成 平成 … 令和' / '26年 27年 … 元年'."""
    eras = re.findall(r"平成|令和", era_line)
    nums = re.findall(r"([０-９0-9]+|元)年", year_line)
    if len(eras) != len(nums) or not eras:
        raise ExtractionError(f"cannot pair country-table header: {era_line!r} / {year_line!r}")
    return [era_year(e, n) for e, n in zip(eras, nums)]


def numbers(line: str) -> list[float | None]:
    return [num(t) for t in line.split() if re.fullmatch(r"[\d,.%０-９]+|更新予定", t)]


@dataclass
class Report:
    label: str
    year: int
    visitors: dict[int, float] = field(default_factory=dict)
    stays: dict[tuple[int, str], float] = field(default_factory=dict)
    foreign_total: dict[int, float] = field(default_factory=dict)
    countries: dict[tuple[int, str], float] = field(default_factory=dict)
    country_total: dict[int, float] = field(default_factory=dict)
    origins: dict[tuple[int, str], float] = field(default_factory=dict)
    yoy: dict[tuple[str, int], float] = field(default_factory=dict)  # published 前年比 (%)


def section(lines: list[str], start: str, end: str) -> list[str]:
    try:
        i = next(k for k, l in enumerate(lines) if l.startswith(start))
        j = next(k for k, l in enumerate(lines) if k > i and l.startswith(end))
    except StopIteration:
        raise ExtractionError(f"section {start!r}…{end!r} not found")
    return lines[i:j]


def parse(path: Path) -> Report:
    label = path.stem
    if label not in REPORT_YEAR:
        raise ExtractionError(f"{path.name}: unknown report label (expected one of {list(REPORT_YEAR)})")
    rep = Report(label, REPORT_YEAR[label])
    with pdfplumber.open(path) as pdf:
        lines = [l.strip() for l in pdf.pages[0].extract_text(x_tolerance=1.5).splitlines()]

    # 1. visitors
    s1 = section(lines, "１．", "２．")
    yrs = next((y for l in s1 if (y := years_inline(l))), None)
    # city total is labelled 全市 (2014+) or 計 under district rows (2011–2013 editions)
    row = next((l for l in s1 if l.split()[0] in ("全市", "計")), None)
    if not yrs or row is None:
        raise ExtractionError(f"{label}: visitors table not parsed")
    allv = numbers(row)
    for y, v, r in zip(yrs, allv[0::2], allv[1::2]):
        if v is not None:
            rep.visitors[y] = v
        if r is not None:
            rep.yoy[("visitors", y)] = r

    # 2. overnight stays by district + origin shares
    s2 = section(lines, "２．", "３．")
    yrs = next((y for l in s2 if (y := years_inline(l))), None)
    # The 2014 and 2015 editions print only a city total (全市), no districts.
    # Either all four districts are present or none; a partial set fails.
    rows = {d: next((l for l in s2 if l.split()[0] == d), None) for d in DISTRICTS}
    found = [d for d, r in rows.items() if r is not None]
    if found and len(found) != len(DISTRICTS):
        raise ExtractionError(f"{label}: only some district rows found: {found}")
    total = next((l for l in s2 if l.split()[0] in ("計", "全市")), None)
    if not yrs or total is None:
        raise ExtractionError(f"{label}: stays total row missing")
    rows["計"] = total
    for d, row in rows.items():
        if row is None:
            continue
        allv = numbers(row)
        for y, v, r in zip(yrs, allv[0::2], allv[1::2]):
            if v is not None:
                rep.stays[(y, d)] = v
            if r is not None:
                rep.yoy[("overnight_stays" if d == "計" else f"stays:{d}", y)] = r
    for l in s2:
        m = re.match(r"^([０-９0-9]+|元)年\s", l)
        if m:
            # rows print only the era number ("３０年", "元年", "５年"). 令和 is still
            # single digits, so anything >= 20 is 平成.
            n = m.group(1).translate(FW)
            era = "平成" if n != "元" and int(n) >= 20 else "令和"
            y = era_year(era, m.group(1))
            if not rep.year - 1 <= y <= rep.year:
                raise ExtractionError(f"{label}: origin row year {y} outside {rep.year - 1}–{rep.year}")
            vals = numbers(l[m.end():])
            if len(vals) != len(ORIGINS) + 1:
                raise ExtractionError(f"{label}: origin row {l!r} has {len(vals)} numbers")
            for (jp, _), v in zip(ORIGINS, vals):
                rep.origins[(y, jp)] = v

    # 3. foreign guests: total + by country
    s3 = section(lines, "３．", "４．")
    yrs = next((y for l in s3 if (y := years_inline(l))), None)
    row = next((l for l in s3 if l.startswith("仙台市")), None)
    if not yrs or row is None:
        raise ExtractionError(f"{label}: foreign total not parsed")
    allv = numbers(row)
    for y, v, r in zip(yrs, allv[0::2], allv[1::2]):
        if v is not None:
            rep.foreign_total[y] = v
        if r is not None:
            rep.yoy[("foreign_stays", y)] = r
    k = next(i for i, l in enumerate(s3) if "（参考）" in l and re.search(r"平成|令和", l))
    cyrs = years_split(s3[k], next(l for l in s3[k + 1:k + 3] if "年" in l and "地域" in l))
    for l in s3:
        name = next((jp for jp, _ in COUNTRIES if l.split(" ")[0].endswith(jp) or f" {jp} " in f" {l} "), None)
        if l.startswith("総計"):
            for y, v in zip(cyrs, numbers(l)):
                rep.country_total[y] = v
        elif name:
            vals = numbers(l)[: len(cyrs)]
            for y, v in zip(cyrs, vals):
                rep.countries[(y, name)] = v

    # header sanity: last year of each table must be the report year
    for what, ys in (("visitors", yrs), ("countries", cyrs)):
        if ys[-1] != rep.year:
            raise ExtractionError(f"{label}: {what} header ends {ys[-1]}, expected {rep.year}")
    return rep


def validate(rep: Report) -> list[str]:
    errs = []
    for y in {y for y, _ in rep.stays}:
        parts = [rep.stays.get((y, d)) for d in DISTRICTS]
        total = rep.stays.get((y, "計"))
        if all(v is None for v in parts):
            continue  # edition without district rows
        if None not in parts and total is not None and abs(sum(parts) - total) > 1:
            errs.append(f"{rep.label} {y}: districts sum {sum(parts):,.0f} != 計 {total:,.0f}")
    for y, total in rep.country_total.items():
        got = [rep.countries.get((y, c)) for c, _ in COUNTRIES]
        if None in got:
            errs.append(f"{rep.label} {y}: missing country values")
        elif abs(sum(got) - total) > 1:
            errs.append(f"{rep.label} {y}: countries sum {sum(got):,.0f} != 総計 {total:,.0f}")
        if y in rep.foreign_total and abs(rep.foreign_total[y] - total) > 1:
            errs.append(f"{rep.label} {y}: 総計 {total:,.0f} != foreign total {rep.foreign_total[y]:,.0f}")
    for y in {y for y, _ in rep.origins}:
        s = sum(rep.origins[(y, o)] or 0 for o, _ in ORIGINS)
        if abs(s - 100) > 0.3:
            errs.append(f"{rep.label} {y}: origin shares sum to {s:.1f}")
    return errs


def merge(reports: list[Report], attr: str, revisions: list[dict]) -> dict:
    """Newest report wins; record every value it overrides."""
    merged: dict = {}
    source: dict = {}
    for rep in sorted(reports, key=lambda r: r.year):
        for key, v in getattr(rep, attr).items():
            if key in merged and v is not None and merged[key] is not None and abs(merged[key] - v) > 0.05:
                revisions.append({"table": attr, "key": key, "old": merged[key], "old_report": source[key],
                                  "new": v, "new_report": rep.label})
            if v is not None:
                merged[key], source[key] = v, rep.label
    return merged


def write(name: str, header: list[str], rows: list[list]) -> None:
    with open(OUT / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def main() -> int:
    pdfs = sorted(RAW.glob("*.pdf"))
    if not pdfs:
        print("no PDFs in data/raw — run scripts/download.py first", file=sys.stderr)
        return 1
    reports, errors = [], []
    for p in pdfs:
        try:
            rep = parse(p)
        except (ExtractionError, StopIteration) as e:
            errors.append(f"{p.name}: {e}")
            continue
        errors += validate(rep)
        reports.append(rep)
    if errors:
        print("EXTRACTION FAILED:\n  " + "\n  ".join(errors), file=sys.stderr)
        return 1

    revisions: list[dict] = []
    visitors = merge(reports, "visitors", revisions)
    stays = merge(reports, "stays", revisions)
    countries = merge(reports, "countries", revisions)
    origins = merge(reports, "origins", revisions)

    OUT.mkdir(parents=True, exist_ok=True)
    years = sorted({y for y, _ in stays} | set(visitors))
    write("annual.csv", ["year", "visitors", "overnight_stays", "foreign_stays"],
          [[y, visitors.get(y), stays.get((y, "計")),
            sum(countries.get((y, c), 0) for c, _ in COUNTRIES) if (y, "台湾") in countries else None]
           for y in years])
    write("stays_by_district.csv", ["year", "district_jp", "district_en", "stays"],
          [[y, d, DISTRICT_EN[d], v] for (y, d), v in sorted(stays.items()) if d != "計"])
    en = dict(COUNTRIES)
    write("foreign_by_country.csv", ["year", "country_jp", "country_en", "stays"],
          [[y, c, en[c], v] for (y, c), v in sorted(countries.items())])
    oen = dict(ORIGINS)
    write("origin_share.csv", ["year", "origin_jp", "origin_en", "share_pct"],
          [[y, o, oen[o], v] for (y, o), v in sorted(origins.items())])
    # Published 前年比 vs the ratio of the published counts. A mismatch is a typo in
    # the source, not in our data: logged and printed, never silently fixed.
    series = {"visitors": visitors,
              "overnight_stays": {y: v for (y, d), v in stays.items() if d == "計"},
              **{f"stays:{dd}": {y: v for (y, d), v in stays.items() if d == dd} for dd in DISTRICTS},
              "foreign_stays": {y: sum(countries[(y, c)] for c, _ in COUNTRIES)
                                for y in {y for y, _ in countries}}}
    flags = []
    for rep in reports:
        for (table, y), published in sorted(rep.yoy.items()):
            cur, prev = series[table].get(y), series[table].get(y - 1)
            if cur and prev:
                calc = cur / prev * 100
                if abs(calc - published) > 0.15:
                    flags.append([rep.label, table, y, published, round(calc, 1)])
    write("quality_flags.csv", ["report", "table", "year", "published_yoy_pct", "calculated_yoy_pct"], flags)

    write("revisions.csv", ["table", "key", "old", "old_report", "new", "new_report"],
          [[r["table"], r["key"], r["old"], r["old_report"], r["new"], r["new_report"]] for r in revisions])

    print(f"ok: {len(reports)} reports, years {years[0]}–{years[-1]}")
    for f in flags:
        print(f"SOURCE TYPO? {f[0]} {f[1]} {f[2]}: printed 前年比 {f[3]}%, numbers give {f[4]}%")
    for r in revisions:
        print(f"REVISED {r['table']} {r['key']}: {r['old']:,} ({r['old_report']}) -> {r['new']:,} ({r['new_report']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
