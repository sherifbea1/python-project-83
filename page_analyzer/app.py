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


# ---------- Подключение к базе ----------
def get_conn():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


# ---------- Главная страница ----------
@app.route('/')
def index():
    return render_template('index.html')


@app.post('/')
def add_url():
    url = request.form.get('url')

    # Валидация URL
    if not url or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html'), 422

    parsed = urlparse(url)
    if not parsed.scheme:
        parsed = urlparse(f"http://{url}")

    normalized_url = f"{parsed.scheme}://{parsed.netloc}"

    conn = get_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO urls (name) VALUES (%s) ON CONFLICT (name) DO NOTHING RETURNING id",
            (normalized_url,)
        )
        row = cur.fetchone()
        conn.commit()

        if row:
            flash('Страница успешно добавлена', 'success')
            return redirect(url_for('show_url', id=row['id']))
        else:
            cur.execute("SELECT id FROM urls WHERE name = %s;", (normalized_url,))
            existing = cur.fetchone()
            flash('Страница уже существует', 'info')
            return redirect(url_for('show_url', id=existing['id']))
    finally:
        cur.close()
        conn.close()


# ---------- Список всех URL ----------
@app.route('/urls')
def list_urls():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM urls ORDER BY id DESC;")
    urls = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('urls.html', urls=urls)


# ---------- Просмотр конкретного URL и его проверок ----------
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


# ---------- Проверка страницы ----------
def check_page(url):
    try:
        response = requests.get(url, timeout=10)
        status_code = response.status_code
        title = h1 = description = None

        if status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            title_tag = soup.find("title")
            title = title_tag.text.strip() if title_tag else None

            h1_tag = soup.find("h1")
            h1 = h1_tag.text.strip() if h1_tag else None

            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = desc_tag["content"].strip() if desc_tag else None

        return {"status_code": status_code, "title": title, "h1": h1, "description": description}
    except requests.RequestException:
        return {"status_code": None, "title": None, "h1": None, "description": None}


# ---------- Добавление новой проверки ----------
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

    result = check_page(url['name'])

    cur.execute(
        """
        INSERT INTO url_checks (url_id, status_code, title, h1, description)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (id, result['status_code'], result['title'], result['h1'], result['description'])
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Страница успешно проверена", "success")
    return redirect(url_for('show_url', id=id))
