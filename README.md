# 🐾 Animal AI — Intelligent Animal Detection & Scientific Knowledge Hub

An advanced, production-grade AI Dashboard and Conversational Chatbot powered by Deep Learning (**MobileNetV2** transfer learning) and Flask. The platform identifies animal species from photographs in real time, provides confidence rankings, delivers 10 verified scientific facts, engages in zoological Q&A, and features an autonomous self-retraining machine learning pipeline.

---

## 🌟 Key Features

### 1. ⚡ Real-Time Neural Classification
- **Deep Learning Architecture**: Utilizes MobileNetV2 transfer learning trained on curated 224×224 images.
- **High-Precision Prediction**: Generates top classification with confidence percentages and top-3 prediction probabilities.
- **Silent Inference**: Seamless inference directly processed in the background with zero UI clutter.

### 2. 🔬 10 Comprehensive Scientific Facts
For every detected animal, the AI Assistant automatically surfaces 10 structured, verified scientific facts:
1. Scientific Taxonomy & Nomenclature
2. Natural Habitat & Biome
3. Average Lifespan (Wild & Captivity)
4. Diet & Feeding Habits
5. Physical Characteristics & Adaptations
6. Weight & Dimensions
7. Geographic Distribution & Range
8. Social Structure & Behavioral Patterns
9. Reproductive Cycle & Gestation
10. Conservation Status (IUCN Red List) & Key Threats

### 3. 💬 Interactive Zoological Chatbot
- Follow-up conversational inquiries directly tied to the currently analyzed animal (e.g., *"Where does this animal live?"*, *"Is it endangered?"*, *"What does it eat?"*).
- Instant replies backed by structured zoological datasets.
- Session conversation history with one-click clear.

### 4. 🔄 Autonomous Model Retraining Pipeline
- **Add New Animal**: Expand model coverage on the fly with a single click.
- **Autonomous Dataset Curation**: Multi-threaded downloader fetches ~100 candidate images, filters corrupted files, deduplicates via MD5 hashing, and verifies image integrity using PIL.
- **Hot-Reload Transfer Learning**: Automatically runs transfer learning with 80/20 train-validation split, categorical crossentropy, `EarlyStopping`, `ReduceLROnPlateau`, and `ModelCheckpoint`.
- **Zero-Downtime Deployment**: Atomically validates temporary weights before hot-reloading the active model and synchronizing `class_labels.json`.

### 5. 🎨 Modern Apple/ChatGPT Glassmorphism UI
- Fully responsive interface optimized for Desktop, Tablet, and Mobile.
- Transparent glassmorphic chat container with subtle glowing emerald borders.
- Drag-and-drop file upload, file browsing, and clipboard paste (`Ctrl+V`) support.
- Quick demo test chips for instant evaluation.

---

## 🏗️ Project Architecture

```
Animal_Detector_App/
│
├── animal_datasets/            # Curated training image sets per animal class
│   ├── cat/
│   ├── cow/
│   ├── deer/
│   ├── dog/
│   ├── elephant/
│   ├── giraffe/
│   ├── hippopotamus/
│   ├── horse/
│   ├── lion/
│   ├── panda/
│   ├── penguin/
│   ├── tiger/
│   ├── wolf/
│   └── zebra/
│
├── models/                     # Saved models and training telemetry
│   ├── best_animal_model.tflite # High-performance LiteRT model (9.8 MB) for production & Vercel
│   ├── best_animal_model.keras # Primary Keras model
│   ├── animal_detector_model.keras
│   ├── accuracy.png            # Retraining accuracy history curve
│   └── loss.png                # Retraining loss history curve
│
├── static/                     # Frontend assets
│   ├── css/
│   │   └── style.css           # Glassmorphism, animations, responsive design
│   └── js/
│       └── main.js             # Client controller, API bridges, UI states
│
├── templates/
│   └── index.html              # Main dashboard view
│
├── api/                        # Vercel serverless functions
│   └── index.py                # Serverless entrypoint
│
├── assets/                     # App media & sample images
│   ├── img/
│   │   └── background.png
│   └── samples/                # Fast demo sample photos for all 15 animals
│
├── uploads/                    # Temporary staging directory for uploads
├── app.py                      # Flask backend API & web server
├── animal_knowledge.py         # Zoological facts database & conversational Q&A
├── image_downloader.py         # Multi-threaded image collector & PIL validator
├── model_manager.py            # Singleton model loader, inference & hot-reload
├── trainer.py                  # Background retraining thread & telemetry
├── class_labels.json           # Active class indices synchronized with model
├── vercel.json                 # Vercel deployment & routing configuration
├── .vercelignore               # Excludes raw datasets & heavy dependencies
├── requirements.txt            # Python dependencies
└── run.bat                     # Windows launch script
```

---

## 🚀 Quickstart Guide

### Prerequisites
- Python 3.9, 3.10, or 3.11 installed.
- Git installed.

### 1. Clone the Repository
```bash
git clone https://github.com/Shubham-shaw-c/Animal_Detector.git
cd Animal_Detector
```

### 2. Set Up Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Application
You can launch directly using the provided Windows script:
```bash
run.bat
```
Or run directly via Python:
```bash
python app.py
```

Open your browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 📡 REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `GET /` | `GET` | Serves main Dashboard web interface |
| `GET /api/animals` | `GET` | Returns list of currently supported animal classes and status |
| `POST /api/predict` | `POST` | Accepts multipart image file, returns classification, top-3 & facts |
| `POST /api/chat` | `POST` | Accepts JSON `{ message, animal }`, returns contextual AI answer |
| `GET /api/sample/<animal>`| `GET` | Serves a sample image from dataset for instant testing |
| `POST /api/add-animal` | `POST` | Accepts `{ name, limit }`, starts automated image collection |
| `GET /api/download-progress`| `GET` | Returns live download and validation progress |
| `POST /api/train` | `POST` | Triggers background model retraining pipeline |
| `GET /api/training-status` | `GET` | Returns real-time training epoch metrics and loss/accuracy |
| `GET /api/facts/<animal>` | `GET` | Returns 10 structured scientific facts for any animal |

---

## 🧠 Supported Animal Classes (15)

- 🐻 **Bear**
- 🐱 **Cat**
- 🐮 **Cow**
- 🦌 **Deer**
- 🐶 **Dog**
- 🐘 **Elephant**
- 🦒 **Giraffe**
- 🦛 **Hippopotamus**
- 🐴 **Horse**
- 🦁 **Lion**
- 🐼 **Panda**
- 🐧 **Penguin**
- 🐯 **Tiger**
- 🐺 **Wolf**
- 🦓 **Zebra**

*Additional animals can be added autonomously via the "+ Add New Animal" dashboard workflow.*

---

## 🛠️ Technology Stack

- **Backend**: Python 3.10, Flask, Flask-CORS, Werkzeug
- **AI / Deep Learning**: TensorFlow 2.16+, Keras, MobileNetV2, NumPy, Matplotlib
- **Image Processing**: Pillow (PIL)
- **Frontend**: Modern HTML5, Responsive CSS3 (Glassmorphism & CSS Grid), Vanilla ES6+ JavaScript
- **Icons & Typography**: FontAwesome 6, Plus Jakarta Sans, JetBrains Mono

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).

