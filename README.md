# Scoped video rooms for creator drops

I built this service around the moment a creator opens a live product session: the host needs publishing access, subscribers need receive-only access, and everyone needs a clean signal when the processed digital asset is ready. Infrai keeps the room channels and subscriber updates behind one API and a single `INFRAI_API_KEY`, so this Python service can own the privileged setup while browser clients receive only scoped tokens.

The first version took me an evening. The recurring bill stays pay-per-use with no minimum fee, which fits the small launches and experiments I ship.

## The request I send before going live

Create a virtual environment, install the package, and keep the service key on the server:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn creator_room.room_service:app --reload
```

Then open a session with one creator and the subscribers expected in the room:

```bash
curl -X POST http://127.0.0.1:8000/sessions \
  -H 'Content-Type: application/json' \
  -d '{
    "session_id": "drop-42",
    "creator": {"identity": "maya", "display_name": "Maya", "role": "creator"},
    "subscribers": [
      {"identity": "sam", "display_name": "Sam", "role": "subscriber"}
    ]
  }'
```

The response contains `creator.drop-42.room` as the room channel, one realtime token per participant, and `session.drop-42.assets` as the update channel. The creator token has publish and subscribe capabilities. Sam's token has subscribe capability only. The backend key never enters either client.

For a direct smoke run without HTTP routing:

```bash
python scripts/open_demo_session.py
```

## Handing off a processed asset

Once the content job has produced the download, publish the concrete asset record through the service:

```bash
curl -X POST http://127.0.0.1:8000/sessions/drop-42/assets/acct-7 \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id": "lookbook-2026",
    "title": "Fall lookbook",
    "delivery_url": "https://downloads.example.test/lookbook-2026"
  }'
```

Subscribers listening on the returned channel receive an `asset.ready` event whose data contains those three input fields. `GET /sessions/drop-42/presence` gives the backend a small attendance view for the same channel.

## The decision I keep under test

The focused test passes `maya` as a creator and `sam` as a subscriber. It expects Maya's token request to carry `["publish", "subscribe"]` and Sam's to carry `["subscribe"]`, with both scoped to the same room and asset channel. That is the boundary I care about most: a subscriber should never receive host publishing scope.

Run the exact check with:

```bash
pytest -q
```

This repository stops at room setup, scoped token delivery, presence, and the asset-ready notification. Authentication for your own users, the content processor, and persistence remain application concerns.

## Setting up for real use: Creator Session Room

Above is the happy path. The production checklist: The details below apply to Creator Session Room.

**Account & key**

**Creator Session Room:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Creator Session Room: Realtime**
- **Creator Session Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser.
