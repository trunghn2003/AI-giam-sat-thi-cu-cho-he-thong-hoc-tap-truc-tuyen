"""
S3 service for uploading violation images.
"""

import logging
from datetime import datetime
from io import BytesIO
from typing import Optional, Tuple

import boto3
import cv2
import numpy as np
from botocore.exceptions import BotoCoreError, ClientError

from .config import s3_config

LOGGER = logging.getLogger(__name__)


class S3Service:
    """Handle S3 operations for violation images."""

    def __init__(self):
        self.bucket_name = s3_config.bucket_name
        self.base_path = s3_config.base_path
        self.public_url = s3_config.public_url
        
        # Initialize S3 client with optional custom endpoint (Cloudflare R2)
        try:
            client_config = {
                'region_name': s3_config.region,
                'aws_access_key_id': s3_config.access_key,
                'aws_secret_access_key': s3_config.secret_key
            }
            
            # Add custom endpoint if provided (for Cloudflare R2)
            if s3_config.endpoint_url:
                client_config['endpoint_url'] = s3_config.endpoint_url
                LOGGER.info(f"Using custom S3 endpoint: {s3_config.endpoint_url}")
            
            self.s3_client = boto3.client('s3', **client_config)
            LOGGER.info(f"S3 client initialized for bucket: {self.bucket_name}")
        except Exception as e:
            LOGGER.error(f"Failed to initialize S3 client: {e}")
            self.s3_client = None

    def upload_violation_image(
        self,
        image_bgr: np.ndarray,
        exam_period_id: int,
        submission_id: int,
        user_id: int,
        violation_type: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Upload violation image to S3.

        Args:
            image_bgr: BGR image array
            exam_period_id: Exam period ID
            submission_id: Submission ID
            user_id: Student user ID
            violation_type: Type of violation

        Returns:
            Tuple of (s3_url, s3_key) or (None, None) if failed
        """
        if self.s3_client is None:
            LOGGER.error("S3 client not initialized")
            return None, None

        try:
            # Generate S3 key with hierarchical structure
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            s3_key = (
                f"{self.base_path}/"
                f"exam_{exam_period_id}/"
                f"submission_{submission_id}/"
                f"user_{user_id}/"
                f"{violation_type}_{timestamp}.jpg"
            )

            # Encode image to JPEG
            success, buffer = cv2.imencode('.jpg', image_bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            if not success:
                LOGGER.error("Failed to encode image to JPEG")
                return None, None

            # Upload to S3
            image_bytes = BytesIO(buffer.tobytes())
            self.s3_client.upload_fileobj(
                image_bytes,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': 'image/jpeg',
                    # 'Metadata': {
                    #     'exam_period_id': str(exam_period_id),
                    #     'submission_id': str(submission_id),
                    #     'user_id': str(user_id),
                    #     'violation_type': violation_type,
                    #     'uploaded_at': datetime.now().isoformat()
                    # }
                }
            )

            # Generate public URL
            if self.public_url:
                # Use public URL for Cloudflare R2
                s3_url = f"{self.public_url}/{s3_key}"
            else:
                # Use default S3 URL
                s3_url = f"https://{self.bucket_name}.s3.{s3_config.region}.amazonaws.com/{s3_key}"
            
            LOGGER.info(f"Uploaded violation image: {s3_key}")
            return s3_url, s3_key

        except (BotoCoreError, ClientError) as e:
            LOGGER.error(f"S3 upload failed: {e}")
            return None, None
        except Exception as e:
            LOGGER.error(f"Unexpected error during S3 upload: {e}")
            return None, None

    def delete_violation_image(self, s3_key: str) -> bool:
        """
        Delete violation image from S3.

        Args:
            s3_key: S3 object key

        Returns:
            True if deleted successfully, False otherwise
        """
        if self.s3_client is None:
            LOGGER.error("S3 client not initialized")
            return False

        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            LOGGER.info(f"Deleted S3 object: {s3_key}")
            return True
        except (BotoCoreError, ClientError) as e:
            LOGGER.error(f"Failed to delete S3 object {s3_key}: {e}")
            return False


# Singleton instance
s3_service = S3Service()
