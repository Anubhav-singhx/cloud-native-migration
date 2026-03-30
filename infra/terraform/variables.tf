# variables.tf
# All configurable values live here — no hardcoded values in other files

variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "cloud-native-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version for EKS"
  type        = string
  default     = "1.29"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "AZs for multi-AZ deployment (HA requires 2 minimum)"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "node_instance_type" {
  description = "EC2 instance type for worker nodes (t3.micro = free tier eligible)"
  type        = string
  default     = "t3.medium"
}

variable "node_desired_size" {
  description = "Desired number of worker nodes"
  type        = number
  default     = 4
}

variable "node_min_size" {
  description = "Minimum worker nodes (for cost saving)"
  type        = number
  default     = 3
}

variable "node_max_size" {
  description = "Maximum worker nodes (for scaling)"
  type        = number
  default     = 5
}

variable "services" {
  description = "List of microservices (used to create ECR repos)"
  type        = list(string)
  default     = ["auth-service", "product-service", "order-service", "notification-service"]
}