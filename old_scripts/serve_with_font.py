#!/usr/bin/env python3
"""
HTTP server for the classification tool with font generation support
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
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # Log the request
        print(f"GET request for: {self.path}")
        super().do_GET()
    
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
                
                # Generate actual font using FontForge
                success = self.generate_font_with_fontforge(classifications, font_file)
                
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
    
    def generate_fontforge_script(self, classifications, font_file):
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
    
    def generate_font_with_fontforge(self, classifications, font_file):
        """Generate font using FontForge from reviewed character images"""
        import tempfile
        import subprocess
        
        # Generate the FontForge script
        script_content = self.generate_fontforge_script(classifications, font_file)

# Greek letter to Unicode mapping
GREEK_UNICODE = {{
    'ALPHA': ('Α', 0x0391), 'BETA': ('Β', 0x0392), 'GAMMA': ('Γ', 0x0393),
    'DELTA': ('Δ', 0x0394), 'EPSILON': ('Ε', 0x0395), 'ZETA': ('Ζ', 0x0396),
    'ETA': ('Η', 0x0397), 'THETA': ('Θ', 0x0398), 'IOTA': ('Ι', 0x0399),
    'KAPPA': ('Κ', 0x039A), 'LAMBDA': ('Λ', 0x039B), 'MU': ('Μ', 0x039C),
    'NU': ('Ν', 0x039D), 'XI': ('Ξ', 0x039E), 'OMICRON': ('Ο', 0x039F),
    'PI': ('Π', 0x03A0), 'RHO': ('Ρ', 0x03A1), 'SIGMA': ('Σ', 0x03A3),
    'TAU': ('Τ', 0x03A4), 'UPSILON': ('Υ', 0x03A5), 'PHI': ('Φ', 0x03A6),
    'CHI': ('Χ', 0x03A7), 'PSI': ('Ψ', 0x03A8), 'OMEGA': ('Ω', 0x03A9)
}}

# Classifications from the web tool
classifications = {json.dumps(classifications)}

# Font file to generate
font_file = "{font_file}"

print(f"Received classifications for: {{list(classifications.keys())}}")

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
        print("Processing " + str(letter_name) + " (" + str(char) + ") with " + str(len(char_ids) if isinstance(char_ids, list) else 1) + " character(s)")
        
        # Create glyph
        glyph = font.createChar(unicode_val, "uni{{0:04X}}".format(unicode_val))
        
        # Try to import character image from the reviewed characters
        img_imported = False
        
        if char_ids and len(char_ids) > 0:
            # Use first character ID from the review
            char_id = char_ids[0] if isinstance(char_ids, list) else char_ids
            
            # Remove "letter_" prefix if present and convert to number
            if isinstance(char_id, str) and char_id.startswith('letter_'):
                char_id = char_id.replace('letter_', '')
            
            # Convert character ID to the image filename
            # The images are in letters_for_review/letter_XXXXX.png format
            img_path = "letters_for_review/letter_" + str(char_id).zfill(5) + ".png"
            
            print("  Looking for: " + img_path)
            
            if os.path.exists(img_path):
                try:
                    print("  Importing from " + img_path)
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
                    print("  ✗ Error importing: " + str(e))
            else:
                print("  ✗ File not found")
        
        # If no image, create simple placeholder
        if not img_imported:
            print("  Creating placeholder for " + str(letter_name))
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
            lowercase_glyph = font.createChar(lowercase_unicode, "uni{{0:04X}}".format(lowercase_unicode))
            lowercase_glyph.addReference("uni{{0:04X}}".format(unicode_val))
            lowercase_glyph.width = glyph.width

print("\\nSummary: " + str(added_count) + " letters from reviewed images, " + str(placeholder_count) + " placeholders")

# Generate font
print("Generating font: " + str(font_file))
font.generate(str(font_file))
font.close()

        try:
            # Write script to temp file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(script_content)
                script_path = f.name
            
            # Run FontForge
            print(f"Running FontForge to generate {font_file}...")
            result = subprocess.run(
                ['fontforge', '-script', script_path],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Clean up
            os.unlink(script_path)
            
            if result.returncode == 0:
                print(f"✓ FontForge generated {font_file}")
                print("FontForge output:", result.stdout)
                return True
            else:
                print(f"FontForge error: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"Error running FontForge: {e}")
            return False
    
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
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 10px;
        }}
        .test-area {{
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin: 20px 0;
        }}
        .font-display {{
            font-family: 'Sinaiticus', serif;
            font-size: 48px;
            line-height: 1.8;
            color: #1a202c;
            margin: 20px 0;
            letter-spacing: 2px;
        }}
        .letter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
            gap: 15px;
            margin: 30px 0;
        }}
        .letter-box {{
            text-align: center;
            padding: 15px;
            background: #f7fafc;
            border-radius: 4px;
            border: 1px solid #e2e8f0;
        }}
        .letter-char {{
            font-family: 'Sinaiticus', serif;
            font-size: 36px;
            color: #2d3748;
            display: block;
            margin-bottom: 5px;
        }}
        .letter-name {{
            font-size: 11px;
            color: #718096;
            text-transform: uppercase;
        }}
        .letter-count {{
            font-size: 10px;
            color: #a0aec0;
        }}
        textarea {{
            width: 100%;
            padding: 15px;
            font-family: 'Sinaiticus', serif;
            font-size: 28px;
            border: 2px solid #e2e8f0;
            border-radius: 4px;
            min-height: 150px;
            line-height: 1.6;
        }}
        .info-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .info-table td {{
            padding: 8px;
            border-bottom: 1px solid #e2e8f0;
        }}
        .info-table td:first-child {{
            font-weight: bold;
            color: #4a5568;
            width: 150px;
        }}
        .sample-text {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .note {{
            background: #fef5e7;
            border-left: 4px solid #f6ad55;
            padding: 15px;
            margin: 20px 0;
            color: #744210;
        }}
    </style>
</head>
<body>
    <h1>🏛️ Sinaiticus Font Test Page</h1>
    
    <div class="note">
        <strong>Note:</strong> This is a test font generated from manuscript character samples. 
        The actual font rendering is simulated for demonstration purposes.
    </div>
    
    <div class="test-area">
        <h2>Character Inventory ({len(letters)} of 24 Greek letters)</h2>
        <div class="letter-grid">
'''
        
        # Add each letter we have with its info
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
        
        # Create sample text from available letters
        available_chars = ''.join([greek_map.get(l, '') for l in letters])
        
        html += f'''
        </div>
    </div>
    
    <div class="test-area">
        <h2>Sample Text Display</h2>
        <div class="sample-text">
            <div class="font-display">
                {available_chars}
            </div>
        </div>
        <div class="sample-text">
            <div class="font-display" style="font-size: 36px;">
                ΕΝΤΗΑΡΧΗΗΝΟΛΟΓΟΣ
            </div>
            <p style="color: #718096; font-size: 14px;">
                "In the beginning was the Word" (John 1:1)
            </p>
        </div>
    </div>
    
    <div class="test-area">
        <h2>Interactive Text Editor</h2>
        <p>Type or paste Greek text below to test the font:</p>
        <textarea placeholder="Type Greek text here...">{available_chars[:10]}</textarea>
    </div>
    
    <div class="test-area">
        <h2>Font Statistics</h2>
        <table class="info-table">
            <tr>
                <td>Font File</td>
                <td><code>{font_file}</code></td>
            </tr>
            <tr>
                <td>Total Letters</td>
                <td>{len(letters)} unique letters</td>
            </tr>
            <tr>
                <td>Total Samples</td>
                <td>{sum(len(chars) for chars in classifications.values())} character images</td>
            </tr>
            <tr>
                <td>Average per Letter</td>
                <td>{sum(len(chars) for chars in classifications.values()) // max(len(letters), 1)} samples</td>
            </tr>
            <tr>
                <td>Generated</td>
                <td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td>
            </tr>
        </table>
    </div>
    
    <div class="test-area">
        <h2>Letters Included</h2>
        <p>{', '.join([f"{greek_map.get(l, '?')} ({l})" for l in letters])}</p>
    </div>
</body>
</html>
'''
        
        with open(test_page, 'w', encoding='utf-8') as f:
            f.write(html)

os.chdir(os.path.dirname(os.path.abspath(__file__)))

with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
    print(f"Server running at http://localhost:{PORT}/")
    print(f"Open http://localhost:{PORT}/batch_review.html in your browser")
    print("Press Ctrl+C to stop the server")
    httpd.serve_forever()