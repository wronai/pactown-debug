# Faulty Terraform configuration

provider "aws" {
  region     = "us-east-1"
  access_key = "AKIAIOSFODNN7EXAMPLE"
  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
}

resource "aws_instance" "web" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}

resource "aws_s3_bucket" "data" {
  bucket = "my-app-data"
  acl    = "public-read-write"
}

resource "aws_ebs_volume" "storage" {
  availability_zone = "us-east-1a"
  size              = 100
  encrypted         = false
}

resource "aws_security_group" "allow_all" {
  name = "allow_all"
  
  ingress {
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "database" {
  allocated_storage = 20
  engine            = "mysql"
  instance_class    = "db.t2.micro"
  password          = "admin123"
}

output "bucket_url" {
  value = aws_s3_bucket.data.bucket_domain_name
}
