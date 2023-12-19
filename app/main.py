from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, g
from urllib.parse import urlparse
from uuid import uuid4
import libsql_client
import logging
import os
import redis

ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION = "Error al conectar a Redis y Turso"
ERROR_MESSAGE_REDIS_CONNECTION = "Error al conectar al servidor Redis"
ERROR_MESSAGE_SQL_CONNECTION = "Error al conectar a la base de datos SQL"

ERROR_MESSAGE_REDIS_GET = "Error al obtener url en Redis"
ERROR_MESSAGE_SQL_GET = "Error al obtener url en Turso"
ERROR_MESSAGE_REDIS_AND_SQL_GET = "Error al obtener la url"

ERROR_MESSAGE_REDIS_STORE = "Error al guardar la url en Redis"
ERROR_MESSAGE_SQL_STORE = "Error al guardar la url en Turso"
ERROR_MESSAGE_REDIS_AND_SQL_STORE = "Error al guardar la url en Redis y Turso"

app = Flask(__name__)


load_dotenv()


def redis_connection():
    if "r" not in g:
        try:
            g.r = redis.Redis(
                host=os.getenv("REDIS_HOST"),
                port=os.getenv("REDIS_PORT"),
                password=os.getenv("REDIS_PASSWORD"),
            )
            g.r.ping()
        except redis.exceptions.ConnectionError:
            logging.error(ERROR_MESSAGE_REDIS_CONNECTION)
            g.r = None
            return None
    return g.r


def sql_connection():
    if "client" not in g:
        try:
            g.client = libsql_client.create_client_sync(
                url=os.getenv("TURSO_URL"),
                auth_token=os.getenv("TURSO_AUTH_TOKEN"),
            )
        except libsql_client.LibsqlError:
            logging.error(ERROR_MESSAGE_SQL_CONNECTION)
            g.client = None
            return None
    return g.client


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        original_url = request.form.get("url")

        if not is_valid_url(original_url):
            return "URL invalida", 400

        uuid = str(uuid4().hex[:6])

        while get_url(uuid) is not None:
            uuid = str(uuid4().hex[:6])

        store_url(uuid, original_url, redis_connection(), sql_connection())

        short_url = f"http://127.0.0.1:5000/{uuid}"

        return render_template(
            "index.html",
            original_url=original_url,
            short_url=short_url,
        )

    return render_template("index.html")


@app.route("/<short_url>")
def redirect_to_url(short_url):
    original_url = get_url(short_url)

    if original_url is None:
        return render_template("index.html")

    return redirect(original_url)


@app.errorhandler(Exception)
def handle_exception(e):
    logging.error(f"Ha ocurrido un error: {e}")
    return "Ha ocurrido un error. Intente de nuevo", 500


def store_url(short_url, original_url, redis_conn, sql_conn):
    if redis_conn is None and sql_conn is None:
        raise RedisAndSqlConnectionError(ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION, 500)

    redis_error = None
    sql_error = None

    try:
        if redis_conn is not None:
            redis_conn.set(short_url, original_url)
    except RedisStoreError:
        redis_error = RedisStoreError
        logging.error(ERROR_MESSAGE_REDIS_STORE)

    try:
        if sql_conn is not None:
            sql_conn.execute(
                "INSERT INTO urls (short_url, original_url) VALUES (?, ?)",
                (short_url, original_url),
            )
    except SqlStoreError:
        sql_error = SqlStoreError
        logging.error(ERROR_MESSAGE_SQL_STORE)

    if redis_error and sql_error:
        raise UrlNotStoredError(ERROR_MESSAGE_REDIS_AND_SQL_STORE, 500)


def get_url(short_url, redis_conn, sql_conn):
    if redis_conn is None and sql_conn is None:
        raise RedisAndSqlConnectionError(ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION, 500)

    redis_error = None
    sql_error = None

    # Buscar en Redis
    try:
        if redis_conn is not None:
            original_url = redis_conn.get(short_url)

            if original_url is not None:
                return original_url.decode("utf-8")
    except redis.exceptions.ConnectionError:
        logging.error(ERROR_MESSAGE_REDIS_GET)
        redis_error = True

    # Buscar en Turso
    try:
        if sql_conn is not None:
            result_set = sql_conn.execute(
                "SELECT original_url FROM urls WHERE short_url = ? LIMIT 1;",
                (short_url,),
            )

            if result_set is not None and len(result_set) > 0:
                return result_set.rows[0][0]
    except libsql_client.LibsqlError:
        logging.error(ERROR_MESSAGE_SQL_GET)
        sql_error = True

    if redis_error and sql_error:
        raise UrlNotRetrievedError(ERROR_MESSAGE_REDIS_AND_SQL_GET, 500)

    # No se encontro la url
    return None


def is_valid_url(url):
    try:
        result = urlparse(url)
        if not result.scheme:
            result = urlparse(f"http://{url}")
        return all([result.scheme, result.netloc, result.scheme in ["http", "https"]])
    except ValueError:
        return False


class RedisStoreError(Exception):
    pass


class SqlStoreError(Exception):
    pass


class RedisAndSqlConnectionError(Exception):
    pass


class UrlNotStoredError(Exception):
    pass


class UrlNotRetrievedError(Exception):
    pass


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
