# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-userpool"

  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  deletion_protection = "ACTIVE"

  # MFA Configuration
  mfa_configuration = "ON"

  software_token_mfa_configuration {
    enabled = true
  }

  user_pool_add_ons {
    advanced_security_mode = "ENFORCED"
    advanced_security_additional_flows {
      custom_auth_mode = "ENFORCED"
    }
  }

  # Account Recovery Settings
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  tags = local.tags
}

# Cognito User Pool Risk Configuration
resource "aws_cognito_risk_configuration" "main" {
  user_pool_id = aws_cognito_user_pool.main.id

  # Compromised Credentials Check
  compromised_credentials_risk_configuration {
    event_filter = ["SIGN_IN", "PASSWORD_CHANGE", "SIGN_UP"]

    actions {
      event_action = "BLOCK"
    }
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email", "profile"]
  supported_identity_providers         = ["COGNITO"]

  callback_urls = [var.web_callback_url]
  logout_urls   = [var.web_logout_url]

  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH"
  ]
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.main.id
}
