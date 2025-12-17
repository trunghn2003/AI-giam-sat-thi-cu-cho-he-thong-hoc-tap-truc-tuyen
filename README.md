# Cheating Detection Service

This project combines face recognition, head pose estimation, and suspicious object detection into a single Flask-based service. It builds on the training artefacts present in the repository.

## Technologies Used

### Core AI/ML Technologies

#### 1. **InsightFace**

- **Purpose**: Face recognition, face detection, and head pose estimation
- **Key Features**:
  - High-accuracy face embedding extraction using ArcFace/CosFace models
  - Real-time face detection with MTCNN and RetinaFace
  - 3D head pose estimation (yaw, pitch, roll angles)
  - Anti-spoofing capabilities for liveness detection
- **Models**: Uses buffalo_l model for balanced speed and accuracy
- **Installation**: `pip install insightface`

#### 2. **YOLOv8 (Ultralytics)**

- **Purpose**: Suspicious object detection (earphones, cellphones, headphones)
- **Key Features**:
  - Real-time object detection and localization
  - Custom trained on cheating-related objects
  - High performance with configurable confidence thresholds
- **Custom Classes**:
  - Class 0: Cellphone
  - Class 1: Earphone
  - Class 2: Headphone
- **Installation**: `pip install ultralytics`

#### 3. **OpenCV (cv2)**

- **Purpose**: Image processing and computer vision utilities
- **Key Features**:
  - Image loading, resizing, and format conversion
  - Real-time video capture and processing
  - Drawing bounding boxes and annotations
  - Color space conversions (BGR/RGB)
- **Installation**: `pip install opencv-python`

### Backend Technologies

#### 4. **Flask**

- **Purpose**: Web framework for API services
- **Key Features**:
  - RESTful API endpoints for detection and face registration
  - File upload handling (multipart/form-data and base64)
  - JSON response formatting
  - CORS support for web integration
- **Installation**: `pip install flask flask-cors`

#### 5. **NumPy**

- **Purpose**: Numerical computing and array operations
- **Key Features**:
  - Face embedding storage and similarity calculations
  - Image array manipulation
  - Mathematical operations for pose classification
- **Installation**: `pip install numpy`

### Data Management

#### 6. **Roboflow**

- **Purpose**: Dataset management and preparation
- **Key Features**:
  - Automated dataset downloading
  - Format conversion for YOLO training
  - Data augmentation and preprocessing
- **Installation**: `pip install roboflow`

#### 7. **PyTorch**

- **Purpose**: Deep learning framework (backend for InsightFace)
- **Key Features**:
  - Model inference and GPU acceleration
  - Tensor operations for embeddings
- **Installation**: `pip install torch torchvision`

### Development Tools

#### 8. **Jupyter Notebook**

- **Purpose**: Interactive development and experimentation
- **Key Features**:
  - Model training and testing workflows
  - Data visualization and analysis
  - Prototype development
- **Installation**: `pip install jupyter`

## System Architecture

```text
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Camera/Image  │───▶│   Flask API      │───▶│   AI Models     │
│     Input       │    │                  │    │                 │
└─────────────────┘    │  - File Upload   │    │ - InsightFace   │
                       │  - Base64 Handle │    │ - YOLOv8        │
                       │  - Response JSON │    │ - OpenCV        │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   Face Database  │
                       │   (Embeddings)   │
                       └──────────────────┘
```

## Model Performance

- **Face Recognition**: ~99% accuracy on LFW dataset
- **Object Detection**: Custom trained on 3 classes with mAP@0.5 > 0.85
- **Head Pose**: ±15° accuracy for yaw/pitch/roll estimation
- **Processing Speed**: ~30-50 FPS on CPU, ~100+ FPS on GPU

## Hardware Requirements

- **Minimum**: 4GB RAM, Intel i5 or equivalent
- **Recommended**: 8GB RAM, GPU with 4GB VRAM
- **Optimal**: 16GB RAM, NVIDIA RTX 3060 or better

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The API listens on port 8000 by default.

### Health check

```bash
curl http://localhost:8000/health
```

### Run detection

Upload an image via multipart form-data:

```bash
curl -X POST http://localhost:8000/api/detect \
  -F "file=@/path/to/exam-frame.jpg"
```

Or with a base64-encoded JSON payload:

```bash
curl -X POST http://localhost:8000/api/detect \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "<base64-image>"}'
```

Include the annotated frame in the response as base64 by setting `return_image=true`:

```bash
curl -X POST "http://localhost:8000/api/detect?return_image=true" \
  -F "file=@/path/to/exam-frame.jpg"
```

### Add a face to the database

Register a new identity with one or more images:

```bash
curl -X POST http://localhost:8000/api/faces \
  -F "name=student_01" \
  -F "images=@/path/to/student_01_a.jpg" \
  -F "images=@/path/to/student_01_b.jpg"
```

Or using JSON with base64-encoded images:

```bash
curl -X POST http://localhost:8000/api/faces \
  -H "Content-Type: application/json" \
  -d '{
        "name": "student_01",
        "images": ["<base64-a>", "<base64-b>"]
      }'
```

The service stores the mean embedding similarly to the original `Face_Database_Training.ipynb` workflow.

### Live camera client

Launch the helper script to stream from the default webcam and show annotated frames (press `q` to quit):

```bash
python camera_client.py
```

## Output structure

Responses include recognised faces, detected suspicious objects, coarse head pose classification, and a high-level status (`clear` or `attention`).
