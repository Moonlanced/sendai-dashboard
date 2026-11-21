from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

DATA = Path(__file__).resolve().parent.parent / "data" / "processed"
BASE = 2019
ACCENT, MUTED, WARN = "#1f6f5c", "#9aa6a0", "#b4651e"

T = {
    "title": {"ja": "仙台市 観光回復ダッシュボード", "en": "Sendai Tourism Recovery Dashboard"},
    "sub": {
        "ja": "仙台市観光統計（年次PDF）を構造化し、コロナ前（2019年）比の回復とインバウンド構成の変化を可視化",
        "en": "City of Sendai annual tourism statistics, extracted from PDF: recovery against 2019 and how the visitor mix changed",
    },
    "year": {"ja": "対象年", "en": "Year"},
    "visitors": {"ja": "観光客入込数", "en": "Visitors"},
    "stays": {"ja": "宿泊者数", "en": "Overnight stays"},
    "foreign": {"ja": "外国人宿泊者数", "en": "Foreign overnight stays"},
    "vs": {"ja": f"{BASE}年比", "en": f"vs {BASE}"},
    "q0": {"ja": "1982年からの推移", "en": "Since 1982"},
    "q0_note": {
        "ja": "点線：集計方法の変更（1996年 宿泊者数、2010年 国の共通基準導入）。前後の数値は単純比較できません。点にカーソルを合わせると市の注記を表示。",
        "en": "Dotted lines: changes in how the city counts (1996 overnight stays, 2010 national standard). Values before and after aren't directly comparable. Hover a point for the city's note on that year.",
    },
    "q1": {"ja": "① 回復度：2019年＝100", "en": "① Recovery: 2019 = 100"},
    "q1_note": {
        "ja": "入込数は2019年比120%で横ばい、宿泊は緩やかに伸び続けている。入込に対する宿泊の比率は一度低下した後、持ち直しつつある",
        "en": "Visits have levelled off at 120% of 2019 while overnight stays keep rising slowly; stays per visit dipped and are now recovering",
    },
    "district": {"ja": "地区別 宿泊者数の回復率（2019年比）", "en": "Overnight-stay recovery by district (vs 2019)"},
    "q2": {"ja": "② インバウンドの国・地域構成", "en": "② Where foreign guests come from"},
    "share": {"ja": "構成比（不明を除く）", "en": "Share (excluding unknown)"},
    "growth": {"ja": "2019年比の伸び（倍）", "en": "Growth vs 2019 (×)"},
    "unknown_note": {
        "ja": "注意：2019年は「その他・不明」が27%を占めるため、構成比は不明分を除いて比較しています。",
        "en": "Caution: 'Other / unknown' was 27% of foreign stays in 2019, so shares here exclude it.",
    },
    "q3": {"ja": "③ 宿泊客の居住地構成", "en": "③ Where overnight guests live"},
    "q3_note": {
        "ja": "観光戦略課調査（不明分除く）。宮城県内の比率が低下し、海外比率が上昇。",
        "en": "City survey, unknown excluded. Share from within Miyagi falls while overseas rises.",
    },
    "data": {"ja": "データと注意点", "en": "Data and caveats"},
    "source": {
        "ja": "出典：仙台市観光戦略課「仙台市観光統計基礎データ」平成23年〜令和7年版、および「観光客入込数・宿泊者数の推移」を加工して作成",
        "en": "Source: City of Sendai, 仙台市観光統計基礎データ (2011–2025 editions) and its 1982– trend series, processed by the author",
    },
}


def t(key: str) -> str:
    return T[key][st.session_state.get("lang", "ja")]


@st.cache_data
def load() -> dict[str, pd.DataFrame]:
    return {
        "annual": pd.read_csv(DATA / "annual.csv"),
        "district": pd.read_csv(DATA / "stays_by_district.csv"),
        "country": pd.read_csv(DATA / "foreign_by_country.csv"),
        "origin": pd.read_csv(DATA / "origin_share.csv"),
        "longrun": pd.read_csv(DATA / "longrun.csv").fillna(""),
    }


