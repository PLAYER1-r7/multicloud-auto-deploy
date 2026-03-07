# Monitoring & Alerts Setup Guide

## Overview

This project implements comprehensive monitoring and alerting across all three cloud providers (AWS, Azure, GCP) using native monitoring services and custom metrics.

## Monitoring Architecture

### AWS CloudWatch

**Components:**

- Lambda error rate monitoring
- API Gateway performance metrics
- CloudFront cache behavior tracking
- SNS topic for email notifications

**Alarms:**

1. **Lambda Errors** (order-dependent alert)
   - Threshold: > 10 errors in 5 minutes
   - Severity: High
   - Action: SNS email notification

2. **Lambda Throttles** (concurrent execution limit)
   - Threshold: > 5 throttles in 5 minutes
   - Severity: High
   - Action: SNS email notification

3. **API Gateway 5XX Errors**
   - Threshold: > 5 errors in 5 minutes
   - Severity: Medium
   - Action: SNS email notification

4. **CloudFront Error Rate**
   - Threshold: > 1% error rate in 5 minutes
   - Severity: Medium
   - Action: SNS email notification

**Setup:**

```bash
# Configure alarm email in Pulumi configuration
pulumi config set alarmEmail "your-email@example.com"

# Deploy AWS monitoring
cd infrastructure/pulumi/aws
pulumi up
```

**Output:**

```
monitoring_sns_topic_arn: arn:aws:sns:us-east-1:xxx:multicloud-auto-deploy-staging-alarms
monitoring_lambda_alarms: [error_rate, throttles, duration]
monitoring_api_alarms: [errors_5xx, errors_4xx]
monitoring_cloudfront_alarms: [error_rate, cache_hit_rate]
```

### Azure Monitor

**Components:**

- Action Group for multi-channel notifications
- Function App performance monitoring
- Cosmos DB throttling tracking
- Front Door error rate monitoring
- Azure Defender integration

**Alarms:**

1. **Function App CPU Usage**
   - Threshold: > 80% for 5 minutes
   - Severity: Warning (2)
   - Aggregation: Average
   - Action: Action Group email + RBAC notifications

2. **Function App Memory Usage**
   - Threshold: 90% of allocated memory (2048 MB = 1843.2 MB)
   - Severity: Warning (2)
   - Aggregation: Average
   - Action: Action Group email

3. **Cosmos DB Throttling**
   - Threshold: > 10 throttle events/5 min
   - Severity: Error (1)
   - Metric: ThrottledRequests
   - Action: Action Group email

4. **Front Door 4XX Error Rate**
   - Threshold: > 5% in 5 minutes
   - Severity: Warning (2)
   - Action: Action Group email

5. **Front Door 5XX Error Rate**
   - Threshold: > 1% in 5 minutes
   - Severity: Error (1)
   - Action: Action Group email

**Setup:**

```bash
# Configure alarm email in Pulumi configuration
pulumi config set alarmEmail "your-email@example.com"

# Configure Function App memory (if non-default)
pulumi config set functionMemoryMb 2048

# Deploy Azure monitoring
cd infrastructure/pulumi/azure
pulumi up
```

**Output:**

```
monitoring_action_group_id: /subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.Insights/actionGroups/multicloud-auto-deploy-staging-alerts
monitoring_function_alerts: [cpu_usage, memory_usage]
monitoring_cosmos_alerts: [throttling]
monitoring_frontdoor_alerts: [error_rate_4xx, error_rate_5xx]
```

**Azure Defender Integration:**

- Azure Defender for Cloud enabled with critical/high-priority alerts
- Security contact: satoshi+defender@ashnova.jp
- RBAC notifications for subscription-level security events
- Recommendations tracked in Azure Security Center dashboard

### GCP Cloud Monitoring

**Components:**

- Notification Channel for email alerts
- Cloud Function error rate tracking
- Firestore operation monitoring
- Cloud Billing budget alerts (production only)

**Alarms:**

1. **Cloud Function Error Rate**
   - Threshold: > 10% in 5 minutes
   - Severity: High (ERROR)
   - Metric: cloudfunctions.googleapis.com/function/execution_count
   - Action: Notification channel email

