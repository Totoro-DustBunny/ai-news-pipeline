"""
generate_linkedin.py — LinkedIn post generator with DALL-E 3 image generation
Uses OpenRouter (llama-4-maverick) to produce 3 thought-leadership LinkedIn posts
— one per classification category — grounded in live articles from articles.db.
Uses OpenAI DALL-E 3 to generate a matching 16:9 image for each post.

Saves results to data/linkedin_posts.json.
Images saved to static/images/linkedin/post_{slug}.png.
"""

import io
import json
import os
import re
import sqlite3
import time
from pathlib import Path

import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

# ── Config ───────────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR    = Path(__file__).parent.parent
DB_PATH     = ROOT_DIR / "storage" / "articles.db"
OUTPUT_PATH = ROOT_DIR / "data" / "linkedin_posts.json"
IMAGES_DIR  = ROOT_DIR / "static" / "images" / "linkedin"

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


# ── Slug helper ───────────────────────────────────────────────────────────────

def make_slug(category: str) -> str:
    """'AI Trends & Market Movements' → 'ai_trends_market_movements'"""
    slug = category.lower()
    slug = re.sub(r"[^a-z0-9\s]", " ", slug)   # replace & and special chars with space
    slug = re.sub(r"\s+", "_", slug.strip())     # collapse whitespace to underscore
    return slug


# ── DB helpers ────────────────────────────────────────────────────────────────

def fetch_source_articles(category: str, limit: int = 5) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT title, url, relevance_reason
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

def make_openrouter_client() -> OpenAI:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENROUTER_API_KEY not found in environment.")
    return OpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers=OPENROUTER_HEADERS,
    )


def make_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY not found in environment.")
    return OpenAI(api_key=api_key)


def sanitize_json(raw: str) -> dict:
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


# ── Image generation ──────────────────────────────────────────────────────────

def generate_image(openai_client: OpenAI, brief: str, slug: str) -> str | None:
    """
    Generate a 1792x1024 PNG via DALL-E 3 and return the relative web path.
    Returns None if the file already exists (skip) or on any API failure.
    """
    output_path = IMAGES_DIR / f"post_{slug}.png"
    rel_path    = f"/static/images/linkedin/post_{slug}.png"

    # Per-post skip check
    if output_path.exists():
        print(f"  [SKIP] Image already exists — skipping.")
        return rel_path

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    image_prompt = f"""
Professional LinkedIn thought leadership illustration.
Style: clean, modern, minimal infographic aesthetic.
White or very light background.
Color palette: deep navy (#3D3B47), steel blue (#6B9BD2), warm gold (#C9B882), muted cyan (#8BBFCC).
No text overlays. No realistic human faces.
No stock photo aesthetic.
Concept: {brief}
Conveys innovation, data, or business transformation.
Flat design or subtle geometric shapes preferred.
Suitable for a professional LinkedIn post header.
"""

    try:
        response = openai_client.images.generate(
            model="dall-e-3",
            prompt=image_prompt,
            size="1792x1024",
            quality="standard",
            n=1,
            response_format="url",
        )
        image_url = response.data[0].url
        img_bytes = requests.get(image_url, timeout=30).content
        img = Image.open(io.BytesIO(img_bytes))
        img.save(output_path, "PNG")
        print(f"  [OK] Image saved: {output_path.name}")
        return rel_path
    except Exception as e:
        print(f"  [FAIL] Image generation failed: {e}")
        return None


# ── Post generation ───────────────────────────────────────────────────────────

def generate_post(llm_client: OpenAI, category: str) -> dict:
    print(f"\n  Fetching source articles for '{category}'...")
    articles = fetch_source_articles(category, limit=5)
    if not articles:
        print(f"  [WARN] No articles found for '{category}'. Skipping source material.")
    article_block = format_articles_block(articles) if articles else "(No source articles available.)"

    print(f"  Generating post content...")
    post_content = call_llm(
        llm_client,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": USER_PROMPT_TEMPLATE.format(
                category=category,
                articles=article_block,
            )},
        ],
        label="post",
    )

    print(f"  Generating metadata (image brief, audience, tone)...")
    time.sleep(0.5)
    meta_raw = call_llm(
        llm_client,
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
        "image_path":      None,   # filled in main() after image generation
        "target_audience": meta.get("target_audience", ""),
        "tone":            meta.get("tone",            ""),
        "source_articles": [{"title": a["title"], "url": a.get("url")} for a in articles],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    llm_client    = make_openrouter_client()
    openai_client = make_openai_client()

    posts        = []
    image_results: list[tuple[str, str | None]] = []  # (category, path_or_None)

    for i, category in enumerate(TARGET_CATEGORIES):
        print(f"\n{'='*60}")
        print(f"[{i+1}/{len(TARGET_CATEGORIES)}] Category: {category}")
        print('='*60)

        post = generate_post(llm_client, category)

        print(f"  Generating image for '{category}'...")
        slug       = make_slug(category)
        image_path = generate_image(openai_client, post["image_brief"], slug)
        post["image_path"] = image_path
        image_results.append((category, image_path))

        posts.append(post)

        print(f"\n--- GENERATED POST ---")
        print(post["content"])
        print(f"\n  Target audience: {post['target_audience']}")
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
    print(f"\nImage generation summary:")
    for idx, (cat, path) in enumerate(image_results, 1):
        if path and (ROOT_DIR / path.lstrip("/")).exists():
            print(f"  Post {idx} [{cat}]: [OK] Saved -> {path}")
        elif path and path.startswith("/static"):
            print(f"  Post {idx} [{cat}]: [OK] Already exists -> {path}")
        else:
            print(f"  Post {idx} [{cat}]: [FAIL] Failed or skipped")
    print('='*60)


if __name__ == "__main__":
    main()
