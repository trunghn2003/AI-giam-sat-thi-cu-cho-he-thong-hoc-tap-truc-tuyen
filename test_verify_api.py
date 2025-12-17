"""
Test script for student verification API.
"""

import base64
import sys

import requests


BASE_URL = "http://localhost:8000"


def verify_student(student_id: str, image_path: str, threshold: float = 0.5):
    """
    Verify student identity before exam entry.
    
    Args:
        student_id: Student ID to verify
        image_path: Path to student photo
        threshold: Verification threshold (0.0-1.0)
    
    Returns:
        True if verified, False otherwise
    """
    print(f"\n{'='*60}")
    print(f"Verifying Student ID: {student_id}")
    print(f"Image: {image_path}")
    print(f"Threshold: {threshold}")
    print(f"{'='*60}")
    
    # Read and encode image
    try:
        with open(image_path, 'rb') as f:
            image_base64 = base64.b64encode(f.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: Image file not found: {image_path}")
        return False
    
    # Send verification request
    try:
        response = requests.post(
            f'{BASE_URL}/api/students/verify',
            json={
                'student_id': student_id,
                'image': image_base64,
                'threshold': threshold
            },
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Failed to connect to server: {e}")
        return False
    
    result = response.json()
    
    print(f"\nStatus Code: {response.status_code}")
    print(f"Response:")
    
    if response.status_code == 200:
        print(f"  ✅ VERIFIED: {result['name']}")
        print(f"  Student ID: {result['student_id']}")
        print(f"  Matched Name: {result.get('matched_name', 'N/A')}")
        print(f"  Confidence: {result['confidence']:.2%}")
        print(f"  Threshold: {result['threshold']:.2f}")
        print(f"  Message: {result['message']}")
        print(f"\n🎓 ✅ ALLOW EXAM ENTRY")
        return True
    else:
        print(f"  ❌ VERIFICATION FAILED")
        print(f"  Student ID: {result.get('student_id', 'N/A')}")
        print(f"  Name: {result.get('name', 'N/A')}")
        print(f"  Matched Name: {result.get('matched_name', 'N/A')}")
        print(f"  Confidence: {result.get('confidence', 0):.2%}")
        print(f"  Face Detected: {result.get('face_detected', False)}")
        print(f"  Message: {result.get('message', result.get('error', 'Unknown error'))}")
        print(f"\n🚫 ❌ DENY EXAM ENTRY")
        return False


def verify_with_file(student_id: str, image_path: str, threshold: float = 0.5):
    """Verify using multipart form-data."""
    print(f"\n{'='*60}")
    print(f"Verifying Student ID: {student_id} (Multipart)")
    print(f"Image: {image_path}")
    print(f"{'='*60}")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image': f}
            data = {
                'student_id': student_id,
                'threshold': str(threshold)
            }
            response = requests.post(
                f'{BASE_URL}/api/students/verify',
                files=files,
                data=data,
                timeout=10
            )
    except FileNotFoundError:
        print(f"❌ Error: Image file not found: {image_path}")
        return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Error: Failed to connect to server: {e}")
        return False
    
    result = response.json()
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ VERIFIED: {result['name']} ({result['confidence']:.2%})")
        return True
    else:
        print(f"❌ FAILED: {result.get('message', result.get('error'))}")
        return False


def test_scenarios():
    """Run various test scenarios."""
    print("\n" + "="*60)
    print("STUDENT VERIFICATION API - TEST SCENARIOS")
    print("="*60)
    
    # Test 1: Valid student with correct photo
    print("\n\n[TEST 1] Valid student with matching photo")
    print("-" * 60)
    verify_student('SV001', 'test_data/student1.jpg', threshold=0.5)
    
    # Test 2: Valid student with wrong photo
    print("\n\n[TEST 2] Valid student with wrong person's photo")
    print("-" * 60)
    verify_student('SV001', 'test_data/different_person.jpg', threshold=0.5)
    
    # Test 3: Invalid student ID
    print("\n\n[TEST 3] Non-existent student ID")
    print("-" * 60)
    verify_student('NOTEXIST', 'test_data/student1.jpg', threshold=0.5)
    
    # Test 4: No face in image
    print("\n\n[TEST 4] Image with no face")
    print("-" * 60)
    verify_student('SV001', 'test_data/no_face.jpg', threshold=0.5)
    
    # Test 5: Custom high threshold
    print("\n\n[TEST 5] High threshold (strict)")
    print("-" * 60)
    verify_student('SV001', 'test_data/student1.jpg', threshold=0.8)
    
    # Test 6: Custom low threshold
    print("\n\n[TEST 6] Low threshold (lenient)")
    print("-" * 60)
    verify_student('SV001', 'test_data/student1_poor_quality.jpg', threshold=0.3)


def interactive_mode():
    """Interactive verification mode."""
    print("\n" + "="*60)
    print("INTERACTIVE VERIFICATION MODE")
    print("="*60)
    
    while True:
        print("\nOptions:")
        print("1. Verify student")
        print("2. Run test scenarios")
        print("3. Exit")
        
        choice = input("\nEnter choice (1-3): ").strip()
        
        if choice == '1':
            student_id = input("Enter student ID: ").strip()
            image_path = input("Enter image path: ").strip()
            threshold_str = input("Enter threshold (default 0.5): ").strip()
            
            threshold = 0.5
            if threshold_str:
                try:
                    threshold = float(threshold_str)
                except ValueError:
                    print("Invalid threshold, using default 0.5")
            
            verify_student(student_id, image_path, threshold)
            
        elif choice == '2':
            test_scenarios()
            
        elif choice == '3':
            print("\nGoodbye!")
            break
        else:
            print("Invalid choice!")


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Command line mode
        if len(sys.argv) < 3:
            print("Usage: python test_verify_api.py <student_id> <image_path> [threshold]")
            print("   or: python test_verify_api.py --interactive")
            print("   or: python test_verify_api.py --test")
            sys.exit(1)
        
        if sys.argv[1] == '--interactive':
            interactive_mode()
        elif sys.argv[1] == '--test':
            test_scenarios()
        else:
            student_id = sys.argv[1]
            image_path = sys.argv[2]
            threshold = float(sys.argv[3]) if len(sys.argv) > 3 else 0.5
            
            result = verify_student(student_id, image_path, threshold)
            sys.exit(0 if result else 1)
    else:
        # Default: interactive mode
        interactive_mode()


if __name__ == "__main__":
    main()
