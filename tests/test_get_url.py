from flask import Flask
from unittest.mock import patch, Mock, MagicMock, call
import logging
import pytest

from app.main import (
    ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION,
    ERROR_MESSAGE_REDIS_GET,
    ERROR_MESSAGE_SQL_GET,
    ERROR_MESSAGE_REDIS_AND_SQL_GET,
)
import app.main as main

SHORT_URL = "123456"
ORIGINAL_URL = "www.google.com"

SQL_QUERY = "SELECT original_url FROM urls WHERE short_url = ? LIMIT 1;"


@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    app.testing = True
    with app.app_context():
        yield


@pytest.fixture
def mock_redis_connection():
    mock_instance = Mock()
    with patch("app.main.redis_connection", return_value=mock_instance) as mock:
        yield mock


@pytest.fixture
def mock_sql_connection():
    mock_instance = Mock()
    with patch("app.main.sql_connection", return_value=mock_instance) as mock:
        yield mock


@pytest.fixture()
def mock_logging_error():
    with patch.object(logging, "error") as mock:
        yield mock
        mock.reset_mock()


def test_get_url_both_redis_and_sql_are_none():
    with pytest.raises(main.RedisAndSqlConnectionError) as e:
        main.get_url(SHORT_URL, None, None)

    assert e.value.args == (ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION, 500)


def test_get_url_redis_success(mock_redis_connection, mock_sql_connection):
    mock_redis_connection.get.return_value = ORIGINAL_URL.encode()

    result = main.get_url(SHORT_URL, mock_redis_connection, mock_sql_connection)

    assert result == ORIGINAL_URL

    mock_redis_connection.get.assert_called_once_with(SHORT_URL)
    mock_sql_connection.execute.assert_not_called()


def test_get_url_redis_fail_sql_available(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.get.side_effect = main.redis.exceptions.ConnectionError()

    mock_result_set = MagicMock()
    mock_result_set.__len__.return_value = 1
    mock_result_set.rows = [(ORIGINAL_URL,)]

    mock_sql_connection.execute.return_value = mock_result_set

    result = main.get_url(SHORT_URL, mock_redis_connection, mock_sql_connection)

    assert result == ORIGINAL_URL

    mock_redis_connection.get.assert_called_once_with(SHORT_URL)
    mock_sql_connection.execute.assert_called_once_with(SQL_QUERY, (SHORT_URL,))

    mock_logging_error.assert_called_once_with(ERROR_MESSAGE_REDIS_GET)


def test_get_url_not_found_on_redis_sql_available(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.get.return_value = None

    mock_result_set = MagicMock()
    mock_result_set.__len__.return_value = 1
    mock_result_set.rows = [(ORIGINAL_URL,)]

    mock_sql_connection.execute.return_value = mock_result_set

    result = main.get_url(SHORT_URL, mock_redis_connection, mock_sql_connection)

    assert result == ORIGINAL_URL

    mock_redis_connection.get.assert_called_once_with(SHORT_URL)
    mock_sql_connection.execute.assert_called_once_with(SQL_QUERY, (SHORT_URL,))

    mock_logging_error.assert_not_called()


def test_get_url_raises_error_when_both_redis_and_sql_fail(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.get.side_effect = main.redis.exceptions.ConnectionError()
    mock_sql_connection.execute.side_effect = main.libsql_client.LibsqlError(
        ERROR_MESSAGE_SQL_GET, 500
    )

    with pytest.raises(main.UrlNotRetrievedError) as e:
        main.get_url(SHORT_URL, mock_redis_connection, mock_sql_connection)

    mock_redis_connection.get.assert_called_once_with(SHORT_URL)
    mock_sql_connection.execute.assert_called_once_with(SQL_QUERY, (SHORT_URL,))

    assert mock_logging_error.call_count == 2
    mock_logging_error.assert_has_calls(
        [
            call(ERROR_MESSAGE_REDIS_GET),
            call(ERROR_MESSAGE_SQL_GET),
        ]
    )

    assert e.value.args == (ERROR_MESSAGE_REDIS_AND_SQL_GET, 500)


def test_get_url_not_found(mock_redis_connection, mock_sql_connection):
    mock_redis_connection.get.return_value = None
    mock_sql_connection.execute.return_value = None

    result = main.get_url(SHORT_URL, mock_redis_connection, mock_sql_connection)

    assert result is None

    mock_redis_connection.get.assert_called_once_with(SHORT_URL)
    mock_sql_connection.execute.assert_called_once_with(SQL_QUERY, (SHORT_URL,))
