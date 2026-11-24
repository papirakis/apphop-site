#!/usr/bin/env python3
"""
Idempotent Bunny CDN setup for apphop-site (standby CDN). Dry-run by default; --apply makes changes.
Requires BUNNY_API_KEY (account key from the vault; never committed). Blocked until the Bunny account exists.

Creates/updates:
  - Storage zone  apphop-site (main region NY + replicas LA, DE) = Bunny's AWS-independent origin
  - Pull zone     apphop-site (origin = storage zone), hostnames www.apphop.app + apphop.app
  - Edge rules    apex -> https://www.apphop.app 301, security headers, x-served-by-cdn: bunny
  - Logging       enabled (Logging API v2, 3-day retention) for the ops collector
  - Monthly bandwidth limit (cost cap, doc section 6.5 cdn-traffic-cost-spike)
  - Optional custom cert upload (--cert/--key, the shared Let's Encrypt cert from scripts/acme_issue.sh).
    Bunny's own free cert uses HTTP-01 and cannot renew while Bunny is on standby, so we upload ours.

VERIFY ON FIRST APPLY (API details to confirm against the live account; printed in dry-run):
  - edge-rule enum values (ActionType/TriggerType) and the redirect variable syntax
  - directory-index behaviour of storage-backed pull zones (/apps/ -> /apps/index.html); the post-apply
    self-check below fails loudly if it is not served.
"""
import argparse, base64, json, os, sys, urllib.request

API = "https://api.bunny.net"
NAME = "apphop-site"
HOSTNAMES = ["www.apphop.app", "apphop.app"]
MONTHLY_BANDWIDTH_LIMIT_BYTES = 200 * 1024**3  # 200 GB ~= $2 at $0.01/GB (NA/EU)

# Bunny edge-rule enums (per API docs at time of writing; verify on first apply).
ACTION_REDIRECT, ACTION_SET_RESPONSE_HEADER = 1, 5
TRIGGER_REQUEST_HEADER, TRIGGER_URL = 1, 0
HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "x-served-by-cdn": "bunny",
}


class Bunny:
    def __init__(self, key, apply):
        self.key, self.apply = key, apply

    def call(self, method, path, body=None, mutate=True):
        if mutate and not self.apply:
            print(f"[dry] {method} {path} {json.dumps(body) if body else ''}")
            return {}
        req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"AccessKey": self.key, "Content-Type": "application/json", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}


def find(items, name):
    for it in items if isinstance(items, list) else items.get("Items", []):
        if it.get("Name") == name:
            return it
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--cert"); ap.add_argument("--key")
    a = ap.parse_args()
    key = os.environ.get("BUNNY_API_KEY")
    if not key:
        print("BUNNY_API_KEY not set: printing the plan only (account not created yet).")
        key, a.apply = "none", False
    b = Bunny(key, a.apply)

    sz = find(b.call("GET", "/storagezone", mutate=False), NAME) if a.apply else None
    if not sz:
        sz = b.call("POST", "/storagezone", {"Name": NAME, "Region": "NY", "ReplicationRegions": ["LA", "DE"], "ZoneTier": 0}) or {"Id": "<new>"}
    pz = find(b.call("GET", "/pullzone", mutate=False), NAME) if a.apply else None
    if not pz:
        pz = b.call("POST", "/pullzone", {"Name": NAME, "StorageZoneId": sz.get("Id"), "OriginType": 2, "Type": 0}) or {"Id": "<new>"}
    pid = pz.get("Id")
    b.call("POST", f"/pullzone/{pid}", {
        "EnableLogging": True, "LoggingIPAnonymizationEnabled": True,
        "MonthlyBandwidthLimit": MONTHLY_BANDWIDTH_LIMIT_BYTES,
        "EnableBrotliCompression": True, "EnableAutoSSL": False, "EnableTLS1": False, "EnableTLS1_1": False,
        "CacheControlMaxAgeOverride": -1,  # respect origin Cache-Control set by scripts/publish.py
        "DisableCookies": True,
    })
    existing = {h.get("Value") for h in pz.get("Hostnames", [])}
    for h in HOSTNAMES:
        if h not in existing:
            b.call("POST", f"/pullzone/{pid}/addHostname", {"Hostname": h})
    rules = [{
        "Description": "apex -> www 301", "Enabled": True, "ActionType": ACTION_REDIRECT,
        "ActionParameter1": "https://www.apphop.app%{Url.Path}", "ActionParameter2": "301",
        "Triggers": [{"Type": TRIGGER_REQUEST_HEADER, "PatternMatches": ["apphop.app"], "Parameter1": "Host", "PatternMatchingType": 0}],
        "TriggerMatchingType": 0,
    }] + [{
        "Description": f"header {k}", "Enabled": True, "ActionType": ACTION_SET_RESPONSE_HEADER,
        "ActionParameter1": k, "ActionParameter2": v,
        "Triggers": [{"Type": TRIGGER_URL, "PatternMatches": ["*"], "PatternMatchingType": 0}], "TriggerMatchingType": 0,
    } for k, v in HEADERS.items()]
    for r in rules:
        b.call("POST", f"/pullzone/{pid}/edgerules/addOrUpdate", r)
    if a.cert and a.key:
        for h in HOSTNAMES:
            b.call("POST", f"/pullzone/{pid}/addCertificate", {
                "Hostname": h,
                "Certificate": base64.b64encode(open(a.cert, "rb").read()).decode(),
                "CertificateKey": base64.b64encode(open(a.key, "rb").read()).decode()})
    if a.apply:
        cdn_host = f"{NAME}.b-cdn.net"
        for path in ("/", "/apps/", "/healthz.json"):
            try:
                with urllib.request.urlopen(f"https://{cdn_host}{path}", timeout=20) as r:
                    print(f"self-check {path}: {r.status}")
            except Exception as e:  # noqa: BLE001
                print(f"SELF-CHECK FAILED {path}: {e}"); sys.exit(1)
    print(json.dumps({"storage_zone": sz.get("Id"), "pull_zone": pid, "cname_target": f"{NAME}.b-cdn.net", "applied": a.apply}))


if __name__ == "__main__":
    main()
