# engine/face_engine.py

import cv2
import numpy as np
import pickle
import os
from scipy.spatial import KDTree
from config import CONFIG


class FaceEngine:
    VERSION = "3.1-SFace"
    """
    High-accuracy Face Pipeline:
      Stage 1 — YuNet (CNN): Face detection + 5 landmarks (BGR input)
      Stage 2 — SFace (CNN): Face alignment + 128-dim L2-normalized feature extraction
      Stage 3 — KDTree: Vector matching via Euclidean distance on unit vectors
                (equivalent to Cosine Similarity: cos_sim = 1 - d^2 / 2)
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
        # For unit-normalized SFace vectors, OpenCV's cosine threshold 0.363
        # corresponds to Euclidean distance ~1.128 (d = sqrt(2 * (1 - cos_sim))).
        self.threshold = float(CONFIG.get("MATCH_THRESHOLD", 1.1))

    @staticmethod
    def _l2_normalize(vec: np.ndarray) -> np.ndarray | None:
        """Return unit-length float32 vector, or None if zero/invalid."""
        if vec is None:
            return None
        arr = np.asarray(vec, dtype=np.float32).flatten()
        norm = float(np.linalg.norm(arr))
        if not np.isfinite(norm) or norm <= 1e-12:
            return None
        return arr / norm

    # ── Encoding ──────────────────────────────────────────────────────

    def _extract_face_encoding(self, image_bgr: np.ndarray, face_info: np.ndarray) -> np.ndarray | None:
        """
        Use SFace to align and extract a unit-normalized 128-dim feature vector.
        OpenCV YuNet/SFace expect BGR images.
        """
        if not self._sface or face_info is None:
            return None

        try:
            aligned_face = self._sface.alignCrop(image_bgr, face_info)
            feature = self._sface.feature(aligned_face)
            return self._l2_normalize(feature)
        except Exception as e:
            print(f"[ERROR] Encoding failed: {e}", flush=True)
            return None

    def encode_image(self, image_bgr: np.ndarray) -> list:
        """Extract unit-normalized encodings from a BGR image."""
        results = self._detect_faces_raw(image_bgr)
        if results is None:
            return []

        encodings = []
        for face in results:
            enc = self._extract_face_encoding(image_bgr, face)
            if enc is not None:
                encodings.append(enc)
        return encodings

    def encode_from_path(self, image_path: str) -> list:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Cannot read image: {image_path}")
        return self.encode_image(img)

    def average_encodings(self, encodings: list) -> np.ndarray:
        """Average multiple encodings into one unit-normalized representative vector."""
        valid = [self._l2_normalize(enc) for enc in encodings]
        valid = [enc for enc in valid if enc is not None]
        if not valid:
            raise ValueError("No valid encodings to average")
        mean_vec = np.mean(valid, axis=0)
        normalized = self._l2_normalize(mean_vec)
        if normalized is None:
            raise ValueError("Averaged encoding collapsed to zero vector")
        return normalized

    # ── KDTree (matching index) ────────────────────────────────────────

    def build_index(self, student_encodings: list):
        """
        Build the KDTree from (student_id, encoding) pairs loaded from DB.
        Call this once at startup and after any new registration/deletion.
        """
        valid_ids = []
        valid_vectors = []
        for sid, enc in student_encodings:
            norm_enc = self._l2_normalize(enc)
            if norm_enc is not None:
                valid_ids.append(sid)
                valid_vectors.append(norm_enc)

        if not valid_vectors:
            self._kdtree = None
            self._student_ids = []
            return

        self._student_ids = valid_ids
        self._kdtree = KDTree(np.array(valid_vectors, dtype=np.float32))

    def identify_face(self, encoding: np.ndarray) -> tuple:
        """
        Query KDTree with one unit-normalized face encoding.
        Returns (student_id, confidence) or (None, 0.0) if no match.
        confidence = cosine similarity in [0, 1].
        """
        if self._kdtree is None:
            return None, 0.0

        norm_enc = self._l2_normalize(encoding)
        if norm_enc is None:
            return None, 0.0

        distance, idx = self._kdtree.query(norm_enc)
        cos_sim = 1.0 - (float(distance) ** 2 / 2.0)
        print(
            f"[DEBUG] Matching result: Distance={distance:.4f}, "
            f"CosSim={cos_sim:.4f} (Threshold={self.threshold})",
            flush=True,
        )

        if distance < self.threshold:
            confidence = round(max(0.0, min(1.0, cos_sim)), 4)
            return self._student_ids[idx], confidence
        return None, 0.0

    # ── Classroom Analysis ─────────────────────────────────────────────

    def analyse_classroom(self, image_bgr: np.ndarray, all_students: list) -> dict:
        """Full pipeline for a classroom photo using YuNet + SFace."""
        raw_faces = self._detect_faces_raw(image_bgr)
        if raw_faces is None:
            return {"present": [], "unknown": [], "annotated_img": image_bgr.copy()}

        student_names = {s["id"]: s.get("name", f"ID:{s['id']}") for s in (all_students or [])}
        best_matches: dict[int, dict] = {}
        unknown = []

        for face in raw_faces:
            x, y, w, h = face[:4].astype(int)
            bbox = (int(x), int(y), int(w), int(h))

            encoding = self._extract_face_encoding(image_bgr, face)
            student_id, confidence = self.identify_face(encoding)

            if student_id is not None:
                prev = best_matches.get(student_id)
                if prev is None or confidence > prev["confidence"]:
                    if prev is not None:
                        unknown.append({"bbox": prev["bbox"]})
                    best_matches[student_id] = {
                        "student_id": student_id,
                        "confidence": confidence,
                        "bbox": bbox,
                    }
                else:
                    unknown.append({"bbox": bbox})
            else:
                unknown.append({"bbox": bbox})

        present = list(best_matches.values())
        annotated = image_bgr.copy()

        for match in present:
            x, y, w, h = match["bbox"]
            sid = match["student_id"]
            label = f"{student_names.get(sid, f'ID:{sid}')} ({match['confidence']*100:.0f}%)"
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 200, 0), 2)
            cv2.putText(annotated, label, (x, max(20, y - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 200, 0), 2)

        for unk in unknown:
            x, y, w, h = unk["bbox"]
            cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 0, 220), 2)
            cv2.putText(annotated, "Unknown", (x, max(20, y - 10)),
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

    def _detect_faces_raw(self, image_bgr: np.ndarray) -> np.ndarray | None:
        """Detect faces in a BGR image and return raw results (including 5 landmarks)."""
        if not self._yunet or image_bgr is None:
            return None

        try:
            h, w = image_bgr.shape[:2]
            self._yunet.setInputSize((w, h))
            _, faces = self._yunet.detect(image_bgr)
            return faces
        except Exception as e:
            print(f"[ERROR] YuNet Raw Detection Failed: {e}", flush=True)
            return None

    def _detect_faces(self, image_bgr: np.ndarray) -> list:
        """Return bounding boxes as (top, right, bottom, left) from a BGR image."""
        raw = self._detect_faces_raw(image_bgr)
        if raw is None:
            return []

        locations = []
        for face in raw:
            x, y, w, h = face[:4].astype(int)
            locations.append((y, x + w, y + h, x))
        return locations


_shared_engine: FaceEngine | None = None


def get_face_engine() -> FaceEngine:
    """Return the shared FaceEngine singleton so all services share one KDTree index."""
    global _shared_engine
    if _shared_engine is None:
        _shared_engine = FaceEngine()
    return _shared_engine
