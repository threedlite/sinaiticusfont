import fontforge
import os
import psMat

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

# Classifications from web tool
classifications = {"ALPHA": ["letter_00030"], "MU": ["letter_00033"], "SIGMA": ["letter_00035"], "OMICRON": ["letter_00042"], "NU": ["letter_00054"], "ETA": ["letter_00055"], "PI": ["letter_00060"], "IOTA": ["letter_00069"], "BETA": ["letter_00098"], "LAMBDA": ["letter_00100"], "RHO": ["letter_00113"], "KAPPA": ["letter_00116"], "CHI": ["letter_00126"], "THETA": ["letter_00223"], "GAMMA": ["letter_00297"], "EPSILON": ["letter_00330"], "OMEGA": ["letter_02320"], "PHI": ["letter_42411"], "XI": ["letter_33764"], "UPSILON": ["letter_24850"], "ZETA": ["letter_36522"], "TAU": ["letter_27128"], "DELTA": ["letter_39319"], "PSI": ["letter_41803"]}

# Cleaned images mapping (for PHI and PSI)
cleaned_images = {"42411": "/tmp/cleaned_PHI_9875.png", "41803": "/tmp/cleaned_PSI_5603.png"}

# Font file to generate
font_file = "sinaiticus_test_20250823_172055.ttf"

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

# Add space character
space_glyph = font.createChar(0x0020, "space")
space_glyph.width = 400

for letter_name, char_ids in classifications.items():
    if letter_name in GREEK_UNICODE:
        char, unicode_val = GREEK_UNICODE[letter_name]
        print("Processing", letter_name, "(" + char + ") with", len(char_ids) if isinstance(char_ids, list) else 1, "characters")
        
        # Create glyph
        glyph = font.createChar(unicode_val, "uni{0:04X}".format(unicode_val))
        
        # Try to import character image
        img_imported = False
        
        if char_ids and len(char_ids) > 0:
            char_id = char_ids[0] if isinstance(char_ids, list) else char_ids
            
            # Remove "letter_" prefix if present
            original_char_id = char_id
            if isinstance(char_id, str) and char_id.startswith('letter_'):
                char_id = char_id.replace('letter_', '')
            
            # Check if we have a cleaned image for this character
            if str(char_id) in cleaned_images:
                img_path = cleaned_images[str(char_id)]
                print("  Using cleaned image:", img_path)
            else:
                # Build normal image path
                img_path = "letters_for_review/letter_" + str(char_id).zfill(5) + ".png"
            
            print("  Looking for:", img_path)
            
            if os.path.exists(img_path):
                try:
                    print("  Importing from", img_path)
                    
                    # Import and trace the outline
                    glyph.importOutlines(img_path)
                    glyph.autoTrace()
                    
                    # For PHI and PSI, scale them up because they're naturally taller
                    # They get compressed when scaled to the same ascender as shorter letters
                    if letter_name in ['PHI', 'PSI']:
                        print("  Scaling up", letter_name, "to preserve natural proportions")
                        # Scale both dimensions equally to maintain aspect ratio
                        # Increase scale by another 5% (2.2 * 1.05 = 2.31)
                        scale_factor = 2.3
                        matrix = psMat.scale(scale_factor)  # Scales both x and y equally
                        glyph.transform(matrix)
                        
                        # Now shift down so it extends below baseline too
                        # With larger scale, need to shift down more
                        shift_down = -500  # Negative moves down
                        matrix2 = psMat.translate(0, shift_down)
                        glyph.transform(matrix2)
                        print("  Scaled", letter_name, "by", scale_factor, "and shifted down by", -shift_down, "units")
                    
                    # For RHO, scale it to extend below baseline but not above
                    elif letter_name == 'RHO':
                        print("  Scaling", letter_name, "to extend below baseline")
                        # RHO should extend below but stay at normal height above
                        # Scale it up but less than PHI/PSI
                        scale_factor = 1.5  # Smaller scale factor than PHI/PSI
                        matrix = psMat.scale(scale_factor)  # Maintains aspect ratio
                        glyph.transform(matrix)
                        
                        # Shift down more to extend further below baseline
                        shift_down = -400  # Much more shift to lower it further
                        matrix2 = psMat.translate(0, shift_down)
                        glyph.transform(matrix2)
                        print("  Scaled", letter_name, "by", scale_factor, "and shifted down by", -shift_down, "units")
                    
                    # Get bounding box for adjustments
                    bbox = glyph.boundingBox()
                    if bbox and len(bbox) >= 4:
                        xmin, ymin, xmax, ymax = bbox
                        glyph_width = xmax - xmin
                        glyph_height = ymax - ymin
                        
                        # Debug output for PHI and PSI
                        if letter_name in ['PHI', 'PSI']:
                            print("  ", letter_name, "bounding box after import:", xmin, ymin, xmax, ymax)
                            print("  ", letter_name, "height:", glyph_height)
                        
                        # Set horizontal spacing
                        glyph.left_side_bearing = 60
                        glyph.width = int(glyph_width + 120)
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
        
        # Create placeholder if no image
        if not img_imported:
            print("  Creating placeholder for", letter_name)
            pen = glyph.glyphPen()
            pen.moveTo((100, 100))
            pen.lineTo((400, 100))
            pen.lineTo((400, 500))
            pen.lineTo((100, 500))
            pen.closePath()
            glyph.width = 600
            glyph.left_side_bearing = 50
            placeholder_count += 1
        
        # Add lowercase reference
        lowercase_unicode = unicode_val + 0x20
        if lowercase_unicode <= 0x03C9:
            lowercase_glyph = font.createChar(lowercase_unicode, "uni{0:04X}".format(lowercase_unicode))
            lowercase_glyph.addReference("uni{0:04X}".format(unicode_val))
            lowercase_glyph.width = glyph.width

