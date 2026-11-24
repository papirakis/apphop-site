#!/usr/bin/env bash
# Issue/renew ONE Let's Encrypt certificate (ECDSA P-256) for apphop.app + www.apphop.app via DNS-01, then the
# caller uploads it to Fastly (BYOC, cdn/fastly) and Bunny (cdn/bunny --cert/--key). CloudFront uses ACM instead.
# Blocked until DNS changes are approved (DNS-01 writes _acme-challenge TXT records).
# DNS provider: porkbun (Option A) or bunny (Option B, www subzone). Credentials come from the environment only.
set -euo pipefail
PROVIDER="${DNS_PROVIDER:-porkbun}"   # lego providers: porkbun (PORKBUN_API_KEY/PORKBUN_SECRET_API_KEY) | bunny (BUNNY_API_KEY)
EMAIL="${ACME_EMAIL:-ops@apphop.app}"
OUT="${CERT_DIR:-$HOME/.apphop-certs}"
mkdir -p "$OUT"; chmod 700 "$OUT"
cmd=run; [ -f "$OUT/certificates/apphop.app.crt" ] && cmd="renew --days 30"
lego --accept-tos --email "$EMAIL" --dns "$PROVIDER" --key-type ec256 --path "$OUT" \
  --domains apphop.app --domains www.apphop.app $cmd
echo "cert: $OUT/certificates/apphop.app.crt  key: $OUT/certificates/apphop.app.key"
