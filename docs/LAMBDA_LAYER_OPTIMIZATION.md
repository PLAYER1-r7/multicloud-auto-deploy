# Lambda Layer Optimization Guide

## Overview

To reduce Lambda function deployment size, we use Lambda Layers to separate dependencies from application code.

**🌟 Recommended: Using Klayers (public Lambda Layers) enables even more efficient deployments!**

See [LAMBDA_LAYER_PUBLIC_RESOURCES.md](LAMBDA_LAYER_PUBLIC_RESOURCES.md) for details.

### Problems Before Optimization

- **Package size**: Over 50MB (including all dependencies)
- **Deployment method**: Upload via S3 required
- **Deployment time**: Slow due to S3 upload + Lambda update
- **Inefficient**: Every deployment re-uploads even when dependencies haven't changed

### Benefits After Optimization

- **Package size**: A few MB (application code only)
- **Deployment method**: Direct upload possible (under 50MB)
- **Deployment time**: Completes in seconds
- **Efficient**: Dependencies managed in Layer; only update when code changes

## Architecture

```
Lambda Function (lightweight)
├── app/              # Application code (~2-5MB)
│   ├── main.py
│   ├── auth.py
│   ├── config.py
│   └── ...
└── index.py

Lambda Layer (dependencies)
└── python/           # Dependencies (~20-40MB)
    ├── fastapi/
    ├── pydantic/
    ├── mangum/
    ├── jwt/
    └── ...
```

## Setup Steps

### Option A: Use Klayers (Recommended)

**Benefits:**
- ✅ No build required (instantly deployable)
- ✅ No maintenance needed (community managed)
- ✅ Easy to update to latest version

```bash
# Klayers ARNs can be found at https://api.klayers.cloud/

# Set use_klayers=true in Pulumi (default)
cd infrastructure/pulumi/aws/simple-sns
pulumi config set use_klayers true
pulumi up

# Or set use_klayers to true in GitHub Actions (default)
```

See [LAMBDA_LAYER_PUBLIC_RESOURCES.md](LAMBDA_LAYER_PUBLIC_RESOURCES.md) for details.

### Option B: Use a Custom Layer

