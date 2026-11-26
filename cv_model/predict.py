import os
from ultralytics import YOLO
from transformers import pipeline
from PIL import Image
import torch

# ==============================
# Paths
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

YOLO_DIR = os.path.join(BASE_DIR, "yolo")
CLIP_DIR = os.path.join(BASE_DIR, "clip")

OBSTACLE_MODEL_PATH = os.path.join(YOLO_DIR, "obstacle_model.pt")
POTHOLE_MODEL_PATH  = os.path.join(YOLO_DIR, "pothole_model.pt")

# ==============================
# Device
# ==============================
device = 0 if torch.cuda.is_available() else -1

# ==============================
# Load Models (ONCE)
# ==============================
obstacle_model = YOLO(OBSTACLE_MODEL_PATH)
pothole_model  = YOLO(POTHOLE_MODEL_PATH)

clip_model = pipeline(
    "zero-shot-image-classification",
    model=CLIP_DIR,
    device=device
)

OBSTACLE_CLASSES = [
    "person", "car", "bus", "truck", "motorcycle", "bicycle"
]

# ==============================
# CLIP – Stairs Detection
# ==============================
def detect_stairs(image_path):
    image = Image.open(image_path)
    labels = ["staircase or steps", "flat road", "sidewalk"]
    results = clip_model(image, candidate_labels=labels)
    top = results[0]
    if top["label"] == "staircase or steps" and top["score"] > 0.45:
        return True
    return False

# ==============================
# CLIP – Surface Suitability
# ==============================
def check_surface_suitability(image_path):
    image = Image.open(image_path)
    surface_labels = [
        "flat smooth asphalt road",
        "clean concrete sidewalk",
        "paved accessible street",
        "smooth colorful tiled pavement",
        "wheelchair accessible ramp or slider",
        "flat brick road without defects",
        "rough rocky offroad",
        "sandy soil",
        "grass floor",
        "damaged broken ground",
        "damaged concrete with holes",
        "broken pavement with loose tiles",
        "uneven surface with cracks and debris"
    ]
    results = clip_model(image, candidate_labels=surface_labels)
    results.sort(key=lambda x: x["score"], reverse=True)
    top_label = results[0]["label"]
    top_score = results[0]["score"]

    safe_labels = [
        "flat smooth asphalt road",
        "clean concrete sidewalk",
        "paved accessible street",
        "smooth colorful tiled pavement",
        "wheelchair accessible ramp or slider",
        "flat brick road without defects"
    ]

    if top_label not in safe_labels or top_score < 0.6:
        return True, top_label  # Unsuitable, with reason

    return False, top_label  # Suitable, with label
# ==============================
# Main Pipeline
# ==============================
def classify_problem(image_path):
    # YOLO: Obstacles
    obs_results = obstacle_model(image_path, conf=0.4, verbose=False)[0]
    obstacles_count = len([
        box for box in obs_results.boxes
        if obstacle_model.names[int(box.cls[0])] in OBSTACLE_CLASSES
    ])

    # YOLO: Potholes
    pothole_results = pothole_model(image_path, conf=0.4, verbose=False)[0]
    potholes_count = len(pothole_results.boxes)

    # CLIP: Stairs
    stairs_detected = detect_stairs(image_path)

    # CLIP: Surface
    surface_unsuitable, surface_type = check_surface_suitability(image_path)

    # Decision logic
    reasons = []
    if potholes_count >= 2:
        reasons.append(f"{potholes_count} potholes/cracks detected")
    if surface_unsuitable:
        reasons.append(f"unsuitable surface ({surface_type})")
    if stairs_detected:
        reasons.append("stairs detected")
    if obstacles_count >= 5:
        reasons.append(f"{obstacles_count} obstacles detected")

    if reasons:
        return (
            "unsafe",
            "❌ Not wheelchair accessible: " + " | ".join(reasons)
        )

    return (
        "safe",
        "✅ Road appears accessible for wheelchair users."
    )
