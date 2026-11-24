# Data dictionary

**Tourism** files are in `data/processed/`; **population** files in `data/processed/population/` (see the end of this page).

All files in `data/processed/` are produced by `scripts/extract.py` from the City of Sendai 「仙台市観光統計基礎データ」 PDFs (editions H23–R7, covering 2007–2025), except longrun.csv (scripts/longrun.py) and excel_crosscheck.csv (scripts/crosscheck_excel.py). Values are counts of people unless noted.

## annual.csv
| Field | Meaning | Source table | Notes |
|---|---|---|---|
| year | Calendar year | – | 2007–2025 |
| visitors | 観光客入込数 (tourist visits, whole city) | §1 | Counts visits, not unique people |
| overnight_stays | 宿泊者数 (overnight guests, whole city) | §2 計 | Excludes 民泊 (private lodging) |
| foreign_stays | 外国人宿泊者数 | §3 国別 総計 | Actual figures only, estimates excluded |

## stays_by_district.csv
| Field | Meaning |
|---|---|
| year | Calendar year |
| district_jp / district_en | 旧仙台地区, 泉地区, 秋保地区, 宮城地区 (宮城地区 includes the 作並 hot-spring area) |
| stays | Overnight guests in that district |

Check: the four districts add up to the published 計 for every year. The 2014 and 2015 editions print only the city total; their district figures come from later editions.

## foreign_by_country.csv
| Field | Meaning |
|---|---|
| year | 2006–2025 |
| country_jp / country_en | 13 categories as printed, e.g. 中国（台湾・香港除く）, ヨーロッパ, その他・不明 |
| stays | Foreign overnight guests from that country or region |

Checks: categories add up to 総計, and 総計 equals the §3 仙台市 total in the same report.
Caveat: その他・不明 is large in some years (27% in 2019, 9% in 2025), so compare shares with it excluded.

## origin_share.csv
| Field | Meaning |
|---|---|
| year | 2010–2025 (each report gives its last two years) |
| origin_jp / origin_en | Where guests live: 宮城県内, 北海道, 東北地方, 関東地方, 北陸・中部, 近畿, 中国・四国, 九州・沖縄, 外国人 |
| share_pct | Share of guests in %, unknown excluded |

Check: shares add up to 100 (±0.3 for rounding).

## revisions.csv
Every value where a newer report changed a figure published in an older one (table, key, old value and report, new value and report). The newest report is used. Currently empty: all overlapping years agree.

## quality_flags.csv
Every printed 前年比 (year-on-year %) that doesn't match the ratio of the printed counts (report, table, year, printed %, calculated %). These are typos in the source; the counts are used as published. Currently five: R7 visitors 2024 (131.3% printed, 103.8% calculated), and four district values in H28 for 2014 printed as ratios (e.g. 0.9) instead of percentages (92.6).

## longrun.csv
| Field | Meaning |
|---|---|
| year | 1982–2025 |
| visitors / overnight_stays | City totals from the city's trend workbooks (irikomi.xlsx, syukuhaku.xlsx) |
| note | The city's own note for that year (events, the earthquake, COVID) |
| method_break | Set in 1996 and 2010, when the counting method changed |

Check: equals annual.csv for every overlapping year (2007–2025), or the run fails.

## excel_crosscheck.csv
For each report: how many of the values extracted from its PDF for its own year were found in the city's Excel version (values_found / values_checked). Any missing value fails the run. Currently 292 of 292.

---

# Population (`data/processed/population/`, from `scripts/population_extract.py`)

Areas: 仙台市 (city), the five wards (青葉区, 宮城野区, 若林区, 太白区, 泉区), and two sub-areas, 宮城総合支所 (part of 青葉区) and 秋保総合支所 (part of 太白区). Sub-areas are never added to the city total. Every file has `area_jp` and `area_en`.

