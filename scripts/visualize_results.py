#!/usr/bin/env python3
"""
Visualize extracted characters in a grid
"""

import cv2
import numpy as np
from pathlib import Path
import json

BASE_DIR = Path(__file__).parent.parent
GLYPHS_DIR = BASE_DIR / "glyphs"

def create_character_grid(char_dir, output_file, cols=10):
    """Create a grid visualization of extracted characters"""
    
    # Load metadata
    with open(char_dir / 'metadata.json', 'r') as f:
        metadata = json.load(f)
    
    # Load character images
    chars = []
    max_height = 0
    max_width = 0
    
    for item in metadata[:50]:  # First 50 characters
        img_path = char_dir / item['file']
        if img_path.exists():
            img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)
            chars.append(img)
            max_height = max(max_height, img.shape[0])
            max_width = max(max_width, img.shape[1])
    
    if not chars:
        print("No characters found")
        return
    
    # Pad all characters to same size
    padded_chars = []
    for img in chars:
        pad_h = max_height - img.shape[0]
        pad_w = max_width - img.shape[1]
        padded = cv2.copyMakeBorder(
            img, 
            pad_h//2, pad_h - pad_h//2,
            pad_w//2, pad_w - pad_w//2,
            cv2.BORDER_CONSTANT, value=255
        )
        padded_chars.append(padded)
    
    # Create grid
    rows = (len(padded_chars) + cols - 1) // cols
    grid = np.ones((rows * max_height, cols * max_width), dtype=np.uint8) * 255
    
    for idx, img in enumerate(padded_chars):
        row = idx // cols
        col = idx % cols
        y = row * max_height
        x = col * max_width
        grid[y:y+max_height, x:x+max_width] = img
    
    # Add grid lines
    for i in range(1, rows):
        cv2.line(grid, (0, i*max_height), (cols*max_width, i*max_height), 200, 1)
    for i in range(1, cols):
        cv2.line(grid, (i*max_width, 0), (i*max_width, rows*max_height), 200, 1)
    
    # Save grid
    cv2.imwrite(str(output_file), grid)
    print(f"Saved character grid: {output_file}")
    print(f"  - Characters: {len(chars)}")
    print(f"  - Grid size: {cols}x{rows}")
    print(f"  - Character size: {max_width}x{max_height}")

def main():
    """Create visualizations for all extracted character sets"""
    
    print("Creating character grid visualizations...")
    print("="*50)
    
    for char_dir in sorted(GLYPHS_DIR.glob("1000007*")):
        if char_dir.is_dir():
            output_file = GLYPHS_DIR / f"{char_dir.name}_grid.png"
            print(f"\nProcessing {char_dir.name}...")
            create_character_grid(char_dir, output_file)
    
    print("\n" + "="*50)
    print("Visualizations complete!")
    print("\nView the results:")
    for grid_file in sorted(GLYPHS_DIR.glob("*_grid.png")):
        print(f"  - {grid_file}")

if __name__ == "__main__":
    main()