print("\nSummary:", added_count, "letters from images,", placeholder_count, "placeholders")

# Add punctuation marks
print("\nAdding punctuation marks...")

# Period (.)
period_glyph = font.createChar(0x002E, "period")
pen = period_glyph.glyphPen()
# Create a small, slightly irregular dot shape like manuscript
center_x, center_y = 300, 100
# Larger irregular blob (2x size)
pen.moveTo((center_x - 80, center_y + 10))
pen.lineTo((center_x - 84, center_y + 50))
pen.lineTo((center_x - 70, center_y + 76))
pen.lineTo((center_x - 40, center_y + 84))
pen.lineTo((center_x - 10, center_y + 80))
pen.lineTo((center_x + 30, center_y + 70))
pen.lineTo((center_x + 60, center_y + 44))
pen.lineTo((center_x + 76, center_y + 16))
pen.lineTo((center_x + 80, center_y - 20))
pen.lineTo((center_x + 70, center_y - 56))
pen.lineTo((center_x + 44, center_y - 76))
pen.lineTo((center_x + 10, center_y - 84))
pen.lineTo((center_x - 24, center_y - 80))
pen.lineTo((center_x - 56, center_y - 64))
pen.lineTo((center_x - 76, center_y - 30))
pen.closePath()
period_glyph.width = 600
print("  ✓ Added period (.) with manuscript-style shape")

# Semicolon (;)
semicolon_glyph = font.createChar(0x003B, "semicolon")
pen = semicolon_glyph.glyphPen()
# Upper dot - larger irregular shape at mid-height (2x size)
center_x, center_y = 300, 400
pen.moveTo((center_x - 80, center_y + 10))
pen.lineTo((center_x - 84, center_y + 50))
pen.lineTo((center_x - 70, center_y + 76))
pen.lineTo((center_x - 40, center_y + 84))
pen.lineTo((center_x - 10, center_y + 80))
pen.lineTo((center_x + 30, center_y + 70))
pen.lineTo((center_x + 60, center_y + 44))
pen.lineTo((center_x + 76, center_y + 16))
pen.lineTo((center_x + 80, center_y - 20))
pen.lineTo((center_x + 70, center_y - 56))
pen.lineTo((center_x + 44, center_y - 76))
pen.lineTo((center_x + 10, center_y - 84))
pen.lineTo((center_x - 24, center_y - 80))
pen.lineTo((center_x - 56, center_y - 64))
pen.lineTo((center_x - 76, center_y - 30))
pen.closePath()
# Lower comma part
pen.moveTo((280, 100))
pen.curveTo((275, 60), (290, -30), (310, -80))
pen.curveTo((315, -90), (320, -95), (325, -90))
pen.curveTo((335, -80), (340, -40), (335, 20))
pen.curveTo((332, 80), (315, 105), (295, 100))
pen.curveTo((285, 98), (280, 100), (280, 100))
pen.closePath()
semicolon_glyph.width = 600
print("  ✓ Added semicolon (;) with larger manuscript style")

