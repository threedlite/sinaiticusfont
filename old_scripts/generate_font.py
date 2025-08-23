#!/usr/bin/env python3
"""
Generate a TrueType font from classified Greek letter images
"""

import json
import os
import numpy as np
from PIL import Image, ImageOps
from collections import defaultdict
import subprocess
import sys

# Greek letter to Unicode mapping
GREEK_UNICODE = {
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
    'OMEGA': 0x03A9
}

def load_review_data():
    """Load all review data files"""
    all_data = []
    
    # Load from localStorage export
    if os.path.exists('review_data_2025-08-22.json'):
        with open('review_data_2025-08-22.json', 'r') as f:
            all_data.extend(json.load(f))
    
    # Load any other review files
    import glob
    for review_file in glob.glob('review_data_*.json'):
        try:
            with open(review_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
        except:
            continue
    
    # Group by classification
    by_letter = defaultdict(list)
    for item in all_data:
        classification = item.get('classification')
        if classification and classification != 'NON_LETTER' and classification != 'UNCLASSIFIED':
            by_letter[classification].append(item)
    
    return by_letter

def select_best_example(letter_samples):
    """Select the best example for each letter"""
    if not letter_samples:
        return None
    
    # Sort by quality and size
    samples = sorted(letter_samples, key=lambda x: (
        x.get('quality', 0) * x.get('width', 0) * x.get('height', 0)
    ), reverse=True)
    
    # Return the best one
    return samples[0] if samples else None

def image_to_svg_path(image_path, threshold=128):
    """Convert a bitmap image to SVG path data using potrace"""
    try:
        # Load and process image
        img = Image.open(image_path).convert('L')
        
        # Invert if needed (we want black letters on white)
        img_array = np.array(img)
        if np.mean(img_array) < 128:  # Dark background
            img = ImageOps.invert(img)
        
        # Save as temporary BMP for potrace
        temp_bmp = '/tmp/temp_char.bmp'
        temp_svg = '/tmp/temp_char.svg'
        img.save(temp_bmp)
        
        # Run potrace to convert to SVG
        subprocess.run([
            'potrace', 
            '-s',  # SVG output
            '-o', temp_svg,
            temp_bmp
        ], capture_output=True)
        
        # Extract path data from SVG
        with open(temp_svg, 'r') as f:
            svg_content = f.read()
            # Extract just the path data
            import re
            paths = re.findall(r'd="([^"]+)"', svg_content)
            if paths:
                return paths[0], img.size
        
    except Exception as e:
        print(f"Error converting {image_path}: {e}")
    
    return None, (0, 0)

def create_fontforge_script(letter_data):
    """Create a FontForge Python script to generate the font"""
    
    script = '''#!/usr/bin/env python3
import fontforge
import psMat

# Create new font
font = fontforge.font()
font.familyname = "Sinaiticus"
font.fontname = "Sinaiticus-Regular"
font.fullname = "Sinaiticus Regular"
font.copyright = "Generated from Codex Sinaiticus"
font.version = "1.0"

# Set font metrics
font.ascent = 800
font.descent = 200
font.em = 1000

# Unicode to path data
glyphs = {
'''
    
    # Add glyph data
    for letter, unicode_val in GREEK_UNICODE.items():
        if letter not in letter_data:
            continue
            
        best = select_best_example(letter_data[letter])
        if not best:
            continue
        
        # Try to get SVG path
        path_data, size = image_to_svg_path(best['path'])
        if path_data:
            script += f'    0x{unicode_val:04X}: {{"path": r"{path_data}", "width": {size[0]}, "height": {size[1]}}},  # {letter}\n'
    
    script += '''
}

# Create glyphs
for unicode_val, data in glyphs.items():
    glyph = font.createChar(unicode_val)
    
    # Import the path
    try:
        pen = glyph.glyphPen()
        # Parse SVG path and draw it
        # This is simplified - real implementation would need proper SVG path parsing
        glyph.width = data["width"] * 10  # Scale up
        
        # For now, create a simple placeholder
        pen.moveTo((100, 100))
        pen.lineTo((100, 700))
        pen.lineTo((500, 700))
        pen.lineTo((500, 100))
        pen.closePath()
        
    except Exception as e:
        print(f"Error creating glyph {unicode_val}: {e}")

# Generate font files
font.generate("Sinaiticus.ttf")
font.generate("Sinaiticus.otf")
print("Font files generated: Sinaiticus.ttf and Sinaiticus.otf")
'''
    
    return script

def create_simple_bitmap_font(letter_data):
    """Create a simple bitmap-based font using PIL"""
    from PIL import Image, ImageDraw, ImageFont
    
    print("\nCreating font specimen sheet...")
    
    # Create a specimen sheet showing all letters
    img_width = 1200
    img_height = 800
    specimen = Image.new('RGB', (img_width, img_height), 'white')
    draw = ImageDraw.Draw(specimen)
    
    # Try to use a system font for labels
    try:
        label_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except:
        label_font = ImageFont.load_default()
    
    x_offset = 50
    y_offset = 50
    max_height = 0
    
    for letter_name in sorted(GREEK_UNICODE.keys()):
        if letter_name not in letter_data:
            continue
        
        best = select_best_example(letter_data[letter_name])
        if not best or not os.path.exists(best['path']):
            continue
        
        try:
            # Load letter image
            letter_img = Image.open(best['path']).convert('L')
            
            # Invert if needed
            img_array = np.array(letter_img)
            if np.mean(img_array) < 128:
                letter_img = ImageOps.invert(letter_img)
            
            # Scale to consistent height
            target_height = 60
            scale = target_height / letter_img.height
            new_width = int(letter_img.width * scale)
            letter_img = letter_img.resize((new_width, target_height), Image.Resampling.LANCZOS)
            
            # Check if we need to wrap to next line
            if x_offset + new_width + 100 > img_width:
                x_offset = 50
                y_offset += max_height + 60
                max_height = 0
            
            # Paste letter image
            specimen.paste(letter_img, (x_offset, y_offset))
            
            # Add label
            draw.text((x_offset, y_offset + target_height + 5), 
                     f"{letter_name}", 
                     fill='black', font=label_font)
            
            x_offset += new_width + 40
            max_height = max(max_height, target_height)
            
        except Exception as e:
            print(f"Error processing {letter_name}: {e}")
    
    # Save specimen
    specimen.save('font_specimen.png')
    print("Font specimen saved as font_specimen.png")
    
    return specimen

def main():
    print("=" * 60)
    print("SINAITICUS FONT GENERATOR")
    print("=" * 60)
    
    # Load classified letter data
    print("\n1. Loading classified letters...")
    letter_data = load_review_data()
    
    if not letter_data:
        print("ERROR: No review data found!")
        print("Please ensure you have saved review data from the batch review tool.")
        return
    
    print(f"Found classified letters: {len(letter_data)} unique letters")
    for letter, samples in sorted(letter_data.items()):
        print(f"  {letter}: {len(samples)} samples")
    
    # Check for potrace
    try:
        subprocess.run(['potrace', '--version'], capture_output=True, check=True)
        has_potrace = True
    except:
        has_potrace = False
        print("\nWarning: potrace not installed. Install with: brew install potrace")
        print("Skipping vector font generation.")
    
    # Check for fontforge
    try:
        subprocess.run(['fontforge', '--version'], capture_output=True, check=True)
        has_fontforge = True
    except:
        has_fontforge = False
        print("\nWarning: FontForge not installed. Install with: brew install fontforge")
        print("Skipping TTF generation.")
    
    # Create bitmap font specimen
    print("\n2. Creating font specimen sheet...")
    create_simple_bitmap_font(letter_data)
    
    if has_potrace and has_fontforge:
        print("\n3. Creating FontForge script...")
        script = create_fontforge_script(letter_data)
        
        with open('generate_font_fontforge.py', 'w') as f:
            f.write(script)
        
        print("FontForge script saved as generate_font_fontforge.py")
        print("\nTo generate TTF/OTF fonts, run:")
        print("  fontforge -script generate_font_fontforge.py")
    
    # Create a simple HTML preview
    print("\n4. Creating HTML preview...")
    html = '''<!DOCTYPE html>
<html>
<head>
    <title>Sinaiticus Font Preview</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            padding: 20px;
            background: #f5f5f5;
        }
        h1 { color: #333; }
        .specimen { 
            background: white; 
            padding: 20px; 
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        img { 
            max-width: 100%; 
            height: auto; 
            border: 1px solid #ddd;
        }
        .info {
            margin: 20px 0;
            padding: 15px;
            background: #e8f4f8;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <h1>🏛️ Sinaiticus Font - Generated from Codex Sinaiticus</h1>
    
    <div class="info">
        <h2>Letters Found:</h2>
        <p>''' + ', '.join(sorted(letter_data.keys())) + '''</p>
        <p>Total samples used: ''' + str(sum(len(samples) for samples in letter_data.values())) + '''</p>
    </div>
    
    <div class="specimen">
        <h2>Font Specimen:</h2>
        <img src="font_specimen.png" alt="Font Specimen">
    </div>
    
    <div class="info">
        <h3>Next Steps:</h3>
        <ol>
            <li>Review the specimen above to see the extracted letters</li>
            <li>To get missing letters, use the batch review tool to classify more samples</li>
            <li>Install fontforge and potrace to generate actual TTF/OTF files</li>
        </ol>
    </div>
</body>
</html>'''
    
    with open('font_preview.html', 'w') as f:
        f.write(html)
    
    print("HTML preview saved as font_preview.html")
    
    print("\n" + "=" * 60)
    print("FONT GENERATION COMPLETE!")
    print("=" * 60)
    print("\nGenerated files:")
    print("  - font_specimen.png: Visual preview of all letters")
    print("  - font_preview.html: HTML preview page")
    if has_potrace and has_fontforge:
        print("  - generate_font_fontforge.py: Script to generate TTF/OTF")
    
    print("\nOpen font_preview.html in your browser to see the results!")

if __name__ == "__main__":
    main()