"""
Configuration for the Deriv toolkit.

All secrets are loaded from environment variables (or a local .env file via
python-dotenv) -- NEVER hardcode your API token in source code.

Get an API token at: https://app.deriv.com/account/api-token
  - For analysis / dashboard only: use a "Read" scoped token.
  - For the bot to place trades: the token also needs "Trade" scope.
  - Strongly recommended: create the token on a DEMO account (a "VRTC..."
    account) while you test. Only switch to a real-money token once you
    fully understand and accept the risk.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv is optional; env vars can be set another way


@dataclass
class RiskLimits:
    """Hard safety limits enforced by the bot regardless of strategy output."""
    max_stake_per_trade: float = float(os.getenv("MAX_STAKE_PER_TRADE", "1.0"))
    max_daily_loss: float = float(os.getenv("MAX_DAILY_LOSS", "10.0"))
    max_open_contracts: int = int(os.getenv("MAX_OPEN_CONTRACTS", "1"))
    max_trades_per_day: int = int(os.getenv("MAX_TRADES_PER_DAY", "20"))
    cooldown_seconds_after_loss: int = int(os.getenv("COOLDOWN_SECONDS_AFTER_LOSS", "30"))


@dataclass
class DerivConfig:
    api_token: str = field(default_factory=lambda: os.getenv("DERIV_API_TOKEN", ""))
    # 1089 is Deriv's public demo app_id, fine for personal/non-commercial use.
    # Register your own at https://api.deriv.com/dashboard if you plan to
    # distribute this to other people.
    app_id: str = field(default_factory=lambda: os.getenv("DERIV_APP_ID", "1089"))
    endpoint: str = field(
        default_factory=lambda: os.getenv("DERIV_WS_ENDPOINT", "wss://ws.derivws.com/websockets/v3")
    )
    is_demo: bool = field(default_factory=lambda: os.getenv("DERIV_IS_DEMO", "true").lower() == "true")
    risk: RiskLimits = field(default_factory=RiskLimits)

    @property
    def ws_url(self) -> str:
        return f"{self.endpoint}?app_id={self.app_id}"

    def validate(self) -> None:
        if not self.api_token:
            raise ValueError(
                "DERIV_API_TOKEN is not set. Create one at "
                "https://app.deriv.com/account/api-token and set it as an "
                "environment variable (or put it in a .env file)."
            )
