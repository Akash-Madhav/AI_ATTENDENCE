# engine/face_engine.py

import cv2
import numpy as np
import pickle
import os
from scipy.spatial import KDTree
from config import CONFIG


class FaceEngine:
    VERSION = "3.0-SFace"
    """
    High-accuracy Face Pipeline (Industry Standard):
      Stage 1 — YuNet (CNN): Face detection + 5 landmarks
      Stage 2 — SFace (CNN): Face alignment + 128-dim feature extraction
      Stage 3 — KDTree: Vector matching via Cosine Similarity (normalized Euclidean)

    Note: This pipeline is highly robust to blur, lighting, and angles.
    """

    def __init__(self):
        print(f"[INFO] FaceEngine Version: {self.VERSION}", flush=True)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        models_dir = os.path.join(os.path.dirname(current_dir), "assets", "models")
        
        # 1. Initialize YuNet (Detector)
        yunet_path = os.path.join(models_dir, "face_detection_yunet_2023mar.onnx")
        self._yunet = None
        if os.path.exists(yunet_path):
            try:
                self._yunet = cv2.FaceDetectorYN.create(
                    model=yunet_path, config="", input_size=(320, 320),
                    score_threshold=0.6, nms_threshold=0.3, top_k=5000
                )
                print("[SUCCESS] YuNet Detector loaded.", flush=True)
            except Exception as e:
                print(f"[ERROR] YuNet Init Failed: {e}", flush=True)

        # 2. Initialize SFace (Recognizer)
        sface_path = os.path.join(models_dir, "face_recognition_sface_2021dec.onnx")
        self._sface = None
        if os.path.exists(sface_path):
            try:
                self._sface = cv2.FaceRecognizerSF.create(model=sface_path, config="")
                print("[SUCCESS] SFace Recognizer loaded.", flush=True)
            except Exception as e:
                print(f"[ERROR] SFace Init Failed: {e}", flush=True)

        self._kdtree = None
        self._student_ids = []
        # Threshold for SFace: Distance < 0.8 is a strong match.
        # Confidence is calculated as (1.0 - distance).
        self.threshold = float(CONFIG.get("MATCH_THRESHOLD", 0.8))

    # ── Encoding ──────────────────────────────────────────────────────

    def _extract_face_encoding(self, rgb: np.ndarray, face_info: np.ndarray) -> np.ndarray:
        """
        Use SFace to align and extract a 128-dim feature vector.
        face_info: The detection result for a single face (including landmarks).
        """
        if not self._sface or face_info is None:
            return np.zeros(128, dtype=np.float32)

        try:
            # 1. Align and crop face using landmarks
            aligned_face = self._sface.alignCrop(rgb, face_info)
            
            # 2. Extract feature vector
            feature = self._sface.feature(aligned_face)
            
            # 3. Normalize to unit length (makes Euclidean distance equivalent to Cosine)
            cv2.normalize(feature, feature)
            
            return feature.flatten()
        except Exception as e:
            print(f"[ERROR] Encoding failed: {e}")
            return np.zeros(128, dtype=np.float32)

    def encode_image(self, image_bgr: np.ndarray) -> list:
        """Extract encodings from a BGR image."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        
        # Detect faces with landmarks
        results = self._detect_faces_raw(rgb)
        if results is None:
            return []

        encodings = []
        for face in results:
            enc = self._extract_face_encoding(rgb, face)
            encodings.append(enc)
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

    def analyse_classroom(self, image_bgr: np.ndarray, all_students: list) -> dict:
        """Full pipeline for a classroom photo using SFace."""
        rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
        
        # Detect faces with landmarks
        raw_faces = self._detect_faces_raw(rgb)
        if raw_faces is None:
            return {"present": [], "unknown": [], "annotated_img": image_bgr.copy()}

        present = []
        unknown = []
        seen_ids = set()
        annotated = image_bgr.copy()

        for face in raw_faces:
            # 1. Get BBox
            x, y, w, h = face[:4].astype(int)
            
            # 2. Encode
            encoding = self._extract_face_encoding(rgb, face)
            
            # 3. Match
            student_id, confidence = self.identify_face(encoding)
            bbox = (x, y, w, h)

            if student_id and student_id not in seen_ids:
                seen_ids.add(student_id)
                present.append({"student_id": student_id, "confidence": confidence, "bbox": bbox})
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 200, 0), 2)
                cv2.putText(annotated, f"ID:{student_id}", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)
            else:
                unknown.append({"bbox": bbox})
                cv2.rectangle(annotated, (x, y), (x+w, y+h), (0, 0, 220), 2)
                cv2.putText(annotated, "Unknown", (x, y - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 220), 2)

        return {"present": present, "unknown": unknown, "annotated_img": annotated}

    # ── Serialisation (for DB storage) ────────────────────────────────

    @staticmethod
    def serialise(encoding: np.ndarray) -> bytes:
        return pickle.dumps(encoding.astype(np.float32))

    @staticmethod
    def deserialise(blob: bytes) -> np.ndarray:
        return pickle.loads(blob)

    # ── Internal Helpers ───────────────────────────────────────────────

    def _detect_faces_raw(self, rgb: np.ndarray) -> np.ndarray:
        """
        Detect faces and return raw results (including landmarks for alignment).
        """
        if not self._yunet:
            return None
        
        try:
            h, w = rgb.shape[:2]
            self._yunet.setInputSize((w, h))
            _, faces = self._yunet.detect(rgb)
            return faces
        except Exception as e:
            print(f"[ERROR] YuNet Raw Detection Failed: {e}", flush=True)
            return None

    def _detect_faces(self, rgb: np.ndarray) -> list:
        """
        Legacy/Simplified face detection. Returns (top, right, bottom, left).
        Now uses YuNet primary with raw data extraction.
        """
        raw = self._detect_faces_raw(rgb)
        if raw is None:
            return []
            
        locations = []
        for face in raw:
            x, y, w, h = face[:4].astype(int)
            locations.append((y, x+w, y+h, x))
        return locations

