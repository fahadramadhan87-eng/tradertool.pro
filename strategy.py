"""
Strategy interface for the bot.

IMPORTANT: The example strategy below is a template to show you the plumbing
(how to read incoming ticks/state and emit a trade decision) -- it is NOT a
validated or recommended trading strategy, and synthetic indices are
explicitly designed to be unpredictable. Nothing here should be read as
financial advice. Write and backtest (see accumulator.backtest_fixed_target)
your own logic before ever pointing it at a real-money account.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass
class TradeDecision:
    should_trade: bool
    stake: float = 0.0
    growth_rate: float = 0.03
    take_profit: Optional[float] = None
    reason: str = ""


@dataclass
class MarketState:
    symbol: str
    last_prices: list[float]  # most recent N ticks, oldest first
    open_contract_count: int
    trades_today: int
    pnl_today: float


class Strategy(Protocol):
    def decide(self, state: MarketState) -> TradeDecision:
        ...


class FixedStakeExampleStrategy:
    """Template strategy: only trades if it hasn't already got an open
    contract and hasn't hit its own daily trade cap. Always proposes the
    same stake/growth_rate/take_profit. Replace `decide()` with your own
    (backtested) entry/exit logic -- this class exists to show the required
    method signature, not to suggest this is a good trading rule.
    """

    def __init__(self, stake: float = 1.0, growth_rate: float = 0.02,
                 take_profit: Optional[float] = None, max_trades_per_day: int = 5):
        self.stake = stake
        self.growth_rate = growth_rate
        self.take_profit = take_profit
        self.max_trades_per_day = max_trades_per_day

    def decide(self, state: MarketState) -> TradeDecision:
        if state.open_contract_count > 0:
            return TradeDecision(should_trade=False, reason="already have an open contract")
        if state.trades_today >= self.max_trades_per_day:
            return TradeDecision(should_trade=False, reason="hit max_trades_per_day")
        return TradeDecision(
            should_trade=True,
            stake=self.stake,
            growth_rate=self.growth_rate,
            take_profit=self.take_profit,
            reason="template strategy: no open contract, under daily trade cap",
        )
