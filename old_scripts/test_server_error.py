#!/usr/bin/env python3
"""Test what happens with the font creation"""

import json

# Test data that the browser would send
test_data = {
    "classifications": {
        "ALPHA": ["letter_59", "letter_338"],
        "BETA": ["letter_98"]
    },
    "timestamp": "2025-08-23"
}

print("Test data to send:")
print(json.dumps(test_data, indent=2))

# Try to create the FontForge script
script_content = f'''
import fontforge
import os

# Classifications from the web tool
classifications = {json.dumps(test_data['classifications'])}

print(f"Received classifications for: {{list(classifications.keys())}}")
'''

print("\nScript content that would be created:")
print(script_content)