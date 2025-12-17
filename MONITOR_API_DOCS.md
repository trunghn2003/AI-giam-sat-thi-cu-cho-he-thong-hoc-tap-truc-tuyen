# Exam Monitoring API Documentation

## Overview
The monitoring system captures webcam frames every 5 seconds during exams, detects violations using AI models, and stores evidence in S3 + MySQL.

## Prerequisites

### 1. Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```bash
# AWS S3 Configuration
S3_BUCKET_NAME=your-bucket-name
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# MySQL Configuration
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=exam_system
MYSQL_USER=root
MYSQL_PASSWORD=your-password
```

### 2. Database Setup
Execute the schema to create violation tracking tables:

```bash
mysql -u root -p < database/schema.sql
```

This creates:
- `violations` table: Individual violation records with S3 URLs
- `violation_summary` table: Aggregated statistics per submission

### 3. S3 Bucket Setup
Create an S3 bucket with proper permissions:

```bash
aws s3 mb s3://your-bucket-name --region ap-southeast-1
```

## API Endpoint

### POST `/api/monitor`

Real-time exam monitoring endpoint. Frontend should call this every 5 seconds during exam sessions.

#### Request

**Content-Type:** `multipart/form-data`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `user_id` | integer | Yes | Student's user ID |
| `exam_period_id` | integer | Yes | Exam period/session ID |
| `submission_id` | integer | Yes | Student's exam submission ID |
| `image` | file | Yes | Webcam capture (JPG/PNG format) |

#### Response

**When violation detected:**
```json
{
  "status": "violation_detected",
  "violation_type": "suspicious_object",
  "severity": "critical",
  "confidence": 0.87,
  "image_url": "https://bucket.s3.region.amazonaws.com/violations/exam_123/submission_456/user_789/suspicious_object_1702800000.jpg",
  "details": {
    "faces_detected": 1,
    "objects_detected": [
      {
        "class": "mobile_phone",
        "confidence": 0.87,
        "bbox": [120, 150, 200, 250]
      }
    ],
    "gaze_direction": "forward"
  }
}
```

**When no violation:**
```json
{
  "status": "clear",
  "details": {
    "faces_detected": 1,
    "objects_detected": [],
    "gaze_direction": "forward"
  }
}
```

**Error responses:**
```json
{
  "error": "Missing required field: user_id"
}

{
  "error": "Invalid image file"
}

{
  "error": "Failed to upload to S3: [error details]"
}

{
  "error": "Failed to save violation: [error details]"
}
```

## Violation Types & Severity

### Critical (Severity: critical)
| Type | Description | Triggered When |
|------|-------------|----------------|
| `suspicious_object` | Prohibited items detected | Mobile phone or headphones detected |
| `multiple_faces` | More than one person | Face count > 1 |
| `no_face` | Student not visible | Face count = 0 |
| `unknown_person` | Unregistered face | Face doesn't match registered student |

### High (Severity: high)
| Type | Description | Triggered When |
|------|-------------|----------------|
| `looking_away` | Gaze not on screen | Eye gaze not forward |
| `head_movement` | Abnormal head movement | Head tracking indicates movement |

### Medium (Severity: medium)
| Type | Description | Triggered When |
|------|-------------|----------------|
| `other_violation` | Unclassified issue | Other detection anomalies |

## S3 Storage Structure

Images are stored with hierarchical paths:
```
violations/
  exam_{exam_period_id}/
    submission_{submission_id}/
      user_{user_id}/
        suspicious_object_1702800000.jpg
        multiple_faces_1702800005.jpg
        looking_away_1702800010.jpg
