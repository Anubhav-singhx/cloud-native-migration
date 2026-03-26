# providers.tf
# Tells Terraform which cloud providers to use and what versions

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.24"
    }
  }

  # Store Terraform state in S3 so team members share the same state
  # Comment this out for first run — create the bucket manually first
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "cloud-native-migration/terraform.tfstate"
  #   region = "us-east-1"
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "cloud-native-migration"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}