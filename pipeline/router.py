# Router module — scores article relevance via OpenRouter LLM API
#
# Why OpenRouter?
# OpenRouter is an API aggregator that routes requests to 100+ models through
# a single OpenAI-compatible endpoint. This gives us:
#   - No vendor lock-in: swap models by changing a string
#   - Built-in fallback: if the primary model is down or rate-limited,
#     we retry with a different provider automatically
#   - Cost control: open-weight models (Llama, Mistral) are cheap for
#     high-volume classification tasks like relevance scoring

import json
import re
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import os

# ── Path constants ─────────────────────────────────────────────────────────────
ROOT_DIR       = Path(__file__).resolve().parent.parent
DB_PATH        = ROOT_DIR / "storage" / "articles.db"
PROMPT_PATH    = ROOT_DIR / "prompts" / "relevance_prompt.txt"

# ── Model config ───────────────────────────────────────────────────────────────
PRIMARY_MODEL  = "meta-llama/llama-3.3-70b-instruct"
FALLBACK_MODEL = "mistralai/mistral-nemo"        # $0.02/M — confirmed working, clean JSON output

# OpenRouter requires these headers for routing analytics and abuse prevention
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/ai-news-pipeline",
    "X-Title":      "AI News Pipeline - Relevance Router",
}

DELAY_BETWEEN_CALLS = 0.5  # seconds — avoid hammering the API


# ── Client setup ───────────────────────────────────────────────────────────────

def init_client() -> OpenAI:
    """
    Load the OpenRouter API key from .env and return an OpenAI-compatible client
    pointed at the OpenRouter base URL.
    """
    load_dotenv(ROOT_DIR / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "OPENROUTER_API_KEY not found. "
            "Copy .env.example to .env and add your key."
        )
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=OPENROUTER_HEADERS,
    )


# ── Prompt loading ─────────────────────────────────────────────────────────────

def load_prompt(path: Path) -> str:
    """Read the relevance prompt template from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── Response sanitizer ────────────────────────────────────────────────────────

def sanitize_json_response(raw: str) -> str:
    """
    Clean up common LLM output artifacts before attempting JSON parsing.

    Problems observed in the wild:
      1. Markdown code fences  — ```json ... ```
      2. Noise characters      — Llama-3.3-70b occasionally injects sequences of
                                 '!!!!!' into its output (mid-key, mid-value, or
                                 between tokens). These are never valid JSON and
                                 can be stripped unconditionally.
      3. Trailing prose        — Text after the closing brace.

    Strategy: strip fences → strip '!' runs → extract the first {...} block.
    """
    # 1. Strip markdown code fences
    if "```" in raw:
        # Grab everything between the first and last fence
        parts = raw.split("```")
        # parts[1] is the fenced block; strip a leading "json" language tag
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

    # 2. Remove runs of '!' — a known Llama output artifact that breaks JSON
    #    (safe because '!' never appears in valid JSON outside a string value,
    #    and the model has never been observed putting '!' in its string values)
    raw = re.sub(r"!+", "", raw)

    # 3. Extract the first complete {...} block to discard any preamble/postamble
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    return raw.strip()


# ── LLM call with fallback ─────────────────────────────────────────────────────

def score_article(
    client: OpenAI,
    prompt_template: str,
    title: str,
    summary: str,
) -> tuple[dict | None, str, int]:
    """
    Send an article to the LLM for relevance scoring.

    Tries the primary model first; if that fails or returns unparseable JSON,
    retries once with the fallback model.

    Returns:
        (parsed_result, model_used, total_tokens)
        parsed_result is None if both attempts fail.
    """
    filled_prompt = prompt_template.format(title=title, summary=summary or "(no summary)")

    for attempt, model in enumerate([PRIMARY_MODEL, FALLBACK_MODEL]):
        label = "primary" if attempt == 0 else "fallback"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": filled_prompt}],
                temperature=0.0,   # deterministic — we want consistent scoring
                max_tokens=150,    # the JSON response is always short
            )

            raw = response.choices[0].message.content.strip()
            tokens = response.usage.total_tokens if response.usage else 0

            # Sanitize before parsing — strips fences, '!!!!' noise, and prose
            raw = sanitize_json_response(raw)

            result = json.loads(raw)

            # Validate required fields are present before accepting
            if not all(k in result for k in ("relevance_score", "relevance_reason", "is_relevant")):
                raise ValueError(f"Missing fields in response: {result}")

            return result, f"{label} ({model})", tokens

        except json.JSONDecodeError as e:
            print(f"    [WARN] JSON parse error on {label} model: {e}")
            print(f"    [WARN] Raw response: {raw!r}")
            if attempt == 1:
                return None, f"both models failed", 0

        except Exception as e:
            print(f"    [WARN] API error on {label} model ({model}): {e}")
            if attempt == 1:
                return None, "both models failed", 0

        # Brief pause before fallback attempt
        if attempt == 0:
            time.sleep(0.5)

    return None, "both models failed", 0


# ── Database helpers ───────────────────────────────────────────────────────────

def fetch_unscored(conn: sqlite3.Connection) -> list[dict]:
    """Return all articles that have not yet been scored (is_relevant IS NULL)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, title, summary FROM articles WHERE is_relevant IS NULL"
    ).fetchall()
    return [dict(row) for row in rows]