```

Example: `violations/exam_123/submission_456/user_789/suspicious_object_1702800000.jpg`

## Database Schema

### violations table
```sql
CREATE TABLE violations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    exam_period_id BIGINT UNSIGNED NOT NULL,
    submission_id BIGINT UNSIGNED NOT NULL,
    user_id BIGINT UNSIGNED NOT NULL,
    violation_type VARCHAR(50) NOT NULL,
    severity ENUM('low', 'medium', 'high', 'critical') NOT NULL,
    confidence DECIMAL(5,4) NOT NULL,
    image_url TEXT NOT NULL,
    image_key VARCHAR(500) NOT NULL,
    detection_data JSON,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_submission (submission_id),
    INDEX idx_user (user_id),
    INDEX idx_exam_period (exam_period_id),
    INDEX idx_severity (severity),
    INDEX idx_detected_at (detected_at)
);
```

### violation_summary table
```sql
CREATE TABLE violation_summary (
    submission_id BIGINT UNSIGNED PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    exam_period_id BIGINT UNSIGNED NOT NULL,
    total_violations INT DEFAULT 0,
    critical_count INT DEFAULT 0,
    high_count INT DEFAULT 0,
    medium_count INT DEFAULT 0,
    low_count INT DEFAULT 0,
    risk_score INT DEFAULT 0,
    first_violation_at TIMESTAMP NULL,
    last_violation_at TIMESTAMP NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Risk Score Formula:**
```
risk_score = (critical_count × 25) + (high_count × 15) + (medium_count × 8) + (low_count × 3)
```

## Frontend Integration

### JavaScript Example

```javascript
class ExamMonitor {
  constructor(userId, examPeriodId, submissionId) {
    this.userId = userId;
    this.examPeriodId = examPeriodId;
    this.submissionId = submissionId;
    this.intervalId = null;
  }

  async startMonitoring() {
    // Capture immediately
    await this.captureAndSend();
    
    // Then every 5 seconds
    this.intervalId = setInterval(() => {
      this.captureAndSend();
    }, 5000);
  }

  stopMonitoring() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  async captureAndSend() {
    try {
      // Get video element
      const video = document.getElementById('webcam');
      
      // Capture frame to canvas
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(video, 0, 0);
      
      // Convert to blob
      const blob = await new Promise(resolve => 
        canvas.toBlob(resolve, 'image/jpeg', 0.9)
      );
      
      // Prepare form data
      const formData = new FormData();
      formData.append('user_id', this.userId);
      formData.append('exam_period_id', this.examPeriodId);
      formData.append('submission_id', this.submissionId);
      formData.append('image', blob, 'frame.jpg');
      
      // Send to API
      const response = await fetch('http://localhost:8000/api/monitor', {
        method: 'POST',
        body: formData
      });
      
      const result = await response.json();
      
      if (result.status === 'violation_detected') {
        console.warn('Violation detected:', result);
        this.handleViolation(result);
      }
      
    } catch (error) {
      console.error('Monitoring error:', error);
    }
  }

  handleViolation(violation) {
    // Show warning to student
    if (violation.severity === 'critical') {
      alert(`⚠️ Violation: ${violation.violation_type}`);
    }
    
    // Update UI indicator
    document.getElementById('violation-indicator').classList.add('active');
    
    // Send to your backend for logging
    // ... your code here ...
  }
}

// Usage during exam
const monitor = new ExamMonitor(
  userId,           // From your auth system
  examPeriodId,     // Current exam session
  submissionId      // Student's submission record
);

// Start when exam begins
monitor.startMonitoring();

// Stop when exam ends
document.getElementById('submit-exam').addEventListener('click', () => {
  monitor.stopMonitoring();
});
```

### React Example

```jsx
import { useEffect, useRef, useState } from 'react';

function ExamMonitoringComponent({ userId, examPeriodId, submissionId }) {
  const videoRef = useRef(null);
  const [violations, setViolations] = useState([]);
  const intervalRef = useRef(null);

  useEffect(() => {
    startMonitoring();
    return () => stopMonitoring();
  }, []);

  const startMonitoring = () => {
    captureAndSend();
    intervalRef.current = setInterval(captureAndSend, 5000);
  };

  const stopMonitoring = () => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
    }
  };

  const captureAndSend = async () => {
    try {
      const canvas = document.createElement('canvas');
      canvas.width = videoRef.current.videoWidth;
      canvas.height = videoRef.current.videoHeight;
      const ctx = canvas.getContext('2d');
      ctx.drawImage(videoRef.current, 0, 0);

      const blob = await new Promise(resolve =>
        canvas.toBlob(resolve, 'image/jpeg', 0.9)
      );

      const formData = new FormData();
      formData.append('user_id', userId);
      formData.append('exam_period_id', examPeriodId);
      formData.append('submission_id', submissionId);
      formData.append('image', blob, 'frame.jpg');

      const response = await fetch('http://localhost:8000/api/monitor', {
        method: 'POST',
        body: formData
      });

      const result = await response.json();

      if (result.status === 'violation_detected') {
        setViolations(prev => [...prev, result]);
      }

    } catch (error) {
      console.error('Monitoring error:', error);
    }
  };

  return (
    <div>
      <video ref={videoRef} autoPlay />
      {violations.length > 0 && (
        <div className="violations-alert">
          ⚠️ {violations.length} violations detected
        </div>
      )}
    </div>
  );
}
```

## Querying Violations

### Get violations for a submission

```python
from database.mysql_service import MySQLService

mysql = MySQLService()
violations = mysql.get_violations_by_submission(submission_id=456)

for v in violations:
    print(f"Type: {v['violation_type']}, Severity: {v['severity']}")
    print(f"Image: {v['image_url']}")
    print(f"Detection: {v['detection_data']}")
```

### SQL Query Examples

```sql
-- Get all violations for a student
SELECT * FROM violations 
WHERE user_id = 789 
ORDER BY detected_at DESC;

-- Get violation summary
SELECT * FROM violation_summary 
WHERE submission_id = 456;

-- Get high-risk submissions
SELECT * FROM violation_summary 
WHERE risk_score > 100 
ORDER BY risk_score DESC;

-- Count violations by type
SELECT violation_type, COUNT(*) as count 
FROM violations 
WHERE exam_period_id = 123 
GROUP BY violation_type;

-- Get critical violations only
SELECT * FROM violations 
WHERE severity = 'critical' 
AND exam_period_id = 123;
```

## Testing

### 1. Test with curl

```bash
# Register a student first
curl -X POST http://localhost:8000/api/students \
  -F "student_id=789" \
  -F "name=Test Student" \
  -F "class=10A" \
  -F "image=@test_face.jpg"

# Monitor endpoint test
curl -X POST http://localhost:8000/api/monitor \
  -F "user_id=789" \
  -F "exam_period_id=123" \
  -F "submission_id=456" \
  -F "image=@test_frame.jpg"
```

### 2. Test violation scenarios

**No face detected:**
- Send image without any person → `no_face` violation

**Multiple faces:**
- Send image with 2+ people → `multiple_faces` violation

**Suspicious object:**
- Send image with phone/headphones → `suspicious_object` violation

**Unknown person:**
- Send image of unregistered student → `unknown_person` violation

**Looking away:**
- Send image with student looking sideways → `looking_away` violation

## Troubleshooting

### S3 Upload Fails
- Check AWS credentials in `.env`
- Verify S3 bucket exists and has proper permissions
- Check AWS region matches your bucket region

### MySQL Connection Error
- Verify MySQL is running: `mysql.server status`
- Check credentials in `.env`
- Ensure database exists: `CREATE DATABASE exam_system;`
- Execute schema: `mysql -u root -p exam_system < database/schema.sql`

### No Violations Detected
- Check if models are loaded correctly (InsightFace, YOLOv8)
- Verify face database has registered students
- Test with `/api/detect` endpoint first
- Check image quality and lighting

### High Memory Usage
- Reduce monitoring frequency (e.g., 10s instead of 5s)
- Lower image resolution before sending
- Use JPEG quality compression (0.8-0.9)

## Performance Considerations

### Bandwidth Optimization
```javascript
// Compress image before sending
canvas.toBlob(resolve, 'image/jpeg', 0.8);  // 80% quality

// Or resize image
const maxWidth = 640;
if (video.videoWidth > maxWidth) {
  canvas.width = maxWidth;
  canvas.height = (video.videoHeight * maxWidth) / video.videoWidth;
}
```

### Request Rate Limiting
- Current: 1 request per 5 seconds per student
- With 100 students: ~20 req/sec average
- Consider load balancing for large exams (500+ students)

### S3 Cost Optimization
- Use lifecycle policies to archive old violations
- Consider S3 Intelligent-Tiering for automatic cost savings
- Delete violations after grading period ends

## Security Recommendations

1. **HTTPS Required:** Use SSL/TLS in production
2. **Authentication:** Add JWT tokens to monitor endpoint
3. **Rate Limiting:** Prevent abuse with Flask-Limiter
4. **Input Validation:** Sanitize all user inputs
5. **S3 Private Access:** Use presigned URLs for image access
6. **CORS Policy:** Restrict to your frontend domain

## Next Steps

1. ✅ Install dependencies: `pip install -r requirements.txt`
2. ✅ Configure `.env` with AWS and MySQL credentials
3. ⏳ Create S3 bucket
4. ⏳ Initialize MySQL database
5. ⏳ Test monitoring endpoint
6. ⏳ Integrate with frontend
7. ⏳ Set up production WSGI server (Gunicorn)
8. ⏳ Deploy with proper security measures
