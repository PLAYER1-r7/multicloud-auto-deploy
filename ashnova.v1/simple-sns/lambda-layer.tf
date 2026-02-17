# Lambda Layer for Node.js dependencies
# This layer contains all node_modules to reduce individual Lambda function size

# Create layer package with node_modules
resource "null_resource" "lambda_layer_build" {
  triggers = {
    # Rebuild layer when package.json or package-lock.json changes
    package_json      = filemd5("${path.module}/package.json")
    package_lock_json = fileexists("${path.module}/package-lock.json") ? filemd5("${path.module}/package-lock.json") : ""
  }

  provisioner "local-exec" {
    command = <<EOT
set -e
echo "Building Lambda Layer..."

# Create layer directory structure
rm -rf ${path.module}/.terraform/layer
mkdir -p ${path.module}/.terraform/layer/nodejs

# Copy package files
cp ${path.module}/package.json ${path.module}/.terraform/layer/nodejs/
if [ -f ${path.module}/package-lock.json ]; then
  cp ${path.module}/package-lock.json ${path.module}/.terraform/layer/nodejs/
fi

# Install production dependencies only
cd ${path.module}/.terraform/layer/nodejs
npm ci --omit=dev --no-audit --no-fund

# Remove unnecessary files to reduce size
find . -name "*.md" -type f -delete
find . -name "*.ts" -type f -delete
find . -name "*.map" -type f -delete
find . -name "LICENSE*" -type f -delete
find . -name "CHANGELOG*" -type f -delete
find . -name "README*" -type f -delete
find . -name "*.d.ts" -type f -delete
find . -name ".gitignore" -type f -delete
find . -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "__tests__" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "docs" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "example" -exec rm -rf {} + 2>/dev/null || true
find . -type d -name "examples" -exec rm -rf {} + 2>/dev/null || true

echo "Lambda Layer build completed"
EOT
  }
}

# Archive the layer
data "archive_file" "lambda_layer" {
  type        = "zip"
  source_dir  = "${path.module}/.terraform/layer"
  output_path = "${path.module}/.terraform/lambda-layer.zip"

  depends_on = [null_resource.lambda_layer_build]
}

# Lambda Layer resource
resource "aws_lambda_layer_version" "nodejs_dependencies" {
  layer_name          = "${var.project_name}-nodejs-dependencies"
  description         = "Node.js dependencies for ${var.project_name} Lambda functions"
  filename            = data.archive_file.lambda_layer.output_path
  source_code_hash    = data.archive_file.lambda_layer.output_base64sha256
  compatible_runtimes = ["nodejs22.x"]

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [data.archive_file.lambda_layer]
}

# Output layer ARN for reference
output "lambda_layer_arn" {
  description = "ARN of the Lambda Layer containing Node.js dependencies"
  value       = aws_lambda_layer_version.nodejs_dependencies.arn
}

output "lambda_layer_version" {
  description = "Version of the Lambda Layer"
  value       = aws_lambda_layer_version.nodejs_dependencies.version
}
