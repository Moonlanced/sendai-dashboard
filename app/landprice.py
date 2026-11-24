"""Land-price page of the Sendai city dashboard.

Data: data/processed/landprice/*.csv, produced by scripts/landprice_extract.py from
国土交通省「国土数値情報（地価公示・行政区域）」 (CC BY 4.0), and the population pipeline.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from geo import add_ward_outlines

ROOT = Path(__file__).resolve().parent.parent / "data" / "processed"
DATA = ROOT / "landprice"
ACCENT, MUTED, WARN, BLUE = "#1f6f5c", "#9aa6a0", "#b4651e", "#3b6ea5"
WARD_COLORS = {"Aoba": "#1f6f5c", "Miyagino": "#3b6ea5", "Wakabayashi": "#b4651e", "Taihaku": "#8a6bb0", "Izumi": "#6b8e23"}
CHANGE_BINS = [(-1e9, 0, "≤ 0%", "#b23a48"), (0, 20, "0–20%", "#c9d8cf"), (20, 40, "20–40%", "#7fb39c"),
               (40, 60, "40–60%", "#3a8a6c"), (60, 1e9, "60%+", "#14503f")]
PRICE_BINS = [(0, 50_000, "< ¥50k", "#e3ebe5"), (50_000, 100_000, "¥50–100k", "#a9c9b8"),
              (100_000, 200_000, "¥100–200k", "#5f9f84"), (200_000, 500_000, "¥200–500k", "#2f7a5f"),
              (500_000, 1e12, "¥500k+", "#103f32")]

T = {
    "title": {"ja": "地価：どこが上がり、どこが止まっているか", "en": "Land prices: where they're rising and where they've stalled"},
    "sub": {
        "ja": "地価公示（毎年1月1日時点、1㎡あたり）。住宅地と商業地、区ごと、駅からの距離ごとの違い",
        "en": "Official land prices (地価公示, per m², as of 1 January each year): residential vs commercial, by ward and by distance to a station",
    },
    "k_res": {"ja": "住宅地 中央値（2026）", "en": "Residential, median (2026)"},
    "k_com": {"ja": "商業地 中央値（2026）", "en": "Commercial, median (2026)"},
    "k_up": {"ja": "前年より上昇した地点", "en": "Points up on last year"},
    "k_peak": {"ja": "住宅地（1991年ピーク比）", "en": "Residential vs 1991 peak"},
    "yoy": {"ja": "前年比 中央値 {v:+.1f}%", "en": "median {v:+.1f}% on last year"},
    "of": {"ja": "{n}地点中", "en": "of {n} points"},
    "q1": {"ja": "① 1983年からの推移（2011年＝100）", "en": "① Since 1983 (index, 2011 = 100)"},
    "res": {"ja": "住宅地", "en": "Residential"},
    "com": {"ja": "商業地", "en": "Commercial"},
    "q1_note": {
        "ja": "各年、前年と両方の価格がある地点の変化率の中央値をつなげた指数。住宅地は1991年のピークを{peak_gap:.0f}%下回る水準まで戻った一方、商業地はピークの約{com_share:.0f}割にとどまる。2012年を底に14年連続で上昇。",
        "en": "Each year's median change across points priced in both years, chained. Residential land is back to {peak_gap:.0f}% below its 1991 peak; commercial land is at about {com_pct:.0f}% of its peak. Both bottomed in 2012 and have risen for 14 years in a row.",
    },
    "q2": {"ja": "② 地図：地点ごとの変化", "en": "② Map: change at each point"},
    "m_5y": {"ja": "5年間の変化（2021→2026）", "en": "5-year change (2021→2026)"},
    "m_1y": {"ja": "前年比（2025→2026）", "en": "1-year change (2025→2026)"},
    "m_price": {"ja": "価格（2026、円/㎡）", "en": "Price (2026, ¥/m²)"},
    "use_all": {"ja": "すべての用途", "en": "All uses"},
    "new": {"ja": "比較できない（新しい地点）", "en": "No earlier price (new point)"},
    "q2_note": {
        "ja": "線は区の境界。点にカーソルを合わせると標準地番号・住所・最寄駅を表示。",
        "en": "Lines are ward borders. Hover a point for its official number, address and nearest station.",
    },
    "q3": {"ja": "③ 区ごとの比較", "en": "③ Wards compared"},
    "q3a": {"ja": "住宅地の指数（2011年＝100）", "en": "Residential index (2011 = 100)"},
    "q3b": {"ja": "5年間の変化 中央値と人口の変化", "en": "Median 5-year change, and population change"},
    "pop_chg": {"ja": "人口 {a}→{b}", "en": "Population {a}→{b}"},
    "q3_note": {
        "ja": "2011年以降の住宅地の上昇は若林区が最も大きい（指数{wak:.0f}）。人口が減っている区（泉区・宮城野区）でも住宅地は30%以上上がっており、この5年は人口の増減と地価の動きが一致していない。",
        "en": "Since 2011, Wakabayashi's residential land has risen most (index {wak:.0f}). Residential prices rose more than 30% even in the wards losing population (Izumi, Miyagino): over these five years, population and land prices haven't moved together.",
    },
    "q4": {"ja": "④ 駅からの距離（住宅地）", "en": "④ Distance to a station (residential)"},
    "band": {"ja": "最寄駅までの距離", "en": "Distance to the nearest station"},
    "q4_note": {
        "ja": "駅から1km以内の住宅地は5年間で中央値32〜35%上昇し、5km以上離れた地点（主に西部・南部の山間部）は約24%にとどまる。価格の水準も駅から離れるほど低い。距離は鑑定評価書に記載された道路距離。",
        "en": "Residential points within 1 km of a station rose by a median of 32–35% over five years; those 5 km or more away (mostly the hills to the west and south) by about 24%. Price levels also fall with distance. The distance is the road distance given in the appraisal.",
    },
    "q5": {"ja": "⑤ 上昇・下落の大きい地点（5年間）", "en": "⑤ Biggest risers and fallers (5 years)"},
    "rise": {"ja": "上昇の大きい10地点", "en": "Top 10 risers"},
    "fall": {"ja": "上昇の小さい10地点", "en": "Bottom 10"},
    "q5_note": {
        "ja": "上位は扇町・苦竹・卸町・港などの工業地と、仙台駅東側の商業地（新寺・榴岡・二十人町・鉄砲町）。下位は坪沼・秋保・上愛子・実沢などの郊外・山間部と、国分町・一番町の中心商業地。2026年に下落したのは泉区の住宅地3地点（加茂・北高森・鶴が丘）のみ。",
        "en": "At the top: industrial land (扇町, 苦竹, 卸町, 港) and commercial land east of Sendai Station (新寺, 榴岡, 二十人町, 鉄砲町). At the bottom: the outskirts and hills (坪沼, 秋保, 上愛子, 実沢) and the central shopping and nightlife streets (国分町, 一番町). The only points that fell in 2026 are three residential points in Izumi (加茂, 北高森, 鶴が丘).",
    },
    "data": {"ja": "データと注意点", "en": "Data and caveats"},
}
COLS = {
    "id": ("標準地番号", "Point"), "address": ("住所", "Address"), "use": ("用途", "Use"),
    "station": ("最寄駅", "Station"), "price_2026": ("2026年（円/㎡）", "2026 (¥/m²)"), "change_5y_pct": ("5年変化（%）", "5-year change (%)"),
}


def t(key: str, **kw) -> str:
    return T[key][st.session_state.get("lang", "ja")].format(**kw)


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    d = {n: pd.read_csv(DATA / f"{n}.csv") for n in ["points", "index", "ward_summary", "checks"]}
    pop = ROOT / "population" / "pop_monthly.csv"
    d["pop"] = pd.read_csv(pop) if pop.exists() else None
    return d


def bin_label(v, bins) -> str:
    if pd.isna(v):
        return None
    for lo, hi, lab, _ in bins:
        if lo < v <= hi or (lo == -1e9 and v <= hi):
            return lab
    return bins[-1][2]


def render() -> None:
    lang = st.session_state.get("lang", "ja")
    en, li = lang == "en", 1 if lang == "en" else 0
    d = load()
    p, idx, ws = d["points"], d["index"], d["ward_summary"]
    res, com = p[p.use_en == "residential"], p[p.use_en == "commercial"]
    city = idx[idx.ward_jp == "仙台市"]
    ri = city[city.group == "residential"].set_index("year")["index"]
    ci = city[city.group == "commercial"].set_index("year")["index"]

    st.title(t("title"))
    st.caption(t("sub"))

    c = st.columns(4)
    c[0].metric(t("k_res"), f"¥{res.price_2026.median():,.0f}/㎡", t("yoy", v=res.yoy_pct.median()), delta_color="off")
    c[1].metric(t("k_com"), f"¥{com.price_2026.median():,.0f}/㎡", t("yoy", v=com.yoy_pct.median()), delta_color="off")
    c[2].metric(t("k_up"), f"{(p.yoy_pct > 0).sum()}", t("of", n=len(p)), delta_color="off")
    c[3].metric(t("k_peak"), f"{(ri[2026] / ri.max() - 1) * 100:+.0f}%")

    # ① long-run index
    st.subheader(t("q1"))
    fig = go.Figure()
    for s, name, col in [(ri, t("res"), ACCENT), (ci, t("com"), WARN)]:
        n = city[city.group == ("residential" if col == ACCENT else "commercial")].set_index("year")["points_compared"]
        s = s.dropna()
        fig.add_scatter(x=s.index, y=s.values, name=name, mode="lines", line=dict(color=col, width=2.5),
                        customdata=n.reindex(s.index).values,
                        hovertemplate="%{x}: %{y:.0f}<br>n = %{customdata}<extra>" + name + "</extra>")
    for x, lab in [(1991, {"ja": "1991 ピーク", "en": "1991 peak"}[lang]), (2011, {"ja": "2011 震災", "en": "2011 earthquake"}[lang])]:
        fig.add_vline(x=x, line=dict(color=MUTED, dash="dot", width=1))
        fig.add_annotation(x=x, y=1, yref="paper", text=lab, showarrow=False, xanchor="left", yanchor="top",
                           font=dict(color="#5b6661", size=11), xshift=4)
    fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.12),
                      yaxis_title=None, xaxis_title=None, hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q1_note", peak_gap=(1 - ri[2026] / ri.max()) * 100, com_share=ci[2026] / ci.max() * 10,
                 com_pct=ci[2026] / ci.max() * 100))

    # ② map
    st.subheader(t("q2"))
    a, b = st.columns([3, 2])
    metric = a.radio(" ", ["m_5y", "m_1y", "m_price"], format_func=t, horizontal=True, label_visibility="collapsed")
    uses = {"all": t("use_all"), "residential": t("res"), "commercial": t("com")}
    use = b.radio("  ", list(uses), format_func=uses.get, horizontal=True, label_visibility="collapsed")
    m = p if use == "all" else p[p.use_en == use]
    col_name, bins = {"m_5y": ("change_5y_pct", CHANGE_BINS), "m_1y": ("yoy_pct", CHANGE_BINS),
                      "m_price": ("price_2026", PRICE_BINS)}[metric]
    if metric == "m_1y":
        bins = [(-1e9, 0, "≤ 0%", "#b23a48"), (0, 3, "0–3%", "#c9d8cf"), (3, 6, "3–6%", "#7fb39c"),
                (6, 10, "6–10%", "#3a8a6c"), (10, 1e9, "10%+", "#14503f")]
    m = m.assign(cls=m[col_name].map(lambda v: bin_label(v, bins)).fillna(t("new")),
                 use=m["use_en" if en else "use_jp"], ward=m["ward_en" if en else "ward_jp"],
                 price=m.price_2026.map(lambda v: f"¥{v:,.0f}"), dist=m.station_m.map(lambda v: f"{v:,.0f} m"))
    order = [lab for *_, lab, _ in bins] + [t("new")]
    colors = {lab: c_ for *_, lab, c_ in bins} | {t("new"): "#bbbbbb"}
    fig = px.scatter_map(m, lat="lat", lon="lon", color="cls", hover_name="id", category_orders={"cls": order},
                         color_discrete_map=colors,
                         hover_data={"address": True, "use": True, "price": True, "change_5y_pct": ":.1f", "yoy_pct": ":.1f",
                                     "station": True, "dist": True, "lat": False, "lon": False, "cls": False},
                         labels={"change_5y_pct": "5y %", "yoy_pct": "1y %", "dist": "→"},
                         zoom=10, center={"lat": 38.27, "lon": 140.80}, height=580, map_style="open-street-map")
    fig.update_traces(marker=dict(size=10, opacity=0.9))
    add_ward_outlines(fig)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), legend=dict(title=None, orientation="h", y=-0.04))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q2_note") + f" ({len(m)})")

    # ③ wards
    st.subheader(t("q3"))
    a, b = st.columns(2)
    wi = idx[(idx.group == "residential") & (idx.ward_jp != "仙台市")].dropna(subset=["index"])
    wi = wi[wi.year >= 1993]
    fig = px.line(wi, x="year", y="index", color="ward_en", color_discrete_map=WARD_COLORS,
                  labels={"ward_en": "", "index": "", "year": ""})
    if not en:
        names = dict(zip(wi.ward_en, wi.ward_jp))
        fig.for_each_trace(lambda tr: tr.update(name=names[tr.name]))
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=30, b=10), legend=dict(orientation="h", y=-0.15),
                      title=dict(text=t("q3a"), font=dict(size=14)), hovermode="x unified")
    a.plotly_chart(fig, use_container_width=True)

    wsum = ws[ws.ward_jp != "仙台市"].copy()
    wsum["label"] = wsum["ward_en" if en else "ward_jp"]
    fig = go.Figure()
    for u, name, col in [("residential", t("res"), ACCENT), ("commercial", t("com"), WARN)]:
        s = wsum[wsum.use == u]
        fig.add_bar(y=s.label, x=s.median_change_5y_pct, name=name, orientation="h", marker_color=col,
                    text=s.median_change_5y_pct.map(lambda v: f"{v:+.0f}%"), textposition="outside", cliponaxis=False,
                    customdata=s.points_with_5y, hovertemplate="%{y}: %{x:.1f}% (n = %{customdata})<extra>" + name + "</extra>")
    popd = d["pop"]
    if popd is not None:
        octs = sorted(x for x in popd.date.unique() if x.endswith("-10-01"))
        y1, y0 = octs[-1], f"{int(octs[-1][:4]) - 5}-10-01"
        if y0 in set(octs):
            pa = popd[popd.date == y0].set_index("area_jp").population
            pb = popd[popd.date == y1].set_index("area_jp").population
            s = wsum[wsum.use == "residential"]
            chg = [(pb[w] / pa[w] - 1) * 100 for w in s.ward_jp]
            fig.add_bar(y=s.label, x=chg, name=t("pop_chg", a=y0[:4], b=y1[:4]), orientation="h", marker_color=MUTED,
                        text=[f"{v:+.1f}%" for v in chg], textposition="outside", cliponaxis=False)
    fig.update_layout(barmode="group", height=380, margin=dict(l=10, r=40, t=30, b=10), yaxis=dict(autorange="reversed"),
                      legend=dict(orientation="h", y=-0.15), title=dict(text=t("q3b"), font=dict(size=14)))
    b.plotly_chart(fig, use_container_width=True)
    wak = wi[(wi.ward_en == "Wakabayashi") & (wi.year == wi.year.max())]["index"].iloc[0]
    st.caption(t("q3_note", wak=wak))

    # ④ distance to station
    st.subheader(t("q4"))
    bands = [(0, 500, "< 500 m"), (500, 1000, "500 m–1 km"), (1000, 2000, "1–2 km"), (2000, 5000, "2–5 km"), (5000, 1e9, "5 km+")]
    rows = []
    for lo, hi, lab in bands:
        s = res[(res.station_m > lo - (lo == 0)) & (res.station_m <= hi)]
        rows.append([lab, len(s), s.change_5y_pct.median(), s.price_2026.median()])
    bt = pd.DataFrame(rows, columns=["band", "n", "chg", "price"])
    a, b = st.columns(2)
    fig = px.bar(bt, x="band", y="chg", text=bt.chg.map(lambda v: f"{v:+.0f}%"), labels={"band": "", "chg": ""},
                 title=t("m_5y") + " — " + {"ja": "中央値", "en": "median"}[lang], custom_data=["n"])
    fig.update_traces(marker_color=ACCENT, textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}: %{y:.1f}% (n = %{customdata[0]})<extra></extra>")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10), title_font_size=14)
    a.plotly_chart(fig, use_container_width=True)
    fig = px.bar(bt, x="band", y="price", text=bt.price.map(lambda v: f"¥{v / 1000:,.0f}k"), labels={"band": "", "price": ""},
                 title=t("m_price") + " — " + {"ja": "中央値", "en": "median"}[lang], custom_data=["n"])
    fig.update_traces(marker_color=BLUE, textposition="outside", cliponaxis=False,
                      hovertemplate="%{x}: ¥%{y:,.0f} (n = %{customdata[0]})<extra></extra>")
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=40, b=10), title_font_size=14)
    b.plotly_chart(fig, use_container_width=True)
    st.caption(t("q4_note"))

    # ⑤ risers and fallers
    st.subheader(t("q5"))
    tab = p.dropna(subset=["change_5y_pct"]).assign(use=p["use_en" if en else "use_jp"])
    show = ["id", "address", "use", "change_5y_pct"]
    ren = {k: v[li] for k, v in COLS.items()}
    a, b = st.columns(2)
    for col, title, frame in [(a, t("rise"), tab.nlargest(10, "change_5y_pct")), (b, t("fall"), tab.nsmallest(10, "change_5y_pct"))]:
        col.markdown(f"**{title}**")
        f = frame[show].assign(address=frame.address.str.replace("宮城県 仙台市", "", regex=False)).rename(columns=ren)
        col.dataframe(f, hide_index=True, use_container_width=True,
                      column_config={ren["change_5y_pct"]: st.column_config.NumberColumn(format="%+.1f")})
    st.caption(t("q5_note"))

    with st.expander(t("data")):
        ck = d["checks"]
        st.markdown(
            "- **Source:** 国土交通省 「国土数値情報 地価公示データ」 (L01) 2026, 2016 and 2006 editions for Miyagi; ward boundaries from "
            "「行政区域データ」 (N03, 1 January 2025). Credit: 出典：国土交通省「国土数値情報」, CC BY 4.0.\n"
            "- **What a 地価公示 price is:** an appraisal of a normal transaction price for a standard plot, by two licensed appraisers, as of "
            "1 January. It isn't a sale price, and there's one point per area, not every plot.\n"
            "- **Survivorship:** the history comes from the 2026 file, which only holds points still surveyed in 2026. Points dropped earlier "
            "aren't in the index; early years rest on fewer points (n is shown on hover). Rebuilding the residential index from the 2016 file's "
            "points gives at most a 1.2% difference.\n"
            "- **Index:** each year, the median price ratio of points priced in both that year and the year before, chained, 2011 = 100. "
            "Years with fewer than 10 comparable points are left out (so commercial starts in 1985).\n"
            "- **Points per ward are few** (5 commercial points in Izumi, 7 in Taihaku), so a ward median can move with one point.\n"
            "- **Population change** uses 推計人口 on 1 October; the 2025 census re-based the series, which is included in the 5-year change.\n"
            f"- **Checks ({(ck.passed.astype(str) == 'True').sum()} passed, {(ck.passed.astype(str) == 'False').sum()} source issues):** "
            "the 2026 price equals its history column; 'surveyed' flags match the prices; every point lies inside the ward polygon its code "
            "names and its address names the same ward; all 306 printed year-on-year % match the prices; every price published in 2016 and "
            "2006 that the 2026 file also holds is identical (5,111 and 195 values; points matched by location)."
            if en else
            "- **出典：** 国土交通省「国土数値情報 地価公示データ」（L01）2026年・2016年・2006年の宮城県分、区の境界は「行政区域データ」（N03、2025年1月1日）。"
            "出典：国土交通省「国土数値情報」（CC BY 4.0）。\n"
            "- **地価公示価格とは：** 1月1日時点の標準地について、不動産鑑定士2名が評価した正常な取引価格。実際の売買価格ではなく、地域ごとの代表地点。\n"
            "- **残存地点のみ：** 推移は2026年ファイルの過去価格を使うため、現在も調査されている地点だけが対象。途中で廃止された地点は含まれず、"
            "古い年ほど地点数が少ない（カーソルでnを表示）。2016年ファイルの地点で住宅地指数を作り直しても差は最大1.2%。\n"
            "- **指数：** 各年、前年と両方の価格がある地点の価格比の中央値をつなげたもの（2011年＝100）。比較できる地点が10未満の年は除外（商業地は1985年から）。\n"
            "- **区ごとの地点数は少ない**（泉区の商業地5、太白区7）ため、1地点で中央値が動く。\n"
            "- **人口の変化**は10月1日の推計人口。2025年国勢調査による補正を含む。\n"
            f"- **検証（合格{(ck.passed.astype(str) == 'True').sum()}件、元データの誤り{(ck.passed.astype(str) == 'False').sum()}件）：** "
            "2026年価格＝過去価格の2026年列、調査年フラグと価格の一致、全地点が区コードの区の境界内にあり住所の区とも一致、前年比306件すべて一致、"
            "2016年・2006年に公表された価格と2026年ファイルの過去価格が完全一致（5,111件・195件、位置で照合）。"
        )
