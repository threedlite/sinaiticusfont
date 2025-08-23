
import fontforge
import sys
from pathlib import Path

BASE_DIR = Path(sys.argv[1])
VECTORS_DIR = BASE_DIR / "vectors"
BUILD_DIR = BASE_DIR / "build"

font = fontforge.font()
font.fontname = "CodexSinaiticus"
font.fullname = "Codex Sinaiticus"
font.familyname = "Codex Sinaiticus"
font.ascent = 800
font.descent = 200

# Find and import SVG files
svg_files = []
for vector_dir in VECTORS_DIR.glob("*"):
    if vector_dir.is_dir():
        svg_files.extend(list(vector_dir.glob("*.svg")))

# Map to Greek capitals
for idx in range(min(24, len(svg_files))):
    unicode_point = 0x0391 + idx  # Start from Greek Alpha
    glyph = font.createChar(unicode_point)
    try:
        glyph.importOutlines(str(svg_files[idx]))
        glyph.width = 600
    except:
        pass

# Add space
space = font.createChar(32)
space.width = 300

# Generate font
BUILD_DIR.mkdir(exist_ok=True)
font.generate(str(BUILD_DIR / "CodexSinaiticus.ttf"))
print("Font generated successfully")
