from __future__ import annotations

import ssl
import sys
from pathlib import Path
from urllib.request import Request, urlopen

# Verify HTTPS against the operating system's trust store (like a browser does).
# Python's bundled certificates often fail on macOS/Windows with
# "CERTIFICATE_VERIFY_FAILED: unable to get local issuer certificate".
# Verification is never switched off.
try:
    import truststore

    SSL_CONTEXT = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
except ImportError:
    try:
        import certifi

        SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        SSL_CONTEXT = ssl.create_default_context()

BASE = "https://www.city.sendai.jp/kankokikaku/toukei/documents/"
RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

# Annual reports parsed by scripts/extract.py: label -> file name on the city site
REPORTS: dict[str, str] = {
    "H23": "heisei23date.pdf",
    "H24": "heisei24date.pdf",
    "H25": "heisei25date.pdf",
    "H26": "heisei26deta.pdf",
    "H27": "heisei27.pdf",
    "H28": "heisei28.pdf",
    "H29": "h29kankoutoukeidata4_02.pdf",
    "H30": "h30kankoutoukeidata6.pdf",
    "R1": "r1kankoutoukeidata3.pdf",
    "R2": "r2kankoutoukeidata3.pdf",
    "R3": "r3kankoutoukeidata.pdf",
    "R4": "r4kankoutoukeidata2.pdf",
    "R5": "r5toukeidata2.pdf",
    "R6": "r6kankoutoukei_ver1_3.pdf",
    "R7": "r7kankoutoukei_ver1.pdf",
}

# Everything else on the page, saved under data/raw/archive/ with --all
ARCHIVE: dict[str, str] = {
    # Excel versions of every annual report
    "H23.xlsx": "h23kankoukisodate.xlsx",
    "H24.xlsx": "h24kankoukisodate.xlsx",
    "H25.xlsx": "h25kankoukisodate.xlsx",
    "H26.xlsx": "h26kankoukisodate.xlsx",
    "H27.xlsx": "h27kankoukisodate.xlsx",
    "H28.xlsx": "h28kankoukisodate.xlsx",
    "H29.xls": "h29kankoukisodate.xls",
    "H30.xls": "h30kankoukisodate.xls",
    "R1.xls": "r1kankoukisodate.xls",
    "R2.xlsx": "r2kankoukisodate.xlsx",
    "R3.xlsx": "r3kankoukisodate.xlsx",
    "R4.xlsx": "r4kankoukisodate.xlsx",
    "R5.xlsx": "r5kankoukisodate.xlsx",
    "R6.xlsx": "r6kankoukisodate.xlsx",
    "R7.xlsx": "r7kankoukisodate.xlsx",
    # long-run series since 1982 (昭和57年)
    "longrun_visitors.xlsx": "irikomi.xlsx",
    "longrun_stays.xlsx": "syukuhaku.xlsx",
    "longrun_visitors.pdf": "r7irikomi.pdf",
    "longrun_stays.pdf": "r7syukuhaku.pdf",
}

# First bytes of each file type, to catch an HTML error page saved under a .pdf name
MAGIC = {".pdf": b"%PDF", ".xlsx": b"PK", ".xls": b"\xd0\xcf\x11\xe0"}


def fetch(name: str, target: Path) -> str | None:
    """Download BASE+name to target. Returns an error message, or None on success."""
    if target.exists() and target.stat().st_size > 0:
        print(f"skip  {target.name} (already downloaded)")
        return None
    url = BASE + name
    try:
        req = Request(url, headers={"User-Agent": "sendai-tourism-dashboard/0.2"})
        with urlopen(req, timeout=60, context=SSL_CONTEXT) as resp:
            data = resp.read()
        magic = MAGIC[target.suffix]
        if not data.startswith(magic):
            raise ValueError(f"response is not a {target.suffix} file")
        target.write_bytes(data)
        print(f"ok    {target.name:<24} {len(data) / 1024:>6.0f} KB  <- {url}")
        return None
    except Exception as exc:
        print(f"FAIL  {target.name}  {url}: {exc}", file=sys.stderr)
        return target.name


def main(argv: list[str]) -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    failed = [f for label, name in REPORTS.items() if (f := fetch(name, RAW / f"{label}.pdf"))]
    if "--all" in argv:
        archive = RAW / "archive"
        archive.mkdir(exist_ok=True)
        failed += [f for out, name in ARCHIVE.items() if (f := fetch(name, archive / out))]
    if failed:
        print(f"\n{len(failed)} download(s) failed: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nall downloads ok")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
