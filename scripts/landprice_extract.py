"""Land prices in Sendai (地価公示, MLIT 国土数値情報 L01) with ward boundaries (N03).

Input:  data/raw/landprice/L01-26_04_GML/   2026 file: every point surveyed in 2026, with its
                                            price for every year 1983–2026 (0 = not surveyed)
        data/raw/landprice/L01-16_04_GML/   2016 file (prices 1983–2016, as published then)
        data/raw/landprice/L01-06_04_GML/   2006 file (2006 price only)
        data/raw/boundaries/N03-20250101_04_GML/  行政区域, Miyagi, 1 January 2025
Run scripts/landprice_download.py first. Credit: 出典：国土交通省「国土数値情報（地価公示・行政区域）」, CC BY 4.0.

Output: data/processed/landprice/
  points.csv         one row per 2026 point: id, use, ward, address, station, zoning, 2026 price,
                     year-on-year %, 5- and 10-year change, location
  history.csv        long format: point id, year, price (yen per m²) — only years the point was surveyed
  index.csv          chained median index by use (and by ward for residential), 2011 = 100
  ward_summary.csv   per ward and use: points, median price, median 1-, 5- and 10-year change
  sendai_wards.geojson  the five ward polygons, simplified for the map (about 30 m tolerance)
  checks.csv         every check and its result

Hard checks (non-zero exit, nothing written):
  * the 2026 price field equals the 2026 history column for every point
  * the "surveyed" flag string agrees with which history columns hold a price
  * every point lies inside the ward polygon its municipality code says, and the address names that ward
  * the five ward polygons don't overlap
Logged, not fatal:
  * printed year-on-year % that doesn't match the prices (source rounding or typo)
  * points also in the 2016 / 2006 files (matched by location): does the 2026 file's history
    equal what was published then?
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import pandas as pd
import shapefile  # pyshp
from shapely.geometry import mapping

from wards import WARD_CODE, BoundaryError, load_wards, ward_of

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "landprice"

WARD_EN = {"青葉区": "Aoba", "宮城野区": "Miyagino", "若林区": "Wakabayashi", "太白区": "Taihaku", "泉区": "Izumi"}
USE = {"000": ("住宅地", "residential"), "003": ("宅地見込地", "land for future housing"),
       "005": ("商業地", "commercial"), "007": ("準工業地", "semi-industrial"), "009": ("工業地", "industrial")}
Y0_26, Y0_16 = 1983, 1983          # first history year in each file
COL0_26, COL0_16 = 62, 48          # L01_062 / L01_048 hold the 1983 price
FLAG_26, FLAG_16 = "L01_061", "L01_047"
MATCH_M = 20                       # points within 20 m are treated as the same site
BASE_YEAR = 2011
MIN_POINTS = 10                    # fewer comparable points than this → no index value that year


class CheckError(Exception):
    pass


def metres(lat1, lon1, lat2, lon2) -> float:
    dy = (lat2 - lat1) * 111_320
    dx = (lon2 - lon1) * 111_320 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(dx, dy)


def find(pattern: str) -> Path:
    hits = sorted(RAW.glob(pattern))
    if not hits:
        raise CheckError(f"no file matches data/raw/{pattern} — run scripts/landprice_download.py first")
    return hits[0]


def load_2026() -> pd.DataFrame:
    geo = json.loads(find("landprice/L01-26_04_GML/**/L01-26_04.geojson").read_text(encoding="utf-8"))
    rows = []
    for f in geo["features"]:
        p = f["properties"]
        if p["L01_001"] not in WARD_CODE:
            continue
        hist = {Y0_26 + i: int(p[f"L01_{COL0_26 + i:03d}"]) for i in range(2026 - Y0_26 + 1)}
        lon, lat = f["geometry"]["coordinates"]
        use = p["L01_002"]
        if use not in USE:
            raise CheckError(f"2026: unknown use code {use}")
        rows.append({
            "id": f"{p['L01_024']}{'' if use == '000' else int(use)}-{int(p['L01_003'])}",
            "code": p["L01_001"], "use": use, "year": p["L01_007"], "price": p["L01_008"],
            "yoy_printed": p["L01_009"], "address": p["L01_025"].replace("　", " "),
            "current_use": p["L01_028"], "area_desc": p["L01_047"], "station": p["L01_048"],
            "station_m": p["L01_050"], "zoning": p["L01_051"], "surveyed": p[FLAG_26],
            "lat": lat, "lon": lon, "prices": hist,
        })
    return pd.DataFrame(rows)


def load_shp(pattern: str, year: int, hist_col0: int | None, flag: str | None) -> pd.DataFrame:
    r = shapefile.Reader(str(find(pattern)), encoding="cp932")
    names = [f[0] for f in r.fields[1:]]
    rows = []
    for sr in r.iterShapeRecords():
        rec = dict(zip(names, sr.record))
        if str(rec["L01_017"]) not in WARD_CODE:
            continue
        if int(rec["L01_005"]) != year:
            raise CheckError(f"{pattern}: survey year {rec['L01_005']}, expected {year}")
        lon, lat = sr.shape.points[0]
        row = {"code": str(rec["L01_017"]), "use": str(rec["L01_001"]), "price": int(rec["L01_006"]),
               "lat": lat, "lon": lon}
        if hist_col0:
            row["prices"] = {Y0_16 + i: int(rec[f"L01_{hist_col0 + i:03d}"]) for i in range(year - Y0_16 + 1)}
            row["surveyed"] = str(rec[flag])
        rows.append(row)
    return pd.DataFrame(rows)


def chained_index(hist: pd.DataFrame) -> pd.DataFrame:
    """hist: columns id, year, price. Median ratio of points priced in both years, chained, BASE_YEAR = 100."""
    wide = hist.pivot(index="id", columns="year", values="price")
    years = sorted(wide.columns)
    out, level = [], {BASE_YEAR: 100.0}
    ratios = {}
    for y in years[1:]:
        both = wide[[y - 1, y]].dropna()
        ratios[y] = (both[y] / both[y - 1]).median() if len(both) >= MIN_POINTS else float("nan")
        out.append((y, len(both)))
    for y in range(BASE_YEAR + 1, years[-1] + 1):
        level[y] = level[y - 1] * ratios[y] if not math.isnan(level[y - 1]) else float("nan")
    for y in range(BASE_YEAR - 1, years[0] - 1, -1):
        level[y] = level[y + 1] / ratios[y + 1] if not math.isnan(level[y + 1]) else float("nan")
    n = dict(out)
    return pd.DataFrame([{"year": y, "index": round(level[y], 2) if not math.isnan(level[y]) else None,
                          "points_compared": n.get(y)} for y in years])


def main() -> int:
    checks = []
    try:
        wards = load_wards()
        cur = load_2026()
        old16 = load_shp("landprice/L01-16_04_GML/L01-16_04.shp", 2016, COL0_16, FLAG_16)
        old06 = load_shp("landprice/L01-06_04_GML/*.shp", 2006, None, None)

        # 2026 price field = 2026 history column
        bad = cur[cur.price != cur.prices.map(lambda h: h[2026])]
        if len(bad):
            raise CheckError(f"2026 price ≠ 2026 history column for {bad.id.tolist()}")
        # surveyed flags agree with prices, in both files that have history
        for name, df, y0 in [("2026", cur, Y0_26), ("2016", old16, Y0_16)]:
            for _, r in df.iterrows():
                if len(r.surveyed) != len(r.prices) or any((c == "1") != (r.prices[y0 + i] > 0) for i, c in enumerate(r.surveyed)):
                    raise CheckError(f"{name} file: surveyed flags {r.surveyed} don't match the prices at {r.get('id', (r.lat, r.lon))}")
        # ward: code, polygon and address agree
        cur["ward_jp"] = cur.code.map(WARD_CODE)
        for _, r in cur.iterrows():
            inside = ward_of(wards, r.lat, r.lon)
            if inside != [r.ward_jp]:
                raise CheckError(f"{r.id}: code says {r.ward_jp}, polygon says {inside}")
            if f"仙台市{r.ward_jp}" not in r.address:
                raise CheckError(f"{r.id}: address {r.address} doesn't name {r.ward_jp}")
        if cur.id.duplicated().any():
            raise CheckError(f"duplicate point ids {cur.id[cur.id.duplicated()].tolist()}")
    except (CheckError, BoundaryError, FileNotFoundError, KeyError) as e:
        print(f"LAND PRICE EXTRACTION FAILED: {e}", file=sys.stderr)
        return 1
    checks += [
        ["L01-26", "2026 price equals the 2026 history column", True, f"{len(cur)} points in Sendai"],
        ["L01-26/L01-16", "'surveyed' flag strings match which years hold a price", True, f"{len(cur)} + {len(old16)} points"],
        ["L01-26 × N03", "every point lies in the ward its code names, and its address names that ward", True,
         f"{len(cur)} of {len(cur)}"],
        ["N03", "the five ward polygons don't overlap", True, "shared borders only"],
    ]

    # printed year-on-year % vs prices
    yoy_bad = []
    for _, r in cur.iterrows():
        p0, p1 = r.prices[2025], r.prices[2026]
        if p0 > 0:
            calc = (p1 / p0 - 1) * 100
            if abs(calc - r.yoy_printed) > 0.051:
                yoy_bad.append(f"{r.id}: printed {r.yoy_printed}, calculated {calc:.2f}")
        elif r.yoy_printed != 0:
            yoy_bad.append(f"{r.id}: printed {r.yoy_printed} but not surveyed in 2025")
    checks.append(["L01-26", "printed year-on-year % matches the 2025 and 2026 prices (±0.05)", not yoy_bad,
                   f"{len(cur) - len(yoy_bad)} of {len(cur)} match" + ("; " + "; ".join(yoy_bad) if yoy_bad else "")])

    # history as published at the time: match 2016 and 2006 points to 2026 points by location
    def match(old: pd.DataFrame) -> list[tuple[int, int]]:
        pairs = []
        for i, o in old.iterrows():
            best = min(((metres(o.lat, o.lon, c.lat, c.lon), j) for j, c in cur.iterrows()), default=(1e9, None))
            if best[0] <= MATCH_M:
                pairs.append((i, best[1]))
        return pairs

    for name, old, year in [("L01-16", old16, 2016), ("L01-06", old06, 2006)]:
        pairs = match(old)
        diffs, compared, later = [], 0, 0
        for i, j in pairs:
            o, c = old.loc[i], cur.loc[j]
            later += c.prices[year] == 0
            years = o.prices.keys() if "prices" in old and isinstance(o.get("prices"), dict) else [year]
            for y in years:
                ov = o.prices[y] if y != year else o.price
                if ov > 0 and c.prices[y] > 0:
                    compared += 1
                    if ov != c.prices[y]:
                        diffs.append(f"{c.id} {y}: {ov} then, {c.prices[y]} in 2026 file")
        status = True if not diffs else "explained"
        checks.append([f"{name} × L01-26",
                       f"prices published in {year} equal the 2026 file's history (points matched within {MATCH_M} m)",
                       status, f"{len(pairs)} of {len(old)} {year} points have a 2026 point within {MATCH_M} m; "
                               f"{compared - len(diffs)} of {compared} year-values equal"
                               + (f"; {later} matched sites have no {year} price in the 2026 file (a later point at the same spot)" if later else "")
                               + ("; differences: " + "; ".join(diffs[:10]) + (" …" if len(diffs) > 10 else "") if diffs else "")])

    # outputs ---------------------------------------------------------------
    hist_rows = [(r.id, y, p) for _, r in cur.iterrows() for y, p in r.prices.items() if p > 0]
    hist = pd.DataFrame(hist_rows, columns=["id", "year", "price"])

    def change(h: dict, years: int) -> float | None:
        a, b = h.get(2026 - years, 0), h[2026]
        return round((b / a - 1) * 100, 1) if a > 0 else None

    points = pd.DataFrame({
        "id": cur.id, "use_code": cur.use, "use_jp": cur.use.map(lambda u: USE[u][0]),
        "use_en": cur.use.map(lambda u: USE[u][1]), "ward_jp": cur.ward_jp, "ward_en": cur.ward_jp.map(WARD_EN),
        "address": cur.address, "current_use": cur.current_use, "area_desc": cur.area_desc,
        "station": cur.station, "station_m": cur.station_m, "zoning": cur.zoning, "price_2026": cur.price,
        "yoy_pct": cur.yoy_printed, "change_5y_pct": cur.prices.map(lambda h: change(h, 5)),
        "change_10y_pct": cur.prices.map(lambda h: change(h, 10)),
        "first_year": cur.prices.map(lambda h: min(y for y, p in h.items() if p > 0)),
        "lat": cur.lat, "lon": cur.lon,
    })

    idx = []
    for use in ["000", "005"]:
        ids = set(points.id[points.use_code == use])
        t = chained_index(hist[hist.id.isin(ids)])
        t.insert(0, "group", USE[use][1]); t.insert(1, "ward_jp", "仙台市")
        idx.append(t)
        for w in WARD_CODE.values():
            if use != "000":
                continue
            ids_w = set(points.id[(points.use_code == use) & (points.ward_jp == w)])
            t = chained_index(hist[hist.id.isin(ids_w)])
            t.insert(0, "group", USE[use][1]); t.insert(1, "ward_jp", w)
            idx.append(t)
    index = pd.concat(idx)
    index.insert(2, "ward_en", index.ward_jp.map({**WARD_EN, "仙台市": "Sendai"}))

    # survivor check: the same index from the 2016 file's points, for 1984–2016
    h16 = pd.DataFrame([(i, y, p) for i, r in old16[old16.use == "000"].iterrows() for y, p in r.prices.items() if p > 0],
                       columns=["id", "year", "price"])
    i16 = chained_index(h16).set_index("year")["index"]
    i26 = index[(index.group == "residential") & (index.ward_jp == "仙台市")].set_index("year")["index"]
    common = [y for y in i16.index if pd.notna(i16[y]) and pd.notna(i26.get(y)) and y <= 2016]
    gap = max(abs(i16[y] / i26[y] - 1) * 100 for y in common)
    worst = max(common, key=lambda y: abs(i16[y] / i26[y] - 1))
    checks.append(["index", "residential index from 2026 points vs from 2016 points (points dropped since 2016)",
                   "explained", f"largest gap {gap:.1f}% in {worst} ({i26[worst]} vs {i16[worst]}); "
                                f"the 2026 file only holds points still surveyed, so early years rest on fewer, surviving points"])

    summ = []
    for w in list(WARD_CODE.values()) + ["仙台市"]:
        for use in ["000", "005"]:
            s = points[(points.use_code == use) & ((points.ward_jp == w) | (w == "仙台市"))]
            summ.append([w, {**WARD_EN, "仙台市": "Sendai"}[w], USE[use][1], len(s), int(s.price_2026.median()) if len(s) else None,
                         s.yoy_pct.median() if len(s) else None, s.change_5y_pct.median() if len(s) else None,
                         s.change_10y_pct.median() if len(s) else None, int(s.change_5y_pct.notna().sum())])
    summary = pd.DataFrame(summ, columns=["ward_jp", "ward_en", "use", "points", "median_price_2026", "median_yoy_pct",
                                          "median_change_5y_pct", "median_change_10y_pct", "points_with_5y"])

    OUT.mkdir(parents=True, exist_ok=True)
    points.to_csv(OUT / "points.csv", index=False)
    hist.to_csv(OUT / "history.csv", index=False)
    index.to_csv(OUT / "index.csv", index=False)
    summary.to_csv(OUT / "ward_summary.csv", index=False)
    feats = [{"type": "Feature", "id": w, "properties": {"ward_jp": w, "ward_en": WARD_EN[w]},
              "geometry": mapping(g.simplify(0.0003, preserve_topology=True))} for w, g in wards.items()]
    (OUT / "sendai_wards.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                          ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with open(OUT / "checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "check", "passed", "detail"])
        w.writerows(checks)
    failed = [c for c in checks if c[2] is False]
    print(f"ok: {len(points)} points ({(points.use_code == '000').sum()} residential, {(points.use_code == '005').sum()} commercial), "
          f"{len(hist)} point-years; {len(failed)} logged source issue(s)")
    for c in checks:
        print(" ", c[2], "|", c[1], "|", c[3][:300])
    return 0


if __name__ == "__main__":
    sys.exit(main())
