"""
MySQL database service for violation tracking.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pymysql
from pymysql.cursors import DictCursor

from .config import mysql_config

LOGGER = logging.getLogger(__name__)


class MySQLService:
    """Handle MySQL operations for violation tracking."""

    def __init__(self):
        self.config = mysql_config
        self._connection = None

    def _get_connection(self):
        """Get or create MySQL connection."""
        if self._connection is None or not self._connection.open:
            try:
                self._connection = pymysql.connect(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database,
                    charset=self.config.charset,
                    cursorclass=DictCursor,
                    autocommit=self.config.autocommit
                )
                LOGGER.info("MySQL connection established")
            except pymysql.Error as e:
                LOGGER.error(f"Failed to connect to MySQL: {e}")
                raise
        return self._connection

    def insert_violation(
        self,
        exam_period_id: int,
        submission_id: int,
        user_id: int,
        violation_type: str,
        severity: str,
        confidence: float,
        image_url: Optional[str],
        image_key: Optional[str],
        detection_data: Dict[str, Any],
        detected_at: datetime
    ) -> Optional[int]:
        """
        Insert a new violation record.

        Args:
            exam_period_id: Exam period ID
            submission_id: Submission ID
            user_id: Student user ID
            violation_type: Type of violation
            severity: Severity level (low, medium, high, critical)
            confidence: Confidence score (0.0-1.0)
            image_url: S3 URL of the violation image
            image_key: S3 key for deletion
            detection_data: Full detection result as dict
            detected_at: When the violation was detected

        Returns:
            Inserted violation ID or None if failed
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                sql = """
                INSERT INTO violations (
                    exam_period_id, submission_id, user_id, violation_type,
                    severity, confidence, image_url, image_key,
                    detection_data, detected_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    exam_period_id,
                    submission_id,
                    user_id,
                    violation_type,
                    severity,
                    confidence,
                    image_url,
                    image_key,
                    json.dumps(detection_data),
                    detected_at
                ))
                violation_id = cursor.lastrowid
                LOGGER.info(f"Inserted violation ID: {violation_id}")
                return violation_id
        except pymysql.Error as e:
            LOGGER.error(f"Failed to insert violation: {e}")
            return None

    def update_violation_summary(
        self,
        submission_id: int,
        user_id: int,
        exam_period_id: int,
        severity: str,
        detected_at: datetime
    ) -> bool:
        """
        Update or create violation summary for a submission.

        Args:
            submission_id: Submission ID
            user_id: Student user ID
            exam_period_id: Exam period ID
            severity: Severity of the new violation
            detected_at: When the violation was detected

        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                # Use INSERT ... ON DUPLICATE KEY UPDATE
                sql = """
                INSERT INTO violation_summary (
                    submission_id, user_id, exam_period_id,
                    total_violations, critical_count, high_count,
                    medium_count, low_count, first_violation_at,
                    last_violation_at, risk_score
                ) VALUES (%s, %s, %s, 1,
                    CASE WHEN %s = 'critical' THEN 1 ELSE 0 END,
                    CASE WHEN %s = 'high' THEN 1 ELSE 0 END,
                    CASE WHEN %s = 'medium' THEN 1 ELSE 0 END,
                    CASE WHEN %s = 'low' THEN 1 ELSE 0 END,
                    %s, %s, 0
                )
                ON DUPLICATE KEY UPDATE
                    total_violations = total_violations + 1,
                    critical_count = critical_count + CASE WHEN %s = 'critical' THEN 1 ELSE 0 END,
                    high_count = high_count + CASE WHEN %s = 'high' THEN 1 ELSE 0 END,
                    medium_count = medium_count + CASE WHEN %s = 'medium' THEN 1 ELSE 0 END,
                    low_count = low_count + CASE WHEN %s = 'low' THEN 1 ELSE 0 END,
                    last_violation_at = %s,
                    risk_score = (
                        (critical_count + CASE WHEN %s = 'critical' THEN 1 ELSE 0 END) * 50 +
                        (high_count + CASE WHEN %s = 'high' THEN 1 ELSE 0 END) * 10 +
                        (medium_count + CASE WHEN %s = 'medium' THEN 1 ELSE 0 END) * 10 +
                        (low_count + CASE WHEN %s = 'low' THEN 1 ELSE 0 END) * 10
                    )
                """
                cursor.execute(sql, (
                    submission_id, user_id, exam_period_id,
                    severity, severity, severity, severity,
                    detected_at, detected_at,
                    severity, severity, severity, severity,
                    detected_at,
                    severity, severity, severity, severity
                ))
                LOGGER.info(f"Updated violation summary for submission {submission_id}")
                return True
        except pymysql.Error as e:
            LOGGER.error(f"Failed to update violation summary: {e}")
            return False

    def get_violations_by_submission(
        self,
        submission_id: int,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all violations for a submission.

        Args:
            submission_id: Submission ID
            limit: Maximum number of records to return

        Returns:
            List of violation records
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                sql = """
                SELECT * FROM violations
                WHERE submission_id = %s
                ORDER BY detected_at DESC
                LIMIT %s
                """
                cursor.execute(sql, (submission_id, limit))
                results = cursor.fetchall()
                
                # Parse JSON detection_data
                for row in results:
                    if row.get('detection_data'):
                        row['detection_data'] = json.loads(row['detection_data'])
                
                return results
        except pymysql.Error as e:
            LOGGER.error(f"Failed to get violations: {e}")
            return []

    def get_violation_summary(self, submission_id: int) -> Optional[Dict[str, Any]]:
        """
        Get violation summary for a submission.

        Args:
            submission_id: Submission ID

        Returns:
            Summary record or None
        """
        try:
            conn = self._get_connection()
            with conn.cursor() as cursor:
                sql = "SELECT * FROM violation_summary WHERE submission_id = %s"
                cursor.execute(sql, (submission_id,))
                return cursor.fetchone()
        except pymysql.Error as e:
            LOGGER.error(f"Failed to get violation summary: {e}")
            return None

    def close(self):
        """Close MySQL connection."""
        if self._connection and self._connection.open:
            self._connection.close()
            LOGGER.info("MySQL connection closed")


# Singleton instance
mysql_service = MySQLService()
