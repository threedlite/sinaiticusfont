#!/usr/bin/env python3
"""
Simple font generator from classified Greek letters - no external dependencies
"""

import json
import os
from collections import defaultdict

# Greek letter to Unicode mapping
GREEK_UNICODE = {
    'ALPHA': ('Α', 0x0391),
    'BETA': ('Β', 0x0392),
    'GAMMA': ('Γ', 0x0393),
    'DELTA': ('Δ', 0x0394),
    'EPSILON': ('Ε', 0x0395),
    'ZETA': ('Ζ', 0x0396),
    'ETA': ('Η', 0x0397),
    'THETA': ('Θ', 0x0398),
    'IOTA': ('Ι', 0x0399),
    'KAPPA': ('Κ', 0x039A),
    'LAMBDA': ('Λ', 0x039B),
    'MU': ('Μ', 0x039C),
    'NU': ('Ν', 0x039D),
    'XI': ('Ξ', 0x039E),
    'OMICRON': ('Ο', 0x039F),
    'PI': ('Π', 0x03A0),
    'RHO': ('Ρ', 0x03A1),
    'SIGMA': ('Σ', 0x03A3),
    'TAU': ('Τ', 0x03A4),
    'UPSILON': ('Υ', 0x03A5),
    'PHI': ('Φ', 0x03A6),
    'CHI': ('Χ', 0x03A7),
    'PSI': ('Ψ', 0x03A8),
    'OMEGA': ('Ω', 0x03A9)
}