**Benefits:**
- ✅ Full control (use specific versions)
- ✅ Size optimization (only what's needed)
- ✅ Use in private environments

### 1. Build the Lambda Layer

```bash
cd /workspaces/ashnova/multicloud-auto-deploy
./scripts/build-lambda-layer.sh
```

This script performs the following:
- Install only AWS-specific dependencies
- Exclude boto3/botocore (included in Lambda runtime)
- Exclude Azure/GCP SDKs (not needed for AWS)
- Remove test files and documentation to reduce size
- Generate `services/api/lambda-layer.zip`

### 2. Use Custom Layer with Pulumi

```bash
cd infrastructure/pulumi/aws/simple-sns

# Configure to use custom Layer
pulumi config set use_klayers false

# Deploy infrastructure including Layer
pulumi up
```

Pulumi will automatically:
- Create the custom Lambda Layer
- Deploy only application code to the Lambda function
- Attach the Layer to the Lambda function

### 3. Automated Deployment with GitHub Actions

```bash
# Trigger GitHub Actions workflow
gh workflow run deploy-aws.yml
```

## Usage in CI/CD

### Using Klayers (Recommended, Default)

The GitHub Actions workflow automatically:

1. **Fetch ARN**: Uses the latest Klayers ARN
2. **Package application code**: ZIPs code only
3. **Update Lambda function**: 
   - Package under 50MB: Direct upload ✅
   - Package over 50MB: Via S3 (fallback)
4. **Attach Klayers**: Connect the public Layer to Lambda

```yaml
# Example trigger in GitHub Actions
name: Deploy
on:
  workflow_dispatch:
    inputs:
      use_klayers:
        description: "Use Klayers (public Lambda Layers)"
        default: true  # Use Klayers by default
```

### Using a Custom Layer

Select `use_klayers: false` in the GitHub Actions workflow:

1. **Build Layer**: Run `build-lambda-layer.sh`
2. **Package application code**: ZIPs code only
3. **Deploy custom Layer**: Publish as Lambda Layer
4. **Update Lambda function**: Direct upload or via S3
5. **Attach Layer**: Connect custom Layer to Lambda

## Dependencies Included in Layer

```
fastapi==0.115.0
pydantic==2.9.0
pydantic-settings==2.5.2
python-jose[cryptography]==3.3.0
python-multipart==0.0.9
pyjwt==2.9.0
mangum==0.17.0
requests==2.32.3
```

### Excluded Dependencies

- **boto3/botocore**: Included in Lambda runtime
- **Azure SDK**: Not required for AWS
- **GCP SDK**: Not required for AWS
- **PostgreSQL/SQLAlchemy**: DynamoDB only is used

## Size Comparison

### Before Optimization

```
Lambda package: 65MB (code + all dependencies)
└── S3 deployment required
```

### After Optimization

```
Lambda package: 3MB (code only)
├── Direct upload possible
└── Layer: 25MB (dependencies)
    └── Re-deploy only when dependencies change
```

## Troubleshooting

### Layer Not Found Error

```bash
# Rebuild Layer
./scripts/build-lambda-layer.sh

# Verify Layer was created
ls -lh services/api/lambda-layer.zip
```

### Module Not Found in Lambda Function

```bash
# Verify Layer is correctly attached
aws lambda get-function-configuration \
  --function-name multicloud-auto-deploy-staging-api \
  --query 'Layers[*].Arn'
```

### Layer Size Too Large

Lambda Layer limits:
- **ZIP size**: 50MB
- **Unzipped size**: 250MB

Size reduction methods:
1. Remove unnecessary files in `build-lambda-layer.sh`
2. Use `--no-deps` to exclude extra dependencies
3. Remove test files and documentation

## Best Practices

### 1. Reduce Layer Update Frequency

- Pin dependency versions
- Only update Lambda when application code changes
- Only update Layer when dependencies change

### 2. Layer Version Management

```bash
# Check Layer versions
aws lambda list-layer-versions \
  --layer-name multicloud-auto-deploy-staging-dependencies

# Delete old versions
aws lambda delete-layer-version \
  --layer-name multicloud-auto-deploy-staging-dependencies \
  --version-number 1
```

### 3. Separate Layers per Environment

```yaml
# staging environment
LAYER_NAME: multicloud-auto-deploy-staging-dependencies

# production environment
LAYER_NAME: multicloud-auto-deploy-production-dependencies
```

## Reference Links

- [Lambda Layer Public Resources Guide](LAMBDA_LAYER_PUBLIC_RESOURCES.md) ⭐ **Recommended**
- [Klayers GitHub](https://github.com/keithrozario/Klayers)
- [Klayers API](https://api.klayers.cloud/)
- [AWS Lambda Layers Documentation](https://docs.aws.amazon.com/lambda/latest/dg/configuration-layers.html)
- [Lambda Deployment Packages](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html)
- [Lambda Quotas](https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html)

## Summary

### Recommended Approach

**🌟 We strongly recommend using Klayers (public Layers)**

By using Lambda Layers:

✅ Reduces deployment size from **65MB → 3MB**  
✅ Reduces deployment time from **minutes → seconds**  
✅ S3 upload **no longer required**  
✅ Dependency management is **separated** for efficiency  
✅ Build time is **zero** (when using Klayers)  

**Selection Criteria:**

| Scenario                                  | Recommended Approach  |
| ----------------------------------------- | --------------------- |
| Standard development / production         | **Klayers** ✅        |
| Rapid prototyping                         | **Klayers** ✅        |
| Specific version required                 | Custom Layer          |
| Private dependencies                      | Custom Layer          |
| Minimize size to the extreme              | Custom Layer          |

See [Lambda Layer Public Resources Guide](LAMBDA_LAYER_PUBLIC_RESOURCES.md) for details.
