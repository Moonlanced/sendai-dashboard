"""Download City of Sendai population statistics (統計情報せんだい 人口).

Reads the city's own index pages and downloads every Excel file linked from them,
so irregular file names (r0701_1.xlsx, h1501.xls, 5-years_h2804.xlsx ...) are
picked up without hard-coding:

  monthly/     推計人口: monthly population and movement, 1999 onward
  age5/        5歳階級別人口: population by 5-year age group, 3x a year, 2003 onward
  projection/  将来人口推計: projections 2020–2070, city, wards, sub-offices, school districts

Usage:
    python scripts/population_download.py
Saves to data/raw/population/. Already-downloaded files are skipped.
Fails loudly (non-zero exit) if a page or file can't be fetched, or a page has no files.
"""
from __future__ import annotations

import re
import ssl
import sys
import time
from pathlib import Path
from urllib.parse import urljoin
from urllib.request import Request, urlopen

try:  # verify HTTPS against the OS trust store, like a browser (see download.py)
    import truststore

    SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

SITE = "https://www.city.sendai.jp/chosatoke/shise/toke/"
OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "population"
UA = {"User-Agent": "sendai-dashboard/0.3 (portfolio project; contact via GitHub)"}
PAUSE = 0.5  # seconds between requests, to be polite to the city's server

# yearly index pages for the monthly series: 平成11–30, 平成31/令和元, 令和2–8
MONTHLY_PAGES = (
    [f"jinko/suikei_h{n:02d}.html" for n in range(11, 32)]
    + [f"jinko/suikei_r{n:02d}.html" for n in range(2, 9)]
)
GROUPS: dict[str, list[str]] = {
    "monthly": MONTHLY_PAGES,
    "age5": ["jinko/nenre.html"],
    "projection": ["shoraijinko.html"],
}
MAGIC = {".xlsx": b"PK", ".xls": b"\xd0\xcf\x11\xe0"}


def get(url: str) -> bytes:
    with urlopen(Request(url, headers=UA), timeout=60, context=SSL_CONTEXT) as resp:
        return resp.read()


def links(page_url: str) -> list[str]:
    html = get(page_url).decode("utf-8", errors="replace")
    hrefs = re.findall(r'href="([^"]+\.xlsx?)"', html, flags=re.IGNORECASE)
    return list(dict.fromkeys(urljoin(page_url, h) for h in hrefs))  # unique, in page order


def main() -> int:
    failed: list[str] = []
    counts: dict[str, int] = {}
    for group, pages in GROUPS.items():
        folder = OUT / group
        folder.mkdir(parents=True, exist_ok=True)
        counts[group] = 0
        for page in pages:
            page_url = SITE + page
            try:
                files = links(page_url)
            except Exception as exc:
                print(f"FAIL  page {page_url}: {exc}", file=sys.stderr)
                failed.append(page)
                continue
            if not files:
                print(f"FAIL  page {page_url}: no Excel links found (layout changed?)", file=sys.stderr)
                failed.append(page)
                continue
            print(f"page  {page:<28} {len(files)} files")
            time.sleep(PAUSE)
            for url in files:
                target = folder / url.rsplit("/", 1)[1]
                counts[group] += 1
                if target.exists() and target.stat().st_size > 0:
                    continue
                try:
                    data = get(url)
                    if not data.startswith(MAGIC[target.suffix.lower()]):
                        raise ValueError(f"not a {target.suffix} file")
                    target.write_bytes(data)
                    print(f"ok    {group}/{target.name}")
                except Exception as exc:
                    print(f"FAIL  {url}: {exc}", file=sys.stderr)
                    failed.append(url)
                time.sleep(PAUSE)

    print("\n" + ", ".join(f"{g}: {n} files" for g, n in counts.items()))
    if failed:
        print(f"{len(failed)} failure(s):\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    print("all population downloads ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
