import asyncio
import os

from creator_room.creator_session import CreatorSessionService, Participant, SessionRequest
from creator_room.infrai_client import InfraiClient


async def main() -> None:
    client = InfraiClient(os.environ["INFRAI_API_KEY"])
    try:
        result = await CreatorSessionService(client).open_session(
            SessionRequest(
                session_id="drop-42",
                creator=Participant(identity="maya", display_name="Maya", role="creator"),
                subscribers=[
                    Participant(identity="sam", display_name="Sam", role="subscriber")
                ],
            )
        )
        print(result.model_dump_json(indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())

