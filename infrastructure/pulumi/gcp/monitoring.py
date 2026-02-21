"""
GCP Monitoring and Alert

ing Configuration

Cloud Monitoring Alerts for:
- Cloud Functions errors and performance
- Firestore operations
- Cloud Run (if used)
- Billing alerts
"""

import pulumi
import pulumi_gcp as gcp
from typing import Optional, List


def calculate_memory_threshold_bytes(function_memory_mb: int) -> int:
    """
    Cloud Function メモリアラートの閾値をバイト単位で返す（割当メモリの90%）。

    IMPORTANT: `cloudfunctions.googleapis.com/function/user_memory_bytes` は
    DISTRIBUTION メトリクスであり、threshold_value は **バイト数** で指定する必要がある。
    0.9 のような比率を渡すと、実際のメモリ使用量（例: 118MB = 123,850,752 bytes）が
    常に 0.9 bytes を超えるため、誤検知アラートが無限に発火し続ける。

    Bug history:
        Feb 18, 2026 — threshold_value=0.9 (bytes) と設定されており、
        production で 123,850,752 bytes (118MB) が 0.9 bytes を超えたとして
        誤検知アラートが発火。commit 9429a67 で本関数を導入して修正済み。

    Args:
        function_memory_mb: Cloud Function に割り当てたメモリ量 (MB単位)

    Returns:
        閾値バイト数 = function_memory_mb * 1024 * 1024 * 0.9
    """
    return int(function_memory_mb * 1024 * 1024 * 0.9)


def create_notification_channel(
    project_name: str,
    stack: str,
    email: Optional[str] = None,
) -> Optional[gcp.monitoring.NotificationChannel]:
    """Create Notification Channel for alert notifications"""

    if not email:
        return None

    channel = gcp.monitoring.NotificationChannel(
        "alert-notification-channel",
        display_name=f"{project_name}-{stack}-email",
        type="email",
        labels={
            "email_address": email,
        },
        user_labels={
            "project": project_name,
            "environment": stack,
            "managed_by": "pulumi",
        },
    )

    return channel