## pop_monthly.csv
| Field | Meaning |
|---|---|
| date | 1st of the month, 1999-01-01 to latest |
| population, men, women | 推計人口: the census figure carried forward with monthly registry changes; re-based on each census (October 2005, 2010, 2015, 2020, 2025) |
| households | Reference only: households are defined differently in the census and the registry |

Checks: every file yields the city and all 5 wards; total = men + women; wards add up to the city; no month missing or duplicated.

## vitals_monthly.csv
| Field | Meaning |
|---|---|
| month | The month the births and deaths happened (each file reports the previous month) |
| births, deaths | Japanese + foreign residents where the file reports both (foreign residents from 2010) |

Checks: wards add up to the city for births and for deaths; summed per year they equal the yearly table printed in the newest file (2021–2025).

## age_groups.csv / age3.csv
| Field | Meaning |
|---|---|
| date | 2003-04-01 to latest, 2–3 dates a year |
| age_group | 0~4 … 95~99, 100歳以上 (age_groups.csv) |
| total, age_0_14, age_15_64, age_65_plus | age3.csv, derived from the 5-year groups |

Source: the resident registry (住民基本台帳), so totals differ slightly from 推計人口. Foreign residents included from July 2012. City and wards only (no sub-areas). Checks: groups add up to each total; wards add up to the city.

## projection.csv
| Field | Meaning |
|---|---|
| year | 2020 (census) to 2070 |
| total, age_0_14, age_15_64, age_65_plus | The city's projection (令和4年推計). Age groups are summed from the single-year ages, not taken from the city's summary table (which has an error in 2022, see checks.csv) |
| kind | census (2020) or projection |

## checks.csv
Every check run on every file, with passed True/False and a detail. Rows with passed=False are errors found in the source: currently four (Miyagino's natural change in the January 2010 file; the same 2022 under-15 figure printed for three wards in the projection summary table).

---

# Mobility (`data/processed/mobility/`, from `scripts/mobility_extract.py`)

## transit_fy.csv
| Field | Meaning |
|---|---|
| fiscal_year | April–March; FY2024 = April 2024–March 2025. FY2006–latest |
| mode | bus (市営バス, including chartered) or subway (地下鉄, both lines) |
| passengers | 乗車人員 for the year, from the 仙台市統計書 table 「市営バス及び地下鉄」 |
| source_edition | The newest yearbook edition the value was taken from |

Check: passengers ÷ days in the fiscal year = the printed daily average (±1). Exceptions explained in checks.csv.

## jr_stations_fy.csv
| Field | Meaning |
|---|---|
| fiscal_year | FY2007–latest (earlier years use different definitions) |
| station | Every JR station in Sendai, 総数 (total, excluding Shinkansen), and 新幹線（仙台駅） (Shinkansen at Sendai Station, listed separately) |
| daily_boardings | Average daily boardings |

Check: stations add up to 総数 (FY2008 on; the FY2007 total includes unmanned stations, per the table's footnote).

## subway_stations_fy.csv
| Field | Meaning |
|---|---|
| fiscal_year, line, station | FY2007–latest, 南北線 / 東西線 (from December 2015), station; 仙台（乗換） = transfers at Sendai |
| boardings | Boardings for the year, from 交通局 「乗車人員一覧」 |

Check: stations (with transfers) add up to each line's 総数. Not directly comparable with transit_fy.csv, which uses the bureau's ridership figure.

## airport_cy.csv
| Field | Meaning |
|---|---|
| year | Calendar year, 2007–latest |
| domestic, international, total | Boarding + alighting passengers at Sendai Airport. International includes Japanese residents travelling abroad |

Source: 国土交通省 「空港管理状況調書」 暦年・年度別 (10-year workbooks). Checks: boarding + alighting (+ transit) = subtotal; domestic + international = total; overlapping years compared across workbooks.

## revisions.csv / checks.csv
As for population: every value a newer edition changed, and every check with passed True / False / "explained" plus the reason.
