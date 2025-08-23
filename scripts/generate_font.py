#!/usr/bin/env python3
"""
Generate a TrueType font from vectorized characters
Uses FontForge's Python scripting interface
"""

import os
import sys
import subprocess
from pathlib import Path
import json

# Add FontForge Python path
sys.path.insert(0, '/opt/homebrew/lib/python3.12/site-packages')
sys.path.insert(0, '/opt/homebrew/lib/python3.11/site-packages')
sys.path.insert(0, '/opt/homebrew/Cellar/fontforge/20230101/lib/python3.11/site-packages')

try:
    import fontforge
except ImportError:
    print("FontForge Python module not found.")
    print("Trying to run with fontforge -script instead...")
    # Will handle this below
    fontforge = None

BASE_DIR = Path(__file__).parent.parent
VECTORS_DIR = BASE_DIR / "vectors"
BUILD_DIR = BASE_DIR / "build"

def create_font_with_fontforge():
    """Create font using FontForge Python API"""
    
    print("Creating font with FontForge...")
    
    # Create new font
    font = fontforge.font()
    font.fontname = "CodexSinaiticus"
    font.fullname = "Codex Sinaiticus"
    font.familyname = "Codex Sinaiticus"
    font.copyright = "Generated from Codex Sinaiticus manuscript (4th century CE)"
    font.version = "0.1"
    
    # Set font metrics
    font.ascent = 800
    font.descent = 200
    font.em = 1000
    
    # Greek capital letters mapping
    # Using the most common characters we can identify
    greek_capitals = {
        'ALPHA': 0x0391,
        'BETA': 0x0392,
        'GAMMA': 0x0393,
        'DELTA': 0x0394,
        'EPSILON': 0x0395,
        'ZETA': 0x0396,
        'ETA': 0x0397,
        'THETA': 0x0398,
        'IOTA': 0x0399,
        'KAPPA': 0x039A,
        'LAMBDA': 0x039B,
        'MU': 0x039C,
        'NU': 0x039D,
        'XI': 0x039E,
        'OMICRON': 0x039F,
        'PI': 0x03A0,
        'RHO': 0x03A1,
        'SIGMA': 0x03A3,
        'TAU': 0x03A4,
        'UPSILON': 0x03A5,
        'PHI': 0x03A6,
        'CHI': 0x03A7,
        'PSI': 0x03A8,
        'OMEGA': 0x03A9,
    }
    
    # Find SVG files
    svg_files = []
    for vector_dir in VECTORS_DIR.glob("*"):
        if vector_dir.is_dir():
            svg_files.extend(list(vector_dir.glob("*.svg")))
    
    if not svg_files:
        print("No SVG files found. Run vectorization first.")
        return None
    
    print(f"Found {len(svg_files)} SVG files")
    
    # Import first N characters as different Greek letters
    # This is a proof of concept - in production you'd need proper classification
    for idx, (name, unicode_point) in enumerate(greek_capitals.items()):
        if idx < len(svg_files):
            svg_file = svg_files[idx]
            
            print(f"  Adding {name} (U+{unicode_point:04X}) from {svg_file.name}")
            
            # Create glyph
            glyph = font.createChar(unicode_point, name)
            
            try:
                # Import the SVG outline
                glyph.importOutlines(str(svg_file))
                
                # Scale to fit em square
                bbox = glyph.boundingBox()
                if bbox[3] - bbox[1] > 0:  # Has height
                    scale_factor = 700 / (bbox[3] - bbox[1])  # Scale to cap height
                    matrix = fontforge.psMat.scale(scale_factor, scale_factor)
                    glyph.transform(matrix)
                
                # Center horizontally
                glyph.width = 600
                
                # Simplify the glyph
                glyph.simplify()
                glyph.round()
                
            except Exception as e:
                print(f"    Warning: Could not import {svg_file.name}: {e}")
    
    # Add basic Latin characters for testing
    test_text = "CODEX SINAITICUS"
    for char in test_text:
        if char != ' ':
            unicode_point = ord(char)
            if unicode_point not in [g.unicode for g in font.glyphs()]:
                glyph = font.createChar(unicode_point)
                # Create a simple rectangle as placeholder
                pen = glyph.glyphPen()
                pen.moveTo((100, 0))
                pen.lineTo((100, 700))
                pen.lineTo((500, 700))
                pen.lineTo((500, 0))
                pen.closePath()
                glyph.width = 600
    
    # Add space character
    space = font.createChar(32, "space")
    space.width = 300
    
    # Generate font file
    output_file = BUILD_DIR / "CodexSinaiticus.ttf"
    BUILD_DIR.mkdir(exist_ok=True)
    
    print(f"Generating font file: {output_file}")
    font.generate(str(output_file))
    
    # Also generate a web font
    woff_file = BUILD_DIR / "CodexSinaiticus.woff"
    font.generate(str(woff_file))
    
    print(f"✓ Font generated successfully: {output_file}")
    print(f"✓ Web font generated: {woff_file}")
    
    return output_file

def create_font_with_script():
    """Alternative: Create font using FontForge command line"""
    
    script_content = '''
import fontforge
import sys
from pathlib import Path

BASE_DIR = Path(sys.argv[1])
VECTORS_DIR = BASE_DIR / "vectors"
BUILD_DIR = BASE_DIR / "build"

font = fontforge.font()
font.fontname = "CodexSinaiticus"
font.fullname = "Codex Sinaiticus"
font.familyname = "Codex Sinaiticus"
font.ascent = 800
font.descent = 200

# Find and import SVG files
svg_files = []
for vector_dir in VECTORS_DIR.glob("*"):
    if vector_dir.is_dir():
        svg_files.extend(list(vector_dir.glob("*.svg")))

# Map to Greek capitals
for idx in range(min(24, len(svg_files))):
    unicode_point = 0x0391 + idx  # Start from Greek Alpha
    glyph = font.createChar(unicode_point)
    try:
        glyph.importOutlines(str(svg_files[idx]))
        glyph.width = 600
    except:
        pass

# Add space
space = font.createChar(32)
space.width = 300

# Generate font
BUILD_DIR.mkdir(exist_ok=True)
font.generate(str(BUILD_DIR / "CodexSinaiticus.ttf"))
print("Font generated successfully")
'''
    
    # Save script
    script_file = BASE_DIR / "scripts" / "fontforge_script.py"
    with open(script_file, 'w') as f:
        f.write(script_content)
    
    # Run with fontforge
    result = subprocess.run(
        ['fontforge', '-script', str(script_file), str(BASE_DIR)],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✓ Font generated successfully using FontForge script")
        return BUILD_DIR / "CodexSinaiticus.ttf"
    else:
        print(f"Error: {result.stderr}")
        return None

def main():
    print("="*50)
    print("Font Generation")
    print("="*50)
    
    if fontforge:
        font_file = create_font_with_fontforge()
    else:
        print("Using FontForge command-line interface...")
        font_file = create_font_with_script()
    
    if font_file and font_file.exists():
        print(f"\n✓ Success! Font file created: {font_file}")
        print(f"  Size: {font_file.stat().st_size:,} bytes")
    else:
        print("\n✗ Font generation failed")
        print("  Make sure SVG files exist in vectors/ directory")

if __name__ == "__main__":
    main()