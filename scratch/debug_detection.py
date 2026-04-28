import cv2
import numpy as np
import os
import sys

# Add root to sys.path
sys.path.append(os.getcwd())

from engine.face_engine import FaceEngine

def debug_detection(image_path):
    print(f"Debugging detection for: {image_path}")
    engine = FaceEngine()
    
    img = cv2.imread(image_path)
    if img is None:
        print(f"Error: Could not read image at {image_path}")
        return

    # Try detection
    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    # Use the same preprocessing as the engine
    preprocessed = engine._preprocess(rgb)
    
    # Check YuNet initialization
    if engine._yunet is None:
        print("YuNet not initialized. Falling back to Haar.")
    
    # Try YuNet detection with different thresholds
    if engine._yunet:
        h, w = preprocessed.shape[:2]
        engine._yunet.setInputSize((w, h))
        
        for thresh in [0.8, 0.7, 0.6, 0.5, 0.4]:
            engine._yunet.setScoreThreshold(thresh)
            _, faces = engine._yunet.detect(preprocessed)
            count = len(faces) if faces is not None else 0
            print(f"YuNet (thresh={thresh}): Found {count} faces")
            if faces is not None:
                for i, face in enumerate(faces):
                    score = face[-1]
                    print(f"  Face {i+1}: score={score:.4f}, bbox={face[:4]}")

    # Try Haar fallback
    gray = cv2.cvtColor(preprocessed, cv2.COLOR_RGB2GRAY)
    faces_frontal = engine._detector_frontal.detectMultiScale(gray, 1.1, 5)
    print(f"Haar Frontal: Found {len(faces_frontal)} faces")

if __name__ == "__main__":
    image_path = "C:/Users/akash/Downloads/WhatsApp Image 2026-04-28 at 20.54.53 (1).jpeg"
    debug_detection(image_path)
