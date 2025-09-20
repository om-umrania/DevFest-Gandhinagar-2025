---
title: "Amazon Web Services (AWS)"
date: "2024-04-30"
tags: ["aws", "cloud", "amazon", "infrastructure"]
---

# Amazon Web Services (AWS)

AWS is a comprehensive cloud computing platform offering over 200 services for computing, storage, databases, networking, and more.

## Core Services

### Compute Services
- **EC2**: Virtual servers in the cloud
- **Lambda**: Serverless compute service
- **ECS**: Container management service
- **EKS**: Kubernetes service

### Storage Services
- **S3**: Object storage service
- **EBS**: Block storage for EC2
- **EFS**: File system service
- **Glacier**: Long-term archival storage

### Database Services
- **RDS**: Relational database service
- **DynamoDB**: NoSQL database
- **ElastiCache**: In-memory caching
- **Redshift**: Data warehouse service

## Getting Started

### AWS Account Setup
1. Create AWS account
2. Set up billing alerts
3. Configure IAM users and roles
4. Enable MFA for security

### AWS CLI Installation
```bash
# Install AWS CLI
pip install awscli

# Configure credentials
aws configure

# Test connection
aws s3 ls
```

## EC2 (Elastic Compute Cloud)

### Launching Instances
```bash
# Launch instance
aws ec2 run-instances \
    --image-id ami-0abcdef1234567890 \
    --instance-type t2.micro \
    --key-name my-key-pair \
    --security-group-ids sg-12345678
```

### Instance Types
- **t2/t3**: Burstable performance
- **m5**: General purpose
- **c5**: Compute optimized
- **r5**: Memory optimized
- **g4**: GPU instances

### Security Groups
- Virtual firewalls
- Control inbound/outbound traffic
- Stateful rules
- Can be attached to multiple instances

## S3 (Simple Storage Service)

### Bucket Operations
```bash
# Create bucket
aws s3 mb s3://my-bucket-name

# List buckets
aws s3 ls

# Upload file
aws s3 cp file.txt s3://my-bucket-name/

# Download file
aws s3 cp s3://my-bucket-name/file.txt ./
```

### S3 Features
- **Versioning**: Keep multiple versions
- **Lifecycle**: Automatic transitions
- **Encryption**: Data at rest and in transit
- **Access Control**: Fine-grained permissions

## RDS (Relational Database Service)

### Database Engines
- **MySQL**: Open-source database
- **PostgreSQL**: Advanced open-source database
- **Oracle**: Enterprise database
- **SQL Server**: Microsoft database

### Creating Database
```bash
# Create RDS instance
aws rds create-db-instance \
    --db-instance-identifier mydb \
    --db-instance-class db.t2.micro \
    --engine mysql \
    --master-username admin \
    --master-user-password mypassword
```

## Lambda (Serverless Computing)

### Function Creation
```python
import json

def lambda_handler(event, context):
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
```

### Lambda Features
- **Event-driven**: Responds to events
- **Auto-scaling**: Scales automatically
- **Pay-per-use**: Only pay for execution time
- **Multiple runtimes**: Python, Node.js, Java, etc.

## Networking

### VPC (Virtual Private Cloud)
- Isolated network environment
- Subnets for different tiers
- Internet Gateway for public access
- NAT Gateway for private subnets

### Load Balancing
- **ALB**: Application Load Balancer
- **NLB**: Network Load Balancer
- **CLB**: Classic Load Balancer
- **Gateway Load Balancer**: Third-party appliances

## Security

### IAM (Identity and Access Management)
- **Users**: Individual accounts
- **Groups**: Collections of users
- **Roles**: Temporary permissions
- **Policies**: Permission documents

### Security Best Practices
- Use least privilege principle
- Enable MFA
- Regular access reviews
- Monitor with CloudTrail

## Monitoring and Logging

### CloudWatch
- **Metrics**: Performance data
- **Logs**: Application logs
- **Alarms**: Automated responses
- **Dashboards**: Visual monitoring

### CloudTrail
- API call logging
- Audit trail
- Compliance reporting
- Security analysis

## Cost Optimization

### Cost Management
- **Cost Explorer**: Analyze spending
- **Budgets**: Set spending limits
- **Reserved Instances**: Save on long-term usage
- **Spot Instances**: Use spare capacity

### Best Practices
- Right-size instances
- Use appropriate storage classes
- Implement auto-scaling
- Regular cost reviews

## Deployment Strategies

### Infrastructure as Code
- **CloudFormation**: AWS native
- **Terraform**: Multi-cloud support
- **CDK**: Programming languages
- **SAM**: Serverless applications

### CI/CD Pipeline
- **CodePipeline**: Continuous delivery
- **CodeBuild**: Build service
- **CodeDeploy**: Deployment service
- **CodeCommit**: Git repository service

## Best Practices

### Security
- Implement defense in depth
- Use encryption everywhere
- Regular security audits
- Follow AWS Well-Architected Framework

### Performance
- Choose right instance types
- Use caching effectively
- Optimize database queries
- Monitor and tune performance

### Cost
- Use cost allocation tags
- Implement auto-scaling
- Choose appropriate storage
- Regular cost optimization reviews
