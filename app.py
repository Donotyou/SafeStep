from flask import Flask, render_template, request, redirect, url_for
import os
from PIL import Image
from werkzeug.utils import secure_filename

from utils.db import init_db
from models.problem_model import create_problem, get_all_problems
from cv_model.predict import classify_problem
from services.geocoding_service import geocode
from services.routing_service import compute_routes
from services.problem_service import get_problems_in_bbox as fetch_problems_in_bbox, get_all_problems as fetch_all_problems
from services.scoring_service import score_route
from flask import jsonify
from utils.db import get_db_connection
from models.problem_model import create_problem as create_problem_model
from models.problem_model import update_problem_status, get_all_problems

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def convert_webp_to_jpg(image_path):
    if image_path.lower().endswith(".webp"):
        im = Image.open(image_path).convert("RGB")
        new_path = os.path.splitext(image_path)[0] + ".jpg"
        im.save(new_path, "JPEG")
        return new_path
    return image_path


@app.route("/")
def index():
    problems = get_all_problems()
    problems_list = [dict(p) for p in problems]
    return render_template("index.html", problems=problems_list)


@app.route("/report", methods=["GET", "POST"])
def report_problem():
    if request.method == "POST":
        image = request.files.get("image")
        lat = float(request.form.get("lat"))
        lon = float(request.form.get("lon"))

        image_path = None
        filename = None
        problem_type = "unknown"
        description = "No description"

        if image and image.filename != "":
          
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            image.save(image_path)

            
            image_path = convert_webp_to_jpg(image_path)
            filename = os.path.basename(image_path)

          
            problem_type, description = classify_problem(image_path)

       
        create_problem(
            problem=problem_type,
            description=description,
            lat=lat,
            lon=lon,
            image_path=filename
        )

        return redirect(url_for("index"))

    return render_template("report_problem.html")


@app.route('/routes')
def routes_page():
    return render_template('routes.html')


@app.route('/api/compute_routes', methods=['POST'])
def api_compute_routes():
    data = request.get_json()
    start = data.get('start')  # [lat, lon]
    dest = data.get('dest')
    if not start or not dest:
        return jsonify({'error': 'start and dest required'}), 400

    # compute route alternatives
    routes = compute_routes((start[0], start[1]), (dest[0], dest[1]), max_routes=3)

    # compute bbox around start/dest and fetch only nearby problems to evaluate routes
    lat_min = min(start[0], dest[0])
    lat_max = max(start[0], dest[0])
    lon_min = min(start[1], dest[1])
    lon_max = max(start[1], dest[1])
    # add padding (degrees) ~0.01 ~= 1.1km; ensures nearby problems slightly off-route are included
    padding = 0.01
    south = lat_min - padding
    north = lat_max + padding
    west = lon_min - padding
    east = lon_max + padding

    problems = fetch_problems_in_bbox(south, north, west, east)

    result_routes = []
    for r in routes:
        # r is list of (lat, lon)
        scoring = score_route(r, problems, proximity_m=30)
        result_routes.append({
            'coords': r,
            'problems_count': len(scoring['problems_found']),
            'score': scoring['score'],
            'problems': scoring['problems_found']
        })

    return jsonify({'routes': result_routes})


@app.route('/api/problems', methods=['GET'])
def api_problems():
    # optional bbox query params: south,north,west,east
    try:
        south = request.args.get('south', type=float)
        north = request.args.get('north', type=float)
        west = request.args.get('west', type=float)
        east = request.args.get('east', type=float)
    except Exception:
        south = north = west = east = None

    if None not in (south, north, west, east):
        problems = fetch_problems_in_bbox(south, north, west, east)
    else:
        problems = fetch_all_problems()

    return jsonify({'problems': problems})


@app.route('/api/report', methods=['POST'])
def api_report():
    # Accept multipart/form-data from modal submission (image optional)
    image = request.files.get('image')
    lat = request.form.get('lat')
    lon = request.form.get('lon')
    problem_type = request.form.get('problem_type') or 'other'
    description = request.form.get('description') or ''

    if lat is None or lon is None:
        return jsonify({'error': 'lat and lon required'}), 400

    try:
        latf = float(lat)
        lonf = float(lon)
    except Exception:
        return jsonify({'error': 'invalid coordinates'}), 400

    filename = None
    image_path = None
    if image and image.filename != '':
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(image_path)
        image_path = convert_webp_to_jpg(image_path)
        filename = os.path.basename(image_path)

    # If you have a classifier available, use it; otherwise use provided problem_type
    problem_label = problem_type
    try:
        if filename:
            # attempt classification, but do not fail if model errors
            problem_label, description = classify_problem(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    except Exception:
        pass

    new_id = create_problem_model(problem_label, description, latf, lonf, filename)

    # fetch inserted row to return
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, problem, description, lat, lon, image_path, created_at FROM reported_problems WHERE id = ?", (new_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'insert failed'}), 500

    problem = {
        'id': row['id'],
        'problem': row['problem'],
        'description': row['description'],
        'lat': float(row['lat']),
        'lon': float(row['lon']),
        'image_path': row['image_path'],
        'created_at': row['created_at']
    }

    return jsonify({'problem': problem})


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


@app.route('/api/admin/problems', methods=['GET'])
def api_admin_problems():
    # support region param or bbox params
    region = request.args.get('region')
    south = request.args.get('south', type=float)
    north = request.args.get('north', type=float)
    west = request.args.get('west', type=float)
    east = request.args.get('east', type=float)

    # simple predefined regions (example bboxes). Adjust as needed.
    regions = {
        'cairo_center': {'south':30.02, 'north':30.08, 'west':31.18, 'east':31.32},
        'downtown': {'south':30.04, 'north':30.06, 'west':31.22, 'east':31.26},
        'giza': {'south':29.95, 'north':30.05, 'west':31.1, 'east':31.3}
    }

    if region in regions:
        r = regions[region]
        problems = fetch_problems_in_bbox(r['south'], r['north'], r['west'], r['east'])
    elif None not in (south, north, west, east):
        problems = fetch_problems_in_bbox(south, north, west, east)
    else:
        problems = fetch_all_problems()

    return jsonify({'problems': problems})


@app.route('/api/admin/resolve', methods=['POST'])
def api_admin_resolve():
    data = request.get_json() or {}
    pid = data.get('id')
    if not pid:
        return jsonify({'error': 'id required'}), 400
    try:
        update_problem_status(pid, status='resolved')
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    init_db()
    # Disable Flask reloader to prevent watchdog from restarting the server
    # when new uploaded files are written into the project tree.
    app.run(debug=True, use_reloader=False)
