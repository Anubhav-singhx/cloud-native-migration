# main.tf
# Root module — wires all child modules together

module "networking" {
  source             = "./modules/networking"
  vpc_cidr           = var.vpc_cidr
  cluster_name       = var.cluster_name
  availability_zones = var.availability_zones
}

module "eks" {
  source              = "./modules/eks"
  cluster_name        = var.cluster_name
  kubernetes_version  = var.kubernetes_version
  public_subnet_ids   = module.networking.public_subnet_ids
  private_subnet_ids  = module.networking.private_subnet_ids
  node_instance_type  = var.node_instance_type
  node_desired_size   = var.node_desired_size
  node_min_size       = var.node_min_size
  node_max_size       = var.node_max_size
}

module "ecr" {
  source       = "./modules/ecr"
  cluster_name = var.cluster_name
  services     = var.services
}