def create_cloud_function_alerts(
    project_name: str,
    stack: str,
    function_name: pulumi.Output[str],
    region: str,
    project_id: str,
    notification_channels: List[pulumi.Output[str]],
    function_memory_mb: int = 512,
) -> dict:
    """Create Cloud Monitoring Alerts for Cloud Functions"""

    alerts = {}

    # Alert 1: High error rate
    alerts["error_rate"] = gcp.monitoring.AlertPolicy(
        "function-error-rate-alert",
        display_name=f"{project_name}-{stack}-function-errors",
        combiner="OR",
        conditions=[
            gcp.monitoring.AlertPolicyConditionArgs(
                display_name="Error rate > 10%",
                condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                    filter=pulumi.Output.all(function_name).apply(
                        lambda args: f'resource.type="cloud_function" AND resource.labels.function_name="{args[0]}" AND metric.type="cloudfunctions.googleapis.com/function/execution_count" AND metric.labels.status!="ok"'
                    ),
                    duration="300s",  # 5 minutes
                    comparison="COMPARISON_GT",
                    threshold_value=10,
                    aggregations=[
                        gcp.monitoring.AlertPolicyConditionConditionThresholdAggregationArgs(
                            alignment_period="300s",
                            per_series_aligner="ALIGN_RATE",
                            cross_series_reducer="REDUCE_SUM",
                        )
                    ],
                ),
            )
        ],
        notification_channels=notification_channels,
        alert_strategy=gcp.monitoring.AlertPolicyAlertStrategyArgs(
            auto_close="604800s",  # Auto-close after 7 days
        ),
        user_labels={
            "project": project_name,
            "environment": stack,
            "managed_by": "pulumi",
        },
    )

    # Alert 2: High execution time
    alerts["execution_time"] = gcp.monitoring.AlertPolicy(
        "function-execution-time-alert",
        display_name=f"{project_name}-{stack}-function-latency",
        combiner="OR",
        conditions=[
            gcp.monitoring.AlertPolicyConditionArgs(
                display_name="Execution time > 10 seconds",
                condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                    filter=pulumi.Output.all(function_name).apply(
                        lambda args: f'resource.type="cloud_function" AND resource.labels.function_name="{args[0]}" AND metric.type="cloudfunctions.googleapis.com/function/execution_times"'
                    ),
                    duration="300s",
                    comparison="COMPARISON_GT",
                    threshold_value=10000000000,  # 10 seconds in nanoseconds
                    aggregations=[
                        gcp.monitoring.AlertPolicyConditionConditionThresholdAggregationArgs(
                            alignment_period="300s",
                            per_series_aligner="ALIGN_DELTA",  # For DISTRIBUTION metrics
                            cross_series_reducer="REDUCE_MEAN",
                        )
                    ],
                ),
            )
        ],
        notification_channels=notification_channels,
        alert_strategy=gcp.monitoring.AlertPolicyAlertStrategyArgs(
            auto_close="604800s",
        ),
        user_labels={
            "project": project_name,
            "environment": stack,
            "managed_by": "pulumi",
        },
    )

    # Alert 3: Low memory available
    # NOTE: user_memory_bytes is a DISTRIBUTION metric measured in BYTES.
    # threshold_value must be set in bytes (NOT as a ratio like 0.9).
    # Formula: function_memory_mb * 1024 * 1024 * 0.9
    # e.g. 512MB × 0.9 = 483,183,820 bytes (~460MB)
    # Bug history: was incorrectly set to 0.9 (bytes), causing alerts to fire
    # unconditionally since any real usage (e.g. 171MB) always exceeds 0.9 bytes.
    memory_threshold_bytes = calculate_memory_threshold_bytes(
        function_memory_mb)
    alerts["memory_usage"] = gcp.monitoring.AlertPolicy(
        "function-memory-alert",
        display_name=f"{project_name}-{stack}-function-memory",
        combiner="OR",
        conditions=[
            gcp.monitoring.AlertPolicyConditionArgs(
                display_name=f"Memory usage > 90% ({function_memory_mb}MB allocated)",
                condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                    filter=pulumi.Output.all(function_name).apply(
                        lambda args: f'resource.type="cloud_function" AND resource.labels.function_name="{args[0]}" AND metric.type="cloudfunctions.googleapis.com/function/user_memory_bytes"'
                    ),
                    duration="300s",
                    comparison="COMPARISON_GT",
                    threshold_value=memory_threshold_bytes,  # 90% of function_memory_mb in bytes
                    aggregations=[
                        gcp.monitoring.AlertPolicyConditionConditionThresholdAggregationArgs(
                            alignment_period="300s",
                            # ALIGN_PERCENTILE_99: appropriate for DISTRIBUTION metrics
                            # (user_memory_bytes is a DISTRIBUTION, not GAUGE/DELTA)
                            per_series_aligner="ALIGN_PERCENTILE_99",
                            cross_series_reducer="REDUCE_MEAN",
                        )
                    ],
                ),
            )
        ],
        notification_channels=notification_channels,
        alert_strategy=gcp.monitoring.AlertPolicyAlertStrategyArgs(
            auto_close="604800s",
        ),
        user_labels={
            "project": project_name,
            "environment": stack,
            "managed_by": "pulumi",
        },
    )

    return alerts


