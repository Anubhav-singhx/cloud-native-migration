output "cluster_name"     { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "ecr_repos"        { value = module.ecr.repository_urls }
output "vpc_id"           { value = module.networking.vpc_id }