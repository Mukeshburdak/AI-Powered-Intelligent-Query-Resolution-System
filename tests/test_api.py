
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.database.connection import SessionLocal
from backend.database.models import User
from backend.security.auth import create_access_token

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "API is running",
    }


def test_query_endpoint_returns_baseline_answer():
    db = SessionLocal()

    try:
        user = (
            db.query(User)
            .filter(User.is_active.is_(True))
            .first()
        )

        assert user is not None, "An active test user is required."
        user_id = user.id

    finally:
        db.close()

    token = create_access_token(user_id)

    headers = {
        "Authorization": f"Bearer {token}"
    }

    with patch(
        "backend.api.routes_query.answer_query",
        return_value={"answer": "Test answer"},
    ) as mock_answer:

        response = client.post(
            "/api/query",
            json={"question": "How does this work?"},
            headers=headers,
        )

    assert response.status_code == 200
    assert "answer" in response.json()

    mock_answer.assert_called_once()

    assert mock_answer.call_args.kwargs["user_id"] == user_id
