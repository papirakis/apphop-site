# CDN publishing (ready to apply once accounts / DNS are approved)

| CDN | Config | Origin | Status |
| --- | --- | --- | --- |
| CloudFront (primary) | `cloudfront/template.yaml` (+ `replica.yaml` in us-east-1) | S3 `apphop-site-origin-usw2` via OAC, failover to `-use1` | Blocked: AWS account hold; deploy in us-east-1, then pick the Free flat-rate plan in the console/API |
| Fastly (standby www, apex redirect) | `fastly/main.tf` (prod, S3) and `fastly/staging/` (live now) | Phase 1: Bunny storage, `https://apphop-site.global.ssl.fastly.net` | Live on the shared TLS domain. Prod Terraform stays unused until S3/DNS exist |
| Bunny (standby) | `bunny/bunny_apply.py --staging` | Bunny Storage `apphop-site` (NY + DE replica) | Live at `https://apphop-site.b-cdn.net`. No custom hostnames or DNS zone yet |

No WAF products are defined in these configs. Note: CloudFront's flat-rate plans automatically attach a WAF web
ACL (a plan requirement), so choosing the Free plan brings that in by design.

## Order of operations

1. `aws cloudformation deploy --region us-east-1 --template-file cdn/cloudfront/replica.yaml --stack-name apphop-site-replica --parameter-overrides FastlyOriginSecret=...`
2. `aws cloudformation deploy --region us-east-1 --template-file cdn/cloudfront/template.yaml --stack-name apphop-site-cf --parameter-overrides ReplicaBucketDomain=<output>`
   (no `Aliases` → staging on `dxxxx.cloudfront.net`; add `Aliases` + `AcmCertificateArn` after DNS approval).
   Update the replica stack with `CloudFrontDistributionArn` for origin failover.
3. `cd cdn/fastly && terraform apply -var origin_secret=...`
4. `BUNNY_API_KEY=... python3 cdn/bunny/bunny_apply.py --apply`
5. `npm run build && python3 scripts/publish.py` (env vars listed in the script header)
6. `python3 scripts/parity_check.py --edge cloudfront=... --edge fastly=... --edge bunny=... --host-per-edge`

Secrets (API keys, the origin secret, certificate keys) come from the vault / SSM at run time and are never committed.


## Phase 1 staging (provider hostnames, no custom DNS)

Origin is a **root-path** build of the site uploaded to Bunny storage (`PUBLIC_STAGING=1 SITE_BASE=/`).
Both CDNs pull from that storage so they serve the same bytes.

```bash
. scripts/cdn_env.sh                          # loads ~/.fastly-secure and ~/.bunny-secure (never echo)
python3 cdn/bunny/bunny_apply.py --staging --apply
PUBLIC_STAGING=1 SITE_BASE=/ BUILD_ID=$(git rev-parse HEAD) npm run build
python3 scripts/publish.py
cdn/fastly/staging/apply.sh
python3 scripts/parity_check.py --host-per-edge \
  --edge fastly=apphop-site.global.ssl.fastly.net \
  --edge bunny=apphop-site.b-cdn.net
```

Expected cost at this traffic: Fastly $0 (free tier: 100 GB + 1M requests). Bunny ≈ $1/month
(storage-zone minimum); CDN bandwidth in NA/EU is $0.01/GB and will sit under that minimum.
No Shield, Optimizer, WAF, or paid Fastly add-ons are enabled. A 100 GB Bunny bandwidth cap is set as a safety brake.
