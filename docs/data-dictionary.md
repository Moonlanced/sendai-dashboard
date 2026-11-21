# Data dictionary

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
