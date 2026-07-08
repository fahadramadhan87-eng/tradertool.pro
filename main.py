"""
CLI entrypoint.

Examples:
  python main.py analyze --symbol R_100 --count 1000
  python main.py dashboard
  python main.py backtest --symbol R_100 --stake 1 --growth-rate 0.03
  python main.py bot --symbol R_100 --stake 1 --growth-rate 0.02          # dry run (default)
  python main.py bot --symbol R_100 --stake 1 --growth-rate 0.02 --live --i-understand-the-risk
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from accumulator import max_ticks_for_cap
from analysis import compute_tick_stats
from backtest import run_backtest_grid
from bot import AccumulatorBot
from config import DerivConfig
from dashboard import run_dashboard
from deriv_client import DerivClient
from risk_manager import RiskManager
from strategy import FixedStakeExampleStrategy

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("main")


async def cmd_analyze(args, cfg: DerivConfig) -> None:
    async with DerivClient(cfg.ws_url, cfg.api_token if args.auth else None) as client:
        hist = await client.tick_history(args.symbol, count=args.count)
        prices = [float(p) for p in hist.get("history", {}).get("prices", [])]
        if not prices:
            print("No price data returned -- check the symbol code, e.g. R_100, R_50, 1HZ100V.")
            return
        stats = compute_tick_stats(args.symbol, prices)
        print(stats.summary())


async def cmd_dashboard(args, cfg: DerivConfig) -> None:
    cfg.validate()
    async with DerivClient(cfg.ws_url, cfg.api_token) as client:
        await run_dashboard(client, refresh_seconds=args.refresh)


async def cmd_backtest(args, cfg: DerivConfig) -> None:
    cfg.validate()
    async with DerivClient(cfg.ws_url, cfg.api_token) as client:
        results = await run_backtest_grid(
            client, args.symbol, args.stake, args.growth_rate,
            tick_count=args.count, targets=args.targets,
        )
        cap_ticks = max_ticks_for_cap(args.stake, args.growth_rate)
        print(f"($10,000 payout cap reached at ~{cap_ticks} surviving ticks for this stake/growth_rate)\n")
        for r in results:
            print(r.summary())
            print()


async def cmd_bot(args, cfg: DerivConfig) -> None:
    cfg.validate()

    live = args.live
    if live and not args.i_understand_the_risk:
        print(
            "Refusing to start in --live mode without --i-understand-the-risk.\n"
            "This will place real trades and can lose real money. Test with "
            "dry-run (the default, omit --live) or a demo-account token first."
        )
        sys.exit(1)

    async with DerivClient(cfg.ws_url, cfg.api_token) as client:
        if live and not client.account_info.get("is_virtual"):
            print(
                f"WARNING: authorized account {client.account_info.get('loginid')} "
                "is a REAL MONEY account and --live is set. Trades placed by this "
                "bot will use real funds."
            )
        elif live:
            print(f"--live set, but authorized account {client.account_info.get('loginid')} is a demo account.")

        strategy = FixedStakeExampleStrategy(
            stake=args.stake, growth_rate=args.growth_rate, take_profit=args.take_profit,
            max_trades_per_day=cfg.risk.max_trades_per_day,
        )
        risk_manager = RiskManager(cfg.risk)
        bot = AccumulatorBot(
            client, strategy, risk_manager, args.symbol,
            dry_run=not live,
        )
        await bot.run()


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Deriv analysis / account / bot toolkit")
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="Pull tick history and print statistics")
    a.add_argument("--symbol", default="R_100", help="e.g. R_100, R_50, 1HZ100V")
    a.add_argument("--count", type=int, default=1000)
    a.add_argument("--auth", action="store_true", help="Authorize with your token (not required for public tick data)")
    a.set_defaults(func=cmd_analyze)

    d = sub.add_parser("dashboard", help="Live-updating account dashboard")
    d.add_argument("--refresh", type=float, default=5.0)
    d.set_defaults(func=cmd_dashboard)

    b = sub.add_parser("backtest", help="Backtest an accumulator target-ticks rule against history")
    b.add_argument("--symbol", default="R_100")
    b.add_argument("--stake", type=float, default=1.0)
    b.add_argument("--growth-rate", type=float, default=0.03, choices=[0.01, 0.02, 0.03, 0.04, 0.05])
    b.add_argument("--count", type=int, default=5000, help="How many historical ticks to pull")
    b.add_argument("--targets", type=int, nargs="+", default=[5, 10, 15, 20, 30, 50])
    b.set_defaults(func=cmd_backtest)

    bot_p = sub.add_parser("bot", help="Run the (dry-run by default) accumulator bot")
    bot_p.add_argument("--symbol", default="R_100")
    bot_p.add_argument("--stake", type=float, default=1.0)
    bot_p.add_argument("--growth-rate", type=float, default=0.02, choices=[0.01, 0.02, 0.03, 0.04, 0.05])
    bot_p.add_argument("--take-profit", type=float, default=None)
    bot_p.add_argument("--live", action="store_true", help="Place real orders instead of dry-run logging")
    bot_p.add_argument("--i-understand-the-risk", action="store_true")
    bot_p.set_defaults(func=cmd_bot)

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cfg = DerivConfig()
    asyncio.run(args.func(args, cfg))


if __name__ == "__main__":
    main()
