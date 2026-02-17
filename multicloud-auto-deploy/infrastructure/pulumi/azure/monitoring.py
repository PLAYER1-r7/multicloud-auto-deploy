"""
Azure Monitoring and Alerting Configuration

Azure Monitor Alerts for:
- Function App errors and performance
- Front Door errors
- Cosmos DB throttling
- Cost anomalies
"""

import pulumi
import pulumi_azure_native as azure_native
from typing import Optional, List


def create_action_group(
    project_name: str,
    stack: str,
    resource_group_name: pulumi.Output[str],
    location: str,
    email: Optional[str] = None,
) -> azure_native.insights.ActionGroup:
    """Create Action Group for alert notifications"""

    email_receivers = []
    if email:
        email_receivers.append(
            azure_native.insights.EmailReceiverArgs(
                name=f"{project_name}-admin",
                email_address=email,
                use_common_alert_schema=True,
            )
        )

    action_group = azure_native.insights.ActionGroup(
        "alert-action-group",
        action_group_name=f"{project_name}-{stack}-alerts",
        resource_group_name=resource_group_name,
        location="Global",  # Action Groups are global resources
        group_short_name=f"{project_name[:12]}",  # Max 12 chars
        enabled=True,
        email_receivers=email_receivers,
        tags={
            "Project": project_name,
            "Environment": stack,
            "ManagedBy": "pulumi",
        },
    )

    return action_group


