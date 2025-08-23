#!/usr/bin/env python3
"""
Test the extraction pipeline with bounding box generation
"""

import sys
from pathlib import Path

# Add scripts directory to path
sys.path.append(str(Path(__file__).parent / "scripts"))

from improved_extraction import ImprovedExtractor
import json

def test_extraction():
    """Test extraction on a single manuscript page"""
    
    # Use the first available manuscript image
    DATA_DIR = Path(__file__).parent / "data"
    image_files = list(DATA_DIR.glob("*.jpg"))
    
    if not image_files:
        print("No manuscript images found in data/")
        return
    
    # Use first image for testing
    test_image = image_files[0]
    print(f"Testing extraction on: {test_image.name}")
    
    # Run extraction
    extractor = ImprovedExtractor()
    
    # Preprocess
    binary, enhanced = extractor.preprocess_advanced(test_image)
    
    # Detect lines
    lines = extractor.detect_text_regions(binary)
    
    # Segment characters
    characters = extractor.segment_characters_advanced(binary, lines)
    
    # Save with bounding boxes
    output_dir = extractor.save_improved_characters(characters, test_image.stem, test_image)
    
    # Check the metadata file
    metadata_file = output_dir / "metadata.json"
    if metadata_file.exists():
        with open(metadata_file, 'r') as f:
            metadata = json.load(f)
        
        print(f"\nMetadata structure:")
        print(f"Source image: {metadata.get('source_image', 'Not found')}")
        
        if 'characters' in metadata and metadata['characters']:
            first_char = metadata['characters'][0]
            print(f"\nFirst character data:")
            print(json.dumps(first_char, indent=2))
            
            if 'bbox' in first_char:
                print(f"\n✅ Bounding box data found!")
                print(f"   x: {first_char['bbox']['x']}")
                print(f"   y: {first_char['bbox']['y']}")
                print(f"   width: {first_char['bbox']['width']}")
                print(f"   height: {first_char['bbox']['height']}")
            else:
                print("\n❌ No bounding box data found")
    else:
        print(f"❌ Metadata file not found at {metadata_file}")

if __name__ == "__main__":
    test_extraction()