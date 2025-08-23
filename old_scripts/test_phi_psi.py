import fontforge
import psMat

font = fontforge.font()
font.fontname = "TestPhiPsi"

# Create PHI glyph
glyph = font.createChar(0x03A6, "PHI")
print("Importing PHI...")
glyph.importOutlines("letters_for_review/letter_42411.png", scale=False)
print("After import, before trace")
glyph.autoTrace()
print("PHI bbox:", glyph.boundingBox())

# Create PSI glyph  
glyph2 = font.createChar(0x03A8, "PSI")
print("Importing PSI...")
glyph2.importOutlines("letters_for_review/letter_41803.png", scale=False)
glyph2.autoTrace()
print("PSI bbox:", glyph2.boundingBox())

# Create ALPHA for comparison
glyph3 = font.createChar(0x0391, "ALPHA")
print("Importing ALPHA...")
glyph3.importOutlines("letters_for_review/letter_00030.png")  # With default scaling
glyph3.autoTrace()
print("ALPHA bbox:", glyph3.boundingBox())

font.generate("test_phi_psi.ttf")
print("Font generated!")
