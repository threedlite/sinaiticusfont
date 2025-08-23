# Sinaiticus Font Generation System

TATF Greek Unicode Font - SIL Open Font License (OFL)
Images are photos I took of my facsimile copy of Codex Sinaiticus


A web-based tool for reviewing manuscript character images and generating custom TrueType fonts from classified Greek letters extracted from the Codex Sinaiticus.

## Quick Start

```bash
# 1. Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python3 serve_with_font_fixed.py

# 4. Open browser to http://localhost:8080/batch_review.html
```

## Prerequisites
- Python 3.x virtual environment based on requirements.txt
- FontForge and potrace installed via brew (macOS)

