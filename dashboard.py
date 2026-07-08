"""
Terminal dashboard: balance, open positions, recent trade history.
Refreshes on a timer using `rich`.
"""
from __future__ import annotations

import asyncio

from rich.console import Console
from rich.live import Live
from rich.table import Table

from deriv_client import DerivClient

console = Console()


def _build_table(account_info: dict, balance: dict, portfolio: dict, profit_table: dict) -> Table:
    root = Table.grid(expand=True)

    header = Table(title="Account", show_header=False, expand=True)
    header.add_row("Login ID", str(account_info.get("loginid")))
    header.add_row("Type", "DEMO" if account_info.get("is_virtual") else "REAL MONEY")
    header.add_row("Currency", str(account_info.get("currency")))
    bal = balance.get("balance", {})
    header.add_row("Balance", f"{bal.get('balance', '?')} {bal.get('currency', '')}")

    positions = Table(title="Open Positions", expand=True)
    for col in ["Contract ID", "Type", "Symbol", "Buy Price", "Current Value", "P/L"]:
        positions.add_column(col)
    for c in portfolio.get("portfolio", {}).get("contracts", []):
        pnl = None
        try:
            pnl = float(c.get("bid_price", 0)) - float(c.get("buy_price", 0))
        except (TypeError, ValueError):
            pass
        positions.add_row(
            str(c.get("contract_id")),
            str(c.get("contract_type")),
            str(c.get("symbol")),
            str(c.get("buy_price")),
            str(c.get("bid_price")),
            f"{pnl:+.2f}" if pnl is not None else "?",
        )
    if not portfolio.get("portfolio", {}).get("contracts"):
        positions.add_row("-", "-", "-", "-", "-", "-")

    history = Table(title="Recent Closed Trades", expand=True)
    for col in ["Contract ID", "Symbol", "Buy Price", "Sell Price", "P/L"]:
        history.add_column(col)
    for t in profit_table.get("profit_table", {}).get("transactions", [])[:10]:
        try:
            pnl = float(t.get("sell_price", 0)) - float(t.get("buy_price", 0))
            pnl_str = f"{pnl:+.2f}"
        except (TypeError, ValueError):
            pnl_str = "?"
        history.add_row(
            str(t.get("contract_id")),
            str(t.get("shortcode", "")).split("_")[0],
            str(t.get("buy_price")),
            str(t.get("sell_price")),
            pnl_str,
        )

    root.add_row(header)
    root.add_row(positions)
    root.add_row(history)
    return root


async def run_dashboard(client: DerivClient, refresh_seconds: float = 5.0) -> None:
    with Live(console=console, refresh_per_second=1) as live:
        while True:
            balance, portfolio, profit_table = await asyncio.gather(
                client.balance(), client.portfolio(), client.profit_table()
            )
            live.update(_build_table(client.account_info, balance, portfolio, profit_table))
            await asyncio.sleep(refresh_seconds)
