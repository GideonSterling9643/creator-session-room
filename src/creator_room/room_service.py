import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from .creator_session import AssetReadyRequest, CreatorSessionService, SessionRequest, SessionResult
from .infrai_client import InfraiClient, InfraiError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    client = InfraiClient(os.environ["INFRAI_API_KEY"])
    app.state.sessions = CreatorSessionService(client)
    yield
    await client.close()


app = FastAPI(title="Creator Session Room", lifespan=lifespan)


@app.exception_handler(InfraiError)
async def infrai_error_handler(_request: object, exc: InfraiError) -> JSONResponse:
    status = exc.status_code if 400 <= exc.status_code < 500 else 502
    return JSONResponse(status_code=status, content={"error": exc.detail})


@app.post("/sessions", response_model=SessionResult)
async def open_session(request: SessionRequest) -> SessionResult:
    try:
        return await app.state.sessions.open_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/sessions/{session_id}/assets/{account_id}")
async def asset_ready(session_id: str, account_id: str, asset: AssetReadyRequest) -> dict:
    return await app.state.sessions.publish_asset_ready(session_id, account_id, asset)


@app.get("/sessions/{session_id}/presence")
async def session_presence(session_id: str) -> dict:
    return await app.state.sessions.presence(session_id)

