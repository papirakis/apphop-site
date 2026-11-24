#!/bin/sh
# Apply the Phase 1 Fastly staging service. Credentials come from chmod 600 env files.
# Secrets are passed as TF_VAR_* environment variables (not argv). Never printed.
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# shellcheck disable=SC1091
. "$HERE/../../../scripts/cdn_env.sh"
: "${FASTLY_API_KEY:?FASTLY_API_KEY/TOKEN missing from ~/.fastly-secure/fastly.env}"
: "${BUNNY_STORAGE_PASSWORD:?BUNNY_STORAGE_PASSWORD missing from ~/.bunny-secure/bunny.env}"
: "${BUNNY_STORAGE_HOST:?}"
: "${BUNNY_STORAGE_ZONE:?}"
export FASTLY_API_KEY
export TF_VAR_storage_password="$BUNNY_STORAGE_PASSWORD"
export TF_VAR_storage_host="$BUNNY_STORAGE_HOST"
export TF_VAR_storage_zone="$BUNNY_STORAGE_ZONE"
cd "$HERE"
terraform init -input=false
if [ -n "${FASTLY_SERVICE_ID:-}" ]; then
  if ! terraform state show fastly_service_vcl.site >/dev/null 2>&1; then
    terraform import -input=false fastly_service_vcl.site "$FASTLY_SERVICE_ID"
  fi
fi
terraform apply -input=false -auto-approve
SID=$(terraform output -raw service_id)
export SID
python3 - << 'PY'
import os
path = os.path.expanduser("~/.fastly-secure/fastly.env")
sid = os.environ["SID"].strip()
kv = {}
if os.path.exists(path):
    for line in open(path):
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.rstrip("\n").split("=", 1)
            kv[k] = v
kv["FASTLY_SERVICE_ID"] = sid
tmp = path + ".tmp"
with open(tmp, "w") as f:
    for k, v in kv.items():
        f.write(f"{k}={v}\n")
os.chmod(tmp, 0o600)
os.replace(tmp, path)
os.chmod(path, 0o600)
print("fastly service id stored")
PY
