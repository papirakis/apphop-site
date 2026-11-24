#!/usr/bin/env python3
"""
Idempotent Bunny CDN setup for apphop-site. Dry-run by default; --apply makes changes.

Credentials: BUNNY_API_KEY from the environment or ~/.bunny-secure/bunny.env (chmod 600).
Never printed, logged, or committed.

Modes:
  --staging (Phase 1, default target once --apply is set with this flag)
    Storage zone + pull zone, root-path origin, default hostname <name>.b-cdn.net only.
    Standard tier, NA+EU only. No Shield, Optimizer, WAF, custom domains, or DNS zone.
  --production
    Storage + pull zone with www/apex hostnames (needs DNS later). Kept for Phase 2.

VERIFY ON FIRST APPLY (API details printed in dry-run / self-check):
  - edge-rule enum values (ActionType/TriggerType) and header application
  - directory-index behaviour of storage-backed pull zones (/apps/ -> /apps/index.html)
"""
import argparse, json, os, stat, sys, urllib.error, urllib.request

API = "https://api.bunny.net"
NAME = "apphop-site"
HOSTNAMES = ["www.apphop.app", "apphop.app"]
SECURE_ENV = os.path.expanduser("~/.bunny-secure/bunny.env")
MONTHLY_BANDWIDTH_LIMIT_BYTES = 100 * 1024**3  # 100 GB safety cap (~$1 at $0.01/GB NA/EU)

ACTION_REDIRECT, ACTION_ORIGIN_URL, ACTION_OVERRIDE_CACHE, ACTION_SET_RESPONSE_HEADER = 1, 2, 3, 5
TRIGGER_URL, TRIGGER_REQUEST_HEADER, TRIGGER_STATUS = 0, 1, 8
MATCH_ANY = 0

STAGING_HEADERS = {
    "Strict-Transport-Security": "max-age=86400",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "X-Robots-Tag": "noindex, nofollow",
    "x-served-by-cdn": "bunny",
}
PROD_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Frame-Options": "DENY",
    "x-served-by-cdn": "bunny",
}


def load_env_file(path):
    kv = {}
    if not os.path.exists(path):
        return kv
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            kv[k] = v
    return kv


