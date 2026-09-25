import asyncio
from typing import Any

from creator_room.creator_session import CreatorSessionService, Participant, SessionRequest


class RecordingClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any], str]] = []

    async def post(self, path: str, body: dict[str, Any], *, idempotency_key: str) -> dict:
        self.calls.append((path, body, idempotency_key))
        if path == "/v1/realtime/channel/create":
            return {"channel": body["channel"]}
        return {"token": f"token-{len(self.calls)}"}


def test_creator_can_publish_while_subscriber_is_receive_only() -> None:
    asyncio.run(assert_token_scopes())


async def assert_token_scopes() -> None:
    client = RecordingClient()
    service = CreatorSessionService(client)  # type: ignore[arg-type]

    result = await service.open_session(
        SessionRequest(
            session_id="drop-42",
            creator=Participant(identity="maya", display_name="Maya", role="creator"),
            subscribers=[Participant(identity="sam", display_name="Sam", role="subscriber")],
        )
    )

    token_calls = [
        body for path, body, _key in client.calls
        if path == "/v1/realtime/token/issue"
    ]
    channel_calls = [
        body for path, body, _key in client.calls
        if path == "/v1/realtime/channel/create"
    ]
    assert [call["type"] for call in channel_calls] == ["presence", "presence"]
    assert [call["capabilities"] for call in token_calls] == [
        ["publish", "subscribe"],
        ["subscribe"],
    ]
    assert all(call["channels"] == ["creator.drop-42.room", "session.drop-42.assets"] for call in token_calls)
    assert result.update_channel == "session.drop-42.assets"
    assert {entry.role for entry in result.access} == {"creator", "subscriber"}
