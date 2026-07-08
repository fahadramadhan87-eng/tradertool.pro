"""
Hard safety limits that sit BETWEEN the strategy and the live order call.
A strategy can only ever request a trade; the RiskManager can veto it.
This is intentionally strict and cannot be bypassed by the strategy object.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from config import RiskLimits


@dataclass
class SessionState:
    trades_today: int = 0
    pnl_today: float = 0.0
    open_contracts: int = 0
    last_loss_time: float = 0.0
    day_start_ts: float = field(default_factory=time.time)


class RiskManager:
    def __init__(self, limits: RiskLimits):
        self.limits = limits
        self.state = SessionState()

    def record_trade_opened(self) -> None:
        self.state.trades_today += 1
        self.state.open_contracts += 1

    def record_trade_closed(self, pnl: float) -> None:
        self.state.open_contracts = max(0, self.state.open_contracts - 1)
        self.state.pnl_today += pnl
        if pnl < 0:
            self.state.last_loss_time = time.time()

    def can_trade(self, requested_stake: float) -> tuple[bool, str]:
        s, lim = self.state, self.limits

        if requested_stake > lim.max_stake_per_trade:
            return False, f"stake {requested_stake} exceeds max_stake_per_trade {lim.max_stake_per_trade}"

        if s.open_contracts >= lim.max_open_contracts:
            return False, f"already at max_open_contracts ({lim.max_open_contracts})"

        if s.trades_today >= lim.max_trades_per_day:
            return False, f"reached max_trades_per_day ({lim.max_trades_per_day})"

        if s.pnl_today <= -abs(lim.max_daily_loss):
            return False, f"max_daily_loss reached ({s.pnl_today:.2f} <= -{lim.max_daily_loss})"

        if s.last_loss_time and (time.time() - s.last_loss_time) < lim.cooldown_seconds_after_loss:
            remaining = lim.cooldown_seconds_after_loss - (time.time() - s.last_loss_time)
            return False, f"cooling down after last loss ({remaining:.0f}s remaining)"

        return True, "ok"
