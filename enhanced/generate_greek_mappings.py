#!/usr/bin/env python3
"""
Generate comprehensive mappings of all Greek Unicode characters with diacriticals
to their base characters for font creation.

Greek Unicode blocks:
- Greek and Coptic: U+0370–U+03FF
- Greek Extended: U+1F00–U+1FFF
"""

import unicodedata

def get_base_greek_chars():
    """Define the base Greek characters (uppercase and lowercase)"""
    return {
        # Uppercase
        'Α': 0x0391,  # Alpha
        'Β': 0x0392,  # Beta
        'Γ': 0x0393,  # Gamma
        'Δ': 0x0394,  # Delta
        'Ε': 0x0395,  # Epsilon
        'Ζ': 0x0396,  # Zeta
        'Η': 0x0397,  # Eta
        'Θ': 0x0398,  # Theta
        'Ι': 0x0399,  # Iota
        'Κ': 0x039A,  # Kappa
        'Λ': 0x039B,  # Lambda
        'Μ': 0x039C,  # Mu
        'Ν': 0x039D,  # Nu
        'Ξ': 0x039E,  # Xi
        'Ο': 0x039F,  # Omicron
        'Π': 0x03A0,  # Pi
        'Ρ': 0x03A1,  # Rho
        'Σ': 0x03A3,  # Sigma
        'Τ': 0x03A4,  # Tau
        'Υ': 0x03A5,  # Upsilon
        'Φ': 0x03A6,  # Phi
        'Χ': 0x03A7,  # Chi
        'Ψ': 0x03A8,  # Psi
        'Ω': 0x03A9,  # Omega
        
        # Lowercase
        'α': 0x03B1,  # alpha
        'β': 0x03B2,  # beta
        'γ': 0x03B3,  # gamma
        'δ': 0x03B4,  # delta
        'ε': 0x03B5,  # epsilon
        'ζ': 0x03B6,  # zeta
        'η': 0x03B7,  # eta
        'θ': 0x03B8,  # theta
        'ι': 0x03B9,  # iota
        'κ': 0x03BA,  # kappa
        'λ': 0x03BB,  # lambda
        'μ': 0x03BC,  # mu
        'ν': 0x03BD,  # nu
        'ξ': 0x03BE,  # xi
        'ο': 0x03BF,  # omicron
        'π': 0x03C0,  # pi
        'ρ': 0x03C1,  # rho
        'σ': 0x03C3,  # sigma
        'ς': 0x03C2,  # final sigma
        'τ': 0x03C4,  # tau
        'υ': 0x03C5,  # upsilon
        'φ': 0x03C6,  # phi
        'χ': 0x03C7,  # chi
        'ψ': 0x03C8,  # psi
        'ω': 0x03C9,  # omega
    }

def identify_base_letter(char_name):
    """Extract the base letter from a Unicode character name"""
    # Map of name components to base characters
    letter_map = {
        'ALPHA': ('Α', 'α'),
        'BETA': ('Β', 'β'),
        'GAMMA': ('Γ', 'γ'),
        'DELTA': ('Δ', 'δ'),
        'EPSILON': ('Ε', 'ε'),
        'ZETA': ('Ζ', 'ζ'),
        'ETA': ('Η', 'η'),
        'THETA': ('Θ', 'θ'),
        'IOTA': ('Ι', 'ι'),
        'KAPPA': ('Κ', 'κ'),
        'LAMDA': ('Λ', 'λ'),
        'LAMBDA': ('Λ', 'λ'),
        'MU': ('Μ', 'μ'),
        'NU': ('Ν', 'ν'),
        'XI': ('Ξ', 'ξ'),
        'OMICRON': ('Ο', 'ο'),
        'PI': ('Π', 'π'),
        'RHO': ('Ρ', 'ρ'),
        'SIGMA': ('Σ', 'σ'),
        'TAU': ('Τ', 'τ'),
        'UPSILON': ('Υ', 'υ'),
        'PHI': ('Φ', 'φ'),
        'CHI': ('Χ', 'χ'),
        'PSI': ('Ψ', 'ψ'),
        'OMEGA': ('Ω', 'ω'),
    }
    
    # Check for capital or small in name
    is_capital = 'CAPITAL' in char_name or 'UPPER' in char_name
    
    for letter_name, (upper, lower) in letter_map.items():
        if letter_name in char_name:
            return upper if is_capital else lower
    
    return None

