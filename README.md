# ĐỒ ÁN TỐT NGHIỆP

## Giảng viên hướng dẫn: PGS.TS. Trần Đình Quế

## Giảng viên phản biện: TS. Đỗ Tiến Dũng

# Tên đề tài: Hệ thống học tập trực tuyến trên nền tảng web và ứng dụng di động
# Repo: Hệ thống Phát hiện Gian lận trong Thi cử sử dụng AI

## Thành viên nhóm:

### Hoàng Việt Trung - B21DCCN729

### Ngô Thế Quang Tiến - B21DCCN705

### Phạm Huy Hòa - B21DCCN381

### Trương Công Tuấn Thành - B21DCCN681

## Mục lục

- [Giới thiệu](#giới-thiệu)
- [Công nghệ sử dụng](#công-nghệ-sử-dụng)
- [Kiến trúc tổng quan](#kiến-trúc-tổng-quan)
- [Cài đặt & Khởi chạy](#cài-đặt--khởi-chạy)
- [Tính năng chính](#tính-năng-chính)
- [API Endpoints](#api-endpoints)
- [Chi tiết kỹ thuật](#chi-tiết-kỹ-thuật)
---

## Giới thiệu

**Hệ thống Phát hiện Gian lận trong Thi cử** là một ứng dụng AI sử dụng Computer Vision để giám sát và phát hiện hành vi gian lận trong các kỳ thi trực tuyến. Hệ thống phân tích khuôn mặt, tư thế đầu, hướng nhìn mắt và phát hiện vật thể khả nghi theo thời gian thực, giúp đảm bảo tính công bằng và minh bạch trong quá trình thi cử.

**Các loại vi phạm phát hiện được:**

- **Vi phạm nghiêm trọng (Critical):**
  - Nhiều khuôn mặt trong khung hình
  - Không phát hiện khuôn mặt (rời khỏi vị trí)
  - Người lạ (chưa đăng ký) làm bài thay
  - Phát hiện vật dụng khả nghi (điện thoại, tai nghe)

- **Vi phạm trung bình (Medium):**
  - Mắt nhìn lên/xuống/trái/phải (nhìn chỗ khác)
  - Đầu quay, ngẩng, cúi bất thường

---

## Công nghệ sử dụng

### Backend Framework
- **Python 3.8+** - Ngôn ngữ lập trình chính
- **Flask** - REST API server
- **MySQL 8.0+** - Lưu trữ vi phạm và thông tin sinh viên
- **AWS S3 / Cloudflare R2** - Lưu trữ ảnh vi phạm

### AI/ML Models
- **InsightFace** - Face Detection & Recognition (ArcFace Loss)
- **MediaPipe Face Mesh** - Eye Gaze Tracking (478 landmarks + iris)
- **YOLOv8** - Object Detection (Ultralytics)
- **OpenCV** - Image processing

### Database & Storage
- **Pickle** - Face embeddings database
- **PyMySQL** - MySQL connector
- **Boto3** - AWS S3 SDK

### Dependencies chính
```
insightface
mediapipe
ultralytics
opencv-python
numpy
flask
pymysql
boto3
```

---

## Kiến trúc tổng quan

### 1. **Luồng xử lý chính**

```
Frontend (Webcam) → Flask API → Detection Pipeline → Database
                                       ↓
                           ┌───────────┴───────────┐
                           ↓                       ↓
                    Face Recognition        Object Detection
                           ↓                       ↓
                    Head Pose Analysis      YOLO Model
                           ↓
                    Eye Gaze Tracking
                           ↓
                    Violation Classification
                           ↓
                    Save to MySQL + S3
```

### 2. **Các module chính**

**Detection Pipeline (`cheating_detection/pipeline.py`)**
- Điều phối tất cả các module AI
- Tổng hợp kết quả và tạo flags vi phạm
- Vẽ annotations lên ảnh

**Face Recognition (`cheating_detection/face_recognition.py`)**
- Detect faces với InsightFace
- Extract 512-dim embeddings
- So sánh với database bằng cosine similarity

**Head Pose Analysis (`cheating_detection/head_pose.py`)**
- Phân tích Euler angles (yaw, pitch, roll)
- Phân loại hướng đầu (trái, phải, lên, xuống)

**Eye Gaze Tracking (`cheating_detection/gaze.py`)**
- Detect 478 face landmarks với MediaPipe
- Tính vị trí iris để xác định hướng nhìn

**Object Detection (`cheating_detection/object_detection.py`)**
- Detect vật thể với YOLOv8
- Filter watched classes (phone, book, laptop)

### 3. **Database Schema**

**Table: `violations`**
```sql
- id, exam_period_id, submission_id, user_id
- violation_type, severity, confidence
- image_url, image_key, detection_data (JSON)
- detected_at, created_at
```

**Table: `violation_summary`**
```sql
- submission_id, user_id, exam_period_id
- total_violations, critical_count, high_count, medium_count, low_count
- first_violation_at, last_violation_at, risk_score
```

---

## Cài đặt & Khởi chạy

### Yêu cầu hệ thống

- Python 3.8+
- MySQL 8.0+
- 4GB RAM (8GB khuyến nghị)
- GPU (optional, tăng tốc inference)

### Các bước cài đặt

1. **Clone repository:**

   ```bash
   git clone https://github.com/trunghn2003/doancheating.git
   cd doancheating
   ```

2. **Tạo virtual environment:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # hoặc
   venv\Scripts\activate  # Windows
   ```

3. **Cài đặt dependencies:**

   ```bash
   pip install -r requirements.txt
   ```


4. **Cấu hình environment variables:**

   Tạo file `.env` trong thư mục gốc:
   
   ```env
   # MySQL Configuration
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=exam_monitoring
   
   # S3/R2 Configuration
   S3_BUCKET_NAME=exam-violations
   S3_REGION=ap-southeast-1
   S3_ACCESS_KEY=your_access_key
   S3_SECRET_KEY=your_secret_key
   S3_ENDPOINT_URL=https://xxx.r2.cloudflarestorage.com  # Optional (Cloudflare R2)
   S3_PUBLIC_URL=https://violations.example.com  # Optional (Cloudflare R2)
   ```

5. **Download AI models:**

   ```bash
   # InsightFace models sẽ tự động download khi chạy lần đầu
   
   # YOLOv8 model - đặt file best.pt vào thư mục Object_detect/
   # Download từ Google Drive hoặc train custom model
   ```

6. **Khởi động server:**

   ```bash
   python app.py
   # Server sẽ chạy tại: http://localhost:8001
   ```

---


## Tính năng chính

### 1. **Đăng ký sinh viên** (`POST /api/students/register`)

**Mô tả:** Đăng ký khuôn mặt sinh viên vào hệ thống

**Request:**
```bash
curl -X POST http://localhost:8001/api/students/register \
  -F "name=Nguyen Van A" \
  -F "student_id=SV001" \
  -F "email=a@email.com" \
  -F "images=@photo1.jpg" \
  -F "images=@photo2.jpg" \
  -F "images=@photo3.jpg"
```

**Response:**
```json
{
  "name": "Nguyen Van A",
  "student_id": "SV001",
  "email": "a@email.com",
  "processed_images": 3,
  "faces_detected": 3,
  "embeddings_used": 3,
  "total_students": 42
}
```

**Quy trình:**
1. Upload ít nhất 3 ảnh khuôn mặt
2. InsightFace detect faces và extract embeddings (512-dim)
3. Tính mean embedding từ tất cả ảnh
4. Lưu vào `face_database_kaggle.pkl`

---

### 2. **Xác thực trước thi** (`POST /api/students/verify/before`)

**Mô tả:** Xác thực danh tính sinh viên trước khi vào phòng thi

**Request:**
```bash
curl -X POST http://localhost:8001/api/students/verify/before \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "SV001",
    "image_base64": "base64_encoded_image",
    "threshold": 0.5
  }'
```

**Response (thành công):**
```json
{
  "verified": true,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "matched_name": "Nguyen Van A",
  "confidence": 0.85,
  "threshold": 0.5,
  "message": "Identity verified: Nguyen Van A"
}
```

**Response (thất bại):**
```json
{
  "verified": false,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "matched_name": "Nguyen Van B",
  "confidence": 0.65,
  "message": "Face matches 'Nguyen Van B' instead of 'Nguyen Van A'"
}
```

---

### 3. **Giám sát thi** (`POST /api/monitor`)

**Mô tả:** Giám sát sinh viên trong khi thi (gọi mỗi 5 giây từ frontend)

**Request:**
```json
{
  "student_id": "SV001",
  "exam_period_id": 123,
  "submission_id": 456,
  "image_base64": "base64_encoded_image"
}
```

**Response (có vi phạm):**
```json
{
  "status": "violation_detected",
  "violation_id": 789,
  "student_id": "SV001",
  "violation_type": "Mắt nhìn trái",
  "severity": "medium",
  "confidence": 0.85,
  "flags": [
    "Gaze Looking Left detected for Nguyen Van A"
  ],
  "image_url": "https://s3.../violations/exam_123/submission_456/user_789/violation_20260107_143022.jpg",
  "detected_at": "2026-01-07T14:30:22"
}
```

**Response (không vi phạm):**
```json
{
  "status": "clear",
  "student_id": "SV001",
  "message": "No violations detected"
}
```

**Quy trình:**
1. Frontend gửi ảnh webcam + thông tin sinh viên
2. Hệ thống chạy detection pipeline:
   - Face Recognition: Nhận diện sinh viên
   - Head Pose: Phân tích hướng đầu
   - Eye Gaze: Phân tích hướng nhìn mắt
   - Object Detection: Phát hiện vật dụng
3. Tổng hợp flags vi phạm
4. Nếu có vi phạm:
   - Upload ảnh lên S3/R2
   - Lưu vào MySQL (tables: violations, violation_summary)
5. Trả về kết quả cho frontend

---

### 4. **Quản lý sinh viên**

**Xem danh sách:** `GET /api/students`
```json
{
  "total": 42,
  "students": [
    {
      "name": "Nguyen Van A",
      "student_id": "SV001",
      "email": "a@email.com",
      "registration_date": "2026-01-07T10:00:00"
    }
  ]
}
```

**Xem thông tin:** `GET /api/students/SV001`

**Xóa sinh viên:** `DELETE /api/students/SV001`

---

## API Endpoints

| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/health` | Health check |
| POST | `/api/detect` | Phát hiện vi phạm (single image) |
| POST | `/api/monitor` | Giám sát thi (với lưu trữ) |
| POST | `/api/students/register` | Đăng ký sinh viên mới |
| POST | `/api/students/verify/before` | Xác thực trước thi |
| GET | `/api/students` | Lấy danh sách sinh viên |
| GET | `/api/students/<id>` | Lấy thông tin sinh viên |
| DELETE | `/api/students/<id>` | Xóa sinh viên |

---

## Chi tiết kỹ thuật

### 1. **Face Recognition (InsightFace + ArcFace)**

**Kiến trúc CNN:**
```
Input (112x112x3) → Conv Layers → ResNet Blocks → 
Global Average Pooling (7x7x2048 → 2048) → 
FC Layer (2048 → 512) → L2 Normalize → 
512-dim Embedding
```

**ArcFace Loss Function:**
```
L = -log(e^(s·cos(θ + m)) / (e^(s·cos(θ + m)) + Σe^(s·cos(θⱼ))))

- θ: góc giữa embedding và weight của class đúng
- m: angular margin (0.5 rad ≈ 28.6°)
- s: scale factor (64)
```


**File storage:** `Face_Recognition_Training/models/face_database_kaggle.pkl`

---

### 2. **Head Pose Analysis**

**Euler Angles:**
- **Yaw**: Quay trái/phải (-180° đến 180°)
- **Pitch**: Ngẩng/cúi (-90° đến 90°)
- **Roll**: Nghiêng trái/phải (-180° đến 180°)

**Thresholds:**
```python
{
    "yaw": 20.0,    # độ
    "pitch": 20.0,  # độ
    "roll": 20.0    # độ
}
```

**Classification:**
- `yaw <= -20°` → "Looking Left"
- `yaw >= 20°` → "Looking Right"
- `pitch >= 20°` → "Looking Up"
- `pitch <= -20°` → "Looking Down"
- Còn lại → "Straight"

---

### 3. **Eye Gaze Tracking (MediaPipe)**

**Face Mesh Landmarks:** 478 điểm 3D + 10 điểm iris

**Iris & Eye Landmarks:**
```python
LEFT_IRIS = (468, 469, 470, 471)
RIGHT_IRIS = (473, 474, 475, 476)
LEFT_EYE_CORNERS = (33, 133)
RIGHT_EYE_CORNERS = (362, 263)
LEFT_EYE_LIDS = (159, 145)
RIGHT_EYE_LIDS = (386, 374)
```

**Horizontal Ratio:**
```python
horizontal_ratio = (iris_center_x - left_corner_x) / (right_corner_x - left_corner_x)

# 0.0 → Nhìn trái
# 0.5 → Nhìn giữa
# 1.0 → Nhìn phải
```

**Thresholds:**
- `< 0.35` → "Looking Left"
- `> 0.65` → "Looking Right"
- `0.35-0.65` → "Center"

---

### 4. **Object Detection (YOLOv8)**

**Model:** Custom trained `best.pt` trên dataset vật dụng gian lận

**Architecture:**
```
Input (640x640) → Backbone (CSPDarknet) → 
Neck (PAN) → Head (Decoupled) → 
NMS → Detections
```

**Watched Classes:**
- cell phone
- ear phone

**Confidence threshold:** 0.5

---