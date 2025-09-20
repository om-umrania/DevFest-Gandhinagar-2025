---
title: "Terraform Infrastructure as Code"
date: "2024-05-06"
tags: ["terraform", "iac", "infrastructure", "automation"]
---

# Terraform Infrastructure as Code

Terraform is an open-source infrastructure as code tool that enables you to define and provision cloud infrastructure using declarative configuration files.

## What is Infrastructure as Code?

### Benefits
- **Version Control**: Track infrastructure changes
- **Reproducibility**: Consistent environments
- **Automation**: Reduce manual errors
- **Collaboration**: Team-based infrastructure management
- **Documentation**: Self-documenting infrastructure

### Terraform vs Other Tools
- **Terraform**: Multi-cloud, declarative
- **CloudFormation**: AWS-specific, declarative
- **Ansible**: Configuration management, imperative
- **Pulumi**: Multi-cloud, programming languages

## Getting Started

### Installation
```bash
# Download Terraform
wget https://releases.hashicorp.com/terraform/1.5.0/terraform_1.5.0_linux_amd64.zip

# Extract and install
unzip terraform_1.5.0_linux_amd64.zip
sudo mv terraform /usr/local/bin/

# Verify installation
terraform version
```

### Basic Configuration
```hcl
# main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "us-west-2"
}

resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
  
  tags = {
    Name = "Web Server"
  }
}
```

## Core Concepts

### Providers
- **AWS**: Amazon Web Services
- **Azure**: Microsoft Azure
- **GCP**: Google Cloud Platform
- **Docker**: Container management
- **Kubernetes**: Container orchestration

### Resources
- **Infrastructure Components**: Servers, databases, networks
- **Configuration Blocks**: Define resource properties
- **State Management**: Track resource state
- **Dependencies**: Resource relationships

### State
- **Current State**: Actual infrastructure state
- **Desired State**: Configuration-defined state
- **State File**: JSON file storing state
- **State Backend**: Remote state storage

## Basic Commands

### Initialization
```bash
# Initialize Terraform
terraform init

# Initialize with backend configuration
terraform init -backend-config="bucket=my-terraform-state"
```

### Planning
```bash
# Create execution plan
terraform plan

# Save plan to file
terraform plan -out=tfplan

# Apply saved plan
terraform apply tfplan
```

### Application
```bash
# Apply changes
terraform apply

# Auto-approve changes
terraform apply -auto-approve

# Apply specific resource
terraform apply -target=aws_instance.web
```

### Destruction
```bash
# Destroy infrastructure
terraform destroy

# Auto-approve destruction
terraform destroy -auto-approve
```

## Resource Configuration

### AWS EC2 Instance
```hcl
resource "aws_instance" "web_server" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
  
  vpc_security_group_ids = [aws_security_group.web_sg.id]
  subnet_id              = aws_subnet.public.id
  
  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y httpd
    systemctl start httpd
    systemctl enable httpd
  EOF
  
  tags = {
    Name        = "Web Server"
    Environment = "Production"
    Owner       = "DevOps Team"
  }
}
```

### Security Group
```hcl
resource "aws_security_group" "web_sg" {
  name_prefix = "web-sg-"
  vpc_id      = aws_vpc.main.id
  
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  tags = {
    Name = "Web Security Group"
  }
}
```

### RDS Database
```hcl
resource "aws_db_instance" "main" {
  identifier = "main-database"
  
  engine         = "postgres"
  engine_version = "13.7"
  instance_class = "db.t3.micro"
  
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_encrypted     = true
  
  db_name  = "mydb"
  username = "admin"
  password = var.db_password
  
  vpc_security_group_ids = [aws_security_group.db_sg.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name
  
  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"
  
  skip_final_snapshot = true
  
  tags = {
    Name = "Main Database"
  }
}
```

## Variables and Outputs

### Variables
```hcl
# variables.tf
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t2.micro"
  
  validation {
    condition     = contains(["t2.micro", "t2.small", "t2.medium"], var.instance_type)
    error_message = "Instance type must be t2.micro, t2.small, or t2.medium."
  }
}

variable "environment" {
  description = "Environment name"
  type        = string
  
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}
```

### Outputs
```hcl
# outputs.tf
output "instance_id" {
  description = "ID of the EC2 instance"
  value       = aws_instance.web.id
}

output "instance_public_ip" {
  description = "Public IP address of the EC2 instance"
  value       = aws_instance.web.public_ip
}

output "database_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}
```

## Modules

### Module Structure
```
modules/
├── ec2/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
├── rds/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   └── versions.tf
└── vpc/
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    └── versions.tf
```

### Module Usage
```hcl
# main.tf
module "vpc" {
  source = "./modules/vpc"
  
  cidr_block = "10.0.0.0/16"
  environment = var.environment
}

module "ec2" {
  source = "./modules/ec2"
  
  vpc_id = module.vpc.vpc_id
  subnet_id = module.vpc.public_subnet_id
  instance_type = var.instance_type
}

module "rds" {
  source = "./modules/rds"
  
  vpc_id = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  db_password = var.db_password
}
```

## State Management

### Local State
```hcl
# Default local state
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

### Remote State
```hcl
# S3 backend
terraform {
  backend "s3" {
    bucket = "my-terraform-state"
    key    = "prod/terraform.tfstate"
    region = "us-west-2"
    
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}
```

### State Commands
```bash
# Show current state
terraform show

# List resources in state
terraform state list

# Move resource in state
terraform state mv aws_instance.old aws_instance.new

# Remove resource from state
terraform state rm aws_instance.web

# Import existing resource
terraform import aws_instance.web i-1234567890abcdef0
```

## Workspaces

### Workspace Management
```bash
# List workspaces
terraform workspace list

# Create new workspace
terraform workspace new staging

# Switch workspace
terraform workspace select staging

# Show current workspace
terraform workspace show

# Delete workspace
terraform workspace delete staging
```

### Workspace Usage
```hcl
# Use workspace in configuration
resource "aws_instance" "web" {
  ami           = "ami-0c55b159cbfafe1d0"
  instance_type = "t2.micro"
  
  tags = {
    Name        = "Web Server"
    Environment = terraform.workspace
  }
}
```

## Best Practices

### Code Organization
- **Separate Environments**: Use workspaces or directories
- **Modular Design**: Create reusable modules
- **Version Control**: Track all changes
- **Documentation**: Document complex configurations

### Security
- **Sensitive Data**: Use variables and outputs carefully
- **State Security**: Secure state file storage
- **Access Control**: Limit Terraform permissions
- **Secrets Management**: Use external secret management

### Performance
- **Parallel Execution**: Terraform runs operations in parallel
- **Targeted Operations**: Use -target for specific resources
- **State Optimization**: Regular state cleanup
- **Provider Caching**: Use provider caching

### Maintenance
- **Regular Updates**: Keep providers and Terraform updated
- **State Validation**: Regular state validation
- **Cost Management**: Monitor infrastructure costs
- **Backup Strategy**: Backup state files regularly
