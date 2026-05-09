# ── AMI (Amazon Linux 2023 최신) ─────────────────────────────
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# ── IAM 역할 (SSM read only) ───────────────────────────────
resource "aws_iam_role" "backtester" {
  name = "${var.project_name}-backtester-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "backtester_ssm_core" {
  role       = aws_iam_role.backtester.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
}

resource "aws_iam_role_policy" "backtester_ssm_params" {
  name = "${var.project_name}-backtester-ssm-params"
  role = aws_iam_role.backtester.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ssm:GetParametersByPath",
          "ssm:GetParameter",
          "ssm:GetParameters"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/${var.project_name}/*"
      },
      {
        # 2026-05-09: backtester EC2 가 자기 kis_devlp.yaml 을 SSM 에 영속화하기 위함.
        # 자격증명 회전 시 EC2 안에서 put-parameter 실행 → CloudTrail 에 명령만 남고
        # 자격증명 본문은 EC2 외부로 유출되지 않음.
        # 대상 파라미터를 1개로 좁혀 최소 권한 유지.
        Effect = "Allow"
        Action = [
          "ssm:PutParameter"
        ]
        Resource = "arn:aws:ssm:*:*:parameter/${var.project_name}/prod/kis_devlp_yaml"
      }
    ]
  })
}

resource "aws_iam_instance_profile" "backtester" {
  name = "${var.project_name}-backtester-profile"
  role = aws_iam_role.backtester.name
}

# ── EC2 인스턴스 ─────────────────────────────────────────────
resource "aws_instance" "backtester" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.instance_type
  subnet_id              = var.subnet_id
  vpc_security_group_ids = [var.backtester_sg_id]
  key_name               = var.key_pair_name
  iam_instance_profile   = aws_iam_instance_profile.backtester.name

  user_data = file("${path.module}/user_data.sh")

  root_block_device {
    volume_size = 50
    volume_type = "gp3"
  }

  tags = { Name = "${var.project_name}-backtester" }
}

# ── Elastic IP ──────────────────────────────────────────────
resource "aws_eip" "backtester" {
  instance = aws_instance.backtester.id
  domain   = "vpc"

  tags = { Name = "${var.project_name}-backtester-eip" }
}

# ── Outputs ─────────────────────────────────────────────────
output "public_ip" {
  value = aws_eip.backtester.public_ip
}

output "private_ip" {
  value = aws_instance.backtester.private_ip
}

output "instance_id" {
  value = aws_instance.backtester.id
}

# ── Variables ───────────────────────────────────────────────
variable "project_name" {
  type = string
}

variable "subnet_id" {
  type = string
}

variable "backtester_sg_id" {
  type = string
}

variable "key_pair_name" {
  type = string
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}