2. **Cloud Function Duration**
   - Threshold: > 90% of execution timeout (typically 540 seconds)
   - Severity: Medium (WARNING)
   - Metric: cloudfunctions.googleapis.com/function/execution_times
   - Action: Notification channel email

3. **Firestore Read Operations**
   - Threshold: > 1,000,000 reads/day (quota tracking)
   - Severity: Medium (WARNING)
   - Metric: firestore.googleapis.com/reads
   - Action: Notification channel email

4. **Cloud Billing Budget (Production)**
   - Monthly budget: $50 USD (configurable)
   - Threshold: 50%, 90%, 100% of budget
   - Severity: Budget escalation
   - Action: Notification channel email

**Memory Threshold Calculation Bug Fix:**

- Previously: threshold_value=0.9 (compared as bytes)
- Fixed: threshold_value = memory_mb × 1024 × 1024 × 0.9 (actual bytes)
- Impact: Eliminated false positive alerts on production function
- Reference: commit 9429a67, February 18, 2026

**Setup:**

```bash
# Configure alarm email in Pulumi configuration
pulumi config set alarmEmail "your-email@example.com"

# Configure Cloud Function memory (if non-default)
pulumi config set functionMemoryMb 512

# Configure billing budget (production only)
pulumi config set billingAccountId "01A2B3-C4D5E6-F7G8H9"
pulumi config set monthlyBudgetUsd 50

# Deploy GCP monitoring
cd infrastructure/pulumi/gcp
pulumi up
```

**Output:**

```
notification_channel_id: projects/multicloud-xxx/notificationChannels/1234567890
monitoring_function_alerts: [error_rate, duration, memory_usage]
monitoring_firestore_alerts: [read_operations, write_operations, delete_operations]
monitoring_billing_budget: projects/multicloud-xxx/budgets/monthly-budget
```

## Configuration Management

### Pulumi Configuration Stack Files

Store configuration in `Pulumi.[stack].yaml` (example for staging):

```yaml
config:
  # Alarm email (required for notifications)
  multicloud-auto-deploy:alarmEmail: satoshi@ashnova.jp

  # Azure-specific
  multicloud-auto-deploy:functionMemoryMb: 2048

  # GCP-specific (production only)
  multicloud-auto-deploy:billingAccountId: "01A2B3-C4D5E6-F7G8H9"
  multicloud-auto-deploy:monthlyBudgetUsd: 50
```

### Email Subscription Management

**AWS SNS:**

- SNS:Subscribe permission required in Lambda IAM role
- SNS:Unsubscribe permission added (Feb 17, 2026)
- SNS:GetSubscriptionAttributes permission added (Feb 17, 2026)
- Email confirmations sent automatically when alarms are deployed
- Manually confirm subscription in email to receive notifications

**Azure Action Groups:**

- Email receivers configured automatically during deployment
- No manual confirmation required
- Supports multiple receivers per action group
- Common Alert Schema enabled for consistency

**GCP Notification Channel:**

- Email channel configured automatically during deployment
- Verification email sent to configured address
- Channel remains in "VERIFICATION_REQUIRED" state until confirmed
- Manually verify in GCP Cloud Console to enable notifications

## Monitoring Dashboard

### AWS CloudWatch Dashboard

- View all Lambda, API Gateway, and CloudFront metrics
- CustomDashboard auto-generated during deployment
- Access: AWS Console → CloudWatch → Dashboards

### Azure Monitor Dashboard

- Function App performance metrics
- Cosmos DB throttling patterns
- Front Door availability and error rates
- Access: Azure Portal → Monitor → View all resources filtered by alarm

### GCP Cloud Monitoring Dashboard

- Cloud Function execution metrics
- Firestore operation statistics
- Billing budget tracking
- Access: GCP Console → Monitoring → Dashboards

## Testing Alerts

### AWS Lambda Alerts

Test error rate alert:

```bash
# Invoke function with invalid input to trigger errors
for i in {1..15}; do
  aws lambda invoke \
    --function-name multicloud-auto-deploy-staging-api \
    --payload '{"invalid": true}' \
    response.json
done

# Check CloudWatch Alarms
aws cloudwatch describe-alarms --alarm-names "multicloud-auto-deploy-staging-lambda-errors"
```

### Azure Function App Alerts

Test CPU usage alert:

