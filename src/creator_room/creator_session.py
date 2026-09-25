from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import quote

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from .infrai_client import InfraiClient


class Participant(BaseModel):
    identity: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    role: Literal["creator", "subscriber"]


class SessionRequest(BaseModel):
    session_id: str = Field(min_length=1)
    creator: Participant
    subscribers: list[Participant] = Field(default_factory=list, max_length=24)


class SessionAccess(BaseModel):
    identity: str
    role: Literal["creator", "subscriber"]
    token: str


class SessionResult(BaseModel):
    room: str
    update_channel: str
    access: list[SessionAccess]


class AssetReadyRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    delivery_url: str


class CreatorSessionService:
    def __init__(self, client: "InfraiClient") -> None:
        self.client = client

    async def open_session(self, request: SessionRequest) -> SessionResult:
        if request.creator.role != "creator":
            raise ValueError("creator must use the creator role")
        if any(person.role != "subscriber" for person in request.subscribers):
            raise ValueError("subscriber entries must use the subscriber role")

        room_name = f"creator.{request.session_id}.room"
        channel = f"session.{request.session_id}.assets"
        await self.client.post(
            "/v1/realtime/channel/create",
            {"channel": room_name, "type": "presence", "vendor": "auto"},
            idempotency_key=f"session:{request.session_id}:room",
        )
        await self.client.post(
            "/v1/realtime/channel/create",
            {"channel": channel, "type": "presence", "vendor": "auto"},
            idempotency_key=f"session:{request.session_id}:channel",
        )

        participants = [request.creator, *request.subscribers]
        access: list[SessionAccess] = []
        for person in participants:
            capabilities = ["subscribe"]
            if person.role == "creator":
                capabilities.insert(0, "publish")
            token_data = await self.client.post(
                "/v1/realtime/token/issue",
                {
                    "client_id": person.identity,
                    "channels": [room_name, channel],
                    "capabilities": capabilities,
                    "ttl_seconds": 3600,
                },
                idempotency_key=f"session:{request.session_id}:token:{person.identity}",
            )
            access.append(
                SessionAccess(
                    identity=person.identity,
                    role=person.role,
                    token=str(token_data["token"]),
                )
            )

        return SessionResult(
            room=room_name,
            update_channel=channel,
            access=access,
        )

    async def publish_asset_ready(
        self, session_id: str, account_id: str, asset: AssetReadyRequest
    ) -> dict[str, Any]:
        channel = f"session.{session_id}.assets"
        data = await self.client.post(
            "/v1/realtime/publish",
            {
                "channel": channel,
                "event": "asset.ready",
                "data": asset.model_dump(),
                "account_id": account_id,
            },
            idempotency_key=f"session:{session_id}:asset:{asset.asset_id}",
        )
        return dict(data)

    async def presence(self, session_id: str) -> dict[str, Any]:
        channel = quote(f"session.{session_id}.assets", safe="")
        return dict(await self.client.get(f"/v1/realtime/presence/get/{channel}"))
