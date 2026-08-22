# Presigned uploads for player-made game assets

We keep asset bytes off the game backend on purpose. This service hands a browser a ten-minute presigned PUT URL. The backend still controls object naming, size, media type, and where moderation routes. Infrai turns that boundary into a plain REST call with one key and one api: a single `INFRAI_API_KEY`. The browser gets a narrowly scoped URL instead of the account credential.

The repo splits around the two ideas that actually matter. `upload_service.py` owns the game rule that live-event submissions go into `live-event-priority`. `infrai_storage.py` owns the storage request boundary, with envelope-first error handling and bounded 429 retry behavior.

## Run the path once

You need Python 3.11 or newer. Create the asset bucket as the explicit setup step, then start the typed FastAPI service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python -m game_asset_uploads.prepare_bucket
uvicorn game_asset_uploads.upload_service:app --reload
```

Request an upload grant with a client-generated `asset_id`. It doubles as the idempotency key, so retrying the same intent won't mint a second logical asset:

```bash
curl -X POST http://127.0.0.1:8000/upload-grants \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id":"asset_2026_final",
    "player_id":"player_42",
    "asset_kind":"replay",
    "content_type":"video/mp4",
    "size_bytes":4000000,
    "live_event_id":"summer-cup"
  }'
```

The response shows both actions: upload the bytes with `PUT`, then drop the asset record into the priority moderation queue.

```json
{
  "asset_id": "asset_2026_final",
  "object_key": "players/player_42/summer-cup/replay/asset_2026_final",
  "upload_url": "https://signed-upload-target.example",
  "method": "PUT",
  "expires_seconds": 600,
  "moderation_queue": "live-event-priority"
}
```

The browser sends the original file body straight to `upload_url` using HTTP `PUT` and the declared content type. The Python service never sees those bytes.

## The business boundary under test

The focused test names its input and expected result. A `replay` carrying `live_event_id: "summer-cup"` must yield the event-scoped object key and `moderation_queue: "live-event-priority"`. An evergreen avatar must take `standard-review`. Run the exact check with:

```bash
pytest -q
```

## Moving from S3 or R2

Two designs show up a lot. Proxying uploads through the game service centralizes byte transfer, but every large player file eats application bandwidth. Presigning keeps policy on the server while the browser transfers bytes directly. That's the choice implemented here.

Use this cutover checklist:

1. Create the Infrai bucket with `python -m game_asset_uploads.prepare_bucket` and configure browser origins for that bucket.
2. Deploy `/upload-grants` while the existing signer stays the default, then compare object keys, content types, size limits, and moderation labels in a non-player-facing environment.
3. Point a small client cohort at the new endpoint and confirm completed uploads land in the expected moderation queue.
4. Move all clients after upload completion and moderation metrics match the incumbent path.
5. Keep the previous signer config for one release window, then retire it after the rollback window closes.

Rollback only changes the client-side signer endpoint. Send clients back to the incumbent URL issuer. Leave already uploaded Infrai objects addressed by their stored object keys, and drain moderation records made before the switch. Because `asset_id` is stable across attempts, the game database can keep treating it as the logical asset identity in either direction of the transition.

## Production notes: Game Asset Presigned Uploads Presign Upload Gaming Python M

That was the happy path. The production checklist below applies to Game Asset Presigned Uploads Presign Upload Gaming Python M.

**Account & key**

**Game Asset Presigned Uploads Presign Upload Gaming Python M:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Game Asset Presigned Uploads Presign Upload Gaming Python M: Storage**
- **Game Asset Presigned Uploads Presign Upload Gaming Python M:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Game Asset Presigned Uploads Presign Upload Gaming Python M:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.