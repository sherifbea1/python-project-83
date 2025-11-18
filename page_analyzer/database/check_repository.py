from .db import get_conn


def insert_check(url_id: int, status_code: int, title: str, h1: str, description: str):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO url_checks (
                url_id, status_code, title, h1, description
            )
            VALUES (%s, %s, %s, %s, %s);
            """,
            (url_id, status_code, title, h1, description)
        )
        conn.commit()

    finally:
        cur.close()
        conn.close()


def get_checks_for_url(url_id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT *
        FROM url_checks
        WHERE url_id = %s
        ORDER BY created_at DESC;
        """,
        (url_id,)
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows
