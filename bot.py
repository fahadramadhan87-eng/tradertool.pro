"""
Bot engine: subscribes to ticks, asks a Strategy for a decision, checks it
against the RiskManager, and (only in live mode) places the trade.

Safety defaults:
  - dry_run=True by default. In dry-run, decisions and risk checks all run
    normally but no `buy` call is ever sent -- it just logs what it would
    have done.
  - To actually place trades you must pass dry_run=False AND the account
    authorized by your token must be the one you intend (check
    client.account_info['is_virtual'] -- 1 means demo, 0 means real money).
  - This bot trades ONE symbol/strategy at a time by design, to keep risk
    legible. Run multiple instances if you want more.
"""
from __future__ import annotations

import asyncio
import logging
import time

from accumulator import payout_after_ticks
from deriv_client import DerivClient
from risk_manager import RiskManager
from strategy import MarketState, Strategy

logger = logging.getLogger("bot")


class AccumulatorBot:
    def __init__(
        self,
        client: DerivClient,
        strategy: Strategy,
        risk_manager: RiskManager,
        symbol: str,
        price_window: int = 100,
        dry_run: bool = True,
    ):
        self.client = client
        self.strategy = strategy
        self.risk = risk_manager
        self.symbol = symbol
        self.price_window = price_window
        self.dry_run = dry_run
        self._prices: list[float] = []
        self._current_contract_id: int | None = None

    async def _refill_price_history(self) -> None:
        hist = await self.client.tick_history(self.symbol, count=self.price_window)
        self._prices = [float(p) for p in hist.get("history", {}).get("prices", [])]

    async def _on_tick(self, quote: float) -> None:
        self._prices.append(quote)
        self._prices = self._prices[-self.price_window:]

        state = MarketState(
            symbol=self.symbol,
            last_prices=list(self._prices),
            open_contract_count=self.risk.state.open_contracts,
            trades_today=self.risk.state.trades_today,
            pnl_today=self.risk.state.pnl_today,
        )
        decision = self.strategy.decide(state)
        if not decision.should_trade:
            return

        ok, reason = self.risk.can_trade(decision.stake)
        if not ok:
            logger.info("Risk manager blocked trade: %s", reason)
            return

        await self._open_trade(decision)

    async def _open_trade(self, decision) -> None:
        proposal_resp = await self.client.accumulator_proposal(
            symbol=self.symbol,
            stake=decision.stake,
            growth_rate=decision.growth_rate,
            take_profit=decision.take_profit,
        )
        proposal = proposal_resp.get("proposal", {})
        proposal_id = proposal.get("id")
        ask_price = proposal.get("ask_price", decision.stake)

        logger.info(
            "Decision: stake=%s growth_rate=%s take_profit=%s reason=%r | proposal ask_price=%s",
            decision.stake, decision.growth_rate, decision.take_profit, decision.reason, ask_price,
        )

        if self.dry_run:
            logger.info("[DRY RUN] would BUY proposal_id=%s at price=%s", proposal_id, ask_price)
            return

        buy_resp = await self.client.buy(proposal_id, ask_price)
        contract_id = buy_resp.get("buy", {}).get("contract_id")
        self._current_contract_id = contract_id
        self.risk.record_trade_opened()
        logger.info("LIVE BUY placed. contract_id=%s", contract_id)
        asyncio.create_task(self._watch_contract(contract_id))

    async def _watch_contract(self, contract_id: int) -> None:
        async for msg in self.client.open_contract_stream(contract_id):
            poc = msg.get("proposal_open_contract", {})
            if poc.get("is_sold"):
                pnl = float(poc.get("profit", 0))
                self.risk.record_trade_closed(pnl)
                logger.info("Contract %s closed. pnl=%+.2f", contract_id, pnl)
                self._current_contract_id = None
                break

    async def run(self) -> None:
        await self._refill_price_history()
        logger.info(
            "Bot starting on %s | dry_run=%s | account=%s (virtual=%s)",
            self.symbol, self.dry_run,
            self.client.account_info.get("loginid"),
            self.client.account_info.get("is_virtual"),
        )
        async for msg in self.client.subscribe({"ticks": self.symbol}):
            tick = msg.get("tick")
            if not tick:
                continue
            await self._on_tick(float(tick["quote"]))
