# Technical Documentation - Sinaiticus Font Generation System

## System Architecture Overview

The Sinaiticus Font Generation System is a web-based application that processes manuscript character images to create custom TrueType fonts. It uses a client-server architecture with FontForge integration for font generation.

## Core Components

### 1. Frontend: batch_review.html
**Purpose**: Web interface for reviewing and classifying character images

**Key Features**:
- **Character Display Grid**: Shows extracted characters in a responsive grid layout
- **K-means Clustering**: Groups visually similar characters (default k=200)
- **Classification System**: Dropdown menus for assigning Greek letter labels
- **Progress Tracking**: Real-time display of classification progress (24/24 letters completed)
- **Similar Character Search**: Feature-based similarity matching with caching
  - Fixed button functionality with proper string ID handling
  - Visual feedback: button shows "⏳ Loading..." during search
  - Prevents double-clicks with immediate button disabling
  - Feature extraction caching for improved performance
  - Cache automatically cleared when k-means clustering is performed
  - Inverted pixel values for correct similarity (black text = 1, white = 0)
- **Letter Sample Management**: Remove individual items from letter sample lists
  - Modal dialog with dropdown selection
  - Greek alphabet ordering in dropdown
  - Immediate UI update after removal

**Data Management**:
```javascript
// Main data structures
let allCharacters = [];        // All loaded character objects
let currentSamples = [];       // Currently displayed characters
let allClassifications = {};   // Character ID → letter mapping
let letterExampleCounts = {};  // Letter → array of character IDs
let seenLetters = new Set();   // Unique classified letters
const featureCache = new Map(); // Cache for extracted image features (imagePath_gridSize → features)
```

**Key Functions**:
- `loadKMeansClusters()`: Performs clustering on character images (clears feature cache)
- `findSimilarCharacters(targetCharId, buttonElement)`: Feature-based similarity search
  - Accepts string IDs like "letter_0", "letter_1"
  - Updates button UI during processing
  - Uses cached features when available
- `extractDetailedFeatures(imagePath, gridSize)`: Extracts and caches image features
  - Returns cached features if available
  - Stores features in Map with key: `imagePath_gridSize`
- `createTestFont()`: Collects classifications and sends to server
- `saveReview()`: Persists data to localStorage and server

### 2. Backend: serve_with_font_fixed.py
**Purpose**: HTTP server with font generation capabilities

**Server Configuration**:
```python
PORT = 8080
# CORS enabled for cross-origin requests
# Serves static files and handles POST endpoints
# Virtual environment required for PIL/Pillow image processing
```

**Endpoints**:

#### POST /save_review
- Receives classification data from frontend
- Saves to JSON file with timestamp
- Returns success/error status

#### POST /create_font
- Receives classifications mapping (letter → character IDs)
- Generates FontForge script dynamically
- Creates TTF font file
- Generates HTML test page
- Opens test page in browser

**Font Generation Process**:
```python
def generate_font_with_fontforge(classifications, font_file):
    # 1. Create FontForge Python script
    script = create_fontforge_script(classifications, font_file)
    
    # 2. Write to temporary file
    with tempfile.NamedTemporaryFile() as f:
        f.write(script)
        
    # 3. Execute with FontForge
    subprocess.run(['fontforge', '-script', script_path])
    
    # 4. Clean up and return status
```

### 3. FontForge Script Generation

**Dynamic Script Creation**:
The server generates a Python script for FontForge that:
1. Creates a new font with proper metadata
2. Maps Greek letters to Unicode points
3. Imports PNG images for each classified letter
4. Auto-traces bitmaps to vector outlines
5. Sets proper glyph metrics and spacing
6. Generates TTF file

**Greek Unicode Mapping**:
```python
GREEK_UNICODE = {
    'ALPHA': ('Α', 0x0391),
    'BETA': ('Β', 0x0392),
    'GAMMA': ('Γ', 0x0393),
    # ... all 24 Greek capital letters
}
```

