#!/usr/bin/env python3
"""
Prepare letters for review with bounding box data
Copies them to letters_for_review directory and creates a manifest.json file
"""

import json
import shutil
from pathlib import Path
import random
from PIL import Image

# Directories
BASE_DIR = Path(__file__).parent
GLYPHS_DIR = BASE_DIR / "glyphs_improved"
REVIEW_DIR = BASE_DIR / "letters_for_review"

# Create review directory
REVIEW_DIR.mkdir(exist_ok=True)

# Collect all character images with metadata
all_chars = []
letter_id = 0

for source_dir in GLYPHS_DIR.glob("*"):
    if source_dir.is_dir():
        source_name = source_dir.name
        
        # Load metadata if it exists
        metadata_file = source_dir / "metadata.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                
            # Get source image name and character data
            source_image = metadata.get('source_image', f"{source_name}.jpg")
            characters = metadata.get('characters', metadata if isinstance(metadata, list) else [])
            
            # Create a lookup dict for metadata by filename
            meta_by_file = {char['file']: char for char in characters}
            
            for char_file in source_dir.glob("*.png"):
                filename = char_file.name
                
                # Get metadata for this character
                char_meta = meta_by_file.get(filename, {})
                
                # Parse quality from filename if not in metadata
                if 'quality' in char_meta:
                    quality = int(char_meta['quality'] * 100)
                else:
                    parts = char_file.stem.split('_')
                    if len(parts) >= 3 and parts[2].startswith('q'):
                        quality = int(parts[2][1:])
                    else:
                        quality = 85
                
                # Get actual image dimensions
                try:
                    with Image.open(char_file) as img:
                        width, height = img.size
                except:
                    width, height = 40, 40
                
                all_chars.append({
                    'source_path': char_file,
                    'source': source_name,
                    'source_image': char_meta.get('source_image', source_image),
                    'quality': quality,
                    'width': width,
                    'height': height,
                    'bbox': char_meta.get('bbox', None),  # Bounding box if available
                    'id': letter_id
                })
                letter_id += 1
        else:
            # No metadata file, process traditionally
            for char_file in source_dir.glob("*.png"):
                parts = char_file.stem.split('_')
                if len(parts) >= 3 and parts[2].startswith('q'):
                    quality = int(parts[2][1:])
                else:
                    quality = 85
                
                # Get actual image dimensions
                try:
                    with Image.open(char_file) as img:
                        width, height = img.size
                except:
                    width, height = 40, 40
                
                all_chars.append({
                    'source_path': char_file,
                    'source': source_name,
                    'source_image': f"{source_name}.jpg",
                    'quality': quality,
                    'width': width,
                    'height': height,
                    'bbox': None,
                    'id': letter_id
                })
                letter_id += 1

print(f"Found {len(all_chars)} total character images")

# Sort by quality (highest first) but take ALL
all_chars.sort(key=lambda x: x['quality'], reverse=True)

# Take ALL characters
selected_chars = all_chars

# Copy files and create manifest with bbox data
manifest = {"letters": []}

for i, char_info in enumerate(selected_chars):
    # Create standardized filename
    new_filename = f"letter_{str(i).zfill(5)}.png"
    dest_path = REVIEW_DIR / new_filename
    
    # Copy file
    shutil.copy2(char_info['source_path'], dest_path)
    
    # Create manifest entry
    entry = {
        "id": i,
        "filename": new_filename,
        "source": char_info['source'],
        "source_image": char_info['source_image'],
        "quality": char_info['quality'],
        "width": char_info['width'],
        "height": char_info['height']
    }
    
    # Add bbox if available
    if char_info['bbox']:
        entry['bbox'] = char_info['bbox']
    
    manifest["letters"].append(entry)
    
    if (i + 1) % 500 == 0:
        print(f"  Processed {i + 1} / {len(selected_chars)}")

# Save manifest
manifest_path = REVIEW_DIR / "manifest.json"
with open(manifest_path, 'w') as f:
    json.dump(manifest, f, indent=2)

print(f"\nPrepared {len(manifest['letters'])} letters for review")
print(f"Files copied to: {REVIEW_DIR}")
print(f"Manifest saved to: {manifest_path}")

# Count how many have bounding boxes
bbox_count = sum(1 for letter in manifest['letters'] if 'bbox' in letter)
print(f"Characters with bounding boxes: {bbox_count}/{len(manifest['letters'])}")