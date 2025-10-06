import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock


def test_get_status_success(client, mock_supabase, valid_api_key):
    """Test successful status retrieval."""
    status_response = MagicMock()
    status_response.data = [{"count": 1}]
    latest_equity_response = MagicMock()
    latest_equity_response.data = [{"timestamp": datetime.now(timezone.utc).isoformat()}]

    table_mock = mock_supabase.return_value.table.return_value
    table_mock.select.return_value.limit.return_value.execute.return_value = status_response
    table_mock.select.return_value.order.return_value.limit.return_value.execute.return_value = latest_equity_response

    response = client.get("/api/status", headers={"X-API-Key": valid_api_key})

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["api"] == "healthy"
    assert data["status"]["database"] == "healthy"
    assert "system_time" in data
    assert "disclaimer" in data


def test_get_status_database_unhealthy(client, mock_supabase, valid_api_key):
    """Database check failures should mark the database as unhealthy."""
    execute_mock = MagicMock()
    execute_mock.data = [{"timestamp": datetime.now(timezone.utc).isoformat()}]
    query = mock_supabase.return_value.table.return_value.select.return_value
    limit_execute = query.limit.return_value.execute
    limit_execute.side_effect = [Exception("Database error"), execute_mock, execute_mock]

    response = client.get("/api/status", headers={"X-API-Key": valid_api_key})

    assert response.status_code == 200
    data = response.json()
    assert data["status"]["database"] == "unhealthy"
    assert data["status"]["api"] == "healthy"


def test_get_status_invalid_api_key(client, monkeypatch):
    """Invalid API keys should be rejected."""
    monkeypatch.setenv("TEST_MODE", "false")
    monkeypatch.setenv("API_KEY", "expected-key")
    response = client.get("/api/status", headers={"X-API-Key": "invalid"})
    assert response.status_code == 403


def test_get_status_internal_error(client, mock_supabase, valid_api_key):
    """Unexpected errors should surface as 500 responses."""
    mock_supabase.return_value.table.side_effect = Exception("boom")

    response = client.get("/api/status", headers={"X-API-Key": valid_api_key})

    assert response.status_code == 500
    assert "boom" in response.json()["detail"]