**Glyph Processing**:
```python
for letter_name, char_ids in classifications.items():
    # Create glyph at Unicode position
    glyph = font.createChar(unicode_val)
    
    # Import character image
    img_path = f"letters_for_review/letter_{char_id}.png"
    glyph.importOutlines(img_path)
    glyph.autoTrace()  # Bitmap to vector
    
    # Special handling for tall letters
    if letter_name in ['PHI', 'PSI']:
        # Scale up 2.3x to preserve natural height
        matrix = psMat.scale(2.3)
        glyph.transform(matrix)
        # Shift down to extend above and below baseline
        matrix2 = psMat.translate(0, -500)
        glyph.transform(matrix2)
    elif letter_name == 'RHO':
        # Scale up 1.5x for descender
        matrix = psMat.scale(1.5)
        glyph.transform(matrix)
        # Shift down less to align top with x-height
        matrix2 = psMat.translate(0, -400)
        glyph.transform(matrix2)
    
    # Set metrics
    glyph.left_side_bearing = 60
    glyph.width = glyph_width + 120
```

**Special Character Processing**:
- **PHI (Φ) and PSI (Ψ)**: Extended above and below baseline
  - Original images are ~160-170 pixels tall (vs 80 for normal letters)
  - Scaled 2.3x after import to counteract FontForge's normalization
  - Shifted down 500 units to center vertically
  - Preserves manuscript's natural ascenders and descenders

- **RHO (Ρ)**: Descender below baseline
  - Scaled 1.5x for proper proportion
  - Shifted down 400 units to create descender while keeping top at x-height

- **Image Cleaning** (PHI/PSI only):
  - Morphological opening with 3x3 structure to remove noise
  - Component analysis to identify and remove isolated dots
  - Preserves main letter structure while cleaning background artifacts

**Punctuation Marks**:
The font includes comprehensive punctuation support:
- **Period (.)** - U+002E - Baseline position
- **Semicolon (;)** - U+003B - Dot at mid-height with comma below
- **Middle Dot (·)** - U+00B7 - Mid-height position
- **Greek Ano Teleia (·)** - U+0387 - Greek-specific middle dot
- **Greek Lower Numeral Sign** - U+0375 - Baseline position
- **High Dot (˙)** - U+02D9 - Above mid-height
- **Bullet (•)** - U+2022 - Same as middle dot

All punctuation uses irregular polygonal shapes to match manuscript style rather than perfect circles.

## Data Flow

### Classification Workflow
1. **Character Loading**:
   - Frontend loads manifest.json with character metadata
   - Images loaded from letters_for_review/ directory
   - Total: 27,779 characters available

2. **User Classification**:
   - User selects Greek letter from dropdown
   - Classification stored in memory (allClassifications)
   - Updates letterExampleCounts for statistics
   - Saves to localStorage automatically

3. **Data Persistence**:
   ```
   Browser Memory → localStorage → Server JSON file
   ```

### Font Generation Workflow
1. **Data Collection**:
   ```javascript
   // Frontend collects from letterExampleCounts
   reviewedChars = {
     "ALPHA": ["letter_59", "letter_338", ...],
     "BETA": ["letter_98", ...],
     // ... 21 letters total
   }
   ```

2. **Server Processing**:
   ```
   POST /create_font → Generate Script → Run FontForge → Create TTF
   ```

3. **Output Generation**:
   - TTF font file: `sinaiticus_test_TIMESTAMP.ttf`
   - Test HTML page: `test_font_TIMESTAMP.html`
   - Automatic browser opening

## Data Structures

### Raised Dot Discovery
The system identified 263 potential raised dot images in the manuscript collection:
- Detected by analyzing small (< 30x30 pixel) roughly square images
- 8 samples classified as RAISED_DOT for font reference
- Examples: letter_24293.png, letter_12721.png, letter_37790.png
- Used as reference for creating authentic manuscript-style punctuation

### Character Object
```javascript
{
  id: "letter_59",              // Unique identifier
  path: "letters_for_review/letter_00059.png",
  filename: "letter_00059.png",
  source: "1000007215",         // Manuscript page
  quality: 85,                  // Quality score
  width: 40,                    // Image dimensions
  height: 40,
  classification: "ALPHA"       // Assigned letter
}
```

### Classifications Format
```javascript
{
  "ALPHA": ["letter_59", "letter_338", "letter_221"],
  "BETA": ["letter_98", "letter_14455"],
  // ... other letters
}
```

### Review Data JSON
```json
[
  {
    "id": "letter_59",
    "path": "letters_for_review/letter_00059.png",
    "filename": "letter_00059.png",
    "source": "1000007215",
    "classification": "ALPHA",
    "corrected": true,
    "quality": 85,
    "width": 40,
    "height": 40
  }
]
```

## Algorithm Details

### K-means Clustering
**Purpose**: Group visually similar characters

