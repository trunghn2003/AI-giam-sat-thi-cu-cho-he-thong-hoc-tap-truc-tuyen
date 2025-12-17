# API Xác Thực Học Sinh Vào Thi

## 🎯 Mục đích

API này dùng để **xác thực danh tính học sinh** trước khi cho phép vào phòng thi. Hệ thống sẽ:
1. Kiểm tra student_id có tồn tại không
2. So sánh khuôn mặt trong ảnh với khuôn mặt đã đăng ký
3. Trả về kết quả xác thực (pass/fail)

## 📡 API Endpoint

### POST /api/students/verify

**Required Fields:**
- `student_id` (string): Mã số sinh viên cần xác thực
- `image`: Ảnh khuôn mặt học sinh (base64 hoặc file upload)

**Optional Fields:**
- `threshold` (float): Ngưỡng xác thực tùy chỉnh (0.0-1.0, mặc định 0.5)

---

## 📝 Ví dụ sử dụng

### 1. JSON với base64 image

```bash
curl -X POST http://localhost:8000/api/students/verify \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "SV001",
    "image": "'"$(base64 -i photo.jpg)"'"
  }'
```

### 2. Multipart form-data

```bash
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=SV001" \
  -F "image=@photo.jpg"
```

### 3. Với threshold tùy chỉnh

```bash
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=SV001" \
  -F "image=@photo.jpg" \
  -F "threshold=0.7"
```

---

## ✅ Response - Xác thực thành công (200)

```json
{
  "verified": true,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "matched_name": "Nguyen Van A",
  "confidence": 0.87,
  "threshold": 0.5,
  "message": "Identity verified: Nguyen Van A",
  "face_detected": true
}
```

**Giải thích:**
- `verified`: `true` = Xác thực thành công
- `confidence`: 0.87 = Độ tương đồng 87%
- `matched_name`: Khớp với "Nguyen Van A"
- HTTP Status: **200 OK**

---

## ❌ Response - Xác thực thất bại

### 1. Khuôn mặt không khớp (401)

```json
{
  "verified": false,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "matched_name": "Tran Thi B",
  "confidence": 0.72,
  "threshold": 0.5,
  "message": "Face matches 'Tran Thi B' instead of 'Nguyen Van A'",
  "face_detected": true
}
```

**Nguyên nhân:** Khuôn mặt trong ảnh là của người khác (Tran Thi B), không phải Nguyen Van A.

---

### 2. Độ tương đồng thấp (401)

```json
{
  "verified": false,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "matched_name": "Nguyen Van A",
  "confidence": 0.42,
  "threshold": 0.5,
  "message": "Similarity score 0.420 below threshold 0.500",
  "face_detected": true
}
```

**Nguyên nhân:** Khuôn mặt khớp với đúng người nhưng độ tương đồng quá thấp (có thể do ảnh mờ, góc chụp khác, ánh sáng xấu).

---

### 3. Không phát hiện khuôn mặt (401)

```json
{
  "verified": false,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "confidence": 0.0,
  "message": "No face detected in the provided image",
  "face_detected": false,
  "face_count": 0
}
```

**Nguyên nhân:** Không tìm thấy khuôn mặt trong ảnh gửi lên.

---

### 4. Multiple Faces Detected (401)

```json
{
  "verified": false,
  "student_id": "SV001",
  "name": "Nguyen Van A",
  "confidence": 0.0,
  "message": "Multiple faces detected (3 faces). Only one person allowed for verification",
  "face_detected": true,
  "face_count": 3
}
```

**Nguyên nhân:** Có nhiều hơn 1 người trong ảnh. Hệ thống chỉ chấp nhận ảnh có **đúng 1 khuôn mặt** để tránh gian lận (người khác đứng sau, người thế mạng).

**Giải pháp:** 
- Đảm bảo chỉ có 1 người trong frame khi chụp
- Không có người khác ở phía sau
- Tránh ảnh selfie nhóm

---

### 5. Student ID không tồn tại (401)

