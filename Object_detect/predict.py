from ultralytics import YOLO
import cv2

model = YOLO(model="yolov8s-oiv7.pt")

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Lỗi mở webcam")
    exit()

# Thêm dòng này để set độ phân giải (giúp nhiều máy fix xanh)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

print("Webcam đã mở – Nhấn 'q' để thoát")

while True:
    ret, frame = cap.read()
    if not ret:
        print("Lỗi đọc frame")
        break

    # Fix xanh lè trên một số máy: flip frame
    frame = cv2.flip(frame, 1)  # lật ngang (mirror)

    # Predict
    results = model(frame, conf=0.3, verbose=False)[0]
    annotated_frame = results.plot()

    cv2.imshow("Phát hiện điện thoại & tai nghe", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()