"""Disaster-preparedness page of the Sendai city dashboard.

Data: data/processed/disaster/*.csv, produced by scripts/disaster_extract.py from the
国土地理院 「指定緊急避難場所・指定避難所データ」 (出典：国土地理院) and the population pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data" / "processed" / "disaster"
ACCENT, MUTED, WARN, BLUE = "#1f6f5c", "#9aa6a0", "#b4651e", "#3b6ea5"
HAZ = {  # column -> (ja, en)
    "flood": ("洪水", "Flood"), "landslide": ("崖崩れ・土石流・地滑り", "Landslide"),
    "earthquake": ("地震", "Earthquake"), "tsunami": ("津波", "Tsunami"),
    "large_fire": ("大規模な火事", "Large fire"), "inland_flood": ("内水氾濫", "Inland flooding"),
    "storm_surge": ("高潮", "Storm surge"), "volcano": ("火山現象", "Volcano"),
}
KIND = {
    "shelter": ("指定避難所", "Shelter"),
    "shelter_welfare": ("指定避難所（福祉）", "Welfare shelter"),
    "emergency_site": ("指定緊急避難場所", "Emergency evacuation site"),
}

T = {
    "title": {"ja": "防災：避難場所と避難所", "en": "Disaster preparedness: evacuation sites and shelters"},
    "sub": {
        "ja": "災害の種類ごとに、どこへ避難できるか。各区の人口あたりの数と、津波に対応した場所の分布",
        "en": "Where people can go, for each kind of disaster: sites per resident in each ward, and where tsunami sites are",
    },
    "notice": {
        "ja": "**ご利用上の注意（国土地理院データ）**\n"
              "1. 本データは、災害対策基本法に基づき市町村長が指定した避難場所・避難所を市町村が登録したものです。最新でない場合や未掲載の場合があるため、最新の状況は必ず**仙台市**にご確認ください。\n"
              "2. **指定緊急避難場所**は、命を守るために緊急的に避難する場所で、**災害の種類ごとに指定**されています。**指定避難所**は、避難した人が一定期間滞在する施設です。\n"
              "3. 本データは随時更新されます。\n\n"
              "実際の避難には、[仙台市の避難所情報](https://www.city.sendai.jp/kurashi/anzen/saigaitaisaku/hinanjo/index.html) を確認してください。このページはデータ分析のための参考です。",
        "en": "**About this data (GSI)**\n"
              "1. These are the sites the city has designated under the Disaster Countermeasures Basic Act and registered with GSI. They may be out of date or incomplete: always check with the **City of Sendai** for the current situation.\n"
              "2. **Emergency evacuation sites** (指定緊急避難場所) are places to escape to immediately, and are **designated per disaster type**. **Shelters** (指定避難所) are where evacuees stay for a period.\n"
              "3. The data is updated from time to time.\n\n"
              "In a real emergency, use the [City of Sendai's evacuation information](https://www.city.sendai.jp/kurashi/anzen/saigaitaisaku/hinanjo/index.html). This page is a data analysis, for reference only.",
    },
    "k_shel": {"ja": "指定避難所", "en": "Shelters"},
    "k_site": {"ja": "指定緊急避難場所", "en": "Emergency sites"},
    "k_tsu": {"ja": "津波に対応", "en": "Tsunami-designated"},
    "k_per": {"ja": "避難所（人口1万人あたり）", "en": "Shelters per 10,000 people"},
    "welfare_note": {"ja": "うち福祉 {n}", "en": "incl. {n} welfare"},
    "upper": {"ja": "うち{n}か所は上階・屋上へ", "en": "{n} need upper floors / roof"},
    "q1": {"ja": "① 地図：災害の種類で絞り込み", "en": "① Map: filter by disaster type"},
    "all": {"ja": "すべて", "en": "All"},
    "shelters_only": {"ja": "指定避難所のみ", "en": "Shelters only"},
    "q1_note": {
        "ja": "点にカーソルを合わせると名称・住所・備考（「2階以上」など）を表示。",
        "en": "Hover a point for its name, address and notes (e.g. 'upper floors only').",
    },
    "q2": {"ja": "② 区ごとの比較（人口1万人あたり）", "en": "② Wards compared (per 10,000 residents)"},
    "per_shel": {"ja": "指定避難所", "en": "Shelters"},
    "per_site": {"ja": "指定緊急避難場所", "en": "Emergency sites"},
    "q2_note": {
        "ja": "人口あたりの避難所数は泉区が最も多く（2.30）、若林区が最も少ない（1.40）。収容人数はデータに含まれないため、数のみの比較です。",
        "en": "Izumi has the most shelters per resident (2.30 per 10,000) and Wakabayashi the fewest (1.40). Capacity isn't in the data, so this compares counts only.",
    },
    "q3": {"ja": "③ 災害の種類 × 区", "en": "③ Disaster type × ward"},
    "q3_note": {
        "ja": "津波に対応した場所は宮城野区（51）と若林区（21）に集中。62か所は上階・屋上への避難（垂直避難）。高潮・火山に指定された場所はなく、大規模な火事は8か所のみ。",
        "en": "Tsunami sites are concentrated in Miyagino (51) and Wakabayashi (21); 62 of them mean going to upper floors or a roof (vertical evacuation). No site is designated for storm surge or volcanoes, and only 8 for large fires.",
    },
    "q4": {"ja": "④ 津波避難場所の種類", "en": "④ What the tsunami sites are"},
    "data": {"ja": "データと注意点", "en": "Data and caveats"},
}

TSUNAMI_TYPES = [  # (pattern in the name, ja, en)
    ("タワー", "津波避難タワー", "Tsunami tower"), ("避難の丘", "避難の丘", "Evacuation hill"),
    ("避難ビル", "津波避難ビル", "Evacuation building"), ("避難階段", "避難階段（東部道路）", "Expressway stairs"),
    ("小学校|中学校|高校|高等学校", "学校", "School"), ("住宅|団地|マンション", "集合住宅", "Housing block"),
]


def t(key: str, **kw) -> str:
    return T[key][st.session_state.get("lang", "ja")].format(**kw)


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    sites = pd.read_csv(DATA / "sites.csv")
    sites["notes"] = sites["notes"].fillna("")
    return {"sites": sites, "wards": pd.read_csv(DATA / "ward_summary.csv")}


def render() -> None:
    en = st.session_state.get("lang", "ja") == "en"
    li = 1 if en else 0
    d = load()
    s, w = d["sites"], d["wards"]
    shel, emerg = s[s.kind.str.startswith("shelter")], s[s.kind == "emergency_site"]
    tsu = emerg[emerg.tsunami == 1]
    upper = tsu.notes.str.contains("階以上|屋上|廊下").sum()

    st.title(t("title"))
    st.caption(t("sub"))
    st.warning(t("notice"))

    pop = w.population.sum()
    c = st.columns(4)
    c[0].metric(t("k_shel"), f"{len(shel)}", t("welfare_note", n=(shel.kind == "shelter_welfare").sum()), delta_color="off")
    c[1].metric(t("k_site"), f"{len(emerg)}")
    c[2].metric(t("k_tsu"), f"{len(tsu)}", t("upper", n=upper), delta_color="off")
    c[3].metric(t("k_per"), f"{(shel.kind == 'shelter').sum() / pop * 10000:.2f}")

    # ① map
    st.subheader(t("q1"))
    options = ["all", "shelters"] + [h for h in HAZ if emerg[h].sum() > 0]
    labels = {"all": t("all"), "shelters": t("shelters_only"), **{h: HAZ[h][li] for h in HAZ}}
    pick = st.radio(" ", options, format_func=lambda o: labels[o], horizontal=True, label_visibility="collapsed")
    if pick == "all":
        m = s
    elif pick == "shelters":
        m = shel
    else:
        m = emerg[emerg[pick] == 1]
    m = m.assign(kind_label=m.kind.map(lambda k: KIND[k][li]), ward=m["ward_en" if en else "ward_jp"])
    fig = px.scatter_map(m, lat="lat", lon="lon", color="kind_label", hover_name="name",
                         hover_data={"address": True, "ward": True, "notes": True, "lat": False, "lon": False, "kind_label": False},
                         color_discrete_map={KIND["shelter"][li]: BLUE, KIND["shelter_welfare"][li]: "#8a6bb0",
                                             KIND["emergency_site"][li]: WARN},
                         zoom=10, center={"lat": 38.27, "lon": 140.87}, height=560, map_style="open-street-map")
    fig.update_traces(marker=dict(size=9, opacity=0.85))
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(title=None, orientation="h", y=-0.05))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q1_note") + f" ({len(m)})")

    # ② per 10,000 residents
    st.subheader(t("q2"))
    ww = w.dropna(subset=["population"]).copy()
    ww["label"] = ww["ward_en" if en else "ward_jp"]
    fig = go.Figure()
    fig.add_bar(y=ww.label, x=ww.shelters_per_10k, name=t("per_shel"), orientation="h", marker_color=BLUE,
                text=ww.shelters_per_10k.map(lambda v: f"{v:.2f}"), textposition="outside")
    fig.add_bar(y=ww.label, x=ww.sites_per_10k, name=t("per_site"), orientation="h", marker_color=WARN,
                text=ww.sites_per_10k.map(lambda v: f"{v:.2f}"), textposition="outside")
    fig.update_layout(barmode="group", height=360, margin=dict(l=10, r=30, t=10, b=10), yaxis=dict(autorange="reversed"),
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q2_note"))

    # ③ hazard x ward heatmap
    st.subheader(t("q3"))
    hz = [h for h in HAZ]
    grid = w.set_index("ward_en" if en else "ward_jp")[[f"sites_{h}" for h in hz]]
    grid.columns = [HAZ[h][li] for h in hz]
    fig = px.imshow(grid, text_auto=True, color_continuous_scale=["#f4f6f3", ACCENT], aspect="auto")
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), coloraxis_showscale=False,
                      xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q3_note"))

    # ④ tsunami site types
    st.subheader(t("q4"))
    rows = []
    rest = tsu.copy()
    for pat, ja, en_l in TSUNAMI_TYPES:
        hit = rest.name.str.contains(pat)
        rows.append((en_l if en else ja, int(hit.sum())))
        rest = rest[~hit]
    rows.append(("Other" if en else "その他", len(rest)))
    tt = pd.DataFrame(rows, columns=["type", "n"]).sort_values("n")
    fig = px.bar(tt, x="n", y="type", orientation="h", text="n")
    fig.update_traces(marker_color=ACCENT, textposition="outside", cliponaxis=False)
    fig.update_layout(height=320, margin=dict(l=10, r=30, t=10, b=10), xaxis_title=None, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander(t("data")):
        st.markdown(
            "- **Source:** 国土地理院 「指定緊急避難場所・指定避難所データ」 for Sendai (04100), downloaded after agreeing to GSI's terms. "
            "Credit: 出典：国土地理院. Ward populations: the population page (推計人口, latest October 1).\n"
            "- **No capacity field** exists in this data or on the city's site, so wards are compared by number of sites, not places.\n"
            "- **Per-resident comparisons are coarse for tsunami:** tsunami risk is concentrated near the coast, not spread across a ward.\n"
            "- **Welfare shelters** (36) are only for people arranged in advance (older or disabled residents); they're counted separately.\n"
            "- **Five tsunami staircases** on the 仙台東部道路 have no ward in their address and are kept as their own group.\n"
            "- **Checks:** CSV and GeoJSON versions hold identical IDs; no duplicates; every site lies inside Sendai; every site flagged as sharing a "
            "shelter's address is in the shelter list (196 of 196); ward counts add up to the totals."
            if en else
            "- **出典：** 国土地理院「指定緊急避難場所・指定避難所データ」（仙台市 04100、利用規約に同意のうえ取得）。区の人口は人口ページ（推計人口、最新の10月1日）。\n"
            "- **収容人数**はこのデータにも市のサイトにも含まれないため、区の比較は数のみ。\n"
            "- **津波は区単位の人口比較になじまない：** 津波の危険は沿岸部に集中しており、区全体に均等ではない。\n"
            "- **福祉避難所**（36か所）は事前に調整した高齢者・障害者等が対象のため、別に集計。\n"
            "- **仙台東部道路の避難階段5か所**は住所に区名がないため、独立したグループとして扱う。\n"
            "- **検証：** CSVとGeoJSONのID一致、重複なし、全地点が仙台市内、指定避難所と住所同一とされた196か所がすべて避難所一覧に存在、区別の合計＝総数。"
        )
