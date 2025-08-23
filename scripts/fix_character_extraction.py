#!/usr/bin/env python3
"""
Fix character extraction to properly extract readable characters from manuscript images
"""

import cv2
import numpy as np
from pathlib import Path
import json
from scipy import ndimage

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
GLYPHS_DIR = BASE_DIR / "glyphs_improved"

class CharacterExtractor:
    def __init__(self):
        GLYPHS_DIR.mkdir(exist_ok=True)
        
    def extract_characters(self, image_path):
        """Extract characters from a manuscript page"""
        print(f"\nProcessing {image_path.name}...")
        
        # Read image
        img = cv2.imread(str(image_path))
        if img is None:
            print(f"  Error: Could not read image")
            return []
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to handle uneven lighting
        # This creates a binary image with text as black on white background
        binary = cv2.adaptiveThreshold(
            gray, 255, 
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 
            21, 10
        )
        
        # Check if we need to invert (text should be black)
        # Count pixels in a sample area
        h, w = binary.shape
        sample = binary[h//4:3*h//4, w//4:3*w//4]
        if np.mean(sample) < 127:  # Mostly black, need to invert
            binary = cv2.bitwise_not(binary)
        
        # Clean up noise
        kernel = np.ones((2,2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        
        # Find text lines using horizontal projection
        lines = self.find_text_lines(binary)
        
        # Extract characters from each line
        characters = []
        char_id = 0
        
        for line_idx, (y1, y2) in enumerate(lines):
            line_img = binary[y1:y2, :]
            line_chars = self.extract_line_characters(line_img)
            
            for char_data in line_chars:
                char_data['id'] = char_id
                char_data['line'] = line_idx
                char_data['global_y'] = y1 + char_data['y']
                characters.append(char_data)
                char_id += 1
        
        print(f"  Extracted {len(characters)} characters from {len(lines)} lines")
        return characters
    
    def find_text_lines(self, binary_img):
        """Find horizontal text lines in the image"""
        # Calculate horizontal projection
        h_projection = np.sum(255 - binary_img, axis=1) / 255
        
        # Smooth the projection
        h_smooth = ndimage.gaussian_filter1d(h_projection, sigma=3)
        
        # Find threshold
        non_zero = h_smooth[h_smooth > 0]
        if len(non_zero) == 0:
            return []
        threshold = np.percentile(non_zero, 25)
        
        # Find line boundaries
        lines = []
        in_line = False
        line_start = 0
        min_line_height = 15
        
        for i, val in enumerate(h_smooth):
            if not in_line and val > threshold:
                in_line = True
                line_start = i
            elif in_line and val <= threshold:
                in_line = False
                if i - line_start >= min_line_height:
                    # Add some padding
                    start = max(0, line_start - 5)
                    end = min(len(h_projection), i + 5)
                    lines.append((start, end))
        
        return lines
    
    def extract_line_characters(self, line_img):
        """Extract individual characters from a text line"""
        # Invert for connected components (OpenCV expects white objects on black)
        inverted = cv2.bitwise_not(line_img)
        
        # Find connected components
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            inverted, connectivity=8
        )
        
        characters = []
        
        for i in range(1, num_labels):  # Skip background (label 0)
            x, y, w, h, area = stats[i]
            
            # Filter by size
            if w < 8 or h < 8:  # Too small
                continue
            if w > 200 or h > 200:  # Too large
                continue
            if area < 40:  # Too few pixels
                continue
            
            # Filter by aspect ratio
            aspect_ratio = w / h
            if aspect_ratio > 4 or aspect_ratio < 0.15:
                continue
            
            # Extract the character region
            char_img = line_img[y:y+h, x:x+w].copy()
            
            # Ensure the character is black on white
            if np.mean(char_img) < 127:
                char_img = cv2.bitwise_not(char_img)
            
            # Add padding to make characters more uniform
            pad = 5
            char_padded = cv2.copyMakeBorder(
                char_img, pad, pad, pad, pad,
                cv2.BORDER_CONSTANT, value=255
            )
            
            # Calculate quality score
            quality = self.calculate_quality(char_padded)
            
            characters.append({
                'x': x,
                'y': y,
                'w': w,
                'h': h,
                'area': area,
                'image': char_padded,
                'quality_score': quality
            })
        
        # Sort by x position (left to right)
        characters.sort(key=lambda c: c['x'])
        
        return characters
    
    def calculate_quality(self, char_img):
        """Calculate quality score for a character"""
        # Check ink density
        black_pixels = np.sum(char_img < 127)
        total_pixels = char_img.size
        ink_ratio = black_pixels / total_pixels
        
        # Ideal ink ratio is between 10% and 40%
        if 0.1 <= ink_ratio <= 0.4:
            density_score = 1.0
        else:
            density_score = max(0, 1.0 - abs(ink_ratio - 0.25) * 2)
        
        # Check connectivity (should be mostly one piece)
        inverted = cv2.bitwise_not(char_img)
        num_components, _, _, _ = cv2.connectedComponentsWithStats(inverted)
        connectivity_score = 1.0 / max(num_components - 1, 1)
        
        # Check edge sharpness
        edges = cv2.Canny(char_img, 50, 150)
        edge_pixels = np.sum(edges > 0)
        edge_ratio = edge_pixels / total_pixels
        edge_score = min(edge_ratio * 20, 1.0)  # Normalize to 0-1
        
        # Combine scores
        quality = (density_score * 0.4 + connectivity_score * 0.3 + edge_score * 0.3)
        
        return quality
    
    def save_characters(self, characters, source_name, source_image_path=None):
        """Save extracted characters to files with bounding box data"""
        output_dir = GLYPHS_DIR / source_name
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Sort by quality and save top characters
        characters.sort(key=lambda x: x['quality_score'], reverse=True)
        
        saved_count = 0
        metadata_list = []
        
        for char in characters:
            if char['quality_score'] < 0.3:  # Skip low quality
                continue
            
            filename = f"char_{char['id']:04d}_q{int(char['quality_score']*100):02d}.png"
            filepath = output_dir / filename
            
            # Save the character image
            cv2.imwrite(str(filepath), char['image'])
            
            # Add metadata with bounding box
            metadata_list.append({
                'id': char['id'],
                'filename': filename,
                'file': filename,  # For compatibility
                'source_image': f"{source_name}.jpg" if not source_image_path else source_image_path.name,
                'quality': float(char['quality_score']),
                'bbox': {  # Bounding box in original image coordinates
                    'x': int(char['x']),
                    'y': int(char.get('global_y', char['y'])),  # Use global_y if available
                    'width': int(char['w']),
                    'height': int(char['h'])
                },
                'line': int(char.get('line', 0))
            })
            
            saved_count += 1
            if saved_count >= 2000:  # Limit per page
                break
        
        # Save metadata with bounding boxes
        metadata_file = output_dir / 'metadata.json'
        with open(metadata_file, 'w') as f:
            json.dump({
                'source_image': f"{source_name}.jpg",
                'characters': metadata_list
            }, f, indent=2)
        
        print(f"  Saved {saved_count} characters to {output_dir}")
        return saved_count

def main():
    print("="*60)
    print("CHARACTER EXTRACTION FROM MANUSCRIPT IMAGES")
    print("="*60)
    
    extractor = CharacterExtractor()
    
    # Process all manuscript images
    image_files = sorted(DATA_DIR.glob("*.jpg"))
    
    if not image_files:
        print("No manuscript images found in data directory!")
        return
    
    print(f"\nFound {len(image_files)} manuscript images")
    
    total_chars = 0
    for img_path in image_files:
        # Extract source name from filename
        source_name = img_path.stem
        
        # Extract characters
        characters = extractor.extract_characters(img_path)
        
        if characters:
            # Save characters
            saved = extractor.save_characters(characters, source_name)
            total_chars += saved
    
    print(f"\n{'='*60}")
    print(f"EXTRACTION COMPLETE")
    print(f"Total characters extracted: {total_chars}")
    print(f"Output directory: {GLYPHS_DIR}")

if __name__ == "__main__":
    main()