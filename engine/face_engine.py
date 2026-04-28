# engine/face_engine.py

import cv2
import numpy as np
import os
import pickle
from scipy.spatial import KDTree
from config import CONFIG


class FaceEngine:
    """
    Face pipeline using OpenCV (Python 3.14 compatible):
      Stage 1 — OpenCV Haar Cascade: face detection → bounding boxes
      Stage 2 — OpenCV: normalized face crop as encoding vector

    For matching: SciPy KDTree over all registered student encodings.
    Threshold: Euclidean distance < 0.6 → match  (tunable in config)
    
    Note: Uses OpenCV Haar Cascade instead of MediaPipe for full Python 3.14 compatibility.
    """

    def __init__(self):
        # YuNet face detector (better than Haar Cascade for group photos)
        detector_path = None
        
        # Try local path first
        local_model = "assets/models/face_detection_yunet_2023mar.onnx"
        if os.path.exists(local_model):
            detector_path = local_model
        else:
            # Try OpenCV data directory
            cv_model = cv2.data.haarcascades.replace('haarcascades', '') + 'face_detection_yunet_2023mar.onnx'
            if os.path.exists(cv_model):
                detector_path = cv_model
        
        self._use_yunet = False
        if detector_path:
            try:
                self._detector = cv2.FaceDetectorYN.create(
                    detector_path,
                    "",
                    (320, 320),
                    score_threshold=0.5,
                    nms_threshold=0.3,
                    top_k=5000
                )
                self._use_yunet = True
                print("✓ YuNet detector loaded successfully")
            except Exception as e:
                print(f"⚠ YuNet initialization failed: {e}, falling back to Haar Cascade")
        
        if not self._use_yunet:
            # Fallback to Haar Cascade
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._detector = cv2.CascadeClassifier(cascade_path)
            print("ℹ Using Haar Cascade detector (download YuNet model for better accuracy)")
            print("  Run: python download_yunet_model.py")
        
        self._kdtree = None
        self._student_ids = []
        self.threshold = float(CONFIG.get("MATCH_THRESHOLD", 0.65))
        self.face_size = (64, 64)  # Fixed size for consistent encodings

    # ── Encoding ──────────────────────────────────────────────────────

    def _extract_face_encoding(self, rgb: np.ndarray, location: tuple) -> np.ndarray:
        """
        Extract a normalized encoding from a detected face region.
        Crops face, resizes to fixed size, converts to grayscale,
        and returns as flattened normalized vector.
        """
        top, right, bottom, left = location
        
        # Ensure bounds are valid
        h, w = rgb.shape[:2]
        top = max(0, top)
        left = max(0, left)
        right = min(w, right)
        bottom = min(h, bottom)
        
        # Crop face region
        face_crop = rgb[top:bottom, left:right]
        if face_crop.size == 0:
            return np.zeros(self.face_size[0] * self.face_size[1], dtype=np.float32)
        
        # Convert to grayscale and resize to fixed size
        gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
        resized = cv2.resize(gray, self.face_size)
        
        # Apply histogram equalization for robustness
        equalized = cv2.equalizeHist(resized)
        
        # Normalize to [0, 1] and flatten
        normalized = equalized.astype(np.float32) / 255.0
        encoding = normalized.flatten()
        
        return encoding

    def encode_image(self, image_bgr: np.ndarray) -> list:
        """
        Given a BGR image (from cv2.imread), return a list of encodings
        — one per detected face. Empty list if no faces found.
        """
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        preprocessed = self._preprocess(rgb)

        # Stage 1: MediaPipe detection → face locations
        locations = self._mediapipe_locations(preprocessed)

        if not locations:
            return []

        # Stage 2: OpenCV-based encodings at detected locations
        encodings = [self._extract_face_encoding(preprocessed, loc) for loc in locations]
        return encodings

    def encode_from_path(self, image_path: str) -> list:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.encode_image(img)

    def average_encodings(self, encodings: list) -> np.ndarray:
        """Average multiple encodings from several photos into one vector."""
        if not encodings:
            raise ValueError("No encodings to average")
        return np.mean(encodings, axis=0)

    # ── KDTree (matching index) ────────────────────────────────────────

    def build_index(self, student_encodings: list):
        """
        Build the KDTree from (student_id, encoding) pairs loaded from DB.
        Call this once at startup and after any new registration.
        """
        if not student_encodings:
            self._kdtree = None
            self._student_ids = []
            return

        self._student_ids = [sid for sid, _ in student_encodings]
        vectors = np.array([enc for _, enc in student_encodings], dtype=np.float32)
        self._kdtree = KDTree(vectors)

    def identify_face(self, encoding: np.ndarray) -> tuple:
        """
        Query KDTree with one face encoding.
        Returns (student_id, confidence) or (None, 0.0) if no match.
        confidence = 1 - distance  →  higher is better
        """
        if self._kdtree is None:
            return None, 0.0

        distance, idx = self._kdtree.query(encoding)
        if distance < self.threshold:
            confidence = round(1.0 - distance, 4)
            return self._student_ids[idx], confidence
        return None, 0.0

    # ── Classroom Analysis ─────────────────────────────────────────────

    def analyse_classroom(
        self,
        image_bgr: np.ndarray,
        all_students: list
    ) -> dict:
        """
        Full pipeline for a classroom photo.
        """
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        preprocessed = self._preprocess(rgb)
        locations = self._mediapipe_locations(preprocessed)

        if not locations:
            annotated = image_bgr.copy()
            return {"present": [], "unknown": [], "annotated_img": annotated}

        encodings = [self._extract_face_encoding(preprocessed, loc) for loc in locations]

        present = []
        unknown = []
        seen_ids = set()

        annotated = image_bgr.copy()

        for (top, right, bottom, left), encoding in zip(locations, encodings):
            student_id, confidence = self.identify_face(encoding)
            bbox = (left, top, right - left, bottom - top)

            if student_id and student_id not in seen_ids:
                seen_ids.add(student_id)
                present.append({"student_id": student_id, "confidence": confidence, "bbox": bbox})
                # Draw green box
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 200, 0), 2)
                label = f"ID:{student_id} ({confidence:.0%})"
                cv2.putText(annotated, label, (left, top - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 1)
            else:
                unknown.append({"bbox": bbox})
                # Draw red box
                cv2.rectangle(annotated, (left, top), (right, bottom), (0, 0, 220), 2)
                cv2.putText(annotated, "Unknown", (left, top - 8),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 220), 1)

        return {"present": present, "unknown": unknown, "annotated_img": annotated}

    # ── Serialisation (for DB storage) ────────────────────────────────

    @staticmethod
    def serialise(encoding: np.ndarray) -> bytes:
        return pickle.dumps(encoding.astype(np.float32))

    @staticmethod
    def deserialise(blob: bytes) -> np.ndarray:
        return pickle.loads(blob)

    # ── Internal Helpers ───────────────────────────────────────────────

    def _preprocess(self, rgb: np.ndarray) -> np.ndarray:
        """
        Resize large images and apply CLAHE for contrast normalisation.
        """
        h, w = rgb.shape[:2]
        max_dim = 1280
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            rgb = cv2.resize(rgb, (int(w * scale), int(h * scale)))

        # CLAHE on L channel of LAB
        lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    def _mediapipe_locations(self, rgb: np.ndarray) -> list:
        """
        Run YuNet face detection (or Haar Cascade fallback) and return locations in (top, right, bottom, left) format.
        """
        if not hasattr(self, '_use_yunet'):
            self._use_yunet = False
        
        if self._use_yunet:
            # YuNet detection
            h, w = rgb.shape[:2]
            self._detector.setInputSize((w, h))
            
            # Convert RGB to BGR for YuNet
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            _, faces = self._detector.detect(bgr)
            
            if faces is None or len(faces) == 0:
                return []
            
            # Convert YuNet format [x, y, w, h, conf, ...] to (top, right, bottom, left)
            locations = []
            for face in faces:
                x, y, fw, fh = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                top = max(0, y)
                left = max(0, x)
                bottom = min(h, y + fh)
                right = min(w, x + fw)
                locations.append((top, right, bottom, left))
            
            return locations
        else:
            # Haar Cascade fallback
            gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
            faces = self._detector.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(20, 20),
                maxSize=(500, 500)
            )
            
            if len(faces) == 0:
                return []
            
            locations = []
            for (x, y, w, h) in faces:
                top = y
                right = x + w
                bottom = y + h
                left = x
                locations.append((top, right, bottom, left))
            
            return locations
