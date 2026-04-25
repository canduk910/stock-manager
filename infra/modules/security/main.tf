# ── EC2 보안그룹 ─────────────────────────────────────────────
resource "aws_security_group" "ec2" {
  name        = "${var.project_name}-ec2-sg"
  description = "EC2 inbound: HTTP/HTTPS/SSH"
  vpc_id      = var.vpc_id

  # HTTP
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP"
  }

  # HTTPS
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS"
  }

  # SSH (관리자 IP만)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip]
    description = "SSH from admin"
  }

  # 아웃바운드 전체 허용 (KIS, DART, yfinance 등 외부 API 호출)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = { Name = "${var.project_name}-ec2-sg" }
}

# ── RDS 보안그룹 ─────────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "RDS inbound: PostgreSQL from EC2 only"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
    description     = "PostgreSQL from EC2"
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}

# ── Backtester 보안그룹 ──────────────────────────────────────
resource "aws_security_group" "backtester" {
  name        = "${var.project_name}-backtester-sg"
  description = "Backtester inbound: SSH/Web UI/MCP"
  vpc_id      = var.vpc_id

  # SSH
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH"
  }

  # Next.js 프론트엔드
  ingress {
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Backtester frontend"
  }

  # FastAPI 백엔드
  ingress {
    from_port   = 8002
    to_port     = 8002
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Backtester backend"
  }

  # MCP 서버
  ingress {
    from_port   = 3846
    to_port     = 3846
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "MCP server"
  }

  # 아웃바운드 전체 허용 (Docker pull, KIS API 등)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = { Name = "${var.project_name}-backtester-sg" }
}

# ── Outputs ─────────────────────────────────────────────────
output "ec2_sg_id" {
  value = aws_security_group.ec2.id
}

output "rds_sg_id" {
  value = aws_security_group.rds.id
}

output "backtester_sg_id" {
  value = aws_security_group.backtester.id
}

# ── Variables ───────────────────────────────────────────────
variable "project_name" {
  type = string
}

variable "vpc_id" {
  type = string
}

variable "my_ip" {
  description = "SSH 접속 허용 IP (CIDR)"
  type        = string
}
