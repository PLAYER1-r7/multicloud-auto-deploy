import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pulumi
import pulumi_gcp as gcp

config = pulumi.Config()
project_name = config.get("project_name") or "ashnova"
environment = config.get("environment") or "production"
site_dir = config.get("site_dir") or "../../../../ashnova.old/gcp/website"
enable_cdn = config.get_bool("enable_cdn")
bucket_location = config.get("bucket_location") or "ASIA"
custom_domain = config.get("custom_domain") or ""

if enable_cdn is None:
    enable_cdn = True

repo_root = Path(__file__).resolve().parent
content_dir = (repo_root / site_dir).resolve()

if not content_dir.exists():
    raise FileNotFoundError(f"site_dir not found: {content_dir}")


def name_suffix(base: str, env: str, stack: str) -> str:
    return hashlib.sha1(f"{base}-{env}-{stack}".encode("utf-8")).hexdigest()[:6]


def bucket_name(base: str, env: str, stack: str) -> str:
    digest = name_suffix(base, env, stack)
    name = f"{base}-{env}-{digest}".lower()
    return name.replace("_", "-")


def resource_name(base: str, env: str, stack: str, suffix: str) -> str:
    return f"{base}-{env}-{suffix}".lower().replace("_", "-")


stack = pulumi.get_stack()
suffix = name_suffix(project_name, environment, stack)
logs_bucket = gcp.storage.Bucket(
    "static-site-logs",
    name=bucket_name(f"{project_name}-logs", environment, stack),
    location=bucket_location,
    uniform_bucket_level_access=True,
    force_destroy=True,
)

site_bucket = gcp.storage.Bucket(
    "static-site-bucket",
    name=bucket_name(project_name, environment, stack),
    location=bucket_location,
    uniform_bucket_level_access=True,
    force_destroy=True,
    website=gcp.storage.BucketWebsiteArgs(
        main_page_suffix="index.html",
        not_found_page="error.html",
    ),
    versioning=gcp.storage.BucketVersioningArgs(enabled=True),
    logging=gcp.storage.BucketLoggingArgs(
        log_bucket=logs_bucket.name,
        log_object_prefix="gcs-logs/",
    ),
)

bucket_iam = gcp.storage.BucketIAMMember(
    "static-site-public",
    bucket=site_bucket.name,
    role="roles/storage.objectViewer",
    member="allUsers",
)


def iter_site_files(root_dir: Path) -> Iterable[Tuple[str, Path]]:
    for path in root_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root_dir).as_posix()
            yield rel, path


def content_type_for(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.as_posix())
    return content_type or "application/octet-stream"


site_objects: Dict[str, gcp.storage.BucketObject] = {}
for rel_path, full_path in iter_site_files(content_dir):
    site_objects[rel_path] = gcp.storage.BucketObject(
        f"static-site-{rel_path.replace('/', '-')}",
        bucket=site_bucket.name,
        name=rel_path,
        source=pulumi.FileAsset(str(full_path)),
        content_type=content_type_for(full_path),
    )

cdn_ip_address = None
website_url = pulumi.Output.concat(
    "http://", site_bucket.name, ".storage.googleapis.com")

if enable_cdn:
    lb_ip = gcp.compute.GlobalAddress(
        "static-site-ip",
        name=resource_name(project_name, environment, stack, f"ip-{suffix}"),
    )

    backend_bucket = gcp.compute.BackendBucket(
        "static-site-backend",
        name=resource_name(project_name, environment,
                           stack, f"backend-{suffix}"),
        bucket_name=site_bucket.name,
        enable_cdn=True,
        cdn_policy=gcp.compute.BackendBucketCdnPolicyArgs(
            cache_mode="CACHE_ALL_STATIC",
            client_ttl=3600,
            default_ttl=3600,
            max_ttl=86400,
            negative_caching=True,
            serve_while_stale=86400,
        ),
    )

    url_map = gcp.compute.URLMap(
        "static-site-urlmap",
        name=resource_name(project_name, environment,
                           stack, f"urlmap-{suffix}"),
        default_service=backend_bucket.self_link,
    )

    http_proxy = gcp.compute.TargetHttpProxy(
        "static-site-http-proxy",
        name=resource_name(project_name, environment,
                           stack, f"http-proxy-{suffix}"),
        url_map=url_map.self_link,
    )

    http_forwarding_rule = gcp.compute.GlobalForwardingRule(
        "static-site-http-forwarding",
        name=resource_name(project_name, environment,
                           stack, f"http-rule-{suffix}"),
        target=http_proxy.self_link,
        port_range="80",
        ip_address=lb_ip.address,
    )

    if custom_domain:
        ssl_cert = gcp.compute.ManagedSslCertificate(
            "static-site-cert",
            name=resource_name(project_name, environment,
                               stack, f"cert-{suffix}"),
            managed=gcp.compute.ManagedSslCertificateManagedArgs(
                domains=[custom_domain],
            ),
        )

        https_proxy = gcp.compute.TargetHttpsProxy(
            "static-site-https-proxy",
            name=resource_name(project_name, environment,
                               stack, f"https-proxy-{suffix}"),
            url_map=url_map.self_link,
            ssl_certificates=[ssl_cert.self_link],
        )

        https_forwarding_rule = gcp.compute.GlobalForwardingRule(
            "static-site-https-forwarding",
            name=resource_name(project_name, environment,
                               stack, f"https-rule-{suffix}"),
            target=https_proxy.self_link,
            port_range="443",
            ip_address=lb_ip.address,
        )

    cdn_ip_address = lb_ip.address
    website_url = pulumi.Output.concat("http://", lb_ip.address)

pulumi.export("bucket_name", site_bucket.name)
pulumi.export("website_url", website_url)
pulumi.export("cdn_ip_address", cdn_ip_address)
