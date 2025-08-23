#!/usr/bin/env python3
"""
Simple classifier training script for Greek letters from Codex Sinaiticus
Uses the reviewed data to train a basic CNN model
"""

import json
import os
import numpy as np
from PIL import Image
from collections import defaultdict
import random

def load_training_data(json_files):
    """Load and combine all review JSON files"""
    all_data = []
    
    # Load each review file
    for json_file in json_files:
        if os.path.exists(json_file):
            with open(json_file, 'r') as f:
                data = json.load(f)
                all_data.extend(data)
    
    # Group by classification
    by_class = defaultdict(list)
    for item in all_data:
        if item['classification'] not in ['UNCLASSIFIED', 'NON_LETTER']:
            by_class[item['classification']].append(item)
    
    return by_class

def prepare_dataset(by_class, target_size=(32, 32), min_samples=3):
    """Prepare images and labels for training"""
    X = []
    y = []
    class_names = []
    
    # Filter classes with enough samples
    valid_classes = {k: v for k, v in by_class.items() if len(v) >= min_samples}
    
    print(f"\nPreparing dataset with {len(valid_classes)} classes:")
    
    for class_idx, (class_name, items) in enumerate(sorted(valid_classes.items())):
        class_names.append(class_name)
        print(f"  {class_name}: {len(items)} samples")
        
        for item in items:
            try:
                # Load and preprocess image
                img_path = item['path']
                if os.path.exists(img_path):
                    img = Image.open(img_path).convert('L')  # Grayscale
                    img = img.resize(target_size, Image.Resampling.LANCZOS)
                    img_array = np.array(img) / 255.0  # Normalize
                    X.append(img_array)
                    y.append(class_idx)
            except Exception as e:
                print(f"    Error loading {img_path}: {e}")
    
    return np.array(X), np.array(y), class_names

def train_simple_classifier(X, y, class_names):
    """Train a simple classifier using scikit-learn"""
    try:
        from sklearn.model_selection import train_test_split
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.metrics import classification_report, confusion_matrix
        import joblib
        
        # Flatten images for sklearn
        X_flat = X.reshape(X.shape[0], -1)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_flat, y, test_size=0.2, random_state=42, stratify=y
        )
        
        print(f"\nTraining Random Forest classifier...")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        
        # Train classifier
        clf = RandomForestClassifier(n_estimators=100, random_state=42)
        clf.fit(X_train, y_train)
        
        # Evaluate
        y_pred = clf.predict(X_test)
        print("\nClassification Report:")
        # Get unique labels in test set
        unique_labels = np.unique(y_test)
        target_names_subset = [class_names[i] for i in unique_labels]
        print(classification_report(y_test, y_pred, labels=unique_labels, target_names=target_names_subset))
        
        # Save model
        model_data = {
            'classifier': clf,
            'class_names': class_names,
            'image_size': (32, 32)
        }
        joblib.dump(model_data, 'greek_letter_classifier.pkl')
        print("\nModel saved to greek_letter_classifier.pkl")
        
        return clf
        
    except ImportError:
        print("\nScikit-learn not installed. Install with: pip install scikit-learn joblib")
        return None

def train_neural_network(X, y, class_names):
    """Train a CNN using TensorFlow/Keras"""
    try:
        import tensorflow as tf
        from tensorflow import keras
        from sklearn.model_selection import train_test_split
        
        # Add channel dimension for CNN
        X = X.reshape(X.shape[0], 32, 32, 1)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Convert to categorical
        y_train = keras.utils.to_categorical(y_train, len(class_names))
        y_test = keras.utils.to_categorical(y_test, len(class_names))
        
        print(f"\nBuilding CNN model...")
        
        # Build simple CNN
        model = keras.Sequential([
            keras.layers.Conv2D(32, (3, 3), activation='relu', input_shape=(32, 32, 1)),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Conv2D(64, (3, 3), activation='relu'),
            keras.layers.MaxPooling2D((2, 2)),
            keras.layers.Flatten(),
            keras.layers.Dense(128, activation='relu'),
            keras.layers.Dropout(0.5),
            keras.layers.Dense(len(class_names), activation='softmax')
        ])
        
        model.compile(
            optimizer='adam',
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        print(model.summary())
        
        # Train
        history = model.fit(
            X_train, y_train,
            epochs=20,
            batch_size=32,
            validation_data=(X_test, y_test),
            verbose=1
        )
        
        # Save model
        model.save('greek_letter_cnn.h5')
        print("\nCNN model saved to greek_letter_cnn.h5")
        
        # Save class names
        with open('class_names.json', 'w') as f:
            json.dump(class_names, f)
        
        return model
        
    except ImportError:
        print("\nTensorFlow not installed. Install with: pip install tensorflow")
        return None

def create_training_summary(by_class):
    """Create a summary of the training data"""
    summary = {
        'total_classes': len(by_class),
        'total_samples': sum(len(items) for items in by_class.values()),
        'classes': {}
    }
    
    for class_name, items in sorted(by_class.items()):
        summary['classes'][class_name] = {
            'count': len(items),
            'sources': list(set(item['source'] for item in items)),
            'avg_quality': np.mean([item['quality'] for item in items]),
            'size_range': {
                'width': [min(item['width'] for item in items), 
                         max(item['width'] for item in items)],
                'height': [min(item['height'] for item in items),
                          max(item['height'] for item in items)]
            }
        }
    
    # Save summary
    with open('training_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    print("\nTraining Data Summary:")
    print(f"  Total classes: {summary['total_classes']}")
    print(f"  Total samples: {summary['total_samples']}")
    print("\nSamples per class:")
    for class_name, info in sorted(summary['classes'].items()):
        print(f"  {class_name}: {info['count']} samples (avg quality: {info['avg_quality']:.1f}%)")
    
    return summary

def main():
    """Main training pipeline"""
    print("Greek Letter Classifier Training")
    print("=" * 50)
    
    # Look for review data files
    review_files = [f for f in os.listdir('.') if f.startswith('review_data_') and f.endswith('.json')]
    
    if not review_files:
        print("\nNo review data files found!")
        print("Please use the batch review tool to create review_data_*.json files first.")
        return
    
    print(f"\nFound {len(review_files)} review file(s): {', '.join(review_files)}")
    
    # Load all training data
    by_class = load_training_data(review_files)
    
    if not by_class:
        print("\nNo valid training data found in review files!")
        return
    
    # Create summary
    summary = create_training_summary(by_class)
    
    # Check if we have enough classes
    if len(by_class) < 10:
        print(f"\nWarning: Only {len(by_class)} letter classes found. ")
        print("Consider reviewing more samples to find all 24 Greek letters.")
    
    # Prepare dataset
    X, y, class_names = prepare_dataset(by_class)
    
    if len(X) < 50:
        print(f"\nWarning: Only {len(X)} total samples. This may not be enough for good training.")
        print("Consider reviewing more samples.")
    
    print(f"\nDataset prepared: {len(X)} samples, {len(class_names)} classes")
    
    # Try different training methods
    print("\n" + "=" * 50)
    print("Training classifiers...")
    
    # Simple sklearn classifier (always available)
    clf = train_simple_classifier(X, y, class_names)
    
    # Neural network (if TensorFlow is available)
    # model = train_neural_network(X, y, class_names)
    
    print("\n" + "=" * 50)
    print("Training complete!")
    print("\nNext steps:")
    print("1. Review training_summary.json to see which letters are missing")
    print("2. Use batch_review.html to find and label missing letters")
    print("3. Re-run this script to update the classifier")
    print("4. Use the classifier to auto-predict new samples")

if __name__ == "__main__":
    main()