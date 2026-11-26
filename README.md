# SafeStep: Accessible Navigation for Wheelchair Users

SafeStep is a web app that plans walking routes with accessibility in mind. Regular maps give the shortest route; SafeStep ranks route alternatives by how many reported obstacles (stairs, potholes, damaged surfaces, crowded paths) lie along them. Users report problems by uploading a photo, and an AI pipeline decides automatically whether the spot is accessible for wheelchair users.

## Features

- **Photo-based problem reporting:** upload a photo and a location; the AI pipeline classifies the spot as `safe` or `unsafe` and explains why.
- **Interactive map:** view all active reports on a Leaflet map.
- **Accessible route planning:** pick a start and destination (by clicking the map or searching an address) and get up to 3 alternative walking routes, each with an accessibility score from 0 to 100.
- **Admin page:** filter reports by region and mark them as resolved.

## How the AI pipeline works

Each uploaded photo goes through four checks in `cv_model/predict.py`:

| Check | Model | Rule |
|---|---|---|
| Potholes and cracks | YOLO (Ultralytics), `pothole_model.pt` | Flagged when 2 or more are detected (confidence ≥ 0.4) |
| Obstacles (people, cars, buses, trucks, motorcycles, bicycles) | YOLO (Ultralytics), `obstacle_model.pt` | Flagged when 5 or more are detected (confidence ≥ 0.4) |
| Stairs | CLIP zero-shot classification (Hugging Face Transformers) | Flagged when "staircase or steps" is the top label with a score above 0.45 |
| Surface suitability | CLIP zero-shot classification | Flagged when the top label is not one of the accessible-surface labels (smooth asphalt, clean sidewalk, ramp, ...) or its score is below 0.6 |

If any check is flagged, the report is marked `unsafe` and the reasons are stored as its description. Otherwise it is marked `safe`.

## How routes are scored

1. **Route generation (`services/routing_service.py`):** with OSMnx installed, the app builds a walkable street graph around the trip and uses NetworkX to find up to 3 shortest simple paths. Without OSMnx, or if routing fails, it falls back to straight-line alternatives so the demo still works.
2. **Scoring (`services/scoring_service.py`):** each route starts at 100. Every active report within 30 m of the route subtracts a penalty based on its type:

| Problem type | Base penalty |
|---|---|
| Stairs | 35 |
| Unsafe surface | 25 |
| Pothole | 15 |
| Obstacle | 10 |
| Other | 5 |

Reports closer to the route weigh more (up to 2x the base penalty). The final score is clamped to 0-100, and the app returns each route's score and the problems found along it.

## Tech stack

Python, Flask, SQLite, Ultralytics YOLO, Hugging Face Transformers (CLIP), PyTorch, Pillow, NetworkX, OSMnx (optional), Leaflet, OpenStreetMap Nominatim (address search).

## Project structure

```
SafeStep/
├── app.py                  # Flask app and API routes
├── cv_model/
│   ├── predict.py          # YOLO + CLIP classification pipeline
│   ├── yolo/               # YOLO weights (not in the repo, see Setup)
│   └── clip/               # CLIP config and tokenizer (weights not in the repo)
├── services/
│   ├── routing_service.py  # route alternatives (OSMnx + NetworkX)
│   ├── scoring_service.py  # accessibility score per route
│   ├── problem_service.py  # queries for reported problems
│   └── geocoding_service.py
├── models/problem_model.py # database operations
├── utils/db.py             # SQLite connection and schema
├── templates/              # Jinja2 pages
├── static/                 # CSS, JavaScript, uploaded images
└── data/                   # SQLite database (created on first run)
```

## Setup

1. Clone the repository and create a virtual environment:

   ```bash
   git clone https://github.com/Donotyou/SaveStep.git
   cd SaveStep
   python -m venv venv
   source venv/bin/activate        # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Add the model files, which are not stored in the repository:
   - `cv_model/yolo/obstacle_model.pt`
   - `cv_model/yolo/pothole_model.pt`
   - CLIP model weights in `cv_model/clip/` next to the existing config and tokenizer files (the config matches a ViT-B/32 CLIP checkpoint, for example `openai/clip-vit-base-patch32` on Hugging Face).

3. Run the app:

   ```bash
   python app.py
   ```

   Open `http://127.0.0.1:5000`. The database is created automatically on the first run.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Map of active reports |
| GET, POST | `/report` | Report a problem with a photo |
| GET | `/routes` | Route planning page |
| POST | `/api/compute_routes` | Compute and score route alternatives |
| GET | `/api/problems` | List active reports, optionally within a bounding box |
| POST | `/api/report` | Submit a report from the map |
| GET | `/admin` | Admin page |
| GET | `/api/admin/problems` | List reports by region or bounding box |
| POST | `/api/admin/resolve` | Mark a report as resolved |

## Known limitations

- The detection thresholds (2 potholes, 5 obstacles, CLIP score cutoffs) are hand-tuned rules, not formally evaluated.
- The admin page has no authentication.
- There are no automated tests yet.
- Address search uses the public Nominatim service, which has usage limits.

## Team

Built as a team project.

<!-- TODO (owner): add a "Model training" section here: dataset source and size, how the YOLO models were fine-tuned, framework and version, and evaluation metrics (mAP, precision/recall). -->
