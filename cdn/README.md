# CDN publishing (ready to apply once accounts / DNS are approved)

| CDN | Config | Origin | Status |
| --- | --- | --- | --- |
| CloudFront (primary) | `cloudfront/template.yaml` (+ `replica.yaml` in us-east-1) | S3 `apphop-site-origin-usw2` via OAC, failover to `-use1` | Blocked: AWS account hold; deploy in us-east-1, then pick the Free flat-rate plan in the console/API |
| Fastly (standby www, apex redirect) | `fastly/main.tf` | S3 `apphop-site-origin-use1` (secret Referer) | Blocked: Fastly account |
| Bunny (standby) | `bunny/bunny_apply.py` | Bunny Storage `apphop-site` (NY + LA, DE replicas) | Blocked: Bunny account |

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
