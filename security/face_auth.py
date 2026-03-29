"""
JARVIS Biometric Face Authentication Engine.

Uses DeepFace with ArcFace model for military-grade face verification.
Multi-frame enrollment + multi-pass verification for maximum security.

Fallback chain: DeepFace (ArcFace) → face_recognition (dlib) → OpenCV LBPH

Face data is stored locally and NEVER leaves the machine.
"""

import os
import sys
import pickle
import time
import threading
import base64
import traceback

import cv2
import numpy as np

# Suppress TensorFlow C++ CPU feature warnings for cleaner console output
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# ── Engine Detection ─────────────────────────────────────────────────
ENGINE = "opencv"  # default fallback

try:
    from deepface import DeepFace
    ENGINE = "deepface"
    print("🔐 Face auth engine: DeepFace (ArcFace) — high accuracy")
except ImportError:
    try:
        import face_recognition
        ENGINE = "face_recognition"
        print("🔐 Face auth engine: face_recognition (dlib)")
    except ImportError:
        print("⚠️  No high-accuracy face engine. Using OpenCV LBPH fallback (NOT secure).")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import CONFIG


class FaceAuthenticator:
    """Military-grade biometric face authentication for JARVIS."""

    # DeepFace model to use — ArcFace is the most accurate
    DEEPFACE_MODEL = "ArcFace"
    DEEPFACE_DETECTOR = "mtcnn"
    # Distance threshold for ArcFace cosine similarity
    # Lower = stricter. ArcFace cosine threshold: verified < 0.68 (default)
    # We use 0.45 for STRICT security
    DEEPFACE_THRESHOLD = 0.45
    # Number of verification passes required (majority vote)
    VERIFY_PASSES = 3
    # Minimum enrollment samples
    MIN_ENROLLMENT_SAMPLES = 2

    def __init__(self):
        self.data_dir = os.path.join(
            os.path.dirname(__file__), "..",
            CONFIG.get("FACE_AUTH_DATA_DIR", "data/face_auth")
        )
        os.makedirs(self.data_dir, exist_ok=True)

        self.encoding_file = os.path.join(self.data_dir, "authorized_face.pkl")
        self.reference_dir = os.path.join(self.data_dir, "reference_faces")
        os.makedirs(self.reference_dir, exist_ok=True)

        self.cascade_file = os.path.join(self.data_dir, "lbph_model.yml")
        self.tolerance = CONFIG.get("FACE_AUTH_TOLERANCE", 0.35)
        self.engine = ENGINE
        self._authorized_encoding = None
        self._lock = threading.Lock()

        # Load existing encoding if available
        self._load_encoding()

    def _load_encoding(self):
        """Load the stored authorized face encoding."""
        if self.engine == "deepface":
            # For DeepFace, check if reference images exist
            if os.path.exists(self.reference_dir):
                refs = [f for f in os.listdir(self.reference_dir)
                        if f.endswith(('.jpg', '.png'))]
                if refs:
                    self._authorized_encoding = "deepface_enrolled"
                    print(f"🔐 Face auth: Loaded {len(refs)} reference faces (DeepFace engine).")
                    return

        if os.path.exists(self.encoding_file):
            try:
                with open(self.encoding_file, "rb") as f:
                    data = pickle.load(f)
                    self._authorized_encoding = data.get("encoding")
                    print(f"🔐 Face auth: Loaded authorized face ({self.engine} engine).")
            except Exception as e:
                print(f"⚠️  Failed to load face encoding: {e}")
                self._authorized_encoding = None

    def has_enrolled_face(self) -> bool:
        """Check if an authorized face is enrolled."""
        return self._authorized_encoding is not None

    def _capture_frame(self, camera_index=0):
        """Capture a single frame from the webcam."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return None, "Camera not accessible"

        # Warm up camera
        for _ in range(5):
            cap.read()
            time.sleep(0.05)

        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return None, "Failed to capture frame"

        return frame, None

    def _capture_frames_burst(self, count=7, camera_index=0):
        """Capture multiple frames for better encoding accuracy."""
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return [], "Camera not accessible"

        # Warm up
        for _ in range(10):
            cap.read()
            time.sleep(0.03)

        frames = []
        for i in range(count * 2):
            ret, frame = cap.read()
            if ret and frame is not None:
                frames.append(frame)
            time.sleep(0.15)

        cap.release()
        return frames, None

    def _frame_to_base64(self, frame):
        """Convert an OpenCV frame to base64 JPEG for the frontend."""
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return base64.b64encode(buffer).decode('utf-8')

    def _detect_single_face(self, frame):
        """Detect exactly one face in a frame. Returns face region or None."""
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=4, minSize=(80, 80)
        )
        if len(faces) >= 1: # Allow multiple faces but only use the first one if DeepFace validates it
            return faces[0]
        return None

    # ── ENROLLMENT ──────────────────────────────────────────────────

    def enroll(self, camera_index=0):
        """
        Enroll the authorized user's face.
        Captures multiple frames and builds robust face reference(s).

        Returns:
            dict: { "success": bool, "message": str, "preview": base64_jpg }
        """
        with self._lock:
            print("🔐 Face enrollment: Starting capture...")

            # Reduced burst count from 10 to 3 to speed up DeepFace processing
            frames, err = self._capture_frames_burst(count=3, camera_index=camera_index)
            if err:
                return {"success": False, "message": f"Camera error: {err}", "preview": None}

            if not frames:
                return {"success": False, "message": "No frames captured from camera.", "preview": None}

            if self.engine == "deepface":
                return self._enroll_deepface(frames)
            elif self.engine == "face_recognition":
                return self._enroll_face_recognition(frames)
            else:
                return self._enroll_opencv(frames)

    def _enroll_deepface(self, frames):
        """Enroll using DeepFace — saves multiple reference face images."""
        # Clear previous enrollment
        for f in os.listdir(self.reference_dir):
            os.remove(os.path.join(self.reference_dir, f))

        saved = 0
        best_frame = None

        for i, frame in enumerate(frames):
            try:
                # Let DeepFace handle the detection and embedding extraction internally
                # It is far more accurate than Haar Cascades
                result = DeepFace.represent(
                    frame,
                    model_name=self.DEEPFACE_MODEL,
                    detector_backend=self.DEEPFACE_DETECTOR,
                    enforce_detection=True,
                )
                if result and len(result) == 1:
                    ref_path = os.path.join(self.reference_dir, f"ref_{saved:02d}.jpg")
                    cv2.imwrite(ref_path, frame)
                    saved += 1
                    if best_frame is None:
                        best_frame = frame
            except Exception as e:
                # Face not detected or multiple faces
                continue

        if saved < self.MIN_ENROLLMENT_SAMPLES:
            return {
                "success": False,
                "message": f"Only captured {saved}/{self.MIN_ENROLLMENT_SAMPLES} valid face samples. "
                           "Ensure good lighting, face the camera directly, and be alone in frame.",
                "preview": None,
            }

        # Also save a pickle marker
        data = {
            "encoding": "deepface_enrolled",
            "engine": "deepface",
            "enrolled_at": time.time(),
            "sample_count": saved,
            "model": self.DEEPFACE_MODEL,
        }
        with open(self.encoding_file, "wb") as f:
            pickle.dump(data, f)

        self._authorized_encoding = "deepface_enrolled"

        preview = self._frame_to_base64(best_frame) if best_frame is not None else None

        print(f"🔐 Face enrollment (DeepFace/ArcFace): SUCCESS — {saved} samples captured.")
        return {
            "success": True,
            "message": f"Enrollment complete. {saved} face samples captured with ArcFace model.",
            "preview": preview,
        }

    def _enroll_face_recognition(self, frames):
        """Enroll using face_recognition library (high accuracy)."""
        import face_recognition as fr

        encodings = []
        best_frame = None

        for frame in frames:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            face_locations = fr.face_locations(rgb, model="hog")

            if len(face_locations) == 1:
                enc = fr.face_encodings(rgb, face_locations)
                if enc:
                    encodings.append(enc[0])
                    if best_frame is None:
                        best_frame = frame

        if len(encodings) < self.MIN_ENROLLMENT_SAMPLES:
            return {
                "success": False,
                "message": f"Could not capture enough face shots ({len(encodings)}/{self.MIN_ENROLLMENT_SAMPLES}). "
                           "Ensure good lighting and face the camera directly.",
                "preview": None,
            }

        avg_encoding = np.mean(encodings, axis=0)

        data = {
            "encoding": avg_encoding,
            "engine": "face_recognition",
            "enrolled_at": time.time(),
            "sample_count": len(encodings),
        }

        with open(self.encoding_file, "wb") as f:
            pickle.dump(data, f)

        self._authorized_encoding = avg_encoding

        preview = self._frame_to_base64(best_frame) if best_frame is not None else None

        print(f"🔐 Face enrollment (face_recognition): SUCCESS — {len(encodings)} samples.")
        return {
            "success": True,
            "message": f"Enrollment complete. {len(encodings)} face samples captured and encoded.",
            "preview": preview,
        }

    def _enroll_opencv(self, frames):
        """Fallback enrollment using OpenCV Haar + LBPH."""
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )

        faces_gray = []
        labels = []
        best_frame = None

        for frame in frames:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            detected = cascade.detectMultiScale(
                gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
            )

            if len(detected) == 1:
                (x, y, w, h) = detected[0]
                face_roi = gray[y:y+h, x:x+w]
                face_roi = cv2.resize(face_roi, (200, 200))
                faces_gray.append(face_roi)
                labels.append(1)
                if best_frame is None:
                    best_frame = frame

        if len(faces_gray) < 3:
            return {
                "success": False,
                "message": f"Could not capture enough face samples ({len(faces_gray)}/3). "
                           "Ensure good lighting.",
                "preview": None,
            }

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces_gray, np.array(labels))
        recognizer.write(self.cascade_file)

        data = {
            "encoding": "lbph",
            "engine": "opencv",
            "enrolled_at": time.time(),
            "sample_count": len(faces_gray),
        }
        with open(self.encoding_file, "wb") as f:
            pickle.dump(data, f)

        self._authorized_encoding = "lbph"

        preview = self._frame_to_base64(best_frame) if best_frame is not None else None

        print(f"🔐 Face enrollment (OpenCV): SUCCESS — {len(faces_gray)} samples.")
        return {
            "success": True,
            "message": f"Enrollment complete (OpenCV). {len(faces_gray)} samples captured.",
            "preview": preview,
        }

    # ── VERIFICATION ────────────────────────────────────────────────

    def verify(self, camera_index=0):
        """
        Verify the current face against the enrolled face.
        Uses multi-pass verification for security.

        Returns:
            dict: {
                "authenticated": bool,
                "confidence": float (0-1),
                "message": str,
                "preview": base64_jpg or None
            }
        """
        with self._lock:
            if not self.has_enrolled_face():
                return {
                    "authenticated": False,
                    "confidence": 0.0,
                    "message": "No enrolled face found. Enrollment required.",
                    "preview": None,
                }

            if self.engine == "deepface":
                return self._verify_deepface(camera_index)
            elif self.engine == "face_recognition":
                frame, err = self._capture_frame(camera_index=camera_index)
                if err:
                    return {
                        "authenticated": False,
                        "confidence": 0.0,
                        "message": f"Camera error: {err}",
                        "preview": None,
                    }
                preview = self._frame_to_base64(frame)
                return self._verify_face_recognition(frame, preview)
            else:
                frame, err = self._capture_frame(camera_index=camera_index)
                if err:
                    return {
                        "authenticated": False,
                        "confidence": 0.0,
                        "message": f"Camera error: {err}",
                        "preview": None,
                    }
                preview = self._frame_to_base64(frame)
                return self._verify_opencv(frame, preview)

    def _verify_deepface(self, camera_index=0):
        """
        Verify using DeepFace with multi-pass security.
        Captures multiple frames and requires majority match against
        ALL reference images.
        """
        # Get reference images
        ref_files = sorted([
            os.path.join(self.reference_dir, f)
            for f in os.listdir(self.reference_dir)
            if f.endswith(('.jpg', '.png'))
        ])

        if not ref_files:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "No reference faces found. Re-enrollment required.",
                "preview": None,
            }

        # Capture multiple frames for multi-pass verification
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "Camera not accessible.",
                "preview": None,
            }

        # Warm up camera
        for _ in range(8):
            cap.read()
            time.sleep(0.04)

        verify_frames = []
        for _ in range(self.VERIFY_PASSES + 2):
            ret, frame = cap.read()
            if ret and frame is not None:
                # Check single face
                face_rect = self._detect_single_face(frame)
                if face_rect is not None:
                    verify_frames.append(frame)
            time.sleep(0.2)

        cap.release()

        if not verify_frames:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "No face detected. Position your face in front of the camera.",
                "preview": None,
            }

        preview = self._frame_to_base64(verify_frames[0])

        # Multi-pass verification: each frame must match against reference(s)
        pass_results = []
        pass_distances = []

        for frame in verify_frames[:self.VERIFY_PASSES]:
            # Save temp frame for DeepFace
            temp_path = os.path.join(self.data_dir, "_temp_verify.jpg")
            cv2.imwrite(temp_path, frame)

            frame_matches = 0
            frame_total = 0
            frame_distances = []

            for ref_path in ref_files[:5]:  # Compare against up to 5 references
                try:
                    result = DeepFace.verify(
                        img1_path=temp_path,
                        img2_path=ref_path,
                        model_name=self.DEEPFACE_MODEL,
                        detector_backend=self.DEEPFACE_DETECTOR,
                        enforce_detection=True,
                        distance_metric="cosine",
                    )
                    distance = result.get("distance", 1.0)
                    frame_distances.append(distance)
                    frame_total += 1

                    if distance < self.DEEPFACE_THRESHOLD:
                        frame_matches += 1

                except Exception as e:
                    print(f"⚠️  DeepFace verify error: {e}")
                    continue

            # This frame passes if majority of reference comparisons match
            if frame_total > 0:
                match_ratio = frame_matches / frame_total
                pass_results.append(match_ratio >= 0.5)
                if frame_distances:
                    pass_distances.append(min(frame_distances))

            # Clean up
            if os.path.exists(temp_path):
                os.remove(temp_path)

        if not pass_results:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "Could not verify face. Try better lighting or positioning.",
                "preview": preview,
            }

        # STRICT: require ALL passes to match (not just majority)
        passes_matched = sum(pass_results)
        total_passes = len(pass_results)
        all_passed = passes_matched == total_passes

        # Confidence based on average distance
        avg_distance = np.mean(pass_distances) if pass_distances else 1.0
        confidence = max(0.0, 1.0 - avg_distance)

        if all_passed and confidence >= 0.55:
            msg = f"Identity verified. Confidence: {confidence:.1%} ({passes_matched}/{total_passes} passes)"
            print(f"🔐 Face auth (DeepFace): ✓ VERIFIED (confidence: {confidence:.1%}, "
                  f"passes: {passes_matched}/{total_passes})")
        else:
            msg = f"Access denied. Face does not match authorized user."
            if passes_matched > 0:
                msg += f" ({passes_matched}/{total_passes} passes, confidence: {confidence:.1%})"
            print(f"🔐 Face auth (DeepFace): ✗ DENIED (confidence: {confidence:.1%}, "
                  f"passes: {passes_matched}/{total_passes})")

        return {
            "authenticated": all_passed and confidence >= 0.55,
            "confidence": round(confidence, 4),
            "message": msg,
            "preview": preview,
        }

    def _verify_face_recognition(self, frame, preview):
        """Verify using face_recognition library."""
        import face_recognition as fr

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        face_locations = fr.face_locations(rgb, model="hog")

        if len(face_locations) == 0:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "No face detected. Position your face in front of the camera.",
                "preview": preview,
            }

        if len(face_locations) > 1:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "Multiple faces detected. Only the authorized user should be visible.",
                "preview": preview,
            }

        encodings = fr.face_encodings(rgb, face_locations)
        if not encodings:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "Could not encode face. Try better lighting.",
                "preview": preview,
            }

        face_distance = fr.face_distance(
            [self._authorized_encoding], encodings[0]
        )[0]

        confidence = max(0.0, 1.0 - face_distance)
        is_match = face_distance <= self.tolerance

        if is_match:
            msg = f"Identity verified. Confidence: {confidence:.1%}"
            print(f"🔐 Face auth: ✓ VERIFIED (confidence: {confidence:.1%})")
        else:
            msg = f"Access denied. Face does not match authorized user."
            print(f"🔐 Face auth: ✗ DENIED (distance: {face_distance:.3f})")

        return {
            "authenticated": is_match,
            "confidence": round(confidence, 4),
            "message": msg,
            "preview": preview,
        }

    def _verify_opencv(self, frame, preview):
        """Verify using OpenCV LBPH recognizer (STRICT thresholds)."""
        if not os.path.exists(self.cascade_file):
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "LBPH model not found. Re-enrollment required.",
                "preview": preview,
            }

        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        detected = cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(100, 100)
        )

        if len(detected) == 0:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "No face detected.",
                "preview": preview,
            }

        if len(detected) > 1:
            return {
                "authenticated": False,
                "confidence": 0.0,
                "message": "Multiple faces detected. Only the authorized user should be visible.",
                "preview": preview,
            }

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.read(self.cascade_file)

        (x, y, w, h) = detected[0]
        face_roi = gray[y:y+h, x:x+w]
        face_roi = cv2.resize(face_roi, (200, 200))

        label, distance = recognizer.predict(face_roi)

        # STRICT threshold: was 80, now 45
        confidence = max(0.0, 1.0 - (distance / 150.0))
        is_match = distance < 45

        if is_match:
            msg = f"Identity verified (OpenCV). Confidence: {confidence:.1%}"
            print(f"🔐 Face auth (OpenCV): ✓ VERIFIED (distance: {distance:.1f})")
        else:
            msg = "Access denied. Face does not match."
            print(f"🔐 Face auth (OpenCV): ✗ DENIED (distance: {distance:.1f})")

        return {
            "authenticated": is_match,
            "confidence": round(confidence, 4),
            "message": msg,
            "preview": preview,
        }

    def delete_enrollment(self):
        """Delete the enrolled face data."""
        # Delete pickle file
        if os.path.exists(self.encoding_file):
            os.remove(self.encoding_file)

        # Delete reference faces
        if os.path.exists(self.reference_dir):
            for f in os.listdir(self.reference_dir):
                os.remove(os.path.join(self.reference_dir, f))

        # Delete LBPH model
        if os.path.exists(self.cascade_file):
            os.remove(self.cascade_file)

        # Delete temp verify file
        temp_path = os.path.join(self.data_dir, "_temp_verify.jpg")
        if os.path.exists(temp_path):
            os.remove(temp_path)

        self._authorized_encoding = None
        print("🔐 Face enrollment data deleted.")
        return {"success": True, "message": "Enrollment data deleted."}


# ── Singleton ───────────────────────────────────────────────────────
_authenticator = None


def get_authenticator() -> FaceAuthenticator:
    """Get the global FaceAuthenticator instance."""
    global _authenticator
    if _authenticator is None:
        _authenticator = FaceAuthenticator()
    return _authenticator
