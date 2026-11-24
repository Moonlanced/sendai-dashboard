"""Evacuation sites in Sendai, from the GSI evacuation-site database (国土地理院
「指定緊急避難場所・指定避難所データ」), joined with ward populations.

Input:  data/raw/disaster/04100_1.csv/.geojson  指定避難所 (shelters), Sendai
        data/raw/disaster/04100_2.csv/.geojson  指定緊急避難場所 (emergency evacuation sites, per hazard), Sendai
        data/processed/population/pop_monthly.csv  (run scripts/population_extract.py first)
The files are downloaded by hand from https://hinanmap.gsi.go.jp/ after agreeing to the
terms there (see data/raw/disaster/GSI_TERMS.txt). Credit: 出典：国土地理院.

Output: data/processed/disaster/
  sites.csv          one row per site: kind, ward, hazards it is designated for, location, notes
  ward_summary.csv   per ward: population, shelters, sites per hazard, per 10,000 residents
  checks.csv         every check and its result

Hard checks (non-zero exit, nothing written):
  * CSV and GeoJSON hold the same IDs (each file cross-checks the other)
  * no duplicate IDs; hazard flags are 1 or empty
  * every coordinate lies inside a box around Sendai
  * every emergency site flagged "same address as a shelter" has that address in the shelter list
  * every site whose address names a ward lies inside that ward's polygon (N03 boundaries)
Sites whose address names no ward (tsunami stairs on the 仙台東部道路) get their ward from the
boundary polygons; ward_source says which ("address" or "boundary").
Needs data/raw/boundaries (scripts/landprice_download.py).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

import pandas as pd

from wards import BoundaryError, load_wards, ward_of

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "disaster"
POP = ROOT / "data" / "processed" / "population" / "pop_monthly.csv"
OUT = ROOT / "data" / "processed" / "disaster"

WARDS = ["青葉区", "宮城野区", "若林区", "太白区", "泉区"]
WARD_EN = {"青葉区": "Aoba", "宮城野区": "Miyagino", "若林区": "Wakabayashi", "太白区": "Taihaku", "泉区": "Izumi"}
HAZARDS = {"洪水": "flood", "崖崩れ、土石流及び地滑り": "landslide", "高潮": "storm_surge", "地震": "earthquake",
           "津波": "tsunami", "大規模な火事": "large_fire", "内水氾濫": "inland_flood", "火山現象": "volcano"}
BOX = (38.10, 38.50, 140.25, 141.10)  # lat min, lat max, lon min, lon max around Sendai


class CheckError(Exception):
    pass


def load(stem: str, wards: dict) -> pd.DataFrame:
    df = pd.read_csv(RAW / f"{stem}.csv", encoding="utf-8-sig", dtype=str).fillna("")
    geo = json.loads((RAW / f"{stem}.geojson").read_text(encoding="utf-8"))
    ids_csv, ids_geo = set(df["共通ID"]), {f["properties"]["共通ID"] for f in geo["features"]}
    if ids_csv != ids_geo:
        raise CheckError(f"{stem}: CSV and GeoJSON differ: {len(ids_csv - ids_geo)} only in CSV, {len(ids_geo - ids_csv)} only in GeoJSON")
    if df["共通ID"].duplicated().any():
        raise CheckError(f"{stem}: duplicate IDs {df.loc[df['共通ID'].duplicated(), '共通ID'].tolist()}")
    lat, lon = df["緯度"].astype(float), df["経度"].astype(float)
    outside = df[~lat.between(BOX[0], BOX[1]) | ~lon.between(BOX[2], BOX[3])]
    if len(outside):
        raise CheckError(f"{stem}: {len(outside)} sites outside Sendai: {outside['施設・場所名'].tolist()}")
    df["ward"] = df["住所"].str.extract(r"仙台市(青葉区|宮城野区|若林区|太白区|泉区)")[0]
    poly = [ward_of(wards, float(a), float(o)) for a, o in zip(df["緯度"], df["経度"])]
    if any(len(p) != 1 for p in poly):
        raise CheckError(f"{stem}: sites in no ward or two wards: {[n for n, p in zip(df['施設・場所名'], poly) if len(p) != 1]}")
    poly = [p[0] for p in poly]
    clash = [n for n, a, p in zip(df["施設・場所名"], df["ward"], poly) if pd.notna(a) and a != p]
    if clash:
        raise CheckError(f"{stem}: address ward differs from the boundary polygon for {clash}")
    df["ward_source"] = ["address" if pd.notna(a) else "boundary" for a in df["ward"]]
    df["ward"] = poly
    return df


def main() -> int:
    checks = []
    try:
        wards = load_wards()
        shelters = load("04100_1", wards)
        sites = load("04100_2", wards)
        bad = {h: sorted(set(sites[h]) - {"", "1"}) for h in HAZARDS if set(sites[h]) - {"", "1"}}
        if bad:
            raise CheckError(f"hazard flags other than 1/empty: {bad}")
        same = sites[sites["指定避難所との住所同一"] == "1"]
        missing = same[~same["住所"].isin(shelters["住所"])]
        if len(missing):
            raise CheckError(f"{len(missing)} sites flagged as a shelter's address but not in the shelter list: {missing['施設・場所名'].tolist()}")
        if not POP.exists():
            raise CheckError(f"{POP} missing — run scripts/population_extract.py first")
    except (CheckError, BoundaryError, FileNotFoundError, KeyError) as e:
        print(f"DISASTER EXTRACTION FAILED: {e}", file=sys.stderr)
        return 1
    checks += [
        ["04100_1", "CSV and GeoJSON hold the same IDs; no duplicates; all inside Sendai", True, f"{len(shelters)} shelters"],
        ["04100_2", "CSV and GeoJSON hold the same IDs; no duplicates; all inside Sendai", True, f"{len(sites)} sites"],
        ["04100_2", "sites flagged 'same address as a shelter' are in the shelter list", True, f"{len(same)} of {len(same)}"],
    ]
    checks.append(["04100_1/2 × N03", "every site whose address names a ward lies inside that ward's boundary", True,
                   f"{(shelters.ward_source == 'address').sum() + (sites.ward_source == 'address').sum()} sites"])
    unassigned = pd.concat([shelters, sites])
    unassigned = unassigned[unassigned.ward_source == "boundary"]
    checks.append(["04100_2", "sites with no ward in the address: ward taken from the boundary polygons", "explained",
                   f"{len(unassigned)}: " + ", ".join(f"{n} → {w}" for n, w in zip(unassigned["施設・場所名"], unassigned.ward))
                   + " — tsunami stairs on the 仙台東部道路"])

    # one table of all sites
    shelters["welfare"] = shelters["受入対象者"] != ""
    rows = []
    for _, r in shelters.iterrows():
        rows.append(["shelter_welfare" if r.welfare else "shelter", r["共通ID"], r["施設・場所名"], r["住所"], r.ward,
                     WARD_EN[r.ward], r.ward_source, float(r["緯度"]), float(r["経度"]), *[""] * len(HAZARDS),
                     (r["受入対象者"] + " " + r["その他市町村長が必要と認める事項"]).strip()])
    for _, r in sites.iterrows():
        rows.append(["emergency_site", r["共通ID"], r["施設・場所名"], r["住所"], r.ward, WARD_EN[r.ward], r.ward_source,
                     float(r["緯度"]), float(r["経度"]), *[1 if r[h] == "1" else 0 for h in HAZARDS],
                     r["備考"].replace("\n", " / ")])

    # ward population: latest October 1 推計人口
    pop = pd.read_csv(POP)
    latest_oct = max(d for d in pop.date if d.endswith("-10-01"))
    popw = pop[pop.date == latest_oct].set_index("area_jp")["population"]
    summary = []
    for w in WARDS:
        s_w, e_w = shelters[shelters.ward == w], sites[sites.ward == w]
        p = popw.get(w)
        line = [w, WARD_EN[w], int(p) if p else None, int((~s_w.welfare).sum()), int(s_w.welfare.sum()), len(e_w)]
        line += [int((e_w[h] == "1").sum()) for h in HAZARDS]
        line += [round((~s_w.welfare).sum() / p * 10000, 2) if p else None,
                 round(len(e_w) / p * 10000, 2) if p else None]
        summary.append(line)
    tot_shel = sum(r[3] for r in summary) + sum(r[4] for r in summary)
    if tot_shel != len(shelters) or sum(r[5] for r in summary) != len(sites):
        print("DISASTER EXTRACTION FAILED: ward totals don't add up to the number of sites", file=sys.stderr)
        return 1
    checks.append(["ward_summary", "ward counts add up to all shelters and all sites", True,
                   f"{tot_shel} shelters, {len(sites)} sites; population as of {latest_oct}"])

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "sites.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["kind", "id", "name", "address", "ward_jp", "ward_en", "ward_source", "lat", "lon", *HAZARDS.values(), "notes"])
        w.writerows(rows)
    with open(OUT / "ward_summary.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["ward_jp", "ward_en", "population", "shelters", "welfare_shelters", "emergency_sites",
                    *[f"sites_{v}" for v in HAZARDS.values()], "shelters_per_10k", "sites_per_10k"])
        w.writerows(summary)
    with open(OUT / "checks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["source", "check", "passed", "detail"])
        w.writerows(checks)
    print(f"ok: {len(shelters)} shelters ({int(shelters.welfare.sum())} welfare), {len(sites)} emergency sites; "
          f"{len(unassigned)} sites placed in a ward by boundary; population as of {latest_oct}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
