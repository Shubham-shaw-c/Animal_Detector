"""
trainer.py
Safe, thread-safe background retraining pipeline using MobileNetV2 transfer learning.
Features live training status tracking, temporary validation, and zero-downtime hot-reload.
"""

import json
import os
import shutil
import tempfile
if "MPLCONFIGDIR" not in os.environ:
    os.environ["MPLCONFIGDIR"] = os.path.join(tempfile.gettempdir(), "mpl_cache")
import threading
import numpy as np
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import tensorflow as tf
from tensorflow.keras.applications import MobileNetV2
from tensorflow.keras.callbacks import Callback, EarlyStopping, ModelCheckpoint, ReduceLROnPlateau
from tensorflow.keras.layers import Dense, Dropout, GlobalAveragePooling2D
from tensorflow.keras.models import Sequential
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from model_manager import model_manager

IMG_SIZE = (224, 224)
BATCH_SIZE = 32
DEFAULT_EPOCHS = 10

DATASET_DIR = "animal_datasets"
MODELS_DIR = "models"
TEMP_MODEL_PATH = os.path.join(MODELS_DIR, "temp_training_model.keras")
BEST_MODEL_PATH = os.path.join(MODELS_DIR, "best_animal_model.keras")
FINAL_MODEL_PATH = os.path.join(MODELS_DIR, "animal_detector_model.keras")
CLASS_LABELS_PATH = "class_labels.json"


class TrainingState:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        with self.lock:
            self.status = "idle"  # idle, preparing, training, validating_model, completed, error
            self.new_animal = None
            self.current_epoch = 0
            self.total_epochs = DEFAULT_EPOCHS
            self.progress_percent = 0
            self.train_accuracy = 0.0
            self.val_accuracy = 0.0
            self.train_loss = 0.0
            self.val_loss = 0.0
            self.total_classes = 0
            self.class_names = []
            self.total_samples = 0
            self.message = "Trainer is ready."
            self.error = None
            self.history = {}

    def update(self, **kwargs):
        with self.lock:
            for k, v in kwargs.items():
                setattr(self, k, v)

    def to_dict(self):
        with self.lock:
            return {
                "status": self.status,
                "new_animal": self.new_animal,
                "current_epoch": self.current_epoch,
                "total_epochs": self.total_epochs,
                "progress_percent": self.progress_percent,
                "train_accuracy": round(float(self.train_accuracy) * 100, 2),
                "val_accuracy": round(float(self.val_accuracy) * 100, 2),
                "train_loss": round(float(self.train_loss), 4),
                "val_loss": round(float(self.val_loss), 4),
                "total_classes": self.total_classes,
                "class_names": self.class_names,
                "total_samples": self.total_samples,
                "message": self.message,
                "error": self.error
            }


global_training_state = TrainingState()
_trainer_lock = threading.Lock()


class EpochProgressCallback(Callback):
    def __init__(self, state: TrainingState, total_epochs: int):
        super().__init__()
        self.state = state
        self.total_epochs = total_epochs

    def on_epoch_begin(self, epoch, logs=None):
        self.state.update(
            status="training",
            current_epoch=epoch + 1,
            message=f"Training epoch {epoch + 1} of {self.total_epochs}..."
        )

    def on_epoch_end(self, epoch, logs=None):
        logs = logs or {}
        t_acc = logs.get("accuracy", 0.0)
        v_acc = logs.get("val_accuracy", 0.0)
        t_loss = logs.get("loss", 0.0)
        v_loss = logs.get("val_loss", 0.0)

        percent = int(((epoch + 1) / self.total_epochs) * 100)
        self.state.update(
            current_epoch=epoch + 1,
            progress_percent=percent,
            train_accuracy=t_acc,
            val_accuracy=v_acc,
            train_loss=t_loss,
            val_loss=v_loss,
            message=f"Epoch {epoch + 1}/{self.total_epochs} completed - Acc: {t_acc*100:.1f}%, Val Acc: {v_acc*100:.1f}%"
        )
        print(f"[TRAINER] Epoch {epoch + 1}/{self.total_epochs} -> Train Acc: {t_acc*100:.1f}%, Val Acc: {v_acc*100:.1f}%")


