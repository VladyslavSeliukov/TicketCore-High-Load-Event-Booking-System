module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = "ticketcore-prod-eks-cluster"
  cluster_version = "1.32"

  vpc_id                   = module.vpc.vpc_id
  subnet_ids               = module.vpc.private_subnets
  control_plane_subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access = true

  enable_irsa = true

  eks_managed_node_groups = {
    backend_nodes = {
      min_size     = 5
      max_size     = 6
      desired_size = 5

      instance_types = ["t3.micro"]
      capacity_type  = "ON_DEMAND"

      labels = {
        role = "backend-worker"
      }
    }
  }

  enable_cluster_creator_admin_permissions = true
}
