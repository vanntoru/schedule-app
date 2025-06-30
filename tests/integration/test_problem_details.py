from schedule_app import create_app

def test_invalid_field_422():
    app = create_app()
    client = app.test_client()

    res = client.post("/api/tasks",
                      json={"title": "t", "duration_min": -5, "priority": "A"},
                      headers={"Content-Type": "application/json"})
    
    assert res.status_code == 422
    body = res.get_json()
    assert body["type"] == "https://schedule.app/errors/invalid-field"
    assert body["title"] == "Validation failed"
    assert body["status"] == 422
    assert body["instance"] == "/api/tasks"
