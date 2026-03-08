"""Token input resolution — address, symbol, or name → structured identifiers."""

from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

COINGECKO_PLATFORM_MAP = {
    "solana": "solana",
    "ethereum": "ethereum",
    "bsc": "binance-smart-chain",
    "arbitrum": "arbitrum-one",
    "polygon": "polygon-pos",
    "avalanche": "avalanche",
    "base": "base",
    "optimism": "optimistic-ethereum",
}

# Reverse map for CoinGecko platform → our chain ID
PLATFORM_TO_CHAIN = {v: k for k, v in COINGECKO_PLATFORM_MAP.items()}


@dataclass
class ResolvedToken:
    input_query: str
    address: str | None = None
    chain: str | None = None
    coingecko_id: str | None = None
    symbol: str | None = None
    name: str | None = None


def _looks_like_solana_address(s: str) -> bool:
    return bool(re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", s))


def _looks_like_evm_address(s: str) -> bool:
    return bool(re.match(r"^0x[0-9a-fA-F]{40}$", s))


async def _search_dexscreener(client: httpx.AsyncClient, query: str, chain_hint: str | None) -> dict | None:
    try:
        r = await client.get(f"https://api.dexscreener.com/latest/dex/search?q={query}")
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        if chain_hint:
            pairs = [p for p in pairs if p.get("chainId") == chain_hint]
        if not pairs:
            return None
        # Pick highest liquidity pair
        best = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd") or 0))
        base = best.get("baseToken", {})
        return {
            "address": base.get("address"),
            "chain": best.get("chainId"),
            "symbol": base.get("symbol"),
            "name": base.get("name"),
        }
    except Exception:
        return None


async def _search_coingecko(client: httpx.AsyncClient, query: str) -> dict | None:
    try:
        r = await client.get(
            "https://api.coingecko.com/api/v3/search",
            params={"query": query},
        )
        r.raise_for_status()
        coins = r.json().get("coins") or []
        if not coins:
            return None
        # Pick best by market_cap_rank
        ranked = [c for c in coins if c.get("market_cap_rank")]
        best = min(ranked, key=lambda c: c["market_cap_rank"]) if ranked else coins[0]
        return {
            "coingecko_id": best.get("id"),
            "symbol": best.get("symbol"),
            "name": best.get("name"),
        }
    except Exception:
        return None


async def _coingecko_by_contract(client: httpx.AsyncClient, chain: str, address: str) -> str | None:
    platform = COINGECKO_PLATFORM_MAP.get(chain)
    if not platform:
        return None
    try:
        r = await client.get(f"https://api.coingecko.com/api/v3/coins/{platform}/contract/{address}")
        r.raise_for_status()
        return r.json().get("id")
    except Exception:
        return None


async def resolve_token(query: str, chain_hint: str | None = None) -> ResolvedToken:
    token = ResolvedToken(input_query=query)

    async with httpx.AsyncClient(timeout=15.0) as client:
        if _looks_like_solana_address(query):
            token.address = query
            token.chain = chain_hint or "solana"
            # Try to get more info from DexScreener
            dex = await _search_dexscreener(client, query, token.chain)
            if dex:
                token.symbol = dex.get("symbol")
                token.name = dex.get("name")
            # Try CoinGecko contract lookup
            token.coingecko_id = await _coingecko_by_contract(client, token.chain, token.address)

        elif _looks_like_evm_address(query):
            token.address = query
            token.chain = chain_hint or "ethereum"
            dex = await _search_dexscreener(client, query, token.chain)
            if dex:
                token.symbol = dex.get("symbol")
                token.name = dex.get("name")
                token.chain = dex.get("chain") or token.chain
            token.coingecko_id = await _coingecko_by_contract(client, token.chain, token.address)

        else:
            # Symbol or name — search both APIs
            import asyncio
            dex_result, cg_result = await asyncio.gather(
                _search_dexscreener(client, query, chain_hint),
                _search_coingecko(client, query),
            )
            if cg_result:
                token.coingecko_id = cg_result.get("coingecko_id")
                token.symbol = cg_result.get("symbol")
                token.name = cg_result.get("name")
            if dex_result:
                token.address = dex_result.get("address")
                token.chain = dex_result.get("chain")
                token.symbol = token.symbol or dex_result.get("symbol")
                token.name = token.name or dex_result.get("name")
            if chain_hint:
                token.chain = chain_hint

    return token
