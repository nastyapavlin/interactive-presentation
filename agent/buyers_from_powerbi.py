#!/usr/bin/env python3
"""Build the deck's `data.buyers` block from Power BI (dataset "USA preferences Main_").

Auth, in order of preference:
  1. User token cached by `python3 agent/pbi_auth.py login` (device-code flow).
  2. Service principal env vars (PBI_TENANT_ID / PBI_CLIENT_ID / PBI_CLIENT_SECRET),
     see agent/POWERBI_SETUP.md — needed for headless/cloud runs.

DAX lives in agent/queries/buyers_by_type.dax and buyers_by_state.dax.
Filter: companies marked 'Тип компании' = "Buyer". "Nationwide" interest is
reported separately in `nationwide` — those buyers bid in every state.

Usage:  python3 agent/buyers_from_powerbi.py [--round]
  --round  approximate all counts (public/demo snapshots: exact figures stay
           internal; totals to the nearest 100, states to the nearest 10)
"""
import json, os, subprocess, sys, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent
DATASET_ID = "f95c5194-987d-4907-a3e9-a6789ea4ff45"  # USA preferences Main_

# Platform classification -> deck group (label, note for the interactive legend)
GROUPS = [
    ("FinTechs", ["FinTechs"],
     "Fintech lenders and investors active in consumer and specialty receivables."),
    ("Debt buying funds", ["Certified Debt Buyer", "Associate Debt Buyer",
                           "International Debt Buyer", "Junk Debt"],
     "Certified and associate debt buyers purchasing performing and charged-off portfolios."),
    ("Collection agencies", ["Certified Collection Agency", "Associate Collection Agency"],
     "Agencies buying paper they will work themselves — strong bidders on skips and deficiencies."),
    ("Law firms", ["Certified Law Firm", "Associate Law Firm"],
     "Legal-network buyers focused on judgments and legal-stage accounts."),
    ("Banks & credit unions", ["Banks", "Credit Unions"],
     "Regulated institutions buying seasoned performing paper."),
    ("Lenders & originators", ["Auto Lenders", "Auto loans", "Consumer Lender",
                               "Small Business Lender", "Commercial Equipment Lenders",
                               "PDL", "Originating Creditor"],
     "Originating lenders acquiring portfolios adjacent to their core business."),
]
OTHER_LABEL = "Other & unclassified"
OTHER_NOTE = "Registered buyers pending classification, brokers, affiliates and partners."

def get_token() -> str:
    r = subprocess.run([sys.executable, str(HERE / "pbi_auth.py"), "token"],
                       capture_output=True, text=True)
    if r.returncode == 0 and r.stdout.strip():
        return r.stdout.strip()
    sys.path.insert(0, str(HERE))
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    if all(os.environ.get(k) for k in ("PBI_TENANT_ID", "PBI_CLIENT_ID", "PBI_CLIENT_SECRET")):
        import urllib.parse
        body = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": os.environ["PBI_CLIENT_ID"],
            "client_secret": os.environ["PBI_CLIENT_SECRET"],
            "scope": "https://analysis.windows.net/powerbi/api/.default"}).encode()
        req = urllib.request.Request(
            f"https://login.microsoftonline.com/{os.environ['PBI_TENANT_ID']}/oauth2/v2.0/token",
            data=body)
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)["access_token"]
    sys.exit("No Power BI auth: run `python3 agent/pbi_auth.py login` or configure agent/.env")

def run_dax(token: str, dax: str) -> list[dict]:
    req = urllib.request.Request(
        f"https://api.powerbi.com/v1.0/myorg/datasets/{DATASET_ID}/executeQueries",
        data=json.dumps({"queries": [{"query": dax}]}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    if "error" in payload:
        sys.exit("Power BI error: " + json.dumps(payload)[:400])
    return payload["results"][0]["tables"][0]["rows"]

def val(row: dict, suffix: str):
    for k, v in row.items():
        if k.endswith(suffix + "]"):
            return v
    return None

def approx(n: int) -> int:
    if n >= 1000: return round(n / 100) * 100
    if n >= 100:  return round(n / 10) * 10
    if n >= 10:   return round(n / 5) * 5
    return n

def main() -> None:
    rounded = "--round" in sys.argv
    token = get_token()
    type_rows = run_dax(token, (HERE / "queries/buyers_by_type.dax").read_text())
    state_rows = run_dax(token, (HERE / "queries/buyers_by_state.dax").read_text())

    raw = {}
    for r in type_rows:
        t = val(r, "Тип типов компании")
        raw[t if t else "no data"] = int(val(r, "Count") or 0)
    total = sum(raw.values())

    by_type, used = [], set()
    for label, keys, note in GROUPS:
        cnt = sum(raw.get(k, 0) for k in keys)
        used.update(keys)
        if cnt:
            by_type.append({"type": label, "count": cnt, "note": note})
    other = sum(c for k, c in raw.items() if k not in used)
    if other:
        by_type.append({"type": OTHER_LABEL, "count": other, "note": OTHER_NOTE})
    by_type.sort(key=lambda x: (x["type"] == OTHER_LABEL, -x["count"]))  # Other last

    # Source data sometimes types state codes with Cyrillic lookalikes ("ОК")
    latinize = str.maketrans("АВСЕНКМОРТХУ", "ABCEHKMOPTXY")
    by_state, nationwide = {}, 0
    for r in state_rows:
        postal, name, cnt = val(r, "postal"), val(r, "name"), int(val(r, "Count") or 0)
        if name == "Nationwide":
            nationwide = cnt
        elif postal:
            by_state[str(postal).upper().translate(latinize)] = cnt

    if rounded:
        for x in by_type:
            x["count"] = approx(x["count"])
        by_state = {k: approx(v) for k, v in by_state.items()}
        nationwide = approx(nationwide)
        total = approx(sum(x["count"] for x in by_type))

    print(json.dumps({
        "asOf": date.today().isoformat(),
        "source": "Power BI · USA preferences Main_",
        "approximate": rounded,
        "total": total,
        "nationwide": nationwide,
        "byType": by_type,
        "byState": by_state,
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
