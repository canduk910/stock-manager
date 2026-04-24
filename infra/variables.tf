variable "aws_region" {
  description = "AWS 리전"
  type        = string
  default     = "ap-northeast-2"
}

variable "project_name" {
  description = "프로젝트 이름 (리소스 태깅/네이밍)"
  type        = string
  default     = "stock-manager"
}

variable "my_ip" {
  description = "SSH 접속 허용 IP (CIDR, 예: 1.2.3.4/32)"
  type        = string
}

variable "key_pair_name" {
  description = "EC2 SSH 키 페어 이름 (AWS에 미리 생성 필요)"
  type        = string
}

variable "ec2_instance_type" {
  description = "EC2 인스턴스 타입"
  type        = string
  default     = "t3.micro"
}

variable "rds_instance_class" {
  description = "RDS 인스턴스 클래스"
  type        = string
  default     = "db.t3.micro"
}

variable "db_name" {
  description = "PostgreSQL 데이터베이스 이름"
  type        = string
  default     = "stockmanager"
}

variable "db_username" {
  description = "PostgreSQL 사용자명"
  type        = string
  default     = "stockadmin"
}

variable "db_password" {
  description = "PostgreSQL 비밀번호"
  type        = string
  sensitive   = true
}
