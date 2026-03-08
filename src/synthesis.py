"""Optional Claude AI synthesis of collected data."""

from __future__ import annotations

import json
import os

from .resolver import ResolvedToken


def get_ai_summary(token: ResolvedToken, data: dict) -> str | None:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        # Build a clean data summary (strip None values)
        clean = {}
        for source, d in data.items():
            if d is not None:
                clean[source] = d

        context = json.dumps(clean, indent=2, default=str)
        token_desc = f"{token.name or token.symbol or token.input_query} ({token.symbol or '?'}) on {token.chain or 'unknown'}"

        msg = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system="You are a crypto research analyst. Given API data about a token, provide a concise 4-6 sentence assessment. Cover: 1) what the token is, 2) current market snapshot, 3) key risks or red flags, 4) notable strengths. Be direct, factual, and opinionated where the data supports it. No disclaimers.",
            messages=[{
                "role": "user",
                "content": f"Research data for {token_desc}:\n\n{context}",
            }],
        )
        return msg.content[0].text
    except Exception as e:
        return f"[AI synthesis failed: {e}]"
