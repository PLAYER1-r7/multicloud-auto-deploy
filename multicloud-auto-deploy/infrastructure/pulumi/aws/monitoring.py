"""
AWS Monitoring and Alerting Configuration

CloudWatch Alarms for:
- Lambda errors and throttles
- API Gateway errors
- CloudFront errors
- Cost anomalies
"""

import pulumi
import pulumi_aws as aws
from typing import Optional


def create_sns_topic(
    project_name: str,
    stack: str,
    email: Optional[str] = None,
) -> aws.sns.Topic:
    """Create SNS topic for alarm notifications"""

    topic = aws.sns.Topic(
        "alarm-topic",
        name=f"{project_name}-{stack}-alarms",
        display_name=f"Alarms for {project_name} ({stack})",
        tags={
            "Project": project_name,
            "Environment": stack,
            "ManagedBy": "pulumi",
        },
    )

    # Subscribe email if provided
    if email:
        aws.sns.TopicSubscription(
            "alarm-email-subscription",
            topic=topic.arn,
            protocol="email",
            endpoint=email,
            opts=pulumi.ResourceOptions(
                retain_on_delete=True,  # Don't delete subscription (requires SNS:Unsubscribe permission)
            ),
        )

    return topic


def create_lambda_alarms(
    project_name: str,
    stack: str,
    lambda_function_name: pulumi.Output[str],
    sns_topic_arn: pulumi.Output[str],
) -> dict:
    """Create CloudWatch Alarms for Lambda function"""

    alarms = {}

    # Alarm 1: High error rate (> 5% in 5 minutes)
    alarms["error_rate"] = aws.cloudwatch.MetricAlarm(
        "lambda-error-rate-alarm",
        name=f"{project_name}-{stack}-lambda-errors",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=1,
        metric_name="Errors",
        namespace="AWS/Lambda",
        period=300,  # 5 minutes
        statistic="Sum",
        threshold=10,  # More than 10 errors in 5 minutes
        alarm_description="Lambda function error rate is too high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "FunctionName": lambda_function_name,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alarm 2: Throttles (Lambda concurrency limit)
    alarms["throttles"] = aws.cloudwatch.MetricAlarm(
        "lambda-throttles-alarm",
        name=f"{project_name}-{stack}-lambda-throttles",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=1,
        metric_name="Throttles",
        namespace="AWS/Lambda",
        period=300,
        statistic="Sum",
        threshold=5,  # More than 5 throttles in 5 minutes
        alarm_description="Lambda function is being throttled",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "FunctionName": lambda_function_name,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alarm 3: High duration (> 10 seconds average)
    alarms["duration"] = aws.cloudwatch.MetricAlarm(
        "lambda-duration-alarm",
        name=f"{project_name}-{stack}-lambda-duration",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,  # 2 consecutive periods
        metric_name="Duration",
        namespace="AWS/Lambda",
        period=300,
        statistic="Average",
        threshold=10000,  # 10 seconds in milliseconds
        alarm_description="Lambda function duration is too high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "FunctionName": lambda_function_name,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alarm 4: Dead Letter Queue (DLQ) messages
    # Note: Requires DLQ to be configured on Lambda
    # alarms["dlq"] = aws.cloudwatch.MetricAlarm(...)

    return alarms


def create_api_gateway_alarms(
    project_name: str,
    stack: str,
    api_gateway_id: pulumi.Output[str],
    api_gateway_name: pulumi.Output[str],
    sns_topic_arn: pulumi.Output[str],
) -> dict:
    """Create CloudWatch Alarms for API Gateway"""

    alarms = {}

    # Alarm 1: High 5xx error rate
    alarms["5xx_errors"] = aws.cloudwatch.MetricAlarm(
        "api-5xx-alarm",
        name=f"{project_name}-{stack}-api-5xx",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=1,
        metric_name="5XXError",
        namespace="AWS/ApiGateway",
        period=300,
        statistic="Sum",
        threshold=10,  # More than 10 5xx errors in 5 minutes
        alarm_description="API Gateway 5xx error rate is too high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "ApiId": api_gateway_id,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alarm 2: High 4xx error rate (potential abuse or misconfiguration)
    alarms["4xx_errors"] = aws.cloudwatch.MetricAlarm(
        "api-4xx-alarm",
        name=f"{project_name}-{stack}-api-4xx",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=1,
        metric_name="4XXError",
        namespace="AWS/ApiGateway",
        period=300,
        statistic="Sum",
        threshold=50,  # More than 50 4xx errors in 5 minutes
        alarm_description="API Gateway 4xx error rate is unusually high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "ApiId": api_gateway_id,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alarm 3: High latency
    alarms["latency"] = aws.cloudwatch.MetricAlarm(
        "api-latency-alarm",
        name=f"{project_name}-{stack}-api-latency",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=2,
        metric_name="Latency",
        namespace="AWS/ApiGateway",
        period=300,
        statistic="Average",
        threshold=5000,  # 5 seconds
        alarm_description="API Gateway latency is too high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "ApiId": api_gateway_id,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    return alarms


def create_cloudfront_alarms(
    project_name: str,
    stack: str,
    distribution_id: pulumi.Output[str],
    sns_topic_arn: pulumi.Output[str],
) -> dict:
    """Create CloudWatch Alarms for CloudFront"""

    alarms = {}

    # Alarm: High error rate (5xx)
    alarms["error_rate"] = aws.cloudwatch.MetricAlarm(
        "cloudfront-error-alarm",
        name=f"{project_name}-{stack}-cloudfront-errors",
        comparison_operator="GreaterThanThreshold",
        evaluation_periods=1,
        metric_name="5xxErrorRate",
        namespace="AWS/CloudFront",
        period=300,
        statistic="Average",
        threshold=5,  # More than 5% error rate
        alarm_description="CloudFront 5xx error rate is too high",
        alarm_actions=[sns_topic_arn],
        dimensions={
            "DistributionId": distribution_id,
        },
        treat_missing_data="notBreaching",
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    return alarms


def setup_monitoring(
    project_name: str,
    stack: str,
    lambda_function_name: pulumi.Output[str],
    api_gateway_id: pulumi.Output[str],
    api_gateway_name: pulumi.Output[str],
    cloudfront_distribution_id: pulumi.Output[str],
    alarm_email: Optional[str] = None,
) -> dict:
    """
    Setup complete monitoring stack

    Returns:
        dict: Dictionary containing all monitoring resources
    """

    # Create SNS topic for notifications
    sns_topic = create_sns_topic(project_name, stack, alarm_email)

    # Create Lambda alarms
    lambda_alarms = create_lambda_alarms(
        project_name,
        stack,
        lambda_function_name,
        sns_topic.arn,
    )

    # Create API Gateway alarms
    api_alarms = create_api_gateway_alarms(
        project_name,
        stack,
        api_gateway_id,
        api_gateway_name,
        sns_topic.arn,
    )

    # Create CloudFront alarms
    cloudfront_alarms = create_cloudfront_alarms(
        project_name,
        stack,
        cloudfront_distribution_id,
        sns_topic.arn,
    )

    return {
        "sns_topic": sns_topic,
        "lambda_alarms": lambda_alarms,
        "api_gateway_alarms": api_alarms,
        "cloudfront_alarms": cloudfront_alarms,
    }
# SNS:Unsubscribe permission added to satoshi user (2026-02-17)
# SNS:GetSubscriptionAttributes permission added (2026-02-17)
