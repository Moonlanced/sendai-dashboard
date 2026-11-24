# Decision log

| # | Date | Decision | Why | Alternatives considered |
|---|---|---|---|---|
| 1 | 2026-11-21 | Use the City of Sendai annual 観光統計 reports as the primary source | It's the only source with Sendai-level foreign guests by country and domestic visitors by origin region | Prefecture-level open data CSVs (no origin breakdown) |
| 2 | 2026-11-21 | Parse the PDF editions with code | The PDF is the official published version and has the same layout every year, so one parser covers 8 editions; the Excel versions exist too and are a fallback | Copying by hand; the per-year Excel files (layout differs by year) |
| 3 | 2026-11-21 | Add monthly seasonality from 観光庁 宿泊旅行統計調査 (Miyagi) | Sendai's reports are annual only | Drop the seasonality question |
| 4 | 2026-11-21 | Descriptive statistics only, no causal claims | Data doesn't support attribution; avoids misleading a decision-maker | Regression on promotion spend (no spend data) |
| 5 | 2026-11-21 | Fail loudly on any extraction mismatch | A silently wrong number in a dashboard is worse than no number | Log a warning and continue |
| 6 | 2026-11-21 | Recalculate every printed 前年比 and log mismatches instead of failing | A wrong % in the source isn't a reason to stop; the counts are correct and the typo should be reported, not hidden | Fail the run; ignore the printed % |
| 7 | 2026-11-21 | Check the PDF extraction against the city's Excel files by value lookup, not by parsing each workbook | Workbook layouts change between years; looking up each extracted value is layout-independent and still catches any mismatch | Write 15 Excel parsers |
| 8 | 2026-11-21 | Show the 1982– series but mark the 1996 and 2010 method changes | The long view is the most useful context, but a reader must not compare across the breaks as if like for like | Start the chart in 2010 |
| 9 | 2026-11-22 | Find files by reading the city's index pages, not a fixed list | ~400 population files with irregular names (r0701_1.xlsx, 5-years_h2804.xlsx); new months are picked up automatically | Hard-code every file name |
| 10 | 2026-11-22 | Identify columns by arithmetic (total = men + women; natural = births − deaths) and block layout by its header text | Column order changed over 27 years; position-based parsing would silently read the wrong column | One parser per layout era |
| 11 | 2026-11-22 | Build projection age groups from the single-year ages | The city's summary table has an error (same value for three wards in 2022); the single-year table is the base data and adds up | Use the summary table as published |
| 12 | 2026-11-22 | One multi-page app (app/dashboard.py) with a module per theme | Keeps the deployed entry point unchanged while adding themes; each page owns its data and text | Separate apps per theme |
| 13 | 2026-11-24 | Don't use the 交通局 事業概要 PDF despite its longer history | Its numbers are drawn without a text layer; OCR got most rows wrong, and guessed numbers don't belong in a verified dashboard | OCR with manual correction |
| 14 | 2026-11-24 | Find yearbook tables by their titles, not by file or sheet name | Files were named five different ways between 2011 and 2025; titles stayed the same | One rule per naming era |
| 15 | 2026-11-24 | Keep explained exceptions in checks.csv as 'explained' with the reason | A check that's waved through silently hides information; one that fails forever hides real problems among known ones | Fail the run; drop the check |
| 16 | 2026-11-24 | Use GSI's national evacuation-site data, downloaded by hand | The city publishes only names and addresses on HTML pages; GSI has coordinates and per-hazard designations. Its consent step is the user's to click | Scrape the city's HTML pages |
| 17 | 2026-11-24 | Show GSI's three usage notes prominently on the page | GSI's terms ask that anyone passing the data on makes sure those notes reach the reader; a disaster page also mustn't look like an official guide | A line in the caveats |
| 18 | 2026-11-24 | Leave sites without a ward in their address unassigned | Assigning a ward by guesswork would put a false number into a per-ward comparison | Nearest-neighbour ward assignment |