def create_firestore_alerts(
    project_name: str,
    stack: str,
    project_id: str,
    notification_channels: List[pulumi.Output[str]],
) -> dict:
    """Create Cloud Monitoring Alerts for Firestore"""

    alerts = {}

    # Alert: High read/write operations (potential cost issue)
    alerts["operations"] = gcp.monitoring.AlertPolicy(
        "firestore-operations-alert",
        display_name=f"{project_name}-{stack}-firestore-ops",
        combiner="OR",
        conditions=[
            gcp.monitoring.AlertPolicyConditionArgs(
                display_name="Document reads > 10000/minute",
                condition_threshold=gcp.monitoring.AlertPolicyConditionConditionThresholdArgs(
                    filter='resource.type="firestore_instance" AND metric.type="firestore.googleapis.com/document/read_count"',
                    duration="300s",
                    comparison="COMPARISON_GT",
                    threshold_value=10000,
                    aggregations=[
                        gcp.monitoring.AlertPolicyConditionConditionThresholdAggregationArgs(
                            alignment_period="60s",
                            per_series_aligner="ALIGN_RATE",
                            cross_series_reducer="REDUCE_SUM",
                        )
                    ],
                ),
            )
        ],
        notification_channels=notification_channels,
        alert_strategy=gcp.monitoring.AlertPolicyAlertStrategyArgs(
            auto_close="604800s",
        ),
        user_labels={
            "project": project_name,
            "environment": stack,
            "managed_by": "pulumi",
        },
    )

    return alerts


def create_billing_budget(
    project_name: str,
    stack: str,
    project_id: str,
    monthly_budget_usd: int = 50,
    notification_channels: List[pulumi.Output[str]] = None,
) -> gcp.billing.Budget:
    """
    Create billing budget with alerts

    Args:
        monthly_budget_usd: Monthly budget in USD (default: $50)
    """

    # Get billing account (requires permission)
    # Note: This might fail if the service account doesn't have billing.accounts.list permission

    budget = gcp.billing.Budget(
        "billing-budget",
        display_name=f"{project_name}-{stack}-budget",
        amount=gcp.billing.BudgetAmountArgs(
            specified_amount=gcp.billing.BudgetAmountSpecifiedAmountArgs(
                currency_code="USD",
                units=str(monthly_budget_usd),
            ),
        ),
        budget_filter=gcp.billing.BudgetBudgetFilterArgs(
            projects=[f"projects/{project_id}"],
        ),
        threshold_rules=[
            # Alert at 50% of budget
            gcp.billing.BudgetThresholdRuleArgs(
                threshold_percent=0.5,
                spend_basis="CURRENT_SPEND",
            ),
            # Alert at 80% of budget
            gcp.billing.BudgetThresholdRuleArgs(
                threshold_percent=0.8,
                spend_basis="CURRENT_SPEND",
            ),
            # Alert at 100% of budget
            gcp.billing.BudgetThresholdRuleArgs(
                threshold_percent=1.0,
                spend_basis="CURRENT_SPEND",
            ),
        ],
        all_updates_rule=gcp.billing.BudgetAllUpdatesRuleArgs(
            monitoring_notification_channels=notification_channels or [],
            disable_default_iam_recipients=False,
        ),
    )

    return budget


def setup_monitoring(
    project_name: str,
    stack: str,
    function_name: pulumi.Output[str],
    region: str,
    project_id: str,
    alarm_email: Optional[str] = None,
    monthly_budget_usd: int = 50,
    function_memory_mb: int = 512,
) -> dict:
    """
    Setup complete monitoring stack for GCP

    Returns:
        dict: Dictionary containing all monitoring resources
    """

    # Create notification channel
    notification_channel = create_notification_channel(
        project_name,
        stack,
        alarm_email,
    )

    notification_channels = [
        notification_channel.id] if notification_channel else []

    # Create Cloud Function alerts
    function_alerts = create_cloud_function_alerts(
        project_name,
        stack,
        function_name,
        region,
        project_id,
        notification_channels,
        function_memory_mb=function_memory_mb,
    )

    # Create Firestore alerts (Firestore is used for GCP backend)
    firestore_alerts = create_firestore_alerts(
        project_name,
        stack,
        project_id,
        notification_channels,
    )

    # Create billing budget (production only)
    billing_budget = None
    if stack == "production":
        try:
            billing_budget = create_billing_budget(
                project_name,
                stack,
                project_id,
                monthly_budget_usd,
                notification_channels,
            )
        except Exception as e:
            pulumi.log.warn(f"Could not create billing budget: {e}")

    return {
        "notification_channel": notification_channel,
        "function_alerts": function_alerts,
        "firestore_alerts": firestore_alerts,
        "billing_budget": billing_budget,
    }
