# Classifier module — assigns business category tags to relevant articles via OpenRouter
#
# Why a more capable model than the router?
# Relevance scoring is a binary signal (relevant / not relevant) that a smaller
# model handles well. Classification requires the model to distinguish between
# five nuanced business categories — e.g. telling apart "New AI Tools & Product
# Launches" from "Foundation Models & Platforms" for an article about a GPT-4o
# feature update. A stronger model reduces miscategorisation and produces more
# reliable confidence scores for downstream filtering.
#
# Model selection (as of 2026-04):
#   Primary  — meta-llama/llama-4-maverick ($0.19/M)
#              Newer generation than Llama 3.3, better instruction-following,
#              confirmed clean JSON output on OpenRouter.
#   Fallback — meta-llama/llama-3.3-70b-instruct ($0.10/M)
#              The proven router primary; reliable JSON, same provider pathway.

import json
import re
import sqlite3
import time
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import os

# ── Path constants ─────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).resolve().parent.parent
DB_PATH     = ROOT_DIR / "storage" / "articles.db"
PROMPT_PATH = ROOT_DIR / "prompts" / "classification_prompt.txt"

# ── Model config ───────────────────────────────────────────────────────────────
PRIMARY_MODEL  = "meta-llama/llama-4-maverick"       # stronger; better category distinction
FALLBACK_MODEL = "meta-llama/llama-3.3-70b-instruct" # proven fallback; same provider pathway

# Valid category names — used to validate model output before writing to DB
VALID_CATEGORIES = {
    "New AI Tools & Product Launches",
    "AI Trends & Market Movements",
    "Practical AI Use Cases",
    "Foundation Models & Platforms",
    "AI Governance & Ethics",
}

# OpenRouter requires these headers for routing analytics and abuse prevention
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/ai-news-pipeline",
    "X-Title":      "AI News Pipeline - Classifier",
}

DELAY_BETWEEN_CALLS = 0.5  # seconds — avoid hammering the API


# ── Client setup ───────────────────────────────────────────────────────────────

def init_client() -> OpenAI:
    """
    Load the OpenRouter API key from .env and return an OpenAI-compatible
    client pointed at the OpenRouter base URL.
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
    """Read the classification prompt template from disk."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# ── Response sanitizer ─────────────────────────────────────────────────────────

def sanitize_json_response(raw: str) -> str:
    """
    Clean up common LLM output artifacts before attempting JSON parsing.
    Mirrors the sanitizer in router.py — see that module for full rationale.
      1. Strip markdown code fences
      2. Remove '!!!!' noise runs (Llama artifact)
      3. Extract the first complete {...} block
    """
    # 1. Strip markdown fences
    if "```" in raw:
        parts = raw.split("```")
        raw = parts[1].lstrip("json").strip() if len(parts) >= 2 else raw

    # 2. Remove runs of '!' — known Llama output artifact
    raw = re.sub(r"!+", "", raw)

    # 3. Extract the first complete JSON object, discarding preamble/postamble
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    return raw.strip()


# ── LLM call with fallback ─────────────────────────────────────────────────────

def classify_article(
    client: OpenAI,
    prompt_template: str,
    title: str,
    summary: str,
) -> tuple[dict | None, str]:
    """
    Send a relevant article to the LLM for category classification.

    Tries the primary model first. If the call fails, the JSON is unparseable,
    or the returned category is not one of the five valid options, retries once
    with the fallback model.

    Returns:
        (parsed_result, model_label)
        parsed_result is None if both attempts fail.
    """
    filled_prompt = prompt_template.format(title=title, summary=summary or "(no summary)")

    for attempt, model in enumerate([PRIMARY_MODEL, FALLBACK_MODEL]):
        label = "primary" if attempt == 0 else "fallback"
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": filled_prompt}],
                temperature=0.0,  # deterministic — we want consistent categorisation
                max_tokens=200,   # slightly more headroom than the router for longer reasons
            )

            raw = response.choices[0].message.content.strip()

            # Sanitize before parsing
            raw = sanitize_json_response(raw)

            result = json.loads(raw)

            # Validate required fields exist
            if not all(k in result for k in ("category", "confidence", "classification_reason")):
                raise ValueError(f"Missing fields in response: {result}")

            # Validate the returned category is one of the five allowed values
            if result["category"] not in VALID_CATEGORIES:
                raise ValueError(
                    f"Invalid category returned: {result['category']!r}. "
                    f"Expected one of: {VALID_CATEGORIES}"
                )

            return result, f"{label} ({model})"

        except json.JSONDecodeError as e:
            print(f"    [WARN] JSON parse error on {label} model: {e}")
            print(f"    [WARN] Raw response: {raw!r}")
            if attempt == 1:
                return None, "both models failed"

        except Exception as e:
            print(f"    [WARN] Error on {label} model ({model}): {e}")
            if attempt == 1:
                return None, "both models failed"

        # Brief pause before fallback attempt
        if attempt == 0:
            time.sleep(0.5)

    return None, "both models failed"


# ── Database helpers ───────────────────────────────────────────────────────────

def fetch_unclassified(conn: sqlite3.Connection) -> list[dict]:
    """
    Return all articles that passed the relevance filter but have not yet
    been assigned a category (is_relevant = 1 AND category IS NULL).
    """
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, title, summary
        FROM   articles
        WHERE  is_relevant = 1
        AND    category IS NULL
        """
    ).fetchall()
    return [dict(row) for row in rows]


def update_article_category(
    conn: sqlite3.Connection,
    article_id: int,
    category: str,
    classification_reason: str,
) -> None:
    """Write the classification result back to the article row."""
    conn.execute(
        """
        UPDATE articles
        SET category              = :category,
            classification_reason = :reason
        WHERE id = :id
        """,
        {
            "category": category,
            "reason":   classification_reason,
            "id":       article_id,
        },
    )
    conn.commit()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== AI News Pipeline - Classifier ===\n")

    client          = init_client()
    prompt_template = load_prompt(PROMPT_PATH)
    conn            = sqlite3.connect(DB_PATH)

    articles = fetch_unclassified(conn)
    print(f"Found {len(articles)} relevant unclassified article(s) to process.\n")

    if not articles:
        print("Nothing to classify. Run ingest.py then router.py first.")
        conn.close()
        return

    total_classified = 0
    total_fallback   = 0
    category_counts  = defaultdict(int)

    for article in articles:
        aid     = article["id"]
        title   = article["title"] or "(no title)"
        summary = article["summary"] or ""

        result, model_used = classify_article(client, prompt_template, title, summary)

        if result is None:
            print(f"  [ERROR] Could not classify article {aid}: \"{title[:60]}\"")
            continue

        category = result["category"]
        confidence = int(result["confidence"])
        reason   = result["classification_reason"]

        update_article_category(conn, aid, category, reason)

        total_classified     += 1
        category_counts[category] += 1
        if "fallback" in model_used:
            total_fallback += 1

        print(f"  [{category}]  conf={confidence}/10  |  {title[:50]}  |  {model_used}")

        time.sleep(DELAY_BETWEEN_CALLS)

    conn.close()

    # Final summary
    print("\n" + "-" * 40)
    print(f"Classification complete.")
    print(f"  Articles classified  : {total_classified}")
    print(f"  Fallback model used  : {total_fallback}")
    print(f"\n  Breakdown by category:")
    for cat, count in sorted(category_counts.items(), key=lambda x: -x[1]):
        bar = "#" * count
        print(f"    {count:>3}  {bar:<20}  {cat}")


if __name__ == "__main__":
    main()
