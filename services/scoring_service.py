from math import radians, cos, sin, asin, sqrt

# ==============================
# Distance (Haversine) in meters
# ==============================
def haversine(lat1, lon1, lat2, lon2):
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return 6371000 * c  # meters


# ==============================
# Problem Severity Mapping
# ==============================
PROBLEM_WEIGHTS = {
    "stairs": 35,
    "unsafe_surface": 25,
    "pothole": 15,
    "obstacle": 10,
    "other": 5
}


def classify_problem_type(problem_text):
    if not problem_text:
        return "other"

    t = problem_text.lower()

    if "stairs" in t or "staircase" in t:
        return "stairs"

    if "unsuitable surface" in t or "surface" in t:
        return "unsafe_surface"

    if "pothole" in t or "crack" in t or "broken" in t:
        return "pothole"

    if "obstacle" in t or "congested" in t:
        return "obstacle"

    return "other"


# ==============================
# Route Scoring (Wheelchair-aware)
# ==============================
def score_route(route_coords, problems, proximity_m=30):
    """
    route_coords: list of (lat, lon)
    problems: list of dicts {lat, lon, problem, description}
    """

    score = 100
    found_problems = []

    for p in problems:
        plat, plon = p["lat"], p["lon"]

        min_dist = min(
            haversine(plat, plon, rlat, rlon)
            for rlat, rlon in route_coords
        )

        if min_dist <= proximity_m:
            ptype = classify_problem_type(p.get("problem", ""))
            penalty = PROBLEM_WEIGHTS.get(ptype, 5)

            # كل ما المشكلة أقرب للطريق → عقوبة أعلى
            distance_factor = max(0.5, min(1.0, min_dist / proximity_m))
            final_penalty = penalty * (1 / distance_factor)

            score -= final_penalty
            found_problems.append({
                **p,
                "type": ptype,
                "penalty": int(final_penalty)
            })

    score = max(0, min(100, int(score)))

    return {
        "score": score,
        "problems_found": found_problems
    }
