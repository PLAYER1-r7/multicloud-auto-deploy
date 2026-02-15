# Changelog

All notable changes to the **multicloud-auto-deploy** project are documented in this file.

This changelog is automatically generated from git commit history using [Conventional Commits](https://www.conventionalcommits.org/) format.

**Repository**: [https://github.com/PLAYER1-r7/multicloud-auto-deploy](https://github.com/PLAYER1-r7/multicloud-auto-deploy)  
**Branch**: `main`  
**Generated**: 2026-02-15 08:06:55

---


## 2026-02-14

### 📚 Documentation

- Update README with comprehensive project overview ([`4aded9d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4aded9d))


## 2026-02-13

### ✨ Features

- Complete multi-cloud auto-deploy platform ([`6ce22f0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6ce22f0))

### 📚 Documentation

- Add comprehensive documentation ([`a8f23a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a8f23a8))


## 2026-02-14

### ✨ Features

- Add Python Full Stack implementation ([`6087b76`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6087b76))
- Implement message CRUD API endpoints ([`4bd5e61`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4bd5e61))
- Update frontend to integrate with new API endpoints ([`fd9a4d9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/fd9a4d9))
- Implement MinIO-based persistent storage for LocalBackend ([`48d9883`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/48d9883))
- 画像アップロード機能を実装 ([`83f8e8f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/83f8e8f))
- メッセージ削除機能を実装 ([`052cecc`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/052cecc))
- Implement message editing functionality ([`a563f84`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a563f84))
- Complete Python frontend migration with Reflex ([`6935e12`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6935e12))
- Add production deployment configuration ([`8215297`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8215297))
- Add CI/CD pipeline for multi-cloud deployment ([`8c3b061`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8c3b061))
- Add React static frontend to replace Reflex SSR ([`5863645`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5863645))
- Deploy React static frontend to AWS S3 + CloudFront ([`d6ac8de`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d6ac8de))
- Make AWS region optional in AWSBackend ([`6539b0d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6539b0d))
- Add Lambda container image support ([`24ba2b0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/24ba2b0))
- Migrate to complete ZIP unification across all clouds ([`3901489`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3901489))
- Migrate from Terraform to Pulumi (Python) ([`4845887`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4845887))
- Deploy to Malaysia West region with Y1 Consumption tier ([`2f2acfa`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2f2acfa))

### 🐛 Bug Fixes

- Update docker-compose and Reflex configuration for local dev ([`1db97c5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/1db97c5))
- Correct JSX syntax errors in App.tsx ([`6add588`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6add588))
- Correct frontend API URL from backend to api service ([`39cba48`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/39cba48))
- Change frontend API URL to localhost for browser access ([`a41db81`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a41db81))
- Implement update_message method in AWSBackend ([`ab1b003`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ab1b003))
- Change update method from PATCH to PUT ([`3870668`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3870668))
- Update CI/CD workflows to use correct directory structure (api/frontend_react) ([`621bb55`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/621bb55))
- Correct source directory from src to app in AWS workflow ([`7aa7bc9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7aa7bc9))
- Make API Gateway endpoint lookup non-blocking in CI/CD ([`128d13d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/128d13d))
- Shorten Azure Storage Account names to meet 24-char limit ([`beb49a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/beb49a8))
- Deploy GCP Cloud Functions via gcloud CLI instead of Terraform ([`94a5afe`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/94a5afe))
- Fix Pulumi.yaml config format and add stack initialization steps ([`3449db4`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3449db4))
- Fix S3 BucketPolicy creation order and IAM policy regions ([`b20d984`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b20d984))
- Add Azure CLI login before Pulumi deployment ([`83ff516`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/83ff516))
- Extract Azure credentials from AZURE_CREDENTIALS secret ([`144ada0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/144ada0))
- Use azure/login action for proper authentication ([`e6921ed`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e6921ed))
- Rename function.py to main.py for Cloud Functions ([`6e5d5f8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6e5d5f8))
- Change min_tls_version to minimum_tls_version in Azure StorageAccount ([`5d388e5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5d388e5))
- Change resource_name to component_name in Application Insights ([`c84734d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/c84734d))
- Remove component_name parameter from Application Insights Component ([`a9fd4c9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a9fd4c9))
- Set ingestion_mode to ApplicationInsights for Application Insights Component ([`cc66be5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cc66be5))
- Change App Service Plan SKU from Consumption (Y1) to Basic (B1) tier ([`f6fc6c2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f6fc6c2))
- Change Azure region from japaneast to eastus for quota availability ([`062840f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/062840f))

### 📚 Documentation

- Comprehensive documentation and tooling update ([`1edfe9e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/1edfe9e))
- Update README for Reflex frontend migration ([`dd0ffbb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/dd0ffbb))
- Add comprehensive CI/CD test results and update README ([`b2e82b7`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b2e82b7))

### 🧪 Tests

- Try Y1 (Consumption) tier with eastus region for quota availability ([`96dfea3`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/96dfea3))

### 💄 Styling

- Fix indentation in devcontainer config ([`fc93ecb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/fc93ecb))

### 🔧 Chores

- Remove unused code and migrate to Pulumi ([`f5fbb84`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f5fbb84))
- Optimize Docker images and cleanup ([`7c77283`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7c77283))

### 📝 Other Changes

- Fix Azure cloud detection in Container Apps ([`7df289d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7df289d))
- Add detailed instructions for AZURE_ACR_LOGIN_SERVER and GCP_SA_KEY ([`54b3c5f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/54b3c5f))
- Update AWS CI/CD workflow to update existing resources only ([`847ba08`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/847ba08))
- Change AWS region from us-east-1 to ap-northeast-1 ([`4db9645`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4db9645))
- Update Lambda runtime to Python 3.12 and set architecture to arm64 ([`d645961`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d645961))
- Update AWS workflow to use Python 3.12 ([`ee78f96`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ee78f96))
- Fix AWS workflow: add region to Lambda update and ensure package directory exists ([`5f6f8ab`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5f6f8ab))
- Fix Lambda deployment: use x86_64 architecture and minimal dependencies for AWS Lambda ([`39bbaab`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/39bbaab))
- Add development tools: Makefile and diagnostics script ([`6c202c9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6c202c9))
- Fix AWS workflow: upload Lambda package via S3 to handle large file size ([`095074d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/095074d))
- Improve AWS workflow: add package optimization and better error handling ([`58e6bfb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/58e6bfb))
- Fix AWS workflow: improve cleanup commands to avoid errors ([`3437bf0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3437bf0))
- Simplify AWS workflow: remove cleanup commands for reliability ([`d8b6330`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d8b6330))
- Update documentation: Add CI/CD badges, live demo URLs, and development tools ([`8f3ce46`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8f3ce46))
- Fix Azure Terraform authentication: use environment variables instead of Azure CLI ([`ea94b19`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ea94b19))
- Fix Azure backend authentication: completely disable Azure CLI auth ([`4e587ee`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4e587ee))
- Fix Terraform backend config: remove invalid backend-config flags ([`4ede2ca`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4ede2ca))
- Fix Azure Terraform backend: remove unsupported use_cli and use_azuread_auth arguments ([`6272301`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6272301))
- Fix Azure authentication: remove initial Azure Login to prevent CLI auth conflicts ([`a1b6d5c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a1b6d5c))
- Fix Azure Terraform authentication: clear CLI config and disable wrapper ([`ced5376`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ced5376))
- Fix Azure workflow: avoid terraform commands after Azure CLI login ([`57857d2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/57857d2))
- Fix Azure Terraform outputs: add missing container_registry_name and frontend_storage_account ([`24c4870`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/24c4870))
- Fix GCP workflow: import existing resources before terraform apply ([`22219d8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/22219d8))
- Optimize GCP workflow: improve import process with state checks ([`2a5597c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2a5597c))
- Add detailed debug output for GCP resource import ([`f33581c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f33581c))
- Fix GCP workflow: enable GCS backend and import existing resources ([`522a639`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/522a639))
- Fix Azure frontend: build after infrastructure deployment with correct API URL ([`e467bb0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e467bb0))
- Fix AWS frontend: build after Lambda deployment with correct API URL ([`4e3be94`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4e3be94))
- Deploy Reflex frontend to Azure and GCP ([`384a36e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/384a36e))
- ✅ Fix: Lambda API Gateway integration (SourceArn format) + Deploy full AWS stack ([`f29afbc`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f29afbc))
- 📚 Add comprehensive tooling and documentation ([`8c9b8fb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8c9b8fb))


## 2026-02-15

### 📝 Other Changes

- Add or update the Azure App Service build and deployment workflow config ([`d1e15a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d1e15a8))


## 2026-02-14

### ✨ Features

- Use Flex Consumption Plan (FC1) for Azure Function App deployment ([`c61a216`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/c61a216))

### 🐛 Bug Fixes

- Add pulumi refresh step before deploy to sync state ([`0c524cd`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/0c524cd))
- Switch from FC1 to EP1 (Elastic Premium) due to Pulumi API limitations ([`395b0ef`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/395b0ef))
- Change App Service Plan resource name to force new EP1 creation ([`e140b8d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e140b8d))


## 2026-02-15

### 📝 Other Changes

- Add or update the Azure App Service build and deployment workflow config ([`b620fb2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b620fb2))


## 2026-02-14

### ✨ Features

- Add frontend deployment workflows for GCP, AWS, and Azure ([`0b6a199`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/0b6a199))
- Add static landing page deployment for all clouds ([`11af839`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/11af839))

### 🐛 Bug Fixes

- Skip Pulumi infrastructure and use Portal-created Azure resources (FC1) ([`2457cde`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2457cde))
- Enable static website hosting and use Azure AD auth for storage ([`4283ec8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4283ec8))
- Use storage account key authentication instead of Azure AD RBAC ([`408e276`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/408e276))
- Correct Lambda handler import path (from main import app) ([`03df82e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/03df82e))
- Preserve app directory structure in Lambda package ([`d6ee071`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d6ee071))
- Add pydantic-settings dependency to Lambda package ([`3829792`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3829792))
- Update FastAPI and Pydantic versions for compatibility with pydantic-settings ([`ffa5431`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ffa5431))
- Add minio dependency to Lambda package for local backend imports ([`5bc9538`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5bc9538))
- Add python-multipart dependency for FastAPI form data handling ([`cfda862`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cfda862))
- Fix query string handling in Azure Functions HTTP trigger ([`eaadd8b`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/eaadd8b))
- Add complete ASGI scope and debug logging for Azure Functions ([`b57decb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b57decb))
- Strip 'HttpTrigger/' from route_params to get correct path ([`cea0886`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cea0886))

### 📝 Other Changes

- debug(azure): Add debug response to check route_params ([`6b4bb9e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6b4bb9e))


## 2026-02-15

### ✨ Features

- Add Pulumi Infrastructure as Code for CDN resources [skip ci] ([`e328534`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e328534))
- add multi-cloud E2E test suite ([`11cb619`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/11cb619))

### 🐛 Bug Fixes

- Add Lambda function entry point and cleanup build artifacts ([`8307b66`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8307b66))
- Use index.py instead of handler.py for Lambda entry point ([`9fe32c6`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/9fe32c6))
- Add CLOUD_PROVIDER env var and fix query_string encoding ([`e8263fa`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e8263fa))
- Add /api/HttpTrigger to API URL and set environment variables ([`4fae1eb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4fae1eb))
- Use existing COSMOS_DB_ENDPOINT for AZURE_COSMOS_ENDPOINT ([`4a175fe`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4a175fe))
- resolve frontend API URL path structure ([`4315dd7`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4315dd7))
- retrieve Cosmos DB credentials from resource directly ([`37aa17d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/37aa17d))
- optimize deployment package and add retry logic ([`202f555`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/202f555))
- handle 'partially successful' deployment status correctly ([`8f75613`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8f75613))
- prioritize 'Deployment was successful' message detection ([`3a4b1ec`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3a4b1ec))
- add retry logic for Function App hostname retrieval ([`8d3fceb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8d3fceb))
- use hostname list instead of defaultHostName for Flex Consumption ([`6005d4e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6005d4e))
- use static credentials for frontend deployments ([`41b1efd`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/41b1efd))

### 📚 Documentation

- Add comment to Lambda handler ([`ed0f6ff`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ed0f6ff))
- Update endpoints and add troubleshooting guides for recent fixes ([`d19845b`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d19845b))
- add Azure Flex Consumption troubleshooting and E2E test documentation ([`acd09c8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/acd09c8))

### ♻️ Refactoring

- consolidate duplicate scripts ([`aa4d402`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/aa4d402))


---

## Legend

- ✨ **Features**: New functionality
- 🐛 **Bug Fixes**: Bug fixes and corrections
- 📚 **Documentation**: Documentation improvements
- ♻️ **Refactoring**: Code refactoring
- ⚡ **Performance**: Performance improvements
- 🧪 **Tests**: Test additions or modifications
- 💄 **Styling**: Code style and formatting
- 🔧 **Chores**: Build, tooling, and maintenance

---

**Note**: This changelog is automatically generated. For more details, see the [commit history](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commits/main).
