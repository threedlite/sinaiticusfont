#!/usr/bin/env python3
"""
End-to-end pipeline for Codex Sinaiticus font generation
Proof of concept to test feasibility
"""

import os
import cv2
import numpy as np
from pathlib import Path
import json
from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys

# Project paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
GLYPHS_DIR = BASE_DIR / "glyphs"
VECTORS_DIR = BASE_DIR / "vectors"
BUILD_DIR = BASE_DIR / "build"
SOURCES_DIR = BASE_DIR / "sources"

class ManuscriptProcessor:
    def __init__(self):
        self.ensure_dirs()
        
    def ensure_dirs(self):
        """Ensure all necessary directories exist"""
        for dir_path in [GLYPHS_DIR, VECTORS_DIR, BUILD_DIR, SOURCES_DIR]:
            dir_path.mkdir(exist_ok=True)
    
    def preprocess_image(self, image_path):
        """
        Preprocess manuscript image for character extraction
        """
        print(f"Preprocessing {image_path}...")
        
        # Read image
        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply adaptive thresholding to handle uneven lighting
        binary = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 21, 10
        )
        
        # Invert if text is lighter than background
        text_pixels = np.sum(binary == 0)
        bg_pixels = np.sum(binary == 255)
        if text_pixels > bg_pixels:
            binary = cv2.bitwise_not(binary)
        
        # Denoise
        denoised = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((2,2), np.uint8))
        denoised = cv2.morphologyEx(denoised, cv2.MORPH_OPEN, np.ones((2,2), np.uint8))
        
        return denoised
    
    def detect_lines(self, binary_img):
        """
        Detect text lines in the manuscript
        """
        print("Detecting text lines...")
        
        # Horizontal projection to find lines
        h_projection = np.sum(binary_img == 0, axis=1)
        
        # Find line boundaries
        lines = []
        in_line = False
        line_start = 0
        
        threshold = np.max(h_projection) * 0.1  # 10% of max as threshold
        
        for i, val in enumerate(h_projection):
            if not in_line and val > threshold:
                in_line = True
                line_start = i
            elif in_line and val <= threshold:
                in_line = False
                if i - line_start > 10:  # Minimum line height
                    lines.append((line_start, i))
        
        print(f"Found {len(lines)} text lines")
        return lines
    
    def segment_characters(self, binary_img, lines):
        """
        Segment individual characters from text lines
        """
        print("Segmenting characters...")
        
        characters = []
        char_id = 0
        
        for line_idx, (y1, y2) in enumerate(lines):
            # Extract line
            line_img = binary_img[y1:y2, :]
            
            # Vertical projection to find characters
            v_projection = np.sum(line_img == 0, axis=0)
            
            # Find character boundaries
            in_char = False
            char_start = 0
            threshold = 3  # Minimum pixels to consider as character
            
            for i, val in enumerate(v_projection):
                if not in_char and val > threshold:
                    in_char = True
                    char_start = i
                elif in_char and val <= threshold:
                    in_char = False
                    char_width = i - char_start
                    if 10 < char_width < 100:  # Reasonable character width
                        char_img = line_img[:, char_start:i]
                        
                        # Add padding
                        pad = 5
                        char_img = cv2.copyMakeBorder(
                            char_img, pad, pad, pad, pad, 
                            cv2.BORDER_CONSTANT, value=255
                        )
                        
                        characters.append({
                            'id': char_id,
                            'line': line_idx,
                            'image': char_img,
                            'x': char_start,
                            'y': y1,
                            'width': char_width,
                            'height': y2 - y1
                        })
                        char_id += 1
        
        print(f"Extracted {len(characters)} characters")
        return characters
    
    def save_characters(self, characters, source_name, source_image_path):
        """
        Save extracted characters as individual images with bounding box data
        """
        print("Saving character images...")
        
        output_dir = GLYPHS_DIR / source_name
        output_dir.mkdir(exist_ok=True)
        
        metadata = []
        
        for char in characters:  # Save ALL characters
            filename = f"char_{char['id']:04d}.png"
            filepath = output_dir / filename
            
            cv2.imwrite(str(filepath), char['image'])
            
            metadata.append({
                'id': char['id'],
                'file': filename,
                'source_image': source_image_path.name,  # Original manuscript image
                'line': char['line'],
                'bbox': {  # Bounding box in original image coordinates
                    'x': char['x'],
                    'y': char['y'],
                    'width': char['width'],
                    'height': char['height']
                }
            })
        
        # Save metadata with bounding boxes
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump({
                'source_image': source_image_path.name,
                'characters': metadata
            }, f, indent=2)
        
        print(f"Saved {len(metadata)} characters to {output_dir}")
        return output_dir
    
    def vectorize_characters(self, char_dir):
        """
        Convert character images to vector format using potrace
        """
        print("Vectorizing characters...")
        
        vector_dir = VECTORS_DIR / char_dir.name
        vector_dir.mkdir(exist_ok=True)
        
        char_files = list(char_dir.glob("char_*.png"))
        
        for char_file in char_files[:20]:  # Process first 20 for testing
            # Convert to PBM format for potrace
            pbm_file = vector_dir / f"{char_file.stem}.pbm"
            svg_file = vector_dir / f"{char_file.stem}.svg"
            
            # Convert PNG to PBM
            img = Image.open(char_file).convert('L')
            img = img.point(lambda x: 0 if x < 128 else 255, '1')
            img.save(pbm_file)
            
            # Run potrace to create SVG
            try:
                subprocess.run([
                    'potrace', 
                    '-s',  # SVG output
                    '-o', str(svg_file),
                    str(pbm_file)
                ], check=True, capture_output=True)
                
                # Clean up PBM file
                pbm_file.unlink()
                
            except subprocess.CalledProcessError as e:
                print(f"Warning: potrace failed for {char_file.name}")
            except FileNotFoundError:
                print("Warning: potrace not found. Install with: brew install potrace")
                return None
        
        print(f"Vectorized characters saved to {vector_dir}")
        return vector_dir
    
    def create_sample_font(self, vector_dir):
        """
        Create a basic font file from vectorized characters
        Using FontForge Python bindings
        """
        print("Creating sample font...")
        
        try:
            import fontforge
        except ImportError:
            print("FontForge Python bindings not found.")
            print("Install with: brew install fontforge")
            print("Then: pip install fontforge")
            return None
        
        # Create new font
        font = fontforge.font()
        font.fontname = "CodexSinaiticusSample"
        font.fullname = "Codex Sinaiticus Sample"
        font.familyname = "Codex Sinaiticus"
        
        # Set font metrics
        font.ascent = 800
        font.descent = 200
        
        # Map some characters to basic Greek letters
        # This is a simplified mapping for proof of concept
        char_mapping = {
            0: 0x0391,  # Alpha
            1: 0x0392,  # Beta
            2: 0x0393,  # Gamma
            3: 0x0394,  # Delta
            4: 0x0395,  # Epsilon
            5: 0x0396,  # Zeta
            6: 0x0397,  # Eta
            7: 0x0398,  # Theta
            8: 0x0399,  # Iota
            9: 0x039A,  # Kappa
        }
        
        svg_files = sorted(vector_dir.glob("*.svg"))[:10]
        
        for idx, svg_file in enumerate(svg_files):
            if idx in char_mapping:
                unicode_point = char_mapping[idx]
                glyph = font.createChar(unicode_point)
                
                try:
                    # Import the SVG
                    glyph.importOutlines(str(svg_file))
                    
                    # Scale and position
                    glyph.width = 600
                    
                except Exception as e:
                    print(f"Warning: Could not import {svg_file.name}: {e}")
        
        # Generate TTF
        output_file = BUILD_DIR / "CodexSinaiticusSample.ttf"
        font.generate(str(output_file))
        
        print(f"Sample font generated: {output_file}")
        return output_file
    
    def process_manuscript(self, image_path):
        """
        Run the complete pipeline on a manuscript image
        """
        print(f"\n{'='*50}")
        print(f"Processing {image_path.name}")
        print('='*50)
        
        # Preprocess
        binary = self.preprocess_image(image_path)
        
        # Save preprocessed image for inspection
        preprocessed_path = GLYPHS_DIR / f"{image_path.stem}_preprocessed.png"
        cv2.imwrite(str(preprocessed_path), binary)
        print(f"Saved preprocessed image: {preprocessed_path}")
        
        # Detect lines
        lines = self.detect_lines(binary)
        
        # Segment characters
        characters = self.segment_characters(binary, lines)
        
        # Save characters with bounding box data
        char_dir = self.save_characters(characters, image_path.stem, image_path)
        
        # Vectorize (if potrace is available)
        vector_dir = self.vectorize_characters(char_dir)
        
        if vector_dir:
            # Create font (if fontforge is available)
            font_file = self.create_sample_font(vector_dir)
        
        return {
            'source': image_path.name,
            'lines': len(lines),
            'characters': len(characters),
            'char_dir': str(char_dir),
            'vector_dir': str(vector_dir) if vector_dir else None
        }

def main():
    """
    Main pipeline execution
    """
    print("Codex Sinaiticus Font Generation Pipeline")
    print("Proof of Concept")
    print("="*50)
    
    processor = ManuscriptProcessor()
    
    # Process all manuscript images
    results = []
    for image_path in sorted(DATA_DIR.glob("*.jpg")):
        result = processor.process_manuscript(image_path)
        results.append(result)
    
    # Save results summary
    summary_file = BASE_DIR / "pipeline_results.json"
    with open(summary_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n{'='*50}")
    print("Pipeline Complete!")
    print(f"Results saved to: {summary_file}")
    print("\nSummary:")
    for result in results:
        print(f"  {result['source']}: {result['characters']} characters from {result['lines']} lines")
    
    print("\nNext steps:")
    print("1. Review extracted characters in glyphs/ directory")
    print("2. Install potrace for vectorization: brew install potrace")
    print("3. Install fontforge for font generation: brew install fontforge")
    print("4. Manually classify and map characters to Unicode points")

if __name__ == "__main__":
    main()