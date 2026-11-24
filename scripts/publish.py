#!/usr/bin/env python3
"""
Publish dist/ to every configured origin, then purge HTML on every configured CDN.

Order (doc section 3.1): 1) new hashed assets (/_astro/, immutable), 2) everything else (HTML/JSON/XML),
3) purge HTML on each CDN, 4) caller runs scripts/parity_check.py. Old assets are never deleted here
(S3 lifecycle keeps noncurrent versions 7 days), so cached HTML never points at a missing file.

Targets are enabled by environment variables; missing ones are skipped with a notice:
  S3_PRIMARY_BUCKET, S3_REPLICA_BUCKET            (boto3; credentials from the environment / OIDC role)
  CLOUDFRONT_DISTRIBUTION_ID
  BUNNY_STORAGE_ZONE, BUNNY_STORAGE_HOST (e.g. storage.bunnycdn.com), BUNNY_STORAGE_PASSWORD
  BUNNY_API_KEY, BUNNY_PULLZONE_ID
  FASTLY_API_KEY, FASTLY_SERVICE_ID
Use --dry-run to print the plan without uploading.
"""
import argparse, json, mimetypes, os, sys, time, urllib.request

mimetypes.add_type("application/manifest+json", ".webmanifest")
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/webp", ".webp")

IMMUTABLE = "public, max-age=31536000, immutable"
HTML = "public, max-age=0, s-maxage=300, must-revalidate"


def files(root):
    out = []
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            rel = os.path.relpath(p, root).replace(os.sep, "/")
            out.append((rel, p))
    assets = sorted(x for x in out if x[0].startswith("_astro/"))
    rest = sorted(x for x in out if not x[0].startswith("_astro/"))
    return assets + rest  # assets first


def meta(rel):
    ctype = mimetypes.guess_type(rel)[0] or "application/octet-stream"
    if ctype.startswith("text/") or ctype in ("application/json", "application/xml", "image/svg+xml", "application/javascript"):
        ctype += "; charset=utf-8" if "charset" not in ctype else ""
    cache = IMMUTABLE if rel.startswith("_astro/") else HTML
    return ctype, cache


def http(method, url, headers=None, data=None):
    req = urllib.request.Request(url, method=method, headers=headers or {}, data=data)
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.read()


def s3_upload(bucket, items, dry):
    if dry:
        print(f"[dry] s3://{bucket}: {len(items)} objects"); return
    import boto3
    s3 = boto3.client("s3")
    for rel, path in items:
        ctype, cache = meta(rel)
        s3.upload_file(path, bucket, rel, ExtraArgs={"ContentType": ctype, "CacheControl": cache})
    print(f"s3://{bucket}: uploaded {len(items)}")


def bunny_upload(items, dry):
    zone, host, pw = os.environ["BUNNY_STORAGE_ZONE"], os.environ.get("BUNNY_STORAGE_HOST", "storage.bunnycdn.com"), os.environ["BUNNY_STORAGE_PASSWORD"]
    if dry:
        print(f"[dry] bunny storage {zone}: {len(items)} objects"); return
    for rel, path in items:
        ctype, _ = meta(rel)
        http("PUT", f"https://{host}/{zone}/{rel}", {"AccessKey": pw, "Content-Type": ctype}, open(path, "rb").read())
    print(f"bunny storage {zone}: uploaded {len(items)}")


def purge(dry):
    if os.environ.get("CLOUDFRONT_DISTRIBUTION_ID"):
        if dry: print("[dry] cloudfront invalidation /*")
        else:
            import boto3
            boto3.client("cloudfront").create_invalidation(
                DistributionId=os.environ["CLOUDFRONT_DISTRIBUTION_ID"],
                InvalidationBatch={"Paths": {"Quantity": 1, "Items": ["/*"]}, "CallerReference": str(time.time())})
            print("cloudfront: invalidated /* (counts as 1 path)")
    if os.environ.get("FASTLY_API_KEY") and os.environ.get("FASTLY_SERVICE_ID"):
        if dry: print("[dry] fastly purge_all")
        else:
            http("POST", f"https://api.fastly.com/service/{os.environ['FASTLY_SERVICE_ID']}/purge_all", {"Fastly-Key": os.environ["FASTLY_API_KEY"], "Accept": "application/json"})
            print("fastly: purge_all")
    if os.environ.get("BUNNY_API_KEY") and os.environ.get("BUNNY_PULLZONE_ID"):
        if dry: print("[dry] bunny purgeCache")
        else:
            http("POST", f"https://api.bunny.net/pullzone/{os.environ['BUNNY_PULLZONE_ID']}/purgeCache", {"AccessKey": os.environ["BUNNY_API_KEY"]})
            print("bunny: purgeCache")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dist", default="dist")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    items = files(a.dist)
    if not items:
        sys.exit("dist/ is empty; run npm run build first")
    did = False
    for var in ("S3_PRIMARY_BUCKET", "S3_REPLICA_BUCKET"):
        if os.environ.get(var):
            s3_upload(os.environ[var], items, a.dry_run); did = True
        else:
            print(f"skip: {var} not set")
    if os.environ.get("BUNNY_STORAGE_ZONE") and os.environ.get("BUNNY_STORAGE_PASSWORD"):
        bunny_upload(items, a.dry_run); did = True
    else:
        print("skip: Bunny storage not configured")
    purge(a.dry_run)
    print(json.dumps({"published": did, "files": len(items)}))


if __name__ == "__main__":
    main()
