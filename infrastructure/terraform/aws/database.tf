# DynamoDB（メッセージストレージ用）
resource "aws_dynamodb_table" "messages" {
  name           = "${var.project_name}-${var.environment}-messages"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "timestamp-index"
    hash_key        = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-messages"
  }
}
