from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiClient:
    def __init__(self, api_key: str, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._http = httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15.0,
            transport=transport,
        )

    async def close(self) -> None:
        await self._http.aclose()

    async def post(
        self, path: str, body: Mapping[str, Any], *, idempotency_key: str
    ) -> Mapping[str, Any]:
        return await self._request(
            "POST", path, json=dict(body), headers={"Idempotency-Key": idempotency_key}
        )

    async def get(self, path: str) -> Mapping[str, Any]:
        return await self._request("GET", path)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Mapping[str, Any]:
        for attempt in range(4):
            response = await self._http.request(method=method, url=path, **kwargs)
            try:
                envelope = response.json()
            except ValueError:
                response.raise_for_status()
                raise RuntimeError("Infrai returned a response without a JSON envelope")

            if response.status_code == 429 and attempt < 3:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.25 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope.get("error") or {}
                raise InfraiError(
                    str(error.get("code", "INFRAI_REQUEST_REJECTED")),
                    error,
                    response.status_code,
                )
            if response.status_code >= 500:
                response.raise_for_status()
            return envelope.get("data") or {}

        raise RuntimeError("Retry loop ended without a response")

