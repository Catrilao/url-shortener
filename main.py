from flask import Flask, render_template, request, redirect, abort
from uuid import uuid4
from dotenv import load_dotenv
from validators import url
import os
import redis
import sqlite3
import atexit

app = Flask(__name__)


def redis_connection():
    load_dotenv()
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=os.getenv("REDIS_PORT"),
            password=os.getenv("REDIS_PASSWORD"),
        )
        r.ping()
        return r
    except redis.exceptions.ConnectionError:
        print("Error al conectar al servidor Redis")
        return None


def sqlite_connection():
    try:
        conn = sqlite3.connect("urls.db")
        return conn
    except sqlite3.OperationalError:
        print("Error al conectar a la base de datos SQLite")
        return None


r = redis_connection()
conn = sqlite_connection()


if conn is not None:
    conn.execute(
        "CREATE TABLE IF NOT EXISTS urls (short_url TEXT PRIMARY KEY, original_url TEXT)"
    )


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        original_url = request.form.get("url")

        if not url(original_url):
            return "URL invalida", 400

        uuid = str(uuid4().hex[:6])

        while get_url(uuid) is not None:
            uuid = str(uuid4().hex[:6])

        store_url(uuid, original_url)

        short_url = f"http://127.0.0.1:5000/{uuid}"

        return render_template(
            "index.html", original_url=original_url, short_url=short_url
        )

    return render_template("index.html")


@app.route("/<short_url>")
def redirect_to_url(short_url):
    try:
        original_url = get_url(short_url)
        return redirect(original_url)
    except ValueError:
        abort(404)


def store_url(short_url, original_url):
    if r is not None:
        r.set(short_url, original_url)

    if conn is not None:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO urls (short_url, original_url) VALUES (?, ?)",
            (short_url, original_url),
        )
        conn.commit()


def get_url(short_url):
    if r is not None:
        original_url = r.get(short_url)
    else:
        original_url = None

    if not original_url and conn is not None:
        try:
            cursor = conn.cursor()
            row = cursor.execute(
                "SELECT original_url FROM urls WHERE short_url = ?", (short_url,)
            ).fetchone()
        except sqlite3.OperationalError:
            row = None
    else:
        row = None

    if row is None:
        raise ValueError("URL not found")
    original_url = row[0]

    if original_url:
        return original_url.decode("utf-8")
    else:
        return None


def close_connections():
    if r is not None:
        r.close()
    if conn is not None:
        conn.close()


atexit.register(close_connections)


if __name__ == "__main__":
    app.run(debug=True)
