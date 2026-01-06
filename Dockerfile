# Sử dụng Python 3.10 slim image để tối ưu kích thước
FROM python:3.10-slim

# Thiết lập thư mục làm việc
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết cho OpenCV và InsightFace
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1 \
    libgl1-mesa-dri \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Copy file requirements.txt vào container
COPY requirements.txt .

# Cài đặt các thư viện Python
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ source code vào container
COPY . .

# Tạo thư mục cho models InsightFace nếu cần (tùy chọn)
# RUN mkdir -p /root/.insightface/models

# Expose port 8001 (port mặc định của app)
EXPOSE 8001

# Lệnh chạy ứng dụng
CMD ["python", "app.py"]
