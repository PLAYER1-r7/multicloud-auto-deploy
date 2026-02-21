.PHONY: help install test-aws test-azure test-gcp test-all deploy-aws deploy-azure deploy-gcp build-frontend build-backend clean \
        hooks-install version version-major version-minor version-patch version-azure-afd-resolved

# Default target
help:
	@echo "Multi-Cloud Auto Deploy - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install        - Install all dependencies (frontend + backend)"
	@echo "  build-frontend - Build frontend application"
	@echo "  build-backend  - Package backend for Lambda (x86_64)"
	@echo "  test-aws       - Test AWS deployment"
	@echo "  test-azure     - Test Azure deployment"
	@echo "  test-gcp       - Test GCP deployment"
	@echo "  test-all       - Test all cloud deployments"
	@echo "  deploy-aws     - Deploy to AWS via CLI"
	@echo "  terraform-init - Initialize Terraform for AWS"
	@echo "  terraform-plan - Plan Terraform changes for AWS"
	@echo "  terraform-apply - Apply Terraform changes for AWS"
	@echo "  clean          - Clean build artifacts"
	@echo ""
	@echo "Version management:"
	@echo "  hooks-install              - git hooks を有効化 (初回セットアップ時に実行)"
	@echo "  version                    - 現在のバージョン一覧を表示"
	@echo "  version-major COMPONENT=<name|all>  - メジャー(X)を手動インクリメント"
	@echo "  version-minor COMPONENT=<name|all>  - マイナー(Y)を手動インクリメント"
	@echo "  version-patch COMPONENT=<name|all>  - パッチ(Z)を手動インクリメント"
	@echo "  version-azure-afd-resolved - Azure AFD 解消後: 0.9.x → 1.0.0"
	@echo ""
	@echo "Components: aws-static-site  azure-static-site  gcp-static-site  simple-sns  all"

# Install dependencies
install:
	@echo "📦 Installing frontend dependencies..."
	cd services/frontend && npm install
	@echo "📦 Installing backend dependencies..."
	cd services/backend && python3.12 -m venv .venv && \
		.venv/bin/pip install --upgrade pip && \
		.venv/bin/pip install -r requirements.txt
	@echo "✅ Dependencies installed"

# Build frontend
build-frontend:
	@echo "🏗️  Building frontend..."
	cd services/frontend && \
		VITE_API_URL=https://52z731x570.execute-api.ap-northeast-1.amazonaws.com npm run build
	@echo "✅ Frontend built in services/frontend/dist/"

# Build backend (x86_64 for Lambda)
build-backend:
	@echo "🏗️  Building backend for AWS Lambda (x86_64)..."
	cd services/backend && \
		rm -rf package lambda.zip && \
		mkdir -p package && \
		pip install --platform manylinux2014_x86_64 --only-binary=:all: \
			--target package --python-version 3.12 --implementation cp \
			fastapi==0.109.0 pydantic==2.5.3 python-dotenv==1.0.0 mangum==0.17.0 && \
		cp -r src/* package/ && \
		cd package && zip -r ../lambda.zip . -q
	@echo "✅ Backend packaged in services/backend/lambda.zip"

# Test deployments
test-aws:
	@echo "☁️  Testing AWS deployment (ap-northeast-1)..."
	@curl -s https://52z731x570.execute-api.ap-northeast-1.amazonaws.com/ | jq .

test-azure:
	@echo "☁️  Testing Azure deployment (japaneast)..."
	@curl -s https://mcad-staging-api--0000003.livelycoast-fa9d3350.japaneast.azurecontainerapps.io/ | jq .

test-gcp:
	@echo "☁️  Testing GCP deployment (asia-northeast1)..."
	@curl -s https://mcad-staging-api-son5b3ml7a-an.a.run.app/ | jq .

test-all: test-aws test-azure test-gcp
	@echo "✅ All deployments tested"

# Deploy to AWS
deploy-aws: build-backend
	@echo "🚀 Deploying to AWS..."
	@cd services/backend && \
		aws lambda update-function-code \
			--function-name multicloud-auto-deploy-staging-api \
			--region ap-northeast-1 \
			--zip-file fileb://lambda.zip \
			--query 'FunctionName' --output text
	@echo "✅ AWS Lambda updated"

deploy-frontend-aws: build-frontend
	@echo "🚀 Deploying frontend to AWS S3..."
	@aws s3 sync services/frontend/dist/ s3://multicloud-auto-deploy-staging-frontend/ --delete
	@aws cloudfront create-invalidation \
		--distribution-id E2GDU7Y7UGDV3S \
		--paths "/*" \
		--query 'Invalidation.Id' --output text
	@echo "✅ Frontend deployed to S3 and CloudFront invalidated"

# Terraform commands
terraform-init:
	@echo "🔧 Initializing Terraform..."
	cd infrastructure/terraform/aws && terraform init

terraform-plan:
	@echo "📋 Planning Terraform changes..."
	cd infrastructure/terraform/aws && \
		terraform plan -var="environment=staging" -var="project_name=multicloud-auto-deploy"

terraform-apply:
	@echo "🚀 Applying Terraform changes..."
	cd infrastructure/terraform/aws && \
		terraform apply -var="environment=staging" -var="project_name=multicloud-auto-deploy" -auto-approve

# Clean
clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf services/frontend/dist
	rm -rf services/frontend/node_modules
	rm -rf services/backend/package
	rm -rf services/backend/lambda.zip
	rm -rf services/backend/.venv
	@echo "✅ Clean complete"

# ============================================================
# バージョン管理
# ============================================================

# git hooks を有効化 (初回セットアップ時に実行)
hooks-install:
	@echo "🔧 git hooks を .githooks に設定..."
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	chmod +x scripts/bump-version.sh
	@echo "✅ git hooks 有効化完了"
	@echo "   コミット時に自動でパッチ(Z)をインクリメントします"
	@echo "   プッシュ時は GitHub Actions がマイナー(Y)をインクリメントします"

# 現在のバージョン一覧
version:
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh show

# メジャー(X)を手動インクリメント
# 使用例: make version-major COMPONENT=all
#          make version-major COMPONENT=aws-static-site
COMPONENT ?= all
version-major:
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh major $(COMPONENT)
	@echo "📝 次のコマンドでコミットしてください:"
	@echo "   git add versions.json && git commit -m 'chore: bump major version [skip-version-bump]'"

version-minor:
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh minor $(COMPONENT)
	@echo "📝 次のコマンドでコミットしてください:"
	@echo "   git add versions.json && git commit -m 'chore: bump minor version [skip-version-bump]'"

version-patch:
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh patch $(COMPONENT)
	@echo "📝 次のコマンドでコミットしてください:"
	@echo "   git add versions.json && git commit -m 'chore: bump patch version [skip-version-bump]'"

# Azure AFD 解消後に 0.9.x → 1.0.0 へ昇格
version-azure-afd-resolved:
	@chmod +x scripts/bump-version.sh
	@./scripts/bump-version.sh azure-afd-resolved
