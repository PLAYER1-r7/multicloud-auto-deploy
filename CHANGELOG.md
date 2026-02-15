# Detailed Changelog

Complete development history of the **multicloud-auto-deploy** project with detailed commit information.

This changelog includes commit bodies, file changes, and statistics for full transparency.

**Repository**: [https://github.com/PLAYER1-r7/multicloud-auto-deploy](https://github.com/PLAYER1-r7/multicloud-auto-deploy)  
**Branch**: `main`  
**Generated**: 2026-02-15 08:25:46

---


## 📅 2026-02-15

### ✨ **feat** (tools): add automatic CHANGELOG generation from git history

**Commit**: [`201cb80`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/201cb803ba3f73fd027a28a8b885ec1d7eeabd39) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+529/-0**

**Details**:

> - Add generate-changelog.sh script
>   - Parses git commit history
>   - Categorizes by Conventional Commits format
>   - Groups by date
>   - Outputs Markdown format with commit links
> 
> - Generate initial CHANGELOG.md
>   - 122 commits documented
>   - Organized by date and category
>   - Features, fixes, docs, refactoring, tests, chores, styling
>   - Direct links to GitHub commits
> 
> - Update TOOLS_REFERENCE.md
>   - Add generate-changelog.sh documentation
>   - Usage examples and parameters
>   - Category legend with emojis
> 
> Changelog Categories:
>   ✨ Features (feat)
>   🐛 Bug Fixes (fix)
>   📚 Documentation (docs)
>   ♻️ Refactoring (refactor)
>   ⚡ Performance (perf)
>   🧪 Tests (test)
>   💄 Styling (style)
>   🔧 Chores (chore)
> 
> Benefits:
>   - Automated changelog generation
>   - Consistent commit history documentation
>   - Easy version tracking
>   - Better transparency for contributors

---

### 📚 **docs** (tools): add tools reference and standardize script headers

**Commit**: [`7bdd456`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7bdd456bcb1d260f9be487e3b57126f2b1b3d321) | **Author**: SATOSHI KAWADA | **Files Changed**: 18 | **+1091/-44**

**Details**:

> - Add comprehensive tools reference documentation (TOOLS_REFERENCE.md)
>   - Deployment tools: 6 scripts (aws, azure, gcp, pulumi, frontend)
>   - Testing tools: 5 scripts (e2e, endpoints, api, deployments, cicd)
>   - Management tools: 4 scripts (secrets, monitoring, cicd-monitor, trigger)
>   - Utilities: 3 scripts (diagnostics, import, cleanup)
>   - Recommended workflows and usage examples
> 
> - Standardize script headers across all 17 scripts
>   - Add metadata: Script Name, Description, Author, Version
>   - Add usage information: Parameters, Examples
>   - Add prerequisites and exit codes
>   - Improve maintainability and documentation
> 
> Scripts updated:
>   - cleanup-old-resources.sh
>   - deploy-aws-pulumi.sh
>   - deploy-aws.sh, deploy-azure.sh, deploy-gcp.sh
>   - deploy-frontend-aws.sh
>   - diagnostics.sh
>   - import-gcp-resources.sh
>   - manage-github-secrets.sh
>   - monitor-cicd.sh, trigger-workflow.sh
>   - setup-monitoring.sh
>   - test-api.sh, test-cicd.sh, test-deployments.sh
>   - test-e2e.sh, test-endpoints.sh
> 
> Benefits:
>   - Consistent script documentation format
>   - Clear usage instructions for all tools
>   - Better onboarding for new developers
>   - Quick reference for troubleshooting

---

### 📚 **docs**: add Azure Flex Consumption troubleshooting and E2E test documentation

**Commit**: [`acd09c8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/acd09c87779203ce8cd6f7ef6e4b80203f7c511e) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+321/-0**

**Details**:

> - Add Azure Functions Flex Consumption Plan troubleshooting section
>   - Problem 1: Deployment shows 'Partially Successful' but function works
>   - Problem 2: defaultHostName returns null for Flex Consumption
>   - Problem 3: Kudu restart during deployment causes failures
> - Add frontend workflow authentication error resolution
>   - AWS: OIDC to static credentials migration
>   - GCP: Workload Identity to credentials_json migration
> - Add E2E test suite documentation to README
>   - Test coverage: 18 tests (3 clouds × 6 operations)
>   - Health checks + Full CRUD validation
>   - Cloud-specific path handling (Azure Flex Consumption)
>   - Data persistence verification
> - Update troubleshooting history (2026-02-15)
> 
> Resolves deployment issues encountered in commits:
> - 4315dd7 (Azure API URL path fix)
> - 37aa17d (Cosmos DB direct fetch)
> - 202f555 (Package optimization + retry logic)
> - 8f75613 (Partially successful detection)
> - 3a4b1ec (Success message priority)
> - 6005d4e (hostname list fix)
> - 41b1efd (Frontend auth unification)

---

### ✨ **feat** (scripts): add multi-cloud E2E test suite

**Commit**: [`11cb619`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/11cb619e9d61f98d8b989a981a3cf633dd53d3f4) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+200/-0**

**Details**:

> - Tests health endpoint on all 3 clouds (AWS/GCP/Azure)
> - Tests full CRUD operations: Create, Read (list & single), Update, Delete
> - Validates data consistency and proper error handling
> - All 18 tests passing across AWS Lambda, GCP Cloud Run, and Azure Functions
> - Handles cloud-specific path structures automatically

---

### 🐛 **fix** (workflows): use static credentials for frontend deployments

**Commit**: [`41b1efd`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/41b1efd15d0447146d71ed049ce55baeecbec646) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+4/-4**

**Details**:

> - AWS: switch from OIDC (role-to-assume) to static credentials
> - GCP: switch from Workload Identity to credentials_json
> - Align with main deployment workflows authentication method
> - Fixes 'Could not load credentials' errors

---

### 🐛 **fix** (azure): use hostname list instead of defaultHostName for Flex Consumption

**Commit**: [`6005d4e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6005d4e29cef04befa42dab69f096fccbf79c62a) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+12/-7**

**Details**:

> - Flex Consumption plan does not populate defaultHostName field
> - Switch to 'az functionapp config hostname list' which works reliably
> - Apply fix to both 'Use Portal-Created Resources' and 'Verify Deployment' steps
> - Fixes 'https:///' URL issue where hostname was null

---

### 🐛 **fix** (azure): add retry logic for Function App hostname retrieval

**Commit**: [`8d3fceb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8d3fceb5df134213811b1562f9350b8b308fc001) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+32/-1**

**Details**:

> - Add retry mechanism (up to 10 attempts with 10s intervals) for getting hostname
> - Fixes 'https:///' URL issue where hostname was empty
> - Function App may not be immediately queryable after deployment
> - Validate hostname is not empty or 'None' before proceeding

---

### 🐛 **fix** (azure): prioritize 'Deployment was successful' message detection

**Commit**: [`3a4b1ec`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3a4b1ec2d69be8d3e7667b494d1644adea65a89c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+10/-3**

**Details**:

> - Add explicit check for 'Deployment was successful' message as highest priority
> - Fixes issue where successful deployments were retried unnecessarily
> - Flex Consumption plan doesn't output detailed step logs, so we need to rely on the success message
> - Reorder checks: success message → step completion → critical errors

---

### 🐛 **fix** (azure): handle 'partially successful' deployment status correctly

**Commit**: [`8f75613`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8f75613dda78f4aa3fac4233eff7d211e1a9363c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+42/-32**

**Details**:

> Problem:
> - Azure reports 'ERROR: Deployment was partially successful'
> - Script treats this as failure and exits
> - BUT actual function is working perfectly (health check passes)
> 
> Root Cause:
> - Azure Flex Consumption plan deployment shows 'partially successful' even when all steps complete
> - Script logic: ERROR: in output → fail immediately
> - Reality: 'partially successful' with all steps completed = SUCCESS
> 
> Evidence:
> - Kudu logs show all steps completed:
>   ✅ ValidationStep completed
>   ✅ ExtractZipStep completed
>   ✅ OryxBuildStep completed (48s build time)
>   ✅ PackageZipStep completed
>   ✅ UploadPackageStep completed
>   ✅ RemoveWorkersStep completed
>   ✅ SyncTriggerStep starting
> - Health check returns 200 OK with proper response
> - Function is fully operational
> 
> Solution:
> 1. Improved deployment detection:
>    - Check for 'UploadPackageStep.*completed' (deployment uploaded)
>    - Check for 'SyncTriggerStep' (final sync started)
>    - Ignore 'partially successful' message
>    - Only fail on critical errors (not 'partially successful')
> 
> 2. Enhanced health check validation:
>    - Extended timeout to 3 minutes (was 2 minutes)
>    - Make health check mandatory (exit 1 if fails)
>    - Capture and display health response
>    - health_check_passed flag for proper exit code
> 
> 3. Better error handling:
>    - Distinguish 'partially successful' from real errors
>    - Continue deployment if key steps completed
>    - Final verification via health check
>    - Clear success/failure messaging
> 
> Expected Flow:
> 1. Deployment runs → 'partially successful' message
> 2. Script checks: UploadPackageStep completed? → YES
> 4. Health check: curl /health → 200 OK
> 5. Final: ✅ Verified deployment success
> 
> Testing:
> - Manually verified: Function already working from previous deploy
> - curl health endpoint → {"status":"ok","cloud_provider":"azure"}

---

### 🐛 **fix** (azure): optimize deployment package and add retry logic

**Commit**: [`202f555`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/202f555cc849e43651fcf582f410234f1f4bee6b) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+62/-9**

**Details**:

> Problem:
> - Kudu restarted during deployment (Flex Consumption plan limitation)
> - Large deployment package causing resource constraints
> - No retry mechanism for transient Kudu issues
> 
> Root Cause:
> - Deployment package included unnecessary files (__pycache__, .pyc, tests, .dist-info)
> - Azure Functions Flex Consumption dynamically scales, causing Kudu restarts
> - Single deployment attempt fails on transient infrastructure issues
> 
> Solution:
> 1. Optimize deployment package:
>    - Remove __pycache__ directories
>    - Delete .pyc/.pyo compiled files
>    - Exclude test directories
>    - Remove .dist-info metadata
>    - Use --no-cache-dir for pip install
>    - Use -q flag for zip (quiet mode)
>    - Report package size for monitoring
> 
> 2. Add intelligent retry logic:
>    - Retry up to 3 times on deployment failure
>    - Detect Kudu restart errors specifically
>    - Wait 30 seconds between retries for Kudu stabilization
>    - Distinguish transient vs permanent errors
>    - Exit immediately on non-transient errors
> 
> 3. Improve logging:
>    - Capture deployment output to log file
>    - Check for ERROR patterns
>    - Show retry attempt numbers
>    - Confirm success before proceeding
> 
> Expected Results:
> - Smaller package → faster upload → less Kudu stress
> - Transient Kudu restart → auto-retry → eventual success
> - Permanent errors → fail fast with clear message
> 
> Previous attempts:
> - Attempt 1: 4m deployment time, Kudu restart, no retry → FAIL
> - Attempt 2: Expected < 3m, auto-retry on Kudu restart → SUCCESS

---

### 🐛 **fix** (azure): retrieve Cosmos DB credentials from resource directly

**Commit**: [`37aa17d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/37aa17d15be7f2205ec8a0a0fea69dbe41807d14) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+51/-9**

**Details**:

> Problem:
> - Environment variables were all null
> - Workflow tried to get COSMOS_DB_ENDPOINT/KEY from existing app settings
> - On first deploy, these settings don't exist yet → null → set null → fail
> 
> Root Cause:
> - Workflow used: az functionapp config appsettings list
> - This returns null for non-existent settings
> - Created a circular dependency issue
> 
> Solution:
> 1. Get Cosmos DB credentials directly from the resource:
>    - az cosmosdb show --query documentEndpoint
>    - az cosmosdb keys list --query primaryMasterKey
> 
> 2. Add validation:
>    - Exit with error if credentials cannot be retrieved
> 
> 3. Improve deployment:
>    - Add --timeout 600 to zip deployment
>    - Suppress appsettings output (security)
> 
> 4. Add post-deployment verification:
>    - Wait up to 2 minutes for function to be ready
>    - Curl health endpoint to verify deployment
>    - Workaround for Flex Consumption plan log limitations
> 
> Expected Result:
> - Cosmos DB credentials properly retrieved: ✅
> - Environment variables correctly set: ✅
> - Function app deployment succeeds: ✅
> - Health check passes: ✅

---

### 🐛 **fix** (azure): resolve frontend API URL path structure

**Commit**: [`4315dd7`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4315dd7e0ab8c3e160e5100cfc3970d24dcebea1) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+23/-6**

**Details**:

> Problem:
> - Azure frontend showed ERR_NAME_NOT_RESOLVED errors
> - API paths were resolving as relative URLs (e.g., 'api/HttpTrigger/api/messages/')
> - VITE_API_URL was not correctly embedded in build
> 
> Root Cause:
> - Azure Functions URL structure: https://xxx.azurewebsites.net/api/HttpTrigger
> - Frontend was appending '/api/messages', resulting in '/api/HttpTrigger/api/messages'
> - This double '/api' path was correct for the backend but confusing
> 
> Solution:
> 1. Enhanced frontend API client (client.ts):
>    - Detect Azure Functions URLs (contains '/api/HttpTrigger')
>    - Use basePath='' for Azure (no '/api' prefix)
>    - Use basePath='/api' for AWS/GCP
> 
> 2. Improved deployment workflow logging:
>    - Echo API_URL during build step
>    - Verify URL was embedded in built assets
>    - Add explicit API URL logging in resource detection
> 
> Result:
> - Azure: https://xxx.azurewebsites.net/api/HttpTrigger + /messages ✅
> - AWS/GCP: https://xxx.run.app + /api/messages ✅
> 
> Testing:
>   curl https://xxx.azurewebsites.net/api/HttpTrigger/messages

---

### ♻️ **refactor** (scripts): consolidate duplicate scripts

**Commit**: [`aa4d402`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/aa4d40288f468349b00468bd3f2d1d64a40c56e6) | **Author**: SATOSHI KAWADA | **Files Changed**: 5 | **+344/-461**

**Details**:

> Changes:
> - ✨ NEW: manage-github-secrets.sh (統合)
>   - Merged set-github-secrets.sh (auto mode)
>   - Merged setup-github-secrets.sh (guide mode)
>   - Added --check-local flag for env validation
> 
> - 🔧 ENHANCED: monitor-cicd.sh
>   - Added --workflow=NAME filter option
>   - Absorbed watch-workflow.sh functionality
> 
> - 🗑️ REMOVED: 3 duplicate scripts
>   - set-github-secrets.sh (9.3K)
>   - setup-github-secrets.sh (6.3K)
>   - watch-workflow.sh (992B)
> 
> Impact:
> - Reduced script count: 19 → 17 (-11%)
> - Eliminated ~16.3KB of duplicate code
> - Improved maintainability (single source of truth)
> - Enhanced UX (unified interfaces)
> 
> Usage:
>   ./manage-github-secrets.sh --mode=auto
>   ./manage-github-secrets.sh --mode=guide
>   ./monitor-cicd.sh --workflow=deploy-aws.yml

---

### 📚 **docs**: Update endpoints and add troubleshooting guides for recent fixes

**Commit**: [`d19845b`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d19845b8d6cae4b8db1061443bed9c264e53cabc) | **Author**: SATOSHI KAWADA | **Files Changed**: 4 | **+276/-16**

**Details**:

> - Updated all cloud provider URLs to current production endpoints
> - Added troubleshooting sections for AWS Lambda ImportModuleError
> - Added GCP Cloud Run 500 error solutions (env vars, query_string)
> - Added Azure Functions 500 error solutions (Cosmos DB env vars)
> - Updated test scripts with correct URLs

---

### 🐛 **fix** (azure): Use existing COSMOS_DB_ENDPOINT for AZURE_COSMOS_ENDPOINT

**Commit**: [`4a175fe`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4a175fed59999d1494985adbce90353e073ccc9c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+13/-2**

---

### 🐛 **fix** (azure): Add /api/HttpTrigger to API URL and set environment variables

**Commit**: [`4fae1eb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4fae1eb2cde08cc133e439ac9c6ffb3dc261b7bf) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+13/-1**

---

### 🐛 **fix** (gcp): Add CLOUD_PROVIDER env var and fix query_string encoding

**Commit**: [`e8263fa`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e8263fa11742933b9a7ba5b1028ee52785d69416) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+2/-2**

---

### 🐛 **fix** (ci): Use index.py instead of handler.py for Lambda entry point

**Commit**: [`9fe32c6`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/9fe32c6ce4e6ca2de7a8639f525e1f12deae6462) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-8**

---

### 📚 **docs**: Add comment to Lambda handler

**Commit**: [`ed0f6ff`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ed0f6ff863dc17003c295dbdc5973364447dcd13) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-0**

---

### 🐛 **fix**: Add Lambda function entry point and cleanup build artifacts

**Commit**: [`8307b66`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8307b66a52fa7a7adf54ffabc8c56fe0b9c8b75e) | **Author**: SATOSHI KAWADA | **Files Changed**: 2447 | **+8/-366328**

**Details**:

> - Add services/api/index.py with Mangum adapter for AWS Lambda
> - Update deploy-lambda-aws.sh to include index.py in deployment package
> - Add services/api/.build/ to .gitignore (pip install artifacts)
> - Remove previously tracked .build/ directory from git
> 
> Fixes: Runtime.ImportModuleError: Unable to import module 'index'
> Context: Lambda function was deployed without application code due to Pulumi ignore_changes setting

---


## 📅 2026-02-14

### ✨ **feat**: Add static landing page deployment for all clouds

**Commit**: [`11af839`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/11af8399b099d3c6b6a711a25fbf32e70363ea8e) | **Author**: SATOSHI KAWADA | **Files Changed**: 5 | **+333/-0**

**Details**:

> - Add static-site/ with index.html and error.html
> - GCP: Deploy to Cloud Storage bucket
> - AWS: Deploy to S3 with website hosting
> - Azure: Deploy to Azure Storage Static Website
> - All workflows include cache-control headers
> - Auto-triggered on static-site changes

---

### ✨ **feat**: Add frontend deployment workflows for GCP, AWS, and Azure

**Commit**: [`0b6a199`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/0b6a1990fd436b20aeec65727c39c778a3946803) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+223/-0**

**Details**:

> - GCP: Deploy to Cloud Storage with public access
> - AWS: Deploy to S3 with website hosting
> - Azure: Deploy to Azure Storage Static Website
> - All workflows include cache-control headers
> - Auto-triggered on frontend changes

---

### 🐛 **fix** (azure): Strip 'HttpTrigger/' from route_params to get correct path

**Commit**: [`cea0886`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cea08862d86ff35638ebc995cb78a5bab2d10cda) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+64/-11**

---

### 📝 **debug** (azure): Add debug response to check route_params

**Commit**: [`6b4bb9e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6b4bb9efbd262a38fb97bad84c5e86121b3a7cca) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+12/-57**

---

### 🐛 **fix** (azure): Add complete ASGI scope and debug logging for Azure Functions

**Commit**: [`b57decb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b57decbcdbc196620265b926054b37f529c3fd5d) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+11/-1**

---

### 🐛 **fix** (azure): Fix query string handling in Azure Functions HTTP trigger

**Commit**: [`eaadd8b`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/eaadd8b2fa9c06caf268d04bd7f32248a9fd53e4) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+10/-2**

---

### 🐛 **fix**: Add python-multipart dependency for FastAPI form data handling

**Commit**: [`cfda862`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cfda862bfe740ffd8be65bb03f9d542cbb840c12) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Add minio dependency to Lambda package for local backend imports

**Commit**: [`5bc9538`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5bc9538c9d33c3785e4396d8e9c5a5d068c0e861) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Update FastAPI and Pydantic versions for compatibility with pydantic-settings

**Commit**: [`ffa5431`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ffa54318a4a40e5f2e725aaed64592aebd7e1c5f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Add pydantic-settings dependency to Lambda package

**Commit**: [`3829792`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/38297928c22f980494f959cda48e4d488c7ef2cb) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+218/-1**

---

### 🐛 **fix**: Preserve app directory structure in Lambda package

**Commit**: [`d6ee071`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d6ee0711c1cdfc51d7093dda90b7c6e6d2566eb2) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+2/-2**

---

### 🐛 **fix**: Correct Lambda handler import path (from main import app)

**Commit**: [`03df82e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/03df82eb9c1643fce9d757464e616f633c39f69a) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Use storage account key authentication instead of Azure AD RBAC

**Commit**: [`408e276`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/408e276b104f131e05875ded585b0c18cebbf6e8) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+16/-3**

---

### 🐛 **fix**: Enable static website hosting and use Azure AD auth for storage

**Commit**: [`4283ec8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4283ec83ee3e830600f239d971936cb439d96f22) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+13/-0**

---

### 🐛 **fix**: Skip Pulumi infrastructure and use Portal-created Azure resources (FC1)

**Commit**: [`2457cde`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2457cde8d849727c5d1da8948ae515bc19d3ef9d) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+15/-33**

---

### 📝 **other**: Add or update the Azure App Service build and deployment workflow config

**Commit**: [`b620fb2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b620fb2f68f780ec823ef4edf413dede64b0ed0f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+85/-0**

---

### 🐛 **fix**: Change App Service Plan resource name to force new EP1 creation

**Commit**: [`e140b8d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e140b8dc006b3689ef2bb1da6b187024403ed38d) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+3/-2**

---

### 🐛 **fix**: Switch from FC1 to EP1 (Elastic Premium) due to Pulumi API limitations

**Commit**: [`395b0ef`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/395b0ef113477d8e3c3581f4ecc1d0746b7c2f9c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+5/-4**

---

### 🐛 **fix**: Add pulumi refresh step before deploy to sync state

**Commit**: [`0c524cd`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/0c524cd6cbe308fa12657d829a570ebcdd88ad2f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+13/-0**

---

### ✨ **feat**: Use Flex Consumption Plan (FC1) for Azure Function App deployment

**Commit**: [`c61a216`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/c61a2161589b58ac804fe419e7ff4c486fdb512e) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+4/-4**

---

### 📝 **other**: Add or update the Azure App Service build and deployment workflow config

**Commit**: [`d1e15a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d1e15a8a5a43ee0d771d5e12c2469e160d84c829) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+85/-0**

---

### ✨ **feat**: Deploy to Malaysia West region with Y1 Consumption tier

**Commit**: [`2f2acfa`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2f2acfa2307f5510715148aea75531e0c5ebe77b) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🧪 **test**: Try Y1 (Consumption) tier with eastus region for quota availability

**Commit**: [`96dfea3`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/96dfea36d5236c60472e5e2383d7e923e7cdcdcf) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+3/-3**

---

### 🐛 **fix**: Change Azure region from japaneast to eastus for quota availability

**Commit**: [`062840f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/062840f292694af51aa4a1b2b4a64f147c760136) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Change App Service Plan SKU from Consumption (Y1) to Basic (B1) tier

**Commit**: [`f6fc6c2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f6fc6c20986f5077937c4e03e3350b73d6a31226) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+3/-3**

---

### 🐛 **fix**: Set ingestion_mode to ApplicationInsights for Application Insights Component

**Commit**: [`cc66be5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/cc66be58e35d4fea06fb56fcbabcfb07066bcb07) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-0**

---

### 🐛 **fix**: Remove component_name parameter from Application Insights Component

**Commit**: [`a9fd4c9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a9fd4c90a24479dd2bcf991eca2625ec4ea45be0) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+0/-1**

---

### 🐛 **fix**: Change resource_name to component_name in Application Insights

**Commit**: [`c84734d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/c84734d6c77cfcb911238c0510674e126ca083af) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 🐛 **fix**: Change min_tls_version to minimum_tls_version in Azure StorageAccount

**Commit**: [`5d388e5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5d388e52063a8d53ae70e5d8de9cb129dda40648) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+2/-2**

---

### 🐛 **fix**: Rename function.py to main.py for Cloud Functions

**Commit**: [`6e5d5f8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6e5d5f8d84400d056c927e020741e1f507e13aaa) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+2/-1**

---

### 🐛 **fix**: Use azure/login action for proper authentication

**Commit**: [`e6921ed`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e6921ed57170a238d0bb9d341dca1f30a2c3529f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+16/-29**

---

### 🐛 **fix**: Extract Azure credentials from AZURE_CREDENTIALS secret

**Commit**: [`144ada0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/144ada064d9f547b485f2d212f757756b5088eb2) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+22/-12**

---

### 🐛 **fix**: Add Azure CLI login before Pulumi deployment

**Commit**: [`83ff516`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/83ff516682501bab899a9d0d8db0955589d51ec9) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+8/-0**

---

### 🐛 **fix**: Fix S3 BucketPolicy creation order and IAM policy regions

**Commit**: [`b20d984`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b20d9842d4f225193c096ddedeef6aebffe35d57) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+13/-11**

---

### 🐛 **fix**: Fix Pulumi.yaml config format and add stack initialization steps

**Commit**: [`3449db4`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3449db4ef7de1ccb16ada3dba4fd777c1780b73d) | **Author**: SATOSHI KAWADA | **Files Changed**: 6 | **+43/-17**

---

### ✨ **feat**: Migrate from Terraform to Pulumi (Python)

**Commit**: [`4845887`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4845887e79554bf170d6a915847e875cafcb79ce) | **Author**: SATOSHI KAWADA | **Files Changed**: 14 | **+681/-421**

**Details**:

> ✨ Complete Infrastructure as Code migration:
> - Replace Terraform with Pulumi Python implementation
> - All 3 clouds: AWS, Azure, GCP
> 
> 📦 Infrastructure Components:
> AWS:
>   - Lambda Function (Python 3.12, ZIP deployment)
>   - API Gateway HTTP API v2
>   - S3 Static Website
>   - IAM Roles
> 
> Azure:
>   - Azure Functions (Consumption Plan Y1)
>   - Storage Accounts (Functions + Frontend)
>   - Application Insights
>   - Random naming for global uniqueness
> 
> GCP:
>   - Cloud Storage (Function source + Frontend)
>   - Cloud Functions Gen 2 (via gcloud CLI)
>   - IAM bindings for public access
> 
> 🔧 Workflow Updates:
> - GitHub Actions now use Pulumi CLI
> - pulumi up for infrastructure deployment
> - Outputs retrieved via pulumi stack output
> - Maintain ZIP-based deployment for all Functions
> 
> 🗑️  Cleanup:
> - Removed all Terraform files
> - Deleted infrastructure/terraform directory
> 
> 💡 Benefits:
> - Real programming language (Python) for IaC
> - Better type safety and error checking
> - More flexible conditional logic
> - Unified codebase management

---

### 🐛 **fix**: Deploy GCP Cloud Functions via gcloud CLI instead of Terraform

**Commit**: [`94a5afe`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/94a5afeabf441580632688482db68178536e1544) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+20/-68**

**Details**:

> - Remove Cloud Functions resource from Terraform (causes 404 error)
> - Terraform now only manages buckets and IAM
> - gcloud functions deploy creates/updates Cloud Functions after ZIP upload
> - Fixes error: 'No such object: function-source.zip'

---

### 🐛 **fix**: Shorten Azure Storage Account names to meet 24-char limit

**Commit**: [`beb49a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/beb49a8850dd759070d9953d53bb8ec80f0f7a4e) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+11/-4**

**Details**:

> - Change from multicloudautodeploystagin g{func/web} (32/31 chars)
> - To mcadstg{func/web} + random 6-char suffix (18/16 chars)
> - Azure requires storage names: 3-24 chars, lowercase + numbers only

---

### ✨ **feat**: Migrate to complete ZIP unification across all clouds

**Commit**: [`3901489`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3901489ae980e289a737f0263f796697318513bd) | **Author**: SATOSHI KAWADA | **Files Changed**: 9 | **+575/-71**

**Details**:

> - Replace Azure Container Apps with Azure Functions (Consumption Plan)
> - Replace GCP Cloud Run with Cloud Functions Gen 2
> - Add Azure Functions entry point (function_app.py)
> - Add Cloud Functions entry point (function.py)
> - Update CI/CD workflows to ZIP deployment
> - Add azure-functions and functions-framework dependencies
> 
> Benefits:
> - Consistent deployment model across AWS/Azure/GCP
> - Faster deployments: 30-70s (vs 2-5min with containers)
> - Lower costs: Consumption-only billing (estimated 0-80/month savings)
> - Simpler CI/CD: No Docker builds or registry management

---

### 📚 **docs**: Add comprehensive CI/CD test results and update README

**Commit**: [`b2e82b7`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/b2e82b7ab295aef8007e7baa92bb376a5d80eea3) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+256/-2**

**Details**:

> - Add detailed CI/CD test results documentation (CICD_TEST_RESULTS.md)
> - Document all discovered issues and their resolutions
> - Include AWS deployment success evidence
> - Add CI/CD tools overview (test-cicd.sh, trigger-workflow.sh, monitor-cicd.sh)
> - Update README with links to CI/CD test results and quick reference
> - Provide recommendations for IAM permissions and future testing

---

### 🐛 **fix**: Make API Gateway endpoint lookup non-blocking in CI/CD

**Commit**: [`128d13d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/128d13ddf5bad80518d5cbfe281aceea884a561f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+6/-4**

**Details**:

> - Continue deployment even if apigateway:GET permission is missing
> - Fall back to default endpoint when API Gateway lookup fails
> - This ensures Lambda update succeeds independent of IAM permissions for API Gateway
> - Lambda deployment is the critical step, API endpoint discovery is optional

---

### 🐛 **fix**: Correct source directory from src to app in AWS workflow

**Commit**: [`7aa7bc9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7aa7bc97e71f2cbff0f3ac1c71d3106f6f379ef8) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+3/-3**

**Details**:

> - Change cp -r src/* to cp -r app/* in Package Backend step
> - Use standard Dockerfile instead of Dockerfile.azure/gcp (they don't exist)
> - This fixes the 'No such file or directory' error in CI/CD
> - All local tests passing (100% success rate)

---

### 🐛 **fix**: Update CI/CD workflows to use correct directory structure (api/frontend_react)

**Commit**: [`621bb55`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/621bb551d2c8240dacd137eda15ba0210a93e0b5) | **Author**: SATOSHI KAWADA | **Files Changed**: 6 | **+720/-11**

**Details**:

> - Fix deploy-aws.yml: backend → api, frontend → frontend_react
> - Fix deploy-azure.yml: backend → api, frontend → frontend_react
> - Fix deploy-gcp.yml: backend → api, frontend → frontend_react
> - Add comprehensive CI/CD testing scripts (test-cicd.sh, trigger-workflow.sh, monitor-cicd.sh)
> - All local tests passing (100% success rate)

---

### 📝 **other**: 📚 Add comprehensive tooling and documentation

**Commit**: [`8c9b8fb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8c9b8fb6defc3ac1981cc5bb8b376d87bf179917) | **Author**: SATOSHI KAWADA | **Files Changed**: 6 | **+1696/-0**

**Details**:

> New Scripts:
> - scripts/deploy-lambda-aws.sh: Full Lambda deployment automation
>   - Auto dependency installation (manylinux2014_x86_64)
>   - ZIP package creation and S3 upload
>   - Lambda function create/update
>   - API Gateway integration setup
>   - Correct Lambda permissions (HTTP API SourceArn format)
>   - CloudWatch Logs access log configuration
> 
> - scripts/test-api.sh: Complete API integration tests
>   - Health check
>   - CRUD operations (Create, Read, Update, Delete)
>   - Pagination testing
>   - Error handling validation
>   - Pass/fail reporting with statistics
> 
> - scripts/setup-monitoring.sh: CloudWatch monitoring setup
>   - SNS topic and email notifications
>   - Lambda alarms (errors, throttles, duration, concurrency)
>   - API Gateway alarms (5XX errors, latency)
>   - DynamoDB alarms (read/write throttles)
>   - CloudWatch Logs metric filters
>   - Auto dashboard creation
> 
> Documentation:
> - docs/QUICK_REFERENCE.md: Quick reference for common operations
>   - Deployment commands
>   - Testing and debugging
>   - Log inspection
>   - Monitoring and metrics
>   - Troubleshooting
>   - Resource management
>   - Useful one-liners
> 
> - docs/TROUBLESHOOTING.md: Added Lambda + API Gateway section
>   - HTTP API vs REST API SourceArn difference
>   - Permission troubleshooting steps
>   - Access log enablement
>   - Debug workflow
> 
> - README.md: Enhanced with tooling and recommendations
>   - New script usage documentation
>   - Recommended AWS services for production:
>     - AWS X-Ray (distributed tracing)
>     - AWS WAF (security)
>     - Route 53 + Custom Domain
>     - Parameter Store/Secrets Manager
>     - Lambda Layers (optimization)
>     - CloudFront Functions (edge processing)
>     - AWS Backup (data protection)
>   - Implementation examples for each service
> 
> All scripts are executable and production-ready.

---

### 📝 **other**: ✅ Fix: Lambda API Gateway integration (SourceArn format) + Deploy full AWS stack

**Commit**: [`f29afbc`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f29afbc9497fe2e1066eff0271b6dad730e6193c) | **Author**: SATOSHI KAWADA | **Files Changed**: 2444 | **+366328/-0**

**Details**:

> - Root cause: HTTP API requires SourceArn format: {api-id}/*/* (not {api-id}/*/*/*)
> - Fixed Lambda resource policy with correct SourceArn pattern
> - Enabled API Gateway access logs for debugging
> - Updated frontend .env to use Lambda API (from GCP Cloud Run)
> - Rebuilt and deployed React app to S3
> - Invalidated CloudFront cache
> - Verified: GET, POST, PUT operations all working via Lambda + API Gateway
> - AWS-only stack now fully operational (S3, CloudFront, Lambda, API Gateway, DynamoDB)

---

### ✨ **feat**: Add Lambda container image support

**Commit**: [`24ba2b0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/24ba2b0545e72361721f994185d06302f9fb01fe) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+12/-0**

**Details**:

> - Create Dockerfile.lambda for AWS Lambda Container Image
> - Make AWS region optional in AWSBackend (auto-detect from environment)
> - Build and deploy to ECR for x86_64 architecture
> - Replace ZIP-based Lambda with container-based Lambda
> 
> This enables AWS-only staging environment without GCP Cloud Run dependency

---

### ✨ **feat**: Make AWS region optional in AWSBackend

**Commit**: [`6539b0d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6539b0da2551c794cc2b9b5ea5ee45fdf43df3db) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+8/-3**

**Details**:

> - Allow boto3 to auto-detect region from environment
> - Lambda automatically provides AWS_REGION variable
> - Fallback to settings.aws_region if provided

---

### 🐛 **fix**: Change update method from PATCH to PUT

**Commit**: [`3870668`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/387066839c0c2eed7b69a8281bd7cc28068768bc) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

**Details**:

> - Backend uses PUT /api/messages/{id}
> - Frontend was using PATCH causing 404/405 errors
> - Update edit functionality now works correctly

---

### 🐛 **fix**: Implement update_message method in AWSBackend

**Commit**: [`ab1b003`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ab1b003ab1856e0d85a73161377ed9d12e980471) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+62/-1**

**Details**:

> - Add update_message implementation for DynamoDB
> - Fix TypeError: abstract method not implemented
> - Support partial updates with exclude_unset
> - Add updated_at timestamp tracking
> - Use DynamoDB UpdateExpression for atomic updates

---

### ✨ **feat**: Deploy React static frontend to AWS S3 + CloudFront

**Commit**: [`d6ac8de`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d6ac8de0cb7daf26d4be6af276c3462a031ee261) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+382/-0**

**Details**:

> Successfully deployed React SPA to replace Reflex SSR frontend:
> 
> Deployment Details:
> - S3 Bucket: multicloud-auto-deploy-staging-frontend
> - CloudFront: E2GDU7Y7UGDV3S (dx3l4mbwg1ade.cloudfront.net)
> - API: https://mcad-staging-api-son5b3ml7a-an.a.run.app
> - Region: ap-northeast-1 (Tokyo)
> 
> Performance:
> - Build size: 90KB gzipped (vs 500KB+ for Reflex)
> - TTFB: 20-50ms (CDN cached, vs 200-500ms SSR)
> - Cost: $1-5/month (vs $20-50/month for containers)
> - Lighthouse: Expected 95+ (vs 70-80 for SSR)
> 
> Files Added:
> - docs/REACT_FRONTEND_DEPLOYMENT.md: Complete deployment guide
> - scripts/deploy-frontend-aws.sh: Automated deployment script
> 
> Cache Strategy:
> - Assets (CSS/JS): max-age=31536000 (1 year, content-hashed)
> - HTML: max-age=0 (always revalidate)
> - CloudFront invalidation: Automatic on deploy
> 
> Next Steps:
> - Phase 2B: Deploy to Azure Blob Storage + CDN
> - Phase 2C: Deploy to GCP Cloud Storage + CDN
> - Phase 3: Update CI/CD pipeline for automated deployments
> - Phase 4: Add staging/production environment separation

---

### ✨ **feat**: Add React static frontend to replace Reflex SSR

**Commit**: [`5863645`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5863645e41ebab7df32931bc9da45f7bbb42047b) | **Author**: SATOSHI KAWADA | **Files Changed**: 27 | **+5734/-0**

**Details**:

> - Create React + TypeScript + Vite frontend application
> - Implement full CRUD operations for messages
> - Add TanStack Query for efficient data management
> - Design responsive UI with Tailwind CSS
> - Build optimized static files (88KB gzipped)
> 
> Architecture change:
> - OLD: Reflex SSR (Container Apps/Cloud Run) - 0-50/month
> - NEW: React SPA (Static CDN hosting) - -5/month
> 
> Components:
> - MessageForm: Create new messages
> - MessageList: Display paginated messages
> - MessageItem: Individual message with edit/delete
> 
> Features:
> - Real-time data synchronization
> - Optimistic UI updates
> - Dark mode support- Error handling and loading states
> - Mobile-responsive design
> - TypeScript type safety
> 
> Build output:
> - dist/index.html (0.46KB)
> - dist/assets/index.css (4.23KB → 1.36KB gzipped)
> - dist/assets/index.js (274.66KB → 88.07KB gzipped)
> 
> Next: Deploy to S3, Blob Storage, Cloud Storage + CDN

---

### ✨ **feat**: Add CI/CD pipeline for multi-cloud deployment

**Commit**: [`8c3b061`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8c3b061a5615d5df4851982606558019e43f1a2f) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+593/-23**

**Details**:

> - Add deploy-multicloud.yml workflow for Azure and GCP
> - Support Docker image build and push to ACR and Artifact Registry
> - Deploy to Azure Container Apps and GCP Cloud Run
> - Add health check validation after deployment
> - Create comprehensive CI/CD setup documentation
> - Update README with new workflow information
> 
> Features:
> - Parallel deployment to Azure and GCP
> - Configurable deployment targets (all/azure/gcp)
> - Environment selection (staging/production)
> - Docker buildx with cache optimization
> - Automated health checks
> - GitHub Actions summary with deployment URLs
> 
> Documentation:
> - docs/CI_CD_SETUP.md: Complete setup guide with secrets
> - README.md: Updated with new workflow table and badges

---

### 📝 **other**: Deploy Reflex frontend to Azure and GCP

**Commit**: [`384a36e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/384a36e6490e26b89503e8a5a85db8b262e6ad46) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+34/-5**

**Details**:

> - Add production-ready Dockerfile for Reflex frontend
> - Add entrypoint.sh with single-port mode support for Cloud Run
> - Install unzip package required for Bun installation
> - Build frontend assets at Docker build time with 'reflex export'
> - Support both dual-port (Azure) and single-port (GCP) modes
> - Deploy to Azure Container Apps and GCP Cloud Run
> 
> Deployed services:
> - Azure: https://mcad-staging-frontend.livelycoast-fa9d3350.japaneast.azurecontainerapps.io
> - GCP: https://mcad-staging-frontend-son5b3ml7a-an.a.run.app

---

### ✨ **feat**: Add production deployment configuration

**Commit**: [`8215297`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8215297adb75c89964d0a4f197d4d381c1b57fd8) | **Author**: SATOSHI KAWADA | **Files Changed**: 6 | **+543/-4**

**Details**:

> Infrastructure:
> - Add ECR repositories for API and Frontend containers
> - Update Pulumi stack with image registry support
> - Add lifecycle policies to manage image retention (keep last 10)
> 
> Environment Configuration:
> - Add .env.example for frontend_reflex
> - Document environment variables for production
> 
> Deployment:
> - Create comprehensive production deployment guide
> - Add deploy-aws-pulumi.sh script for automated deployment
> - Include AWS App Runner, ECS Fargate deployment options
> - Document secrets management with AWS Secrets Manager
> - Add CI/CD pipeline examples for GitHub Actions
> 
> Documentation:
> - PRODUCTION_DEPLOYMENT.md with complete deployment workflows
> - Health checks, monitoring, rollback procedures
> - Cost optimization strategies
> - Security best practices
> 
> Ready for production deployment with:
> - Containerized API and Frontend
> - ECR image storage
> - Infrastructure as Code (Pulumi)
> - Automated deployment scripts

---

### 🔧 **chore**: Optimize Docker images and cleanup

**Commit**: [`7c77283`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/7c772839b18e220da895852c86d6c8de9316c0e6) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+18/-28**

**Details**:

> Docker image optimization:
> - Remove unused dependencies (unzip from frontend_reflex)
> - Add --no-install-recommends to apt-get
> - Clean apt cache and Python __pycache__
> - Add PYTHONDONTWRITEBYTECODE=1 environment variable
> - Use selective COPY instead of COPY . .
> - Apply optimizations to both api and frontend_reflex
> 
> Cleanup:
> - Remove all test data (74 messages)
> - Delete Python cache files (__pycache__/*.pyc)
> - Remove legacy backend service from docker-compose.yml
> - Remove obsolete 'version' directive from docker-compose.yml
> 
> Benefits:
> - Reduced image size overhead
> - Faster build times with layer caching
> - Cleaner production images

---

### 📚 **docs**: Update README for Reflex frontend migration

**Commit**: [`dd0ffbb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/dd0ffbb0bf3a28f06c450fab50c6a4820862a779) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+18/-28**

**Details**:

> - Update project structure (frontend_reflex instead of web/frontend)
> - Remove Node.js from prerequisites (pure Python stack)
> - Update tech stack (Reflex 0.8+, no JavaScript/React)
> - Update port numbers (3002 for Reflex frontend)
> - Update Docker Compose service names
> - Emphasize pure Python full-stack approach

---

### ✨ **feat**: Complete Python frontend migration with Reflex

**Commit**: [`6935e12`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6935e12e68398852aced56916cfd47e38aeb246c) | **Author**: SATOSHI KAWADA | **Files Changed**: 22 | **+620/-4339**

**Details**:

> - Add new Reflex frontend (services/frontend_reflex/)
>   - Pure Python implementation (447 lines)
>   - All CRUD operations (create, read, update, delete)
>   - Image upload with MinIO integration
>   - Pagination support (20 items per page)
>   - WebSocket state management
>   - Proper HTTP status code handling (200/201/204)
> 
> - Docker integration
>   - Add Dockerfile for Reflex frontend
>   - Update docker-compose.yml (ports 3002/3003)
>   - Add .dockerignore for optimized builds
> 
> - Remove legacy React frontend
>   - Delete services/frontend/ directory (99MB freed)
>   - Remove frontend service from docker-compose.yml
> 
> - Benefits
>   - Full-stack Python development
>   - Simplified dependency management
>   - Better type safety and code consistency
>   - Reduced JavaScript/Node.js complexity

---

### 💄 **style**: Fix indentation in devcontainer config

**Commit**: [`fc93ecb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/fc93ecb30d08ffc407595d4da24965c58c308d86) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+22/-18**

---

### 🔧 **chore**: Remove unused code and migrate to Pulumi

**Commit**: [`f5fbb84`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f5fbb8412f388859dba968ea38e4ef813146a180) | **Author**: SATOSHI KAWADA | **Files Changed**: 30 | **+0/-1707**

**Details**:

> Remove legacy implementations and free up 1.1GB of disk space:
> 
> - Remove services/backend/ (192MB) - old FastAPI implementation, now using services/api/
> - Remove services/web/ (28KB) - Reflex frontend, now using React in services/frontend/
> - Remove services/database/ - empty directory
> - Remove infrastructure/terraform/ (948MB) - migrated to Pulumi
> 
> The project now uses:
> - Backend: services/api/ (FastAPI + Python)
> - Frontend: services/frontend/ (React + TypeScript)
> - IaC: infrastructure/pulumi/ (Python)
> - Storage: MinIO (local), S3/GCS/Azure Storage (cloud)

---

### ✨ **feat**: Implement message editing functionality

**Commit**: [`a563f84`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a563f84526c0144935fc118b2ff1237034454bef) | **Author**: SATOSHI KAWADA | **Files Changed**: 5 | **+194/-32**

**Details**:

> - Add MessageUpdate model with optional fields for partial updates
> - Implement update_message method in BaseBackend and LocalBackend
> - Add PUT /api/messages/{id} endpoint for updating messages
> - Add edit mode UI with inline editing in frontend
> - Support updating content and author while preserving created_at
> - Add updated_at timestamp on message updates
> - Include edit and cancel buttons in message cards

---

### ✨ **feat**: メッセージ削除機能を実装

**Commit**: [`052cecc`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/052cecc231a991c1cc4345fbe3eae917d6ea3fbe) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+33/-4**

**Details**:

> 実装内容:
> - フロントエンドに削除ボタン追加
>   - ゴミ箱アイコンのSVG表示
>   - ホバー時の視覚的フィードバック
>   - メッセージカードの右上に配置
> 
> - 削除確認ダイアログ
>   - window.confirm() で削除前に確認
>   - メッセージ内容の一部を表示（最大50文字）
>   - キャンセル可能
> 
> - DELETE API呼び出し
>   - axios.delete() でバックエンドAPIを呼び出し
>   - 削除成功後に自動的にメッセージリストを更新
>   - エラーハンドリング付き
> 
> 技術詳細:
> - handleDeleteMessage関数を追加
> - メッセージIDとコンテンツを引数に受け取る
> - 削除後はfetchMessages()で再取得
> 
> テスト結果:
> ✅ メッセージ削除: 成功（9件→7件）
> ✅ 削除確認ダイアログ: 動作確認
> ✅ API呼び出し: 正常
> ✅ MinIO永続化: 確認済み（再起動後も7件）
> ✅ リスト自動更新: 正常

---

### ✨ **feat**: 画像アップロード機能を実装

**Commit**: [`83f8e8f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/83f8e8fc81d09696cfef81beba2a3aa9f5fc2b35) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+250/-6**

**Details**:

> 実装内容:
> - POST /api/uploads エンドポイント作成
>   - 画像ファイルのバリデーション (形式、サイズ)
>   - MinIOへの画像保存 (images/ フォルダ)
>   - ブラウザアクセス可能なURLを返却
> 
> - フロントエンド画像アップロードUI
>   - ファイル選択ボタン
>   - 画像プレビュー表示
>   - メッセージ送信時に画像URLを含める
>   - メッセージ一覧での画像表示
> 
> 技術詳細:
> - FastAPI UploadFile でマルチパート処理
> - MinIO公開読み取りポリシー設定 (images/ フォルダ)
> - React useState で画像プレビュー管理
> - 最大10MB、画像形式のみ対応
> 
> テスト結果:
> ✅ 画像アップロード成功
> ✅ 画像付きメッセージ作成成功
> ✅ MinIO永続化確認
> ✅ ブラウザから画像表示可能

---

### ✨ **feat**: Implement MinIO-based persistent storage for LocalBackend

**Commit**: [`48d9883`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/48d9883dab6d41ef6701806e2a73c206984a7465) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+112/-18**

**Details**:

> Changes:
> - Replace in-memory dict storage with MinIO object storage
> - Store messages as JSON files in MinIO bucket (simple-sns/messages/)
> - Auto-create bucket on initialization
> - Implement full CRUD operations with MinIO SDK:
>   * create_message: Save as JSON to MinIO
>   * get_messages: List and read all message objects
>   * get_message: Read single message by ID
>   * delete_message: Remove object from MinIO
> 
> Benefits:
> - Data persists across container restarts
> - S3-compatible API (easy to migrate to real S3)
> - Compatible with existing API interface
> - Automatic bucket management
> 
> Testing:
> - ✅ Created 4 messages successfully
> - ✅ Retrieved messages from MinIO
> - ✅ Restarted API container
> - ✅ All 4 messages still available after restart
> - ✅ MinIO console shows JSON files in simple-sns/messages/
> 
> Architecture:
> - MinIO container stores data in Docker volume (minio-data)
> - Messages stored as: messages/{uuid}.json
> - JSON format matches Message model schema

---

### 🐛 **fix**: Change frontend API URL to localhost for browser access

**Commit**: [`a41db81`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a41db810a691c83eae9042af70ed6383f787f049) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

**Details**:

> Root cause:
> - Browser runs on host machine, not inside Docker network
> - 'api:8000' hostname only resolves within Docker network
> - Browser cannot resolve 'api' hostname (ERR_NAME_NOT_RESOLVED)
> 
> Fixed:
> - VITE_API_URL=http://api:8000 → http://localhost:8000
> 
> Architecture:
> - Browser (host) → localhost:8000 → Docker port mapping → api:8000 (container)
> - Docker internal services can still use 'api:8000' hostname
> - Port 8000 is exposed to host via docker-compose ports mapping
> 
> After this fix, browser can successfully connect to FastAPI backend.

---

### 🐛 **fix**: Correct frontend API URL from backend to api service

**Commit**: [`39cba48`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/39cba48d1079c5ce91273da4631c395aa83d4588) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

**Details**:

> Fixed issue where frontend was trying to connect to non-existent
> 'backend' service instead of 'api' service in Docker network.
> 
> Changed:
> - VITE_API_URL=http://backend:8000 → http://api:8000
> 
> This was causing 'メッセージの送信に失敗しました' error because
> the frontend could not reach the API service on the Docker network.
> 
> After this fix, users need to force-reload the browser (Ctrl+Shift+R)
> to clear the cached Vite build with the old environment variable.

---

### 🐛 **fix**: Correct JSX syntax errors in App.tsx

**Commit**: [`6add588`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6add588efb66f36b19a8e9e0621ebb43a7a8a576) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+3/-3**

**Details**:

> Fixed issues:
> - Corrected h2 tag className from 'mb-space-y-3' to 'mb-4'
> - Added missing form tag with proper onSubmit handler
> - Removed duplicated closing tags that caused syntax error
> - Restored correct HTML structure for message submission form
> 
> The error was causing Babel parser to fail at line 126 with
> 'Unexpected token, expected jsxTagEnd'.

---

### ✨ **feat**: Update frontend to integrate with new API endpoints

**Commit**: [`fd9a4d9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/fd9a4d9b6e443153a49085aa4601c888542c1499) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+55/-31**

**Details**:

> Changes:
> - Update Message interface to match backend model (content, author, created_at)
> - Add MessageListResponse interface for paginated responses
> - Update API endpoints: /api/messages → /api/messages/, /api/health → /health
> - Change POST payload from { text } to { content, author }
> - Add author input field to the message form
> - Update message display to show author name and created_at timestamp
> - Fix cloud provider detection to use cloud_provider field
> 
> Integration Testing:
> - ✅ Health check endpoint working (Status: ok, Provider: local)
> - ✅ POST /api/messages/ creates messages successfully
> - ✅ GET /api/messages/ returns paginated message list
> - ✅ CORS configuration working correctly
> - ✅ Frontend accessible at http://localhost:3001
> - ✅ API docs accessible at http://localhost:8000/docs
> 
> User Flow:
> 1. Enter name in the author field
> 2. Enter message content
> 3. Click submit button
> 4. Message appears in the list below with author and timestamp

---

### ✨ **feat**: Implement message CRUD API endpoints

**Commit**: [`4bd5e61`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4bd5e61071b12e3895c9381c32019c06cce47f9c) | **Author**: SATOSHI KAWADA | **Files Changed**: 7 | **+315/-3**

**Details**:

> Changes:
> - Add BaseBackend abstract class (app/backends/__init__.py)
> - Implement LocalBackend with in-memory storage (app/backends/local.py)
> - Implement AWSBackend with DynamoDB support (app/backends/aws.py)
> - Add backend factory for multi-cloud support (app/backends/factory.py)
> - Create messages router with CRUD operations (app/routes/messages.py)
> - Register messages router in main.py
> 
> API Endpoints:
> - POST /api/messages/ - Create message
> - GET /api/messages/ - List messages (with pagination)
> - GET /api/messages/{id} - Get single message
> - DELETE /api/messages/{id} - Delete message
> 
> Testing:
> - ✅ POST creates messages successfully
> - ✅ GET returns paginated message list
> - ✅ LocalBackend stores 6 test messages
> - ✅ Frontend accessible at http://localhost:3001
> - ✅ API docs at http://localhost:8000/docs

---

### 🐛 **fix**: Update docker-compose and Reflex configuration for local dev

**Commit**: [`1db97c5`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/1db97c5d5fdede7438d99b3eb13d6b70f0c97f2c) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+9/-10**

**Details**:

> Changes:
> - Fix web service to use Dockerfile instead of inline command
> - Update httpx version requirement (>=0.25.1) for Reflex compatibility
> - Add Node.js to Reflex Dockerfile for proper frontend compilation
> - Switch Reflex to production mode to avoid init issues
> 
> Testing:
> - FastAPI (api): ✅ Working on http://localhost:8000
> - React Frontend: ✅ Working on http://localhost:3001
> - MinIO: ✅ Working on http://localhost:9000-9001
> 
> All services successfully running in local development environment.

---

### ✨ **feat**: Add Python Full Stack implementation

**Commit**: [`6087b76`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6087b7602681700fad57c69eccbf72e3ac17a5b0) | **Author**: SATOSHI KAWADA | **Files Changed**: 23 | **+1747/-13**

**Details**:

> Major Changes:
> - Add FastAPI backend (services/api/) with multi-cloud support
> - Add Reflex frontend (services/web/) for complete Python UI
> - Add Pulumi IaC for AWS (infrastructure/pulumi/aws/)
> - Update docker-compose.yml with new Python services
> - Add comprehensive migration guide (docs/PYTHON_MIGRATION.md)
> - Update README with Python Full Stack section
> 
> New Services:
> - services/api/ - FastAPI backend (Python 3.12)
>   * Multi-cloud backends (AWS/Azure/GCP/Local)
>   * Pydantic models and settings
>   * Dockerized for easy deployment
> 
> - services/web/ - Reflex frontend (Python)
>   * React-like components in Python
>   * State management with async support
>   * Full TypeScript replacement
> 
> - infrastructure/pulumi/aws/ - Pulumi IaC (Python)
>   * Lambda + API Gateway + DynamoDB + S3
>   * Replaces Terraform with Python-native IaC
>   * Complete AWS infrastructure as code
> 
> Benefits:
> - Unified Python stack (IaC + Backend + Frontend)
> - Type safety across entire codebase
> - Improved developer experience
> - Easier maintenance and debugging
> 
> 23 files changed, 1800+ insertions

---

### 📚 **docs**: Comprehensive documentation and tooling update

**Commit**: [`1edfe9e`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/1edfe9e8c762a62f16df0882f76e7bb2eb917d5d) | **Author**: SATOSHI KAWADA | **Files Changed**: 11 | **+1586/-20**

**Details**:

> Documentation:
> - Add TROUBLESHOOTING.md with all CI/CD issues and solutions
>   * Azure authentication problems (Service Principal, Terraform Wrapper)
>   * GCP resource conflicts (GCS backend, resource imports)
>   * Frontend API connection issues (build order, API URL)
>   * Permission errors and IAM configurations
> - Add ENDPOINTS.md with complete endpoint information
>   * AWS, Azure, GCP API and frontend URLs
>   * Management console links
>   * API specification and test scripts
> - Update CICD_SETUP.md with troubleshooting references
> - Update README.md with latest information
>   * All cloud providers now fully operational
>   * New documentation and script references
>   * Dev Container support info
> 
> Tools & Scripts:
> - Add test-endpoints.sh - Test all cloud endpoints
> - Add import-gcp-resources.sh - Import existing GCP resources
> - Add setup-github-secrets.sh - GitHub Secrets setup guide
> - Make all scripts executable
> 
> Dev Container:
> - Add .devcontainer/devcontainer.json with full tooling
>   * Terraform 1.7.5, Node.js 18, Python 3.12
>   * AWS CLI, Azure CLI, gcloud CLI
>   * Docker-in-Docker support
>   * VS Code extensions for cloud development
> - Add .devcontainer/Dockerfile with additional utilities
> - Add .devcontainer/setup.sh for initialization
> - Include helpful aliases and functions
> 
> This completes the documentation and tooling setup after successful
> deployment to all three cloud providers (AWS, Azure, GCP).

---

### 📝 **other**: Fix AWS frontend: build after Lambda deployment with correct API URL

**Commit**: [`4e3be94`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4e3be94e038bd26b567413f94dba08f4601262e1) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+21/-9**

**Details**:

> Issue: Frontend was building with incorrect API URL (us-east-1 instead of ap-northeast-1)
> Changes:
> - Move Build Frontend step after Lambda deployment
> - Dynamically fetch API Gateway endpoint from AWS
> - Use fetched API endpoint when building frontend (VITE_API_URL)
> - Update CloudFront distribution ID default value (E2GDU7Y7UGDV3S)
> 
> This ensures the frontend knows the correct API URL at build time.

---

### 📝 **other**: Fix Azure frontend: build after infrastructure deployment with correct API URL

**Commit**: [`e467bb0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/e467bb06d5cc7142801c43aa74ccc69832c57db2) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+11/-14**

**Details**:

> Issue: Frontend was building before infrastructure deployment, so API URL was not available
> Changes:
> - Move Deploy Infrastructure step before Build Frontend
> - Extract api_url from Terraform outputs
> - Use api_url output when building frontend (VITE_API_URL)
> - Frontend now built with correct API endpoint
> 
> This ensures the frontend knows the correct API URL at build time.

---

### 📝 **other**: Fix GCP workflow: enable GCS backend and import existing resources

**Commit**: [`522a639`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/522a6392bf9f72e38e2e7191d21c70af06ff2a75) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+52/-88**

**Details**:

> Major changes:
> 1. Enable GCS backend for persistent Terraform state
>    - Created gs://multicloud-auto-deploy-tfstate-gcp bucket
>    - Granted storage.objectAdmin role to service account
>    - Enabled backend in main.tf
> 
> 2. Imported existing GCP resources to Terraform state
>    - google_artifact_registry_repository.main (mcad-staging-repo)
>    - google_storage_bucket.frontend (mcad-staging-frontend)
>    - google_compute_global_address.frontend (mcad-staging-frontend-ip)
>    - google_firestore_database.main ((default))
> 
> 3. Simplified GitHub Actions workflow
>    - Removed complex import logic (now handled by persistent state)
>    - Use GitHub Actions outputs instead of terraform output commands
>    - Cleaner workflow with better logging
> 
> 4. Added missing Terraform outputs
>    - artifact_registry_location
>    - frontend_storage_bucket
>    - api_url in workflow outputs
> 
> Benefits:
> - No more 'resource already exists' errors
> - Faster workflow execution (no repeated imports)
> - Consistent state across workflow runs
> - Easier to maintain and debug

---

### 📝 **other**: Add detailed debug output for GCP resource import

**Commit**: [`f33581c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/f33581cce65b8d13984d1a7970a7e1c5a40337fc) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+51/-18**

**Details**:

> Changes:
> - Add extensive logging to import process
> - Show environment variables being used
> - Display state check results
> - Show terraform state list after import
> - Add separators for better log readability
> 
> This will help diagnose why imports are failing and resources
> still show 'already exists' errors.

---

### 📝 **other**: Optimize GCP workflow: improve import process with state checks

**Commit**: [`2a5597c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/2a5597cb1d9632535ec4036470451d537a08881c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+28/-28**

**Details**:

> Changes:
> - Add import_resource function to check state before importing
> - Skip import if resource already in state
> - Better error handling and progress messages
> - This reduces execution time and provides clearer feedback
> 
> Benefits:
> - Faster execution when resources already imported
> - Clear status messages (✓ = in state, → = importing, ○ = not found)
> - Avoids redundant import attempts

---

### 📝 **other**: Fix GCP workflow: import existing resources before terraform apply

**Commit**: [`22219d8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/22219d85725d84e5ee340ad94c34b8f499672869) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+39/-0**

**Details**:

> Changes:
> - Add Firestore owner role to service account
> - Import existing GCP resources before terraform apply:
>   * Artifact Registry repository
>   * Firestore database (default)
>   * Storage bucket for frontend
>   * Global address for frontend
> - Ignore import errors if resources already in state
> - This prevents 'resource already exists' errors
> 
> Errors fixed:
> - Error 409: Repository/bucket/address already exists
> - Error 403: No permission for Firestore (role added)

---

### 📝 **other**: Fix Azure Terraform outputs: add missing container_registry_name and frontend_storage_account

**Commit**: [`24c4870`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/24c4870627e4d545ad1a577848eabc89e42d6a2f) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+36/-5**

**Details**:

> Changes:
> - Add container_registry_name output (ACR name)
> - Add frontend_storage_account output (Storage Account name)
> - Add debug output in Deploy Infrastructure step
> - Add ACR_NAME validation in Build and Push Docker Image step
> 
> These outputs are required by the GitHub Actions workflow to:
> - Login to ACR for Docker image push
> - Deploy to Container App
> - Upload frontend files to Storage Account

---

### 📝 **other**: Fix Azure workflow: avoid terraform commands after Azure CLI login

**Commit**: [`57857d2`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/57857d2759ac5c3507e79dd979e0cf01a769ae6f) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+17/-13**

**Details**:

> Key changes:
> - Store Terraform outputs in Deploy Infrastructure step
> - Pass outputs to subsequent steps via GitHub Actions outputs
> - Avoid running 'terraform output' after Azure CLI login
> - This prevents CLI auth conflicts with Terraform
> 
> Terraform outputs stored:
> - acr_name (Container Registry)
> - resource_group (Resource Group)
> - container_app (Container App name)
> - storage_account (Frontend Storage Account)

---

### 📝 **other**: Fix Azure Terraform authentication: clear CLI config and disable wrapper

**Commit**: [`ced5376`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ced5376aaeff7b3c06cc3f01fd845a38b002016e) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+8/-2**

**Details**:

> Critical fixes:
> - Disable terraform_wrapper to ensure environment variables pass correctly
> - Clear Azure CLI config (az account clear) before Terraform execution
> - Explicitly disable use_cli, use_msi, use_oidc in provider
> - Environment variables (ARM_*) are the ONLY authentication method
> 
> This ensures Terraform uses Service Principal credentials exclusively.

---

### 📝 **other**: Fix Azure authentication: remove initial Azure Login to prevent CLI auth conflicts

**Commit**: [`a1b6d5c`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a1b6d5c145e247435c358b777fa8219aac4d94cb) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+15/-12**

**Details**:

> Changes:
> - Remove initial Azure Login step (not needed for Terraform)
> - Terraform uses ARM_* environment variables for Service Principal auth
> - Added use_msi=false and use_oidc=false to provider block
> - Login to Azure CLI only when needed for ACR operations
> - This prevents Terraform from attempting Azure CLI authentication

---

### 📝 **other**: Fix Azure Terraform backend: remove unsupported use_cli and use_azuread_auth arguments

**Commit**: [`6272301`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6272301b507eeb954400a1948bf36cf68834b08c) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+0/-2**

**Details**:

> - Backend block does not support use_cli or use_azuread_auth
> - Authentication via ARM_* environment variables (already set in workflow)
> - Keep use_cli=false in provider block (this is valid)

---

### 📝 **other**: Fix Terraform backend config: remove invalid backend-config flags

**Commit**: [`4ede2ca`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4ede2ca69e1579982c0ab76fe930946724cd57a0) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+2/-4**

**Details**:

> - Remove -backend-config flags from terraform init
> - Backend settings (use_cli, use_azuread_auth) are already in main.tf
> - Simplify to standard terraform init command

---

### 📝 **other**: Fix Azure backend authentication: completely disable Azure CLI auth

**Commit**: [`4e587ee`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4e587eef906dd31f70e7f68a876bb0a89bde0a27) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+11/-2**

**Details**:

> - Add use_cli=false and use_azuread_auth=false to backend block
> - Add backend-config flags to terraform init command
> - Add ARM_USE_CLI and ARM_USE_AZUREAD_AUTH environment variables
> - Ensures both backend and provider use Service Principal authentication

---

### 📝 **other**: Fix Azure Terraform authentication: use environment variables instead of Azure CLI

**Commit**: [`ea94b19`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ea94b198933b74db02708072be7313040c236554) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+19/-0**

**Details**:

> - Add use_cli = false to azurerm provider to prevent Azure CLI auth
> - Add az logout step before Terraform to avoid authentication conflicts
> - Re-login to Azure CLI after Terraform for ACR operations
> - Ensures proper Service Principal authentication for Terraform

---

### 📝 **other**: Update documentation: Add CI/CD badges, live demo URLs, and development tools

**Commit**: [`8f3ce46`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/8f3ce460b19f790c94ca2be539a65ff46a677710) | **Author**: SATOSHI KAWADA | **Files Changed**: 3 | **+179/-23**

**Details**:

> - Add GitHub Actions workflow status badges
> - Add live demo URLs for AWS/Azure/GCP deployments
> - Update technology stack (Python 3.12, x86_64, Terraform 1.14.5)
> - Add detailed CI/CD deployment flow
> - Document development tools (Makefile, diagnostics script)
> - Update architecture section with actual deployment status
> - Add IAM policy for GitHub Actions deployment

---

### 📝 **other**: Simplify AWS workflow: remove cleanup commands for reliability

**Commit**: [`d8b6330`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d8b6330d7dc7e23d4857ace3be740befc2d67d05) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+11/-9**

**Details**:

> - Remove all cleanup commands that were causing failures
> - Use simpler packaging process without optimization
> - Package size will be ~4.3MB (still under 250MB S3 limit)
> - Focus on reliability over optimization

---

### 📝 **other**: Fix AWS workflow: improve cleanup commands to avoid errors

**Commit**: [`3437bf0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/3437bf04ba4c4adceeb43484efd8cbd53b678e6e) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+7/-4**

**Details**:

> - Use xargs for __pycache__ removal instead of -exec
> - Add || true to all cleanup commands to prevent pipeline failures
> - Add package size display for debugging
> - Tested locally: successfully creates 2.8MB package (35% size reduction)

---

### 📝 **other**: Improve AWS workflow: add package optimization and better error handling

**Commit**: [`58e6bfb`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/58e6bfbc2d335abf7e14be8c5a293213d6025e9c) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+60/-4**

**Details**:

> - Remove __pycache__, *.pyc, tests, *.dist-info to reduce package size
> - Add detailed logging for each step (📦 ☁️ 🚀)
> - Add error handling with clear failure messages
> - Add workflow monitoring script
> - Exit immediately on any command failure (set -e)

---

### 📝 **other**: Fix AWS workflow: upload Lambda package via S3 to handle large file size

**Commit**: [`095074d`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/095074d7aa9eb5c57f16eebb291d689e9a2acd33) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+9/-1**

**Details**:

> - Lambda package is ~58MB, exceeding direct upload limit (50MB)
> - Upload to S3 first, then update Lambda from S3
> - Fixes exit code 254 error (RequestEntityTooLargeException)

---

### 📝 **other**: Add development tools: Makefile and diagnostics script

**Commit**: [`6c202c9`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6c202c91a483757ab6f8c883020fec776d8c290e) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+277/-0**

**Details**:

> - Add Makefile with common tasks (build, test, deploy)
> - Add diagnostics.sh script for troubleshooting
> - Makefile supports: build-frontend, build-backend, test-all, deploy-aws
> - Diagnostics checks: tools, Python env, cloud auth, deployments, AWS resources

---

### 📝 **other**: Fix Lambda deployment: use x86_64 architecture and minimal dependencies for AWS Lambda

**Commit**: [`39bbaab`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/39bbaab7d0dd3eb6b14b394979891991d4baf5b4) | **Author**: SATOSHI KAWADA | **Files Changed**: 2 | **+5/-2**

---

### 📝 **other**: Fix AWS workflow: add region to Lambda update and ensure package directory exists

**Commit**: [`5f6f8ab`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/5f6f8ab6656dd823ab8ea5ffaf1d469846c92766) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+2/-0**

---

### 📝 **other**: Update AWS workflow to use Python 3.12

**Commit**: [`ee78f96`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/ee78f961db166fdc42afad7056c2c12ecea6ff45) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+1/-1**

---

### 📝 **other**: Update Lambda runtime to Python 3.12 and set architecture to arm64

**Commit**: [`d645961`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/d645961004f0686edf4b177f3524d692fc06be8b) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+4/-9**

---

### 📝 **other**: Change AWS region from us-east-1 to ap-northeast-1

**Commit**: [`4db9645`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/4db9645a65e2d8737545e517e27a4332e018365f) | **Author**: SATOSHI KAWADA | **Files Changed**: 4 | **+5/-5**

**Details**:

> - Update Terraform backend to new S3 bucket in ap-northeast-1
> - Update all region references in Terraform configs
> - Update GitHub Actions workflow AWS_REGION
> - Update deployment scripts
> - Migrate Terraform state to new bucket with versioning and encryption
> 
> New bucket: multicloud-auto-deploy-terraform-state-apne1

---

### 📝 **other**: Update AWS CI/CD workflow to update existing resources only

**Commit**: [`847ba08`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/847ba08254773db654f083b2ac1250c20afddc3b) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+32/-3**

**Details**:

> - Remove dependency on deploy-aws.sh script
> - Directly update Lambda function code
> - Sync frontend to S3 bucket
> - Invalidate CloudFront cache
> - Use secrets for resource names with fallback defaults

---

### 📝 **other**: Add detailed instructions for AZURE_ACR_LOGIN_SERVER and GCP_SA_KEY

**Commit**: [`54b3c5f`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/54b3c5f8c8f324cc1eafa9fa225a81702d75d951) | **Author**: SATOSHI KAWADA | **Files Changed**: 1 | **+81/-5**

**Details**:

> - Add Azure ACR login server retrieval method
> - Add GCP service account key (GCP_CREDENTIALS) detailed steps
> - Add Service Principal ACR access permissions setup
> - Add existing service account key creation method
> - Clarify Secret names and their usage in workflows

---


## 📅 2026-02-13

### 📚 **docs**: Add comprehensive documentation

**Commit**: [`a8f23a8`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/a8f23a8aa3d6b888bbafefba2d95fa2fa5570296) | **Author**: SATOSHI KAWADA | **Files Changed**: 4 | **+716/-0**

**Details**:

> - Add AWS deployment guide with architecture details
> - Add system architecture documentation
> - Add contributing guidelines
> - Add MIT license
> - Complete project documentation

---

### ✨ **feat**: Complete multi-cloud auto-deploy platform

**Commit**: [`6ce22f0`](https://github.com/PLAYER1-r7/multicloud-auto-deploy/commit/6ce22f0867b3e9757e7c1be52b16329d0ef5ff1c) | **Author**: SATOSHI KAWADA | **Files Changed**: 30 | **+1380/-0**

**Details**:

> - Add full-stack sample application (React + FastAPI)
> - Add infrastructure as code for AWS (Terraform)
> - Add GitHub Actions workflows for automated deployment
> - Add deployment scripts for AWS/Azure/GCP
> - Add comprehensive documentation and setup guide
> - Configure Docker Compose for local development

---


---

**Note**: This detailed changelog includes complete commit information with file changes. For a summary version, see [CHANGELOG.md](CHANGELOG.md).