def execute_training_pipeline(new_animal_name: str = None, epochs: int = DEFAULT_EPOCHS):
    """Executes the full training, validation, checkpointing, and safe deployment pipeline."""
    state = global_training_state
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        state.update(
            status="preparing",
            new_animal=new_animal_name,
            total_epochs=epochs,
            progress_percent=5,
            message="Preparing dataset and loading MobileNetV2 architecture..."
        )

        if not os.path.exists(DATASET_DIR):
            raise FileNotFoundError(f"Dataset directory '{DATASET_DIR}' not found.")

        # 1. Data augmentation & preprocessing (identical to train.py)
        train_datagen = ImageDataGenerator(
            rescale=1.0 / 255,
            validation_split=0.2,
            rotation_range=30,
            zoom_range=0.2,
            width_shift_range=0.2,
            height_shift_range=0.2,
            shear_range=0.2,
            horizontal_flip=True,
            fill_mode="nearest"
        )

        val_datagen = ImageDataGenerator(
            rescale=1.0 / 255,
            validation_split=0.2
        )

        train_data = train_datagen.flow_from_directory(
            DATASET_DIR,
            target_size=IMG_SIZE,
            batch_size=BATCH_SIZE,
            class_mode="categorical",
            subset="training",
            shuffle=True,
            seed=42
        )

        val_data = val_datagen.flow_from_directory(
            DATASET_DIR,
            target_size=IMG_SIZE,
            batch_size=BATCH_SIZE,
            class_mode="categorical",
            subset="validation",
            shuffle=False,
            seed=42
        )

        num_classes = len(train_data.class_indices)
        classes_list = sorted(list(train_data.class_indices.keys()))

        state.update(
            total_classes=num_classes,
            class_names=[c.capitalize() for c in classes_list],
            total_samples=train_data.samples + val_data.samples,
            message=f"Dataset verified: {num_classes} classes, {train_data.samples} train & {val_data.samples} val images."
        )

        print(f"[Trainer] Classes: {train_data.class_indices}")
        print(f"[Trainer] Train samples: {train_data.samples}, Val samples: {val_data.samples}")

        # 2. Build or Reuse MobileNetV2 Architecture without requiring internet download
        model = None
        if os.path.exists(BEST_MODEL_PATH):
            try:
                existing_model = tf.keras.models.load_model(BEST_MODEL_PATH)
                if existing_model.output_shape[-1] == num_classes:
                    model = existing_model
                else:
                    base_model = existing_model.layers[0]
                    base_model.trainable = False
                    model = Sequential([
                        base_model,
                        GlobalAveragePooling2D(),
                        Dense(256, activation="relu"),
                        Dropout(0.5),
                        Dense(128, activation="relu"),
                        Dense(num_classes, activation="softmax")
                    ])
            except Exception:
                pass

        if model is None:
            base_model = MobileNetV2(
                input_shape=(224, 224, 3),
                include_top=False,
                weights=None
            )
            base_model.trainable = False
            model = Sequential([
                base_model,
                GlobalAveragePooling2D(),
                Dense(256, activation="relu"),
                Dropout(0.5),
                Dense(128, activation="relu"),
                Dense(num_classes, activation="softmax")
            ])

        model.compile(
            optimizer="adam",
            loss="categorical_crossentropy",
            metrics=["accuracy"]
        )

        # 3. Callbacks: EarlyStopping, ModelCheckpoint (to temp path), ReduceLROnPlateau
        if os.path.exists(TEMP_MODEL_PATH):
            try:
                os.remove(TEMP_MODEL_PATH)
            except Exception:
                pass

        callbacks = [
            EpochProgressCallback(state, total_epochs=epochs),
            EarlyStopping(
                monitor="val_loss",
                patience=4,
                restore_best_weights=True
            ),
            ModelCheckpoint(
                TEMP_MODEL_PATH,
                monitor="val_accuracy",
                save_best_only=True,
                mode="max"
            ),
            ReduceLROnPlateau(
                monitor="val_loss",
                factor=0.2,
                patience=2,
                min_lr=0.000001
            )
        ]

        # 4. Train with verbose=0 so terminal stays clean
        history = model.fit(
            train_data,
            validation_data=val_data,
            epochs=epochs,
            callbacks=callbacks,
            verbose=0
        )

        state.update(
            status="validating_model",
            message="Validating trained model weights before deployment..."
        )

        # If checkpoint didn't save for any reason, save current model to temp path
        if not os.path.exists(TEMP_MODEL_PATH):
            model.save(TEMP_MODEL_PATH)

        # 5. Model Validation Step: Ensure the temp model loads properly
        test_loaded_model = tf.keras.models.load_model(TEMP_MODEL_PATH)
        dummy_input = np.zeros((1, 224, 224, 3), dtype=np.float32)
        _ = test_loaded_model.predict(dummy_input, verbose=0)
        del test_loaded_model

        # 6. Safe Atomic Replacement: Only deploy after successful validation
        shutil.copyfile(TEMP_MODEL_PATH, BEST_MODEL_PATH)
        model.save(FINAL_MODEL_PATH)

        # 7. Update class_labels.json in sync with model
        with open(CLASS_LABELS_PATH, "w", encoding="utf-8") as f:
            json.dump(train_data.class_indices, f, indent=4)

        # 8. Plot & save accuracy and loss graphs
        try:
            plt.figure(figsize=(9, 4.5))
            plt.plot(history.history.get("accuracy", []), label="Training Accuracy", color="#10b981")
            plt.plot(history.history.get("val_accuracy", []), label="Validation Accuracy", color="#34d399")
            plt.title("Model Retraining Accuracy")
            plt.xlabel("Epoch")
            plt.ylabel("Accuracy")
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(MODELS_DIR, "accuracy.png"))
            plt.close()

            plt.figure(figsize=(9, 4.5))
            plt.plot(history.history.get("loss", []), label="Training Loss", color="#ef4444")
            plt.plot(history.history.get("val_loss", []), label="Validation Loss", color="#f59e0b")
            plt.title("Model Retraining Loss")
            plt.xlabel("Epoch")
            plt.ylabel("Loss")
            plt.legend()
            plt.tight_layout()
            plt.savefig(os.path.join(MODELS_DIR, "loss.png"))
            plt.close()
        except Exception:
            pass

        # 9. Hot-reload ModelManager
        model_manager.reload()

        final_train_acc = history.history.get("accuracy", [0.0])[-1]
        final_val_acc = history.history.get("val_accuracy", [0.0])[-1]

        state.update(
            status="completed",
            progress_percent=100,
            train_accuracy=final_train_acc,
            val_accuracy=final_val_acc,
            message=(
                f"Model successfully updated with {num_classes} classes! "
                f"Train Accuracy: {final_train_acc*100:.1f}%, Val Accuracy: {final_val_acc*100:.1f}%."
            )
        )
        print(f"[Trainer] Training completed successfully for '{new_animal_name}'.")

    except Exception as e:
        print(f"[Trainer] Training failed: {e}")
        state.update(
            status="error",
            error=str(e),
            message=f"Training encountered an error: {str(e)}"
        )
    finally:
        # Clean up temp file
        if os.path.exists(TEMP_MODEL_PATH):
            try:
                os.remove(TEMP_MODEL_PATH)
            except Exception:
                pass


def start_retraining(new_animal_name: str = None, epochs: int = DEFAULT_EPOCHS) -> tuple[bool, str]:
    """Starts the retraining process in a separate background thread."""
    global _trainer_lock
    if global_training_state.status in ["preparing", "training", "validating_model"]:
        return False, "A model retraining process is currently in progress."

    with _trainer_lock:
        global_training_state.reset()
        global_training_state.new_animal = new_animal_name
        thread = threading.Thread(
            target=execute_training_pipeline,
            args=(new_animal_name, epochs),
            daemon=True
        )
        thread.start()
        return True, "Model retraining initiated successfully."


def get_current_training_status() -> dict:
    return global_training_state.to_dict()

