"""CLI entry point for CryptoResearch."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from rich.console import Console

from .resolver import resolve_token
from .fetchers import fetch_all
from .synthesis import get_ai_summary
from .report import render_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="research",
        description="Crypto research CLI — pulls free API data into a structured report.",
    )
    parser.add_argument("token", help="Token address, symbol, or name")
    parser.add_argument("--no-ai", action="store_true", help="Skip Claude AI synthesis")
    parser.add_argument("--chain", type=str, default=None, help="Chain hint (solana, ethereum, bsc, arbitrum, base, ...)")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of terminal report")
    return parser.parse_args()


async def main() -> None:
    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    args = parse_args()
    # When outputting JSON, send status/progress to stderr so stdout stays clean
    console = Console(stderr=True) if args.json else Console()

    with console.status("[cyan]Resolving token...[/cyan]"):
        token = await resolve_token(args.token, args.chain)

    if not token.address and not token.coingecko_id:
        console.print(f"[red]Could not resolve '{args.token}' — try a contract address or check spelling.[/red]")
        sys.exit(1)

    console.print(f"[dim]Resolved: {token.name or token.symbol or '?'} | chain={token.chain} | addr={token.address or 'N/A'}[/dim]")

    with console.status("[cyan]Fetching data from 5 APIs...[/cyan]"):
        data = await fetch_all(token)

    ai_summary = None
    if not args.no_ai:
        with console.status("[cyan]Generating AI synthesis...[/cyan]"):
            ai_summary = get_ai_summary(token, data)

    if args.json:
        output = {"token": asdict(token), "data": data}
        print(json.dumps(output, indent=2, default=str))
    else:
        render_report(token, data, ai_summary)


def run() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run()
