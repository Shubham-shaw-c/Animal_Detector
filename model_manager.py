"""
model_manager.py
Thread-safe loader and inference engine for the Animal Detection model.
Supports high-performance lightweight LiteRT / TFLite runtime (optimal for Vercel serverless)
with seamless fallback to full TensorFlow Keras if running in offline training mode.
"""

import json
import os
import threading
import numpy as np
from PIL import Image

from animal_knowledge import get_animal_facts

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TFLITE_PATH = os.path.join(BASE_DIR, "models", "best_animal_model.tflite")
KERAS_PATHS = [
    os.path.join(BASE_DIR, "models", "best_animal_model.keras"),
    os.path.join(BASE_DIR, "models", "animal_detector_model.keras")
]
CLASS_LABELS_PATH = os.path.join(BASE_DIR, "class_labels.json")
TARGET_SIZE = (224, 224)

# Graceful multi-tier interpreter resolution
Interpreter = None
try:
    from ai_edge_litert.interpreter import Interpreter
except ImportError:
    try:
        from tflite_runtime.interpreter import Interpreter
    except ImportError:
        try:
            from tensorflow.lite.python.interpreter import Interpreter
        except ImportError:
            try:
                import tensorflow as tf
                Interpreter = tf.lite.Interpreter
            except ImportError:
                Interpreter = None


class AnimalModelManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.interpreter = None
        self.input_details = None
        self.output_details = None
        self.keras_model = None
        self.class_indices = {}
        self.index_to_label = {}
        self.model_path_used = None
        self.inference_lock = threading.Lock()
        self.load_model()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = AnimalModelManager()
            return cls._instance

    def load_model(self):
        """Loads model prioritizing lightweight TFLite/LiteRT for speed and low memory."""
        with self.inference_lock:
            # 1. Load class labels
            if os.path.exists(CLASS_LABELS_PATH):
                try:
                    with open(CLASS_LABELS_PATH, "r", encoding="utf-8") as f:
                        self.class_indices = json.load(f)
                    self.index_to_label = {int(idx): animal for animal, idx in self.class_indices.items()}
                except Exception as e:
                    print(f"[ModelManager] Error reading {CLASS_LABELS_PATH}: {e}")
            else:
                print(f"[ModelManager] Warning: {CLASS_LABELS_PATH} not found.")

            # 2. Try loading LiteRT / TFLite model first
            loaded = False
            if Interpreter is not None and os.path.exists(TFLITE_PATH):
                try:
                    self.interpreter = Interpreter(model_path=TFLITE_PATH)
                    self.interpreter.allocate_tensors()
                    self.input_details = self.interpreter.get_input_details()
                    self.output_details = self.interpreter.get_output_details()
                    self.model_path_used = TFLITE_PATH
                    loaded = True
                    print(f"[ModelManager] LiteRT/TFLite model loaded successfully ({len(self.index_to_label)} classes).")
                except Exception as e:
                    print(f"[ModelManager] TFLite initialization note: {e}")

            # 3. Fallback to Keras if TFLite not available or failed
            if not loaded:
                for p in KERAS_PATHS:
                    if os.path.exists(p):
                        try:
                            import tensorflow as tf
                            self.keras_model = tf.keras.models.load_model(p)
                            self.model_path_used = p
                            loaded = True
                            print(f"[ModelManager] Keras model loaded successfully from {p}.")
                            break
                        except Exception as e:
                            print(f"[ModelManager] Keras load attempt: {e}")

            if not loaded:
                print("[ModelManager] Warning: No model could be loaded.")

    def reload(self):
        """Hot-reload model and labels after retraining."""
        print("[ModelManager] Hot-reloading model and class labels...")
        self.load_model()

    def get_supported_classes(self):
        """Returns sorted list of supported animal names and metadata."""
        classes = sorted(list(self.class_indices.keys()))
        return {
            "total_classes": len(classes),
            "classes": [c.capitalize() for c in classes],
            "raw_classes": classes,
            "model_path": self.model_path_used,
            "is_loaded": (self.interpreter is not None) or (self.keras_model is not None)
        }

    def preprocess_image(self, pil_image: Image.Image) -> np.ndarray:
        """
        Preprocesses a PIL image to match the training pipeline:
        - Convert to RGB
        - Resize to (224, 224)
        - Rescale pixel values with 1.0 / 255.0
        - Add batch dimension -> (1, 224, 224, 3)
        """
        if pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")
        resized = pil_image.resize(TARGET_SIZE, Image.Resampling.BILINEAR)
        img_array = np.array(resized, dtype=np.float32) / 255.0
        return np.expand_dims(img_array, axis=0)

    def predict(self, pil_image: Image.Image) -> dict:
        """
        Runs model inference on the provided PIL image.
        Returns predicted animal, confidence, top 3 predictions, and 10 scientific facts.
        """
        if self.interpreter is None and self.keras_model is None:
            raise RuntimeError("Model is not loaded. Please train or provide a model file.")

        img_array = self.preprocess_image(pil_image)

        with self.inference_lock:
            if self.interpreter is not None:
                self.interpreter.set_tensor(self.input_details[0]["index"], img_array)
                self.interpreter.invoke()
                raw_predictions = self.interpreter.get_tensor(self.output_details[0]["index"])[0]
            else:
                raw_predictions = self.keras_model.predict(img_array, verbose=0)[0]

        top_indices = np.argsort(raw_predictions)[::-1]
        best_idx = int(top_indices[0])
        best_confidence = float(raw_predictions[best_idx]) * 100.0

        best_label = self.index_to_label.get(best_idx, f"Class {best_idx}")
        display_name = best_label.capitalize()

        # Top 3 predictions
        top_3 = []
        for idx in top_indices[:3]:
            i = int(idx)
            lbl = self.index_to_label.get(i, f"Class {i}").capitalize()
            conf = float(raw_predictions[i]) * 100.0
            top_3.append({
                "animal": lbl,
                "confidence": round(conf, 2),
                "index": i
            })

        # Fetch 10 curated scientific facts
        facts_data = get_animal_facts(best_label)

        return {
            "success": True,
            "detected_animal": display_name,
            "animal_key": best_label.lower(),
            "confidence": round(best_confidence, 2),
            "top_predictions": top_3,
            "facts": facts_data["facts"],
            "raw_data": facts_data["raw_data"]
        }


# Singleton accessor
model_manager = AnimalModelManager.get_instance()
