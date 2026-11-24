# Fastly (standby CDN for www, primary for the apex redirect). Free tier: 100 GB + 1M requests / month.
# Apply after the Fastly account exists:  export FASTLY_API_KEY=...; terraform init; terraform apply
# No WAF / Next-Gen WAF products are configured.
terraform {
  required_providers {
    fastly = { source = "fastly/fastly", version = "~> 5.0" }
  }
}

variable "replica_bucket" { default = "apphop-site-origin-use1" }
variable "replica_region" { default = "us-east-1" }
variable "origin_secret" {
  type        = string
  sensitive   = true
  description = "Same value as FastlyOriginSecret in cdn/cloudfront/replica.yaml (sent as Referer to S3)."
}
variable "domains" {
  type    = list(string)
  default = ["www.apphop.app", "apphop.app"]
}
variable "enable_logging" {
  type    = bool
  default = false
}
variable "log_bucket" { default = "apphop-site-cdn-logs" }
variable "log_access_key" {
  type      = string
  sensitive = true
  default   = ""
}
variable "log_secret_key" {
  type      = string
  sensitive = true
  default   = ""
}
# Optional BYOC: paths written by scripts/acme_issue.sh (one Let's Encrypt cert reused on Fastly + Bunny).
variable "tls_cert_pem" { default = "" }
variable "tls_key_pem" {
  default   = ""
  sensitive = true
}

locals {
  origin_host = "${var.replica_bucket}.s3.${var.replica_region}.amazonaws.com"
}

resource "fastly_service_vcl" "site" {
  name = "apphop-site"

  dynamic "domain" {
    for_each = var.domains
    content { name = domain.value }
  }

  backend {
    name               = "s3_replica"
    address            = local.origin_host
    override_host      = local.origin_host
    port               = 443
    use_ssl            = true
    ssl_cert_hostname  = local.origin_host
    ssl_sni_hostname   = local.origin_host
    shield             = "iad-va-us" # origin shield near us-east-1
    connect_timeout    = 3000
    first_byte_timeout = 15000
  }

  gzip {
    name          = "compress"
    content_types = ["text/html", "text/css", "application/javascript", "application/json", "image/svg+xml", "application/xml"]
    extensions    = ["html", "css", "js", "json", "svg", "xml"]
  }

  snippet {
    name    = "recv"
    type    = "recv"
    content = <<-VCL
      if (req.http.host == "apphop.app") { error 801 "apex"; }
      if (req.url.path ~ "/$") { set req.url = req.url.path "index.html"; }
      elsif (req.url.path !~ "\.[a-zA-Z0-9]+$") { error 802 "slash"; }
      set req.http.Referer = "${var.origin_secret}";
      unset req.http.Cookie;
    VCL
  }

  snippet {
    name    = "error_redirects"
    type    = "error"
    content = <<-VCL
      if (obj.status == 801) {
        set obj.status = 301; set obj.response = "Moved Permanently";
        set obj.http.Location = "https://www.apphop.app" req.url;
        set obj.http.Strict-Transport-Security = "max-age=63072000; includeSubDomains";
        synthetic ""; return(deliver);
      }
      if (obj.status == 802) {
        set obj.status = 301; set obj.response = "Moved Permanently";
        set obj.http.Location = req.url.path "/";
        synthetic ""; return(deliver);
      }
    VCL
  }

  snippet {
    name    = "fetch_ttl"
    type    = "fetch"
    content = <<-VCL
      if (beresp.status == 403 || beresp.status == 404) { set beresp.ttl = 60s; return(deliver); }
      if (bereq.url ~ "^/_astro/") { set beresp.ttl = 365d; }
      elsif (beresp.http.Content-Type ~ "text/html" || bereq.url ~ "\.(json|xml|txt)$") { set beresp.ttl = 300s; }
    VCL
  }

  snippet {
    name    = "deliver_headers"
    type    = "deliver"
    content = <<-VCL
      set resp.http.Strict-Transport-Security = "max-age=63072000; includeSubDomains";
      set resp.http.X-Content-Type-Options = "nosniff";
      set resp.http.Referrer-Policy = "strict-origin-when-cross-origin";
      set resp.http.X-Frame-Options = "DENY";
      set resp.http.Content-Security-Policy = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'";
      set resp.http.x-served-by-cdn = "fastly";
      unset resp.http.x-amz-request-id; unset resp.http.x-amz-id-2; unset resp.http.x-amz-version-id;
    VCL
  }

  # Real-time log streaming to S3 (JSON lines) for the ops dashboard. Disabled until keys are provided.
  dynamic "logging_s3" {
    for_each = var.enable_logging ? ["on"] : []
    content {
      name          = "ops-lake"
      bucket_name   = var.log_bucket
      domain        = "s3.us-west-2.amazonaws.com"
      path          = "/fastly/%Y/%m/%d/"
      period        = 300
      gzip_level    = 6
      message_type  = "blank"
      s3_access_key = var.log_access_key
      s3_secret_key = var.log_secret_key
      format        = "{\"ts\":\"%%{begin:%Y-%m-%dT%H:%M:%SZ}t\",\"host\":\"%%{req.http.host}V\",\"path\":\"%%{json.escape(req.url.path)}V\",\"status\":%%{resp.status}V,\"bytes\":%%{resp.bytes_written}V,\"cache\":\"%%{fastly_info.state}V\",\"pop\":\"%%{server.datacenter}V\",\"ttfb_us\":%%{time.to_first_byte}V,\"country\":\"%%{client.geo.country_code}V\"}"
    }
  }

  force_destroy = false
}

resource "fastly_tls_private_key" "byoc" {
  count   = var.tls_key_pem == "" ? 0 : 1
  key_pem = file(var.tls_key_pem)
  name    = "apphop-site-le"
}

resource "fastly_tls_certificate" "byoc" {
  count            = var.tls_cert_pem == "" ? 0 : 1
  certificate_body = file(var.tls_cert_pem)
  name             = "apphop-site-le"
  depends_on       = [fastly_tls_private_key.byoc]
}

output "service_id" { value = fastly_service_vcl.site.id }
