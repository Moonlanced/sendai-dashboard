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

## Milestone: Disaster preparedness (防災) ✅
- [x] Shelters and emergency evacuation sites from GSI, with per-hazard designations, on a map
- [x] Sites per 10,000 residents by ward, hazard × ward grid, tsunami site types
- [x] Ward boundaries (国土数値情報 N03) to assign the expressway staircases and draw ward areas
- [ ] Compare Sendai with other Miyagi municipalities (04000 files already downloaded)
- [ ] Tsunami inundation area overlay (宮城県 津波浸水想定)

## Milestone: Land prices (地価) ✅
- [x] 地価公示 2026 with history to 1983; 2016 and 2006 editions as cross-checks
- [x] Chained index by use and ward, map, ward comparison with population, distance to station, risers and fallers
- [ ] 都道府県地価調査 (July survey, L02) for twice-yearly points
- [ ] Link to subway station ridership (Tōzai line opening, 2015)

## Milestone: Later
- [ ] Jobs and industry (有効求人倍率, 経済センサス)
- [ ] Monthly seasonality for tourism (観光庁 宿泊旅行統計調査)
- [ ] Unit tests for both parsers using the downloaded files as fixtures
