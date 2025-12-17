# Hệ Thống Giám Sát Thi - Tổng Quan

## Tổng Quan Hệ Thống

Hệ thống giám sát thi tự động với AI đã được xây dựng hoàn chỉnh, bao gồm:

- ✅ **Đăng ký khuôn mặt học sinh** - API để đăng ký và quản lý database khuôn mặt
- ✅ **Xác thực học sinh trước thi** - Kiểm tra danh tính trước khi vào phòng thi
- ✅ **Giám sát thời gian thực** - Theo dõi học sinh mỗi 5 giây trong khi thi
- ✅ **Lưu trữ vi phạm tự động** - Upload ảnh lên S3 và lưu vào MySQL
- ✅ **Phân loại vi phạm** - Tự động phân loại mức độ nghiêm trọng

## Công Nghệ Sử Dụng

### AI Models
- **InsightFace (buffalo_l)**: Nhận diện khuôn mặt với độ chính xác cao
- **YOLOv8**: Phát hiện đồ vật (điện thoại, tai nghe) với threshold 0.6
- **MediaPipe Face Mesh**: Theo dõi hướng nhìn của mắt

### Backend
- **Flask**: REST API server
- **AWS S3 (boto3)**: Lưu trữ ảnh vi phạm trên cloud
- **MySQL (PyMySQL)**: Database theo dõi vi phạm
- **python-dotenv**: Quản lý cấu hình môi trường

## Cấu Trúc Dự Án

```
doancheating/
├── app.py                          # Flask API với tất cả endpoints
├── requirements.txt                # Dependencies (đã cập nhật)
├── .env.example                    # Template cho cấu hình
├── .env                           # Cấu hình thực tế (cần tạo)
│
├── database/                      # Module xử lý S3 và MySQL
│   ├── __init__.py
│   ├── config.py                  # S3Config, MySQLConfig
│   ├── s3_service.py              # Upload/delete ảnh lên S3
│   ├── mysql_service.py           # Insert/update violations
│   └── schema.sql                 # Database schema
│
├── cheating_detection/            # AI detection modules
│   ├── face_recognition.py        # Nhận diện khuôn mặt
│   ├── face_database.py           # Quản lý database học sinh
│   ├── object_detection.py        # Phát hiện đồ vật
│   ├── gaze_detection.py          # Theo dõi hướng nhìn
│   └── pipeline.py                # Pipeline tổng hợp
│
├── MONITOR_API_DOCS.md            # Documentation đầy đủ
├── VERIFY_API_EXAMPLES.md         # Ví dụ API xác thực
└── test_setup.py                  # Script kiểm tra setup
```

## API Endpoints

### 1. Quản Lý Học Sinh

#### POST `/api/students` - Đăng ký học sinh
```bash
curl -X POST http://localhost:8000/api/students \
  -F "student_id=123" \
  -F "name=Nguyen Van A" \
  -F "class=10A1" \
  -F "image=@student_photo.jpg"
```

#### GET `/api/students` - Danh sách học sinh
```bash
curl http://localhost:8000/api/students
```

#### DELETE `/api/students/{student_id}` - Xóa học sinh
```bash
curl -X DELETE http://localhost:8000/api/students/123
```

### 2. Xác Thực Trước Thi

#### POST `/api/students/verify/before` - Xác thực danh tính
```bash
curl -X POST http://localhost:8000/api/students/verify/before \
  -F "student_id=123" \
  -F "image=@current_photo.jpg"
```

**Response thành công:**
```json
{
  "verified": true,
  "student_id": "123",
  "name": "Nguyen Van A",
  "similarity": 0.85
}
```

**Response lỗi:**
```json
{
  "verified": false,
  "error": "Multiple faces detected (2 faces). Only one person allowed",
  "face_count": 2
}
```

### 3. Giám Sát Trong Thi ⭐ MỚI

#### POST `/api/monitor` - Giám sát thời gian thực
Frontend gửi ảnh mỗi 5 giây:

```bash
curl -X POST http://localhost:8000/api/monitor \
  -F "user_id=123" \
  -F "exam_period_id=456" \
  -F "submission_id=789" \
  -F "image=@webcam_frame.jpg"
```

**Response khi có vi phạm:**
```json
{
  "status": "violation_detected",
  "violation_type": "suspicious_object",
  "severity": "critical",
  "confidence": 0.87,
  "image_url": "https://bucket.s3.amazonaws.com/violations/exam_456/submission_789/user_123/suspicious_object_1702800000.jpg",
  "details": {
    "faces_detected": 1,
    "objects_detected": [
      {
        "class": "mobile_phone",
        "confidence": 0.87
      }
    ]
  }
}
```

