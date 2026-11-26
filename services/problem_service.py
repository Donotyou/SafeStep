from utils.db import get_db_connection
import os


def get_all_problems():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, problem, description, lat, lon, image_path
        FROM reported_problems
        WHERE status = 'active'
        """
    )

    rows = cur.fetchall()
    conn.close()

    problems = []
    for r in rows:
        img = r["image_path"]
        if img:
            img = os.path.basename(img)

        problems.append({
            "id": r["id"],

            "problem": r["problem"],
            "description": r["description"],

            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "image_path": img
        })

    return problems


def get_problems_in_bbox(south, north, west, east):
    """
    Returns AI-detected problems inside map bounding box
    """

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, problem, description, lat, lon, image_path
        FROM reported_problems
        WHERE status = 'active'
          AND lat BETWEEN ? AND ?
          AND lon BETWEEN ? AND ?
        """,
        (south, north, west, east)
    )

    rows = cur.fetchall()
    conn.close()

    problems = []
    for r in rows:
        img = r["image_path"]
        if img:
            img = os.path.basename(img)

        problems.append({
            "id": r["id"],

            "problem": r["problem"],
            "description": r["description"],

            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "image_path": img
        })

    return problems
