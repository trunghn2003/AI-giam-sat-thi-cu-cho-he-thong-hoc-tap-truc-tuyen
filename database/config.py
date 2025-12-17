"""
Configuration for S3 and MySQL connections.
"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class S3Config:
    """AWS S3 / Cloudflare R2 configuration."""
    bucket_name: str = os.getenv("S3_BUCKET_NAME", "exam-monitoring-violations")
    region: str = os.getenv("AWS_REGION", "auto")
    access_key: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    secret_key: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    endpoint_url: str = os.getenv("AWS_ENDPOINT_URL")  # For Cloudflare R2 or custom S3
    public_url: str = os.getenv("AWS_PUBLIC_URL")      # Public URL base for files
    base_path: str = "violations"  # Base path in S3 bucket


@dataclass
class MySQLConfig:
    """MySQL database configuration."""
    host: str = os.getenv("MYSQL_HOST", "localhost")
    port: int = int(os.getenv("MYSQL_PORT", "3306"))
    database: str = os.getenv("MYSQL_DATABASE", "exam_monitoring")
    user: str = os.getenv("MYSQL_USER", "root")
    password: str = os.getenv("MYSQL_PASSWORD", "")
    charset: str = "utf8mb4"
    autocommit: bool = True


# Singleton instances
s3_config = S3Config()
mysql_config = MySQLConfig()
