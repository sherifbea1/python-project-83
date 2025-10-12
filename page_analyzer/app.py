import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default-secret')

DATABASE_URL = os.getenv('DATABASE_URL')


def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def normalize_url(input_url: str) -> str:
    parsed = urlparse(input_url)
    if not parsed.scheme:
        parsed = urlparse(f"http://{input_url}")
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_page(html_text: str) -> dict:
    soup = BeautifulSoup(html_text, "html.parser")
    title_tag = soup.find("title")
    h1_tag = soup.find("h1")
    desc_tag = soup.find("meta", attrs={"name": "description"})
    title = title_tag.text.strip() if title_tag else None
    h1 = h1_tag.text.strip() if h1_tag else None
    description = desc_tag.get("content").strip() if desc_tag and desc_tag.get("content") else None
    return {"title": title, "h1": h1, "description": description}


def check_page(url: str):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        parsed = parse_page(response.text)
        return {
            "status_code": response.status_code,
            "title": parsed["title"],
            "h1": parsed["h1"],
            "description": parsed["description"],
        }
    except requests.RequestException:
        return None


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def add_url():
    raw_url = request.form.get('url')
    if not raw_url or len(raw_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422

    parsed = urlparse(raw_url)
    if not parsed.netloc:
        parsed = urlparse(f"http://{raw_url}")
    if not parsed.netloc:
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422

    normalized = normalize_url(raw_url)
    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO urls (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id;",
            (normalized,),
        )
        row = cur.fetchone()
        conn.commit()
        if row:
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('show_url', id=row['id']))
        cur.execute("SELECT id FROM urls WHERE name = %s;", (normalized,))
        existing = cur.fetchone()
        flash('Страница уже существует', 'info')
        return redirect(url_for('show_url', id=existing['id']))
    finally:
        cur.close()
        conn.close()


@app.route('/urls')
def list_urls():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
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
    """)
    urls = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>')
def show_url(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM urls WHERE id = %s;", (id,))
    url = cur.fetchone()
    if not url:
        flash('URL не найден', 'danger')
        cur.close()
        conn.close()
        return redirect(url_for('list_urls'))
    cur.execute(
        "SELECT * FROM url_checks WHERE url_id = %s ORDER BY created_at DESC;",
        (id,)
    )
    checks = cur.fetchall()
    url['checks'] = checks
    cur.close()
    conn.close()
    return render_template('url.html', url=url)


@app.post('/urls/<int:id>/checks')
def add_check(id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM urls WHERE id = %s;", (id,))
    url = cur.fetchone()
    if not url:
        flash("URL не найден", "danger")
        cur.close()
        conn.close()
        return redirect(url_for('list_urls'))
    try:
        result = check_page(url['name'])
        if result is None:
            flash("Произошла ошибка при проверке", "danger")
        else:
            cur.execute(
                """
                INSERT INTO url_checks (url_id, status_code, title, h1, description)
                VALUES (%s, %s, %s, %s, %s);
                """,
                (id, result['status_code'], result['title'], result['h1'], result['description'])
            )
            conn.commit()
            flash("Страница успешно проверена", "success")
    except Exception:
        conn.rollback()
        flash("Произошла ошибка при проверке", "danger")
    finally:
        cur.close()
        conn.close()
    return redirect(url_for('show_url', id=id))
