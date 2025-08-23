#!/usr/bin/env python3
"""
HTTP server for the classification tool with font generation support - FIXED VERSION
"""

import http.server
import socketserver
import os
import json
from datetime import datetime
from pathlib import Path
import webbrowser
import tempfile
import subprocess

PORT = 8080

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with additional endpoints"""
    
    def do_GET(self):
        """Handle GET requests"""
        print(f"GET request for: {self.path}")
        # Default behavior for serving files
        super().do_GET()
    
    def clean_image_for_fontforge(self, img_path, letter_name):
        """Clean isolated dots from image while preserving the main letter"""
        try:
            from PIL import Image, ImageFilter
            import numpy as np
            from scipy import ndimage
            
            # Load image
            img = Image.open(img_path).convert('L')
            img_array = np.array(img)
            
            # First pass: aggressive threshold to remove light gray dots
            # Most background noise is lighter than the main text
            threshold = 100  # More aggressive threshold (was 128)
            binary = img_array < threshold  # True for dark pixels (text)
            
            # Apply morphological opening to remove small isolated dots
            # Opening = erosion followed by dilation
            # This removes small objects while preserving larger ones
            from scipy.ndimage import binary_opening, binary_closing
            
            # Use a small structural element for opening
            # This will remove dots smaller than 3x3 pixels
            structure = np.ones((3, 3))
            cleaned_binary = binary_opening(binary, structure=structure, iterations=1)
            
            # Now find the largest connected component (the main letter)
            labeled, num_features = ndimage.label(cleaned_binary)
            
            if num_features == 0:
                return img_path  # No features found
            
            # Get component sizes
            component_sizes = []
            for i in range(1, num_features + 1):
                size = np.sum(labeled == i)
                component_sizes.append((size, i))
            
            # Sort by size and keep only the largest components
            component_sizes.sort(reverse=True)
            
            # Get the main component (largest)
            main_size, main_label = component_sizes[0] if component_sizes else (0, 0)
            
            # Find bounding box of main component for distance calculation
            main_mask = labeled == main_label
            main_coords = np.where(main_mask)
            if len(main_coords[0]) > 0:
                main_y_min, main_y_max = main_coords[0].min(), main_coords[0].max()
                main_x_min, main_x_max = main_coords[1].min(), main_coords[1].max()
                # Add smaller margin around main component to be more selective
                margin = 15  # pixels - reduced to catch only nearby components
                main_y_min = max(0, main_y_min - margin)
                main_y_max = min(binary.shape[0], main_y_max + margin)
                main_x_min = max(0, main_x_min - margin)
                main_x_max = min(binary.shape[1], main_x_max + margin)
            else:
                main_y_min = main_y_max = main_x_min = main_x_max = 0
            
            # Create final cleaned image
            final_mask = np.zeros_like(binary)
            
            # Keep largest components
            # Adjust thresholds to be less aggressive for PHI
            if letter_name == 'PHI':
                # For PHI, keep more components to preserve the letter structure
                size_threshold = 30  # Smaller threshold for PHI
                components_to_keep = 15  # Keep more components for PHI
            else:
                # For PSI and others, more aggressive cleaning
                size_threshold = 50  # Standard threshold  
                components_to_keep = 10  # Keep fewer components
            
            kept = 0
            removed = 0
            for idx, (size, label) in enumerate(component_sizes):
                if idx < components_to_keep and size > size_threshold:
                    final_mask |= (labeled == label)
                    kept += 1
                else:
                    removed += 1
                    
            # Convert back to grayscale image
            cleaned = np.ones_like(img_array) * 255  # White background
            cleaned[final_mask] = 0  # Black text
            
            # Save cleaned image
            import random
            rand_id = random.randint(1000, 9999)
            cleaned_path = f'/tmp/cleaned_{letter_name}_{rand_id}.png'
            Image.fromarray(cleaned.astype(np.uint8)).save(cleaned_path)
            
            # Save comparison for debugging
            comparison = np.hstack([img_array, cleaned])
            comparison_path = f'comparison_{letter_name}_{rand_id}.png'
            Image.fromarray(comparison.astype(np.uint8)).save(comparison_path)
            
            print(f"    Cleaned {letter_name}: kept {kept} large components out of {num_features} total")
            print(f"    Saved comparison to: {comparison_path}")
            return cleaned_path
            
        except Exception as e:
            import traceback
            print(f"    ERROR in clean_image_for_fontforge: {e}")
            print(f"    Traceback: {traceback.format_exc()}")
            return img_path  # Return original if cleaning fails
    
    def do_POST(self):
        """Handle POST requests for saving review data and creating fonts"""
        if self.path == '/save_review':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                filename = data.get('filename', 'review_data.json')
                review_data = data.get('data', [])
                
                # Save to project directory
                filepath = os.path.join(os.getcwd(), filename)
                with open(filepath, 'w') as f:
                    json.dump(review_data, f, indent=2)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                
                response = {'status': 'success', 'message': f'Saved {len(review_data)} items'}
                self.wfile.write(json.dumps(response).encode())
                
                print(f"✓ Saved {len(review_data)} reviewed characters to {filename}")
                
            except Exception as e:
                # Send error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e)}
                self.wfile.write(json.dumps(response).encode())
                print(f"Error saving review data: {e}")
                
        elif self.path == '/create_font':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                data = json.loads(post_data)
                classifications = data.get('classifications', {})
                
                # Create test font and page
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                font_file = f'sinaiticus_test_{timestamp}.ttf'
                test_page = f'test_font_{timestamp}.html'
                
                # Clean PHI and PSI images before font generation
                cleaned_images = {}
                print(f"DEBUG: Starting cleaning process for classifications: {classifications.keys()}")
                for letter_name, char_ids in classifications.items():
                    print(f"DEBUG: Checking {letter_name}: {char_ids}")
                    if letter_name in ['PHI', 'PSI'] and char_ids and len(char_ids) > 0:
                        print(f"DEBUG: {letter_name} needs cleaning")
                        # Clean the image for PHI and PSI
                        char_id = char_ids[0] if isinstance(char_ids, list) else char_ids
                        if isinstance(char_id, str) and char_id.startswith('letter_'):
                            char_id = char_id.replace('letter_', '')
                        
                        img_path = f"letters_for_review/letter_{str(char_id).zfill(5)}.png"
                        print(f"DEBUG: Looking for image at: {img_path}")
                        print(f"DEBUG: Image exists: {os.path.exists(img_path)}")
                        if os.path.exists(img_path):
                            print(f"DEBUG: Calling clean_image_for_fontforge for {letter_name}")
                            cleaned_path = self.clean_image_for_fontforge(img_path, letter_name)
                            print(f"DEBUG: Cleaned path returned: {cleaned_path}")
                            # Map the original char_id to the cleaned path
                            cleaned_images[str(char_id)] = cleaned_path
                        else:
                            print(f"DEBUG: Image not found at {img_path}")
                print(f"DEBUG: Cleaned images dict: {cleaned_images}")
                
                # Generate actual font using FontForge (pass cleaned_images separately)
                success = self.generate_font_with_fontforge(classifications, font_file, cleaned_images)
                
                if not success:
                    # If FontForge fails, create placeholder
                    Path(font_file).touch()
                    print("Warning: FontForge generation failed, created placeholder")
                
                # Create the test page
                self.create_test_page(font_file, test_page, classifications)
                
                # Open the test page in browser
                test_url = f'http://localhost:{PORT}/{test_page}'
                print(f"Opening test page: {test_url}")
                webbrowser.open(test_url)
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {
                    'status': 'success',
                    'font_file': font_file,
                    'test_page_url': test_url
                }
                self.wfile.write(json.dumps(response).encode())
                
                print(f"✓ Created test font: {font_file}")
                print(f"✓ Created test page: {test_page}")
                
            except Exception as e:
                import traceback
                error_trace = traceback.format_exc()
                print(f"Error creating font: {e}")
                print(f"Full traceback:\n{error_trace}")
                
                # Send error response
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                response = {'status': 'error', 'message': str(e), 'traceback': error_trace}
                self.wfile.write(json.dumps(response).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests for CORS"""
        self.send_response(200)
        self.end_headers()
    
    def generate_font_with_fontforge(self, classifications, font_file, cleaned_images=None):
        """Generate font using FontForge from reviewed character images"""
        
        # Create FontForge script
        script_content = self.create_fontforge_script(classifications, font_file, cleaned_images or {})
        
        try:
            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Debug: save script for inspection
            try:
                from datetime import datetime
                debug_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                debug_path = f'fontforge_script_{debug_timestamp}.py'
                with open(debug_path, 'w') as debug_f:
                    debug_f.write(script_content)
                print(f"DEBUG: Script saved to {debug_path}")
            except Exception as e:
                print(f"DEBUG: Could not save script: {e}")
            
            # Run FontForge
            print(f"Running FontForge to generate {font_file}...")
            result = subprocess.run(
                ['fontforge', '-script', script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Print FontForge output for debugging
            if result.stdout:
                print("FontForge output:")
                print(result.stdout)
            if result.stderr:
                print("FontForge errors:")
                print(result.stderr)
            
            # Clean up temp file (but not debug file)
            os.unlink(script_path)
            
            if result.returncode == 0:
                print(f"✓ FontForge generated {font_file}")
                return True
            else:
                print(f"FontForge error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error running FontForge: {e}")
            return False
    
    def create_fontforge_script(self, classifications, font_file, cleaned_images):
        """Create FontForge Python script"""
        
        # Convert classifications and cleaned images to JSON
        classifications_json = json.dumps(classifications)
        cleaned_images_json = json.dumps(cleaned_images)
        
        # Build script using string concatenation to avoid f-string issues
        script = '''import fontforge
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
classifications = ''' + classifications_json + '''

# Cleaned images mapping (for PHI and PSI)
cleaned_images = ''' + cleaned_images_json + '''

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

print("\\nSummary:", added_count, "letters from images,", placeholder_count, "placeholders")

# Add punctuation marks
print("\\nAdding punctuation marks...")

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
'''
        return script
    
    def create_test_page(self, font_file, test_page, classifications):
        """Create an HTML test page for the font"""
        # Greek letter mapping in proper alphabetical order
        greek_order = [
            'ALPHA', 'BETA', 'GAMMA', 'DELTA', 'EPSILON', 'ZETA', 'ETA', 'THETA',
            'IOTA', 'KAPPA', 'LAMBDA', 'MU', 'NU', 'XI', 'OMICRON', 'PI',
            'RHO', 'SIGMA', 'TAU', 'UPSILON', 'PHI', 'CHI', 'PSI', 'OMEGA'
        ]
        
        greek_map = {
            'ALPHA': 'Α', 'BETA': 'Β', 'GAMMA': 'Γ', 'DELTA': 'Δ', 'EPSILON': 'Ε',
            'ZETA': 'Ζ', 'ETA': 'Η', 'THETA': 'Θ', 'IOTA': 'Ι', 'KAPPA': 'Κ',
            'LAMBDA': 'Λ', 'MU': 'Μ', 'NU': 'Ν', 'XI': 'Ξ', 'OMICRON': 'Ο',
            'PI': 'Π', 'RHO': 'Ρ', 'SIGMA': 'Σ', 'TAU': 'Τ', 'UPSILON': 'Υ',
            'PHI': 'Φ', 'CHI': 'Χ', 'PSI': 'Ψ', 'OMEGA': 'Ω'
        }
        
        # Only include letters that we have in classifications, in proper order
        letters = [l for l in greek_order if l in classifications]
        
        html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sinaiticus Font Test</title>
    <style>
        @font-face {{
            font-family: 'Sinaiticus';
            src: url('{font_file}') format('truetype');
        }}
        body {{
            font-family: Arial, sans-serif;
            padding: 40px;
            background: #f5f5f5;
        }}
        h1 {{
            color: #2d3748;
            border-bottom: 2px solid #4a5568;
            padding-bottom: 10px;
        }}
        .font-display {{
            font-family: 'Sinaiticus', serif;
            font-size: 48px;
            line-height: 1.6;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .letter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .letter-box {{
            background: white;
            padding: 15px;
            text-align: center;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .letter-char {{
            font-family: 'Sinaiticus', serif;
            font-size: 36px;
            color: #2d3748;
            display: block;
            margin-bottom: 5px;
        }}
        .letter-name {{
            font-size: 12px;
            color: #718096;
        }}
        .letter-count {{
            font-size: 10px;
            color: #a0aec0;
        }}
    </style>
</head>
<body>
    <h1>🏛️ Sinaiticus Font Test Page</h1>
    
    <h2>Character Inventory ({len(letters)} of 24 Greek letters)</h2>
    <div class="letter-grid">
'''
        
        # Add each letter
        for letter in letters:
            char = greek_map.get(letter, '?')
            count = len(classifications[letter])
            html += f'''
        <div class="letter-box">
            <div class="letter-char">{char}</div>
            <div class="letter-name">{letter}</div>
            <div class="letter-count">{count} samples</div>
        </div>
'''
        
        # Show missing letters
        missing_letters = [l for l in greek_order if l not in classifications]
        if missing_letters:
            html += f'''
    </div>
    
    <h3>Missing Letters ({len(missing_letters)})</h3>
    <div class="letter-grid" style="opacity: 0.5;">
'''
            for letter in missing_letters:
                char = greek_map.get(letter, '?')
                html += f'''
        <div class="letter-box">
            <div class="letter-char" style="color: #ccc;">{char}</div>
            <div class="letter-name">{letter}</div>
            <div class="letter-count">No samples</div>
        </div>
'''
        
        html += '''
    </div>
    
    <h2>Punctuation Marks</h2>
    <div class="letter-grid">
        <div class="letter-box">
            <div class="letter-char">.</div>
            <div class="letter-name">PERIOD</div>
        </div>
        <div class="letter-box">
            <div class="letter-char">;</div>
            <div class="letter-name">SEMICOLON</div>
        </div>
        <div class="letter-box">
            <div class="letter-char">·</div>
            <div class="letter-name">RAISED DOT</div>
        </div>
    </div>
    
    <h2>Sample Text</h2>
    <div class="font-display">
        ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ
    </div>
    
    <div class="font-display" id="display-text">
        ΕΝ ΑΡΧΗ ΗΝ Ο ΛΟΓΟΣ. ΚΑΙ Ο ΛΟΓΟΣ· ΗΝ ΠΡΟΣ ΤΟΝ ΘΕΟΝ;
    </div>
    
    <div style="margin: 40px 0; text-align: center;">
        <label for="custom-text" style="display: block; margin-bottom: 10px; font-family: -apple-system, sans-serif; font-size: 14px;">
            Type your own text to test kerning:
        </label>
        <input type="text" 
               id="custom-text" 
               placeholder="Type Greek text here..." 
               style="width: 80%; padding: 10px; font-size: 16px; border: 1px solid #ccc; border-radius: 4px;">
        <div class="font-display" id="custom-display" style="margin-top: 20px; min-height: 100px; padding: 20px; background: #f9f9f9;">
            
        </div>
    </div>
    
    <script>
        const input = document.getElementById('custom-text');
        const display = document.getElementById('custom-display');
        
        input.addEventListener('input', function() {
            display.textContent = this.value || ' ';
        });
        
        // Allow typing Greek letters easily with Latin keyboard mapping
        const greekMap = {
            'a': 'Α', 'b': 'Β', 'g': 'Γ', 'd': 'Δ', 'e': 'Ε',
            'z': 'Ζ', 'h': 'Η', 'q': 'Θ', 'i': 'Ι', 'k': 'Κ',
            'l': 'Λ', 'm': 'Μ', 'n': 'Ν', 'x': 'Ξ', 'o': 'Ο',
            'p': 'Π', 'r': 'Ρ', 's': 'Σ', 't': 'Τ', 'u': 'Υ',
            'f': 'Φ', 'c': 'Χ', 'y': 'Ψ', 'w': 'Ω'
        };
        
        input.addEventListener('keypress', function(e) {
            if (e.key in greekMap && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                const start = this.selectionStart;
                const end = this.selectionEnd;
                const text = this.value;
                const greek = e.shiftKey ? greekMap[e.key.toLowerCase()] : greekMap[e.key];
                this.value = text.substring(0, start) + greek + text.substring(end);
                this.selectionStart = this.selectionEnd = start + 1;
                
                // Trigger input event to update display
                this.dispatchEvent(new Event('input'));
            }
        });
    </script>
</body>
</html>'''
        
        with open(test_page, 'w', encoding='utf-8') as f:
            f.write(html)

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Set up CORS headers
class CORSRequestHandler(MyHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), CORSRequestHandler) as httpd:
        print(f"Server running at http://localhost:{PORT}/")
        print(f"Open http://localhost:{PORT}/batch_review.html in your browser")
        httpd.serve_forever()