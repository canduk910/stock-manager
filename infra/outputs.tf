output "ec2_public_ip" {
  description = "EC2 퍼블릭 IP (Elastic IP)"
  value       = module.compute.public_ip
}

output "rds_endpoint" {
  description = "RDS PostgreSQL 엔드포인트"
  value       = module.database.endpoint
}

output "ecr_repo_url" {
  description = "ECR 리포지토리 URL"
  value       = module.ecr.repo_url
}

output "ssh_command" {
  description = "EC2 SSH 접속 명령어"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ec2-user@${module.compute.public_ip}"
}

output "database_url" {
  description = "PostgreSQL DATABASE_URL (비밀번호 마스킹)"
  value       = "postgresql://${var.db_username}:****@${module.database.endpoint}:5432/${var.db_name}"
}
