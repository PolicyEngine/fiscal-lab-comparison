"""Download Fiscal Lab's dashboard and extract the two bills compared here.

Fiscal Lab's terms reserve republication, so this repository does not commit
its data. This script fetches the one public dashboard page and writes the
extract to data/fiscal_lab/ (git-ignored).

Run: uv run python scripts/fetch_fiscal_lab.py
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

URL = "https://fiscallab.org/score/healthcare-working-group-memo-scores/dashboard.html"
BILLS = ["H.R. 4849", "H.R. 1428"]
OUT = Path(__file__).resolve().parents[1] / "data" / "fiscal_lab"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8")
    marker = "const DATA = "
    start = html.index(marker) + len(marker)
    data, _ = json.JSONDecoder().raw_decode(html[start:])
    keep = {
        "built": data["built"],
        "years": data["years"],
        "source": URL,
        "bills": {
            b["label"]: {
                k: b.get(k)
                for k in ("title", "models", "figure", "low", "high", "t1", "t3", "t4", "glance")
            }
            for b in data["bills"]
            if b["label"] in BILLS
        },
    }
    (OUT / "two_bills.json").write_text(json.dumps(keep, indent=1))
    print(f"wrote {OUT / 'two_bills.json'} (dashboard built {data['built']})")


if __name__ == "__main__":
    main()
