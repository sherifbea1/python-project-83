from .db import get_conn


def insert_url(normalized_url: str):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            """
            INSERT INTO urls (name)
            VALUES (%s)
            ON CONFLICT (name) DO NOTHING
            RETURNING id;
            """,
            (normalized_url,)
        )
        row = cur.fetchone()
        conn.commit()

        return row["id"] if row else None

    finally:
        cur.close()
        conn.close()


def get_url_by_name(name: str):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM urls WHERE name = %s;", (name,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row


def get_url_by_id(id: int):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT * FROM urls WHERE id = %s;", (id,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row


def get_all_urls():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            u.id,
            u.name,
            u.created_at,
            lc.status_code AS last_status,
            lc.created_at AS last_check
        FROM urls u
        LEFT JOIN LATERAL (
            SELECT status_code, created_at
            FROM url_checks uc
            WHERE uc.url_id = u.id
            ORDER BY created_at DESC
            LIMIT 1
        ) lc ON true
        ORDER BY u.id DESC;
        """
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()
    return rows
