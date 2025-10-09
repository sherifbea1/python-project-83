import os
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

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
    cur.execute("""
        SELECT
          urls.id,
          urls.name,
          urls.created_at,
          MAX(url_checks.created_at) AS last_check
        FROM urls
        LEFT JOIN url_checks ON urls.id = url_checks.url_id
        GROUP BY urls.id
        ORDER BY urls.id DESC;
    """)
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


# ---------- Добавление новой проверки ----------
@app.post('/urls/<int:id>/checks')
def add_check(id):
    conn = get_conn()
    cur = conn.cursor()

    # Проверяем, что URL существует
    cur.execute("SELECT * FROM urls WHERE id = %s;", (id,))
    url = cur.fetchone()
    if not url:
        flash("URL не найден", "danger")
        cur.close()
        conn.close()
        return redirect(url_for('list_urls'))

    # Создаём запись проверки (только url_id и created_at)
    cur.execute(
        "INSERT INTO url_checks (url_id) VALUES (%s);",
        (id,)
    )
    conn.commit()
    cur.close()
    conn.close()

    flash("Проверка страницы создана", "success")
    return redirect(url_for('show_url', id=id))