def update_article_score(
    conn: sqlite3.Connection,
    article_id: int,
    relevance_score: int,
    is_relevant: bool,
    relevance_reason: str,
) -> None:
    """Write the scoring result back to the article row."""
    conn.execute(
        """
        UPDATE articles
        SET relevance_score  = :score,
            is_relevant      = :relevant,
            relevance_reason = :reason
        WHERE id = :id
        """,
        {
            "score":    relevance_score,
            "relevant": is_relevant,
            "reason":   relevance_reason,
            "id":       article_id,
        },
    )
    conn.commit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== AI News Pipeline - Relevance Router ===\n")

    client          = init_client()
    prompt_template = load_prompt(PROMPT_PATH)
    conn            = sqlite3.connect(DB_PATH)

    articles = fetch_unscored(conn)
    print(f"Found {len(articles)} unscored article(s) to process.\n")

    if not articles:
        print("Nothing to score. Run ingest.py first.")
        conn.close()
        return

    total_scored    = 0
    total_relevant  = 0
    total_fallback  = 0
    total_tokens    = 0

    for article in articles:
        aid     = article["id"]
        title   = article["title"] or "(no title)"
        summary = article["summary"] or ""

        result, model_used, tokens = score_article(client, prompt_template, title, summary)
        total_tokens += tokens

        if result is None:
            print(f"  [ERROR] Could not score article {aid}: \"{title[:60]}\"")
            continue

        score    = int(result["relevance_score"])
        relevant = bool(result["is_relevant"])
        reason   = result["relevance_reason"]

        update_article_score(conn, aid, score, relevant, reason)

        total_scored   += 1
        if relevant:
            total_relevant += 1
        if "fallback" in model_used:
            total_fallback += 1

        relevance_flag = "RELEVANT" if relevant else "skip"
        print(f"  [{relevance_flag}] score={score}/10 | {title[:55]} | {model_used}")

        time.sleep(DELAY_BETWEEN_CALLS)

    conn.close()

    # Final summary
    print("\n" + "-" * 40)
    print(f"Routing complete.")
    print(f"  Articles scored    : {total_scored}")
    print(f"  Relevant (>=7)     : {total_relevant}")
    print(f"  Not relevant (<7)  : {total_scored - total_relevant}")
    print(f"  Fallback model used: {total_fallback}")
    print(f"  Total tokens used  : {total_tokens if total_tokens else 'unavailable'}")


if __name__ == "__main__":
    main()
