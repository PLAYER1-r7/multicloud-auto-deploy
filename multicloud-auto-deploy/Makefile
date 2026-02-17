.PHONY: help install test-aws test-azure test-gcp test-all deploy-aws deploy-azure deploy-gcp build-frontend build-backend clean

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
