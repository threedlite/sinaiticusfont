#!/usr/bin/env python3
"""
Improved character extraction with better segmentation and quality control
"""

import cv2
import numpy as np
from pathlib import Path
import json
from scipy import ndimage
from skimage import morphology, measure

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
GLYPHS_DIR = BASE_DIR / "glyphs_improved"

class ImprovedExtractor:
    def __init__(self):
        GLYPHS_DIR.mkdir(exist_ok=True)
        
    def preprocess_advanced(self, image_path):
        """Advanced preprocessing with better noise removal"""
        print(f"Advanced preprocessing of {image_path.name}...")
        
        # Read image
        img = cv2.imread(str(image_path))
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Apply CLAHE for better contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Multi-scale adaptive thresholding
        binary1 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 11, 5)
        binary2 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 21, 8)
        binary3 = cv2.adaptiveThreshold(enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                        cv2.THRESH_BINARY, 31, 10)
        
        # Combine multiple scales
        binary = cv2.bitwise_and(binary1, cv2.bitwise_and(binary2, binary3))
        
        # Invert if needed
        if np.sum(binary == 0) > np.sum(binary == 255):
            binary = cv2.bitwise_not(binary)
        
        # Remove salt and pepper noise
        binary = cv2.medianBlur(binary, 3)
        
        # Morphological cleaning
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        closed = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel_close)
        
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2,2))
        opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, kernel_open)
        
        return opened, enhanced
    
    def detect_text_regions(self, binary_img):
        """Detect text regions using projection profiles and connected components"""
        print("Detecting text regions...")
        
        # Horizontal projection
        h_proj = np.sum(binary_img == 0, axis=1)
        h_smooth = ndimage.gaussian_filter1d(h_proj, sigma=2)
        
        # Find peaks (text lines)
        threshold = np.percentile(h_smooth[h_smooth > 0], 20)
        
        lines = []
        in_line = False
        line_start = 0
        min_line_height = 20
        
        for i, val in enumerate(h_smooth):
            if not in_line and val > threshold:
                in_line = True
                line_start = i
            elif in_line and val <= threshold:
                in_line = False
                if i - line_start >= min_line_height:
                    # Refine line boundaries
                    actual_start = max(0, line_start - 5)
                    actual_end = min(len(h_proj), i + 5)
                    lines.append((actual_start, actual_end))
        
        print(f"Found {len(lines)} text lines")
        return lines
    
    def segment_characters_advanced(self, binary_img, lines):
        """Advanced character segmentation with better handling of touching characters"""
        print("Advanced character segmentation...")
        
        all_characters = []
        char_id = 0
        
        for line_idx, (y1, y2) in enumerate(lines):
            line_img = binary_img[y1:y2, :]
            
            # Use connected components
            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                cv2.bitwise_not(line_img), connectivity=8
            )
            
            # Filter components by size
            line_chars = []
            for i in range(1, num_labels):  # Skip background (0)
                x, y, w, h, area = stats[i]
                
                # Size filters
                if w < 5 or h < 10:  # Too small
                    continue
                if w > 150 or h > 150:  # Too large
                    continue
                if area < 50:  # Too few pixels
                    continue
                
                # Aspect ratio filter (most Greek letters are roughly square)
                aspect = w / h
                if aspect > 3 or aspect < 0.2:  # Too wide or tall
                    continue
                
                # Extract character
                char_mask = (labels == i).astype(np.uint8) * 255
                char_img = line_img[y:y+h, x:x+w]
                char_mask_crop = char_mask[y:y+h, x:x+w]
                
                # Apply mask to get clean character
                char_clean = cv2.bitwise_and(char_img, char_mask_crop)
                
                # Check for omega (double-o pattern)
                is_omega = self.detect_omega_pattern(char_clean, w, h)
                
                line_chars.append({
                    'x': x,
                    'y': y,
                    'w': w,
                    'h': h,
                    'area': area,
                    'image': char_clean,
                    'is_omega': is_omega
                })
            
            # Sort by x position
            line_chars.sort(key=lambda c: c['x'])
            
            # Handle touching characters
            processed_chars = self.split_touching_characters(line_chars, line_img)
            
            # Add to results
            for char_data in processed_chars:
                # Add padding
                pad = 8
                padded = cv2.copyMakeBorder(
                    char_data['image'], pad, pad, pad, pad,
                    cv2.BORDER_CONSTANT, value=255
                )
                
                all_characters.append({
                    'id': char_id,
                    'line': line_idx,
                    'image': padded,
                    'x': char_data['x'],
                    'y': y1 + char_data['y'],
                    'width': char_data['w'],
                    'height': char_data['h'],
                    'quality_score': self.calculate_quality_score(padded),
                    'is_omega': char_data.get('is_omega', False)
                })
                char_id += 1
        
        print(f"Extracted {len(all_characters)} characters")
        
        # Filter by quality
        quality_threshold = 0.3
        good_chars = [c for c in all_characters if c['quality_score'] > quality_threshold]
        print(f"Kept {len(good_chars)} high-quality characters")
        
        return good_chars
    
    def detect_omega_pattern(self, char_img, width, height):
        """Detect if character is omega (double-o pattern)"""
        # Omega is typically wider than tall
        if width / height < 1.3:
            return False
        
        # Check for two connected components (double-o)
        # Apply erosion to potentially separate the two 'o's
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3,3))
        eroded = cv2.erode(cv2.bitwise_not(char_img), kernel, iterations=1)
        
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(eroded, connectivity=8)
        
        # Omega might have 2-3 main components (the two bowls)
        if 2 <= num_labels - 1 <= 3:  # -1 for background
            return True
        
        return False
    
    def split_touching_characters(self, line_chars, line_img):
        """Attempt to split touching characters"""
        processed = []
        
        for char_data in line_chars:
            w, h = char_data['w'], char_data['h']
            
            # Check if likely to be touching characters
            if w / h > 1.8 and not char_data.get('is_omega', False):
                # Try to split using vertical projection
                char_img = char_data['image']
                v_proj = np.sum(char_img == 0, axis=0)
                
                # Find minimum in the middle region
                mid_start = w // 3
                mid_end = 2 * w // 3
                
                if mid_start < mid_end:
                    mid_proj = v_proj[mid_start:mid_end]
                    if len(mid_proj) > 0 and np.min(mid_proj) < np.max(mid_proj) * 0.3:
                        # Found a good split point
                        split_point = mid_start + np.argmin(mid_proj)
                        
                        # Create two characters
                        left_char = char_img[:, :split_point]
                        right_char = char_img[:, split_point:]
                        
                        if left_char.shape[1] > 5 and right_char.shape[1] > 5:
                            processed.append({
                                'x': char_data['x'],
                                'y': char_data['y'],
                                'w': split_point,
                                'h': h,
                                'image': left_char
                            })
                            processed.append({
                                'x': char_data['x'] + split_point,
                                'y': char_data['y'],
                                'w': w - split_point,
                                'h': h,
                                'image': right_char
                            })
                            continue
            
            # No split needed or possible
            processed.append(char_data)
        
        return processed
    
    def calculate_quality_score(self, char_img):
        """Calculate quality score for a character"""
        # Multiple quality metrics
        
        # 1. Ink density (not too light, not too dark)
        ink_ratio = np.sum(char_img == 0) / char_img.size
        density_score = 1.0 - abs(ink_ratio - 0.15) / 0.15  # Optimal around 15%
        
        # 2. Edge clarity (sharp edges)
        edges = cv2.Canny(char_img, 50, 150)
        edge_ratio = np.sum(edges > 0) / char_img.size
        edge_score = min(edge_ratio / 0.05, 1.0)  # More edges = clearer
        
        # 3. Connectivity (should be mostly connected)
        num_labels, _, _, _ = cv2.connectedComponentsWithStats(
            cv2.bitwise_not(char_img), connectivity=8
        )
        connectivity_score = 1.0 / max(num_labels - 1, 1)  # Fewer components = better
        
        # 4. Size consistency
        h, w = char_img.shape
        size_score = 1.0 if 20 < h < 120 and 15 < w < 100 else 0.5
        
        # Combine scores
        quality = (density_score * 0.3 + 
                  edge_score * 0.3 + 
                  connectivity_score * 0.2 + 
                  size_score * 0.2)
        
        return quality
    
    def save_improved_characters(self, characters, source_name, source_image_path):
        """Save improved character extraction with bounding box data"""
        output_dir = GLYPHS_DIR / source_name
        output_dir.mkdir(exist_ok=True)
        
        metadata = []
        saved_count = 0
        
        # Sort by quality score and save best examples
        characters.sort(key=lambda x: x['quality_score'], reverse=True)
        
        for char in characters:  # Save ALL characters
            filename = f"char_{char['id']:04d}_q{int(char['quality_score']*100):02d}.png"
            filepath = output_dir / filename
            
            cv2.imwrite(str(filepath), char['image'])
            
            metadata.append({
                'id': int(char['id']),
                'file': filename,
                'source_image': source_image_path.name,  # Original manuscript image
                'line': int(char['line']),
                'bbox': {  # Bounding box in original image coordinates
                    'x': int(char['x']),
                    'y': int(char['y']),
                    'width': int(char['width']),
                    'height': int(char['height'])
                },
                'quality': float(char['quality_score']),
                'is_omega': bool(char.get('is_omega', False))
            })
            saved_count += 1
        
        # Save metadata with source image reference
        with open(output_dir / 'metadata.json', 'w') as f:
            json.dump({
                'source_image': source_image_path.name,
                'characters': metadata
            }, f, indent=2)
        
        # Save quality statistics
        quality_stats = {
            'total_extracted': len(characters),
            'saved': saved_count,
            'avg_quality': float(np.mean([c['quality_score'] for c in characters])),
            'quality_distribution': {
                'excellent': len([c for c in characters if c['quality_score'] > 0.7]),
                'good': len([c for c in characters if 0.5 < c['quality_score'] <= 0.7]),
                'fair': len([c for c in characters if 0.3 < c['quality_score'] <= 0.5]),
                'poor': len([c for c in characters if c['quality_score'] <= 0.3])
            },
            'omega_detected': len([c for c in characters if c.get('is_omega', False)])
        }
        
        with open(output_dir / 'quality_stats.json', 'w') as f:
            json.dump(quality_stats, f, indent=2)
        
        print(f"Saved {saved_count} characters to {output_dir}")
        print(f"Quality stats: {quality_stats}")
        
        return output_dir

def main():
    print("="*60)
    print("IMPROVED CHARACTER EXTRACTION")
    print("="*60)
    
    extractor = ImprovedExtractor()
    
    for image_path in sorted(DATA_DIR.glob("*.jpg")):
        print(f"\nProcessing {image_path.name}...")
        
        # Advanced preprocessing
        binary, enhanced = extractor.preprocess_advanced(image_path)
        
        # Save preprocessed for inspection
        cv2.imwrite(str(GLYPHS_DIR / f"{image_path.stem}_preprocessed.png"), binary)
        
        # Detect text regions
        lines = extractor.detect_text_regions(binary)
        
        # Advanced segmentation
        characters = extractor.segment_characters_advanced(binary, lines)
        
        # Save with quality metrics and bounding box data
        extractor.save_improved_characters(characters, image_path.stem, image_path)
    
    print("\n" + "="*60)
    print("Improved extraction complete!")
    print(f"Results saved to {GLYPHS_DIR}")

if __name__ == "__main__":
    main()