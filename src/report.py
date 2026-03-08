"""Rich terminal report renderer."""

from __future__ import annotations

from datetime import datetime, timezone

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .resolver import ResolvedToken


def render_report(token: ResolvedToken, data: dict, ai_summary: str | None = None) -> None:
    console = Console()
    console.print()

    # --- Header ---
    cg = data.get("coingecko") or {}
    meta = cg.get("meta") or {}
    name = token.name or meta.get("name") or token.input_query
    symbol = (token.symbol or "???").upper()
    chain = (token.chain or "unknown").upper()
    rank = meta.get("market_cap_rank")
    categories = ", ".join(meta.get("categories") or []) or None
    addr_display = token.address[:16] + "..." + token.address[-8:] if token.address and len(token.address) > 24 else token.address

    header_lines = [f"[bold]{name}[/bold] ({symbol}) on {chain}"]
    if addr_display:
        header_lines.append(f"[dim]{addr_display}[/dim]")
    if rank:
        header_lines.append(f"CoinGecko Rank: #{rank}")
    if categories:
        header_lines.append(f"Categories: {categories}")

    sources_hit = [k for k, v in data.items() if v is not None]
    header_lines.append(f"[dim]Data sources: {', '.join(sources_hit) or 'none'}[/dim]")

    console.print(Panel("\n".join(header_lines), title="TOKEN RESEARCH", border_style="cyan"))

    # --- Price & Market ---
    market = cg.get("market") or {}
    dex = data.get("dexscreener") or {}
    price = market.get("price_usd") or dex.get("price_usd")

    if price or market:
        t = Table(title="Price & Market Data", show_header=False, border_style="blue", pad_edge=False)
        t.add_column("Metric", style="bold", width=24)
        t.add_column("Value", width=36)

        if price:
            t.add_row("Price", f"${_fmt_num(price)}")
        if market.get("market_cap"):
            t.add_row("Market Cap", f"${_fmt_big(market['market_cap'])}")
        if market.get("fdv") or dex.get("fdv"):
            t.add_row("FDV", f"${_fmt_big(market.get('fdv') or dex.get('fdv'))}")
        if market.get("total_volume"):
            t.add_row("24h Volume", f"${_fmt_big(market['total_volume'])}")

        # Price changes
        for label, key_cg, key_dex in [
            ("1h Change", None, "1h"),
            ("24h Change", "price_change_24h", "24h"),
            ("7d Change", "price_change_7d", None),
            ("30d Change", "price_change_30d", None),
        ]:
            val = market.get(key_cg) if key_cg else None
            if val is None and key_dex:
                val = (dex.get("price_changes") or {}).get(key_dex)
            if val is not None:
                t.add_row(label, _color_pct(val))

        if market.get("ath"):
            ath_pct = market.get("ath_change_pct")
            ath_str = f"${_fmt_num(market['ath'])}"
            if ath_pct is not None:
                ath_str += f" ({_color_pct(ath_pct, raw=True)})"
            t.add_row("ATH", ath_str)
        if market.get("atl"):
            t.add_row("ATL", f"${_fmt_num(market['atl'])}")

        # Supply
        if market.get("circulating_supply"):
            t.add_row("Circulating Supply", _fmt_big(market["circulating_supply"]))
        if market.get("total_supply"):
            t.add_row("Total Supply", _fmt_big(market["total_supply"]))

        console.print(t)
        console.print()

    # --- Liquidity & Volume (DEX) ---
    if dex:
        t = Table(title="DEX Liquidity & Volume", show_header=False, border_style="green", pad_edge=False)
        t.add_column("Metric", style="bold", width=24)
        t.add_column("Value", width=36)

        t.add_row("Total Liquidity", f"${_fmt_big(dex.get('liquidity_usd'))}")
        vol_24 = (dex.get("volume") or {}).get("24h")
        liq = dex.get("liquidity_usd")
        if vol_24 and liq and liq > 0:
            t.add_row("Vol/Liq Ratio (24h)", f"{float(vol_24) / liq:.2f}")

        for period in ["5m", "1h", "6h", "24h"]:
            v = (dex.get("volume") or {}).get(period)
            if v:
                t.add_row(f"Volume ({period})", f"${_fmt_big(v)}")

        txns = dex.get("txns_24h") or {}
        buys = txns.get("buys", 0)
        sells = txns.get("sells", 0)
        if buys or sells:
            ratio = f" (ratio: {buys / sells:.2f})" if sells > 0 else ""
            t.add_row("24h Txns", f"{buys} buys / {sells} sells{ratio}")

        t.add_row("Pairs Found", str(dex.get("pairs_count", 0)))

        if dex.get("pair_created_at"):
            try:
                ts = int(dex["pair_created_at"]) / 1000
                age = datetime.now(timezone.utc) - datetime.fromtimestamp(ts, tz=timezone.utc)
                t.add_row("Pair Age", f"{age.days}d {age.seconds // 3600}h")
            except Exception:
                pass

        console.print(t)

        # Top pairs sub-table
        if dex.get("top_pairs"):
            pt = Table(title="Top Pairs", border_style="dim green")
            pt.add_column("DEX")
            pt.add_column("Pair")
            pt.add_column("Liquidity", justify="right")
            pt.add_column("Volume 24h", justify="right")
            for p in dex["top_pairs"]:
                pt.add_row(
                    p.get("dex", "?"),
                    p.get("pair", "?"),
                    f"${_fmt_big(p.get('liquidity_usd'))}",
                    f"${_fmt_big(p.get('volume_24h'))}",
                )
            console.print(pt)
        console.print()

    # --- Security & Risk ---
    be = data.get("birdeye") or {}
    sec = be.get("security")
    helius_meta = (data.get("helius") or {}).get("metadata")

    if sec or helius_meta:
        title = "Security & Token Info"
        if sec:
            title += " (Birdeye + Helius)" if helius_meta else " (Birdeye)"
        elif helius_meta:
            title += " (Helius)"
        t = Table(title=title, show_header=False, border_style="red", pad_edge=False)
        t.add_column("Check", style="bold", width=24)
        t.add_column("Status", width=36)

        # Helius metadata
        if helius_meta:
            t.add_row("Token Standard", helius_meta.get("token_standard") or "Unknown")
            mint_auth = helius_meta.get("mint_authority")
            if mint_auth:
                t.add_row("Mint Authority", f"[yellow]{mint_auth[:16]}...[/yellow]")
            else:
                t.add_row("Mint Authority", "[green]Revoked[/green]")

        # Birdeye security flags
        if sec:
            _flag(t, "Mutable Metadata", sec.get("mutable_metadata"), bad=True)
            _flag(t, "Freezeable", sec.get("freezeable"), bad=True)
            _flag(t, "Freeze Authority", sec.get("freeze_authority"), bad=True, is_present=True)
            _flag(t, "Transfer Fee", sec.get("transfer_fee"), bad=True)
            _flag(t, "Token2022", sec.get("is_token2022"))
            _flag(t, "Non-Transferable", sec.get("non_transferable"), bad=True)

            top10 = sec.get("top10_holder_pct")
            if top10 is not None:
                pct_val = float(top10) * 100 if float(top10) <= 1 else float(top10)
                color = "red" if pct_val > 50 else "yellow" if pct_val > 30 else "green"
                t.add_row("Top 10 Holder %", f"[{color}]{pct_val:.1f}%[/{color}]")

            if sec.get("creator"):
                t.add_row("Creator", f"[dim]{sec['creator'][:16]}...[/dim]")

        console.print(t)
        console.print()

    # --- Holder Analysis ---
    helius_all = data.get("helius") or {}
    holders = helius_all.get("holders")
    be_ov = be.get("overview") or {}

    has_holder_data = be_ov.get("holder_count") or (holders and holders.get("top_accounts"))
    if has_holder_data:
        t = Table(title="Holder Analysis", show_header=False, border_style="magenta", pad_edge=False)
        t.add_column("Metric", style="bold", width=24)
        t.add_column("Value", width=36)

        if be_ov.get("holder_count"):
            t.add_row("Total Holders", _fmt_big(be_ov["holder_count"]))
        if be_ov.get("unique_wallets_24h"):
            t.add_row("Unique Wallets 24h", _fmt_big(be_ov["unique_wallets_24h"]))

        if holders:
            t.add_row("Top 10 Concentration", f"{holders.get('top10_total_pct', 0)}%")

        console.print(t)

        # Top holders table
        if holders and holders.get("top_accounts"):
            ht = Table(title="Top Holders (Helius)", border_style="dim magenta")
            ht.add_column("#", width=3)
            ht.add_column("Address")
            ht.add_column("% Supply", justify="right")
            for i, h in enumerate(holders["top_accounts"], 1):
                ht.add_row(str(i), h["address"], f"{h['pct']:.2f}%")
            console.print(ht)
        console.print()

    # --- Community & On-chain ---
    community = cg.get("community") or {}
    developer = cg.get("developer") or {}
    dl = data.get("defillama") or {}
    protocol = dl.get("protocol") if dl else None

    has_community = any(v for v in community.values() if v)
    has_dev = any(v for v in developer.values() if v)

    if has_community or has_dev or protocol:
        t = Table(title="Community & On-chain", show_header=False, border_style="yellow", pad_edge=False)
        t.add_column("Metric", style="bold", width=24)
        t.add_column("Value", width=36)

        if community.get("twitter_followers"):
            t.add_row("Twitter Followers", _fmt_big(community["twitter_followers"]))
        if community.get("reddit_subscribers"):
            t.add_row("Reddit Subscribers", _fmt_big(community["reddit_subscribers"]))
        if community.get("telegram_members"):
            t.add_row("Telegram Members", _fmt_big(community["telegram_members"]))
        if developer.get("stars"):
            t.add_row("GitHub Stars", _fmt_big(developer["stars"]))
        if developer.get("commits_4w"):
            t.add_row("Commits (4 weeks)", str(developer["commits_4w"]))

        if meta.get("sentiment_up_pct"):
            t.add_row("CG Sentiment (up)", f"{meta['sentiment_up_pct']:.0f}%")
        if meta.get("watchlist_users"):
            t.add_row("CG Watchlist Users", _fmt_big(meta["watchlist_users"]))

        if protocol:
            t.add_row("DeFiLlama TVL", f"${_fmt_big(protocol.get('tvl'))}")
            if protocol.get("change_1d"):
                t.add_row("TVL Change 1d", _color_pct(protocol["change_1d"]))
            if protocol.get("category"):
                t.add_row("Protocol Category", protocol["category"])
            if protocol.get("chains"):
                t.add_row("Chains", ", ".join(protocol["chains"][:5]))

        console.print(t)
        console.print()

    # --- AI Synthesis ---
    if ai_summary:
        console.print(Panel(ai_summary, title="AI SYNTHESIS (Claude)", border_style="bright_cyan"))
        console.print()

    # --- Sources footer ---
    missed = [k for k, v in data.items() if v is None]
    if missed:
        console.print(f"[dim]No data from: {', '.join(missed)}[/dim]")
    if dex and dex.get("url"):
        console.print(f"[dim]DexScreener: {dex['url']}[/dim]")
    console.print()


