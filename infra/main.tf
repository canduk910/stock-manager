terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  # S3 backend (terraform apply 후 활성화 권장)
  # backend "s3" {
  #   bucket = "stock-manager-tfstate"
  #   key    = "prod/terraform.tfstate"
  #   region = "ap-northeast-2"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      ManagedBy   = "terraform"
      Environment = "prod"
    }
  }
}

# ── 네트워크 ─────────────────────────────────────────────────
module "network" {
  source       = "./modules/network"
  project_name = var.project_name
  aws_region   = var.aws_region
}

# ── 보안그룹 ─────────────────────────────────────────────────
module "security" {
  source       = "./modules/security"
  project_name = var.project_name
  vpc_id       = module.network.vpc_id
  my_ip        = var.my_ip
}

# ── ECR ──────────────────────────────────────────────────────
module "ecr" {
  source       = "./modules/ecr"
  project_name = var.project_name
}

# ── RDS PostgreSQL ───────────────────────────────────────────
module "database" {
  source              = "./modules/database"
  project_name        = var.project_name
  db_subnet_group     = module.network.db_subnet_group_name
  rds_sg_id           = module.security.rds_sg_id
  db_name             = var.db_name
  db_username         = var.db_username
  db_password         = var.db_password
  rds_instance_class  = var.rds_instance_class
}

# ── EC2 ──────────────────────────────────────────────────────
module "compute" {
  source             = "./modules/compute"
  project_name       = var.project_name
  subnet_id          = module.network.public_subnet_id
  ec2_sg_id          = module.security.ec2_sg_id
  ecr_repo_arn       = module.ecr.repo_arn
  key_pair_name      = var.key_pair_name
  ec2_instance_type  = var.ec2_instance_type
}

# ── SSM Parameter Store ─────────────────────────────────────
module "secrets" {
  source       = "./modules/secrets"
  project_name = var.project_name
  db_endpoint  = module.database.endpoint
  db_name      = var.db_name
  db_username  = var.db_username
  db_password  = var.db_password
}