def main() -> None:
    st.set_page_config(page_title="Sendai Tourism", page_icon="📊", layout="wide")
    lang = st.sidebar.radio("Language / 言語", ["日本語", "English"], horizontal=True)
    st.session_state["lang"] = "ja" if lang == "日本語" else "en"
    en = st.session_state["lang"] == "en"

    d = load()
    annual = d["annual"].set_index("year")
    years = [y for y in annual.index if y >= BASE + 1]
    year = st.sidebar.selectbox(t("year"), years[::-1])

    st.title(t("title"))
    st.caption(t("sub"))

    # KPI row
    cols = st.columns(3)
    for col, key, field in zip(cols, ["visitors", "stays", "foreign"], ["visitors", "overnight_stays", "foreign_stays"]):
        now, base = annual.loc[year, field], annual.loc[BASE, field]
        col.metric(t(key), f"{now:,.0f}", f"{now / base * 100:.0f}% {t('vs')}", delta_color="off")

    # Long-run headline
    st.subheader(t("q0"))
    lr = d["longrun"]
    fig = go.Figure()
    for field, key, color in [("visitors", "visitors", ACCENT), ("overnight_stays", "stays", MUTED)]:
        fig.add_scatter(x=lr["year"], y=lr[field] / 1e6, name=t(key), mode="lines+markers", marker=dict(size=4),
                        line=dict(color=color, width=2.5), customdata=lr["note"],
                        hovertemplate="%{x}: %{y:.2f}M<br>%{customdata}<extra></extra>")
    for y in lr.loc[lr["method_break"] != "", "year"]:
        fig.add_vline(x=y - 0.5, line_dash="dot", line_color=WARN)
    for y, label, ax, ay in [(2011, "3.11", 0, 40), (2020, "COVID-19", -55, 0)]:
        fig.add_annotation(x=y, y=float(lr.loc[lr.year == y, "visitors"].iloc[0]) / 1e6, text=label,
                           showarrow=True, arrowhead=0, ax=ax, ay=ay, font=dict(size=11),
                           bgcolor="rgba(255,255,255,0.85)")
    fig.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="million" if en else "百万人",
                      legend=dict(orientation="h", y=-0.15))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q0_note"))

    # Q1 recovery index
    st.subheader(t("q1"))
    idx = (annual[["visitors", "overnight_stays", "foreign_stays"]] / annual.loc[BASE] * 100)
    fig = go.Figure()
    for field, key, color in [("visitors", "visitors", ACCENT), ("overnight_stays", "stays", MUTED), ("foreign_stays", "foreign", WARN)]:
        fig.add_scatter(x=idx.index, y=idx[field], name=t(key), mode="lines+markers", line=dict(color=color, width=2.5))
    fig.add_hline(y=100, line_dash="dot", line_color=MUTED)
    fig.update_layout(height=360, margin=dict(l=10, r=10, t=10, b=10), yaxis_title="2019 = 100", legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q1_note"))

    dist = d["district"].pivot(index="district_en" if en else "district_jp", columns="year", values="stays")
    rec = (dist[year] / dist[BASE] * 100).sort_values()
    fig = px.bar(rec, orientation="h", text=rec.round(0).astype(int).astype(str) + "%")
    fig.update_traces(marker_color=[WARN if v < 100 else ACCENT for v in rec])
    fig.add_vline(x=100, line_dash="dot", line_color=MUTED)
    fig.update_layout(height=260, showlegend=False, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="%", yaxis_title=None, title=t("district"))
    st.plotly_chart(fig, use_container_width=True)

    # Q2 foreign markets
    st.subheader(t("q2"))
    c = d["country"]
    name = "country_en" if en else "country_jp"
    p = c.pivot(index=name, columns="year", values="stays")
    unknown = "Other / unknown" if en else "その他・不明"
    known = p.drop(index=unknown)
    shares = known[[BASE, year]] / known[[BASE, year]].sum() * 100
    shares = shares.sort_values(year)
    left, right = st.columns(2)
    fig = go.Figure()
    fig.add_bar(y=shares.index, x=shares[BASE], name=str(BASE), orientation="h", marker_color=MUTED)
    fig.add_bar(y=shares.index, x=shares[year], name=str(year), orientation="h", marker_color=ACCENT)
    fig.update_layout(barmode="group", height=460, title=t("share"), xaxis_title="%", margin=dict(l=10, r=10, t=40, b=10),
                      legend=dict(orientation="h", y=-0.12))
    left.plotly_chart(fig, use_container_width=True)
    growth = (known[year] / known[BASE]).sort_values()
    fig = px.bar(growth, orientation="h", text=growth.map(lambda v: f"{v:.1f}×"))
    fig.update_traces(marker_color=[WARN if v < 1.5 else ACCENT for v in growth], textposition="outside", cliponaxis=False)
    fig.add_vline(x=1, line_dash="dot", line_color=MUTED)
    fig.update_layout(height=460, showlegend=False, title=t("growth"), xaxis_title="×", yaxis_title=None, margin=dict(l=10, r=10, t=40, b=10))
    right.plotly_chart(fig, use_container_width=True)
    st.info(t("unknown_note"))

    # Q3 domestic origin
    st.subheader(t("q3"))
    o = d["origin"]
    oname = "origin_en" if en else "origin_jp"
    order = o[o.year == o.year.max()].sort_values("share_pct", ascending=False)[oname].tolist()
    fig = px.area(o, x="year", y="share_pct", color=oname, category_orders={oname: order},
                  color_discrete_sequence=px.colors.qualitative.Safe)
    fig.update_layout(height=380, yaxis_title="%", xaxis_title=None, legend_title=None, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(t("q3_note"))

    with st.expander(t("data")):
        st.markdown(t("source"))
        st.markdown(
            "- 2007–2025 annual figures from 15 reports; foreign guests by country 2006–2025; guest origin 2010–2025; long-run totals 1982–2025.\n"
            "- Every table is checked against its published total during extraction; overlapping years agree across all 15 reports, all 292 report-year values match the city's Excel files, and the 1982– series matches for every overlapping year.\n"
            "- Five errors found in the source and logged (quality_flags.csv), e.g. the 2025 edition prints 2024 visitors as +31.3% on the year; its own numbers give +3.8%.\n"
            "- Counting methods changed in 1996 and 2010, so long-run comparisons across those years are indicative only.\n"
            "- 2020–2022 are pandemic years. Foreign-guest counts are actual figures only (推計値は含まず).\n"
            "- Descriptive only: these numbers do not show *why* anything changed."
            if en else
            "- 年次データ2007〜2025年（15冊）、国・地域別外国人宿泊者2006〜2025年、居住地別2010〜2025年、長期推移1982〜2025年。\n"
            "- 抽出時に各表の合計値と照合済み。15冊の報告書間で重複年の数値はすべて一致。Excel版とも292項目すべて一致、1982年からの長期推移とも重複年はすべて一致。\n"
            "- 原資料の誤記を5件検出し記録（quality_flags.csv）。例：令和7年版で2024年の入込数の前年比が131.3%と記載（実数からの計算値は103.8%）。\n"
            "- 1996年・2010年に集計方法が変更されており、その前後の比較は参考値。\n"
            "- 2020〜2022年はコロナ禍の影響を受けた年。外国人宿泊者数は実数値のみ（推計値は含まず）。\n"
            "- 記述統計のみで、増減の要因（因果）は示していません。"
        )
        st.download_button("annual.csv", (DATA / "annual.csv").read_bytes(), "annual.csv")


if __name__ == "__main__":
    main()