```json
{
  "verified": false,
  "student_id": "SV999",
  "name": null,
  "confidence": 0.0,
  "message": "Student ID 'SV999' not found in database",
  "face_detected": false
}
```

**Nguyên nhân:** Student ID chưa được đăng ký trong hệ thống.

---

### 6. Missing student_id (400)

```json
{
  "error": "Missing 'student_id' field"
}
```

---

### 7. Missing image (400)

```json
{
  "error": "Image is required for verification"
}
```

---

## 🔧 Tùy chỉnh threshold

### Threshold thấp (0.3-0.5): Dễ pass hơn
```bash
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=SV001" \
  -F "image=@photo.jpg" \
  -F "threshold=0.3"
```
- ✅ Chấp nhận ảnh chụp từ góc khác, ánh sáng xấu
- ⚠️ Tăng nguy cơ false positive (chấp nhận nhầm người)

### Threshold cao (0.7-0.9): Chặt chẽ hơn
```bash
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=SV001" \
  -F "image=@photo.jpg" \
  -F "threshold=0.8"
```
- ✅ Giảm false positive, chính xác hơn
- ⚠️ Có thể từ chối người đúng nếu ảnh không tốt

**Khuyến nghị:** 0.5-0.6 (default 0.5)

---

## 🐍 Python Example

```python
import requests
import base64

def verify_student(student_id: str, image_path: str, threshold: float = 0.5):
    """Verify student identity before exam entry."""
    
    # Read and encode image
    with open(image_path, 'rb') as f:
        image_base64 = base64.b64encode(f.read()).decode('utf-8')
    
    # Send verification request
    response = requests.post(
        'http://localhost:8000/api/students/verify',
        json={
            'student_id': student_id,
            'image': image_base64,
            'threshold': threshold
        }
    )
    
    result = response.json()
    
    if response.status_code == 200:
        print(f"✅ VERIFIED: {result['name']}")
        print(f"   Confidence: {result['confidence']:.2%}")
        return True
    else:
        print(f"❌ FAILED: {result['message']}")
        print(f"   Confidence: {result.get('confidence', 0):.2%}")
        return False

# Usage
if verify_student('SV001', 'student_photo.jpg'):
    print("Allow exam entry")
else:
    print("Deny exam entry")
```

---

## 🎯 Use Cases

### 1. Cổng vào phòng thi
```python
# Học sinh đưa thẻ sinh viên và chụp ảnh
student_id = scan_student_card()
photo = capture_webcam()

if verify_student(student_id, photo):
    open_door()
    log_entry(student_id)
else:
    alert_proctor("Identity verification failed")
```

### 2. Đăng nhập hệ thống thi online
```javascript
// Frontend
const stream = await navigator.mediaDevices.getUserMedia({ video: true });
const photo = captureFrame(stream);

const response = await fetch('/api/students/verify', {
  method: 'POST',
  body: JSON.stringify({
    student_id: studentId,
    image: photo.toBase64()
  })
});

if (response.ok) {
  startExam();
} else {
  showError("Identity verification failed");
}
```

### 3. Kiểm tra định kỳ trong thi
```python
# Chụp ảnh ngẫu nhiên mỗi 5 phút
import time

while exam_in_progress:
    time.sleep(300)  # 5 minutes
    photo = capture_webcam()
    
    if not verify_student(current_student_id, photo, threshold=0.4):
        flag_suspicious_activity()
        notify_proctor()
```

---

## 📊 Response Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200  | OK | Xác thực thành công, cho phép vào thi |
| 400  | Bad Request | Thiếu thông tin bắt buộc (student_id, image) |
| 401  | Unauthorized | Xác thực thất bại (wrong person, low similarity, no face) |
| 500  | Internal Server Error | Lỗi server |

---

## ⚠️ Lưu ý quan trọng

### 1. Chất lượng ảnh
- ✅ Sử dụng ảnh rõ nét, ánh sáng tốt
- ✅ Khuôn mặt nhìn thẳng camera
- ✅ Không đeo khẩu trang, kính đen
- ❌ Tránh ảnh mờ, tối, góc nghiêng quá nhiều

