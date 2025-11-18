import os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash,
)
from dotenv import load_dotenv

from .url_normalizer import normalize_url
from .parser import check_page

from .database.url_repository import (
    insert_url,
    get_url_by_name,
    get_url_by_id,
    get_all_urls,
)
from .database.check_repository import (
    insert_check,
    get_checks_for_url,
)

load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default-secret")


@app.route("/")
def index():
    return render_template("index.html")


@app.post("/urls")
def add_url():
    raw_url = request.form.get("url")

    if not raw_url or len(raw_url) > 255:
        flash("Некорректный URL", "danger")
        return render_template("index.html"), 422

    normalized = normalize_url(raw_url)

    if not (normalized.startswith("http://") or normalized.startswith("https://")):
        flash("Некорректный URL", "danger")
        return render_template("index.html"), 422

    new_id = insert_url(normalized)

    if new_id:
        flash("Страница успешно добавлена", "success")
        return redirect(url_for("show_url", id=new_id))

    existing = get_url_by_name(normalized)
    flash("Страница уже существует", "info")
    return redirect(url_for("show_url", id=existing["id"]))


@app.route("/urls")
def list_urls():
    urls = get_all_urls()
    return render_template("urls.html", urls=urls)


@app.route("/urls/<int:id>")
def show_url(id):
    url = get_url_by_id(id)

    if not url:
        flash("URL не найден", "danger")
        return redirect(url_for("list_urls"))

    checks = get_checks_for_url(id)
    url["checks"] = checks

    return render_template("url.html", url=url)


@app.post("/urls/<int:id>/checks")
def add_check(id):
    url = get_url_by_id(id)

    if not url:
        flash("URL не найден", "danger")
        return redirect(url_for("list_urls"))

    result = check_page(url["name"])

    if result is None:
        flash("Произошла ошибка при проверке", "danger")
        return redirect(url_for("show_url", id=id))

    insert_check(
        id,
        result["status_code"],
        result["title"],
        result["h1"],
        result["description"],
    )

    flash("Страница успешно проверена", "success")
    return redirect(url_for("show_url", id=id))
