# Fastly service (Terraform)

## Phase 1 staging (live)

Shared-TLS hostname, no custom DNS, no paid add-ons. Origin is Bunny storage until the AWS hold lifts.

```bash
. ../../scripts/cdn_env.sh
cdn/fastly/staging/apply.sh
```

- URL: `https://apphop-site.global.ssl.fastly.net`
- The signup stub service (`AppHop's website`) was imported and renamed to `apphop-site`.
- HTTP on this shared SSL domain is not used; clients should use HTTPS.
- Header `x-served-by-cdn: fastly`. Staging responses also send `X-Robots-Tag: noindex, nofollow`.

Terraform state stays local and is gitignored (it includes the storage-origin credential).

## Production (blocked: S3 origin + DNS)

Blocked until the Fastly account exists. Then:

```bash
export FASTLY_API_KEY=...            # from the vault, never committed
terraform init
terraform apply -var origin_secret=... [-var tls_cert_pem=... -var tls_key_pem=...]
```

- Origin: `apphop-site-origin-use1` (S3, us-east-1), admitted by the secret Referer (see `../cloudfront/replica.yaml`).
- Apex `apphop.app` gets a 301 to `https://www.apphop.app` at the edge. DNS for the apex uses the anycast A/AAAA
  records shown in the Fastly TLS configuration (Phase 2, needs DNS approval).
- CNAME target for `www` when steered here: the `*.global.ssl.fastly.net` / `*.map.fastly.net` name from the TLS config.
- Header `x-served-by-cdn: fastly` lets probes and dashboards confirm which CDN answered.