**Response khi không có vi phạm:**
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

## Phân Loại Vi Phạm

### Critical (Nghiêm trọng)
- `suspicious_object` - Phát hiện điện thoại hoặc tai nghe
- `multiple_faces` - Nhiều hơn 1 người trong khung hình
- `no_face` - Không thấy khuôn mặt học sinh
- `unknown_person` - Người lạ (không phải học sinh đã đăng ký)

### High (Cao)
- `looking_away` - Nhìn sang chỗ khác
- `head_movement` - Cử động đầu bất thường

### Medium (Trung bình)
- `other_violation` - Vi phạm khác

## Database Schema

### Bảng `violations` - Lưu từng vi phạm
```sql
- id: BIGINT (Primary key)
- exam_period_id: BIGINT (ID kỳ thi)
- submission_id: BIGINT (ID bài thi học sinh nộp)
- user_id: BIGINT (ID học sinh)
- violation_type: VARCHAR(50)
- severity: ENUM('critical', 'high', 'medium', 'low')
- confidence: DECIMAL(5,4)
- image_url: TEXT (URL ảnh trên S3)
- image_key: VARCHAR(500) (S3 key)
- detection_data: JSON (Chi tiết phát hiện)
- detected_at: TIMESTAMP
```

### Bảng `violation_summary` - Tổng hợp theo bài thi
```sql
- submission_id: BIGINT (Primary key)
- user_id: BIGINT
- exam_period_id: BIGINT
- total_violations: INT
- critical_count: INT
- high_count: INT
- medium_count: INT
- low_count: INT
- risk_score: INT (= critical×25 + high×15 + medium×8 + low×3)
- first_violation_at: TIMESTAMP
- last_violation_at: TIMESTAMP
```

## Cấu Trúc Lưu Trữ S3

Ảnh được tổ chức theo cấu trúc:
```
violations/
  exam_{exam_period_id}/
    submission_{submission_id}/
      user_{user_id}/
        suspicious_object_1702800000.jpg
        multiple_faces_1702800005.jpg
        looking_away_1702800010.jpg
```

## Hướng Dẫn Cài Đặt

### 1. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 2. Cấu hình môi trường
```bash
# Copy template
cp .env.example .env

# Điền thông tin AWS S3
S3_BUCKET_NAME=exam-violations-bucket
AWS_REGION=ap-southeast-1
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret

# Điền thông tin MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=exam_system
MYSQL_USER=root
MYSQL_PASSWORD=your-password
```

### 3. Tạo S3 bucket
```bash
aws s3 mb s3://exam-violations-bucket --region ap-southeast-1
```

### 4. Khởi tạo database
```bash
# Tạo database
mysql -u root -p -e "CREATE DATABASE exam_system;"

# Import schema
mysql -u root -p exam_system < database/schema.sql
```

### 5. Kiểm tra setup
```bash
python test_setup.py
```

Script này sẽ kiểm tra:
- ✓ Dependencies đã cài đặt
- ✓ File .env đã cấu hình
- ✓ Kết nối S3 thành công
- ✓ Kết nối MySQL và tables đã tạo
- ✓ Face database sẵn sàng

### 6. Chạy server
```bash
python app.py
```

Server sẽ chạy tại: `http://localhost:8000`

## Tích Hợp Frontend

### JavaScript/React Example
```javascript
class ExamMonitor {
  constructor(userId, examPeriodId, submissionId) {
    this.userId = userId;
    this.examPeriodId = examPeriodId;
    this.submissionId = submissionId;
  }

  async startMonitoring() {
    // Gửi ngay lập tức
    await this.captureAndSend();
    
    // Sau đó mỗi 5 giây
    this.intervalId = setInterval(() => {
      this.captureAndSend();
    }, 5000);
  }

  stopMonitoring() {
    clearInterval(this.intervalId);
  }

  async captureAndSend() {
    // Lấy frame từ webcam
    const video = document.getElementById('webcam');
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);
    
    // Convert sang blob
    const blob = await new Promise(resolve => 
      canvas.toBlob(resolve, 'image/jpeg', 0.9)
    );
    
    // Gửi lên server
    const formData = new FormData();
    formData.append('user_id', this.userId);
    formData.append('exam_period_id', this.examPeriodId);
    formData.append('submission_id', this.submissionId);
    formData.append('image', blob, 'frame.jpg');
    
    const response = await fetch('http://localhost:8000/api/monitor', {
      method: 'POST',
      body: formData
    });
    
    const result = await response.json();
    
    if (result.status === 'violation_detected') {
      console.warn('Vi phạm:', result);
      this.handleViolation(result);
    }
  }

  handleViolation(violation) {
    // Hiển thị cảnh báo cho học sinh
    if (violation.severity === 'critical') {
      alert(`⚠️ Vi phạm: ${violation.violation_type}`);
    }
  }
}

// Sử dụng
const monitor = new ExamMonitor(userId, examPeriodId, submissionId);
monitor.startMonitoring();
```

