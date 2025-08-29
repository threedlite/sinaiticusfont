#!/usr/bin/env python3
# FontForge Python script to map all Greek diacritical combinations to base characters

import fontforge
import sys

if len(sys.argv) != 3:
    print("Usage: fontforge -lang=py -script enhance_greek_font.py input.ttf output.ttf")
    sys.exit(1)

input_font = sys.argv[1]
output_font = sys.argv[2]

# Open the font
font = fontforge.open(input_font)

# Character mappings (Unicode point -> base character Unicode point)
# This maps all Greek characters with diacriticals to their base forms
mappings = {}

# Helper to get base characters
base_chars = {
    # Uppercase
    'Α': 0x0391, 'Β': 0x0392, 'Γ': 0x0393, 'Δ': 0x0394, 'Ε': 0x0395,
    'Ζ': 0x0396, 'Η': 0x0397, 'Θ': 0x0398, 'Ι': 0x0399, 'Κ': 0x039A,
    'Λ': 0x039B, 'Μ': 0x039C, 'Ν': 0x039D, 'Ξ': 0x039E, 'Ο': 0x039F,
    'Π': 0x03A0, 'Ρ': 0x03A1, 'Σ': 0x03A3, 'Τ': 0x03A4, 'Υ': 0x03A5,
    'Φ': 0x03A6, 'Χ': 0x03A7, 'Ψ': 0x03A8, 'Ω': 0x03A9,
    # Lowercase
    'α': 0x03B1, 'β': 0x03B2, 'γ': 0x03B3, 'δ': 0x03B4, 'ε': 0x03B5,
    'ζ': 0x03B6, 'η': 0x03B7, 'θ': 0x03B8, 'ι': 0x03B9, 'κ': 0x03BA,
    'λ': 0x03BB, 'μ': 0x03BC, 'ν': 0x03BD, 'ξ': 0x03BE, 'ο': 0x03BF,
    'π': 0x03C0, 'ρ': 0x03C1, 'σ': 0x03C3, 'ς': 0x03C2, 'τ': 0x03C4,
    'υ': 0x03C5, 'φ': 0x03C6, 'χ': 0x03C7, 'ψ': 0x03C8, 'ω': 0x03C9,
}

# Map final sigma to regular sigma
mappings[0x03C2] = 0x03C3

# Greek and Coptic with tonos/dialytika (U+0386-U+03CE)
tonos_mappings = {
    0x0386: 0x0391,  # Ά -> Α
    0x0388: 0x0395,  # Έ -> Ε
    0x0389: 0x0397,  # Ή -> Η
    0x038A: 0x0399,  # Ί -> Ι
    0x038C: 0x039F,  # Ό -> Ο
    0x038E: 0x03A5,  # Ύ -> Υ
    0x038F: 0x03A9,  # Ώ -> Ω
    0x0390: 0x03B9,  # ΐ -> ι
    0x03AC: 0x03B1,  # ά -> α
    0x03AD: 0x03B5,  # έ -> ε
    0x03AE: 0x03B7,  # ή -> η
    0x03AF: 0x03B9,  # ί -> ι
    0x03B0: 0x03C5,  # ΰ -> υ
    0x03CA: 0x03B9,  # ϊ -> ι
    0x03CB: 0x03C5,  # ϋ -> υ
    0x03CC: 0x03BF,  # ό -> ο
    0x03CD: 0x03C5,  # ύ -> υ
    0x03CE: 0x03C9,  # ώ -> ω
}
mappings.update(tonos_mappings)

# Greek Extended (U+1F00-U+1FFF) - All polytonic combinations
# This is the main block with breathing marks, accents, iota subscripts, etc.

# Alpha combinations (ἀ-ᾷ)
for i in range(0x1F00, 0x1F10): mappings[i] = 0x03B1  # α with breathings/accents
for i in range(0x1F10, 0x1F16): mappings[i] = 0x03B5  # ε with breathings/accents
for i in range(0x1F18, 0x1F1E): mappings[i] = 0x0395  # Ε with breathings/accents
for i in range(0x1F20, 0x1F30): mappings[i] = 0x03B7  # η with breathings/accents
for i in range(0x1F30, 0x1F38): mappings[i] = 0x03B9  # ι with breathings/accents
for i in range(0x1F38, 0x1F40): mappings[i] = 0x0399  # Ι with breathings/accents
for i in range(0x1F40, 0x1F46): mappings[i] = 0x03BF  # ο with breathings/accents
for i in range(0x1F48, 0x1F4E): mappings[i] = 0x039F  # Ο with breathings/accents
for i in range(0x1F50, 0x1F58): mappings[i] = 0x03C5  # υ with breathings/accents
for i in range(0x1F59, 0x1F60): mappings[i] = 0x03A5  # Υ with breathings/accents
for i in range(0x1F60, 0x1F70): mappings[i] = 0x03C9  # ω with breathings/accents
for i in range(0x1F68, 0x1F70): mappings[i] = 0x03A9  # Ω with breathings/accents

