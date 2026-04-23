"""
generate_linkedin.py — LinkedIn post generator
Uses OpenRouter (llama-4-maverick) to produce 3 thought-leadership
LinkedIn posts — one per classification category — grounded in
live articles from storage/articles.db.

Saves results to data/linkedin_posts.json.
"""

import json
import os
import re
import sqlite3
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR    = Path(__file__).parent.parent
DB_PATH     = ROOT_DIR / "storage" / "articles.db"
OUTPUT_PATH = ROOT_DIR / "data" / "linkedin_posts.json"

MODEL = "meta-llama/llama-4-maverick"

OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/ai-news-pipeline",
    "X-Title":      "AI News Pipeline - LinkedIn Generator",
}

TARGET_CATEGORIES = [
    "AI Trends & Market Movements",
    "New AI Tools & Product Launches",
    "Practical AI Use Cases",
]

# Category color mapping (matches Tab 3)
CATEGORY_COLORS = {
    "New AI Tools & Product Launches":  "#6B9BD2",
    "AI Trends & Market Movements":     "#8B8B35",
    "Practical AI Use Cases":           "#8BBFCC",
    "Foundation Models & Platforms":    "#C9B882",
    "AI Governance & Ethics":           "#8B7FA3",
}

SYSTEM_PROMPT = """You are an expert LinkedIn content strategist specializing in AI and technology thought leadership. You write for an audience of senior professionals, SaaS founders, and business decision-makers.

Your posts follow this anatomy (the LinkedIn Post Anatomy Checklist):
1. HOOK: Open with a bold claim, surprising stat, or provocative question. Must work as a standalone sentence.
2. CONTEXT: 1-2 sentences explaining why this matters right now.
3. INSIGHT BODY: 3-5 short scannable bullet points or short paragraphs. Mobile-optimized. One idea per line.
4. CREDIBILITY SIGNAL: Anchor one point with a real data point, named tool, or concrete outcome.
5. BUSINESS IMPLICATION: One sentence on what this means for founders, executives, or investors.
6. ENGAGEMENT CLOSER: End with a direct question or provocation.
7. FORMAT: 180-280 words total. 3-5 relevant hashtags at the end.

Write in a voice that blends Cassie Kozyrkov's analytical precision, Andrew Ng's instructional clarity, and Allie K. Miller's data-grounded directness. Avoid corporate buzzwords."""

USER_PROMPT_TEMPLATE = """Write a LinkedIn post for the category: {category}.
Target audience: Tech-savvy professionals, SaaS founders, and business leaders interested in AI adoption.
Tone: Thought leadership — authoritative but accessible.

Use the following recent AI news articles as source material for facts, context, and examples:
{articles}

Do not fabricate statistics. Only reference tools, companies, or data points that appear in the source articles above."""

META_PROMPT_TEMPLATE = """You just wrote a LinkedIn post about {category}. Now provide three short metadata items about it.

Respond in valid JSON only, with exactly these three fields:
{{
  "image_brief": "A 2-sentence description of an image or visual that would accompany this post (e.g. a chart concept, an illustration style, a data visualization idea).",
  "target_audience": "One sentence describing who this post is for.",
  "tone": "One short phrase describing the tone (e.g. 'Thought leadership — analytical')."
}}"""


# ── DB helpers ────────────────────────────────────────────────────────────────

def fetch_source_articles(category: str, limit: int = 5) -> list[dict]:
    """Return up to `limit` relevant articles for the given category."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, relevance_reason
        FROM   articles
        WHERE  is_relevant = 1
          AND  category    = ?
        ORDER  BY published_date DESC
        LIMIT  ?
        """,
        (category, limit),
    )
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def format_articles_block(articles: list[dict]) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        title   = a.get("title", "(no title)")
        summary = a.get("relevance_reason", "")
        lines.append(f"{i}. {title}")
        if summary:
            lines.append(f"   Summary: {summary}")
    return "\n".join(lines)


# ── LLM helpers ───────────────────────────────────────────────────────────────

def make_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY not found in environment.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=OPENROUTER_HEADERS,
    )


def sanitize_json(raw: str) -> dict:
    """Strip markdown fences, then extract and parse the first JSON object."""
    raw = re.sub(r"```(?:json)?", "", raw).strip("`").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError(f"No JSON object found in response:\n{raw[:300]}")
    return json.loads(match.group())


def call_llm(client: OpenAI, messages: list[dict], label: str = "") -> str:
    tag = f"[{label}] " if label else ""
    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.8,
            max_tokens=700,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"  {tag}LLM error: {e}")
        raise


# ── Post generation ───────────────────────────────────────────────────────────

def generate_post(client: OpenAI, category: str) -> dict:
    print(f"\n  Fetching source articles for '{category}'...")
    articles = fetch_source_articles(category, limit=5)
    if not articles:
        print(f"  [WARN] No articles found for '{category}'. Skipping source material.")
    article_block = format_articles_block(articles) if articles else "(No source articles available.)"

    # Step 1: generate the post body
    print(f"  Generating post content...")
    post_content = call_llm(
        client,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT_TEMPLATE.format(
                category=category,
                articles=article_block,
            )},
        ],
        label="post",
    )

    # Step 2: generate metadata
    print(f"  Generating metadata (image brief, audience, tone)...")
    time.sleep(0.5)
    meta_raw = call_llm(
        client,
        messages=[
            {"role": "system", "content": "You are a helpful assistant. Respond only in valid JSON."},
            {"role": "user",   "content": META_PROMPT_TEMPLATE.format(category=category)},
        ],
        label="meta",
    )
    try:
        meta = sanitize_json(meta_raw)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"  [WARN] Metadata parse failed ({e}). Using defaults.")
        meta = {
            "image_brief":     "A clean, minimal data visualization related to AI trends.",
            "target_audience": "AI-curious professionals and SaaS founders.",
            "tone":            "Thought leadership — analytical",
        }

    return {
        "category":        category,
        "color":           CATEGORY_COLORS.get(category, "#aaa"),
        "content":         post_content,
        "image_brief":     meta.get("image_brief",     ""),
        "target_audience": meta.get("target_audience", ""),
        "tone":            meta.get("tone",            ""),
        "source_articles": [a["title"] for a in articles],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    client = make_client()
    posts  = []

    for i, category in enumerate(TARGET_CATEGORIES):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(TARGET_CATEGORIES)}] Category: {category}")
        print('='*60)

        post = generate_post(client, category)
        posts.append(post)

        print(f"\n--- GENERATED POST ---")
        print(post["content"])
        print(f"\n  Image brief:     {post['image_brief']}")
        print(f"  Target audience: {post['target_audience']}")
        print(f"  Tone:            {post['tone']}")
        print(f"  Source articles: {len(post['source_articles'])}")

        if i < len(TARGET_CATEGORIES) - 1:
            time.sleep(1.5)

    OUTPUT_PATH.write_text(
        json.dumps({"posts": posts}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\n{'='*60}")
    print(f"Saved {len(posts)} posts to {OUTPUT_PATH}")
    print('='*60)


if __name__ == "__main__":
    main()
