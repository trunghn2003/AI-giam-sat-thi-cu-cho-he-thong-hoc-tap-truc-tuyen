#!/usr/bin/env python3
"""
Test the monitoring API endpoint
"""

import requests
import json

# API endpoint
API_URL = "http://localhost:8000/api/monitor"

# Test data
test_image = "/Users/hoangtrung/Documents/doancheating/head_pose/faceset/Image108.jpg"

# Request data
data = {
    "user_id": 123,
    "exam_period_id": 456,
    "submission_id": 789
}

print("=" * 60)
print("Testing Monitoring API")
print("=" * 60)
print(f"\nEndpoint: {API_URL}")
print(f"Image: {test_image}")
print(f"Data: {json.dumps(data, indent=2)}")

try:
    # Open and send image
    with open(test_image, 'rb') as f:
        files = {'image': ('test.jpg', f, 'image/jpeg')}
        response = requests.post(API_URL, data=data, files=files)
    
    print(f"\nStatus Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n" + "=" * 60)
        print("Response:")
        print("=" * 60)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
        if result.get('status') == 'violation_detected':
            print("\n" + "=" * 60)
            print("⚠️  VIOLATION DETECTED!")
            print("=" * 60)
            print(f"Type: {result.get('violation_type')}")
            print(f"Severity: {result.get('severity')}")
            print(f"Confidence: {result.get('confidence')}")
            print(f"Image URL: {result.get('image_url')}")
        else:
            print("\n✅ No violations detected - Student is following rules")
    else:
        print(f"\n❌ Error: {response.text}")

except FileNotFoundError:
    print(f"\n❌ Error: Test image not found at {test_image}")
    print("Please update the test_image path")
except Exception as e:
    print(f"\n❌ Error: {e}")

print("\n" + "=" * 60)
