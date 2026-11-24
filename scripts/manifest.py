#!/usr/bin/env python3
"""Write dist/manifest.json: sha256 of every published file (used by the cross-CDN parity check)."""
import hashlib, json, os, sys

root = sys.argv[1] if len(sys.argv) > 1 else "dist"
out = {}
for d, _, files in os.walk(root):
    for f in files:
        p = os.path.join(d, f)
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        if rel == "manifest.json":
            continue
        out[rel] = hashlib.sha256(open(p, "rb").read()).hexdigest()
build_id = os.environ.get("BUILD_ID") or os.environ.get("GITHUB_SHA") or "dev"
json.dump({"build_id": build_id, "files": dict(sorted(out.items()))}, open(os.path.join(root, "manifest.json"), "w"), indent=1)
print(f"manifest: {len(out)} files, build {build_id}")