def generate_mappings():
    """Generate all Greek character to base character mappings"""
    mappings = {}
    base_chars = get_base_greek_chars()
    
    # Greek and Coptic block (U+0370–U+03FF)
    for code in range(0x0370, 0x0400):
        char = chr(code)
        try:
            name = unicodedata.name(char)
            if 'GREEK' in name:
                # Handle special cases
                if code == 0x03C2:  # Final sigma
                    mappings[code] = 0x03C3  # Map to regular sigma
                elif 'TONOS' in name or 'DIALYTIKA' in name:
                    # Characters with tonos or dialytika
                    base = identify_base_letter(name)
                    if base and base in base_chars:
                        mappings[code] = base_chars[base]
                elif code not in base_chars.values():
                    # If not a base character, try to identify what it should map to
                    base = identify_base_letter(name)
                    if base and base in base_chars:
                        mappings[code] = base_chars[base]
        except ValueError:
            # Character has no name
            pass
    
    # Greek Extended block (U+1F00–U+1FFF)
    # This block contains all the polytonic Greek combinations
    for code in range(0x1F00, 0x2000):
        char = chr(code)
        try:
            name = unicodedata.name(char)
            if 'GREEK' in name:
                base = identify_base_letter(name)
                if base and base in base_chars:
                    mappings[code] = base_chars[base]
        except ValueError:
            # Character has no name
            pass
    
    return mappings

def generate_fontforge_script(mappings):
    """Generate a FontForge Python script to modify the font"""
    script = '''#!/usr/bin/env fontforge
# FontForge script to map all Greek diacritical combinations to base characters

import fontforge
import sys

if len(sys.argv) != 3:
    print("Usage: fontforge -script enhance_greek_font.ff input.ttf output.ttf")
    sys.exit(1)

input_font = sys.argv[1]
output_font = sys.argv[2]

# Open the font
font = fontforge.open(input_font)

# Character mappings (Unicode point -> base character Unicode point)
mappings = {
'''
    
    # Add all mappings
    for char_code, base_code in sorted(mappings.items()):
        script += f'    0x{char_code:04X}: 0x{base_code:04X},  # {chr(char_code)} -> {chr(base_code)}\n'
    
    script += '''
}

# Apply mappings by copying glyphs
for source, target in mappings.items():
    try:
        # Check if base character exists in font
        if target in font:
            # Copy the base character glyph to the accented character position
            font.selection.select(target)
            font.copy()
            font.selection.select(source)
            font.paste()
            print(f"Mapped U+{source:04X} to U+{target:04X}")
        else:
            print(f"Warning: Base character U+{target:04X} not found in font")
    except Exception as e:
        print(f"Error mapping U+{source:04X}: {e}")

# Set font metadata
font.fontname = "SinaiticusNoMarks"
font.fullname = "Sinaiticus No Diacritical Marks"
font.familyname = "Sinaiticus No Marks"

# Generate the output font
font.generate(output_font)
font.close()

print(f"Enhanced font saved to {output_font}")
'''
    
    return script

def main():
    print("Generating Greek character mappings...")
    
    # Generate mappings
    mappings = generate_mappings()
    
    # Statistics
    print(f"\nFound {len(mappings)} characters to map to base characters")
    
    # Show some examples
    print("\nExample mappings:")
    examples = [
        (0x03AC, "ά (alpha with tonos)"),
        (0x1F00, "ἀ (alpha with psili)"),
        (0x1F01, "ἁ (alpha with dasia)"),
        (0x1F04, "ἄ (alpha with psili and oxia)"),
        (0x1F80, "ᾀ (alpha with psili and ypogegrammeni)"),
        (0x1F8D, "ᾍ (capital alpha with dasia and oxia and prosgegrammeni)"),
        (0x1F70, "ὰ (alpha with varia)"),
        (0x1FB6, "ᾶ (alpha with perispomeni)"),
    ]
    
    for code, desc in examples:
        if code in mappings:
            base = mappings[code]
            print(f"  {desc} -> {chr(base)} (U+{base:04X})")
    
    # Generate FontForge script
    script = generate_fontforge_script(mappings)
    
    # Save the script
    with open('enhance_greek_font.ff', 'w', encoding='utf-8') as f:
        f.write(script)
    
    print(f"\nFontForge script saved to enhance_greek_font.ff")
    print("\nTo apply these mappings to your font:")
    print("1. Install FontForge: brew install fontforge")
    print("2. Run: fontforge -script enhance_greek_font.ff sinaiticus_test_20250823_172055.ttf sinaiticus_enhanced.ttf")
    
    # Also save mapping table for reference
    with open('greek_mappings.txt', 'w', encoding='utf-8') as f:
        f.write("Greek Diacritical to Base Character Mappings\n")
        f.write("=" * 50 + "\n\n")
        for code, base in sorted(mappings.items()):
            char = chr(code)
            base_char = chr(base)
            try:
                name = unicodedata.name(char)
                f.write(f"U+{code:04X} {char} ({name}) -> U+{base:04X} {base_char}\n")
            except ValueError:
                f.write(f"U+{code:04X} {char} -> U+{base:04X} {base_char}\n")
    
    print("Mapping table saved to greek_mappings.txt")

if __name__ == "__main__":
    main()