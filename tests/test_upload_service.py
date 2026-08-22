from fastapi.testclient import TestClient

from game_asset_uploads.upload_service import app, get_storage


class RecordingStorage:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def presign_put(self, bucket: str, key: str, **body: object) -> dict[str, str]:
        self.calls.append({"bucket": bucket, "key": key, **body})
        return {"url": "https://uploads.example/signed-target"}


def test_live_event_asset_gets_priority_review_and_scoped_put() -> None:
    storage = RecordingStorage()
    app.dependency_overrides[get_storage] = lambda: storage
    client = TestClient(app)

    response = client.post(
        "/upload-grants",
        json={
            "asset_id": "asset_2026_final",
            "player_id": "player_42",
            "asset_kind": "replay",
            "content_type": "video/mp4",
            "size_bytes": 4_000_000,
            "live_event_id": "summer-cup",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "asset_id": "asset_2026_final",
        "object_key": "players/player_42/summer-cup/replay/asset_2026_final",
        "upload_url": "https://uploads.example/signed-target",
        "method": "PUT",
        "expires_seconds": 600,
        "moderation_queue": "live-event-priority",
    }
    assert storage.calls[0]["idempotency_key"] == "asset_2026_final"
    assert storage.calls[0]["max_bytes"] == 4_000_000
    app.dependency_overrides.clear()


def test_evergreen_asset_uses_standard_review() -> None:
    storage = RecordingStorage()
    app.dependency_overrides[get_storage] = lambda: storage
    client = TestClient(app)

    response = client.post(
        "/upload-grants",
        json={
            "asset_id": "avatar_1234",
            "player_id": "player_42",
            "asset_kind": "avatar",
            "content_type": "image/png",
            "size_bytes": 80_000,
        },
    )

    assert response.status_code == 200
    assert response.json()["moderation_queue"] == "standard-review"
    assert "/evergreen/avatar/" in response.json()["object_key"]
    app.dependency_overrides.clear()

