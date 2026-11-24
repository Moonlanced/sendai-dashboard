"""Mobility page of the Sendai city dashboard.

Data: data/processed/mobility/*.csv, produced by scripts/mobility_extract.py from the
仙台市統計書 (city buses, subway, JR stations), 交通局 station counts and the
国土交通省 airport statistics. Foreign overnight stays come from the tourism pipeline.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent / "data" / "processed"
DATA = ROOT / "mobility"
ACCENT, MUTED, WARN, BLUE = "#1f6f5c", "#9aa6a0", "#b4651e", "#3b6ea5"
BASE = 2019

T = {
    "title": {"ja": "交通：市民の移動と空の玄関口", "en": "Mobility: how people move, and the airport"},
    "sub": {
        "ja": "市営バス・地下鉄（2006年度〜）、JR各駅（2007年度〜）、地下鉄駅別（2007年度〜）、仙台空港（2007年〜）",
        "en": "City buses and subway (FY2006–), JR stations (FY2007–), subway stations (FY2007–), Sendai Airport (2007–)",
    },
    "subway": {"ja": "地下鉄", "en": "Subway"},
    "bus": {"ja": "市営バス", "en": "City buses"},
    "jr": {"ja": "JR 1日平均", "en": "JR per day"},
    "airport": {"ja": "仙台空港 旅客数", "en": "Sendai Airport passengers"},
    "vs": {"ja": f"{BASE}年度比", "en": f"vs FY{BASE}"},
    "vs_cy": {"ja": f"{BASE}年比", "en": f"vs {BASE}"},
    "q1": {"ja": "① 市営バスと地下鉄の乗車人員（年度）", "en": "① City bus and subway passengers (fiscal year)"},
    "q1_note": {
        "ja": "2015年12月の東西線開業を境に、地下鉄が増え市営バスが減った。バスはコロナ前から長期的に減少しており、2024年度は2019年度の92%。地下鉄は2024年度に過去最多。",
        "en": "When the Tozai Line opened in December 2015, subway use rose and bus use fell. Buses were declining long before COVID and are at 92% of FY2019 in FY2024; the subway set a record in FY2024.",
    },
    "q2": {"ja": "② コロナ前（2019＝100）からの回復", "en": "② Recovery from COVID (2019 = 100)"},
    "q2_note": {
        "ja": "交通機関は年度、空港は暦年。空港は2025年に過去最多の397万人。",
        "en": "Transit is by fiscal year, the airport by calendar year. The airport set a record in 2025: 3.97 million passengers.",
    },
    "q3": {"ja": "③ 駅ごとの変化（2019年度→最新年度）", "en": "③ Station by station (FY2019 → latest)"},
    "q3_sub": {"ja": "地下鉄（乗車人員）", "en": "Subway (boardings)"},
    "q3_jr": {"ja": "JR（1日平均乗車人員）", "en": "JR (daily boardings)"},
    "q4": {"ja": "④ 空の玄関口とインバウンド", "en": "④ The airport and foreign visitors"},
    "dom": {"ja": "国内線", "en": "Domestic"},
    "intl": {"ja": "国際線", "en": "International"},
    "foreign": {"ja": "外国人宿泊者数（観光ページ）", "en": "Foreign overnight stays (tourism page)"},
    "q4_note": {
        "ja": "国際線旅客数と外国人宿泊者数は同じ方向に動く。ただし国際線には海外へ出かける日本人も含まれるため、2019年までは国際線が外国人宿泊者数を大きく上回っていた。2025年は外国人宿泊者数（76.7万人）が国際線旅客数（62.8万人）を上回り、空路以外（新幹線など）で仙台に来る外国人客の存在がうかがえる。国際線は2021年に0人（全便運休）。相関は因果を示すものではありません。",
        "en": "International passengers and foreign overnight stays move in the same direction. International passengers also include Japanese residents travelling abroad, which is why they were well above foreign stays until 2019. In 2025 foreign stays (767,000) exceeded international passengers (628,000), a sign that many foreign visitors reach Sendai other than by air (e.g. Shinkansen). In 2021 there were no international passengers at all. Moving together doesn't prove one causes the other.",
    },
    "data": {"ja": "データと注意点", "en": "Data and caveats"},
}


def t(key: str) -> str:
    return T[key][st.session_state.get("lang", "ja")]


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    d = {
        "transit": pd.read_csv(DATA / "transit_fy.csv"),
        "jr": pd.read_csv(DATA / "jr_stations_fy.csv"),
        "subway_st": pd.read_csv(DATA / "subway_stations_fy.csv"),
        "airport": pd.read_csv(DATA / "airport_cy.csv"),
    }
    tour = ROOT / "annual.csv"
    d["tourism"] = pd.read_csv(tour) if tour.exists() else pd.DataFrame(columns=["year", "foreign_stays"])
    return d


def render() -> None:
    en = st.session_state.get("lang", "ja") == "en"
    d = load()
    tr = d["transit"].pivot(index="fiscal_year", columns="mode", values="passengers")
    jr = d["jr"]
    jr_total = jr[jr.station == "総数"].set_index("fiscal_year").daily_boardings
    ap = d["airport"].set_index("year")

    st.title(t("title"))
    st.caption(t("sub"))

    fy, cy = tr.index.max(), ap.index.max()
    c = st.columns(4)
    for col, key, s, label in [(c[0], "subway", tr["subway"], t("vs")), (c[1], "bus", tr["bus"], t("vs"))]:
        col.metric(f"{t(key)} (FY{fy})", f"{s.loc[fy] / 1e6:.1f}M" if en else f"{s.loc[fy] / 1e4:,.0f}万人",
                   f"{s.loc[fy] / s.loc[BASE] * 100:.0f}% {label}", delta_color="off")
    jfy = jr_total.index.max()
    c[2].metric(f"{t('jr')} (FY{jfy})", f"{jr_total.loc[jfy]:,.0f}",
                f"{jr_total.loc[jfy] / jr_total.loc[BASE] * 100:.0f}% {t('vs')}", delta_color="off")
    c[3].metric(f"{t('airport')} ({cy})", f"{ap.total.loc[cy] / 1e6:.2f}M" if en else f"{ap.total.loc[cy] / 1e4:,.0f}万人",
                f"{ap.total.loc[cy] / ap.total.loc[BASE] * 100:.0f}% {t('vs_cy')}", delta_color="off")

    # ① bus and subway
    st.subheader(t("q1"))
    fig = go.Figure()
    for mode, color in (("subway", ACCENT), ("bus", WARN)):
        fig.add_scatter(x=tr.index, y=tr[mode] / 1e6, name=t(mode), mode="lines+markers", line=dict(color=color, width=2.5),
                        hovertemplate="FY%{x}: %{y:.1f}M<extra></extra>")
    for x, label in ((2015, "東西線" if not en else "Tozai Line"), (2010, "3.11"), (2020, "COVID-19")):
        fig.add_vline(x=x - 0.5 if x == 2015 else x, line_dash="dot", line_color=MUTED)
        fig.add_annotation(x=x, y=1.02, yref="paper", text=label, showarrow=False, font=dict(size=11))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=30, b=10), yaxis_title="million" if en else "百万人",
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q1_note"))

    # ② recovery index
    st.subheader(t("q2"))
    series = {
        t("subway"): (tr["subway"] / tr.loc[BASE, "subway"] * 100, ACCENT),
        t("bus"): (tr["bus"] / tr.loc[BASE, "bus"] * 100, WARN),
        "JR": (jr_total / jr_total.loc[BASE] * 100, BLUE),
        t("airport"): (ap.total / ap.total.loc[BASE] * 100, "#222222"),
    }
    fig = go.Figure()
    for name, (s, color) in series.items():
        s = s.loc[2017:]
        fig.add_scatter(x=s.index, y=s, name=name, mode="lines+markers", line=dict(color=color, width=2.5))
    fig.add_hline(y=100, line_dash="dot", line_color=MUTED)
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="2019 = 100",
                      legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q2_note"))

    # ③ stations
    st.subheader(t("q3"))
    left, right = st.columns(2)
    ss = d["subway_st"]
    ss = ss[~ss.station.isin(["総数"]) & ~ss.station.str.contains("乗換")]
    last = ss.fiscal_year.max()
    p = ss[ss.fiscal_year.isin([BASE, last])].pivot_table(index="station", columns="fiscal_year", values="boardings", aggfunc="sum")
    chg = ((p[last] / p[BASE] - 1) * 100).dropna().sort_values()
    fig = px.bar(chg, orientation="h", text=chg.map(lambda v: f"{v:+.0f}%"))
    fig.update_traces(marker_color=[WARN if v < 0 else ACCENT for v in chg], textangle=0, cliponaxis=False,
                      textposition=["inside" if abs(v) > 8 else "outside" for v in chg],
                      textfont=dict(color=["white" if abs(v) > 8 else "#444" for v in chg]))
    fig.add_vline(x=0, line_color=MUTED)
    fig.update_layout(height=760, showlegend=False, title=f"{t('q3_sub')} FY{BASE}→FY{last}", xaxis_title="%",
                      yaxis_title=None, margin=dict(l=10, r=40, t=40, b=10))
    left.plotly_chart(fig, use_container_width=True)

    jl = jr.fiscal_year.max()
    pj = jr[jr.fiscal_year.isin([BASE, jl]) & ~jr.station.isin(["総数"])].pivot(index="station", columns="fiscal_year",
                                                                               values="daily_boardings")
    cj = ((pj[jl] / pj[BASE] - 1) * 100).dropna().sort_values()
    fig = px.bar(cj, orientation="h", text=cj.map(lambda v: f"{v:+.0f}%"))
    fig.update_traces(marker_color=[WARN if v < 0 else ACCENT for v in cj], textangle=0, cliponaxis=False,
                      textposition=["inside" if abs(v) > 8 else "outside" for v in cj],
                      textfont=dict(color=["white" if abs(v) > 8 else "#444" for v in cj]))
    fig.add_vline(x=0, line_color=MUTED)
    fig.update_layout(height=760, showlegend=False, title=f"{t('q3_jr')} FY{BASE}→FY{jl}", xaxis_title="%",
                      yaxis_title=None, margin=dict(l=10, r=40, t=40, b=10))
    right.plotly_chart(fig, use_container_width=True)

    # ④ airport and foreign visitors
    st.subheader(t("q4"))
    tour = d["tourism"].set_index("year")["foreign_stays"] if len(d["tourism"]) else pd.Series(dtype=float)
    left, right = st.columns([3, 2])
    fig = go.Figure()
    fig.add_scatter(x=ap.index, y=ap.international, name=t("intl"), mode="lines+markers", line=dict(color=ACCENT, width=2.5))
    if len(tour):
        tt = tour.loc[tour.index >= ap.index.min()]
        fig.add_scatter(x=tt.index, y=tt, name=t("foreign"), mode="lines+markers", line=dict(color=WARN, width=2.5))
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_tickformat=",",
                      legend=dict(orientation="h", y=-0.2))
    left.plotly_chart(fig, use_container_width=True)
    fig = go.Figure()
    fig.add_bar(x=ap.index, y=ap.domestic / 1e6, name=t("dom"), marker_color=MUTED)
    fig.add_bar(x=ap.index, y=ap.international / 1e6, name=t("intl"), marker_color=ACCENT)
    fig.update_layout(barmode="stack", height=360, margin=dict(l=10, r=10, t=30, b=10), title=t("airport"),
                      yaxis_title="million" if en else "百万人", legend=dict(orientation="h", y=-0.2))
    right.plotly_chart(fig, use_container_width=True)
    st.caption(t("q4_note"))

    with st.expander(t("data")):
        st.markdown(
            "- **Sources:** 仙台市統計書 「交通・運輸・通信」 (15 editions, 2011–2025) for city buses, subway and JR stations; "
            "仙台市交通局 「乗車人員一覧」 for subway stations; 国土交通省 「空港管理状況調書」 (10 workbooks) for Sendai Airport.\n"
            "- **Fiscal years** run April–March (FY2024 = April 2024–March 2025). The airport is by calendar year.\n"
            "- **Not directly comparable:** the subway total in ① is the transport bureau's ridership figure; the station counts in ③ "
            "are boardings at each station, with transfers at Sendai Station counted separately (excluded here).\n"
            "- **JR:** average daily boardings from FY2007; before that, 仙台 included Shinkansen passengers and the total included unmanned stations.\n"
            "- **Checks (372):** every row's passengers ÷ days = printed daily average; JR stations add up to the total; subway stations add up "
            "to each line; airport boarding + alighting = subtotal and domestic + international = total; overlapping years are compared across "
            "editions and files. Explained exceptions: FY2010 subway (service suspended after the earthquake), FY2016 (the source divides by 366 days), "
            "FY2007 JR (footnote). One revision: a later edition corrected FY2014 JR 仙台 from 84,951 to 82,706 a day."
            if en else
            "- **出典：** 仙台市統計書「交通・運輸・通信」（平成23年版〜令和7年版の15冊）＝市営バス・地下鉄・JR各駅、仙台市交通局「乗車人員一覧」＝地下鉄駅別、"
            "国土交通省「空港管理状況調書」（10ファイル）＝仙台空港。\n"
            "- **年度**は4月〜翌年3月（2024年度＝2024年4月〜2025年3月）。空港は暦年。\n"
            "- **単純比較できない点：** ①の地下鉄は交通局の乗車人員、③の駅別は各駅の乗車人員（仙台駅の乗換人員は除外）。\n"
            "- **JR：** 2007年度以降の1日平均乗車人員。それ以前は仙台駅に新幹線を含み、総数に無人駅を含むため除外。\n"
            "- **検証（372件）：** 乗車人員÷日数＝1日平均、JR各駅の合計＝総数、地下鉄各駅の合計＝路線計、空港の乗客＋降客＝小計・国内＋国際＝合計、"
            "版・ファイル間の重複年を照合。説明のつく例外：2010年度地下鉄（震災による運休）、2016年度（原資料が366日で割っている）、2007年度JR（脚注）。"
            "改訂1件：2014年度JR仙台駅を後の版で84,951→82,706人/日に修正。"
        )
