# Usage Guide - Sinaiticus Font Generation

## Step-by-Step Instructions

### Step 1: Start the System

1. Open Terminal
2. Navigate to project directory:
   ```bash
   cd /Users/user1/git/sinaiticusfont
   ```

3. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```

4. Start the server:
   ```bash
   python3 serve_with_font_fixed.py
   ```
   
   You should see:
   ```
   Server running at http://localhost:8080/
   Open http://localhost:8080/batch_review.html in your browser
   ```

### Step 2: Open the Review Interface

1. Open your web browser (Chrome, Firefox, or Safari)
2. Go to: http://localhost:8080/batch_review.html
3. You should see the character review interface with buttons at the top

### Step 3: Load Characters for Review

You have several options:

#### Option A: K-means Clustering (Recommended)
1. Click **"Load K-Means Clusters"** button
2. Wait for clustering to complete (may take 30-60 seconds)
3. A cluster selector will appear showing grouped similar characters
4. Click on any cluster to view its characters

#### Option B: Show All Characters
1. Click **"Show All"** button
2. Displays all characters sorted by size/quality
3. Use sample size control to limit display

#### Option C: Filter by Source
1. Select a manuscript page from the **Source dropdown**
2. Click **"Load K-Means Clusters"** or **"Show All"**
3. Only characters from that source will appear

### Step 4: Classify Characters

1. **Review each character** in the grid
2. **Use the dropdown** below each character to classify it:
   - Select the appropriate Greek letter (ALPHA, BETA, GAMMA, etc.)
   - Or mark as NON_LETTER if it's not a letter
   - Leave as UNCLASSIFIED if unsure

3. **Progress indicator** at the top shows:
   - Letters Found: 21/24 (your progress)
   - Missing Letters: Lists which Greek letters haven't been found

4. **Find similar characters**:
   - Click the **"Similar"** button on any character
   - System will show visually similar characters
   - Useful for finding more examples of the same letter

### Step 5: Save Your Work

#### Automatic Saving
- Classifications are automatically saved to browser localStorage
- No action needed for basic saving

#### Manual Save to File
1. Click **"Save Review"** button
2. Creates a JSON file with timestamp: `review_data_YYYY-MM-DD.json`
3. Confirmation message shows number of items saved

### Step 6: Create the Font

1. **Ensure you have classified letters**:
   - Check the progress indicator (should show 21/24 or similar)
   - You need at least a few letters classified

2. **Click "🔤 Create Test Font"** button

3. **Wait for processing**:
   - Server collects all classified letters
   - FontForge generates the TTF file
   - Test page is created

4. **Test page opens automatically**:
   - Shows your font with all classified letters
   - Displays sample text
   - Lists missing letters (grayed out)

### Step 7: Use Your Font

1. **Find the generated files**:
   - Font file: `sinaiticus_test_YYYYMMDD_HHMMSS.ttf`
   - Test page: `test_font_YYYYMMDD_HHMMSS.html`

2. **Install the font** (optional):
   - macOS: Double-click TTF file and click "Install Font"
   - Windows: Right-click TTF file and select "Install"
   - Linux: Copy to ~/.fonts/ directory

3. **Use in applications**:
   - Font name: "Sinaiticus"
   - Includes uppercase Greek letters you classified
   - Lowercase letters reference uppercase

## Keyboard Shortcuts

While reviewing characters:
- **Tab**: Move to next character
- **Shift+Tab**: Move to previous character
- **Enter**: Confirm current selection

## Tips for Better Results

### Classification Tips
1. **Start with clear examples**: Look for well-preserved, complete letters
2. **Use clustering**: Similar characters are often the same letter
3. **Compare with references**: Keep a Greek alphabet reference handy
4. **Be consistent**: If unsure, mark as UNCLASSIFIED rather than guessing

### Finding Missing Letters
1. Check the **"Missing Letters"** list at the top
2. Use the cluster view to find potential matches
3. Try different source pages - some letters may be more common in certain texts

### Quality Improvement
1. **Review multiple examples**: Classification improves with more samples
2. **Use "Similar" feature**: Find the best quality version of each letter
3. **Check different sources**: Some manuscript pages have better preservation

## Common Tasks

### Loading Previous Work
1. Click **"📂 Load Saved File"** button
2. Or refresh the page - localStorage data loads automatically

### Clearing and Starting Over
1. Click **"Clear All"** button
2. Confirm the action
3. All current classifications will be removed

### Changing Cluster Count
1. Modify the **K value** input (default: 200)
2. Click **"Load K-Means Clusters"** again
3. Higher K = more clusters (finer grouping)
4. Lower K = fewer clusters (broader grouping)

### Batch Classification
1. Load a cluster with similar characters
2. If they all look like the same letter, classify them sequentially
3. Use Tab key to move quickly between characters

## Troubleshooting

### Nothing Appears When Loading
- Check browser console (F12) for errors
- Ensure server is running
- Try refreshing the page
- Check that letters_for_review/ directory has images

### Classifications Not Saving
- Check browser localStorage is enabled
- Try manual save with "Save Review" button
- Look for confirmation messages

### Font Generation Fails
- Ensure FontForge is installed
- Check server console for error messages
- Verify at least some letters are classified
- Try with fewer letters first

### Test Page Doesn't Open
- Check for popup blockers
- Look in server console for the URL
- Manually open test_font_*.html file

### Font Looks Wrong
- Verify character images are correct
- Check that classifications match the letters
- Some manuscript damage may affect quality
- Try different character examples

## Expected Results

After successful completion, you should have:

1. **Classification Data**:
   - 21 out of 24 Greek letters identified
   - Multiple examples per letter
   - Saved review data files

2. **Generated Font**:
   - TTF file with your classified letters
   - Proper Unicode mappings
   - Based on actual manuscript characters

3. **Test Page**:
   - Visual confirmation of your font
   - Character inventory
   - Sample Greek text display

## Advanced Features

### Custom Sample Size
- Adjust the **Sample Size** input (default: 50)
- Controls how many characters display at once
- Larger values may slow browser performance

### Export Classifications
1. Open browser Developer Tools (F12)
2. Console tab
3. Type: `JSON.stringify(letterExampleCounts)`
4. Copy the output for external use

### Manual Font Testing
1. Create a new HTML file
2. Add font-face CSS:
   ```css
   @font-face {
     font-family: 'Sinaiticus';
     src: url('sinaiticus_test_TIMESTAMP.ttf');
   }
   ```
3. Use in your content:
   ```html
   <p style="font-family: Sinaiticus">ΑΒΓΔΕ</p>
   ```

## Support

### Getting Help
- Check TECHNICAL_DOCUMENTATION.md for detailed information
- Review browser console for error messages
- Examine server output for processing details

### Reporting Issues
Document:
1. What you were trying to do
2. What actually happened
3. Any error messages
4. Browser and OS information

### Known Limitations
- Only uppercase Greek letters supported
- One character variant per letter used in font
- Manual classification required (no OCR)
- Browser must support localStorage
- FontForge must be installed for font generation