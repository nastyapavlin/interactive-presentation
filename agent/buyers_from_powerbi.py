#!/usr/bin/env python3
"""Build the deck's `data.buyers` block from Power BI (REST API, executeQueries).

Auth: Azure AD service principal (client-credentials flow). Credentials come
ONLY from environment variables (or a local `.env` file next to this script,
never committed):

  PBI_TENANT_ID     Azure AD tenant id
  PBI_CLIENT_ID     app registration (service principal) client id
  PBI_CLIENT_SECRET service principal secret
  PBI_DATASET_ID    Power BI dataset id (Workspace -> Dataset -> Settings, or from URL)

DAX queries live in agent/queries/buyers_by_type.dax and buyers_by_state.dax —
adapt the table/column names there to the real model once.

Usage:
  python3 agent/buyers_from_powerbi.py            # print buyers JSON block
See agent/POWERBI_SETUP.md for the one-time admin setup.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).parent

def load_dotenv() -> None:
    env = HERE / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())

def get_token(tenant: str, client_id: str, secret: str) -> str:
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": secret,
        "scope": "https://analysis.windows.net/powerbi/api/.default",
    }).encode()
    req = urllib.request.Request(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token", data=body)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)["access_token"]

def run_dax(dataset: str, token: str, dax: str) -> list[dict]:
    req = urllib.request.Request(
        f"https://api.powerbi.com/v1.0/myorg/datasets/{dataset}/executeQueries",
        data=json.dumps({"queries": [{"query": dax}],
                         "serializerSettings": {"includeNulls": True}}).encode(),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        payload = json.load(r)
    return payload["results"][0]["tables"][0]["rows"]

def col(row: dict, suffix: str):
    """DAX rows come back with keys like "Buyers[Buyer Type]" or "[Count]"."""
    for k, v in row.items():
        if k.endswith(suffix + "]"):
            return v
    raise KeyError(f"column ending '{suffix}]' not in {list(row)}")

def main() -> None:
    load_dotenv()
    missing = [k for k in ("PBI_TENANT_ID", "PBI_CLIENT_ID", "PBI_CLIENT_SECRET", "PBI_DATASET_ID")
               if not os.environ.get(k)]
    if missing:
        sys.exit("Missing env vars: " + ", ".join(missing) + " (see agent/POWERBI_SETUP.md)")

    token = get_token(os.environ["PBI_TENANT_ID"], os.environ["PBI_CLIENT_ID"],
                      os.environ["PBI_CLIENT_SECRET"])
    dataset = os.environ["PBI_DATASET_ID"]

    by_type_rows = run_dax(dataset, token, (HERE / "queries/buyers_by_type.dax").read_text())
    by_state_rows = run_dax(dataset, token, (HERE / "queries/buyers_by_state.dax").read_text())

    by_type = [{"type": col(r, "Buyer Type"), "count": int(col(r, "Count"))} for r in by_type_rows]
    by_state = {str(col(r, "State")): int(col(r, "Count")) for r in by_state_rows}

    print(json.dumps({
        "asOf": date.today().isoformat(),
        "source": "Power BI",
        "total": sum(x["count"] for x in by_type),
        "byType": by_type,
        "byState": by_state,
    }, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
