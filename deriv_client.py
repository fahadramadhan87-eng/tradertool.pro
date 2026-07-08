"""
Thin async wrapper around the Deriv WebSocket API.

NOTE ON API STABILITY: Deriv has published a newer REST+WebSocket flow
(OTP-based, at developers.deriv.com) alongside the long-standing WebSocket
flow used here (token sent directly in an `authorize` request to
wss://ws.derivws.com/websockets/v3). This client uses the latter because
it's what every current third-party library (python-deriv-api, deriv-api
JS) still targets. If Deriv fully retires it, re-point `connect()` at the
new OTP endpoint described at https://developers.deriv.com/docs/intro/api-overview/.
Always sanity-check field names against the live schemas here before
trading real money: https://github.com/deriv-com/deriv-api-schemas

This module deliberately stays low-level (raw request/response dicts)
rather than hiding the wire format, so you can always see exactly what
is being sent to your account.
"""
from __future__ import annotations

import asyncio
import itertools
import json
import logging
from typing import Any, AsyncIterator, Optional

import websockets

logger = logging.getLogger("deriv_client")


class DerivAPIError(Exception):
    def __init__(self, error: dict):
        self.code = error.get("code")
        self.message = error.get("message")
        super().__init__(f"{self.code}: {self.message}")


class DerivClient:
    def __init__(self, ws_url: str, api_token: Optional[str] = None):
        self.ws_url = ws_url
        self.api_token = api_token
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._req_id = itertools.count(1)
        self._pending: dict[int, asyncio.Future] = {}
        self._subscribers: dict[str, list[asyncio.Queue]] = {}
        self._reader_task: Optional[asyncio.Task] = None
        self.account_info: dict = {}

    # -- connection lifecycle -------------------------------------------------
    async def connect(self) -> None:
        self._ws = await websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10)
        self._reader_task = asyncio.create_task(self._reader_loop())
        if self.api_token:
            await self.authorize(self.api_token)

    async def close(self) -> None:
        if self._reader_task:
            self._reader_task.cancel()
        if self._ws:
            await self._ws.close()

    async def __aenter__(self) -> "DerivClient":
        await self.connect()
        return self

    async def __aexit__(self, *exc) -> None:
        await self.close()

    # -- core request/response -------------------------------------------------
    async def _reader_loop(self) -> None:
        assert self._ws is not None
        async for raw in self._ws:
            msg = json.loads(raw)
            req_id = msg.get("req_id")
            msg_type = msg.get("msg_type")

            if msg.get("error"):
                fut = self._pending.pop(req_id, None)
                if fut and not fut.done():
                    fut.set_exception(DerivAPIError(msg["error"]))
                    continue
                logger.warning("Unhandled API error: %s", msg["error"])
                continue

            if req_id is not None and req_id in self._pending:
                fut = self._pending.pop(req_id)
                if not fut.done():
                    fut.set_result(msg)

            # fan out to any streaming subscribers (ticks, proposal_open_contract, balance...)
            if msg_type in self._subscribers:
                for q in self._subscribers[msg_type]:
                    q.put_nowait(msg)

    async def request(self, payload: dict, timeout: float = 15.0) -> dict:
        if self._ws is None:
            raise RuntimeError("Not connected. Call connect() first.")
        req_id = next(self._req_id)
        payload = {**payload, "req_id": req_id}
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[req_id] = fut
        await self._ws.send(json.dumps(payload))
        return await asyncio.wait_for(fut, timeout=timeout)

    async def subscribe(self, payload: dict) -> AsyncIterator[dict]:
        """Yields every message of this msg_type, including the first response."""
        msg_type = payload.get(list(payload.keys())[0]) and list(payload.keys())[0]
        # msg_type in Deriv responses matches the request key, e.g. "ticks", "proposal_open_contract"
        key = [k for k in payload if k not in ("subscribe", "req_id")][0]
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(key, []).append(q)
        first = await self.request({**payload, "subscribe": 1})
        yield first
        while True:
            yield await q.get()

    # -- account -------------------------------------------------------------
    async def authorize(self, token: str) -> dict:
        resp = await self.request({"authorize": token})
        self.account_info = resp.get("authorize", {})
        return self.account_info

    async def balance(self) -> dict:
        return await self.request({"balance": 1})

    async def portfolio(self) -> dict:
        return await self.request({"portfolio": 1})

    async def profit_table(self, limit: int = 50) -> dict:
        return await self.request({"profit_table": 1, "limit": limit, "sort": "DESC"})

    async def statement(self, limit: int = 50) -> dict:
        return await self.request({"statement": 1, "limit": limit})

    # -- market data -----------------------------------------------------------
    async def tick_history(self, symbol: str, count: int = 1000) -> dict:
        return await self.request(
            {"ticks_history": symbol, "count": count, "end": "latest", "style": "ticks"}
        )

    async def candles_history(self, symbol: str, count: int = 500, granularity: int = 60) -> dict:
        return await self.request(
            {
                "ticks_history": symbol,
                "count": count,
                "end": "latest",
                "style": "candles",
                "granularity": granularity,
            }
        )

    async def active_symbols(self) -> dict:
        return await self.request({"active_symbols": "brief"})

    # -- trading ---------------------------------------------------------------
    async def accumulator_proposal(
        self, symbol: str, stake: float, growth_rate: float, currency: str = "USD",
        take_profit: Optional[float] = None, limit_order: Optional[dict] = None,
    ) -> dict:
        payload = {
            "proposal": 1,
            "contract_type": "ACCU",
            "symbol": symbol,
            "amount": stake,
            "basis": "stake",
            "currency": currency,
            "growth_rate": growth_rate,
        }
        if take_profit is not None:
            payload["limit_order"] = {"take_profit": take_profit}
        elif limit_order:
            payload["limit_order"] = limit_order
        return await self.request(payload)

    async def buy(self, proposal_id: str, price: float) -> dict:
        return await self.request({"buy": proposal_id, "price": price})

    async def sell(self, contract_id: int, price: float = 0) -> dict:
        return await self.request({"sell": contract_id, "price": price})

    async def open_contract_stream(self, contract_id: int) -> AsyncIterator[dict]:
        async for msg in self.subscribe({"proposal_open_contract": 1, "contract_id": contract_id}):
            yield msg
