#!/usr/bin/env python3
# Test the font creation directly
import json

# Sample classifications from the review data
classifications = {
    "ALPHA": ["letter_59"],
    "BETA": ["letter_98"],
}

# Test the font generation script content creation
script_content = f'''
import fontforge
import os

# Classifications from the web tool
classifications = {json.dumps(classifications)}

print(f"Received classifications for: {{list(classifications.keys())}}")
'''

print(script_content)