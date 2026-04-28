import urllib.request
import os
from pathlib import Path

MODEL_DIR = Path("assets/models")
MODEL_PATH = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"

def download():
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading from {URL}...")
    try:
        urllib.request.urlretrieve(URL, MODEL_PATH)
        print(f"Downloaded to {MODEL_PATH}")
        print(f"Size: {os.path.getsize(MODEL_PATH)} bytes")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    download()