### 2. Security
- Threshold quá thấp → Dễ bị giả mạo
- Threshold quá cao → Từ chối người đúng
- **Khuyến nghị:** 0.5-0.6 cho production

### 3. Performance
- Mỗi request mất ~100-300ms
- Có thể cache kết quả trong session
- Dùng rate limiting để tránh brute force

### 4. Multiple faces
- Nếu ảnh có nhiều khuôn mặt → Dùng face đầu tiên
- Warning sẽ được log
- Khuyến nghị: Đảm bảo chỉ có 1 người trong frame

---

## 🔄 Workflow hoàn chỉnh

```
1. Học sinh đăng ký
   POST /api/students/register
   ↓
2. Học sinh đến thi
   - Đưa thẻ SV
   - Chụp ảnh
   ↓
3. Xác thực
   POST /api/students/verify
   ↓
4a. verified=true (200)
    → Cho vào thi
    → Bắt đầu monitoring với /api/detect
    
4b. verified=false (401)
    → Từ chối
    → Log sự cố
    → Thông báo giám thị
```

---

## 🧪 Testing

```bash
# 1. Đăng ký học sinh test
curl -X POST http://localhost:8000/api/students/register \
  -F "name=Test Student" \
  -F "student_id=TEST001" \
  -F "email=test@example.com" \
  -F "images=@test1.jpg" \
  -F "images=@test2.jpg" \
  -F "images=@test3.jpg"

# 2. Verify với ảnh đúng
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=TEST001" \
  -F "image=@test1.jpg"
# → Expect: verified=true

# 3. Verify với ảnh sai
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=TEST001" \
  -F "image=@other_person.jpg"
# → Expect: verified=false

# 4. Verify với student_id không tồn tại
curl -X POST http://localhost:8000/api/students/verify \
  -F "student_id=NOTEXIST" \
  -F "image=@test1.jpg"
# → Expect: error message
```

---

## 📚 Integration với Frontend

### HTML Form Example

```html
<form id="verifyForm">
  <label>Mã sinh viên:</label>
  <input type="text" id="studentId" required>
  
  <label>Chụp ảnh:</label>
  <video id="video" autoplay></video>
  <canvas id="canvas" style="display:none"></canvas>
  
  <button type="button" onclick="captureAndVerify()">
    Xác thực
  </button>
  
  <div id="result"></div>
</form>

<script>
async function captureAndVerify() {
  const studentId = document.getElementById('studentId').value;
  const video = document.getElementById('video');
  const canvas = document.getElementById('canvas');
  
  // Capture frame
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  canvas.getContext('2d').drawImage(video, 0, 0);
  const imageData = canvas.toDataURL('image/jpeg').split(',')[1];
  
  // Send to API
  const response = await fetch('/api/students/verify', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      student_id: studentId,
      image: imageData
    })
  });
  
  const result = await response.json();
  const resultDiv = document.getElementById('result');
  
  if (result.verified) {
    resultDiv.innerHTML = `
      <div class="success">
        ✅ Xác thực thành công!<br>
        Sinh viên: ${result.name}<br>
        Độ tin cậy: ${(result.confidence * 100).toFixed(1)}%
      </div>
    `;
    // Redirect to exam
    setTimeout(() => window.location.href = '/exam', 2000);
  } else {
    resultDiv.innerHTML = `
      <div class="error">
        ❌ Xác thực thất bại<br>
        ${result.message}
      </div>
    `;
  }
}

// Start webcam
navigator.mediaDevices.getUserMedia({ video: true })
  .then(stream => {
    document.getElementById('video').srcObject = stream;
  });
</script>
```

---

## 📞 Support

Nếu có vấn đề:
1. Kiểm tra server đang chạy: `curl http://localhost:8000/health`
2. Kiểm tra student_id đã đăng ký: `curl http://localhost:8000/api/students`
3. Thử với threshold thấp hơn
4. Kiểm tra chất lượng ảnh

---

**Thời gian:** Mỗi verification ~100-300ms  
**Độ chính xác:** ~95-98% với ảnh chất lượng tốt  
**Khuyến nghị threshold:** 0.5-0.6
