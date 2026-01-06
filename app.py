"""
Flask entry-point exposing the cheating detection pipeline as a REST API.
"""

from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import cv2
import numpy as np
from flask import Flask, jsonify, request, url_for

from cheating_detection import annotate_detections, load_default_pipeline
from cheating_detection.utils import (
    decode_image_from_base64,
    decode_image_from_bytes,
)
from database import mysql_service, s3_service


def convert_numpy_to_json_serializable(obj):
    """Recursively convert numpy arrays to lists for JSON serialization."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy_to_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_numpy_to_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating)):
        return obj.item()
    else:
        return obj

LOGGER = logging.getLogger(__name__)

app = Flask(__name__)
PIPELINE = load_default_pipeline()
ANNOTATED_DIR = Path(app.static_folder) / "annotated"
ANNOTATED_DIR.mkdir(parents=True, exist_ok=True)


@app.route("/health", methods=["GET"])
def health() -> Any:
    return jsonify({"status": "ok"})


@app.route("/api/detect", methods=["POST"])
def detect() -> Any:

    payload = request.get_json(silent=True) if request.is_json else None
    try:
        image = _extract_image_payload(payload)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    try:
        result = PIPELINE.analyze(image)
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("Cheating detection failed")
        return jsonify({"error": "Internal detection failure"}), 500

    try:
        annotated = annotate_detections(image, result)
        filename = _persist_annotated_image(annotated)
        result["annotated_image_url"] = url_for(
            "static", filename=f"annotated/{filename}", _external=True
        )
    except ValueError as exc:
        LOGGER.warning("Failed to persist annotated image: %s", exc)
    return convert_numpy_to_json_serializable(result)


def _extract_image_payload(payload: Dict[str, Any] | None = None):
    """
    Attempt to load an image from the incoming request.
    """
    if request.files:
        file_storage = request.files.get("file")
        if not file_storage or not file_storage.filename:
            raise ValueError("Missing uploaded file")
        return decode_image_from_bytes(file_storage.read())

    if payload is None and request.is_json:
        payload = request.get_json() or {}
    if payload:
        if "image_base64" in payload:
            return decode_image_from_base64(payload["image_base64"])
        if "image_bytes" in payload:
            return decode_image_from_base64(payload["image_bytes"])

    raise ValueError(
        "Unsupported request payload. Provide 'file' via form-data "
        "or 'image_base64' within a JSON body."
    )


@app.route("/api/monitor", methods=["POST"])
def monitor_exam() -> Any:
    """
    Monitor student during exam - called every 5 seconds from frontend.
    Detects violations and saves to S3 + MySQL if any.
    
    Required fields:
    - student_id: Student ID (mã học sinh)
    - exam_period_id: Exam period ID (bigint) 
    - submission_id: Exam submission ID (bigint)
    - image: Photo of student (base64 or multipart)
    
    Returns:
        Detection result with violation status
    """
    try:
        # Extract required fields
        student_id = _extract_field("student_id", required=True, field_type=str)
        exam_period_id = _extract_field("exam_period_id", required=True, field_type=int)
        submission_id = _extract_field("submission_id", required=True, field_type=int)
        
        # Query MySQL to get user_id from users table where employee_code = student_id
        try:
            conn = mysql_service._get_connection()
            cursor = conn.cursor()
            
            cursor.execute( 
                "SELECT id FROM users WHERE employee_code = %s LIMIT 1",
                (student_id,)
            )
            result = cursor.fetchone()
            cursor.close()
            
            if not result:
                return jsonify({
                    "error": f"Học sinh với mã '{student_id}' không tìm thấy"
                }), 404
            
            user_id = result['id']
            LOGGER.info(f"Found user_id {user_id} for student_id '{student_id}'")
            
        except Exception as e:
            LOGGER.error(f"Failed to lookup user_id for student_id '{student_id}': {e}")
            return jsonify({"error": "Database error while looking up student"}), 500
                
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    
    # Extract image
    images = _extract_images()
    if not images:
        return jsonify({"error": "Image is required for monitoring"}), 400
    
    image = images[0]
    
    try:
        # Run detection pipeline
        result = PIPELINE.analyze(image)
        detected_at = datetime.now()
        
        # Check if there are any violations
        has_violation = result.get("status") != "clear"
        flags = result.get("flags", [])
        
        if has_violation and flags:
            # Determine violation type and severity
            violation_type, severity = _classify_violation(result, flags)
            
            # Calculate confidence (average from detection results)
            confidence = _calculate_confidence(result)
            
            # Get annotated image (with bounding boxes, landmarks, gaze arrows)
            annotated_image = result.get("annotated_image", image)
            
            # Upload annotated image to S3 (only if violation)
            image_url, image_key = s3_service.upload_violation_image(
                image_bgr=annotated_image,
                exam_period_id=exam_period_id,
                submission_id=submission_id,
                user_id=user_id,
                violation_type=violation_type
            )
            print(f"Uploaded violation image to S3: {image_url} (key: {image_key})")
            
            # Remove annotated_image and convert numpy arrays to lists
            detection_data = {k: v for k, v in result.items() if k != "annotated_image"}
            detection_data = convert_numpy_to_json_serializable(detection_data)
            
            # Save violation to MySQL
            violation_id = mysql_service.insert_violation(
                exam_period_id=exam_period_id,
                submission_id=submission_id,
                user_id=user_id,
                violation_type=violation_type,
                severity=severity,
                confidence=confidence,
                image_url=image_url,
                image_key=image_key,
                detection_data=detection_data,
                detected_at=detected_at
            )
            
            # Update violation summary
            if violation_id:
                mysql_service.update_violation_summary(
                    submission_id=submission_id,
                    user_id=user_id,
                    exam_period_id=exam_period_id,
                    severity=severity,
                    detected_at=detected_at
                )
            
            # Prepare response (remove annotated_image and convert numpy)
            response_result = {k: v for k, v in result.items() if k != "annotated_image"}
            response_result = convert_numpy_to_json_serializable(response_result)
            
            return jsonify({
                "status": "violation_detected",
                "violation_id": violation_id,
                "student_id": student_id,
                "violation_type": violation_type,
                "severity": severity,
                "confidence": confidence,
                "flags": flags,
                "image_url": image_url,
                "detected_at": detected_at.isoformat(),
                "detection_result": response_result
            }), 200
        else:
            # No violation - return success without saving
            response_result = {k: v for k, v in result.items() if k != "annotated_image"}
            response_result = convert_numpy_to_json_serializable(response_result)
            
            return jsonify({
                "student_id": student_id,
                "status": "clear",
                "message": "No violations detected",
                "detection_result": response_result
            }), 200
            
    except Exception as exc:  # pragma: no cover - defensive
        LOGGER.exception("Monitoring failed")
        return jsonify({"error": "Internal error during monitoring"}), 500


@app.route("/api/students/register", methods=["POST"])
def register_student() -> Any:
    """
    Register a new student in the face recognition database.
    
    Required fields:
    - name: Student's full name
    - student_id: Student ID number (unique)
    - images: List of face images (at least 3 recommended)
    
    Optional fields:
    - email: Student's email address
    """
    try:
        # Extract and validate student info
        name = _extract_name()
        student_id = _extract_student_id()
        email = _extract_email()  # Optional
        
        # Check if student_id already exists
        existing_name = PIPELINE.face_recognizer.database.find_by_student_id(student_id)
        if existing_name:
            return jsonify({
                "error": f"Học sinh có mã '{student_id}' đã được đăng ký với tên '{existing_name}'"
            }), 400
        
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    
    images = _extract_images()
    if not images:
        return jsonify({"error": "Yêu cầu tải lên ít nhất 1 ảnh"}), 400
    
    if len(images) < 3:
       return jsonify({"error": "Yêu cầu tải lên ít nhất 3 ảnh"}), 400


    try:
        summary = PIPELINE.face_recognizer.add_person(
            name, 
            images,
            student_id=student_id,
            email=email
        )
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to register student")
        return jsonify({"error": "Lỗi khi thêm học sinh"}), 500

    summary["student_id"] = student_id
    summary["email"] = email
    summary["total_students"] = len(PIPELINE.face_recognizer.database.people)
    return jsonify(summary), 201


@app.route("/api/students", methods=["GET"])
def get_all_students() -> Any:
    """
    Get list of all registered students.
    
    Returns:
        List of students with their metadata (name, student_id, email, registration_date)
    """
    try:
        students = PIPELINE.face_recognizer.database.get_all_students()
        return jsonify({
            "total": len(students),
            "students": students
        }), 200
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to retrieve students")
        return jsonify({"error": "Internal error while retrieving students"}), 500


@app.route("/api/students/<string:identifier>", methods=["DELETE"])
def delete_student(identifier: str) -> Any:
    """
    Delete a student from the database.
    
    Args:
        identifier: Can be either student name or student_id
    
    Returns:
        Success message or error
    """
    try:
        # Try to find by student_id first
        name = PIPELINE.face_recognizer.database.find_by_student_id(identifier)
        if not name:
            # If not found, treat identifier as name
            name = identifier
        
        success = PIPELINE.face_recognizer.database.delete_person(name)
        if not success:
            return jsonify({"error": f"Student '{identifier}' not found"}), 404
        
        return jsonify({
            "message": f"Student '{name}' deleted successfully",
            "total_students": len(PIPELINE.face_recognizer.database.people)
        }), 200
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to delete student")
        return jsonify({"error": "Internal error while deleting student"}), 500


@app.route("/api/students/<string:identifier>", methods=["GET"])
def get_student_info(identifier: str) -> Any:
    """
    Get information about a specific student.
    
    Args:
        identifier: Can be either student name or student_id
    
    Returns:
        Student information including metadata
    """
    try:
        # Try to find by student_id first
        name = PIPELINE.face_recognizer.database.find_by_student_id(identifier)
        if not name:
            # If not found, treat identifier as name
            name = identifier
        
        if not PIPELINE.face_recognizer.database.has_person(name):
            return jsonify({"error": f"Student '{identifier}' not found"}), 404
        
        metadata = PIPELINE.face_recognizer.database.get_student_info(name)
        return jsonify({
            "name": name,
            **metadata
        }), 200
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to retrieve student info")
        return jsonify({"error": "Internal error while retrieving student info"}), 500


@app.route("/api/students/verify/before", methods=["POST"])
def verify_student() -> Any:
    """
    Verify student identity before allowing exam entry.
    
    Required fields:
    - student_id: Student ID number to verify
    - image: Photo of the student (base64 or multipart)
    
    Optional fields:
    - threshold: Custom verification threshold (0.0-1.0)
    
    Returns:
        {
            "verified": true/false,
            "student_id": "SV001",
            "name": "Student Name",
            "confidence": 0.85,
            "message": "Identity verified"
        }
    """
    try:
        student_id = _extract_student_id()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    
    # Extract optional threshold
    threshold = None
    if request.is_json:
        payload = request.get_json() or {}
        threshold = payload.get("threshold")
    elif request.form:
        threshold_str = request.form.get("threshold")
        if threshold_str:
            try:
                threshold = float(threshold_str)
            except ValueError:
                return jsonify({"error": "Invalid threshold value"}), 400
    
    # Validate threshold range
    if threshold is not None and (threshold < 0.0 or threshold > 1.0):
        return jsonify({"error": "Threshold must be between 0.0 and 1.0"}), 400
    
    # Extract image
    images = _extract_images()
    if not images:
        return jsonify({"error": "Image is required for verification"}), 400
    
    if len(images) > 1:
        LOGGER.warning("Multiple images provided for verification. Using the first one.")
    
    image = images[0]
    
    try:
        result = PIPELINE.face_recognizer.verify_student(
            student_id=student_id,
            image_bgr=image,
            verification_threshold=threshold
        )
        
        # Return appropriate status code
        if result["verified"]:
            return jsonify(result), 200
        else:
            return jsonify(result), 401  # Unauthorized
            
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to verify student")
        return jsonify({"error": "Internal error during verification"}), 500


# Keep old endpoint for backward compatibility
@app.route("/api/faces", methods=["POST"])
def add_face() -> Any:
    """
    [DEPRECATED] Use /api/students/register instead.
    Register a new identity in the face database.
    """
    try:
        name = _extract_name()
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    images = _extract_images()
    if not images:
        return jsonify({"error": "At least one image is required"}), 400

    try:
        summary = PIPELINE.face_recognizer.add_person(name, images)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:  # pragma: no cover - defensive
        LOGGER.exception("Failed to add identity")
        return jsonify({"error": "Internal error while adding face"}), 500

    summary["total_identities"] = len(PIPELINE.face_recognizer.database.people)
    return jsonify(summary), 201


def _extract_field(field_name: str, required: bool = True, field_type: type = str):
    """
    Extract a field from request (JSON or form-data).
    
    Args:
        field_name: Name of the field to extract
        required: Whether the field is required
        field_type: Type to convert the field to (str, int, float)
    
    Returns:
        Field value converted to field_type
    
    Raises:
        ValueError: If required field is missing or type conversion fails
    """
    value = None
    
    if request.is_json:
        payload = request.get_json() or {}
        value = payload.get(field_name)
    elif request.form:
        value = request.form.get(field_name)
    
    if value is None:
        if required:
            raise ValueError(f"Missing '{field_name}' field")
        return None
    
    # Type conversion
    try:
        if field_type == int:
            return int(value)
        elif field_type == float:
            return float(value)
        else:
            return str(value).strip()
    except (ValueError, TypeError):
        raise ValueError(f"Invalid value for '{field_name}': expected {field_type.__name__}")


def _classify_violation(result: Dict[str, Any], flags: list) -> tuple[str, str]:
    """
    Phân loại loại vi phạm và mức độ nghiêm trọng dựa trên kết quả phát hiện.
    
    Args:
        result: Kết quả phát hiện từ pipeline
        flags: Danh sách cờ vi phạm
    
    Returns:
        Tuple của (loại_vi_phạm, mức_độ_nghiêm_trọng)
        
    Mức độ nghiêm trọng:
        - critical: Nhiều khuôn mặt, Không có khuôn mặt, Người lạ, Vật dụng khả nghi
        - medium: Các vi phạm khác (nhìn chỗ khác, cử động đầu)
    """
    faces = result.get("faces", [])
    objects = result.get("objects", [])
    
    # NGHIÊM TRỌNG: Nhiều khuôn mặt
    if len(faces) > 1:
        return "Nhiều khuôn mặt trong khung hình", "critical"
    
    # NGHIÊM TRỌNG: Không phát hiện khuôn mặt
    if len(faces) == 0:
        return "Không phát hiện khuôn mặt", "critical"
    
    # NGHIÊM TRỌNG: Người lạ (chưa đăng ký)
    if faces and faces[0].get("label") == "Unknown":
        return "Phát hiện người lạ", "critical"
    
    # NGHIÊM TRỌNG: Phát hiện vật dụng khả nghi
    if objects:
        return "Phát hiện vật dụng khả nghi", "critical"
    
    # KHÔNG NGHIÊM TRỌNG: Kiểm tra vi phạm về hướng nhìn/cử động đầu
    for flag in flags:
        flag_lower = flag.lower()
        
        # Nhìn chỗ khác
        # Nhìn chỗ khác (Gaze)
        if "gaze" in flag_lower and "center" not in flag_lower:
            if "looking up" in flag_lower:
                return "Mắt nhìn lên", "medium"
            if "looking down" in flag_lower:
                return "Mắt nhìn xuống", "medium"
            if "looking left" in flag_lower:
                return "Mắt nhìn trái", "medium"
            if "looking right" in flag_lower:
                return "Mắt nhìn phải", "medium"
            return "Mắt nhìn sang chỗ khác", "medium"
        
        # Cử động đầu bất thường (Head Pose)
        if "head orientation" in flag_lower:
            if "looking up" in flag_lower:
                return "Đầu ngẩng lên", "medium"
            if "looking down" in flag_lower:
                return "Đầu cúi xuống", "medium"
            if "looking left" in flag_lower:
                return "Đầu quay trái", "medium"
            if "looking right" in flag_lower:
                return "Đầu quay phải", "medium"
            return "Cử động đầu bất thường", "medium"
    
    # Mặc định: Vi phạm khác
    return "Vi phạm khác", "medium"


def _calculate_confidence(result: Dict[str, Any]) -> float:
    """
    Calculate average confidence from detection result.
    
    Args:
        result: Detection result from pipeline
    
    Returns:
        Average confidence score (0.0-1.0)
    """
    confidences = []
    
    # Face recognition confidence
    for face in result.get("faces", []):
        conf = face.get("confidence")
        if conf is not None:
            confidences.append(float(conf))
    
    # Object detection confidence
    for obj in result.get("objects", []):
        conf = obj.get("confidence")
        if conf is not None:
            confidences.append(float(conf))
    
    if confidences:
        return round(sum(confidences) / len(confidences), 2)
    return 0.0


def _extract_name() -> str:
    if request.is_json:
        payload = request.get_json() or {}
        name = payload.get("name")
        if name:
            return name.strip()
    if request.form:
        name = request.form.get("name")
        if name:
            return name.strip()
    raise ValueError("Missing 'name' field")


def _extract_student_id() -> str:
    """Extract and validate student ID from request."""
    if request.is_json:
        payload = request.get_json() or {}
        student_id = payload.get("student_id")
        if student_id:
            return student_id.strip()
    if request.form:
        student_id = request.form.get("student_id")
        if student_id:
            return student_id.strip()
    raise ValueError("Missing 'student_id' field")


def _extract_email() -> str:
    """Extract and validate email from request (optional)."""
    email = None
    if request.is_json:
        payload = request.get_json() or {}
        email = payload.get("email")
    elif request.form:
        email = request.form.get("email")
    
    if email:
        email = email.strip()
        # Basic email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError(f"Invalid email format: {email}")
    
    return email or ""


def _extract_images():
    images = []
    if request.files:
        file_list = request.files.getlist("images") or request.files.getlist("file")
        for idx, item in enumerate(file_list):
            if not item or not item.filename:
                continue
            try:
                images.append(decode_image_from_bytes(item.read()))
            except ValueError as exc:
                LOGGER.warning("Failed to decode uploaded image %d (%s): %s", idx, item.filename, exc)
    elif request.is_json:
        payload: Dict[str, Any] = request.get_json() or {}
        base64_images = payload.get("images")
        single = payload.get("image_base64") or payload.get("image_bytes")
        if single and not base64_images:
            base64_images = [single]
        if base64_images:
            for idx, data in enumerate(base64_images):
                try:
                    images.append(decode_image_from_base64(data))
                except ValueError as exc:
                    LOGGER.warning("Failed to decode base64 image %d: %s", idx, exc)
    return images


def _persist_annotated_image(image) -> str:
    """
    Store the annotated frame on disk and return the relative filename.
    """
    success, buffer = cv2.imencode(".jpg", image)
    if not success:
        raise ValueError("Failed to encode annotated frame")
    filename = f"{uuid.uuid4().hex}.jpg"
    output_path = ANNOTATED_DIR / filename
    output_path.write_bytes(buffer.tobytes())
    return filename


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(host="0.0.0.0", port=8001, debug=False)
