from utils.db import get_db_connection

def create_problem(problem, description, lat, lon, image_path=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reported_problems (problem, description, lat, lon, image_path)
        VALUES (?, ?, ?, ?, ?)
    """, (problem, description, lat, lon, image_path))

    last_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return last_id


def get_all_problems(status="active"):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT * FROM reported_problems
        WHERE status = ?
        ORDER BY created_at DESC
    """, (status,))

    problems = cursor.fetchall()
    conn.close()
    return problems


def update_problem_status(problem_id, status="resolved"):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE reported_problems
        SET status = ?
        WHERE id = ?
    """, (status, problem_id))

    conn.commit()
    conn.close()
