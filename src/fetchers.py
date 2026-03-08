"""Parallel API fetchers — all return dict | None, never raise."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from .resolver import ResolvedToken, COINGECKO_PLATFORM_MAP


async def fetch_dexscreener(client: httpx.AsyncClient, token: ResolvedToken) -> dict | None:
    try:
        if token.address:
            r = await client.get(f"https://api.dexscreener.com/latest/dex/tokens/{token.address}")
        else:
            q = token.symbol or token.name or token.input_query
            r = await client.get(f"https://api.dexscreener.com/latest/dex/search?q={q}")
        r.raise_for_status()
        pairs = r.json().get("pairs") or []
        if token.chain:
            chain_pairs = [p for p in pairs if p.get("chainId") == token.chain]
            if chain_pairs:
                pairs = chain_pairs
        if not pairs:
            return None

        # Sort by liquidity descending
        pairs.sort(key=lambda p: float(p.get("liquidity", {}).get("usd") or 0), reverse=True)
        best = pairs[0]

        top_pairs = []
        for p in pairs[:3]:
            top_pairs.append({
                "dex": p.get("dexId"),
                "pair": p.get("pairAddress", "")[:12] + "...",
                "liquidity_usd": float(p.get("liquidity", {}).get("usd") or 0),
                "volume_24h": float(p.get("volume", {}).get("h24") or 0),
            })

        return {
            "price_usd": best.get("priceUsd"),
            "price_native": best.get("priceNative"),
            "price_changes": {
                "5m": best.get("priceChange", {}).get("m5"),
                "1h": best.get("priceChange", {}).get("h1"),
                "6h": best.get("priceChange", {}).get("h6"),
                "24h": best.get("priceChange", {}).get("h24"),
            },
            "volume": {
                "5m": best.get("volume", {}).get("m5"),
                "1h": best.get("volume", {}).get("h1"),
                "6h": best.get("volume", {}).get("h6"),
                "24h": best.get("volume", {}).get("h24"),
            },
            "liquidity_usd": float(best.get("liquidity", {}).get("usd") or 0),
            "txns_24h": best.get("txns", {}).get("h24", {}),
            "fdv": best.get("fdv"),
            "market_cap": best.get("marketCap"),
            "pair_created_at": best.get("pairCreatedAt"),
            "pairs_count": len(pairs),
            "top_pairs": top_pairs,
            "url": best.get("url"),
        }
    except Exception:
        return None


async def fetch_coingecko(client: httpx.AsyncClient, token: ResolvedToken) -> dict | None:
    try:
        cg_id = token.coingecko_id
        if not cg_id and token.address and token.chain:
            platform = COINGECKO_PLATFORM_MAP.get(token.chain)
            if platform:
                r = await client.get(f"https://api.coingecko.com/api/v3/coins/{platform}/contract/{token.address}")
                if r.status_code == 200:
                    data = r.json()
                    cg_id = data.get("id")
        if not cg_id:
            return None

        r = await client.get(
            f"https://api.coingecko.com/api/v3/coins/{cg_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "community_data": "true",
                "developer_data": "true",
                "sparkline": "false",
            },
        )
        r.raise_for_status()
        data = r.json()
        md = data.get("market_data") or {}
        cd = data.get("community_data") or {}
        dd = data.get("developer_data") or {}

        return {
            "market": {
                "price_usd": _nested(md, "current_price", "usd"),
                "market_cap": _nested(md, "market_cap", "usd"),
                "total_volume": _nested(md, "total_volume", "usd"),
                "price_change_24h": md.get("price_change_percentage_24h"),
                "price_change_7d": md.get("price_change_percentage_7d"),
                "price_change_30d": md.get("price_change_percentage_30d"),
                "ath": _nested(md, "ath", "usd"),
                "ath_change_pct": _nested(md, "ath_change_percentage", "usd"),
                "ath_date": _nested(md, "ath_date", "usd"),
                "atl": _nested(md, "atl", "usd"),
                "atl_date": _nested(md, "atl_date", "usd"),
                "circulating_supply": md.get("circulating_supply"),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
                "fdv": md.get("fully_diluted_valuation", {}).get("usd"),
            },
            "community": {
                "twitter_followers": cd.get("twitter_followers"),
                "reddit_subscribers": cd.get("reddit_subscribers"),
                "reddit_active_48h": cd.get("reddit_accounts_active_48h"),
                "telegram_members": cd.get("telegram_channel_user_count"),
            },
            "developer": {
                "forks": dd.get("forks"),
                "stars": dd.get("stars"),
                "commits_4w": dd.get("commit_count_4_weeks"),
                "prs_merged": dd.get("pull_requests_merged"),
            },
            "meta": {
                "categories": data.get("categories"),
                "genesis_date": data.get("genesis_date"),
                "sentiment_up_pct": data.get("sentiment_votes_up_percentage"),
                "watchlist_users": data.get("watchlist_portfolio_users"),
                "market_cap_rank": data.get("market_cap_rank"),
                "description": (data.get("description", {}).get("en") or "")[:300],
            },
        }
    except Exception:
        return None


async def fetch_birdeye(client: httpx.AsyncClient, token: ResolvedToken) -> dict | None:
    api_key = os.getenv("BIRDEYE_API_KEY")
    if not api_key or token.chain != "solana" or not token.address:
        return None
    headers = {"X-API-KEY": api_key, "x-chain": "solana"}
    try:
        overview_req = client.get(
            "https://public-api.birdeye.so/defi/token_overview",
            params={"address": token.address},
            headers=headers,
        )
        security_req = client.get(
            "https://public-api.birdeye.so/defi/token_security",
            params={"address": token.address},
            headers=headers,
        )
        ov_resp, sec_resp = await asyncio.gather(overview_req, security_req, return_exceptions=True)

        overview = None
        if isinstance(ov_resp, httpx.Response) and ov_resp.status_code == 200:
            od = ov_resp.json().get("data") or {}
            overview = {
                "price": od.get("price"),
                "liquidity": od.get("liquidity"),
                "holder_count": od.get("holder"),
                "trade_24h": od.get("trade24h"),
                "buy_24h": od.get("buy24h"),
                "sell_24h": od.get("sell24h"),
                "unique_wallets_24h": od.get("uniqueWallet24h"),
                "unique_wallets_history_24h": od.get("uniqueWalletHistory24h"),
                "v1h": od.get("v1hUSD"),
                "v6h": od.get("v6hUSD"),
                "v24h": od.get("v24hUSD"),
                "last_trade_time": od.get("lastTradeUnixTime"),
            }

        security = None
        if isinstance(sec_resp, httpx.Response) and sec_resp.status_code == 200:
            sd = sec_resp.json().get("data") or {}
            security = {
                "mutable_metadata": sd.get("mutableMetadata"),
                "top10_holder_pct": sd.get("top10HolderPercent"),
                "top10_user_pct": sd.get("top10UserPercent"),
                "freezeable": sd.get("freezeable"),
                "freeze_authority": sd.get("freezeAuthority"),
                "transfer_fee": sd.get("transferFeeEnable"),
                "is_token2022": sd.get("isToken2022"),
                "non_transferable": sd.get("nonTransferable"),
                "creator": sd.get("creatorAddress"),
                "creation_time": sd.get("creationTime"),
            }

        if not overview and not security:
            return None
        return {"overview": overview, "security": security}
    except Exception:
        return None


async def fetch_helius(client: httpx.AsyncClient, token: ResolvedToken) -> dict | None:
    api_key = os.getenv("HELIUS_API_KEY")
    if not api_key or token.chain != "solana" or not token.address:
        return None
    url = f"https://mainnet.helius-rpc.com/?api-key={api_key}"
    try:
        asset_req = client.post(url, json={
            "jsonrpc": "2.0", "id": "1", "method": "getAsset",
            "params": {"id": token.address},
        })
        # getTokenLargestAccounts via standard RPC
        holders_req = client.post(url, json={
            "jsonrpc": "2.0", "id": "2", "method": "getTokenLargestAccounts",
            "params": [token.address],
        })
        asset_resp, holders_resp = await asyncio.gather(asset_req, holders_req, return_exceptions=True)

        metadata = None
        if isinstance(asset_resp, httpx.Response) and asset_resp.status_code == 200:
            result = asset_resp.json().get("result") or {}
            metadata = {
                "name": result.get("content", {}).get("metadata", {}).get("name"),
                "symbol": result.get("content", {}).get("metadata", {}).get("symbol"),
                "token_standard": result.get("content", {}).get("metadata", {}).get("token_standard"),
                "supply": result.get("token_info", {}).get("supply"),
                "decimals": result.get("token_info", {}).get("decimals"),
                "mint_authority": result.get("authorities", [{}])[0].get("address") if result.get("authorities") else None,
            }

        holders = None
        if isinstance(holders_resp, httpx.Response) and holders_resp.status_code == 200:
            accounts = holders_resp.json().get("result", {}).get("value") or []
            total = sum(float(a.get("uiAmount") or 0) for a in accounts)
            top_holders = []
            for a in accounts[:10]:
                amt = float(a.get("uiAmount") or 0)
                top_holders.append({
                    "address": a.get("address", "")[:12] + "...",
                    "amount": amt,
                    "pct": round(amt / total * 100, 2) if total > 0 else 0,
                })
            holders = {
                "top_accounts": top_holders,
                "top10_total_pct": round(sum(h["pct"] for h in top_holders), 2),
            }

        if not metadata and not holders:
            return None
        return {"metadata": metadata, "holders": holders}
    except Exception:
        return None


async def fetch_defillama(client: httpx.AsyncClient, token: ResolvedToken) -> dict | None:
    try:
        results: dict[str, Any] = {}

        # Price check
        if token.address and token.chain:
            r = await client.get(f"https://coins.llama.fi/prices/current/{token.chain}:{token.address}")
            if r.status_code == 200:
                coins = r.json().get("coins") or {}
                for v in coins.values():
                    results["price"] = {
                        "price": v.get("price"),
                        "symbol": v.get("symbol"),
                        "confidence": v.get("confidence"),
                    }
                    break
        elif token.coingecko_id:
            r = await client.get(f"https://coins.llama.fi/prices/current/coingecko:{token.coingecko_id}")
            if r.status_code == 200:
                coins = r.json().get("coins") or {}
                for v in coins.values():
                    results["price"] = {
                        "price": v.get("price"),
                        "symbol": v.get("symbol"),
                        "confidence": v.get("confidence"),
                    }
                    break

        # Protocol lookup
        if token.coingecko_id or token.symbol:
            r = await client.get("https://api.llama.fi/protocols")
            if r.status_code == 200:
                protocols = r.json()
                match = None
                for p in protocols:
                    if token.coingecko_id and p.get("gecko_id") == token.coingecko_id:
                        match = p
                        break
                if not match and token.symbol:
                    sym = token.symbol.upper()
                    for p in protocols:
                        if (p.get("symbol") or "").upper() == sym:
                            match = p
                            break
                if match:
                    results["protocol"] = {
                        "name": match.get("name"),
                        "tvl": match.get("tvl"),
                        "change_1d": match.get("change_1d"),
                        "change_7d": match.get("change_7d"),
                        "category": match.get("category"),
                        "chains": match.get("chains"),
                        "audits": match.get("audits"),
                        "mcap": match.get("mcap"),
                    }

        return results if results else None
    except Exception:
        return None


async def fetch_all(token: ResolvedToken) -> dict[str, dict | None]:
    async with httpx.AsyncClient(timeout=20.0) as client:
        results = await asyncio.gather(
            fetch_dexscreener(client, token),
            fetch_coingecko(client, token),
            fetch_birdeye(client, token),
            fetch_helius(client, token),
            fetch_defillama(client, token),
            return_exceptions=True,
        )
    names = ["dexscreener", "coingecko", "birdeye", "helius", "defillama"]
    return {
        name: (r if isinstance(r, dict) else None)
        for name, r in zip(names, results)
    }


def _nested(d: dict, *keys: str) -> Any:
    for k in keys:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d