def create_function_app_alerts(
    project_name: str,
    stack: str,
    resource_group_name: pulumi.Output[str],
    function_app_name: pulumi.Output[str],
    function_app_id: pulumi.Output[str],
    action_group_id: pulumi.Output[str],
) -> dict:
    """Create Azure Monitor Alerts for Function App"""

    alerts = {}

    # Alert 1: High CPU usage
    alerts["cpu_usage"] = azure_native.insights.MetricAlert(
        "function-cpu-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Function App CPU usage is too high",
        severity=2,  # 0: Critical, 1: Error, 2: Warning, 3: Informational, 4: Verbose
        enabled=True,
        scopes=[function_app_id],
        evaluation_frequency="PT5M",  # Every 5 minutes
        window_size="PT5M",  # 5 minute window
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="CpuPercentage",
                    metric_name="CpuPercentage",
                    metric_namespace="Microsoft.Web/sites",
                    operator="GreaterThan",
                    threshold=80,  # 80% CPU
                    time_aggregation="Average",
                    criterion_type="StaticThresholdCriterion",
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alert 2: High execution count (potential DDoS or infinite loop)
    alerts["execution_count"] = azure_native.insights.MetricAlert(
        "function-execution-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Function App execution count is unusually high",
        severity=3,
        enabled=True,
        scopes=[function_app_id],
        evaluation_frequency="PT5M",
        window_size="PT15M",  # 15 minute window
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="ExecutionCount",
                    metric_name="OnDemandFunctionExecutionCount",
                    metric_namespace="Microsoft.Web/sites",
                    operator="GreaterThan",
                    threshold=1000,  # 1000 executions in 15 min
                    time_aggregation="Total",
                    criterion_type="StaticThresholdCriterion",
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alert 3: High memory usage
    alerts["memory"] = azure_native.insights.MetricAlert(
        "function-memory-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Function App memory usage is too high",
        severity=3,
        enabled=True,
        scopes=[function_app_id],
        evaluation_frequency="PT5M",
        window_size="PT15M",
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="MemoryWorkingSet",
                    metric_name="MemoryWorkingSet",
                    metric_namespace="Microsoft.Web/sites",
                    operator="GreaterThan",
                    threshold=800_000_000,  # 800 MB
                    time_aggregation="Average",
                    criterion_type="StaticThresholdCriterion",
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    return alerts


def create_cosmos_db_alerts(
    project_name: str,
    stack: str,
    resource_group_name: pulumi.Output[str],
    cosmos_account_name: pulumi.Output[str],
    cosmos_account_id: pulumi.Output[str],
    action_group_id: pulumi.Output[str],
) -> dict:
    """Create Azure Monitor Alerts for Cosmos DB"""

    alerts = {}

    # Alert 1: Throttled requests (429 errors)
    alerts["throttled_requests"] = azure_native.insights.MetricAlert(
        "cosmos-throttled-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Cosmos DB has throttled requests (increase RU/s)",
        severity=2,
        enabled=True,
        scopes=[cosmos_account_id],
        evaluation_frequency="PT5M",
        window_size="PT5M",
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="TotalRequestUnits",
                    metric_name="TotalRequestUnits",
                    metric_namespace="Microsoft.DocumentDB/databaseAccounts",
                    operator="GreaterThan",
                    threshold=1000,  # More than 1000 throttled requests
                    time_aggregation="Total",
                    criterion_type="StaticThresholdCriterion",
                    dimensions=[
                        azure_native.insights.MetricDimensionArgs(
                            name="StatusCode",
                            operator="Include",
                            values=["429"],
                        )
                    ],
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    # Alert 2: High latency
    alerts["latency"] = azure_native.insights.MetricAlert(
        "cosmos-latency-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Cosmos DB server-side latency is too high",
        severity=3,
        enabled=True,
        scopes=[cosmos_account_id],
        evaluation_frequency="PT5M",
        window_size="PT15M",
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="ServerSideLatency",
                    metric_name="ServerSideLatency",
                    metric_namespace="Microsoft.DocumentDB/databaseAccounts",
                    operator="GreaterThan",
                    threshold=100,  # 100ms
                    time_aggregation="Average",
                    criterion_type="StaticThresholdCriterion",
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    return alerts


def create_frontdoor_alerts(
    project_name: str,
    stack: str,
    resource_group_name: pulumi.Output[str],
    frontdoor_profile_id: pulumi.Output[str],
    action_group_id: pulumi.Output[str],
) -> dict:
    """Create Azure Monitor Alerts for Front Door"""

    alerts = {}

    # Alert: High error率 (5xx)
    alerts["error_percentage"] = azure_native.insights.MetricAlert(
        "frontdoor-error-alert",
        resource_group_name=resource_group_name,
        location="Global",  # Metric alerts for platform metrics must be global
        description="Front Door 5xx error percentage is too high",
        severity=2,
        enabled=True,
        scopes=[frontdoor_profile_id],
        evaluation_frequency="PT5M",
        window_size="PT5M",
        criteria=azure_native.insights.MetricAlertMultipleResourceMultipleMetricCriteriaArgs(
            odata_type="Microsoft.Azure.Monitor.MultipleResourceMultipleMetricCriteria",
            all_of=[
                azure_native.insights.MetricCriteriaArgs(
                    name="BackendHealthPercentage",
                    metric_name="Percentage5XX",
                    metric_namespace="Microsoft.Cdn/profiles",
                    operator="GreaterThan",
                    threshold=5,  # More than 5%
                    time_aggregation="Average",
                    criterion_type="StaticThresholdCriterion",
                )
            ],
        ),
        actions=[
            azure_native.insights.MetricAlertActionArgs(action_group_id=action_group_id)
        ],
        tags={
            "Project": project_name,
            "Environment": stack,
        },
    )

    return alerts


def setup_monitoring(
    project_name: str,
    stack: str,
    resource_group_name: pulumi.Output[str],
    location: str,
    function_app_id: pulumi.Output[str],
    cosmos_account_id: Optional[pulumi.Output[str]],
    frontdoor_profile_id: pulumi.Output[str],
    alarm_email: Optional[str] = None,
) -> dict:
    """
    Setup complete monitoring stack for Azure

    Returns:
        dict: Dictionary containing all monitoring resources
    """

    # Derive resource names from IDs
    function_app_name = f"{project_name}-{stack}-func"
    cosmos_account_name = f"{project_name}-{stack}-cosmos"  # Not used if cosmos_account_id is None

    # Create Action Group for notifications
    action_group = create_action_group(
        project_name,
        stack,
        resource_group_name,
        location,
        alarm_email,
    )

    # Create Function App alerts
    function_alerts = create_function_app_alerts(
        project_name,
        stack,
        resource_group_name,
        function_app_name,
        function_app_id,
        action_group.id,
    )

    # Create Cosmos DB alerts (if Cosmos is used)
    cosmos_alerts = {}
    if cosmos_account_id:
        cosmos_alerts = create_cosmos_db_alerts(
            project_name,
            stack,
            resource_group_name,
            cosmos_account_name,
            cosmos_account_id,
            action_group.id,
        )

    # Create Front Door alerts
    frontdoor_alerts = create_frontdoor_alerts(
        project_name,
        stack,
        resource_group_name,
        frontdoor_profile_id,
        action_group.id,
    )

    return {
        "action_group": action_group,
        "function_alerts": function_alerts,
        "cosmos_alerts": cosmos_alerts,
        "frontdoor_alerts": frontdoor_alerts,
    }