**Implementation**:
```javascript
async function loadKMeansClusters(k = 200) {
    // 1. Extract features from all characters
    const features = await extractFeaturesFromAll(allCharacters);
    
    // 2. Run k-means clustering
    const clusters = performKMeans(features, k);
    
    // 3. Group characters by cluster
    const grouped = groupByCluster(allCharacters, clusters);
    
    // 4. Display cluster selector
    showClusterSelection(grouped);
}
```

**Feature Extraction**:
- 16x16 pixel grid sampling
- Grayscale intensity values
- Normalized to [0, 1] range
- 256-dimensional feature vector per character

### Similarity Search
**Purpose**: Find characters similar to a selected one

**Process**:
1. Extract detailed features (32x32 grid) with caching
2. Calculate Euclidean distance to all characters
3. Sort by distance
4. Display top 200 similar characters

**Implementation with Caching**:
```javascript
async function findSimilarCharacters(targetCharId, buttonElement) {
    // Update button UI immediately
    if (buttonElement) {
        buttonElement.innerHTML = '⏳ Loading...';
        buttonElement.disabled = true;
    }
    
    const targetChar = currentSamples.find(c => c.id === targetCharId);
    const targetFeatures = await extractDetailedFeatures(targetChar.path, 32);
    
    // Process in batches with cached features
    const similarities = [];
    for (let i = 0; i < allCharacters.length; i += 50) {
        const batch = allCharacters.slice(i, i + 50);
        const batchResults = await Promise.all(
            batch.map(async (char) => {
                const features = await extractDetailedFeatures(char.path, 32);
                const distance = euclideanDistance(targetFeatures, features);
                return { char, distance };
            })
        );
        similarities.push(...batchResults);
    }
    
    // Sort and display top results
    return similarities
        .sort((a, b) => a.distance - b.distance)
        .slice(0, 200);
}
```

**Feature Caching**:
- Features cached in Map with key: `imagePath_gridSize`
- Cache persists across searches for speed
- Automatically cleared when k-means clustering is performed
- Significantly improves performance after first extraction

## Storage Locations

### Browser Storage
- **localStorage**:
  - `all_classifications`: Complete classification mapping
  - `letter_counts`: Letter frequency data
  - `all_review_data`: Full review dataset

### File System
```
sinaiticusfont/
├── letters_for_review/         # Character images (27,779 files)
│   ├── letter_00001.png
│   ├── letter_00002.png
│   └── ...
├── review_data_*.json          # Daily backups
├── complete_review_21_letters.json  # Full dataset
├── sinaiticus_test_*.ttf       # Generated fonts
└── test_font_*.html            # Test pages
```

## Performance Considerations

### Frontend Optimizations
- **Lazy Loading**: Characters loaded on demand
- **Batch Processing**: K-means runs on subset first
- **Canvas Reuse**: Single canvas for feature extraction
- **Async Operations**: Non-blocking UI updates

### Backend Optimizations
- **Script Caching**: FontForge script generated once
- **Subprocess Management**: Proper cleanup of temp files
- **Error Recovery**: Graceful handling of FontForge failures

## Error Handling

### Common Issues and Solutions

**Issue**: F-string evaluation in script generation
**Solution**: Use string concatenation instead of f-strings
```python
# Wrong
script = f"print(f'Processing {letter_name}')"

# Correct
script = "print('Processing ' + str(letter_name))"
```

**Issue**: Character ID format mismatch
**Solution**: Handle both formats
```javascript
// IDs can be "75" or "letter_75"
const numericId = charId.replace('letter_', '');
```

**Issue**: Missing character images
**Solution**: Create placeholder glyphs
```python
if not os.path.exists(img_path):
    # Create simple rectangle placeholder
    pen = glyph.glyphPen()
    pen.moveTo((100, 100))
    # ... draw rectangle
```

## Security Considerations

1. **CORS Headers**: Enabled for local development
2. **Input Validation**: Character IDs sanitized
3. **File Path Security**: Restricted to project directory
4. **Process Isolation**: FontForge runs in subprocess
5. **Temporary File Cleanup**: Automatic deletion

## Testing Procedures

### Manual Testing Checklist
1. [ ] Server starts on port 8080
2. [ ] batch_review.html loads successfully
3. [ ] Characters display in grid
4. [ ] K-means clustering completes
5. [ ] Classifications save to localStorage
6. [ ] Save Review persists to JSON
7. [ ] Create Test Font generates TTF
8. [ ] Test page opens automatically
9. [ ] Font displays correctly

