import cv2
import numpy as np
import os
from engine.face_engine import FaceEngine

def test_detection():
    print("Testing Face Engine with YuNet...")
    engine = FaceEngine()
    
    if engine._yunet is not None:
        print("✓ YuNet detector is initialized correctly.")
    else:
        print("✗ YuNet detector failed to initialize.")
        return

    # Create a dummy image with a face-like structure (or just a black image to test crash)
    dummy_img = np.zeros((480, 640, 3), dtype=np.uint8)
    try:
        results = engine._detect_faces(dummy_img)
        print(f"Detection test successful. Found {len(results)} faces in blank image.")
    except Exception as e:
        print(f"✗ Detection test failed: {e}")

if __name__ == "__main__":
    test_detection()
