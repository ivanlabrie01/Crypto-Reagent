# Reagent

A lightweight crypto research CLI that pulls data from free APIs and renders structured terminal reports. One command, all the data you need before entering a position.

## What it does

Give it a token address, symbol, or name — it queries 5 APIs in parallel and outputs a clean report covering:

- **Price & Market Data** — price, market cap, FDV, volume, price changes, ATH/ATL, supply
- **DEX Liquidity & Volume** — liquidity depth, vol/liq ratio, buy/sell counts, top pairs
- **Security & Token Info** — mint/freeze authority, mutable metadata, token standard
- **Holder Analysis** — holder count, top holder concentration, unique wallets
- **Community & On-chain** — social followers, dev activity, DeFiLlama TVL, CoinGecko sentiment
- **AI Synthesis** — optional Claude-powered summary tying it all together

Works for any token on any chain — Solana memes, BTC, ETH, DeFi protocols, whatever.

## Data Sources

All free tier, no paid APIs required:

| Source | Key needed | Coverage |
|---|---|---|
| DexScreener | No | DEX pairs, liquidity, volume (all chains) |
| CoinGecko | No | Market data, community, dev stats |
| DeFiLlama | No | TVL, protocol data |
| Helius | Yes (free) | Solana token metadata, holders |
| Birdeye | Yes (free) | Solana token overview, security flags |

## Install

```bash
git clone https://github.com/ivanlabrie01/Crypto-Reagent.git
cd Crypto-Reagent
python3 -m venv .venv
.venv/bin/pip install -e .
```

Copy `.env.example` to `.env` and add your keys:

```bash
cp .env.example .env
```

## Usage

```bash
# By symbol
.venv/bin/research SOL
.venv/bin/research bitcoin
.venv/bin/research PEPE --chain ethereum

# By contract address
.venv/bin/research JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN

# Skip AI summary
.venv/bin/research SOL --no-ai

# JSON output (for piping to jq or other tools)
.venv/bin/research SOL --json
```

## Options

| Flag | Description |
|---|---|
| `--no-ai` | Skip Claude AI synthesis |
| `--chain` | Chain hint: solana, ethereum, bsc, arbitrum, base, ... |
| `--json` | Output raw JSON instead of terminal report |

## Requirements

- Python 3.11+
- Free API keys for Solana-specific data (Helius, Birdeye)
- Anthropic API key for AI synthesis (optional)

---

## About

Built by Ivan Labrie, trend-following trader (Time at Mode, Tim West's framework), trading full-time since 2015 with a public, timestamped track record.

- Site and services: https://ivanlabrie.netlify.app
- Free analysis (Substack): https://ivanlabrie.substack.com
- TradingView (ideas and free indicators): https://www.tradingview.com/u/IvanLabrie
- Track record: https://x.com/ivan_labrie (the pinned post has the full archive)