# --- Helpers ---

def _fmt_num(val) -> str:
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if f < 0.01:
            return f"{f:.8f}"
        if f < 1:
            return f"{f:.4f}"
        if f < 1000:
            return f"{f:,.2f}"
        return f"{f:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def _fmt_big(val) -> str:
    if val is None:
        return "N/A"
    try:
        f = float(val)
        if abs(f) >= 1e9:
            return f"{f / 1e9:.2f}B"
        if abs(f) >= 1e6:
            return f"{f / 1e6:.2f}M"
        if abs(f) >= 1e3:
            return f"{f / 1e3:.1f}K"
        return f"{f:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def _color_pct(val, raw: bool = False) -> str:
    try:
        f = float(val)
        color = "green" if f >= 0 else "red"
        text = f"{f:+.2f}%"
        if raw:
            return f"[{color}]{text}[/{color}]"
        return f"[{color}]{text}[/{color}]"
    except (ValueError, TypeError):
        return str(val)


def _flag(table: Table, label: str, value, bad: bool = False, is_present: bool = False):
    if value is None:
        return
    if is_present:
        # For fields where having a value is the flag
        has = bool(value) and value != "None"
        color = "red" if has and bad else "green"
        status = "SET" if has else "None"
    else:
        color = "red" if value and bad else "green"
        status = "Yes" if value else "No"
    table.add_row(label, f"[{color}]{status}[/{color}]")
