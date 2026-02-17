import mimetypes
import os
from pathlib import Path
from typing import Dict, Iterable, Tuple

import pulumi
import pulumi_aws as aws

config = pulumi.Config()
project_name = config.get("project_name") or "ashnova-static-site"
site_dir = config.get("site_dir") or "../../../../static-site"
enable_cloudfront = config.get_bool("enable_cloudfront")
aws_profile = config.get("aws_profile") or os.getenv(
    "AWS_PROFILE") or os.getenv("AWS_DEFAULT_PROFILE")
domain_name = config.get("domain_name")
zone_id = config.get("zone_id")
price_class = config.get("price_class") or "PriceClass_100"
force_destroy = config.get_bool("force_destroy") or False

if enable_cloudfront is None:
    enable_cloudfront = True

repo_root = Path(__file__).resolve().parent
content_dir = (repo_root / site_dir).resolve()

if not content_dir.exists():
    raise FileNotFoundError(f"site_dir not found: {content_dir}")

bucket = aws.s3.Bucket(
    f"{project_name}-bucket",
    bucket=f"{project_name}-{pulumi.get_stack()}".lower(),
    force_destroy=force_destroy,
)

bucket_versioning = aws.s3.BucketVersioning(
    f"{project_name}-versioning",
    bucket=bucket.id,
    versioning_configuration=aws.s3.BucketVersioningVersioningConfigurationArgs(
        status="Enabled",
    ),
)

bucket_encryption = aws.s3.BucketServerSideEncryptionConfiguration(
    f"{project_name}-encryption",
    bucket=bucket.id,
    rules=[
        aws.s3.BucketServerSideEncryptionConfigurationRuleArgs(
            apply_server_side_encryption_by_default=aws.s3.BucketServerSideEncryptionConfigurationRuleApplyServerSideEncryptionByDefaultArgs(
                sse_algorithm="AES256",
            )
        )
    ],
)

public_access_block = aws.s3.BucketPublicAccessBlock(
    f"{project_name}-public-access",
    bucket=bucket.id,
    block_public_acls=enable_cloudfront,
    block_public_policy=enable_cloudfront,
    ignore_public_acls=enable_cloudfront,
    restrict_public_buckets=enable_cloudfront,
)

website_config = None
if not enable_cloudfront:
    website_config = aws.s3.BucketWebsiteConfiguration(
        f"{project_name}-website",
        bucket=bucket.id,
        index_document=aws.s3.BucketWebsiteConfigurationIndexDocumentArgs(
            suffix="index.html"),
        error_document=aws.s3.BucketWebsiteConfigurationErrorDocumentArgs(
            key="error.html"),
    )

if not enable_cloudfront:
    bucket_policy = aws.s3.BucketPolicy(
        f"{project_name}-public-policy",
        bucket=bucket.id,
        policy=bucket.id.apply(
            lambda bucket_name: aws.iam.get_policy_document(
                statements=[
                    aws.iam.GetPolicyDocumentStatementArgs(
                        actions=["s3:GetObject"],
                        resources=[f"arn:aws:s3:::{bucket_name}/*"],
                        principals=[
                            aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                                type="*",
                                identifiers=["*"],
                            )
                        ],
                    )
                ]
            ).json
        ),
    )
else:
    bucket_policy = None

us_east_1 = aws.Provider(
    "us-east-1",
    region="us-east-1",
    profile=aws_profile,
) if aws_profile else aws.Provider("us-east-1", region="us-east-1")

certificate = None
certificate_validation = None
validation_record_details = []
if domain_name:
    certificate = aws.acm.Certificate(
        f"{project_name}-cert",
        domain_name=domain_name,
        validation_method="DNS",
        opts=pulumi.ResourceOptions(provider=us_east_1),
    )

    validation_record_details = certificate.domain_validation_options.apply(
        lambda options: [
            {
                "name": option.resource_record_name,
                "type": option.resource_record_type,
                "value": option.resource_record_value,
            }
            for option in options
        ]
    )

    if zone_id:
        def create_route53_records(options):
            for option in options:
                aws.route53.Record(
                    f"{project_name}-cert-validation-{option.domain_name}",
                    name=option.resource_record_name,
                    type=option.resource_record_type,
                    zone_id=zone_id,
                    records=[option.resource_record_value],
                    ttl=300,
                )
            return True

        certificate.domain_validation_options.apply(create_route53_records)

    certificate_validation = aws.acm.CertificateValidation(
        f"{project_name}-cert-validation",
        certificate_arn=certificate.arn,
        validation_record_fqdns=certificate.domain_validation_options.apply(
            lambda options: [option.resource_record_name for option in options]
        ),
        opts=pulumi.ResourceOptions(provider=us_east_1),
    )

