"""Sendai city dashboard (Streamlit, multi-page).

Run:  streamlit run app/dashboard.py
Each page lives in its own module and reads the CSVs its pipeline produces:
  tourism.py     <- scripts/extract.py, longrun.py, crosscheck_excel.py
  population.py  <- scripts/population_extract.py
  mobility.py    <- scripts/mobility_extract.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mobility  # noqa: E402
import population  # noqa: E402
import tourism  # noqa: E402

TITLE = {"ja": "仙台市 都市ダッシュボード", "en": "Sendai City Dashboard"}
INTRO = {
    "ja": "仙台市が公開している統計を集め、検証し、問いに答える形で可視化しています。各ページの「データと注意点」に出典と検証内容を記載しています。",
    "en": "Statistics published by the City of Sendai, collected, checked against each other, and organised around the questions a city planner would ask. Every page lists its sources and checks under 'Data and caveats'.",
}
PAGES = {
    "home": {"ja": "ホーム", "en": "Home"},
    "population": {"ja": "人口", "en": "Population"},
    "mobility": {"ja": "交通", "en": "Mobility"},
    "tourism": {"ja": "観光", "en": "Tourism"},
}


def home() -> None:
    lang = st.session_state.get("lang", "ja")
    st.title(TITLE[lang])
    st.write(INTRO[lang])
    pop = population.load()["pop_monthly"]
    city = pop[pop.area_jp == "仙台市"].set_index("date")["population"]
    tour = tourism.load()["annual"].set_index("year")
    y = tour.index.max()
    ap = mobility.load()["airport"].set_index("year")
    c = st.columns(4)
    c[0].metric({"ja": "人口", "en": "Population"}[lang] + f" ({city.index[-1]:%Y-%m})", f"{city.iloc[-1]:,.0f}",
                f"{city.iloc[-1] - city.max():+,.0f} " + {"ja": "（ピーク比）", "en": "vs peak"}[lang], delta_color="off")
    c[1].metric({"ja": "観光客入込数", "en": "Tourist visits"}[lang] + f" ({y})", f"{tour.loc[y, 'visitors']:,.0f}")
    c[3].metric({"ja": "仙台空港 旅客数", "en": "Sendai Airport passengers"}[lang] + f" ({ap.index.max()})",
                f"{ap.total.iloc[-1]:,.0f}", f"{ap.total.iloc[-1] / ap.total.loc[2019] * 100:.0f}% " + {"ja": "2019年比", "en": "of 2019"}[lang],
                delta_color="off")
    c[2].metric({"ja": "外国人宿泊者数", "en": "Foreign overnight stays"}[lang] + f" ({y})", f"{tour.loc[y, 'foreign_stays']:,.0f}",
                f"{tour.loc[y, 'foreign_stays'] / tour.loc[2019, 'foreign_stays'] * 100:.0f}% " + {"ja": "2019年比", "en": "of 2019"}[lang],
                delta_color="off")
    st.markdown(
        {"ja": "**ページ**\n- **人口**：どの区で人口減少・高齢化が進み、2070年までにどう変わるか\n- **交通**：コロナ後、市民の移動と空の玄関口はどこまで戻ったか\n- **観光**：コロナ前からどこまで回復し、インバウンドの構成はどう変わったか",
         "en": "**Pages**\n- **Population**: which wards are shrinking and ageing, and how that changes by 2070\n- **Mobility**: how far travel in the city and through the airport has come back since COVID\n- **Tourism**: how far tourism has recovered, and how the mix of foreign visitors changed"}[lang])


def main() -> None:
    st.set_page_config(page_title="Sendai City Dashboard", page_icon="📊", layout="wide")
    choice = st.sidebar.radio("Language / 言語", ["日本語", "English"], horizontal=True)
    st.session_state["lang"] = lang = "ja" if choice == "日本語" else "en"
    nav = st.navigation([
        st.Page(home, title=PAGES["home"][lang], icon="🏠", default=True),
        st.Page(population.render, title=PAGES["population"][lang], icon="👥", url_path="population"),
        st.Page(mobility.render, title=PAGES["mobility"][lang], icon="🚇", url_path="mobility"),
        st.Page(tourism.render, title=PAGES["tourism"][lang], icon="🧳", url_path="tourism"),
    ])
    nav.run()


main()
