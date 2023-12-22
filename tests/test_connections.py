from flask import Flask, g
from libsql_client import LibsqlError
from redis.exceptions import ConnectionError
from unittest.mock import patch, Mock, call
import logging
import pytest

from main import ERROR_MESSAGE_REDIS_CONNECTION, ERROR_MESSAGE_SQL_CONNECTION
import main

REDIS_HOST = "localhost"
REDIS_PORT = "6467"
REDIS_PASSWORD = "password"
TURSO_DB_URL = "www.turso.com"
TURSO_DB_AUTH_TOKEN = "1234567890"


@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    app.testing = True
    with app.app_context():
        yield


@pytest.fixture()
def mock_logging_error():
    with patch.object(logging, "error") as mock:
        yield mock
        mock.reset_mock()


@pytest.fixture()
def mock_getenv():
    with patch("os.getenv") as mock:
        yield mock
        mock.reset_mock()


@pytest.fixture()
def mock_redis():
    with patch("redis.Redis") as mock:
        yield mock
        mock.reset_mock()


@pytest.fixture()
def mock_client():
    with patch("libsql_client.create_client_sync") as mock:
        yield mock
        mock.reset_mock()


def test_redis_connection_success(mock_redis, mock_getenv):
    mock_getenv.side_effect = [REDIS_HOST, REDIS_PORT, REDIS_PASSWORD]
    mock_redis.return_value = Mock()
    mock_redis.return_value.ping.return_value = None

    result1 = main.redis_connection()

    assert result1 is not None
    assert isinstance(result1, Mock)

    assert "r" in g
    assert isinstance(g.r, Mock)

    mock_redis.assert_called_once_with(
        host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD
    )

    result2 = main.redis_connection()
    assert result2 == result1

    mock_redis.assert_called_once()

    assert mock_getenv.call_count == 3
    mock_getenv.assert_has_calls(
        [
            call("REDIS_HOST"),
            call("REDIS_PORT"),
            call("REDIS_PASSWORD"),
        ]
    )


def test_redis_connection_logs_error_on_failure(mock_redis, mock_logging_error):
    mock_redis.return_value.ping.side_effect = ConnectionError(
        ERROR_MESSAGE_REDIS_CONNECTION
    )

    result = main.redis_connection()

    assert result is None
    mock_logging_error.assert_called_once_with(ERROR_MESSAGE_REDIS_CONNECTION)


def test_sql_connection_success(mock_client, mock_getenv):
    mock_getenv.side_effect = [TURSO_DB_URL, TURSO_DB_AUTH_TOKEN]
    mock_client.return_value = Mock()

    result1 = main.sql_connection()

    assert result1 is not None
    assert isinstance(result1, Mock)

    assert "client" in g
    assert isinstance(g.client, Mock)

    mock_client.assert_called_once_with(
        url=TURSO_DB_URL, auth_token=TURSO_DB_AUTH_TOKEN
    )

    result2 = main.sql_connection()

    assert result2 == result1
    mock_client.assert_called_once()

    assert mock_getenv.call_count == 2
    mock_getenv.assert_has_calls(
        [
            call("TURSO_DB_URL"),
            call("TURSO_DB_AUTH_TOKEN"),
        ]
    )


def test_sql_connection_logs_error_on_failure(mock_client, mock_logging_error):
    mock_client.side_effect = LibsqlError(ERROR_MESSAGE_SQL_CONNECTION, 500)

    result = main.sql_connection()

    assert result is None
    mock_logging_error.assert_called_once_with(ERROR_MESSAGE_SQL_CONNECTION)
