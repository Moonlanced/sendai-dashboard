"""Ward outlines shared by the map pages (from scripts/landprice_extract.py, N03 boundaries)."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

WARDS = Path(__file__).resolve().parent.parent / "data" / "processed" / "landprice" / "sendai_wards.geojson"


@st.cache_data
def wards_geojson() -> dict | None:
    return json.loads(WARDS.read_text(encoding="utf-8")) if WARDS.exists() else None


def add_ward_outlines(fig, color: str = "#3d4a44") -> None:
    """Draw the five ward borders under the markers of a plotly map figure (no-op if the file is missing)."""
    geo = wards_geojson()
    if geo:
        fig.update_layout(map_layers=[{"source": geo, "type": "line", "color": color, "line": {"width": 1.5},
                                       "below": "traces"}])
