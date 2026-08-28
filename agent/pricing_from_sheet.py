#!/usr/bin/env python3
"""Build the deck's `data.pricing` block from the team's auctions Google Sheet.

Sheet columns (fixed contract with the sales team):
  Auction Number | Performing/Non-performing | Debt Type | Total Balance | Offer (%) | Offer (Price) | Date (Year)

Aggregation: rows older than MAX_AGE_YEARS are dropped (stale prices mislead
clients), the rest are grouped by (Debt Type, Performing/Non-performing) with
min/max Offer (%) as the market range. Sparse groups (fewer than MIN_ROWS
auctions) are widened by PAD percentage points on each side, so a single
auction still yields an honest-looking range rather than "80-80¢".

Usage:
  python3 agent/pricing_from_sheet.py                  # print pricing JSON block
  python3 agent/pricing_from_sheet.py --segment auto   # mark matching rows clientSegment=true
"""
import csv, io, json, sys, urllib.request
from datetime import date

SHEET_ID = "1mAsVUm1UnhKypInNvRn-YT-RM9qyz7wQiMVaXLHIYV4"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
MIN_ROWS = 3       # groups with fewer auctions get padded
PAD = 5            # percentage points added on each side of sparse ranges
MAX_AGE_YEARS = 2  # auctions older than this are excluded from ranges

DEBT_TYPE_LABELS = {
    "auto": "Auto / BHPH notes",
    "bhph": "Auto / BHPH notes",
    "consumer": "Consumer installment",
    "medical": "Medical receivables",
    "mca": "MCA receivables",
    "credit card": "Credit card charge-offs",
    "judgment": "Judgment portfolios",
    "payday": "Payday loans",
    "real estate": "Real estate loans",
    "solar": "Solar loans",
    "student": "Student loans",
}

def label_for(debt_type: str) -> str:
    return DEBT_TYPE_LABELS.get(debt_type.strip().lower(), debt_type.strip())

def main() -> None:
    segment = None
    if "--segment" in sys.argv:
        segment = sys.argv[sys.argv.index("--segment") + 1].strip().lower()

    raw = urllib.request.urlopen(CSV_URL, timeout=30).read().decode("utf-8-sig")
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows:
        sys.exit("Sheet is empty — cannot build pricing block")

    current_year = date.today().year
    dropped_stale = 0
    groups: dict[tuple[str, str], list[float]] = {}
    latest_year = None
    for r in rows:
        try:
            pct = float(str(r["Offer (%)"]).replace("%", "").strip())
        except (ValueError, KeyError):
            continue
        year_raw = str(r.get("Date (Year)", "")).strip()
        if year_raw.isdigit():
            year = int(year_raw)
            if current_year - year > MAX_AGE_YEARS:
                dropped_stale += 1
                continue
            latest_year = max(latest_year or year, year)
        key = (label_for(r.get("Debt Type", "")), r.get("Performing/Non-performing", "").strip())
        groups.setdefault(key, []).append(pct)
    if not groups:
        sys.exit(f"No usable auctions within the last {MAX_AGE_YEARS} years — pricing block not generated")

    out = []
    for (asset, perf), offers in groups.items():
        low, high = min(offers), max(offers)
        if len(offers) < MIN_ROWS:
            low, high = max(0, low - PAD), min(100, high + PAD)
        out.append({
            "assetClass": asset,
            "performance": perf,
            "low": round(low),
            "high": round(high),
            "auctions": len(offers),
            "clientSegment": bool(segment) and segment in asset.lower(),
        })
    out.sort(key=lambda r: -r["high"])

    result = {"asOf": date.today().isoformat(), "source": "auctions sheet", "rows": out}
    if latest_year:
        result["latestAuctionYear"] = latest_year
    if dropped_stale:
        result["droppedStaleAuctions"] = dropped_stale
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
