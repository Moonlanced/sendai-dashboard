"""Population page of the Sendai city dashboard.

Data: data/processed/population/*.csv, produced by scripts/population_extract.py
from the City of Sendai 推計人口, 5歳階級別人口 and 将来人口推計 files.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data" / "processed" / "population"
ACCENT, MUTED, WARN, BLUE = "#1f6f5c", "#9aa6a0", "#b4651e", "#3b6ea5"
WARDS_JP = ["青葉区", "宮城野区", "若林区", "太白区", "泉区"]
WARD_COLORS = {"青葉区": "#1f6f5c", "宮城野区": "#3b6ea5", "若林区": "#8a6bb0", "太白区": "#9aa6a0", "泉区": "#b4651e"}

T = {
    "title": {"ja": "人口：減少・高齢化と区ごとの差", "en": "Population: decline, ageing and the gap between wards"},
    "sub": {
        "ja": "推計人口（1999年〜、月次335か月分）・年齢別人口（2003年〜）・将来人口推計（〜2070年）を統合",
        "en": "Monthly population since 1999 (335 months), age structure since 2003 and the city's projections to 2070",
    },
    "k_pop": {"ja": "人口", "en": "Population"},
    "k_peak": {"ja": "ピーク比", "en": "vs peak"},
    "k_old": {"ja": "65歳以上の割合", "en": "Aged 65+"},
    "k_nat": {"ja": "自然増減（出生−死亡）", "en": "Births − deaths"},
    "q1": {"ja": "① 人口の推移（1999年〜）", "en": "① Population since 1999"},
    "q1_note": {
        "ja": "2022年11月の1,099,547人がピーク。毎年4月の落ち込みは進学・就職・転勤による転出入の季節変動。国勢調査ごとに推計の基準が更新されるため、10月に小さな段差が生じます。",
        "en": "Peak: 1,099,547 in November 2022. The dip every April is the seasonal move for school, jobs and transfers. The estimate is re-based on each census, which causes small steps in October.",
    },
    "q2": {"ja": "② 出生と死亡", "en": "② Births and deaths"},
    "q2_note": {
        "ja": "2017年に死亡が出生を上回り、以降は自然減。出生は1999年の10,070人から2025年は6,301人（−37%）、死亡は約2倍に。人口を支えているのは転入（社会増）。",
        "en": "Deaths have outnumbered births since 2017. Births fell from 10,070 (1999) to 6,301 (2025), −37%, while deaths doubled; people moving in are what keeps the population up.",
    },
    "births": {"ja": "出生", "en": "Births"},
    "deaths": {"ja": "死亡", "en": "Deaths"},
    "q3": {"ja": "③ 区ごとの差", "en": "③ How the wards differ"},
    "chg": {"ja": "2019年10月からの人口増減率", "en": "Population change since Oct 2019"},
    "aging": {"ja": "65歳以上の割合の推移", "en": "Share aged 65+ over time"},
    "q3_note": {
        "ja": "泉区は2003年には最も若い区（65歳以上12.0%）だったが、現在は最も高齢化が進んだ区。秋保は2019年比で約1割減少。",
        "en": "Izumi was the youngest ward in 2003 (12.0% aged 65+) and is now the oldest. The Akiu area has lost about a tenth of its people since 2019.",
    },
    "pyramid": {"ja": "年齢構成の変化（仙台市）", "en": "Age structure then and now (city)"},
    "q4": {"ja": "④ 2070年までの将来推計（2020年＝100）", "en": "④ Projection to 2070 (2020 = 100)"},
    "q4_note": {
        "ja": "市の推計（令和4年推計）。泉区は2070年に2020年の約半分（52%）、65歳以上が46%になる見込み。点は実績値（推計人口、各年10月1日）。2025年の実績は推計を市全体で0.4%下回り、宮城野区は2.3%下回る一方、青葉区は1.3%上回った。",
        "en": "City projection (2022). Izumi is projected to fall to about half its 2020 size by 2070 (52%), with 46% aged 65+. Dots are actual figures (October 1 each year). In 2025 the city came in 0.4% below the projection; Miyagino 2.3% below, Aoba 1.3% above.",
    },
    "actual": {"ja": "実績", "en": "actual"},
    "data": {"ja": "データと注意点", "en": "Data and caveats"},
    "source": {
        "ja": "出典：仙台市「推計人口」「住民基本台帳による区・年齢（5歳階級）別人口」「仙台市の将来人口推計（令和4年推計）」を加工して作成",
        "en": "Source: City of Sendai 推計人口, 年齢5歳階級別人口 and 将来人口推計 (2022), processed by the author",
    },
}


def t(key: str) -> str:
    return T[key][st.session_state.get("lang", "ja")]


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    d = {name: pd.read_csv(DATA / f"{name}.csv") for name in
         ("pop_monthly", "vitals_monthly", "age3", "age_groups", "projection")}
    d["pop_monthly"]["date"] = pd.to_datetime(d["pop_monthly"]["date"])
    return d


def render() -> None:
    en = st.session_state.get("lang", "ja") == "en"
    area = "area_en" if en else "area_jp"
    d = load()
    pm, vit, age3, groups, proj = d["pop_monthly"], d["vitals_monthly"], d["age3"], d["age_groups"], d["projection"]

    st.title(t("title"))
    st.caption(t("sub"))

    city = pm[pm.area_jp == "仙台市"].set_index("date")["population"]
    latest, peak = city.iloc[-1], city.max()
    a_latest = age3[age3.date == age3.date.max()].set_index("area_jp")
    vit["year"] = vit["month"].str[:4].astype(int)
    full_year = vit[vit.area_jp == "仙台市"].groupby("year").size().loc[lambda s: s == 12].index.max()
    yv = vit[(vit.area_jp == "仙台市") & (vit.year == full_year)][["births", "deaths"]].sum()

    c = st.columns(4)
    c[0].metric(f"{t('k_pop')} ({city.index[-1]:%Y-%m})", f"{latest:,.0f}")
    c[1].metric(t("k_peak"), f"{latest - peak:+,.0f}", f"{city.idxmax():%Y-%m}: {peak:,.0f}", delta_color="off")
    c[2].metric(f"{t('k_old')} ({age3.date.max()[:7]})",
                f"{a_latest.loc['仙台市', 'age_65_plus'] / a_latest.loc['仙台市', 'total'] * 100:.1f}%")
    c[3].metric(f"{t('k_nat')} ({full_year})", f"{yv.births - yv.deaths:+,.0f}",
                f"{t('births')} {yv.births:,.0f} / {t('deaths')} {yv.deaths:,.0f}", delta_color="off")

    # ① population since 1999
    st.subheader(t("q1"))
    options = ["仙台市"] + WARDS_JP + ["宮城総合支所", "秋保総合支所"]
    labels = dict(zip(pm.area_jp, pm[area]))
    pick = st.selectbox(" ", options, format_func=lambda a: labels[a], label_visibility="collapsed")
    s = pm[pm.area_jp == pick]
    fig = go.Figure(go.Scatter(x=s.date, y=s.population, mode="lines", line=dict(color=ACCENT, width=2.5),
                               hovertemplate="%{x|%Y-%m}: %{y:,.0f}<extra></extra>"))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis_tickformat=",")
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q1_note"))

    # ② births and deaths per calendar year (complete years only)
    st.subheader(t("q2"))
    yearly = vit[vit.area_jp == "仙台市"].groupby("year").agg(births=("births", "sum"), deaths=("deaths", "sum"),
                                                             months=("births", "size"))
    yearly = yearly[yearly.months == 12]
    fig = go.Figure()
    fig.add_scatter(x=yearly.index, y=yearly.births, name=t("births"), mode="lines+markers", line=dict(color=ACCENT, width=2.5))
    fig.add_scatter(x=yearly.index, y=yearly.deaths, name=t("deaths"), mode="lines+markers", line=dict(color=WARN, width=2.5))
    fig.update_layout(height=320, margin=dict(l=10, r=10, t=10, b=10), yaxis_tickformat=",", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q2_note"))

    # ③ wards
    st.subheader(t("q3"))
    left, right = st.columns(2)
    base = pm[pm.date == "2019-10-01"].set_index("area_jp")["population"]
    last_oct = pm[pm.date.dt.month == 10].date.max()
    now = pm[pm.date == last_oct].set_index("area_jp")["population"]
    chg = ((now / base - 1) * 100).drop("仙台市").sort_values()
    chg.index = [labels[a] for a in chg.index]
    fig = px.bar(chg, orientation="h", text=chg.map(lambda v: f"{v:+.1f}%"))
    # long bars: label inside (white); short bars: label outside, so it never collides with the axis labels
    fig.update_traces(marker_color=[WARN if v < 0 else ACCENT for v in chg], textangle=0, cliponaxis=False,
                      textposition=["inside" if abs(v) > 2.5 else "outside" for v in chg],
                      insidetextanchor="middle",
                      textfont=dict(color=["white" if abs(v) > 2.5 else "#444" for v in chg]))
    fig.add_vline(x=0, line_color=MUTED)
    fig.update_layout(height=340, showlegend=False, title=f"{t('chg')} → {last_oct:%Y-%m}", xaxis_title="%",
                      yaxis_title=None, margin=dict(l=10, r=40, t=40, b=10))
    left.plotly_chart(fig, use_container_width=True)

    a = age3[age3.area_jp.isin(WARDS_JP)].copy()
    a["share65"] = a.age_65_plus / a.total * 100
    a["date"] = pd.to_datetime(a.date)
    fig = go.Figure()
    for w in WARDS_JP:
        s = a[a.area_jp == w]
        fig.add_scatter(x=s.date, y=s.share65, name=labels[w], mode="lines", line=dict(color=WARD_COLORS[w], width=2.5))
    fig.update_layout(height=340, title=t("aging"), yaxis_title="%", margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.2))
    right.plotly_chart(fig, use_container_width=True)
    st.caption(t("q3_note"))

    # age structure: first vs latest date, city
    first, last = groups.date.min(), groups.date.max()
    g = groups[(groups.area_jp == "仙台市") & groups.date.isin([first, last])]
    order = list(dict.fromkeys(g.age_group))
    fig = go.Figure()
    for date, color in ((first, MUTED), (last, ACCENT)):
        s = g[g.date == date].set_index("age_group").reindex(order)
        fig.add_bar(x=order, y=s.population, name=date[:7], marker_color=color)
    fig.update_layout(barmode="group", height=320, title=t("pyramid"), yaxis_tickformat=",",
                      margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig, use_container_width=True)

    # ④ projection, indexed to 2020, with actual October figures as dots
    st.subheader(t("q4"))
    p = proj[proj.area_jp.isin(["仙台市"] + WARDS_JP)].copy()
    p["idx"] = p.groupby("area_jp").total.transform(lambda s: s / s.iloc[0] * 100)
    act = pm[(pm.date.dt.month == 10) & (pm.date.dt.year >= 2020) & pm.area_jp.isin(["仙台市"] + WARDS_JP)].copy()
    act["year"] = act.date.dt.year
    base2020 = p[p.year == 2020].set_index("area_jp").total
    act["idx"] = act.population / act.area_jp.map(base2020) * 100
    fig = go.Figure()
    for a_jp in ["仙台市"] + WARDS_JP:
        color = "#222222" if a_jp == "仙台市" else WARD_COLORS[a_jp]
        s = p[p.area_jp == a_jp]
        fig.add_scatter(x=s.year, y=s.idx, name=labels[a_jp], mode="lines",
                        line=dict(color=color, width=3 if a_jp == "仙台市" else 2, dash="solid"))
        s = act[act.area_jp == a_jp]
        fig.add_scatter(x=s.year, y=s.idx, name=f"{labels[a_jp]} ({t('actual')})", mode="markers",
                        marker=dict(color=color, size=6), showlegend=False,
                        hovertemplate="%{x}: %{y:.1f} (" + t("actual") + ")<extra></extra>")
    fig.add_hline(y=100, line_dash="dot", line_color=MUTED)
    fig.update_layout(height=420, yaxis_title="2020 = 100", margin=dict(l=10, r=10, t=10, b=10),
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q4_note"))

    with st.expander(t("data")):
        st.markdown(t("source"))
        st.markdown(
            "- **Population (①③)** is the city's 推計人口: census figures carried forward with monthly registry changes. "
            "**Age structure** comes from the resident registry (住民基本台帳), so its totals differ slightly from 推計人口.\n"
            "- Foreign residents are in the registry figures from July 2012 (law change).\n"
            "- The Miyagi and Akiu areas are parts of Aoba and Taihaku wards; they are not added to the city total.\n"
            "- Checks on every file: wards add up to the city; total = men + women; births and deaths summed per year match "
            "the city's own yearly table exactly (2021–2025); no month is missing.\n"
            "- Errors found in the source and logged in checks.csv: the Dec 2009 file prints 宮城野区's natural change as 0 "
            "(births − deaths = 101); the projection file prints the same 2022 under-15 figure (24,067) for three wards — the "
            "single-year ages are used instead.\n"
            "- Projections are the city's (2022), not the author's."
            if en else
            "- **人口（①③）** は市の推計人口（国勢調査人口に毎月の住民基本台帳の増減を加減）。**年齢構成**は住民基本台帳によるため、合計が推計人口とわずかに異なります。\n"
            "- 平成24年7月の法改正以降、住民基本台帳には外国人住民も含まれます。\n"
            "- 宮城総合支所・秋保総合支所はそれぞれ青葉区・太白区の一部で、市の合計には加算していません。\n"
            "- 全ファイルで検証：区の合計＝市、総数＝男＋女、月別の出生・死亡の年合計が市の年次表と完全一致（2021〜2025年）、欠けている月なし。\n"
            "- 原資料の誤記を検出し checks.csv に記録：平成22年1月版で宮城野区の自然増加数が0と記載（出生−死亡＝101）、将来推計で3つの区の2022年0〜14歳が同じ値（24,067）と記載（各歳別人口から再集計した値を使用）。\n"
            "- 将来推計は市の推計（令和4年推計）であり、作成者によるものではありません。"
        )
