from __future__ import annotations

import os
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_storage import InfraiError, InfraiStorage

ASSET_BUCKET = os.environ.get("GAME_ASSET_BUCKET", "player-generated-assets")


class UploadRequest(BaseModel):
    asset_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{8,64}$")
    player_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{3,64}$")
    asset_kind: Literal["avatar", "level", "replay"]
    content_type: Literal["image/png", "image/jpeg", "application/json", "video/mp4"]
    size_bytes: int = Field(gt=0, le=25_000_000)
    live_event_id: str | None = Field(default=None, max_length=64)


class UploadGrant(BaseModel):
    asset_id: str
    object_key: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    expires_seconds: int
    moderation_queue: Literal["standard-review", "live-event-priority"]


def moderation_queue(request: UploadRequest) -> Literal["standard-review", "live-event-priority"]:
    return "live-event-priority" if request.live_event_id else "standard-review"


def get_storage() -> InfraiStorage:
    return InfraiStorage()


app = FastAPI(title="Game asset upload grants")


@app.post("/upload-grants", response_model=UploadGrant)
def create_upload_grant(
    request: UploadRequest,
    storage: InfraiStorage = Depends(get_storage),
) -> UploadGrant:
    event_scope = request.live_event_id or "evergreen"
    object_key = (
        f"players/{request.player_id}/{event_scope}/"
        f"{request.asset_kind}/{request.asset_id}"
    )
    try:
        signed = storage.presign_put(
            ASSET_BUCKET,
            object_key,
            content_type=request.content_type,
            max_bytes=request.size_bytes,
            idempotency_key=request.asset_id,
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc.detail.get("message", "request rejected"))},
        ) from exc

    return UploadGrant(
        asset_id=request.asset_id,
        object_key=object_key,
        upload_url=str(signed["url"]),
        expires_seconds=600,
        moderation_queue=moderation_queue(request),
    )