def upsert_env(path, updates):
    """Write keys to a chmod 600 env file. Never prints values."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kv = load_env_file(path)
    kv.update({k: str(v) for k, v in updates.items() if v is not None and v != ""})
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        for k, v in kv.items():
            f.write(f"{k}={v}\n")
    os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def load_key():
    if os.environ.get("BUNNY_API_KEY"):
        return os.environ["BUNNY_API_KEY"]
    kv = load_env_file(SECURE_ENV)
    if kv.get("BUNNY_API_KEY"):
        os.environ["BUNNY_API_KEY"] = kv["BUNNY_API_KEY"]
        return kv["BUNNY_API_KEY"]
    return None


def redact(s: str) -> str:
    for v in (os.environ.get("BUNNY_API_KEY"), os.environ.get("BUNNY_STORAGE_PASSWORD")):
        if v and v in s:
            s = s.replace(v, "[REDACTED]")
    return s


def strip_secrets(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if any(x in k.lower() for x in ("password", "key", "secret", "token", "auth")):
                out[k] = "[REDACTED]"
            else:
                out[k] = strip_secrets(v)
        return out
    if isinstance(obj, list):
        return [strip_secrets(x) for x in obj]
    return obj


class Bunny:
    def __init__(self, key, apply):
        self.key, self.apply = key, apply

    def call(self, method, path, body=None, mutate=True):
        if mutate and not self.apply:
            print(f"[dry] {method} {path} {json.dumps(strip_secrets(body)) if body else ''}")
            return {}
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            API + path,
            method=method,
            data=data,
            headers={"AccessKey": self.key, "Content-Type": "application/json", "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err = redact(e.read().decode("utf-8", "replace"))
            raise SystemExit(f"Bunny API {method} {path} failed: HTTP {e.code} {err}") from None


def find(items, name):
    seq = items if isinstance(items, list) else (items or {}).get("Items", [])
    for it in seq or []:
        if it.get("Name") == name:
            return it
    return None


def find_rule(rules, description):
    for r in rules or []:
        if r.get("Description") == description:
            return r
    return None


def header_rules(headers):
    return [
        {
            "Description": f"header {k}",
            "Enabled": True,
            "ActionType": ACTION_SET_RESPONSE_HEADER,
            "ActionParameter1": k,
            "ActionParameter2": v,
            "Triggers": [{"Type": TRIGGER_URL, "PatternMatches": ["*"], "PatternMatchingType": MATCH_ANY}],
            "TriggerMatchingType": MATCH_ANY,
        }
        for k, v in headers.items()
    ]


def upsert_rules(b, pid, existing, rules):
    for r in rules:
        prev = find_rule(existing, r["Description"])
        if prev and prev.get("Guid"):
            r = dict(r, Guid=prev["Guid"])
        b.call("POST", f"/pullzone/{pid}/edgerules/addOrUpdate", r)


def storage_host_for_region(region: str) -> str:
    r = (region or "NY").upper()
    # DE historically used the unprefixed host; the regional form is preferred.
    return {"NY": "ny.storage.bunnycdn.com", "LA": "la.storage.bunnycdn.com",
            "SG": "sg.storage.bunnycdn.com", "SYD": "syd.storage.bunnycdn.com",
            "DE": "de.storage.bunnycdn.com"}.get(r, f"{r.lower()}.storage.bunnycdn.com")


def pullzone_common(staging: bool) -> dict:
    return {
        "EnableLogging": False,
        "MonthlyBandwidthLimit": MONTHLY_BANDWIDTH_LIMIT_BYTES,
        "EnableBrotliCompression": True,
        "EnableAutoSSL": False,
        "EnableTLS1": False,
        "EnableTLS1_1": False,
        "CacheControlMaxAgeOverride": -1,
        "DisableCookies": True,
        "EnableOriginShield": False,
        "OptimizerEnabled": False,
        "EnableGeoZoneUS": True,
        "EnableGeoZoneEU": True,
        "EnableGeoZoneASIA": False,
        "EnableGeoZoneSA": False,
        "EnableGeoZoneAF": False,
        "Type": 0,  # standard tier
        "ErrorPageEnableStatuspage": False,
        "IgnoreQueryStrings": True,
        "EnableCacheSlice": False,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--staging", action="store_true", help="Phase 1: provider hostname only, NA+EU, no custom DNS")
    ap.add_argument("--production", action="store_true", help="Phase 2: add www/apex hostnames (do not use until DNS is approved)")
    ap.add_argument("--cert")
    ap.add_argument("--key")
    a = ap.parse_args()
    if a.production and a.staging:
        sys.exit("choose --staging or --production, not both")
    staging = a.staging or not a.production
    key = load_key()
    if not key:
        print("BUNNY_API_KEY not set: printing the plan only (account not created yet).")
        key, a.apply = "none", False
    b = Bunny(key, a.apply)

    sz = find(b.call("GET", "/storagezone", mutate=False), NAME) if a.apply else None
    if not sz:
        sz = b.call("POST", "/storagezone", {
            "Name": NAME, "Region": "NY", "ReplicationRegions": ["DE"], "ZoneTier": 0,
        }) or {"Id": "<new>", "Region": "NY"}

    storage_password = sz.get("Password") or os.environ.get("BUNNY_STORAGE_PASSWORD") or load_env_file(SECURE_ENV).get("BUNNY_STORAGE_PASSWORD")
    storage_host = storage_host_for_region(sz.get("Region") or "NY")
    # Some accounts return a StorageHostname; prefer it when present and not a secret.
    if sz.get("StorageHostname") and "password" not in str(sz.get("StorageHostname")).lower():
        storage_host = sz["StorageHostname"]

    pz = find(b.call("GET", "/pullzone", mutate=False), NAME) if a.apply else None
    if not pz:
        pz = b.call("POST", "/pullzone", {
            "Name": NAME,
            "StorageZoneId": sz.get("Id"),
            "OriginType": 2,
            "Type": 0,
            "EnableGeoZoneUS": True,
            "EnableGeoZoneEU": True,
            "EnableGeoZoneASIA": False,
            "EnableGeoZoneSA": False,
            "EnableGeoZoneAF": False,
        }) or {"Id": "<new>", "Hostnames": []}
    pid = pz.get("Id")

    update = dict(pullzone_common(staging), StorageZoneId=sz.get("Id"), OriginType=2)
    # Re-GET after create so we can set fields the create endpoint may ignore.
    if a.apply and pid not in (None, "<new>"):
        b.call("POST", f"/pullzone/{pid}", update)
        pz = b.call("GET", f"/pullzone/{pid}", mutate=False) or pz
    else:
        b.call("POST", f"/pullzone/{pid}", update)

    if not staging:
        existing = {h.get("Value") for h in (pz.get("Hostnames") or [])}
        for h in HOSTNAMES:
            if h not in existing:
                b.call("POST", f"/pullzone/{pid}/addHostname", {"Hostname": h})

    if a.apply:
        pz = b.call("GET", f"/pullzone/{pid}", mutate=False) or pz
    rules = []
    if not staging:
        rules.append({
            "Description": "apex -> www 301", "Enabled": True, "ActionType": ACTION_REDIRECT,
            "ActionParameter1": "https://www.apphop.app%{Url.Path}", "ActionParameter2": "301",
            "Triggers": [{"Type": TRIGGER_REQUEST_HEADER, "PatternMatches": ["apphop.app"], "Parameter1": "Host", "PatternMatchingType": MATCH_ANY}],
            "TriggerMatchingType": MATCH_ANY,
        })
    rules.append({
        "Description": "long cache hashed assets", "Enabled": True, "ActionType": ACTION_OVERRIDE_CACHE,
        "ActionParameter1": "31536000",
        "Triggers": [{"Type": TRIGGER_URL, "PatternMatches": ["*/_astro/*"], "PatternMatchingType": MATCH_ANY}],
        "TriggerMatchingType": MATCH_ANY,
    })
    rules.append({
        "Description": "short cache html and data", "Enabled": True, "ActionType": ACTION_OVERRIDE_CACHE,
        "ActionParameter1": "300",
        "Triggers": [{"Type": TRIGGER_URL, "PatternMatches": ["*.html", "*/", "*.json", "*.xml", "*.txt"], "PatternMatchingType": MATCH_ANY}],
        "TriggerMatchingType": MATCH_ANY,
    })
    rules.extend(header_rules(STAGING_HEADERS if staging else PROD_HEADERS))
    upsert_rules(b, pid, pz.get("EdgeRules") if a.apply else [], rules)

    if a.cert and a.key and not staging:
        import base64
        for h in HOSTNAMES:
            b.call("POST", f"/pullzone/{pid}/addCertificate", {
                "Hostname": h,
                "Certificate": base64.b64encode(open(a.cert, "rb").read()).decode(),
                "CertificateKey": base64.b64encode(open(a.key, "rb").read()).decode(),
            })

    if a.apply:
        if not storage_password:
            sys.exit("storage zone password missing from API response and env; cannot save")
        upsert_env(SECURE_ENV, {
            "BUNNY_API_KEY": key,
            "BUNNY_STORAGE_ZONE": NAME,
            "BUNNY_STORAGE_HOST": storage_host,
            "BUNNY_STORAGE_PASSWORD": storage_password,
            "BUNNY_PULLZONE_ID": pid,
        })
        os.environ["BUNNY_STORAGE_PASSWORD"] = storage_password
        print(f"wrote zone ids to {SECURE_ENV} (chmod 600); values not printed")

    print(json.dumps({
        "mode": "staging" if staging else "production",
        "storage_zone_id": sz.get("Id"),
        "storage_region": sz.get("Region") or "NY",
        "storage_host": storage_host,
        "pull_zone_id": pid,
        "cname_target": f"{NAME}.b-cdn.net",
        "geo": "US+EU",
        "tier": "standard",
        "applied": a.apply,
    }, indent=2, default=str))


if __name__ == "__main__":
    main()
