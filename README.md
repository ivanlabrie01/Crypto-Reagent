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
git clone https://github.com/ivanlabrie/reagent.git
cd reagent
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

### Ivan Labrie's Laboratory

Built by [Ivan Labrie's Laboratory](https://discord.gg/xRp9yjCqSQ) — a crypto signals and research community covering options, perpetual futures, spot, and DeFi strategies.

**What you get:**
- Live trade signals and portfolio updates
- Market regime analysis and macro reads
- Tools and bots built in-house (like this one)
- Direct access to research and discussion

**Subscription tiers:**
- 1 week free trial — no commitment
- $200 / quarter
- $750 / year

[![Discord](https://img.shields.io/badge/Join%20the%20Lab-Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/xRp9yjCqSQ)
