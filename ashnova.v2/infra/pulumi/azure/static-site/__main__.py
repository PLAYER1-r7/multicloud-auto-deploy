import hashlib
import mimetypes
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pulumi
import pulumi_azure_native as azure_native

config = pulumi.Config()
project_name = config.get("project_name") or "ashnova-static-site"
environment = config.get("environment") or "prod"
site_dir = config.get("site_dir") or "../../../../ashnova.old/azure/website"
location = config.get("azure:location") or "japaneast"
enable_frontdoor = config.get_bool("enable_frontdoor")
custom_domain = config.get("custom_domain")
custom_tags = config.get_object("tags") or {}

if enable_frontdoor is None:
    enable_frontdoor = True

repo_root = Path(__file__).resolve().parent
content_dir = (repo_root / site_dir).resolve()

if not content_dir.exists():
    raise FileNotFoundError(f"site_dir not found: {content_dir}")


def sanitize_name(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def hyphenated(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def storage_account_name(base: str, env: str, stack: str) -> str:
    seed = f"{base}-{env}-{stack}"
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:6]
    raw = f"{sanitize_name(base)}{sanitize_name(env)}{digest}"
    return raw[:24]


stack = pulumi.get_stack()
account_name = storage_account_name(project_name, environment, stack)
afd_suffix = hashlib.sha1(
    f"afd-{project_name}-{environment}-{stack}".encode("utf-8")).hexdigest()[:6]
afd_profile_name = hyphenated(f"afd-{project_name}-{environment}")
afd_endpoint_name = hyphenated(
    f"afd-{project_name}-{environment}-{afd_suffix}")

resource_group = azure_native.resources.ResourceGroup(
    f"{project_name}-rg",
    resource_group_name=f"rg-{project_name}-{environment}",
    location=location,
    tags={
        "Project": project_name,
        "Environment": environment,
        **custom_tags,
    },
)

storage_account = azure_native.storage.StorageAccount(
    f"{project_name}-storage",
    account_name=account_name,
    resource_group_name=resource_group.name,
    location=resource_group.location,
    kind=azure_native.storage.Kind.STORAGE_V2,
    sku=azure_native.storage.SkuArgs(
        name=azure_native.storage.SkuName.STANDARD_LRS
    ),
    allow_blob_public_access=True,
    minimum_tls_version=azure_native.storage.MinimumTlsVersion.TLS1_2,
    enable_https_traffic_only=True,
    tags=resource_group.tags,
)

static_website = azure_native.storage.StorageAccountStaticWebsite(
    f"{project_name}-static-website",
    account_name=storage_account.name,
    resource_group_name=resource_group.name,
    index_document="index.html",
    error404_document="error.html",
)

web_container = azure_native.storage.BlobContainer(
    f"{project_name}-web-container",
    account_name=storage_account.name,
    container_name="$web",
    public_access=azure_native.storage.PublicAccess.BLOB,
    resource_group_name=resource_group.name,
)


def iter_site_files(root_dir: Path) -> Iterable[Tuple[str, Path]]:
    for path in root_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root_dir).as_posix()
            yield rel, path


def content_type_for(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.as_posix())
    return content_type or "application/octet-stream"


site_objects: Dict[str, azure_native.storage.Blob] = {}
for rel_path, full_path in iter_site_files(content_dir):
    site_objects[rel_path] = azure_native.storage.Blob(
        f"{project_name}-{rel_path.replace('/', '-')}",
        account_name=storage_account.name,
        resource_group_name=resource_group.name,
        container_name=web_container.name,
        blob_name=rel_path,
        content_type=content_type_for(full_path),
        source=pulumi.FileAsset(str(full_path)),
    )

