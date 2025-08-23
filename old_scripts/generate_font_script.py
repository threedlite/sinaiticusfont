#!/usr/bin/env python3
"""Generate the FontForge script properly"""

import json

def generate_fontforge_script(classifications, font_file):
    """Generate a FontForge Python script as a string"""
    
    # Convert classifications to JSON for embedding
    classifications_json = json.dumps(classifications)
    
    # Create the script using regular string concatenation to avoid f-string issues
    script = '''import fontforge
import os

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

# Classifications from the web tool
classifications = ''' + classifications_json + '''

# Font file to generate  
font_file = "''' + font_file + '''"

print("Received classifications for:", list(classifications.keys()))

# Create font
font = fontforge.font()
font.familyname = "Sinaiticus"
font.fontname = "Sinaiticus-Review"
font.fullname = "Sinaiticus Review"
font.copyright = "From manuscript review"
font.version = "1.0"

# Set font metrics
font.ascent = 800
font.descent = 200
font.em = 1000

added_count = 0
placeholder_count = 0

# Add space character first
space_glyph = font.createChar(0x0020, "space")
space_glyph.width = 400

for letter_name, char_ids in classifications.items():
    if letter_name in GREEK_UNICODE:
        char, unicode_val = GREEK_UNICODE[letter_name]
        print("Processing", letter_name, "(" + char + ") with", len(char_ids) if isinstance(char_ids, list) else 1, "character(s)")
        
        # Create glyph
        glyph = font.createChar(unicode_val, "uni{0:04X}".format(unicode_val))
        
        # Try to import character image from the reviewed characters
        img_imported = False
        
        if char_ids and len(char_ids) > 0:
            # Use first character ID from the review
            char_id = char_ids[0] if isinstance(char_ids, list) else char_ids
            
            # Remove "letter_" prefix if present and convert to number
            if isinstance(char_id, str) and char_id.startswith('letter_'):
                char_id = char_id.replace('letter_', '')
            
            # Convert character ID to the image filename
            img_path = "letters_for_review/letter_" + str(char_id).zfill(5) + ".png"
            
            print("  Looking for:", img_path)
            
            if os.path.exists(img_path):
                try:
                    print("  Importing from", img_path)
                    glyph.importOutlines(img_path)
                    glyph.autoTrace()
                    
                    # Set proper spacing
                    bbox = glyph.boundingBox()
                    if bbox and len(bbox) >= 4:
                        xmin, ymin, xmax, ymax = bbox
                        glyph_width = xmax - xmin
                        
                        # Set spacing
                        left_bearing = 60
                        right_bearing = 60
                        
                        glyph.left_side_bearing = int(left_bearing)
                        glyph.width = int(glyph_width + left_bearing + right_bearing)
                    else:
                        glyph.width = 600
                        glyph.left_side_bearing = 50
                    
                    glyph.simplify()
                    glyph.correctDirection()
                    added_count += 1
                    img_imported = True
                    print("  ✓ Successfully imported")
                except Exception as e:
                    print("  ✗ Error importing:", str(e))
            else:
                print("  ✗ File not found")
        
        # If no image, create simple placeholder
        if not img_imported:
            print("  Creating placeholder for", letter_name)
            pen = glyph.glyphPen()
            # Simple rectangle placeholder
            pen.moveTo((100, 100))
            pen.lineTo((400, 100))
            pen.lineTo((400, 500))
            pen.lineTo((100, 500))
            pen.closePath()
            glyph.width = 600
            glyph.left_side_bearing = 50
            placeholder_count += 1
        
        # Add lowercase version (reference to uppercase)
        lowercase_unicode = unicode_val + 0x20
        if lowercase_unicode <= 0x03C9:
            lowercase_glyph = font.createChar(lowercase_unicode, "uni{0:04X}".format(lowercase_unicode))
            lowercase_glyph.addReference("uni{0:04X}".format(unicode_val))
            lowercase_glyph.width = glyph.width

print("\\nSummary:", added_count, "letters from reviewed images,", placeholder_count, "placeholders")

# Generate font
print("Generating font:", font_file)
font.generate(font_file)
font.close()

print("Font generated successfully!")
'''
    
    return script

# Test it
if __name__ == "__main__":
    test_classifications = {"ALPHA": ["letter_59"], "BETA": ["letter_98"]}
    script = generate_fontforge_script(test_classifications, "test.ttf")
    print("Generated script length:", len(script))
    print("First 500 chars:")
    print(script[:500])