from ultralytics import YOLO
import cv2

# Load model đã train
model = YOLO("best.pt")  # đặt file best.pt cùng folder hoặc sửa đường dẫn đầy đủ

# Test 1 ảnh
results = model("IMG_1655.jpg", conf=0.3)[0]  # thay "test.jpg" bằng ảnh của bạn

# Vẽ kết quả
annotated = results.plot()  # tự động vẽ bounding box + label + confidence

# Lưu ảnh kết quả
cv2.imwrite("ket_qua.jpg", annotated)
print("Đã lưu kết quả vào ket_qua.jpg")

# Hiển thị (nếu muốn xem ngay)
cv2.imshow("Ket qua", annotated)
cv2.waitKey(0)
cv2.destroyAllWindows()