"""Download land prices and ward boundaries for Sendai from 国土数値情報 (MLIT).

  landprice/   地価公示 L01, Miyagi (04). The 2026 file holds every current survey point with
               its price for every year 1984–2026. The 2016 and 2006 files are kept to
               cross-check those history columns against what was published at the time.
  boundaries/  行政区域 N03, Miyagi, 1 Jan 2025: municipality and ward polygons.

Licence: CC BY 4.0 (出典：国土交通省「国土数値情報」).

Usage:
    python scripts/landprice_download.py
Saves the zips to data/raw/landprice/ and data/raw/boundaries/ and unpacks them.
Fails loudly (non-zero exit) if a file can't be fetched or isn't a zip.
"""
from __future__ import annotations

import ssl
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

try:  # verify HTTPS against the OS trust store, like a browser (see download.py)
    import truststore

    SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
BASE = "https://nlftp.mlit.go.jp/ksj/gml/data/"
FILES = [
    ("landprice", "L01/L01-26/L01-26_04_GML.zip"),
    ("landprice", "L01/L01-16/L01-16_04_GML.zip"),
    ("landprice", "L01/L01-06/L01-06_04_GML.zip"),
    ("boundaries", "N03/N03-2025/N03-20250101_04_GML.zip"),
]
UA = {"User-Agent": "sendai-dashboard/0.5 (portfolio project; contact via GitHub)"}


def main() -> int:
    failed = []
    for folder, path in FILES:
        out = RAW / folder
        out.mkdir(parents=True, exist_ok=True)
        target = out / path.rsplit("/", 1)[1]
        try:
            if not (target.exists() and target.stat().st_size > 0):
                with urlopen(Request(BASE + path, headers=UA), timeout=120, context=SSL_CONTEXT) as resp:
                    data = resp.read()
                if not data.startswith(b"PK"):
                    raise ValueError("not a zip file")
                target.write_bytes(data)
                print(f"ok    {folder}/{target.name}  {len(data) / 1024:.0f} KB")
                time.sleep(0.5)
            else:
                print(f"skip  {folder}/{target.name}")
            unpack = out / target.stem
            if not unpack.exists():
                with zipfile.ZipFile(target) as z:
                    z.extractall(unpack)
        except Exception as exc:
            print(f"FAIL  {BASE + path}: {exc}", file=sys.stderr)
            failed.append(path)
    if failed:
        print(f"\n{len(failed)} failure(s)", file=sys.stderr)
        return 1
    print("\nall land-price and boundary downloads ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
