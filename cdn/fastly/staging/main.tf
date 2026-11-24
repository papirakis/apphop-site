# Phase 1 staging Fastly service on the shared TLS domain (no custom DNS).
# Origin: Bunny storage (root-path build) until the AWS hold lifts and S3 is ready.
# Free tier only: no shield, WAF/NGWAF, image optimizer, or logging add-ons.
#
# Apply:
#   . ../../../scripts/cdn_env.sh
#   terraform init
#   terraform import fastly_service_vcl.site "$FASTLY_SERVICE_ID"   # first time, reuse the signup stub
#   terraform apply -var="storage_password=${BUNNY_STORAGE_PASSWORD}" \
#                   -var="storage_host=${BUNNY_STORAGE_HOST}" \
#                   -var="storage_zone=${BUNNY_STORAGE_ZONE}"
terraform {
  required_providers {
    fastly = { source = "fastly/fastly", version = "~> 5.0" }
  }
}

variable "domain" {
  type    = string
  default = "apphop-site.global.ssl.fastly.net"
}

variable "storage_host" {
  type        = string
  default     = "ny.storage.bunnycdn.com"
  description = "Regional Bunny storage hostname (not a secret)."
}

variable "storage_zone" {
  type        = string
  default     = "apphop-site"
  description = "Bunny storage zone name; prepended to the object key on the origin request."
}

variable "storage_password" {
  type        = string
  sensitive   = true
  description = "Bunny storage zone password; from ~/.bunny-secure/bunny.env, never committed."
}

locals {
  # Bunny storage expects /{zone}/{key} plus the AccessKey header.
  origin_prefix = "/${var.storage_zone}"
}

resource "fastly_service_vcl" "site" {
  name = "apphop-site"

  domain {
    name = var.domain
  }

  backend {
    name               = "bunny_storage"
    address            = var.storage_host
    override_host      = var.storage_host
    port               = 443
    use_ssl            = true
    ssl_cert_hostname  = var.storage_host
    ssl_sni_hostname   = var.storage_host
    connect_timeout    = 3000
    first_byte_timeout = 15000
  }

  request_setting {
    name      = "force_tls"
    force_ssl = true
  }

  gzip {
    name          = "compress"
    content_types = ["text/html", "text/css", "application/javascript", "application/json", "image/svg+xml", "application/xml", "application/xml+rss", "application/manifest+json"]
    extensions    = ["html", "css", "js", "json", "svg", "xml", "txt", "webmanifest"]
  }

  snippet {
    name     = "recv"
    type     = "recv"
    priority = 100
    content  = <<-VCL
      if (req.http.AccessKey) { unset req.http.AccessKey; }
      unset req.http.Cookie;
      if (req.http.X-404) {
        set req.url = "/404.html";
      } else {
        if (req.url.path ~ "/$") { set req.url = req.url.path "index.html"; }
        elsif (req.url.path !~ "\.[a-zA-Z0-9]+$") { error 802 "slash"; }
      }
    VCL
  }

  snippet {
    name     = "miss_auth"
    type     = "miss"
    priority = 100
    content  = <<-VCL
      unset bereq.http.Referer;
      unset bereq.http.Origin;
      set bereq.http.AccessKey = "${var.storage_password}";
      set bereq.url = "${local.origin_prefix}" bereq.url;
    VCL
  }

  snippet {
    name     = "pass_auth"
    type     = "pass"
    priority = 100
    content  = <<-VCL
      unset bereq.http.Referer;
      unset bereq.http.Origin;
      set bereq.http.AccessKey = "${var.storage_password}";
      set bereq.url = "${local.origin_prefix}" bereq.url;
    VCL
  }

  snippet {
    name     = "error_redirects"
    type     = "error"
    priority = 100
    content  = <<-VCL
      if (obj.status == 802) {
        set obj.status = 301;
        set obj.response = "Moved Permanently";
        set obj.http.Location = req.url.path "/";
        synthetic "";
        return(deliver);
      }
    VCL
  }

  snippet {
    name     = "fetch_ttl"
    type     = "fetch"
    priority = 100
    content  = <<-VCL
      if (beresp.status == 404 && !req.http.X-404) {
        set req.http.X-404 = "1";
        restart;
      }
      if (req.http.X-404) { set beresp.status = 404; set beresp.ttl = 60s; }
      elsif (bereq.url ~ "/_astro/") { set beresp.ttl = 365d; }
      elsif (beresp.http.Content-Type ~ "text/html" || bereq.url ~ "\.(json|xml|txt)$") { set beresp.ttl = 300s; }
      unset beresp.http.AccessKey;
    VCL
  }

  snippet {
    name     = "deliver_headers"
    type     = "deliver"
    priority = 100
    content  = <<-VCL
      if (req.http.X-404) { set resp.status = 404; }
      set resp.http.Strict-Transport-Security = "max-age=86400";
      set resp.http.X-Content-Type-Options = "nosniff";
      set resp.http.Referrer-Policy = "strict-origin-when-cross-origin";
      set resp.http.X-Frame-Options = "DENY";
      set resp.http.X-Robots-Tag = "noindex, nofollow";
      set resp.http.Content-Security-Policy = "default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'";
      set resp.http.x-served-by-cdn = "fastly";
      unset resp.http.AccessKey;
      unset resp.http.x-amz-request-id;
    VCL
  }

  force_destroy = false
}

output "service_id" { value = fastly_service_vcl.site.id }
output "domain" { value = var.domain }
