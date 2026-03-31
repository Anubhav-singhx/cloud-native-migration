# modules/ecr/main.tf
resource "aws_ecr_repository" "services" {
  for_each = toset(var.services)

  name                 = "${var.cluster_name}/${each.value}"
  image_tag_mutability = "MUTABLE"
  
  # This allows Terraform to delete the repository even if it still contains images
  force_delete = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.cluster_name}-${each.value}"
  }
}

# (lifecycle policy stays exactly the same)
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