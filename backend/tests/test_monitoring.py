import logging


def test_health_checks_database(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_request_log_correlates_response_id(client, caplog):
    with caplog.at_level(logging.INFO, logger="app.request"):
        response = client.get("/health")

    request_logs = [record for record in caplog.records if record.name == "app.request"]
    assert len(request_logs) == 1
    request_log = request_logs[0]
    assert response.headers["X-Request-ID"] == request_log.request_id
    assert request_log.method == "GET"
    assert request_log.path == "/health"
    assert request_log.status == 200
    assert request_log.duration_ms >= 0
