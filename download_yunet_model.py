"""Download YuNet face detection model."""

import os
import urllib.request
from pathlib import Path

MODEL_DIR = Path("assets/models")
MODEL_NAME = "face_detection_yunet_2023mar.onnx"
MODEL_PATH = MODEL_DIR / MODEL_NAME

# YuNet model URL from OpenCV GitHub
DOWNLOAD_URL = "https://github.com/opencv/opencv_zoo/raw/master/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def download_model():
    """Download YuNet model if not present."""
    if MODEL_PATH.exists():
        print(f"✓ Model already exists: {MODEL_PATH}")
        return True
    
    print(f"Downloading YuNet model from OpenCV Zoo...")
    print(f"URL: {DOWNLOAD_URL}")
    print(f"Saving to: {MODEL_PATH}")
    
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        urllib.request.urlretrieve(DOWNLOAD_URL, MODEL_PATH)
        print(f"✓ Model downloaded successfully!")
        return True
    except Exception as e:
        print(f"✗ Download failed: {e}")
        print(f"\nManual download:")
        print(f"1. Visit: {DOWNLOAD_URL}")
        print(f"2. Save as: {MODEL_PATH}")
        return False

if __name__ == "__main__":
    success = download_model()
    exit(0 if success else 1)
