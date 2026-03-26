# modules/networking/main.tf
# Creates the VPC, subnets across 2 AZs, internet gateway, and routing

# ─── VPC ─────────────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true   # Needed for EKS
  enable_dns_support   = true   # Needed for EKS

  tags = {
    Name = "${var.cluster_name}-vpc"
    # These tags are REQUIRED for the AWS Load Balancer Controller to find subnets
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# ─── PUBLIC SUBNETS (one per AZ) ─────────────────────────────────────────────
# Public subnets are for the Load Balancer (internet-facing)
resource "aws_subnet" "public" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index)
  availability_zone = var.availability_zones[count.index]

  # Auto-assign public IPs to instances in this subnet
  map_public_ip_on_launch = true

  tags = {
    Name = "${var.cluster_name}-public-${var.availability_zones[count.index]}"
    # This tag tells the Load Balancer Controller this is a public subnet
    "kubernetes.io/role/elb"                    = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# ─── PRIVATE SUBNETS (one per AZ) ────────────────────────────────────────────
# Private subnets are for worker nodes (more secure, not directly internet-accessible)
resource "aws_subnet" "private" {
  count             = length(var.availability_zones)
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 4, count.index + length(var.availability_zones))
  availability_zone = var.availability_zones[count.index]

  tags = {
    Name = "${var.cluster_name}-private-${var.availability_zones[count.index]}"
    # This tag tells the Load Balancer Controller this is a private subnet
    "kubernetes.io/role/internal-elb"           = "1"
    "kubernetes.io/cluster/${var.cluster_name}" = "shared"
  }
}

# ─── INTERNET GATEWAY ────────────────────────────────────────────────────────
# Allows traffic between VPC and the internet
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${var.cluster_name}-igw" }
}

# ─── ELASTIC IPs for NAT Gateways ────────────────────────────────────────────
resource "aws_eip" "nat" {
  count  = length(var.availability_zones)
  domain = "vpc"
  tags   = { Name = "${var.cluster_name}-nat-eip-${count.index}" }
}

# ─── NAT GATEWAYS (one per AZ for HA) ────────────────────────────────────────
# Allow private subnet instances to reach internet (for pulling images, updates)
# without being directly reachable from internet
resource "aws_nat_gateway" "main" {
  count         = length(var.availability_zones)
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${var.cluster_name}-nat-${count.index}" }
  depends_on    = [aws_internet_gateway.main]
}

# ─── ROUTE TABLES ────────────────────────────────────────────────────────────

# Public route table: sends all traffic to internet gateway
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
  tags = { Name = "${var.cluster_name}-public-rt" }
}

resource "aws_route_table_association" "public" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private route tables: one per AZ, sends traffic to that AZ's NAT gateway
resource "aws_route_table" "private" {
  count  = length(var.availability_zones)
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  tags = { Name = "${var.cluster_name}-private-rt-${count.index}" }
}

resource "aws_route_table_association" "private" {
  count          = length(var.availability_zones)
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}