# Vowels with varia/oxia
for i in range(0x1F70, 0x1F72): mappings[i] = 0x03B1  # α
for i in range(0x1F72, 0x1F74): mappings[i] = 0x03B5  # ε
for i in range(0x1F74, 0x1F76): mappings[i] = 0x03B7  # η
for i in range(0x1F76, 0x1F78): mappings[i] = 0x03B9  # ι
for i in range(0x1F78, 0x1F7A): mappings[i] = 0x03BF  # ο
for i in range(0x1F7A, 0x1F7C): mappings[i] = 0x03C5  # υ
for i in range(0x1F7C, 0x1F7E): mappings[i] = 0x03C9  # ω

# Alpha with iota subscript combinations
for i in range(0x1F80, 0x1F90): mappings[i] = 0x03B1  # α with iota subscript
for i in range(0x1F88, 0x1F90): mappings[i] = 0x0391  # Α with iota subscript
for i in range(0x1F90, 0x1FA0): mappings[i] = 0x03B7  # η with iota subscript
for i in range(0x1F98, 0x1FA0): mappings[i] = 0x0397  # Η with iota subscript
for i in range(0x1FA0, 0x1FB0): mappings[i] = 0x03C9  # ω with iota subscript
for i in range(0x1FA8, 0x1FB0): mappings[i] = 0x03A9  # Ω with iota subscript

# More alpha combinations
for i in range(0x1FB0, 0x1FB5): mappings[i] = 0x03B1  # α
for i in range(0x1FB6, 0x1FBC): mappings[i] = 0x03B1  # α
mappings[0x1FBC] = 0x0391  # Α with prosgegrammeni

# Eta combinations
for i in range(0x1FC0, 0x1FC5): mappings[i] = 0x03B7  # η
for i in range(0x1FC6, 0x1FCC): mappings[i] = 0x03B7  # η
mappings[0x1FCC] = 0x0397  # Η with prosgegrammeni

# Iota combinations
for i in range(0x1FD0, 0x1FD4): mappings[i] = 0x03B9  # ι
for i in range(0x1FD6, 0x1FDC): mappings[i] = 0x03B9  # ι
for i in range(0x1FD8, 0x1FDC): mappings[i] = 0x0399  # Ι

# Upsilon combinations
for i in range(0x1FE0, 0x1FE4): mappings[i] = 0x03C5  # υ
for i in range(0x1FE4, 0x1FED): mappings[i] = 0x03C1  # ρ
for i in range(0x1FE6, 0x1FED): mappings[i] = 0x03C5  # υ
for i in range(0x1FE8, 0x1FED): mappings[i] = 0x03A5  # Υ

# Omega combinations
for i in range(0x1FF0, 0x1FF5): mappings[i] = 0x03C9  # ω
for i in range(0x1FF6, 0x1FFC): mappings[i] = 0x03C9  # ω
mappings[0x1FFC] = 0x03A9  # Ω with prosgegrammeni

# Rho with breathings
mappings[0x1FE4] = 0x03C1  # ῤ -> ρ
mappings[0x1FE5] = 0x03C1  # ῥ -> ρ
mappings[0x1FEC] = 0x03A1  # Ῥ -> Ρ

print(f"Processing {len(mappings)} character mappings...")

# Apply mappings by copying glyphs
successful = 0
for source, target in mappings.items():
    try:
        # Check if we have the target character in the font
        if target in font:
            # Get the target glyph
            target_glyph = font[target]
            # Create or select the source position
            font.selection.select(source)
            font.createChar(source)
            # Copy from target to source
            font.selection.select(target)
            font.copy()
            font.selection.select(source)
            font.paste()
            successful += 1
            if successful % 50 == 0:
                print(f"  Processed {successful} mappings...")
        else:
            print(f"Warning: Base character U+{target:04X} not found in font")
    except Exception as e:
        # Silently skip characters that don't exist
        pass

print(f"Successfully mapped {successful} characters")

# Set font metadata
font.fontname = "SinaiticusNoMarks"
font.fullname = "Sinaiticus No Diacritical Marks"
font.familyname = "Sinaiticus No Marks"

# Generate the output font
print(f"Saving enhanced font to {output_font}...")
font.generate(output_font)
font.close()

print(f"Enhanced font saved to {output_font}")