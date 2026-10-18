"""Download one year of daily PM2.5 for six Pakistani cities from the OpenAQ v3 API.

Usage:
    python fetch_cities.py                  # all cities, last 365 days
    python fetch_cities.py --city Karachi   # one city
    python fetch_cities.py --refresh        # re-download cities already saved

The API key is read from OPENAQ_API_KEY, from ./.env, or from ../lahore-smog/.env.
.env files are git-ignored and must never be committed.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd
import requests

API = "https://api.openaq.org/v3"
RADIUS_M = 25_000  # API maximum; the same radius for every city
PAUSE_S = 1.1  # stay under the 60 requests/minute limit
HERE = Path(__file__).parent
DATA = HERE / "data"

# City centres (lat, lon)
CITIES: Dict[str, Tuple[float, float]] = {
    "Lahore": (31.5204, 74.3587),
    "Karachi": (24.8607, 67.0011),
    "Islamabad": (33.6844, 73.0479),
    "Faisalabad": (31.4504, 73.1350),
    "Peshawar": (34.0151, 71.5249),
    "Quetta": (30.1798, 66.9750),
}


def load_api_key() -> str:
    key = os.environ.get("OPENAQ_API_KEY", "").strip()
    for env_file in (HERE / ".env", HERE.parent / "lahore-smog" / ".env"):
        if key:
            break
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("OPENAQ_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip("'\"")
    if not key:
        sys.exit("Missing OPENAQ_API_KEY (env var, ./.env or ../lahore-smog/.env)")
    return key


class OpenAQ:
    def __init__(self, api_key: str) -> None:
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key, "Accept": "application/json"})

    def get(self, path: str, **params: Any) -> Dict[str, Any]:
        for attempt in range(4):
            resp = self.session.get(f"{API}{path}", params=params, timeout=60)
            if resp.status_code == 429:
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


def pm25_sensors(client: OpenAQ, centre: Tuple[float, float], active_since: date) -> List[Dict[str, Any]]:
    """PM2.5 sensors at fixed locations within RADIUS_M of the centre with data since ``active_since``."""
    sensors: List[Dict[str, Any]] = []
    for loc in client.paged("/locations", coordinates=f"{centre[0]},{centre[1]}", radius=RADIUS_M, limit=100):
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
                })
    return sensors


def coverage_pct(row: Dict[str, Any]) -> Optional[float]:
    cov = row.get("coverage") or {}
    value = cov.get("percentComplete", cov.get("percentCoverage"))
    return float(value) if value is not None else None


def fetch_city(client: OpenAQ, city: str, date_from: date, date_to: date) -> pd.DataFrame:
    sensors = pm25_sensors(client, CITIES[city], date_from)
    print(f"{city}: {len(sensors)} PM2.5 sensors found")
    rows: List[Dict[str, Any]] = []
    for i, s in enumerate(sensors, 1):
        n = len(rows)
        for d in client.paged(f"/sensors/{s['sensor_id']}/days",
                              date_from=date_from.isoformat(), date_to=date_to.isoformat()):
            period = (d.get("period") or {}).get("datetimeFrom") or {}
            rows.append({"city": city, **s,
                         "date": (period.get("local") or period.get("utc") or "")[:10],
                         "pm25": d.get("value"), "coverage_pct": coverage_pct(d)})
        print(f"  [{i}/{len(sensors)}] {s['location']}: {len(rows) - n} days")
    cols = ["city", "location_id", "location", "provider", "is_monitor", "sensor_id", "date", "pm25", "coverage_pct"]
    return pd.DataFrame(rows, columns=cols)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--city", choices=sorted(CITIES), help="fetch one city only")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--refresh", action="store_true", help="re-download cities already saved")
    args = parser.parse_args()

    client = OpenAQ(load_api_key())
    date_to = date.today()
    date_from = date_to - timedelta(days=args.days)
    DATA.mkdir(exist_ok=True)

    for city in ([args.city] if args.city else list(CITIES)):
        out = DATA / f"{city.lower()}_daily_pm25.csv"
        if out.exists() and not args.refresh:
            print(f"{city}: already saved, skipping (use --refresh to re-download)")
            continue
        df = fetch_city(client, city, date_from, date_to)
        df.to_csv(out, index=False)
        print(f"{city}: saved {len(df)} rows to {out.name}\n")
    print(f"Window: {date_from} to {date_to}")


if __name__ == "__main__":
    main()
