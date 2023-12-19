from flask import Flask
from unittest.mock import patch, Mock, call
import logging
import pytest

from app.main import (
    ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION,
    ERROR_MESSAGE_REDIS_STORE,
    ERROR_MESSAGE_SQL_STORE,
    ERROR_MESSAGE_REDIS_AND_SQL_STORE,
)
import app.main as main


SHORT_URL = "123456"
ORIGINAL_URL = "https://www.google.com/"

SQL_QUERY = "INSERT INTO urls (short_url, original_url) VALUES (?, ?)"


@pytest.fixture(autouse=True)
def app_context():
    app = Flask(__name__)
    app.testing = True
    with app.app_context():
        yield


@pytest.fixture
def mock_redis_connection():
    with patch("app.main.redis_connection") as mock:
        mock.return_value = Mock()
        yield mock


@pytest.fixture
def mock_sql_connection():
    with patch("app.main.sql_connection") as mock:
        mock.return_value = Mock()
        yield mock


@pytest.fixture(autouse=True)
def mock_logging_error():
    with patch.object(logging, "error") as mock:
        yield mock
        mock.reset_mock()


def test_store_url_success(mock_redis_connection, mock_sql_connection):
    result = main.store_url(
        SHORT_URL, ORIGINAL_URL, mock_redis_connection, mock_sql_connection
    )

    mock_redis_connection.set.assert_called_once_with(SHORT_URL, ORIGINAL_URL)
    mock_sql_connection.execute.assert_called_once_with(
        SQL_QUERY,
        (SHORT_URL, ORIGINAL_URL),
    )

    assert result is None


def test_store_url_both_redis_and_sql_connections_are_none():
    with pytest.raises(main.RedisAndSqlConnectionError) as e:
        main.store_url(SHORT_URL, ORIGINAL_URL, None, None)

    assert e.value.args == (ERROR_MESSAGE_REDIS_AND_SQL_CONNECTION, 500)


def test_store_url_logs_error_on_redis_failure(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.set.side_effect = main.RedisStoreError(
        ERROR_MESSAGE_REDIS_STORE
    )
    mock_sql_connection.execute.side_effect = None

    main.store_url(SHORT_URL, ORIGINAL_URL, mock_redis_connection, mock_sql_connection)

    mock_redis_connection.set.assert_called_once_with(SHORT_URL, ORIGINAL_URL)
    mock_sql_connection.execute.assert_called_once_with(
        SQL_QUERY,
        (SHORT_URL, ORIGINAL_URL),
    )

    mock_logging_error.assert_called_once_with(ERROR_MESSAGE_REDIS_STORE)


def test_store_url_logs_error_on_sql_failure(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.set.side_effect = None
    mock_sql_connection.execute.side_effect = main.SqlStoreError(
        ERROR_MESSAGE_SQL_STORE
    )

    main.store_url(SHORT_URL, ORIGINAL_URL, mock_redis_connection, mock_sql_connection)

    mock_redis_connection.set.assert_called_once_with(SHORT_URL, ORIGINAL_URL)
    mock_sql_connection.execute.assert_called_once_with(
        SQL_QUERY,
        (SHORT_URL, ORIGINAL_URL),
    )

    mock_logging_error.assert_called_once_with(ERROR_MESSAGE_SQL_STORE)


def test_store_url_raises_exception_on_redis_and_sql_failure(
    mock_redis_connection, mock_sql_connection, mock_logging_error
):
    mock_redis_connection.set.side_effect = main.RedisStoreError(
        ERROR_MESSAGE_REDIS_STORE
    )
    mock_sql_connection.execute.side_effect = main.SqlStoreError(
        ERROR_MESSAGE_SQL_STORE
    )

    with pytest.raises(main.UrlNotStoredError) as e:
        main.store_url(
            SHORT_URL, ORIGINAL_URL, mock_redis_connection, mock_sql_connection
        )

        mock_redis_connection.set.assert_called_once_with(SHORT_URL, ORIGINAL_URL)
        mock_sql_connection.execute.assert_called_once_with(
            SQL_QUERY,
            (SHORT_URL, ORIGINAL_URL),
        )

        assert mock_logging_error.call_count == 2
        mock_logging_error.assert_has_calls(
            [
                call(ERROR_MESSAGE_SQL_STORE),
                call(ERROR_MESSAGE_REDIS_STORE),
            ]
        )

    assert e.value.args == (ERROR_MESSAGE_REDIS_AND_SQL_STORE, 500)
