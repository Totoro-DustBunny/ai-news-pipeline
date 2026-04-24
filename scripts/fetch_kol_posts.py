"""
fetch_kol_posts.py — KOL web search + dynamic writing style extraction
Runs 3 targeted DuckDuckGo searches per KOL, applies quality filtering,
extracts writing style via OpenRouter, and saves to data/kol_posts.json.
"""

import json
import os
import re
import time
from pathlib import Path

from ddgs import DDGS
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ROOT_DIR    = Path(__file__).parent.parent
OUTPUT_PATH = ROOT_DIR / "data" / "kol_posts.json"

MODEL = "meta-llama/llama-3.3-70b-instruct"
OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://github.com/ai-news-pipeline",
    "X-Title":      "AI News Pipeline - KOL Research",
}

DELAY_BETWEEN_QUERIES = 1.2
DELAY_BETWEEN_KOLS    = 2.0
MAX_POSTS_PER_KOL     = 3

# ── KOL definitions ──────────────────────────────────────────────────────────

KOLS = [
    {
        "name":         "Cassie Kozyrkov",
        "title":        "Chief Decision Scientist · Google | AI & Statistics",
        "linkedin_url": "https://www.linkedin.com/in/cassie-kozyrkov/",
        "focus_areas":  ["Decision Science", "AI Strategy", "Statistics"],
    },
    {
        "name":         "Andrew Ng",
        "title":        "Founder · DeepLearning.AI | AI Education & Research",
        "linkedin_url": "https://www.linkedin.com/in/andrewyng/",
        "focus_areas":  ["Deep Learning", "AI Education", "LLMs"],
    },
    {
        "name":         "Allie K. Miller",
        "title":        "AI Entrepreneur & Advisor | Former Amazon & IBM",
        "linkedin_url": "https://www.linkedin.com/in/alliekmiller/",
        "focus_areas":  ["AI Products", "Business Strategy", "Startups"],
    },
    {
        "name":         "Kirk Borne",
        "title":        "Chief Science Officer · DataPrime | Data & AI Thought Leader",
        "linkedin_url": "https://www.linkedin.com/in/kirkdborne/",
        "focus_areas":  ["Data Science", "Machine Learning", "AI Trends"],
    },
    {
        "name":         "Steve Nouri",
        "title":        "AI & Technology Executive | Global AI Ambassador",
        "linkedin_url": "https://www.linkedin.com/in/stevenouri/",
        "focus_areas":  ["AI Leadership", "Future of Work", "Generative AI"],
    },
]

# ── Hardcoded fallback styles ─────────────────────────────────────────────────

FALLBACK_STYLES: dict[str, dict] = {
    "Cassie Kozyrkov": {
        "hook_style":   "Opens with a bold counter-intuitive claim or rhetorical question that challenges mainstream assumptions",
        "structure":    "Short punchy paragraphs, heavy use of line breaks, numbered insights, emoji for visual scanning",
        "credibility":  "Draws on Google-scale experience, statistical rigor, and named research",
        "engagement":   "Ends with a provocative question or direct challenge to the reader",
        "style_tag":    "Contrarian + Instructional",
        "confidence":   6,
    },
    "Andrew Ng": {
        "hook_style":   "Opens with a concrete field observation or surprising AI adoption data point",
        "structure":    "Narrative flow with clear sections and analogies to simplify complex ideas",
        "credibility":  "Cites real course data, student outcomes, and industry partnerships",
        "engagement":   "Closes with an invitation to learn more — links to course, paper, or resource",
        "style_tag":    "Instructional + Narrative",
        "confidence":   6,
    },
    "Allie K. Miller": {
        "hook_style":   "Opens with a punchy stat, product launch hook, or first-person market observation",
        "structure":    "Scannable bullet lists, bold keyword highlighting, mobile-optimized formatting",
        "credibility":  "References specific companies, tools, and dollar figures grounded in market reality",
        "engagement":   "Direct CTAs — asks followers to share, comment, or tag someone",
        "style_tag":    "Concise + Data-driven",
        "confidence":   6,
    },
    "Kirk Borne": {
        "hook_style":   "Leads with a thought-provoking quote, fascinating data point, or trending AI topic",
        "structure":    "Curated list format, thread-style posts with emoji bullets, high information density",
        "credibility":  "Astrophysics and data science background lends cross-domain authority",
        "engagement":   "Uses hashtag strategy and asks community for their take",
        "style_tag":    "Curated + Educational",
        "confidence":   6,
    },
    "Steve Nouri": {
        "hook_style":   "Opens with a bold statement about AI's direction or what most people are getting wrong",
        "structure":    "Clean numbered lists, visual metaphors, accessible language for broad audiences",
        "credibility":  "Founder narrative, large following as social proof, references AI tools by name",
        "engagement":   "Ends with a community question or invitation to follow for more AI insights",
        "style_tag":    "Visionary + Accessible",
        "confidence":   6,
    },
}

