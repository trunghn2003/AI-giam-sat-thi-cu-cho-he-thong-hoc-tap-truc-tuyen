# Database Schema for Exam Monitoring System

CREATE DATABASE IF NOT EXISTS exam_monitoring CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE exam_monitoring;

-- Bảng vi phạm
CREATE TABLE IF NOT EXISTS violations (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    exam_period_id BIGINT UNSIGNED NOT NULL COMMENT 'Foreign key to exam_periods.id',
    submission_id BIGINT UNSIGNED NOT NULL COMMENT 'Foreign key to exam_submissions.id',
    user_id BIGINT UNSIGNED NOT NULL COMMENT 'Foreign key to users.id (student)',
    violation_type VARCHAR(100) NOT NULL COMMENT 'e.g., multiple_faces, looking_away, suspicious_object, no_face, unknown_person',
    severity ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    confidence DECIMAL(5,2) COMMENT 'Confidence score 0.00-1.00',
    image_url VARCHAR(500) COMMENT 'S3 URL of the violation image',
    image_key VARCHAR(500) COMMENT 'S3 object key for deletion',
    detection_data JSON COMMENT 'Full detection result from pipeline',
    detected_at DATETIME NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_submission (submission_id),
    INDEX idx_user (user_id),
    INDEX idx_exam_period (exam_period_id),
    INDEX idx_detected_at (detected_at),
    INDEX idx_severity (severity),
    INDEX idx_violation_type (violation_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Bảng summary vi phạm theo submission
CREATE TABLE IF NOT EXISTS violation_summary (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    submission_id BIGINT UNSIGNED UNIQUE NOT NULL COMMENT 'Foreign key to exam_submissions.id',
    user_id BIGINT UNSIGNED NOT NULL COMMENT 'Foreign key to users.id (student)',
    exam_period_id BIGINT UNSIGNED NOT NULL COMMENT 'Foreign key to exam_periods.id',
    total_violations INT DEFAULT 0,
    critical_count INT DEFAULT 0,
    high_count INT DEFAULT 0,
    medium_count INT DEFAULT 0,
    low_count INT DEFAULT 0,
    first_violation_at DATETIME,
    last_violation_at DATETIME,
    risk_score DECIMAL(5,2) DEFAULT 0.00 COMMENT 'Overall risk score 0-100',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_risk_score (risk_score),
    INDEX idx_exam_period (exam_period_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