response_headers_policy = aws.cloudfront.ResponseHeadersPolicy(
    f"{project_name}-security-headers",
    security_headers_config=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigArgs(
        content_security_policy=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigContentSecurityPolicyArgs(
            content_security_policy="default-src 'self'",
            override=True,
        ),
        content_type_options=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigContentTypeOptionsArgs(
            override=True
        ),
        frame_options=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigFrameOptionsArgs(
            frame_option="DENY",
            override=True,
        ),
        referrer_policy=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigReferrerPolicyArgs(
            referrer_policy="no-referrer",
            override=True,
        ),
        strict_transport_security=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigStrictTransportSecurityArgs(
            access_control_max_age_sec=31536000,
            include_subdomains=True,
            preload=True,
            override=True,
        ),
        xss_protection=aws.cloudfront.ResponseHeadersPolicySecurityHeadersConfigXssProtectionArgs(
            protection=True,
            mode_block=True,
            override=True,
        ),
    ),
)

origin_access_control = None
cloudfront_distribution = None
if enable_cloudfront:
    origin_access_control = aws.cloudfront.OriginAccessControl(
        f"{project_name}-oac",
        description=f"OAC for {project_name}",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
    )

    cloudfront_distribution = aws.cloudfront.Distribution(
        f"{project_name}-cdn",
        enabled=True,
        origins=[
            aws.cloudfront.DistributionOriginArgs(
                origin_id=bucket.arn,
                domain_name=bucket.bucket_regional_domain_name,
                origin_access_control_id=origin_access_control.id,
                s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                    origin_access_identity="",
                ),
            )
        ],
        default_root_object="index.html",
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=bucket.arn,
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            cached_methods=["GET", "HEAD", "OPTIONS"],
            compress=True,
            response_headers_policy_id=response_headers_policy.id,
            forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                query_string=False,
                cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                    forward="none"
                ),
            ),
        ),
        price_class=price_class,
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            )
        ),
        viewer_certificate=(
            aws.cloudfront.DistributionViewerCertificateArgs(
                acm_certificate_arn=certificate_validation.certificate_arn,
                ssl_support_method="sni-only",
                minimum_protocol_version="TLSv1.2_2021",
            )
            if certificate_validation
            else aws.cloudfront.DistributionViewerCertificateArgs(
                cloudfront_default_certificate=True
            )
        ),
        aliases=[domain_name] if domain_name else None,
        custom_error_responses=[
            aws.cloudfront.DistributionCustomErrorResponseArgs(
                error_code=404,
                response_code=404,
                response_page_path="/error.html",
            )
        ],
    )

    bucket_policy = aws.s3.BucketPolicy(
        f"{project_name}-oac-policy",
        bucket=bucket.id,
        policy=pulumi.Output.all(bucket.arn, cloudfront_distribution.arn).apply(
            lambda args: aws.iam.get_policy_document(
                statements=[
                    aws.iam.GetPolicyDocumentStatementArgs(
                        actions=["s3:GetObject"],
                        resources=[f"{args[0]}/*"],
                        principals=[
                            aws.iam.GetPolicyDocumentStatementPrincipalArgs(
                                type="Service",
                                identifiers=["cloudfront.amazonaws.com"],
                            )
                        ],
                        conditions=[
                            aws.iam.GetPolicyDocumentStatementConditionArgs(
                                test="StringEquals",
                                variable="AWS:SourceArn",
                                values=[args[1]],
                            )
                        ],
                    )
                ]
            ).json
        ),
    )


def iter_site_files(root_dir: Path) -> Iterable[Tuple[str, Path]]:
    for path in root_dir.rglob("*"):
        if path.is_file():
            rel = path.relative_to(root_dir).as_posix()
            yield rel, path


def content_type_for(path: Path) -> str:
    content_type, _ = mimetypes.guess_type(path.as_posix())
    return content_type or "application/octet-stream"


site_objects: Dict[str, aws.s3.BucketObject] = {}
for rel_path, full_path in iter_site_files(content_dir):
    site_objects[rel_path] = aws.s3.BucketObject(
        f"{project_name}-{rel_path.replace('/', '-')}",
        bucket=bucket.id,
        key=rel_path,
        source=pulumi.FileAsset(str(full_path)),
        content_type=content_type_for(full_path),
    )

website_url = None
if enable_cloudfront:
    website_url = cloudfront_distribution.domain_name
else:
    website_url = bucket.website_endpoint

pulumi.export("bucket_name", bucket.bucket)
pulumi.export("cloudfront_domain_name",
              cloudfront_distribution.domain_name if cloudfront_distribution else "")
pulumi.export("website_url", website_url)
pulumi.export("acm_validation_records", validation_record_details)
