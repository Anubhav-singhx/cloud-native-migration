# modules/ecr/main.tf
# Creates ECR (Elastic Container Registry) repos for each microservice
# ECR is private Docker registry managed by AWS

resource "aws_ecr_repository" "services" {
  for_each             = toset(var.services)
  name                 = "${var.cluster_name}/${each.value}"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true   # Automatically scan images for vulnerabilities on push
  }

  tags = { Name = "${var.cluster_name}-${each.value}" }
}

# Lifecycle policy: keep only the last 10 images to save storage costs
resource "aws_ecr_lifecycle_policy" "services" {
  for_each   = aws_ecr_repository.services
  repository = each.value.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}