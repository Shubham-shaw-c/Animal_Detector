"""
model_manager.py
Thread-safe loader and inference engine for the MobileNetV2 animal detection model.
Handles image preprocessing, prediction, top-3 confidence ranking, and hot-reloading.
"""

import json
import os
import threading
import numpy as np
from PIL import Image
import tensorflow as tf

from animal_knowledge import get_animal_facts

MODEL_PATHS = [
    "models/best_animal_model.keras",
    "models/animal_detector_model.keras"
]
CLASS_LABELS_PATH = "class_labels.json"
TARGET_SIZE = (224, 224)


class AnimalModelManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.model = None
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
        """Loads or reloads the trained Keras model and class indices."""
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

            # 2. Find and load model
            loaded = False
            for p in MODEL_PATHS:
                if os.path.exists(p):
                    try:
                        print(f"[ModelManager] Loading model from: {p}")
                        self.model = tf.keras.models.load_model(p)
                        self.model_path_used = p
                        loaded = True
                        print(f"[ModelManager] Model loaded successfully from {p} with {len(self.index_to_label)} classes.")
                        break
                    except Exception as e:
                        print(f"[ModelManager] Failed loading model {p}: {e}")

            if not loaded:
                print("[ModelManager] Warning: No valid model file could be loaded.")

    def reload(self):
        """Hot-reload model and labels after retraining."""
        print("[ModelManager] Reloading model and class labels...")
        self.load_model()

    def get_supported_classes(self):
        """Returns sorted list of supported animal names and metadata."""
        classes = sorted(list(self.class_indices.keys()))
        return {
            "total_classes": len(classes),
            "classes": [c.capitalize() for c in classes],
            "raw_classes": classes,
            "model_path": self.model_path_used,
            "is_loaded": self.model is not None
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
        img_array = np.array(resized, dtype=np.float32)
        img_array = img_array / 255.0
        img_array = np.expand_dims(img_array, axis=0)
        return img_array

    def predict(self, pil_image: Image.Image) -> dict:
        """
        Runs model inference on the provided PIL image.
        Returns predicted animal, confidence, top 3 predictions, and 10 scientific facts.
        """
        if self.model is None:
            raise RuntimeError("Model is not loaded. Please train or provide a model file.")

        img_array = self.preprocess_image(pil_image)

        with self.inference_lock:
            raw_predictions = self.model.predict(img_array, verbose=0)[0]

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