```bash
# Deploy load test to Function App
az functionapp deployment slot create \
  --name multicloud-auto-deploy-staging-func \
  --resource-group multicloud-auto-deploy-staging \
  --slot load-test

# Monitor alert triggers in Azure Portal
```

### GCP Cloud Function Alerts

Test error rate alert:

```bash
# Invoke function with invalid input
gcloud functions call multicloud-auto-deploy-staging-api \
  --region asia-northeast1 \
  --data '{"invalid": true}'

# View in Cloud Monitoring
gcloud monitoring alerts describe --filter="displayName='multicloud-auto-deploy-staging-function-errors'"
```

## Alert Escalation Policy

### Severity Levels

| Level                                      | Response Time | Action                               | Escalation                   |
| ------------------------------------------ | ------------- | ------------------------------------ | ---------------------------- |
| Critical (AWS: High, Azure: 1, GCP: ERROR) | 15 min        | Immediate notification via SNS/Email | Escalate to on-call engineer |
| Error (AWS: High, Azure: 1)                | 30 min        | Team notification                    | Escalate after 1 hour        |
| Warning (Azure: 2, GCP: WARNING)           | 1 hour        | Log and review                       | No escalation                |
| Info                                       | 4 hours       | Dashboard monitoring                 | No action required           |

### On-Call Contact

- **Primary:** satoshi@ashnova.jp
- **Secondary:** (configure in config section)
- **Azure Defender:** satoshi+defender@ashnova.jp

## Integration with CI/CD

### GitHub Actions Integration

Monitoring metrics are exported as Pulumi stack outputs and can be used in CI/CD workflows:

```yaml
# .github/workflows/check-monitoring.yml
- name: Verify monitoring is configured
  run: |
    # Check that alarms exist in CloudWatch/Azure Monitor/Cloud Monitoring
    pulumi stack output monitoring_lambda_alarms
    pulumi stack output monitoring_action_group_id
    pulumi stack output monitoring_function_alerts
```

## Troubleshooting

### No Alerts Being Received

1. **Check email subscription confirms (AWS SNS)**

   ```bash
   aws sns list-subscriptions --topic-arn <topic-arn>
   ```

2. **Verify Action Group configuration (Azure)**

   ```bash
   az monitor action-group show --resource-group <rg> --name <action-group-name>
   ```

3. **Confirm notification channel (GCP)**
   ```bash
   gcloud alpha monitoring channels list
   ```

### High False Positive Rate

1. **Adjust threshold values** in `monitoring.py`
2. **Increase evaluation period** to account for natural variation
3. **Add filter conditions** to exclude false positive scenarios

### Memory Alert False Positives

**Known Issue (Fixed):**

- GCP Cloud Function memory threshold was hardcoded to 0.9 bytes instead of calculated bytes
- Fixed: threshold now calculated as `memory_mb × 1024 × 1024 × 0.9`
- If upgrading from old version, rerun `pulumi up` to fix

## Best Practices

1. **Email Configuration**
   - Use distribution list email where possible (e.g., team@company.com)
   - Avoid personal email addresses for production alerts

2. **Alarm Tuning**
   - Start with conservative thresholds
   - Gradually reduce thresholds based on actual metrics
   - Review alarm history monthly

3. **Dashboard Maintenance**
   - Keep dashboards updated with new metrics
   - Archive/remove unused metrics
   - Share dashboards with team members

4. **Documentation**
   - Document alert intention and expected response
   - Update runbooks when metrics change
   - Include alert in incident response procedures

## Related Documentation

- [Security Implementation Guide](AI_AGENT_08_SECURITY.md) - Includes Azure Defender setup
- [CI/CD Documentation](AI_AGENT_05_CICD.md) - Integration with GitHub Actions
- [Infrastructure Documentation](AI_AGENT_02_ARCHITECTURE.md) - Cloud architecture overview
- [Troubleshooting Guide](../TROUBLESHOOTING.md) - Common issues and solutions

## References

- AWS CloudWatch Alarms: https://docs.aws.amazon.com/AmazonCloudWatch/latest/events/WhatIsCloudWatch.html
- Azure Monitor Alerts: https://docs.microsoft.com/en-us/azure/azure-monitor/alerts/alerts-overview
- GCP Cloud Monitoring: https://cloud.google.com/monitors/
