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


def test_invalid_block_row():
    app = create_app()

    from flask import Blueprint
    from schedule_app.errors import InvalidBlockRow

    bp = Blueprint("testbp", __name__)

    @bp.get("/raise-block")
    def raise_block():  # pragma: no cover - simple test route
        raise InvalidBlockRow()

    app.register_blueprint(bp)
    client = app.test_client()

    res = client.get("/raise-block")

    assert res.status_code == 422
    body = res.get_json()
    assert body["type"] == "https://schedule.app/errors/invalid-block-row"
    assert body["title"] == "Block row validation failed"
    assert body["status"] == 422
