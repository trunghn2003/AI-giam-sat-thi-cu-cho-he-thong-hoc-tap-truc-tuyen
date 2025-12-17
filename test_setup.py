#!/usr/bin/env python3
"""
Quick setup test for exam monitoring system
"""

import os
import sys

def check_dependencies():
    """Check if all required packages are installed"""
    print("Checking dependencies...")
    required = {
        'boto3': '1.34.0',
        'pymysql': '1.1.0',
        'dotenv': '1.0.0'
    }
    
    missing = []
    for package, version in required.items():
        try:
            if package == 'dotenv':
                import dotenv
                print(f"✓ python-dotenv installed")
            elif package == 'pymysql':
                import pymysql
                print(f"✓ PyMySQL installed")
            elif package == 'boto3':
                import boto3
                print(f"✓ boto3 installed")
        except ImportError:
            missing.append(f"{package}=={version}")
    
    if missing:
        print(f"\n✗ Missing packages: {', '.join(missing)}")
        print(f"Install with: pip install {' '.join(missing)}")
        return False
    
    print("\n✓ All dependencies installed\n")
    return True


def check_env_file():
    """Check if .env file exists and has required variables"""
    print("Checking environment configuration...")
    
    if not os.path.exists('.env'):
        print("✗ .env file not found")
        print("Copy .env.example to .env and fill in your credentials:")
        print("  cp .env.example .env")
        return False
    
    from dotenv import load_dotenv
    load_dotenv()
    
    required_vars = [
        'S3_BUCKET_NAME',
        'AWS_REGION',
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'MYSQL_HOST',
        'MYSQL_PORT',
        'MYSQL_DATABASE',
        'MYSQL_USER',
        'MYSQL_PASSWORD'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"✗ Missing environment variables: {', '.join(missing)}")
        print("Edit .env file and provide these values")
        return False
    
    print("✓ Environment file configured\n")
    return True


def check_s3_connection():
    """Test S3 connection"""
    print("Testing S3 connection...")
    
    try:
        from database.config import S3Config
        import boto3
        
        config = S3Config.from_env()
        s3_client = boto3.client(
            's3',
            region_name=config.region,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key
        )
        
        # Try to check if bucket exists
        s3_client.head_bucket(Bucket=config.bucket_name)
        print(f"✓ S3 bucket '{config.bucket_name}' accessible\n")
        return True
        
    except Exception as e:
        print(f"✗ S3 connection failed: {str(e)}")
        print("Make sure:")
        print("  1. AWS credentials are correct")
        print("  2. S3 bucket exists")
        print("  3. Bucket region matches AWS_REGION")
        print(f"\nCreate bucket with: aws s3 mb s3://{os.getenv('S3_BUCKET_NAME', 'your-bucket')} --region {os.getenv('AWS_REGION', 'ap-southeast-1')}\n")
        return False


def check_mysql_connection():
    """Test MySQL connection"""
    print("Testing MySQL connection...")
    
    try:
        from database.config import MySQLConfig
        import pymysql
        
        config = MySQLConfig.from_env()
        connection = pymysql.connect(
            host=config.host,
            port=config.port,
            user=config.user,
            password=config.password,
            database=config.database
        )
        
        # Check if tables exist
        cursor = connection.cursor()
        cursor.execute("SHOW TABLES LIKE 'violations'")
        violations_table = cursor.fetchone()
        
        cursor.execute("SHOW TABLES LIKE 'violation_summary'")
        summary_table = cursor.fetchone()
        
        cursor.close()
        connection.close()
        
        if not violations_table or not summary_table:
            print("✗ Database tables not found")
            print("Initialize database with: mysql -u root -p < database/schema.sql\n")
            return False
        
        print(f"✓ MySQL database '{config.database}' accessible")
        print("✓ Required tables exist\n")
        return True
        
    except Exception as e:
        print(f"✗ MySQL connection failed: {str(e)}")
        print("Make sure:")
        print("  1. MySQL is running")
        print("  2. Database exists: CREATE DATABASE exam_system;")
        print("  3. Schema is loaded: mysql -u root -p exam_system < database/schema.sql\n")
        return False


def check_face_database():
    """Check if face database has registered students"""
    print("Checking face database...")
    
    try:
        from cheating_detection.face_database import FaceDatabase
        
        db = FaceDatabase()
        students = db.list_students()
        
        if not students:
            print("⚠ No students registered")
            print("Register at least one student to test verification:")
            print("  POST /api/students with student_id, name, class, image\n")
        else:
            print(f"✓ {len(students)} student(s) registered\n")
        
        return True
        
    except Exception as e:
        print(f"✗ Failed to check face database: {str(e)}\n")
        return False


def main():
    """Run all setup checks"""
    print("=" * 60)
    print("Exam Monitoring System - Setup Test")
    print("=" * 60 + "\n")
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Environment", check_env_file),
        ("S3 Connection", check_s3_connection),
        ("MySQL Connection", check_mysql_connection),
        ("Face Database", check_face_database),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"✗ {name} check failed with error: {str(e)}\n")
            results[name] = False
    
    print("=" * 60)
    print("Setup Summary")
    print("=" * 60)
    
    for name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {name}")
    
    print()
    
    if all(results.values()):
        print("✓ All checks passed! System ready for testing.")
        print("\nNext steps:")
        print("  1. Restart Flask server: python app.py")
        print("  2. Test monitor endpoint: see MONITOR_API_DOCS.md")
        print("  3. Integrate with frontend")
    else:
        print("✗ Some checks failed. Please fix the issues above.")
        sys.exit(1)


if __name__ == '__main__':
    main()
