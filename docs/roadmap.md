# Roadmap

Create these as GitHub Issues, one Milestone per theme.

## Milestone: Tourism ✅
- [x] Persona, questions and KPIs (requirements.md)
- [x] Extract 15 annual reports (2007–2025) with total checks and a cross-report revision log
- [x] Recalculate printed year-on-year % and log source errors
- [x] Long-run chart from 1982 with method-change markers
- [x] Cross-check against the city's Excel files
- [x] Insights write-up

## Milestone: Population ✅
- [x] Crawl the city's index pages for ~400 files (monthly 1999–, age 2003–, projection –2070)
- [x] Structure-based parsing across 27 years of layout changes
- [x] Checks: wards sum to city, total = men + women, yearly births/deaths match the city's table
- [x] Multi-page app with a home page
- [x] Insights write-up

## Milestone: Mobility ✅
- [x] City bus and subway ridership FY2006– from 15 yearbook editions, matched by table title
- [x] JR stations and subway stations, FY2007–
- [x] Sendai Airport passengers 2007– from 10 ministry workbooks, cross-checked
- [x] Link international passengers to foreign overnight stays on the tourism page
- [ ] Taxis, private buses (宮城交通) and expressway interchanges (also in the yearbook)
- [ ] Monthly ridership for COVID detail

## Milestone: Disaster preparedness (防災)
- [ ] Shelters and tsunami evacuation areas from the city's open data
- [ ] Shelter capacity per ward against ward population (map)

## Milestone: Later
- [ ] Land prices (国交省 不動産情報ライブラリ API)
- [ ] Jobs and industry (有効求人倍率, 経済センサス)
- [ ] Monthly seasonality for tourism (観光庁 宿泊旅行統計調査)
- [ ] Unit tests for both parsers using the downloaded files as fixtures
