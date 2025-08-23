#!/usr/bin/env python3
"""
Direct font creation from review data - no server needed
"""
import json
import fontforge
import os
from datetime import datetime

# Load the review data
with open('review_data_2025-08-23.json', 'r') as f:
    review_data = json.load(f)

# Build classifications from review data
classifications = {}
for item in review_data:
    if item.get('classification') and item['classification'] not in ['UNCLASSIFIED', 'NON_LETTER', None]:
        letter = item['classification']
        if letter not in classifications:
            classifications[letter] = []
        # Store the ID without the "letter_" prefix
        char_id = item['id'].replace('letter_', '')
        classifications[letter].append(char_id)

print(f"Found {len(classifications)} letters in review data:")
for letter, ids in sorted(classifications.items()):
    print(f"  {letter}: {len(ids)} characters")

# Greek letter mappings
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

# Create font
font = fontforge.font()
font.familyname = "Sinaiticus"
font.fullname = "Sinaiticus Test"
font.copyright = "Generated from manuscript samples"
font.version = "1.0"

# Set font metrics
font.ascent = 800
font.descent = 200
font.em = 1000

print("\nGenerating font glyphs...")
added_count = 0
placeholder_count = 0

for letter_name in sorted(classifications.keys()):
    if letter_name in GREEK_UNICODE:
        char, unicode_val = GREEK_UNICODE[letter_name]
        char_ids = classifications[letter_name]
        
        print(f"\nProcessing {letter_name} ({char}):")
        
        # Create glyph
        glyph = font.createChar(unicode_val)
        
        # Use first character image
        if char_ids:
            char_id = char_ids[0]
            img_path = f"letters_for_review/letter_{str(char_id).zfill(5)}.png"
            
            print(f"  Looking for: {img_path}")
            
            if os.path.exists(img_path):
                try:
                    print(f"  Importing image...")
                    glyph.importOutlines(img_path)
                    glyph.autoTrace()
                    
                    # Set width
                    bbox = glyph.boundingBox()
                    if bbox and len(bbox) >= 4:
                        xmin, ymin, xmax, ymax = bbox
                        glyph_width = xmax - xmin
                        glyph.left_side_bearing = 60
                        glyph.width = int(glyph_width + 120)
                    else:
                        glyph.width = 600
                    
                    glyph.simplify()
                    glyph.correctDirection()
                    added_count += 1
                    print(f"  ✓ Successfully added to font")
                except Exception as e:
                    print(f"  ✗ Error: {e}")
                    placeholder_count += 1
            else:
                print(f"  ✗ Image not found")
                placeholder_count += 1
        
        # Add lowercase reference
        lowercase_unicode = unicode_val + 0x20
        if lowercase_unicode <= 0x03C9:
            lowercase_glyph = font.createChar(lowercase_unicode)
            lowercase_glyph.addReference(glyph.glyphname)
            lowercase_glyph.width = glyph.width

print(f"\nSummary: {added_count} letters imported, {placeholder_count} placeholders")

# Generate font file
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
font_file = f'sinaiticus_direct_{timestamp}.ttf'
print(f"\nGenerating font file: {font_file}")
font.generate(font_file)
font.close()

print(f"✓ Font created successfully: {font_file}")
print(f"\nTo test the font, open test_fixed_font.html and update the font source to '{font_file}'")