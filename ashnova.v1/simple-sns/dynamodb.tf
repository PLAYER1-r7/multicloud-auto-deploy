# DynamoDB Table
resource "aws_dynamodb_table" "posts" {
  name           = "${var.project_name}-Posts"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "PK"
  range_key      = "SK"
  deletion_protection_enabled = true

  attribute {
    name = "PK"
    type = "S"
  }

  attribute {
    name = "SK"
    type = "S"
  }

  attribute {
    name = "postId"
    type = "S"
  }

  global_secondary_index {
    name            = "PostIdIndex"
    hash_key        = "postId"
    projection_type = "ALL"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = null # Uses AWS managed key
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = local.tags
}
