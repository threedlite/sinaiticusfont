#!/usr/bin/env python3
"""
Prepare letters for review by copying them to letters_for_review directory
and creating a manifest.json file
"""

import json
import shutil
from pathlib import Path
import random

# Directories
BASE_DIR = Path(__file__).parent
GLYPHS_DIR = BASE_DIR / "glyphs_improved"
REVIEW_DIR = BASE_DIR / "letters_for_review"

# Create review directory
REVIEW_DIR.mkdir(exist_ok=True)

# Collect all character images
all_chars = []
letter_id = 0

for source_dir in GLYPHS_DIR.glob("*"):
    if source_dir.is_dir():
        source_name = source_dir.name
        for char_file in source_dir.glob("*.png"):
            # Parse filename to get quality
            parts = char_file.stem.split('_')
            if len(parts) >= 3 and parts[2].startswith('q'):
                quality = int(parts[2][1:])
            else:
                quality = 85  # default
            
            all_chars.append({
                'source_path': char_file,
                'source': source_name,
                'quality': quality,
                'id': letter_id
            })
            letter_id += 1

print(f"Found {len(all_chars)} total character images")

# Sort by quality (highest first) but take ALL
all_chars.sort(key=lambda x: x['quality'], reverse=True)

# Take ALL characters, no limit
selected_chars = all_chars  # Use ALL characters

# Copy files and create manifest
manifest = {"letters": []}

for i, char_info in enumerate(selected_chars):
    # Create standardized filename
    new_filename = f"letter_{str(i).zfill(5)}.png"
    dest_path = REVIEW_DIR / new_filename
    
    # Copy file
    shutil.copy2(char_info['source_path'], dest_path)
    
    # Add to manifest
    manifest["letters"].append({
        "id": i,
        "filename": new_filename,
        "source": char_info['source'],
        "quality": char_info['quality'],
        "width": 40,  # Default, would need to read image to get actual
        "height": 40  # Default, would need to read image to get actual
    })
    
    if (i + 1) % 500 == 0:
        print(f"  Processed {i + 1} / {len(selected_chars)}")

# Save manifest
manifest_path = REVIEW_DIR / "manifest.json"
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\nPrepared {len(manifest['letters'])} letters for review")
print(f"Files copied to: {REVIEW_DIR}")
print(f"Manifest saved to: {manifest_path}")