"""Download mobility data for Sendai: subway, city buses, Sendai Airport.

Like population_download.py, it reads the publishers' own pages and follows their
links, because file locations change every year (wp-content/uploads/2026/10/...):

  subway/     交通局「乗車人員一覧」: boardings per subway station (Excel)
  airport/    国土交通省「空港管理状況調書」暦年・年度別: passengers per airport, 10 years per file (Excel)
  yearbook/   仙台市統計書「交通・運輸・通信」chapter of each edition: city buses, subway,
              JR stations, private buses, taxis, expressway interchanges, airport (Excel)

(The 交通局 事業概要 PDF has longer histories, but its numbers are drawn without a
text layer and can only be read by OCR, which isn't reliable enough to publish.)

Usage:
    python scripts/mobility_download.py
Saves to data/raw/mobility/. Already-downloaded files are skipped.
Fails loudly (non-zero exit) if a page can't be read, a page has no matching links,
or a file isn't the expected type.
"""
from __future__ import annotations

import html
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

OUT = Path(__file__).resolve().parent.parent / "data" / "raw" / "mobility"
UA = {"User-Agent": "sendai-dashboard/0.4 (portfolio project; contact via GitHub)"}
PAUSE = 0.5
MAGIC = {".xlsx": b"PK", ".xlsm": b"PK", ".xls": b"\xd0\xcf\x11\xe0", ".pdf": b"%PDF"}

# (folder, page to read, link text must contain, file extensions)
SOURCES = [
    ("subway", "https://www.kotsu.city.sendai.jp/subway/joushajinin/", "", (".xlsx",)),
    ("airport", "https://www.mlit.go.jp/koku/15_bf_000185.html", "暦年・年度別", (".xlsx", ".xlsm", ".xls")),
]
YEARBOOK_INDEX = "https://www.city.sendai.jp/chosatoke/shise/toke/tokesho/index.html"
YEARBOOK_EDITIONS = 15  # newest editions to fetch; older ones are PDF only


def get(url: str) -> bytes:
    with urlopen(Request(url, headers=UA), timeout=60, context=SSL_CONTEXT) as resp:
        return resp.read()


def links(page_url: str, must_contain: str, exts: tuple[str, ...]) -> list[str]:
    page = get(page_url).decode("utf-8", errors="replace")
    found = []
    for href, text in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I):
        label = re.sub(r"<[^>]+>|\s+", "", html.unescape(text))
        if href.lower().endswith(exts) and must_contain in label:
            found.append(urljoin(page_url, href))
    return list(dict.fromkeys(found))


def fetch(url: str, folder: Path) -> str | None:
    target = folder / url.rsplit("/", 1)[1]
    if target.exists() and target.stat().st_size > 0:
        return None
    try:
        data = get(url)
        if not data.startswith(MAGIC[target.suffix.lower()]):
            raise ValueError(f"not a {target.suffix} file")
        target.write_bytes(data)
        print(f"ok    {folder.name}/{target.name}  {len(data) / 1024:.0f} KB")
        return None
    except Exception as exc:
        print(f"FAIL  {url}: {exc}", file=sys.stderr)
        return url
    finally:
        time.sleep(PAUSE)


def anchors(url: str) -> list[tuple[str, str]]:
    """[(absolute href, visible text)] for every link on a page."""
    page = get(url).decode("utf-8", errors="replace")
    return [(urljoin(url, h), re.sub(r"<[^>]+>|\s+", "", html.unescape(t)))
            for h, t in re.findall(r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>', page, flags=re.S | re.I)]


def yearbook() -> list[str]:
    """Download the 交通・運輸・通信 chapter of the newest yearbook editions.

    Two layouts exist:
      2022 editions on: the edition page links one Excel file for the whole chapter (documents/r7_13.xls)
      2021 and older:   the edition has a chapter page (r03-01/13.html) with one Excel file per table
    Every page also has a sidebar link to the 2020 edition's chapter, so a link only counts if
    it belongs to the edition being read. If two editions come back with identical files,
    the run fails: that would mean the wrong links were followed.
    """
    import hashlib

    failed: list[str] = []
    try:
        editions = [(u, t) for u, t in anchors(YEARBOOK_INDEX) if re.search(r"(令和|平成)\S*年版", t)]
    except Exception as exc:
        print(f"FAIL  page {YEARBOOK_INDEX}: {exc}", file=sys.stderr)
        return [YEARBOOK_INDEX]
    seen: dict[str, str] = {}  # content hash -> edition label
    for k, (edition_url, label) in enumerate(editions[:YEARBOOK_EDITIONS]):
        slug = re.search(r"/([rhs]\d\d-01)", edition_url)
        code = re.match(r"([rhs])(\d\d)", slug.group(1)) if slug else None
        time.sleep(PAUSE)
        try:
            if not slug or not code:
                raise ValueError(f"cannot read edition code from {edition_url}")
            links_here = anchors(edition_url)
            # layout 1: one Excel file for the chapter, named like r7_13.xls / r07_13.xlsx
            prefix = f"{code.group(1)}{int(code.group(2))}_13."
            files = [u for u, t in links_here
                     if u.lower().endswith((".xls", ".xlsx")) and "交通" in t
                     and re.sub(r"^0", "", u.rsplit("/", 1)[1].lower()).startswith(prefix)]
            if not files:
                # layout 2: chapter page inside this edition's own folder
                chapter = next((u for u, t in links_here
                                if f"/{slug.group(1)}/" in u and "交通" in t and "運輸" in t), None)
                if chapter is None:
                    raise ValueError("no 交通・運輸 chapter link for this edition")
                time.sleep(PAUSE)
                files = [u for u, _ in anchors(chapter) if u.lower().endswith((".xls", ".xlsx"))]
            files = list(dict.fromkeys(files))
            if not files:
                raise ValueError("chapter has no Excel files")
        except Exception as exc:
            print(f"{'FAIL' if k == 0 else 'note'}  {label}: {exc}", file=sys.stderr if k == 0 else sys.stdout)
            if k == 0:
                failed.append(edition_url)
            continue
        folder = OUT / "yearbook" / re.sub(r"\W", "", label)
        folder.mkdir(parents=True, exist_ok=True)
        print(f"page  {label}  {len(files)} file(s)")
        failed += [f for u in files if (f := fetch(u, folder))]
        digest = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(folder.iterdir()))).hexdigest()
        if digest in seen:
            print(f"FAIL  {label}: files identical to {seen[digest]} — wrong links followed", file=sys.stderr)
            failed.append(edition_url)
        seen[digest] = label
    return failed


def main() -> int:
    failed: list[str] = []
    for folder_name, page, must, exts in SOURCES:
        folder = OUT / folder_name
        folder.mkdir(parents=True, exist_ok=True)
        try:
            urls = links(page, must, exts)
        except Exception as exc:
            print(f"FAIL  page {page}: {exc}", file=sys.stderr)
            failed.append(page)
            continue
        if not urls:
            print(f"FAIL  page {page}: no matching links (layout changed?)", file=sys.stderr)
            failed.append(page)
            continue
        print(f"page  {page}  {len(urls)} files")
        failed += [f for u in urls if (f := fetch(u, folder))]
    failed += yearbook()
    if failed:
        print(f"\n{len(failed)} failure(s):\n  " + "\n  ".join(failed), file=sys.stderr)
        return 1
    print("\nall mobility downloads ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
