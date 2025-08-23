#!/usr/bin/env python3
"""
Create a test font with proper glyphs from reviewed characters
"""

import fontforge
import sys
import os
from pathlib import Path

# Greek letter to Unicode mapping
GREEK_UNICODE = {
    'ALPHA': ('Α', 0x0391), 'BETA': ('Β', 0x0392), 'GAMMA': ('Γ', 0x0393),
    'DELTA': ('Δ', 0x0394), 'EPSILON': ('Ε', 0x0395), 'ZETA': ('Ζ', 0x0396),
    'ETA': ('Η', 0x0397), 'THETA': ('Θ', 0x0398), 'IOTA': ('Ι', 0x0399),
    'KAPPA': ('Κ', 0x039A), 'LAMBDA': ('Λ', 0x039B), 'MU': ('Μ', 0x039C),
    'NU': ('Ν', 0x039D), 'XI': ('Ξ', 0x039E), 'OMICRON': ('Ο', 0x039F),
    'PI': ('Π', 0x03A0), 'RHO': ('Ρ', 0x03A1), 'SIGMA': ('Σ', 0x03A3),
    'TAU': ('Τ', 0x03A4), 'UPSILON': ('Υ', 0x03A5), 'PHI': ('Φ', 0x03A6),
    'CHI': ('Χ', 0x03A7), 'PSI': ('Ψ', 0x03A8), 'OMEGA': ('Ω', 0x03A9)
}

def create_simple_glyph(glyph, letter_name):
    """Create a simple placeholder glyph that will render properly"""
    
    # Create a simple letter shape based on the letter
    pen = glyph.glyphPen()
    
    if letter_name == 'ALPHA':
        # Simple A shape
        pen.moveTo((100, 0))
        pen.lineTo((300, 600))
        pen.lineTo((500, 0))
        pen.lineTo((400, 0))
        pen.lineTo((350, 200))
        pen.lineTo((250, 200))
        pen.lineTo((200, 0))
        pen.closePath()
        pen.moveTo((275, 300))
        pen.lineTo((325, 300))
        pen.lineTo((300, 400))
        pen.closePath()
    elif letter_name == 'BETA':
        # Simple B shape
        pen.moveTo((100, 0))
        pen.lineTo((100, 600))
        pen.lineTo((350, 600))
        pen.curveTo((450, 600), (500, 550), (500, 450))
        pen.curveTo((500, 350), (450, 325), (375, 325))
        pen.curveTo((450, 300), (500, 250), (500, 150))
        pen.curveTo((500, 50), (450, 0), (350, 0))
        pen.closePath()
    elif letter_name == 'GAMMA':
        # Simple Gamma shape
        pen.moveTo((100, 0))
        pen.lineTo((100, 600))
        pen.lineTo((500, 600))
        pen.lineTo((500, 500))
        pen.lineTo((200, 500))
        pen.lineTo((200, 0))
        pen.closePath()
    elif letter_name == 'DELTA':
        # Simple triangle
        pen.moveTo((50, 0))
        pen.lineTo((300, 600))
        pen.lineTo((550, 0))
        pen.closePath()
    elif letter_name == 'OMEGA':
        # Simple omega shape
        pen.moveTo((100, 0))
        pen.lineTo((100, 100))
        pen.curveTo((100, 400), (150, 500), (250, 500))
        pen.curveTo((300, 500), (300, 400), (300, 300))
        pen.curveTo((300, 400), (300, 500), (350, 500))
        pen.curveTo((450, 500), (500, 400), (500, 100))
        pen.lineTo((500, 0))
        pen.lineTo((400, 0))
        pen.lineTo((400, 100))
        pen.curveTo((400, 300), (375, 400), (350, 400))
        pen.curveTo((325, 400), (300, 300), (300, 200))
        pen.curveTo((300, 300), (275, 400), (250, 400))
        pen.curveTo((225, 400), (200, 300), (200, 100))
        pen.lineTo((200, 0))
        pen.closePath()
    else:
        # Default square shape for other letters
        pen.moveTo((100, 0))
        pen.lineTo((100, 600))
        pen.lineTo((500, 600))
        pen.lineTo((500, 0))
        pen.closePath()
        # Add inner hole to make it render properly
        pen.moveTo((200, 100))
        pen.lineTo((400, 100))
        pen.lineTo((400, 500))
        pen.lineTo((200, 500))
        pen.closePath()
    
    pen = None
    
    # Set width
    glyph.width = 600
    
    # Correct direction and simplify
    glyph.correctDirection()
    glyph.simplify()

def main():
    output_file = sys.argv[1] if len(sys.argv) > 1 else "test_font_fixed.ttf"
    
    print(f"Creating font: {output_file}")
    
    # Create font
    font = fontforge.font()
    font.familyname = "Sinaiticus"
    font.fontname = "Sinaiticus-Test"
    font.fullname = "Sinaiticus Test"
    font.copyright = "Based on Codex Sinaiticus"
    font.version = "1.0"
    
    # Set font metrics
    font.ascent = 800
    font.descent = 200
    font.em = 1000
    
    # Add space character first
    space = font.createChar(0x0020, "space")
    space.width = 400
    
    # Add all Greek letters
    for letter_name, (char, unicode_val) in GREEK_UNICODE.items():
        print(f"Adding {letter_name} ({char})...")
        
        # Create glyph
        glyph = font.createChar(unicode_val, f"uni{unicode_val:04X}")
        
        # Try to import from actual character images
        imported = False
        possible_paths = [
            f"letters_for_review/letter_*.png",
            f"glyphs_improved/*/char_*.png"
        ]
        
        import glob
        for pattern in possible_paths[:1]:  # Just check first pattern for now
            matches = glob.glob(pattern)
            if matches and len(matches) > unicode_val % len(matches):
                img_path = matches[unicode_val % len(matches)]
                if os.path.exists(img_path):
                    try:
                        glyph.importOutlines(img_path)
                        glyph.autoTrace()
                        glyph.width = 600
                        glyph.correctDirection()
                        glyph.simplify()
                        imported = True
                        print(f"  Imported from {img_path}")
                        break
                    except Exception as e:
                        print(f"  Could not import: {e}")
        
        if not imported:
            # Create simple placeholder glyph
            create_simple_glyph(glyph, letter_name)
            print(f"  Created placeholder glyph")
        
        # Add lowercase version
        lowercase_unicode = unicode_val + 0x20
        if lowercase_unicode <= 0x03C9:
            lowercase = font.createChar(lowercase_unicode, f"uni{lowercase_unicode:04X}")
            lowercase.addReference(f"uni{unicode_val:04X}")
            lowercase.width = glyph.width
    
    # Add basic ASCII for testing
    for i in range(0x0041, 0x005B):  # A-Z
        ascii_glyph = font.createChar(i)
        # Map to corresponding Greek if possible
        greek_offset = i - 0x0041  # 0 for A, 1 for B, etc.
        if greek_offset < len(GREEK_UNICODE):
            greek_unicode = 0x0391 + greek_offset
            if greek_unicode in font:
                ascii_glyph.addReference(f"uni{greek_unicode:04X}")
                ascii_glyph.width = font[greek_unicode].width
    
    # Generate font
    print(f"Generating {output_file}...")
    font.generate(output_file)
    font.close()
    
    print(f"Font created: {output_file}")
    print(f"File size: {os.path.getsize(output_file)} bytes")

if __name__ == "__main__":
    main()