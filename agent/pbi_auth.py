#!/usr/bin/env python3
"""Sign in to Power BI as a user via the device-code flow and cache the token.

Uses Microsoft's public Azure CLI client id, so no app registration is needed.
The token cache (with refresh token) is stored in agent/.pbi_token.json —
git-ignored, local to this machine.

Usage:
  python3 agent/pbi_auth.py login    # prints the code, waits for you to sign in
  python3 agent/pbi_auth.py token    # prints a valid access token (auto-refresh)
  python3 agent/pbi_auth.py whoami   # sanity check: lists first workspaces
"""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

CLIENT_ID = "04b07795-8ddb-461a-bbee-02f9e1bf7b46"  # Microsoft Azure CLI (public client)
AUTHORITY = "https://login.microsoftonline.com/organizations"
SCOPE = "https://analysis.windows.net/powerbi/api/.default offline_access"
CACHE = Path(__file__).parent / ".pbi_token.json"

def _post(url: str, data: dict) -> dict:
    req = urllib.request.Request(url, data=urllib.parse.urlencode(data).encode())
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode())

def login() -> None:
    dc = _post(f"{AUTHORITY}/oauth2/v2.0/devicecode", {"client_id": CLIENT_ID, "scope": SCOPE})
    if "user_code" not in dc:
        sys.exit("Device code request failed: " + json.dumps(dc))
    print(f"CODE: {dc['user_code']}")
    print(f"URL:  {dc['verification_uri']}")
    sys.stdout.flush()
    interval = dc.get("interval", 5)
    deadline = time.time() + dc.get("expires_in", 900)
    while time.time() < deadline:
        time.sleep(interval)
        tok = _post(f"{AUTHORITY}/oauth2/v2.0/token", {
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "client_id": CLIENT_ID, "device_code": dc["device_code"]})
        if "access_token" in tok:
            tok["obtained_at"] = int(time.time())
            CACHE.write_text(json.dumps(tok))
            CACHE.chmod(0o600)
            print("LOGIN OK")
            return
        if tok.get("error") not in ("authorization_pending", "slow_down"):
            sys.exit("Login failed: " + json.dumps(tok))
        if tok.get("error") == "slow_down":
            interval += 5
    sys.exit("Login timed out — run login again")

def token() -> str:
    if not CACHE.exists():
        sys.exit("Not logged in — run: python3 agent/pbi_auth.py login")
    tok = json.loads(CACHE.read_text())
    if time.time() < tok["obtained_at"] + tok.get("expires_in", 3600) - 120:
        return tok["access_token"]
    ref = _post(f"{AUTHORITY}/oauth2/v2.0/token", {
        "grant_type": "refresh_token", "client_id": CLIENT_ID,
        "refresh_token": tok["refresh_token"], "scope": SCOPE})
    if "access_token" not in ref:
        sys.exit("Token refresh failed — run login again: " + ref.get("error", "?"))
    ref["obtained_at"] = int(time.time())
    CACHE.write_text(json.dumps(ref))
    return ref["access_token"]

def whoami() -> None:
    t = token()
    req = urllib.request.Request("https://api.powerbi.com/v1.0/myorg/groups?$top=20",
                                 headers={"Authorization": f"Bearer {t}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        groups = json.load(r).get("value", [])
    print(json.dumps([{"id": g["id"], "name": g["name"]} for g in groups],
                     indent=2, ensure_ascii=False))

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "login"
    if cmd == "login": login()
    elif cmd == "token": print(token())
    elif cmd == "whoami": whoami()
    else: sys.exit("unknown command: " + cmd)
