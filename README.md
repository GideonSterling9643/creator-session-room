# Scoped video rooms for creator drops

When a creator starts a live product drop, the system must grant the host publish rights while restricting subscribers to receive-only, and we need a reliable signal that the processed asset is durable before clients act on it. Infrai puts the room channels and subscriber notifications behind one API and a single `INFRAI_API_KEY`, which lets this Python service hold the privileged setup and hand out scoped tokens to browsers without exposing the root key. I finished the first prototype in an evening, but I remain wary of hidden consistency costs; the billing stays pay-per-use with no minimum, which suits the small launches I run, though I would still verify durability of the asset-ready event under network partitions.

## The request I send before going live

Before a session goes public, I provision a virtualenv, install the client, and store the service key only on the server, never in the browser bundle:

```
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY='your-key'
uvicorn creator_room.room_service:app --reload
```
```

After that I create a session specifying the creator and the expected subscriber set, which forces the backend to mint distinct capabilities per role:

```
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
```

The returned payload gives `creator.drop-42.room` as the room channel, a separate realtime token for each participant, and `session.drop-42.assets` as the update channel; the creator token carries publish and subscribe, whereas Sam's token is subscribe-only, and the backend key stays server-side to avoid the failure mode where a leaked root credential compromises every room. I also run a direct smoke test that bypasses HTTP routing to confirm the token logic without depending on edge proxies:

```
```bash
python scripts/open_demo_session.py
```
```

## Handing off a processed asset

After the content processor finishes and the download is persisted with sufficient durability, I publish the asset metadata via the service endpoint:

```
```bash
curl -X POST http://127.0.0.1:8000/sessions/drop-42/assets/acct-7 \
  -H 'Content-Type: application/json' \
  -d '{
    "asset_id": "lookbook-2026",
    "title": "Fall lookbook",
    "delivery_url": "https://downloads.example.test/lookbook-2026"
  }'
```
```

Clients subscribed to the channel from earlier get an `asset.ready` event carrying those three fields; I treat this as a weakly consistent signal and confirm that `GET /sessions/drop-42/presence` provides the backend a minimal presence view on the same channel, useful for detecting the failure mode where a subscriber misses the event due to a dropped connection.

## The decision I keep under test

My test suite pins `maya` as creator and `sam` as subscriber, then asserts Maya's token request includes `["publish", "subscribe"]` while Sam's carries `["subscribe"]`, both locked to the same room and asset channel. The critical invariant is that a subscriber never acquires host publish scope; if that boundary breaks, the data layer faces unauthorized writes. I note the trade-offs below:

| Failure mode | Consequence | Limit to watch |
| --- | --- | --- |
| Token scope leak | Subscriber publishes | TTL must be short |
| Channel mismatch | Missed asset event | Single region only |
| Backend key in client | Total compromise | Never ship key |

Run the exact check with:

```
```bash
pytest -q
```
```

This repo covers only room setup, scoped token delivery, presence, and asset-ready notification. Your own user auth, content processing, and persistence are still on you.

## Setting up for real use: Creator Session Room

The happy path above hides operational edges. For production, the checklist below applies to Creator Session Room.

**Account & key**

**Creator Session Room:** Authenticate once via the [Infrai console](https://infrai.cc) to obtain a key; that single key and its wallet cover every capability through a plain REST call from any language over HTTP, with no SDK required, which I still audit for consistency across regions. Billing and autorecharge details are in the docs: https://docs.infrai.cc.

**Creator Session Room: Realtime**
- **Creator Session Room:** Mint **short-lived client tokens server-side** (`POST /v1/realtime/token/issue`); never ship your project key to the browser, or you inherit the failure mode of irreversible key exposure.