### Validation Tests
```bash
# Test font generation endpoint
curl -X POST http://localhost:8080/create_font \
  -H "Content-Type: application/json" \
  -d '{"classifications": {"ALPHA": ["letter_59"]}}'

# Verify font file
file sinaiticus_test_*.ttf
# Output: TrueType Font data

# Check test page
curl http://localhost:8080/test_font_*.html | grep "Sinaiticus"
```

## Development Notes

### Adding New Features
1. **New Greek Letters**: Update GREEK_UNICODE mapping
2. **Different Scripts**: Modify Unicode ranges
3. **Multiple Variants**: Extend classification structure
4. **Export Formats**: Add FontForge generation options

### Debug Mode
Enable console logging:
```javascript
// In batch_review.html
const DEBUG = true;
if (DEBUG) console.log('Debug info:', data);
```

Server debug output:
```python
# In serve_with_font_fixed.py
print(f"Debug: Processing {letter_name}")
print(f"FontForge output: {result.stdout}")
```

## Dependencies

### Python Packages
```
opencv-python==4.10.0.84    # Image processing
numpy==2.0.1                # Numerical operations
Pillow==10.4.0              # Image I/O
scipy==1.14.1               # K-means clustering
scikit-image==0.24.0        # Advanced image processing
```

### System Requirements
- FontForge: Font generation engine
- Potrace: Bitmap to vector tracing (used by FontForge)
- Python 3.7+: Runtime environment
- Modern browser: Chrome/Firefox/Safari with localStorage

## Version History

### Current Version (2024-08)
- 21 of 24 Greek letters classified
- K-means clustering with k=200
- Feature-based similarity search with caching
- Automatic font generation
- Browser-based test page

### Recent Updates (2025-08-23)
1. **Similar Button Not Working**:
   - Issue: Character IDs were strings ("letter_0") but passed without quotes to onclick handler
   - Fix: Added quotes around ID parameter in onclick handler
   - Fix: Removed unnecessary parseInt conversion in findSimilarCharacters function

2. **No Visual Feedback During Search**:
   - Issue: Loading spinner only visible at top of page, not visible when scrolled down
   - Fix: Button now shows "⏳ Loading..." text during search
   - Fix: Button immediately disabled to prevent double-clicks

3. **Performance Issues**:
   - Issue: Feature extraction repeated for same images
   - Fix: Added Map-based feature cache with `imagePath_gridSize` keys
   - Fix: Cache automatically cleared when k-means clustering performed

4. **Similar Function Returning Wrong Items**:
   - Issue: Feature values inverted (white = 1, black = 0)
   - Fix: Inverted pixel values: `1 - (gray / 255)` so black text = 1

5. **Letter Sample Management**:
   - Added ability to remove individual items from letter sample lists
   - Modal dialog with dropdown selection
   - Greek alphabet ordering in dropdown

6. **PHI and PSI Characters Compressed**:
   - Issue: FontForge was shrinking tall letters to fit standard height
   - Fix: Scale PHI/PSI 2.3x after import, shift down 500 units
   - Preserves natural ascenders and descenders from manuscript

7. **RHO Descender Support**:
   - Added special handling for RHO to extend below baseline
   - Scaled 1.5x, shifted down 400 units
   - Top aligns with x-height while bottom extends as descender

8. **Background Noise in PHI/PSI**:
   - Implemented image cleaning with morphological operations
   - Component analysis to remove isolated dots
   - Adjustable thresholds for PHI vs PSI

9. **Punctuation Support**:
   - Added 7 punctuation marks with manuscript-style irregular shapes
   - Period, semicolon, middle dot, Greek ano teleia, high dot, bullet
   - Discovered 263 raised dot samples in manuscript collection

10. **RAISED_DOT Classification**:
    - Identified and classified 8 manuscript dot samples
    - Used as reference for authentic punctuation shapes

### Known Limitations
1. Only first character used per letter
2. No glyph editing capabilities
3. Single font weight/style
4. Limited to Greek uppercase
5. Manual classification required

## Future Enhancements
- [ ] Support for lowercase letters
- [ ] Multiple character variants per glyph
- [ ] Automatic character recognition (OCR)
- [ ] Batch processing capabilities
- [ ] Export to additional formats (OTF, WOFF2)
- [ ] Cloud storage integration
- [ ] Collaborative review features