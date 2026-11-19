
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient

from backend.main import app
from backend.api.routes_whatsapp import get_current_user


client = TestClient(app)


def fake_user(user_id):
    user = MagicMock()
    user.id = user_id
    return user


def test_owner_can_queue_retry():
    app.dependency_overrides[get_current_user] = lambda: fake_user(3)

    with patch(
        "backend.api.routes_whatsapp.get_whatsapp_retry_owner",
        return_value=3,
    ), patch(
        "backend.api.routes_whatsapp.retry_whatsapp_message"
    ) as retry_worker:

        response = client.post(
            "/api/whatsapp/retry/wamid.test_owner"
        )

        assert response.status_code == 202
        assert response.json()["status"] == "queued"
        retry_worker.assert_called_once_with("wamid.test_owner")

    app.dependency_overrides.clear()


def test_other_user_cannot_retry():
    app.dependency_overrides[get_current_user] = lambda: fake_user(4)

    with patch(
        "backend.api.routes_whatsapp.get_whatsapp_retry_owner",
        return_value=3,
    ), patch(
        "backend.api.routes_whatsapp.retry_whatsapp_message"
    ) as retry_worker:

        response = client.post(
            "/api/whatsapp/retry/wamid.test_owner"
        )

        assert response.status_code == 403
        retry_worker.assert_not_called()

    app.dependency_overrides.clear()


def test_nonexistent_retry_message():
    app.dependency_overrides[get_current_user] = lambda: fake_user(3)

    with patch(
        "backend.api.routes_whatsapp.get_whatsapp_retry_owner",
        return_value=None,
    ), patch(
        "backend.api.routes_whatsapp.retry_whatsapp_message"
    ) as retry_worker:

        response = client.post(
            "/api/whatsapp/retry/wamid.test_missing"
        )

        assert response.status_code == 404
        retry_worker.assert_not_called()

    app.dependency_overrides.clear()


if __name__ == "__main__":
    test_owner_can_queue_retry()
    print("Owner retry authorization: PASSED")

    test_other_user_cannot_retry()
    print("Cross-user retry rejection: PASSED")

    test_nonexistent_retry_message()
    print("Nonexistent message rejection: PASSED")

    print("\nALL RETRY ENDPOINT TESTS PASSED.")
