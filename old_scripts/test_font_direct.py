#!/usr/bin/env python3
"""Test font creation directly"""

import json
import requests

# Test with a simple request
test_data = {
    "classifications": {
        "ALPHA": ["letter_59"],
        "BETA": ["letter_98"]
    },
    "timestamp": "2025-08-23"
}

print("Sending test data to server...")
print(json.dumps(test_data, indent=2))

try:
    response = requests.post(
        'http://localhost:8080/create_font',
        json=test_data,
        headers={'Content-Type': 'application/json'}
    )
    
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 500:
        print("Error response:")
        try:
            error_data = response.json()
            print(json.dumps(error_data, indent=2))
            if 'traceback' in error_data:
                print("\nTraceback:")
                print(error_data['traceback'])
        except:
            print(response.text)
    else:
        print("Success response:")
        print(json.dumps(response.json(), indent=2))
        
except Exception as e:
    print(f"Request failed: {e}")