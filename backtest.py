"""
Run an accumulator backtest against real historical tick data pulled from
Deriv, across a grid of target_ticks, so you can see how win-rate and
average P/L trade off. See accumulator.py's module docstring for the
mechanics and caveats -- this describes the past, it does not predict
the future.
"""
from __future__ import annotations

from accumulator import backtest_fixed_target, fetch_barrier_pct
from deriv_client import DerivClient


async def run_backtest_grid(
    client: DerivClient,
    symbol: str,
    stake: float,
    growth_rate: float,
    tick_count: int = 5000,
    targets: list[int] | None = None,
) -> list:
    targets = targets or [5, 10, 15, 20, 30, 50]

    hist = await client.tick_history(symbol, count=tick_count)
    prices = [float(p) for p in hist.get("history", {}).get("prices", [])]
    if len(prices) < 100:
        raise ValueError(f"Only got {len(prices)} historical prices, need more for a meaningful backtest")

    barrier_pct = await fetch_barrier_pct(client, symbol, stake, growth_rate)

    results = []
    for target in targets:
        results.append(backtest_fixed_target(prices, barrier_pct, stake, growth_rate, target))
    return results