# ── Filter helpers ────────────────────────────────────────────────────────────

DISCARD_TITLE_PHRASES = [
    "interview with", "profile of", "named to",
    "recognized as", "according to",
]

FIRST_PERSON_TOKENS = ["I ", "I've ", "I'm ", "we ", "my "]


def build_queries(kol: dict) -> list[str]:
    name = kol["name"]
    return [
        f'site:linkedin.com "{name}" 2026',
        f'"{name}" "linkedin.com/posts" AI 2026',
        f'"{name}" linkedin AI post January OR February OR March OR April 2026',
    ]


def passes_filter(result: dict, kol: dict) -> bool:
    """Return True if this result should be kept."""
    url     = result.get("href") or result.get("url", "")
    title   = (result.get("title") or "").lower()
    snippet = result.get("body") or ""

    # ── Discard rules ─────────────────────────────────────────────────────────
    if len(snippet) < 60:
        return False
    for phrase in DISCARD_TITLE_PHRASES:
        if phrase in title:
            return False
    # Discard the KOL's own homepage / about page
    homepage = kol["linkedin_url"].rstrip("/")
    if url.rstrip("/") in (homepage, homepage + "/about"):
        return False

    # ── Keep rules ────────────────────────────────────────────────────────────
    if "linkedin.com/posts" in url:
        return True
    if "linkedin.com" in url:
        return True
    if any(tok in snippet for tok in FIRST_PERSON_TOKENS):
        return True
    if len(snippet) > 100:
        return True

    return False


def make_placeholder(kol: dict) -> dict:
    focus = ", ".join(kol["focus_areas"][:2])
    return {
        "title":          "Post not retrievable — LinkedIn blocks indexing",
        "snippet":        f"This KOL is known for posting about {focus}. Visit their LinkedIn profile directly for recent posts.",
        "url":            kol["linkedin_url"],
        "date":           "2026",
        "is_placeholder": True,
    }


# ── Search ────────────────────────────────────────────────────────────────────

def search_kol(kol: dict) -> list[dict]:
    """Run 3 targeted searches, apply quality filter, return top-3 posts."""
    seen_urls:  set[str]  = set()
    candidates: list[dict] = []

    for query in build_queries(kol):
        try:
            results = DDGS().text(query, max_results=5, timelimit="m6") or []
        except Exception as e:
            print(f"  [WARN] Query failed ({query!r}): {e}")
            results = []

        for r in results:
            url = r.get("href") or r.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            if passes_filter(r, kol):
                candidates.append({
                    "title":          r.get("title", ""),
                    "snippet":        r.get("body", ""),
                    "url":            url,
                    "date":           r.get("published", "None"),
                    "is_placeholder": False,
                })

        time.sleep(DELAY_BETWEEN_QUERIES)

    posts = candidates[:MAX_POSTS_PER_KOL]
    while len(posts) < MAX_POSTS_PER_KOL:
        posts.append(make_placeholder(kol))

    return posts


# ── Writing style extraction ──────────────────────────────────────────────────

STYLE_SYSTEM = (
    "You are an expert LinkedIn content analyst. "
    "Analyze the following posts or content snippets from a LinkedIn "
    "thought leader and extract their writing style."
)

