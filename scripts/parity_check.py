#!/usr/bin/env python3
"""
Cross-CDN parity check (doc section 3.1). Connects to each CDN edge DIRECTLY (bypassing public DNS) with
TLS SNI + Host set to the public hostname, then compares build_id and file hashes against dist/manifest.json.
A deploy is "done" only when every enabled CDN passes; a failing CDN is reported ineligible for steering.

  python3 scripts/parity_check.py --edge cloudfront=dxxxx.cloudfront.net --edge fastly=xyz.global.ssl.fastly.net \
      --edge bunny=apphop.b-cdn.net [--host www.apphop.app] [--sample 20]

Before DNS/certs exist, pass --host equal to each edge's own name with --host-per-edge.
Exit code 0 = all pass, 1 = at least one CDN failed.
"""
import argparse, hashlib, http.client, json, random, socket, ssl, sys

PREFIX = ""  # set by --prefix, e.g. /apphop-site for GitHub Pages staging
HEADERS_REQUIRED = ["strict-transport-security", "x-content-type-options", "referrer-policy"]


def fetch(edge, host, path, timeout=10):
    ip = socket.getaddrinfo(edge, 443, proto=socket.IPPROTO_TCP)[0][4][0]
    ctx = ssl.create_default_context()
    raw = socket.create_connection((ip, 443), timeout=timeout)
    tls = ctx.wrap_socket(raw, server_hostname=host)
    conn = http.client.HTTPConnection(host, timeout=timeout)
    conn.sock = tls
    conn.request("GET", PREFIX + "/" + path.lstrip("/"), headers={"Host": host, "User-Agent": "apphop-parity/1", "Accept-Encoding": "identity"})
    r = conn.getresponse()
    body = r.read()
    hdrs = {k.lower(): v for k, v in r.getheaders()}
    conn.close()
    return r.status, hdrs, body


def check(name, edge, host, manifest, sample):
    problems = []
    try:
        st, h, body = fetch(edge, host, "healthz.json")
        bid = json.loads(body).get("build_id") if st == 200 else None
        if bid != manifest["build_id"]:
            problems.append(f"build_id {bid!r} != {manifest['build_id']!r}")
        for hh in HEADERS_REQUIRED:
            if hh not in h:
                problems.append(f"missing header {hh}")
        paths = [p for p in manifest["files"] if p != "healthz.json"]
        random.seed(manifest["build_id"])
        for p in random.sample(paths, min(sample, len(paths))):
            st, _, body = fetch(edge, host, p)
            if st != 200:
                problems.append(f"{p}: HTTP {st}")
            elif hashlib.sha256(body).hexdigest() != manifest["files"][p]:
                problems.append(f"{p}: hash mismatch")
    except Exception as e:  # noqa: BLE001 - report any failure as a parity failure
        problems.append(f"error: {e}")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--edge", action="append", required=True, help="name=edge-hostname")
    ap.add_argument("--host", default="www.apphop.app")
    ap.add_argument("--host-per-edge", action="store_true", help="use each edge's own hostname as SNI/Host (pre-DNS)")
    ap.add_argument("--manifest", default="dist/manifest.json")
    ap.add_argument("--sample", type=int, default=20)
    ap.add_argument("--prefix", default="", help="path prefix, e.g. /apphop-site on GitHub Pages")
    ap.add_argument("--no-headers", action="store_true", help="skip security-header checks (staging hosts we don't control)")
    a = ap.parse_args()
    global PREFIX
    PREFIX = a.prefix.rstrip("/")
    if a.no_headers:
        HEADERS_REQUIRED.clear()
    manifest = json.load(open(a.manifest))
    report, ok = {}, True
    for spec in a.edge:
        name, edge = spec.split("=", 1)
        host = edge if a.host_per_edge else a.host
        probs = check(name, edge, host, manifest, a.sample)
        report[name] = {"eligible": not probs, "problems": probs}
        ok &= not probs
    print(json.dumps({"build_id": manifest["build_id"], "cdns": report}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
