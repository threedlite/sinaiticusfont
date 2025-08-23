#!/usr/bin/env python3
"""
Interactive HTML tool for manually classifying character clusters
"""

import json
from pathlib import Path
import base64
import cv2

BASE_DIR = Path(__file__).parent.parent
BUILD_DIR = BASE_DIR / "build"
CLUSTERS_DIR = BUILD_DIR / "clusters"

def image_to_base64(image_path):
    """Convert image to base64 for embedding in HTML"""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def create_classification_tool():
    """Create an interactive HTML tool for character classification"""
    
    # Load cluster data
    with open(CLUSTERS_DIR / 'clusters.json', 'r') as f:
        cluster_data = json.load(f)
    
    # Greek letter mapping with proper uncial characteristics
    greek_letters = [
        ('Α', 'ALPHA', 'Triangle-like shape'),
        ('Β', 'BETA', 'B-like with two bowls'),
        ('Γ', 'GAMMA', 'L-shaped or inverted L'),
        ('Δ', 'DELTA', 'Triangle shape'),
        ('Ε', 'EPSILON', 'E-like with horizontal bars'),
        ('Ζ', 'ZETA', 'Z-like diagonal'),
        ('Η', 'ETA', 'H-like with crossbar'),
        ('Θ', 'THETA', 'O with horizontal bar'),
        ('Ι', 'IOTA', 'Simple vertical line'),
        ('Κ', 'KAPPA', 'K-like with diagonal arms'),
        ('Λ', 'LAMBDA', 'Inverted V shape'),
        ('Μ', 'MU', 'M-like with vertical stems'),
        ('Ν', 'NU', 'N-like diagonal'),
        ('Ξ', 'XI', 'Three horizontal lines'),
        ('Ο', 'OMICRON', 'Simple circle/oval'),
        ('Π', 'PI', 'Gate-like, horizontal top'),
        ('Ρ', 'RHO', 'P-like with curved bowl'),
        ('Σ', 'SIGMA', 'C-like lunate curve'),
        ('Τ', 'TAU', 'T-like cross'),
        ('Υ', 'UPSILON', 'Y-like or V on stem'),
        ('Φ', 'PHI', 'Circle with vertical line'),
        ('Χ', 'CHI', 'X-like diagonal cross'),
        ('Ψ', 'PSI', 'Trident shape'),
        ('Ω', 'OMEGA', 'Double-O or wide ω shape'),
        ('', 'UNKNOWN', 'Not a letter'),
        ('', 'DECORATION', 'Decorative element'),
        ('', 'DAMAGED', 'Too damaged to identify'),
        ('', 'LIGATURE', 'Combined letters'),
    ]
    
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Codex Sinaiticus Character Classification Tool</title>
    <style>
        * { box-sizing: border-box; }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            margin: 0;
            padding: 20px;
            background: #f5f5f5;
        }
        
        .header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        h1 {
            margin: 0 0 10px 0;
            color: #333;
        }
        
        .instructions {
            color: #666;
            line-height: 1.6;
        }
        
        .container {
            display: grid;
            grid-template-columns: 250px 1fr;
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .sidebar {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: fit-content;
            position: sticky;
            top: 20px;
        }
        
        .greek-letters {
            display: grid;
            grid-template-columns: 1fr;
            gap: 5px;
            margin-top: 15px;
        }
        
        .letter-btn {
            display: flex;
            align-items: center;
            padding: 8px 12px;
            border: 2px solid #ddd;
            border-radius: 4px;
            background: white;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .letter-btn:hover {
            background: #f0f0f0;
            border-color: #4CAF50;
        }
        
        .letter-btn.selected {
            background: #4CAF50;
            color: white;
            border-color: #4CAF50;
        }
        
        .letter-symbol {
            font-size: 24px;
            width: 40px;
            text-align: center;
            font-weight: bold;
        }
        
        .letter-name {
            flex: 1;
            font-size: 12px;
            margin-left: 10px;
        }
        
        .clusters {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        
        .cluster-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: all 0.2s;
        }
        
        .cluster-card.classified {
            border: 2px solid #4CAF50;
        }
        
        .cluster-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        
        .cluster-id {
            font-weight: bold;
            color: #666;
        }
        
        .cluster-count {
            font-size: 12px;
            color: #999;
        }
        
        .cluster-image {
            width: 100%;
            height: auto;
            border: 1px solid #eee;
            border-radius: 4px;
            margin: 10px 0;
        }
        
        .cluster-classification {
            display: flex;
            align-items: center;
            padding: 10px;
            background: #f9f9f9;
            border-radius: 4px;
            margin-top: 10px;
        }
        
        .classification-label {
            font-size: 20px;
            font-weight: bold;
            margin-right: 10px;
        }
        
        .classification-name {
            flex: 1;
            color: #666;
        }
        
        .clear-btn {
            padding: 4px 8px;
            background: #ff5252;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        
        .actions {
            position: fixed;
            bottom: 20px;
            right: 20px;
            display: flex;
            gap: 10px;
        }
        
        .action-btn {
            padding: 12px 24px;
            background: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        
        .action-btn:hover {
            background: #1976D2;
        }
        
        .export-btn {
            background: #4CAF50;
        }
        
        .export-btn:hover {
            background: #388E3C;
        }
        
        .stats {
            padding: 15px;
            background: #e3f2fd;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .special-section {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 2px solid #eee;
        }
        
        .section-title {
            font-size: 12px;
            color: #999;
            margin-bottom: 10px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Codex Sinaiticus Character Classification Tool</h1>
        <div class="instructions">
            <p>Click on a Greek letter in the sidebar, then click on the cluster(s) that match that letter.</p>
            <p>Remember: Sigma is always lunate (C-shaped) and Omega is always double-o shaped in this manuscript.</p>
        </div>
    </div>
    
    <div class="container">
        <div class="sidebar">
            <div class="stats" id="stats">
                <div>Clusters: <span id="total-clusters">0</span></div>
                <div>Classified: <span id="classified-count">0</span></div>
                <div>Remaining: <span id="remaining-count">0</span></div>
            </div>
            
            <div class="section-title">Greek Letters</div>
            <div class="greek-letters" id="greek-letters">
                <!-- Letters will be inserted here -->
            </div>
            
            <div class="special-section">
                <div class="section-title">Special Categories</div>
                <div class="greek-letters" id="special-categories">
                    <!-- Special categories will be inserted here -->
                </div>
            </div>
        </div>
        
        <div class="clusters" id="clusters">
            <!-- Clusters will be inserted here -->
        </div>
    </div>
    
    <div class="actions">
        <button class="action-btn" onclick="saveProgress()">Save Progress</button>
        <button class="action-btn export-btn" onclick="exportMapping()">Export Mapping</button>
    </div>
    
    <script>
        let selectedLetter = null;
        let classifications = {};
        
        // Load saved progress if exists
        const saved = localStorage.getItem('cluster_classifications');
        if (saved) {
            classifications = JSON.parse(saved);
        }
        
        const greekLetters = ''' + json.dumps(greek_letters) + ''';
        const clusterData = ''' + json.dumps(cluster_data) + ''';
        
        function initializeLetterButtons() {
            const lettersContainer = document.getElementById('greek-letters');
            const specialContainer = document.getElementById('special-categories');
            
            greekLetters.forEach((letter, index) => {
                const [symbol, name, description] = letter;
                const btn = document.createElement('button');
                btn.className = 'letter-btn';
                btn.dataset.index = index;
                btn.dataset.name = name;
                btn.dataset.symbol = symbol;
                btn.onclick = () => selectLetter(index);
                
                btn.innerHTML = `
                    <span class="letter-symbol">${symbol || '?'}</span>
                    <span class="letter-name">${name}</span>
                `;
                
                btn.title = description;
                
                if (name === 'UNKNOWN' || name === 'DECORATION' || name === 'DAMAGED' || name === 'LIGATURE') {
                    specialContainer.appendChild(btn);
                } else {
                    lettersContainer.appendChild(btn);
                }
            });
        }
        
        function selectLetter(index) {
            // Clear previous selection
            document.querySelectorAll('.letter-btn').forEach(btn => {
                btn.classList.remove('selected');
            });
            
            // Set new selection
            const btn = document.querySelector(`[data-index="${index}"]`);
            btn.classList.add('selected');
            selectedLetter = index;
        }
        
        function initializeClusters() {
            const container = document.getElementById('clusters');
            
            Object.entries(clusterData).forEach(([clusterId, data]) => {
                const card = document.createElement('div');
                card.className = 'cluster-card';
                card.dataset.clusterId = clusterId;
                
                // Check if already classified
                if (classifications[clusterId] !== undefined) {
                    card.classList.add('classified');
                }
                
                card.innerHTML = `
                    <div class="cluster-header">
                        <span class="cluster-id">Cluster ${clusterId}</span>
                        <span class="cluster-count">${data.count} chars</span>
                    </div>
                    <img class="cluster-image" id="cluster-img-${clusterId}">
                    <div class="cluster-classification" id="class-${clusterId}" style="display: none;">
                        <span class="classification-label"></span>
                        <span class="classification-name"></span>
                        <button class="clear-btn" onclick="clearClassification('${clusterId}')">Clear</button>
                    </div>
                `;
                
                card.onclick = (e) => {
                    if (!e.target.classList.contains('clear-btn')) {
                        classifyCluster(clusterId);
                    }
                };
                
                container.appendChild(card);
                
                // Load cluster image
                loadClusterImage(clusterId);
                
                // Show existing classification
                if (classifications[clusterId] !== undefined) {
                    showClassification(clusterId, classifications[clusterId]);
                }
            });
            
            updateStats();
        }
        
        function loadClusterImage(clusterId) {
            // Load the cluster visualization image
            const img = document.getElementById(`cluster-img-${clusterId}`);
            // Use relative path from HTML file location
            img.src = `build/clusters/cluster_${String(clusterId).padStart(2, '0')}.png`;
        }
        
        function classifyCluster(clusterId) {
            if (selectedLetter === null) {
                alert('Please select a Greek letter first');
                return;
            }
            
            classifications[clusterId] = selectedLetter;
            
            const card = document.querySelector(`[data-cluster-id="${clusterId}"]`);
            card.classList.add('classified');
            
            showClassification(clusterId, selectedLetter);
            updateStats();
        }
        
        function showClassification(clusterId, letterIndex) {
            const classDiv = document.getElementById(`class-${clusterId}`);
            const [symbol, name] = greekLetters[letterIndex];
            
            classDiv.style.display = 'flex';
            classDiv.querySelector('.classification-label').textContent = symbol || '?';
            classDiv.querySelector('.classification-name').textContent = name;
        }
        
        function clearClassification(clusterId) {
            delete classifications[clusterId];
            
            const card = document.querySelector(`[data-cluster-id="${clusterId}"]`);
            card.classList.remove('classified');
            
            const classDiv = document.getElementById(`class-${clusterId}`);
            classDiv.style.display = 'none';
            
            updateStats();
        }
        
        function updateStats() {
            const total = Object.keys(clusterData).length;
            const classified = Object.keys(classifications).length;
            
            document.getElementById('total-clusters').textContent = total;
            document.getElementById('classified-count').textContent = classified;
            document.getElementById('remaining-count').textContent = total - classified;
        }
        
        function saveProgress() {
            localStorage.setItem('cluster_classifications', JSON.stringify(classifications));
            alert('Progress saved!');
        }
        
        function exportMapping() {
            const mapping = {};
            
            Object.entries(classifications).forEach(([clusterId, letterIndex]) => {
                const [symbol, name] = greekLetters[letterIndex];
                mapping[clusterId] = {
                    letter: name,
                    symbol: symbol,
                    unicode: symbol ? symbol.charCodeAt(0).toString(16).toUpperCase() : null,
                    samples: clusterData[clusterId].samples
                };
            });
            
            const json = JSON.stringify(mapping, null, 2);
            const blob = new Blob([json], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = 'character_mapping.json';
            a.click();
            
            URL.revokeObjectURL(url);
        }
        
        // Initialize
        initializeLetterButtons();
        initializeClusters();
    </script>
</body>
</html>'''
    
    # Save HTML file
    output_file = BASE_DIR / 'classify_characters.html'
    with open(output_file, 'w') as f:
        f.write(html_content)
    
    print(f"Classification tool created: {output_file}")
    return output_file

def main():
    print("Creating interactive classification tool...")
    
    if not CLUSTERS_DIR.exists():
        print("Error: Clusters not found. Run cluster_characters.py first.")
        return
    
    tool_file = create_classification_tool()
    print(f"\n✓ Success!")
    print(f"Open {tool_file} in your browser to classify characters")
    print("\nInstructions:")
    print("1. Click on a Greek letter in the sidebar")
    print("2. Click on cluster images that match that letter")
    print("3. Save your progress regularly")
    print("4. Export the mapping when done")

if __name__ == "__main__":
    main()