frontdoor_endpoint_host = None
frontdoor_custom_domain_host = None
if enable_frontdoor:
    afd_profile = azure_native.cdn.Profile(
        f"{project_name}-afd-profile",
        profile_name=afd_profile_name,
        resource_group_name=resource_group.name,
        location="global",
        sku=azure_native.cdn.SkuArgs(
            name=azure_native.cdn.SkuName.STANDARD_AZURE_FRONT_DOOR,
        ),
        tags=resource_group.tags,
    )

    afd_endpoint = azure_native.cdn.AFDEndpoint(
        f"{project_name}-afd-endpoint",
        endpoint_name=afd_endpoint_name,
        profile_name=afd_profile.name,
        resource_group_name=resource_group.name,
        enabled_state=azure_native.cdn.EnabledState.ENABLED,
        location="global",
        tags=resource_group.tags,
    )

    def host_from_url(url: str) -> str:
        return url.replace("https://", "").replace("http://", "").rstrip("/")

    web_origin_host = storage_account.primary_endpoints.apply(
        lambda endpoints: host_from_url(
            endpoints.web) if endpoints and endpoints.web else ""
    )

    origin_group = azure_native.cdn.AFDOriginGroup(
        f"{project_name}-afd-origin-group",
        profile_name=afd_profile.name,
        resource_group_name=resource_group.name,
        origin_group_name=f"og-{project_name}-{environment}",
        load_balancing_settings=azure_native.cdn.LoadBalancingSettingsParametersArgs(
            sample_size=4,
            successful_samples_required=3,
            additional_latency_in_milliseconds=0,
        ),
        health_probe_settings=azure_native.cdn.HealthProbeParametersArgs(
            probe_protocol=azure_native.cdn.ProbeProtocol.HTTPS,
            probe_request_type=azure_native.cdn.HealthProbeRequestType.HEAD,
            probe_interval_in_seconds=120,
            probe_path="/",
        ),
    )

    origin = azure_native.cdn.AFDOrigin(
        f"{project_name}-afd-origin",
        origin_name=f"origin-{project_name}",
        profile_name=afd_profile.name,
        resource_group_name=resource_group.name,
        origin_group_name=origin_group.name,
        host_name=web_origin_host,
        origin_host_header=web_origin_host,
        https_port=443,
        http_port=80,
        enabled_state=azure_native.cdn.EnabledState.ENABLED,
        enforce_certificate_name_check=True,
        priority=1,
        weight=1000,
    )

    afd_custom_domain = None
    if custom_domain:
        afd_custom_domain = azure_native.cdn.AFDCustomDomain(
            f"{project_name}-afd-custom-domain",
            custom_domain_name=hyphenated(custom_domain),
            host_name=custom_domain,
            profile_name=afd_profile.name,
            resource_group_name=resource_group.name,
            tls_settings=azure_native.cdn.AFDDomainHttpsParametersArgs(
                certificate_type=azure_native.cdn.AfdCertificateType.MANAGED_CERTIFICATE,
                minimum_tls_version=azure_native.cdn.AfdMinimumTlsVersion.TLS12,
            ),
        )
        frontdoor_custom_domain_host = custom_domain

    route = azure_native.cdn.Route(
        f"{project_name}-afd-route",
        route_name=f"route-{project_name}-{environment}",
        endpoint_name=afd_endpoint.name,
        profile_name=afd_profile.name,
        resource_group_name=resource_group.name,
        origin_group=azure_native.cdn.ResourceReferenceArgs(
            id=origin_group.id),
        supported_protocols=[
            azure_native.cdn.AFDEndpointProtocols.HTTP,
            azure_native.cdn.AFDEndpointProtocols.HTTPS,
        ],
        patterns_to_match=["/*"],
        forwarding_protocol=azure_native.cdn.ForwardingProtocol.HTTPS_ONLY,
        https_redirect=azure_native.cdn.HttpsRedirect.ENABLED,
        link_to_default_domain=azure_native.cdn.LinkToDefaultDomain.ENABLED,
        custom_domains=(
            [azure_native.cdn.ActivatedResourceReferenceArgs(
                id=afd_custom_domain.id)]
            if afd_custom_domain
            else None
        ),
        opts=pulumi.ResourceOptions(depends_on=[origin_group, origin]),
    )

    frontdoor_endpoint_host = afd_endpoint.host_name

static_url = storage_account.primary_endpoints.apply(
    lambda endpoints: endpoints.web if endpoints else None
)

pulumi.export("storage_account_name", storage_account.name)
pulumi.export("static_website_url", static_url)
pulumi.export("frontdoor_endpoint_host", frontdoor_endpoint_host)
pulumi.export("frontdoor_custom_domain", frontdoor_custom_domain_host)