STYLE_USER_TEMPLATE = """\
KOL: {name} - {title}
Posts/Snippets:
{snippets}

Analyze and return ONLY a valid JSON object with these fields:
{{
  "hook_style": "<one sentence describing how they open posts>",
  "structure": "<one sentence describing formatting approach>",
  "credibility": "<one sentence describing how they build authority>",
  "engagement": "<one sentence describing their closing/CTA style>",
  "style_tag": "<2-3 word label e.g. Contrarian + Instructional>",
  "confidence": <integer 1-10, how confident based on available data>
}}
Return no other text, no markdown, no preamble.\
"""


def extract_writing_style(client: OpenAI, kol: dict, posts: list[dict]) -> dict | None:
    real_snippets = [
        p["snippet"] for p in posts
        if not p.get("is_placeholder") and p.get("snippet")
    ]
    if not real_snippets:
        return None

    snippets_block = "\n".join(f"- {s}" for s in real_snippets)
    user_msg = STYLE_USER_TEMPLATE.format(
        name=kol["name"], title=kol["title"], snippets=snippets_block
    )

    try:
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": STYLE_SYSTEM},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.3,
            max_tokens=400,
        )
        raw = resp.choices[0].message.content.strip()
        raw = re.sub(r"```(?:json)?", "", raw).strip("`").strip()
        raw = re.sub(r"!+", "", raw)          # strip Llama noise artifacts
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            print(f"  [WARN] No JSON found in style response.")
            return None
        return json.loads(match.group())
    except Exception as e:
        print(f"  [WARN] Style extraction failed: {e}")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv("OPENROUTER_API_KEY")
    client  = None
    if api_key:
        client = OpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers=OPENROUTER_HEADERS,
        )
    else:
        print("[WARN] OPENROUTER_API_KEY not set — will use fallback styles only.")

    kol_data = []

    for i, kol in enumerate(KOLS):
        print(f"\n{'='*56}")
        print(f"[{i+1}/{len(KOLS)}] {kol['name']}")
        print(f"{'='*56}")

        # Step 1: search
        posts        = search_kol(kol)
        real_count   = sum(1 for p in posts if not p.get("is_placeholder"))
        ph_count     = MAX_POSTS_PER_KOL - real_count
        print(f"  Posts: {real_count} real, {ph_count} placeholder(s)")
        for p in posts:
            flag = "[PH]" if p.get("is_placeholder") else "    "
            print(f"  {flag} {p['url'][:72]}")

        # Step 2: extract writing style
        writing_style: dict | None = None
        if client and real_count > 0:
            print(f"  Extracting writing style via OpenRouter...")
            writing_style = extract_writing_style(client, kol, posts)
            time.sleep(0.5)

        if writing_style:
            writing_style["source"] = "dynamic"
            conf = writing_style.get("confidence", "?")
            print(f"  Style: dynamic (confidence {conf}/10, tag: {writing_style.get('style_tag','')})")
        else:
            fallback = FALLBACK_STYLES.get(kol["name"], {})
            writing_style = {**fallback, "source": "fallback"}
            print(f"  Style: fallback")

        entry = dict(kol)          # already excludes "queries" since KOLS have none now
        entry["writing_style"] = writing_style
        entry["posts"]         = posts
        kol_data.append(entry)

        if i < len(KOLS) - 1:
            time.sleep(DELAY_BETWEEN_KOLS)

    payload = {"kols": kol_data}
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    total_real     = sum(sum(1 for p in k["posts"] if not p.get("is_placeholder")) for k in kol_data)
    dynamic_styles = sum(1 for k in kol_data if k["writing_style"].get("source") == "dynamic")
    print(f"\n{'='*56}")
    print(f"Saved {len(kol_data)} KOL profiles to {OUTPUT_PATH}")
    print(f"Real posts: {total_real} | Dynamic styles extracted: {dynamic_styles}/{len(kol_data)}")
    print(f"{'='*56}")


if __name__ == "__main__":
    main()
