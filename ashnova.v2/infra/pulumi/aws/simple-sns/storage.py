import json
import pulumi
import pulumi_aws as aws
from config import project_name, base_tags


def create_storage_resources():
    posts_table = aws.dynamodb.Table(
        f"{project_name}-posts",
        attributes=[
            aws.dynamodb.TableAttributeArgs(name="PK", type="S"),
            aws.dynamodb.TableAttributeArgs(name="SK", type="S"),
            aws.dynamodb.TableAttributeArgs(name="postId", type="S"),
        ],
        hash_key="PK",
        range_key="SK",
        billing_mode="PAY_PER_REQUEST",
        global_secondary_indexes=[
            aws.dynamodb.TableGlobalSecondaryIndexArgs(
                name="PostIdIndex",
                hash_key="postId",
                projection_type="ALL",
            )
        ],
        tags=base_tags,
    )

    images_bucket = aws.s3.Bucket(
        f"{project_name}-images",
        force_destroy=True,
        cors_rules=[
            aws.s3.BucketCorsRuleArgs(
                allowed_methods=["GET", "PUT", "HEAD"],
                allowed_origins=["*"],
                allowed_headers=["*"],
                expose_headers=["ETag"],
                max_age_seconds=3000,
            )
        ],
        tags=base_tags,
    )

    # Ensure bucket is private (Block Public Access)
    aws.s3.BucketPublicAccessBlock(
        f"{project_name}-images-public-access",
        bucket=images_bucket.id,
        block_public_acls=True,
        block_public_policy=True,
        ignore_public_acls=True,
        restrict_public_buckets=True,
    )

    # CloudFront OAC
    oac = aws.cloudfront.OriginAccessControl(
        f"{project_name}-oac",
        description=f"OAC for {project_name}-images",
        origin_access_control_origin_type="s3",
        signing_behavior="always",
        signing_protocol="sigv4",
    )

    # CloudFront Distribution
    distribution = aws.cloudfront.Distribution(
        f"{project_name}-cdn",
        enabled=True,
        origins=[
            aws.cloudfront.DistributionOriginArgs(
                origin_id=images_bucket.arn,
                domain_name=images_bucket.bucket_regional_domain_name,
                origin_access_control_id=oac.id,
                s3_origin_config=aws.cloudfront.DistributionOriginS3OriginConfigArgs(
                    origin_access_identity="",
                ),
            )
        ],
        default_cache_behavior=aws.cloudfront.DistributionDefaultCacheBehaviorArgs(
            target_origin_id=images_bucket.arn,
            viewer_protocol_policy="redirect-to-https",
            allowed_methods=["GET", "HEAD", "OPTIONS"],
            cached_methods=["GET", "HEAD", "OPTIONS"],
            compress=True,
            forwarded_values=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesArgs(
                query_string=False,
                cookies=aws.cloudfront.DistributionDefaultCacheBehaviorForwardedValuesCookiesArgs(
                    forward="none"
                ),
            ),
        ),
        price_class="PriceClass_100",
        restrictions=aws.cloudfront.DistributionRestrictionsArgs(
            geo_restriction=aws.cloudfront.DistributionRestrictionsGeoRestrictionArgs(
                restriction_type="none",
            )
        ),
        viewer_certificate=aws.cloudfront.DistributionViewerCertificateArgs(
            cloudfront_default_certificate=True
        ),
        tags=base_tags,
    )

    # Bucket Policy for OAC
    aws.s3.BucketPolicy(
        f"{project_name}-images-policy",
        bucket=images_bucket.id,
        policy=pulumi.Output.all(images_bucket.arn, distribution.arn).apply(
            lambda args: json.dumps({
                "Version": "2012-10-17",
                "Statement": [{
                    "Sid": "AllowCloudFrontServicePrincipal",
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "cloudfront.amazonaws.com"
                    },
                    "Action": "s3:GetObject",
                    "Resource": f"{args[0]}/*",
                    "Condition": {
                        "StringEquals": {
                            "AWS:SourceArn": args[1]
                        }
                    }
                }]
            })
        )
    )

    return {
        "posts_table": posts_table,
        "images_bucket": images_bucket,
        "distribution": distribution,
    }
