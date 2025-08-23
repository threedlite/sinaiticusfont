#!/usr/bin/env python3
"""
Add bounding box data to existing extracted letters by matching them in the original images
This preserves the original 27,779 letters and just adds bbox coordinates
"""

import cv2
import numpy as np
from pathlib import Path
import json
from tqdm import tqdm

# Directories
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
REVIEW_DIR = BASE_DIR / "letters_for_review"

def find_character_in_manuscript(char_img, manuscript_img, threshold=0.8):
    """
    Find where a character image appears in the manuscript using template matching
    """
    # Convert to grayscale if needed
    if len(char_img.shape) == 3:
        char_gray = cv2.cvtColor(char_img, cv2.COLOR_BGR2GRAY)
    else:
        char_gray = char_img
        
    if len(manuscript_img.shape) == 3:
        manuscript_gray = cv2.cvtColor(manuscript_img, cv2.COLOR_BGR2GRAY)
    else:
        manuscript_gray = manuscript_img
    
    # Get dimensions
    h, w = char_gray.shape
    
    # Template matching
    result = cv2.matchTemplate(manuscript_gray, char_gray, cv2.TM_CCOEFF_NORMED)
    
    # Find best match
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
    
    if max_val >= threshold:
        # Found a good match
        return {
            'x': max_loc[0],
            'y': max_loc[1],
            'width': w,
            'height': h,
            'confidence': max_val
        }
    
    return None

def main():
    print("Adding bounding boxes to existing letters...")
    
    # Load existing manifest
    manifest_path = REVIEW_DIR / "manifest.json"
    if not manifest_path.exists():
        print("Error: manifest.json not found")
        return
        
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    print(f"Loaded manifest with {len(manifest['letters'])} letters")
    
    # Group letters by source
    letters_by_source = {}
    for letter in manifest['letters']:
        source = letter.get('source', 'unknown')
        if source not in letters_by_source:
            letters_by_source[source] = []
        letters_by_source[source].append(letter)
    
    print(f"Found {len(letters_by_source)} manuscript sources")
    
    # Process each manuscript
    updated_count = 0
    for source_id, letters in letters_by_source.items():
        manuscript_path = DATA_DIR / f"{source_id}.jpg"
        
        if not manuscript_path.exists():
            print(f"  Skipping {source_id}: manuscript image not found")
            continue
            
        print(f"\nProcessing {source_id} with {len(letters)} letters...")
        
        # Load manuscript image
        manuscript_img = cv2.imread(str(manuscript_path))
        if manuscript_img is None:
            print(f"  Error loading manuscript image")
            continue
        
        # Process each letter
        matches = 0
        for i, letter in enumerate(letters):
            if 'bbox' in letter:
                # Already has bbox, skip
                continue
                
            # Load character image
            char_path = REVIEW_DIR / letter['filename']
            if not char_path.exists():
                continue
                
            char_img = cv2.imread(str(char_path))
            if char_img is None:
                continue
            
            # Try to find character in manuscript
            bbox = find_character_in_manuscript(char_img, manuscript_img)
            
            if bbox:
                # Add bbox to letter data
                letter['bbox'] = {
                    'x': int(bbox['x']),
                    'y': int(bbox['y']),
                    'width': int(bbox['width']),
                    'height': int(bbox['height'])
                }
                letter['source_image'] = f"{source_id}.jpg"
                matches += 1
                updated_count += 1
                
            if (i + 1) % 100 == 0:
                print(f"    Processed {i + 1}/{len(letters)} letters, {matches} matches found")
        
        print(f"  Found bounding boxes for {matches}/{len(letters)} letters")
    
    # Save updated manifest
    output_path = REVIEW_DIR / "manifest_with_template_bbox.json"
    with open(output_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\nTotal letters with bounding boxes: {updated_count}")
    print(f"Updated manifest saved to: {output_path}")
    
    # Also update the main manifest
    if updated_count > 0:
        response = input("\nReplace main manifest.json? (y/n): ")
        if response.lower() == 'y':
            import shutil
            shutil.copy2(output_path, manifest_path)
            print("Main manifest.json updated")

if __name__ == "__main__":
    main()