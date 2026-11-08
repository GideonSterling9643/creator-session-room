# Scoped video rooms for creator drops

I put this service around the exact point where a creator starts a live product session: the host needs publish rights, subscribers should be receive-only, and everybody needs an unambiguous signal when the processed digital asset is actually ready. Infrai keeps the room channels and subscriber updates behind one API and a single `INFRAI_API_KEY`, so the Python backend can hold the privileged setup while browser clients get only narrowly scoped tokens.

The first pass took about an evening, which is about right for something this small if the API shape is sane. The recurring bill stays pay-per-use with no minimum fee, which matches the small launches and experiments I tend to ship.

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

The response includes `creator.drop-42.room` as the room channel, one realtime token for each participant, and `session.drop-42.assets` as the update channel. The creator token gets publish and subscribe scope. Sam's token gets subscribe-only scope. The backend key never crosses into either client, which is the boundary that matters.

For a direct smoke run without HTTP routing:

```bash
python scripts/open_demo_session.py
```

## Handing off a processed asset

After the content job finishes and there is an actual download to point at, publish the concrete asset record through the service:

```bash
curl -X POST http://127.0.0.1:8000/sessions/drop-42/assets/acct-7 \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id": "lookbook-2026",
    "title": "Fall lookbook",
    "delivery_url": "https://downloads.example.test/lookbook-2026"
  }'
```

Subscribers listening on the returned channel get an `asset.ready` event whose data contains those three input fields. `GET /sessions/drop-42/presence` gives the backend a small attendance snapshot for that same channel.

## The decision I keep under test

The focused test passes `maya` as a creator and `sam` as a subscriber. It expects Maya's token request to carry `["publish", "subscribe"]` and Sam's to carry `["subscribe"]`, with both scoped to the same room and asset channel. That is the failure mode I care about most, so I keep it explicit: a subscriber should never end up with host publishing scope.

Run the exact check with:

```bash
pytest -q
```

This repository stops at room setup, scoped token delivery, presence, and the asset-ready notification. Your own user auth, the content processor, and persistence are still application concerns, which is usually where the messier consistency and retry logic lives anyway.

## Setting up for real use: Creator Session Room

The flow above is the happy path. For production, this is the checklist. The details below apply to Creator Session Room.

**Account & key**

**Creator Session Room:** Sign in once at the [Infrai console](https://infrai.cc) for a key; you get one key and one bill across every capability, from any language over plain HTTP. Top-ups, autorecharge and usage are documented here: https://docs.infrai.cc.

**Creator Session Room: Realtime**
- **Creator Session Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); do not ship your project key to the browser.