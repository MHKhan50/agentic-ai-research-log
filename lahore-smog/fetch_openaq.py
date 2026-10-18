"""Download daily PM2.5 for monitors around Lahore from the OpenAQ v3 API.

Usage:
    python fetch_openaq.py                 # last 365 days
    python fetch_openaq.py --days 730

Needs a free OpenAQ API key in the environment or in a local .env file:
    OPENAQ_API_KEY=your-key-here
The .env file is git-ignored and must never be committed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

import pandas as pd
import requests

API = "https://api.openaq.org/v3"
LAHORE = (31.5204, 74.3587)  # lat, lon (city centre)
RADIUS_M = 25_000  # API maximum
HERE = Path(__file__).parent
PAUSE_S = 1.1  # stay under the 60 requests/minute limit


def load_api_key() -> str:
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    env_file = HERE / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("OPENAQ_API_KEY="):
                key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("Missing OPENAQ_API_KEY. Create a free key at explore.openaq.org and put it in lahore-smog/.env")
    return key


class OpenAQ:
    def __init__(self, api_key: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})

    def get(self, path: str, **params: Any) -> Dict[str, Any]:
        for attempt in range(4):
            resp = self.session.get(f"{API}{path}", params=params, timeout=60)
            if resp.status_code == 429:  # rate limited: back off and retry
                time.sleep(10 * (attempt + 1))
                continue
            if resp.status_code == 401:
                sys.exit("OpenAQ rejected the API key (401). Check the key in .env")
            resp.raise_for_status()
            time.sleep(PAUSE_S)
            return resp.json()
        raise RuntimeError(f"Rate limited too many times on {path}")

    def paged(self, path: str, limit: int = 1000, **params: Any) -> Iterator[Dict[str, Any]]:
        page = 1
        while True:
            results = self.get(path, limit=limit, page=page, **params).get("results", [])
            yield from results
            if len(results) < limit:
                return
            page += 1


def pm25_sensors(client: OpenAQ, active_since: date) -> List[Dict[str, Any]]:
    """PM2.5 sensors at fixed (non-mobile) locations within 25 km of central Lahore,
    skipping locations with no data since ``active_since``."""
    sensors: List[Dict[str, Any]] = []
    coords = f"{LAHORE[0]},{LAHORE[1]}"
    for loc in client.paged("/locations", coordinates=coords, radius=RADIUS_M, limit=100):
        if loc.get("isMobile"):
            continue
        last = ((loc.get("datetimeLast") or {}).get("utc") or "")[:10]
        if last and last < active_since.isoformat():
            continue
        for s in loc.get("sensors", []):
            param = s.get("parameter") or {}
            if param.get("name") == "pm25":
                sensors.append({
                    "location_id": loc.get("id"),
                    "location": loc.get("name"),
                    "provider": (loc.get("provider") or {}).get("name"),
                    "is_monitor": bool(loc.get("isMonitor")),
                    "sensor_id": s.get("id"),
                    "units": param.get("units"),
                })
    return sensors


def coverage_pct(row: Dict[str, Any]) -> Optional[float]:
    cov = row.get("coverage") or {}
    value = cov.get("percentComplete", cov.get("percentCoverage"))
    return float(value) if value is not None else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=365)
    args = parser.parse_args()

    client = OpenAQ(load_api_key())
    date_to = date.today()
    date_from = date_to - timedelta(days=args.days)

    sensors = pm25_sensors(client, date_from)
    print(f"Found {len(sensors)} PM2.5 sensors within {RADIUS_M // 1000} km of Lahore")
    if not sensors:
        sys.exit("No PM2.5 sensors found. Try again later or increase --days.")

    rows: List[Dict[str, Any]] = []
    for i, s in enumerate(sensors, 1):
        n_before = len(rows)
        for d in client.paged(f"/sensors/{s['sensor_id']}/days",
                              date_from=date_from.isoformat(), date_to=date_to.isoformat()):
            period = (d.get("period") or {}).get("datetimeFrom") or {}
            rows.append({
                **s,
                "date": (period.get("local") or period.get("utc") or "")[:10],
                "pm25": d.get("value"),
                "coverage_pct": coverage_pct(d),
            })
        print(f"[{i}/{len(sensors)}] {s['location']} (sensor {s['sensor_id']}): {len(rows) - n_before} days")

    out = HERE / "data" / "raw_daily_pm25.csv"
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"Saved {len(rows)} rows to {out} ({date_from} to {date_to})")


if __name__ == "__main__":
    main()
