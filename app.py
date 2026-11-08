"""
app.py
Production-ready Flask application for AI Animal Detection Dashboard and Chatbot.
Provides real-time model inference, dataset expansion, background retraining,
and conversational scientific facts exploration.
"""

import os
import sys
import subprocess
import warnings
import logging

# Ensure quiet environment: suppress TensorFlow, absl, CUDA, oneDNN, matplotlib, and PIL warnings
import tempfile
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
os.environ['MPLCONFIGDIR'] = os.path.join(tempfile.gettempdir(), 'mpl_cache')
os.environ['PYTHONWARNINGS'] = 'ignore'
warnings.filterwarnings('ignore')
logging.getLogger('tensorflow').setLevel(logging.ERROR)

# Automatically switch to project virtual environment if invoked via global python
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
venv_python = os.path.join(BASE_DIR, "venv", "Scripts", "python.exe")
if os.path.exists(venv_python) and os.path.abspath(sys.executable).lower() != os.path.abspath(venv_python).lower():
    sys.exit(subprocess.call([venv_python] + sys.argv))

# Suppress Werkzeug HTTP request logger to prevent log flooding from polling & assets
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

import uuid
import werkzeug.utils
from flask import Flask, jsonify, render_template, request, send_from_directory
from flask_cors import CORS
from PIL import Image

from animal_knowledge import answer_animal_question, get_animal_facts
from image_downloader import (
    get_current_download_status,
    start_image_download,
    validate_animal_name,
)
from model_manager import model_manager
from trainer import (
    get_current_training_status,
    global_training_state,
    start_retraining,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
ASSETS_FOLDER = os.path.join(BASE_DIR, "assets")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "jfif"}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(ASSETS_FOLDER, exist_ok=True)

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static"
)
CORS(app)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max upload limit


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    print(f"[USER ACTION] Connected to Animal AI Dashboard from {request.remote_addr}")
    return render_template("index.html")


@app.route("/assets/<path:filename>")
def serve_assets(filename):
    return send_from_directory(ASSETS_FOLDER, filename)


@app.route("/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


@app.route("/api/sample/<animal>")
def get_sample_image(animal):
    """Serve a sample image from the existing dataset for instant demonstration."""
    folder = os.path.join(BASE_DIR, "animal_datasets", animal.lower().strip())
    if os.path.exists(folder):
        images = [f for f in os.listdir(folder) if allowed_file(f)]
        if images:
            print(f"[USER ACTION] Loaded demo sample photo for '{animal.capitalize()}'")
            return send_from_directory(folder, images[0])
    return jsonify({"error": f"No sample found for {animal}"}), 404


# ==========================================
# API ENDPOINTS
# ==========================================

@app.route("/api/animals", methods=["GET"])
def get_animals():
    """Return list of supported animal classes and model status."""
    info = model_manager.get_supported_classes()
    return jsonify({
        "success": True,
        "total_classes": info["total_classes"],
        "classes": info["classes"],
        "raw_classes": info["raw_classes"],
        "is_loaded": info["is_loaded"],
        "model_path": info["model_path"]
    })


@app.route("/api/predict", methods=["POST"])
def predict():
    """Upload and classify an animal image."""
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file provided in request."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename."}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "success": False,
            "error": "Unsupported file format. Please upload JPG, PNG, WEBP, or BMP."
        }), 400

    try:
        # Save uploaded image with unique safe filename
        ext = file.filename.rsplit(".", 1)[1].lower()
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)
        file.save(filepath)

        # Open and verify with PIL
        with Image.open(filepath) as pil_img:
            # Perform prediction
            result = model_manager.predict(pil_img)

        result["image_url"] = f"/uploads/{unique_name}"
        print(f"[PREDICTION] Analyzed uploaded image -> Detected: {result.get('detected_animal')} ({result.get('confidence', 0):.1f}% confidence)")
        return jsonify(result)

    except Exception as e:
        print(f"[API /predict] Inference error: {e}")
        return jsonify({"success": False, "error": f"Inference error: {str(e)}"}), 500


@app.route("/api/chat", methods=["POST"])
def chat():
    """Handle follow-up questions about the detected animal."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    animal = data.get("animal", "").strip()

    if not message:
        return jsonify({"success": False, "error": "Message is required."}), 400

    if not animal:
        # Fallback if no animal was previously detected
        return jsonify({
            "success": True,
            "reply": "Please upload an animal image first so I can analyze it and answer questions about it!",
            "animal": None
        })

    reply = answer_animal_question(animal, message)
    print(f"[CHAT] Animal: {animal} | User Question: '{message}'")
    return jsonify({
        "success": True,
        "reply": reply,
        "animal": animal
    })


@app.route("/api/add-animal", methods=["POST"])
def add_animal():
    """Validate and initiate dataset download for a new animal."""
    data = request.get_json(silent=True) or {}
    raw_name = data.get("name", "").strip()
    limit = int(data.get("limit", 100))

    existing_classes = model_manager.get_supported_classes()["raw_classes"]
    is_valid, normalized_name, error_msg = validate_animal_name(raw_name, existing_classes)

    if not is_valid:
        return jsonify({"success": False, "error": error_msg}), 400

    print(f"[NEW ANIMAL] User requested to add animal class: '{raw_name.capitalize()}'")
    success, msg = start_image_download(normalized_name, target_count=limit)
    if not success:
        return jsonify({"success": False, "error": msg}), 409

    return jsonify({
        "success": True,
        "animal": normalized_name,
        "display_name": raw_name.capitalize(),
        "message": msg
    })


@app.route("/api/download-progress", methods=["GET"])
def download_progress():
    """Get real-time dataset download and validation progress."""
    status = get_current_download_status()
    return jsonify({"success": True, "data": status})


@app.route("/api/train", methods=["POST"])
def train():
    """Trigger background model retraining on the complete updated dataset."""
    data = request.get_json(silent=True) or {}
    new_animal = data.get("animal", "").strip()
    epochs = int(data.get("epochs", 10))

    print(f"[TRAINER] User triggered retraining for: '{new_animal.capitalize() if new_animal else 'Complete Dataset'}'")
    success, msg = start_retraining(new_animal_name=new_animal or None, epochs=epochs)
    if not success:
        return jsonify({"success": False, "error": msg}), 409

    return jsonify({
        "success": True,
        "message": msg,
        "new_animal": new_animal
    })


@app.route("/api/training-status", methods=["GET"])
def training_status():
    """Get real-time model retraining status and epoch metrics."""
    status = get_current_training_status()
    return jsonify({"success": True, "data": status})


@app.route("/api/facts/<animal_name>", methods=["GET"])
def get_facts_endpoint(animal_name):
    """Retrieve 10 structured scientific facts for any animal."""
    facts_data = get_animal_facts(animal_name)
    return jsonify({"success": True, "data": facts_data})


if __name__ == "__main__":
    # Suppress default Flask startup banner for clean terminal output
    import flask.cli
    flask.cli.show_server_banner = lambda *args: None


    print("  🐾 ANIMAL AI — DETECTOR & SCIENTIFIC CHATBOT DASHBOARD")
    print("  🌐 Running at : http://127.0.0.1:5000")
    print(f"  🧠 Model Ready : {len(model_manager.class_indices)} Animal Classes Supported")
    print("[SYSTEM] Server initialized successfully. Ready for user requests.\n")

    app.run(host="127.0.0.1", port=5000, debug=False)

