"""Sendai's five ward polygons from 国土数値情報 行政区域 (N03), shared by the extract scripts.

The file is downloaded by scripts/landprice_download.py into data/raw/boundaries/.
Credit: 出典：国土交通省「国土数値情報（行政区域データ）」, CC BY 4.0.
"""
from __future__ import annotations

import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.ops import unary_union

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "boundaries"
WARD_CODE = {"04101": "青葉区", "04102": "宮城野区", "04103": "若林区", "04104": "太白区", "04105": "泉区"}


class BoundaryError(Exception):
    pass


def load_wards() -> dict[str, object]:
    """Ward name → shapely (Multi)Polygon. Fails if a ward is missing, misnamed, or two wards overlap."""
    hits = sorted(RAW.glob("N03-*_04_GML/*.geojson"))
    if not hits:
        raise BoundaryError("no N03 file in data/raw/boundaries — run scripts/landprice_download.py first")
    geo = json.loads(hits[-1].read_text(encoding="utf-8"))
    parts: dict[str, list] = {}
    for f in geo["features"]:
        code = f["properties"].get("N03_007") or ""
        if code in WARD_CODE:
            if f["properties"].get("N03_005") != WARD_CODE[code]:
                raise BoundaryError(f"N03: code {code} is named {f['properties'].get('N03_005')}, expected {WARD_CODE[code]}")
            parts.setdefault(WARD_CODE[code], []).append(shape(f["geometry"]))
    if set(parts) != set(WARD_CODE.values()):
        raise BoundaryError(f"N03: wards found {sorted(parts)}")
    wards = {w: unary_union(p) for w, p in parts.items()}
    names = list(wards)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            overlap = wards[a].intersection(wards[b]).area
            if overlap > 1e-9:  # shared borders have zero area
                raise BoundaryError(f"N03: {a} and {b} overlap ({overlap:.2e} deg²)")
    return wards


def ward_of(wards: dict[str, object], lat: float, lon: float) -> list[str]:
    """Every ward whose polygon covers the point (normally exactly one)."""
    p = Point(lon, lat)
    return [w for w, g in wards.items() if g.covers(p)]