def load_review_data():
    """Load all review data files"""
    all_data = []
    
    # Load any review files
    import glob
    for review_file in glob.glob('review_data_*.json'):
        try:
            with open(review_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
                print(f"Loaded {len(data)} items from {review_file}")
        except Exception as e:
            print(f"Error loading {review_file}: {e}")
            continue
    
    # Group by classification
    by_letter = defaultdict(list)
    for item in all_data:
        classification = item.get('classification')
        if classification and classification != 'NON_LETTER' and classification != 'UNCLASSIFIED':
            by_letter[classification].append(item)
    
    return by_letter

def select_best_examples(letter_samples, max_examples=5):
    """Select the best examples for each letter"""
    if not letter_samples:
        return []
    
    # Sort by quality and size
    samples = sorted(letter_samples, key=lambda x: (
        x.get('quality', 0) * x.get('width', 0) * x.get('height', 0)
    ), reverse=True)
    
    # Return top examples
    return samples[:max_examples]

def create_html_font_display(letter_data):
    """Create an HTML page showing the font"""
    
    html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Sinaiticus Font - Generated from Codex Sinaiticus</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            background: white;
            border-radius: 12px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        h1 {
            font-size: 36px;
            color: #2d3748;
            margin-bottom: 10px;
        }
        
        .subtitle {
            color: #718096;
            font-size: 18px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            display: block;
        }
        
        .stat-label {
            font-size: 14px;
            opacity: 0.9;
            margin-top: 5px;
        }
        
        .alphabet-grid {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }
        
        .letter-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .letter-card {
            background: #f7fafc;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s;
        }
        
        .letter-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 20px rgba(0,0,0,0.1);
            border-color: #667eea;
        }
        
        .letter-card.missing {
            background: #fff5f5;
            border-color: #fc8181;
            opacity: 0.6;
        }
        
        .letter-images {
            min-height: 80px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
            margin-bottom: 10px;
        }
        
        .letter-image {
            max-width: 60px;
            max-height: 60px;
            image-rendering: pixelated;
            image-rendering: -moz-crisp-edges;
            image-rendering: crisp-edges;
        }
        
        .letter-symbol {
            font-size: 48px;
            color: #667eea;
            margin-bottom: 10px;
            font-weight: bold;
        }
        
        .letter-name {
            font-size: 14px;
            color: #4a5568;
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .letter-count {
            font-size: 12px;
            color: #718096;
        }
        
        .preview-section {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        
        .preview-text {
            font-size: 24px;
            line-height: 2;
            color: #2d3748;
            padding: 20px;
            background: #f7fafc;
            border-radius: 8px;
            margin-top: 20px;
        }
        
        .missing-notice {
            background: #fef5e7;
            border: 2px solid #f39c12;
            border-radius: 8px;
            padding: 15px;
            margin: 20px 0;
            color: #856404;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏛️ Sinaiticus Font</h1>
            <p class="subtitle">Reconstructed from Codex Sinaiticus manuscript images</p>
            
            <div class="stats">
'''
    
    # Add statistics
    total_letters = len([k for k in letter_data.keys() if k in GREEK_UNICODE])
    total_samples = sum(len(samples) for samples in letter_data.values())
    missing_letters = [name for name in GREEK_UNICODE.keys() if name not in letter_data]
    
    html += f'''
                <div class="stat-card">
                    <span class="stat-value">{total_letters}</span>
                    <span class="stat-label">Letters Found</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">{24 - total_letters}</span>
                    <span class="stat-label">Letters Missing</span>
                </div>
                <div class="stat-card">
                    <span class="stat-value">{total_samples}</span>
                    <span class="stat-label">Total Samples</span>
                </div>
            </div>
        </div>
'''
    
    # Add missing letters notice if any
    if missing_letters:
        html += f'''
        <div class="missing-notice">
            <strong>⚠️ Missing Letters:</strong> {', '.join([GREEK_UNICODE[m][0] + ' (' + m + ')' for m in missing_letters])}
            <br>Use the batch review tool to find and classify these letters.
        </div>
'''
    
    # Add alphabet grid
    html += '''
        <div class="alphabet-grid">
            <h2>Greek Alphabet</h2>
            <div class="letter-grid">
'''
    
    for letter_name, (symbol, unicode_val) in GREEK_UNICODE.items():
        if letter_name in letter_data:
            samples = select_best_examples(letter_data[letter_name], 3)
            html += f'''
                <div class="letter-card">
                    <div class="letter-images">
'''
            for sample in samples[:3]:
                if os.path.exists(sample['path']):
                    html += f'                        <img src="{sample["path"]}" class="letter-image" alt="{letter_name}">\n'
            
            html += f'''
                    </div>
                    <div class="letter-symbol">{symbol}</div>
                    <div class="letter-name">{letter_name}</div>
                    <div class="letter-count">{len(letter_data[letter_name])} samples</div>
                </div>
'''
        else:
            html += f'''
                <div class="letter-card missing">
                    <div class="letter-images">
                        <div style="color: #cbd5e0; font-size: 48px;">?</div>
                    </div>
                    <div class="letter-symbol" style="opacity: 0.3;">{symbol}</div>
                    <div class="letter-name">{letter_name}</div>
                    <div class="letter-count">Missing</div>
                </div>
'''
    
    html += '''
            </div>
        </div>
        
        <div class="preview-section">
            <h2>Sample Text</h2>
            <div class="preview-text">
'''
    
    # Add sample Greek text using available letters
    sample_texts = [
        'ΑΛΦΑ ΒΗΤΑ ΓΑΜΜΑ ΔΕΛΤΑ',
        'ΕΠΣΙΛΟΝ ΖΗΤΑ ΗΤΑ ΘΗΤΑ',
        'ΙΩΤΑ ΚΑΠΠΑ ΛΑΜΒΔΑ ΜΥ',
        'ΝΥ ΞΙ ΟΜΙΚΡΟΝ ΠΙ',
        'ΡΩ ΣΙΓΜΑ ΤΑΥ ΥΨΙΛΟΝ',
        'ΦΙ ΧΙ ΨΙ ΩΜΕΓΑ'
    ]
    
    for text in sample_texts:
        display_text = ''
        for char in text:
            if char == ' ':
                display_text += ' '
            else:
                # Find if we have this letter
                letter_name = None
                for name, (symbol, _) in GREEK_UNICODE.items():
                    if symbol == char:
                        letter_name = name
                        break
                
                if letter_name and letter_name in letter_data:
                    # We have this letter - show it
                    best = select_best_examples(letter_data[letter_name], 1)
                    if best and os.path.exists(best[0]['path']):
                        display_text += f'<img src="{best[0]["path"]}" style="height: 30px; vertical-align: middle; margin: 0 2px;">'
                    else:
                        display_text += f'<span style="color: #cbd5e0;">{char}</span>'
                else:
                    display_text += f'<span style="color: #cbd5e0;">{char}</span>'
        
        html += f'            <div>{display_text}</div>\n'
    
    html += '''
            </div>
        </div>
    </div>
</body>
</html>'''
    
    return html

def main():
    print("=" * 60)
    print("SINAITICUS FONT GENERATOR")
    print("=" * 60)
    
    # Load classified letter data
    print("\n1. Loading classified letters...")
    letter_data = load_review_data()
    
    if not letter_data:
        print("\nERROR: No review data found!")
        print("Please save review data from the batch review tool first.")
        print("Expected files: review_data_*.json")
        return
    
    print(f"\nFound {len(letter_data)} unique letter types:")
    
    # Show summary
    found_letters = []
    missing_letters = []
    
    for letter_name, (symbol, _) in sorted(GREEK_UNICODE.items()):
        if letter_name in letter_data:
            count = len(letter_data[letter_name])
            print(f"  ✓ {symbol} ({letter_name}): {count} samples")
            found_letters.append(letter_name)
        else:
            print(f"  ✗ {symbol} ({letter_name}): MISSING")
            missing_letters.append(letter_name)
    
    print(f"\nSummary:")
    print(f"  Letters found: {len(found_letters)}/24")
    print(f"  Total samples: {sum(len(samples) for samples in letter_data.values())}")
    
    if missing_letters:
        print(f"\nMissing letters: {', '.join(missing_letters)}")
        print("Use the batch review tool to find and classify these letters.")
    
    # Create HTML display
    print("\n2. Creating HTML font display...")
    html = create_html_font_display(letter_data)
    
    with open('sinaiticus_font.html', 'w', encoding='utf-8') as f:
        f.write(html)
    
    print("HTML font display saved as sinaiticus_font.html")
    
    print("\n" + "=" * 60)
    print("FONT GENERATION COMPLETE!")
    print("=" * 60)
    print("\nOpen sinaiticus_font.html in your browser to see your font!")
    print("\nTo complete the font:")
    print("1. Use batch_review.html to find missing letters")
    print("2. Save the review data")
    print("3. Run this script again")

if __name__ == "__main__":
    main()