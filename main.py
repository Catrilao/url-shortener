from flask import Flask, render_template, request, redirect, abort
from uuid import uuid4
from dotenv import load_dotenv
from validators import url
import os
import redis
import libsql_client

app = Flask(__name__)


load_dotenv()


def redis_connection():
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


def sql_connection():
    try:
        return libsql_client.create_client_sync(
            url=os.getenv("TURSO_URL"),
            auth_token=os.getenv("TURSO_AUTH_TOKEN"),
        )
    except Exception:
        print("Error al conectar a la base de datos SQL")
        return None


r = redis_connection()
client = sql_connection()


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
    original_url = get_url(short_url)

    if original_url is None:
        abort(404)

    return redirect(original_url)


def store_url(short_url, original_url):
    if r is not None:
        r.set(short_url, original_url)

    client.execute(
        "INSERT INTO urls (short_url, original_url) VALUES (?, ?)",
        (short_url, original_url),
    )


def get_url(short_url):
    if r is not None:
        original_url = r.get(short_url)

        if original_url is not None:
            return original_url.decode("utf-8")

    result_set = client.execute(
        "SELECT original_url FROM urls WHERE short_url = ?", (short_url,)
    )

    if len(result_set) > 0:
        return result_set.rows[0][0]

    return None


if __name__ == "__main__":
    app.run(debug=True)