# Raised/Middle dot (·) - Unicode U+00B7
raised_dot_glyph = font.createChar(0x00B7, "periodcentered")
pen = raised_dot_glyph.glyphPen()
# Create a larger irregular dot shape at mid-height (2x size)
center_x, center_y = 300, 400  # Mid-height
# Larger irregular blob (2x size)
pen.moveTo((center_x - 80, center_y + 10))
pen.lineTo((center_x - 84, center_y + 50))
pen.lineTo((center_x - 70, center_y + 76))
pen.lineTo((center_x - 40, center_y + 84))
pen.lineTo((center_x - 10, center_y + 80))
pen.lineTo((center_x + 30, center_y + 70))
pen.lineTo((center_x + 60, center_y + 44))
pen.lineTo((center_x + 76, center_y + 16))
pen.lineTo((center_x + 80, center_y - 20))
pen.lineTo((center_x + 70, center_y - 56))
pen.lineTo((center_x + 44, center_y - 76))
pen.lineTo((center_x + 10, center_y - 84))
pen.lineTo((center_x - 24, center_y - 80))
pen.lineTo((center_x - 56, center_y - 64))
pen.lineTo((center_x - 76, center_y - 30))
pen.closePath()
raised_dot_glyph.width = 600
print("  ✓ Added raised dot (·) with manuscript-style shape")

# Also add Greek ano teleia (·) - Unicode U+0387 (Greek semicolon/raised dot)
# This is the Greek-specific middle dot!
greek_raised_dot_glyph = font.createChar(0x0387, "anoteleia")
greek_raised_dot_glyph.addReference("periodcentered")
greek_raised_dot_glyph.width = 600
print("  ✓ Added Greek ano teleia (·) - Greek middle dot")

# Add Greek lower numeral sign - Unicode U+0375
greek_lower_numeral_glyph = font.createChar(0x0375, "uni0375")
pen = greek_lower_numeral_glyph.glyphPen()
# Position at baseline like period
center_x, center_y = 300, 100
# Same irregular blob shape
pen.moveTo((center_x - 80, center_y + 10))
pen.lineTo((center_x - 84, center_y + 50))
pen.lineTo((center_x - 70, center_y + 76))
pen.lineTo((center_x - 40, center_y + 84))
pen.lineTo((center_x - 10, center_y + 80))
pen.lineTo((center_x + 30, center_y + 70))
pen.lineTo((center_x + 60, center_y + 44))
pen.lineTo((center_x + 76, center_y + 16))
pen.lineTo((center_x + 80, center_y - 20))
pen.lineTo((center_x + 70, center_y - 56))
pen.lineTo((center_x + 44, center_y - 76))
pen.lineTo((center_x + 10, center_y - 84))
pen.lineTo((center_x - 24, center_y - 80))
pen.lineTo((center_x - 56, center_y - 64))
pen.lineTo((center_x - 76, center_y - 30))
pen.closePath()
greek_lower_numeral_glyph.width = 600
print("  ✓ Added Greek lower numeral sign")

# Add high dot (˙) - Unicode U+02D9 (dot above)
high_dot_glyph = font.createChar(0x02D9, "dotaccent")
pen = high_dot_glyph.glyphPen()
# Higher position than raised dot
center_x, center_y = 300, 550  # Higher than mid-height
# Same irregular blob shape
pen.moveTo((center_x - 80, center_y + 10))
pen.lineTo((center_x - 84, center_y + 50))
pen.lineTo((center_x - 70, center_y + 76))
pen.lineTo((center_x - 40, center_y + 84))
pen.lineTo((center_x - 10, center_y + 80))
pen.lineTo((center_x + 30, center_y + 70))
pen.lineTo((center_x + 60, center_y + 44))
pen.lineTo((center_x + 76, center_y + 16))
pen.lineTo((center_x + 80, center_y - 20))
pen.lineTo((center_x + 70, center_y - 56))
pen.lineTo((center_x + 44, center_y - 76))
pen.lineTo((center_x + 10, center_y - 84))
pen.lineTo((center_x - 24, center_y - 80))
pen.lineTo((center_x - 56, center_y - 64))
pen.lineTo((center_x - 76, center_y - 30))
pen.closePath()
high_dot_glyph.width = 600
print("  ✓ Added high dot (˙)")

# Add bullet operator (•) - Unicode U+2022
bullet_glyph = font.createChar(0x2022, "bullet")
bullet_glyph.addReference("periodcentered")  # Same as middle dot
bullet_glyph.width = 600
print("  ✓ Added bullet (•)")

# Generate font
print("Generating font:", font_file)
font.generate(font_file)
font.close()

print("Font generated successfully!")
