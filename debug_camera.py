
import cv2
import numpy as np
from cheating_detection import load_default_pipeline
from cheating_detection.visualization import annotate_detections

def main():
    print("Loading pipeline...")
    pipeline = load_default_pipeline()
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Cannot open camera")
        return

    print("Starting camera... Press 'q' to quit.")
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Failed to capture frame")
            break

        # Run analysis
        try:
            result = pipeline.analyze(frame)
        except Exception as e:
            print(f"Analysis failed: {e}")
            continue

        # Draw basic annotations (faces, objects, labels)
        annotated_frame = result.get("annotated_image", frame).copy()

        # Extra: Draw raw Head Pose angles for debugging
        faces = result.get("faces", [])
        for i, face in enumerate(faces):
            pose = face.get("pose") # This is [pitch, yaw, roll] based on head_pose.py logic? 
            # Note: head_pose.py: classify_sequence -> _ordered_pose(pose) -> zip(pose_order, values)
            # Default pose_order is ("pitch", "yaw", "roll").
            # InsightFace typically returns pose in [pitch, yaw, roll] degrees.
            
            if pose is not None and len(pose) == 3:
                pitch, yaw, roll = pose
                
                # Create debug text for Head Pose
                pose_text = f"Head P:{pitch:.1f} Y:{yaw:.1f} R:{roll:.1f}"
                
                # Get Gaze Metrics
                gaze_metrics = face.get("gaze_metrics", {})
                h_ratio = gaze_metrics.get("horizontal_ratio", 0.0)
                v_ratio = gaze_metrics.get("vertical_ratio", 0.0)
                gaze_text = f"Eye V:{v_ratio:.2f} H:{h_ratio:.2f}"

                # Draw it near the face bbox
                bbox = face.get("bbox")
                if bbox:
                    x1, y1, x2, y2 = [int(v) for v in bbox]
                    # Draw above the standard label
                    cv2.putText(annotated_frame, pose_text, (x1, y1 - 45), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    cv2.putText(annotated_frame, gaze_text, (x1, y1 - 25), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Show status flags
        flags = result.get("flags", [])
        for idx, flag in enumerate(flags):
            cv2.putText(annotated_frame, flag, (10, 30 + idx * 30), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        cv2.imshow("Debug Camera - Head Pose", annotated_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
