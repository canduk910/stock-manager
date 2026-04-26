# SSM Parameter Store: 환경변수를 SecureString으로 저장
# 초기값은 placeholder — terraform apply 후 AWS 콘솔 또는 CLI로 실제 값 설정
#
# 설정 예:
#   aws ssm put-parameter --name "/stock-manager/prod/KIS_APP_KEY" \
#     --value "실제키" --type SecureString --overwrite

locals {
  # SecureString (민감 정보)
  secure_params = {
    KIS_APP_KEY      = "CHANGE_ME"
    KIS_APP_SECRET   = "CHANGE_ME"
    KIS_ACNT_NO      = "CHANGE_ME"
    OPENDART_API_KEY = "CHANGE_ME"
    OPENAI_API_KEY   = "CHANGE_ME"
    KRX_ID           = "CHANGE_ME"
    KRX_PASSWORD     = "CHANGE_ME"
    FINNHUB_API_KEY  = "CHANGE_ME"
    KIS_HTS_ID       = "CHANGE_ME"
    JWT_SECRET_KEY   = "CHANGE_ME"
  }

  # String (비민감 설정)
  plain_params = {
    KIS_ACNT_PRDT_CD_STK = "01"
    KIS_ACNT_PRDT_CD_FNO = "NONE"
    KIS_BASE_URL          = "https://openapi.koreainvestment.com:9443"
    OPENAI_MODEL          = "gpt-5-mini"
    DATABASE_URL          = "postgresql://${var.db_username}:${var.db_password}@${var.db_endpoint}:5432/${var.db_name}"
    KIS_MCP_URL           = "CHANGE_ME"
    KIS_MCP_ENABLED       = "true"
  }
}

resource "aws_ssm_parameter" "secure" {
  for_each = local.secure_params

  name  = "/${var.project_name}/prod/${each.key}"
  type  = "SecureString"
  value = each.value

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Name = each.key }
}

resource "aws_ssm_parameter" "plain" {
  for_each = local.plain_params

  name  = "/${var.project_name}/prod/${each.key}"
  type  = "String"
  value = each.value

  lifecycle {
    ignore_changes = [value]
  }

  tags = { Name = each.key }
}

# ── Variables ───────────────────────────────────────────────
variable "project_name" {
  type = string
}

variable "db_endpoint" {
  type = string
}

variable "db_name" {
  type = string
}

variable "db_username" {
  type = string
}

variable "db_password" {
  type      = string
  sensitive = true
}
