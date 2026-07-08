# Deriv Toolkit

A local Python toolkit for [Deriv](https://deriv.com) synthetic-index trading:
market/tick analysis, an account dashboard, an accumulator backtester, and a
bare-bones automated bot for Accumulator ("ACCU") contracts.

## ⚠️ Read this first

- **Synthetic indices and accumulators carry real financial risk.** Nothing
  in this toolkit is financial advice, and no code here can predict future
  price movement — synthetic indices are generated from a published
  pseudo-random model, so historical patterns don't change future odds.
- **Start on a demo account.** Create an API token from a demo (virtual)
  account and run everything, including `bot`, against that first.
- The `bot` command defaults to **dry-run** (it logs what it *would* trade
  but places no order). Live trading requires both `--live` and
  `--i-understand-the-risk`.
- `risk_manager.py` enforces hard caps (max stake, max daily loss, max open
  contracts, max trades/day, a cooldown after a loss) that the strategy
  cannot override — review and tighten `.env` before ever going live.
- The example strategy in `strategy.py` is a plumbing template, not a
  recommended trading rule. Write and backtest your own logic first.
- I sourced the request/response shapes here from Deriv's current public
  docs, but Deriv does update its API — before trading real money, sanity
  check field names against https://developers.deriv.com/docs/accumulator-options/
  and the schemas at https://github.com/deriv-com/deriv-api-schemas.

## Setup

```bash
cd deriv_toolkit
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env
```

Get an API token: log into Deriv → Settings → API token
(https://app.deriv.com/account/api-token). For `analyze` you don't need one.
For `dashboard`/`backtest` you need "Read" scope. For live `bot` trading you
additionally need "Trade" scope. Paste it into `.env` as `DERIV_API_TOKEN`.

## Commands

```bash
# Pull recent tick history for a symbol and print descriptive statistics
python main.py analyze --symbol R_100 --count 1000

# Live account dashboard: balance, open positions, recent closed trades
python main.py dashboard

# Backtest a "hold for N ticks, take profit or knockout" accumulator rule
# against real historical data, across several N values
python main.py backtest --symbol R_100 --stake 1 --growth-rate 0.03

# Run the bot in dry-run (default, no real orders placed)
python main.py bot --symbol R_100 --stake 1 --growth-rate 0.02

# Run the bot for real (only after you've reviewed strategy.py and .env risk limits)
python main.py bot --symbol R_100 --stake 1 --growth-rate 0.02 --live --i-understand-the-risk
```

Common symbols: `R_10`, `R_25`, `R_50`, `R_75`, `R_100` (Volatility Indices),
`1HZ100V`, `1HZ50V`, etc. (1-second Volatility Indices). Full list via the
`active_symbols` API call (see `DerivClient.active_symbols`).

## Web Interface

This toolkit now includes a FastAPI web interface with Vercel Web Analytics integration. When deployed to Vercel, you can:

- Access the web dashboard at the root URL (`/`)
- View API health status at `/api/health`
- Access service information at `/api/info`
- Browse interactive API docs at `/docs`

The web interface automatically tracks visitor analytics when deployed on Vercel.

### Local Development

To run the web interface locally:

```bash
pip install uvicorn
uvicorn api.index:app --reload
```

Then visit `http://localhost:8000` in your browser.

## Project layout

| File | Purpose |
|---|---|
| `api/index.py` | FastAPI web application with Vercel Analytics |
| `vercel.json` | Vercel deployment configuration |
| `config.py` | Loads API token, app_id, and risk limits from env/`.env` |
| `deriv_client.py` | Async WebSocket client for the Deriv API |
| `analysis.py` | Tick statistics, volatility, streak/run-length analysis |
| `accumulator.py` | Accumulator payout math + historical backtester |
| `strategy.py` | Pluggable strategy interface + template example |
| `risk_manager.py` | Hard safety limits the strategy cannot bypass |
| `bot.py` | Ties client + strategy + risk manager together |
| `dashboard.py` | `rich`-based terminal account dashboard |
| `backtest.py` | Backtest grid runner used by `main.py backtest` |
| `main.py` | CLI entrypoint |

## Extending it

- **New strategy**: implement `decide(state: MarketState) -> TradeDecision`
  (see `strategy.py`), backtest it via `accumulator.backtest_fixed_target`
  using real barrier widths from `accumulator.fetch_barrier_pct`, then wire
  it into `main.py`'s `cmd_bot`.
- **Other contract types** (Multipliers, Rise/Fall, Turbos): add a
  `*_proposal` method to `DerivClient` following the same pattern as
  `accumulator_proposal`, referencing the field names in Deriv's docs for
  that contract type.