## Query Violations

### Python
```python
from database.mysql_service import MySQLService

mysql = MySQLService()

# Lấy tất cả vi phạm của 1 bài thi
violations = mysql.get_violations_by_submission(submission_id=789)

for v in violations:
    print(f"Loại: {v['violation_type']}")
    print(f"Mức độ: {v['severity']}")
    print(f"Ảnh: {v['image_url']}")
```

### SQL
```sql
-- Tổng hợp vi phạm của học sinh
SELECT * FROM violation_summary 
WHERE submission_id = 789;

-- Danh sách vi phạm nghiêm trọng
SELECT * FROM violations 
WHERE severity = 'critical' 
AND exam_period_id = 456;

-- Học sinh có risk_score cao nhất
SELECT * FROM violation_summary 
WHERE exam_period_id = 456 
ORDER BY risk_score DESC 
LIMIT 10;
```

## Kiểm Tra API

### 1. Đăng ký học sinh
```bash
curl -X POST http://localhost:8000/api/students \
  -F "student_id=123" \
  -F "name=Nguyen Van A" \
  -F "class=10A1" \
  -F "image=@test_face.jpg"
```

### 2. Xác thực trước thi
```bash
curl -X POST http://localhost:8000/api/students/verify/before \
  -F "student_id=123" \
  -F "image=@webcam_capture.jpg"
```

### 3. Test giám sát
```bash
curl -X POST http://localhost:8000/api/monitor \
  -F "user_id=123" \
  -F "exam_period_id=456" \
  -F "submission_id=789" \
  -F "image=@test_violation.jpg"
```

## Troubleshooting

### S3 Upload lỗi
- Kiểm tra AWS credentials trong .env
- Verify bucket tồn tại: `aws s3 ls`
- Kiểm tra region đúng

### MySQL connection lỗi
- Kiểm tra MySQL đang chạy: `mysql.server status`
- Verify database tồn tại
- Kiểm tra username/password

### Không phát hiện vi phạm
- Kiểm tra models đã load: YOLOv8, InsightFace
- Verify face database có học sinh đã đăng ký
- Test với `/api/detect` endpoint trước
- Kiểm tra chất lượng ảnh

## Tối Ưu Performance

### Giảm băng thông
```javascript
// Nén ảnh trước khi gửi
canvas.toBlob(resolve, 'image/jpeg', 0.8);  // 80% quality

// Giảm resolution
const maxWidth = 640;
canvas.width = maxWidth;
canvas.height = (video.videoHeight * maxWidth) / video.videoWidth;
```

### Request rate
- Hiện tại: 1 request / 5 giây / học sinh
- 100 học sinh = ~20 req/sec
- Cân nhắc load balancing với kỳ thi lớn (500+ học sinh)

## Bảo Mật

1. **HTTPS bắt buộc** trong production
2. **JWT Authentication** cho tất cả endpoints
3. **Rate limiting** để tránh abuse
4. **Input validation** cho tất cả user input
5. **S3 private access** với presigned URLs
6. **CORS policy** chỉ cho phép domain frontend

## Các Bước Tiếp Theo

- [x] Cài đặt dependencies
- [x] Tạo database schema
- [x] Implement S3 service
- [x] Implement MySQL service
- [x] Tạo monitor endpoint
- [ ] Cấu hình .env với credentials thực tế
- [ ] Tạo S3 bucket
- [ ] Khởi tạo MySQL database
- [ ] Test monitoring endpoint
- [ ] Tích hợp với frontend
- [ ] Deploy với Gunicorn/Nginx
- [ ] Setup SSL certificate
- [ ] Cấu hình monitoring và logging

## Tài Liệu Chi Tiết

- **MONITOR_API_DOCS.md** - Documentation đầy đủ về monitoring API
- **VERIFY_API_EXAMPLES.md** - Ví dụ về API xác thực
- **database/schema.sql** - Database schema với comments

## Liên Hệ & Support

Nếu có vấn đề hoặc cần hỗ trợ, tham khảo:
1. Documentation files
2. Test setup script: `python test_setup.py`
3. Check logs trong terminal Flask server
