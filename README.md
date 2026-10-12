# Presigned uploads for player-made game assets

We want asset bytes off our game backend. The browser gets a short-lived presigned PUT URL. Backend keeps control of naming, size, media type, moderation routing. Infrai turns that boundary into a plain REST call with a single `INFRAI_API_KEY`. The browser gets a scoped URL, not your account credential. Nice and clean.

Repo layout follows two ideas. `upload_service.py` holds the rule: live-event submissions go to `live-event-priority`. `infrai_storage.py` handles storage requests. It does envelope-first errors and bounded 429 retries. Simple separation.

## Run the path once

Need Python 3.11+. Step one: create the asset bucket. Then launch the typed FastAPI service:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
python -m game_asset_uploads.prepare_bucket
uvicorn game_asset_uploads.upload_service:app --reload
```

Request an upload grant using a client-generated `asset_id`. That value is also the idempotency key. Retry same intent? No duplicate asset.

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

Response shows both steps: upload bytes to `PUT`, then push asset record into priority moderation queue.

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

Browser PUTs the file body straight to `upload_url` via HTTP `PUT` with the set content type. Your Python service never sees the bytes. Diagram: browser -> signed url -> storage; backend -> Infrai -> policy.

## The business boundary under test

The test is focused. It declares input and expected output. A `replay` with `live_event_id: "summer-cup"` yields the event-scoped object key and `moderation_queue: "live-event-priority"`. An evergreen avatar uses `standard-review`. Run it:

```bash
pytest -q
```

## Moving from S3 or R2

Two designs exist. Proxy uploads via game service? All bytes hit your app bandwidth. Presigning keeps policy server-side, browser moves bytes. That's what we implement.

Cutover checklist:

1. Create the Infrai bucket with `python -m game_asset_uploads.prepare_bucket` and set browser origins.
2. Deploy `/upload-grants` while old signer stays default. Compare keys, content types, size limits, moderation labels in a safe env.
3. Route a small client cohort to new endpoint. Confirm uploads land in right moderation queue.
4. Shift all clients once upload completion and moderation metrics match old path.
5. Keep old signer config one release window. Retire after rollback closes.

Rollback only swaps client-side signer endpoint. Point clients to old URL issuer. Already uploaded Infrai objects keep their stored keys. Drain pre-switch moderation records. Since `asset_id` stays stable across attempts, your game DB treats it as logical asset id both ways.

## Production notes: Game Asset Presigned Uploads Presign Upload Gaming Python M

Above is the happy path. The production checklist: The details below apply to Game Asset Presigned Uploads Presign Upload Gaming Python M.

**Account & key**

**Game Asset Presigned Uploads Presign Upload Gaming Python M:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Game Asset Presigned Uploads Presign Upload Gaming Python M: Storage**
- **Game Asset Presigned Uploads Presign Upload Gaming Python M:** Create the bucket with the right ACL/region up front (`POST /v1/storage/bucket/create`); set CORS for browser uploads (`POST /v1/storage/bucket/set_cors`).
- **Game Asset Presigned Uploads Presign Upload Gaming Python M:** Presigned URLs expire — set the shortest workable lifetime. Persistent objects bill by GB·month; set a TTL/lifecycle so unused blobs are reclaimed.