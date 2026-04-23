"""
fetch_kol_posts.py — KOL web search script
Searches DuckDuckGo for recent LinkedIn posts from 5 AI KOLs,
collects up to 3 results per KOL, and saves to data/kol_posts.json.
"""

import json
import time
from pathlib import Path
from ddgs import DDGS

# ── KOL definitions ──────────────────────────────────────────────────────────

KOLS = [
    {
        "name":         "Cassie Kozyrkov",
        "title":        "Chief Decision Scientist · Google | AI & Statistics",
        "linkedin_url": "https://www.linkedin.com/in/cassie-kozyrkov/",
        "focus_areas":  ["Decision Science", "AI Strategy", "Statistics"],
        "queries": [
            "Cassie Kozyrkov LinkedIn AI post 2024",
            "Cassie Kozyrkov artificial intelligence insights LinkedIn",
        ],
    },
    {
        "name":         "Andrew Ng",
        "title":        "Founder · DeepLearning.AI | AI Education & Research",
        "linkedin_url": "https://www.linkedin.com/in/andrewyng/",
        "focus_areas":  ["Deep Learning", "AI Education", "LLMs"],
        "queries": [
            "Andrew Ng LinkedIn AI post 2024",
            "Andrew Ng machine learning insights LinkedIn",
        ],
    },
    {
        "name":         "Allie K. Miller",
        "title":        "AI Entrepreneur & Advisor | Former Amazon & IBM",
        "linkedin_url": "https://www.linkedin.com/in/alliekmiller/",
        "focus_areas":  ["AI Products", "Business Strategy", "Startups"],
        "queries": [
            "Allie K. Miller LinkedIn AI post 2024",
            "Allie Miller AI business LinkedIn insights",
        ],
    },
    {
        "name":         "Kirk Borne",
        "title":        "Chief Science Officer · DataPrime | Data & AI Thought Leader",
        "linkedin_url": "https://www.linkedin.com/in/kirkdborne/",
        "focus_areas":  ["Data Science", "Machine Learning", "AI Trends"],
        "queries": [
            "Kirk Borne LinkedIn AI data science post 2024",
            "Kirk Borne artificial intelligence trends LinkedIn",
        ],
    },
    {
        "name":         "Steve Nouri",
        "title":        "AI & Technology Executive | Global AI Ambassador",
        "linkedin_url": "https://www.linkedin.com/in/stevenouri/",
        "focus_areas":  ["AI Leadership", "Future of Work", "Generative AI"],
        "queries": [
            "Steve Nouri LinkedIn AI post 2024",
            "Steve Nouri generative AI insights LinkedIn",
        ],
    },
]

MAX_POSTS_PER_KOL    = 3
DELAY_BETWEEN_QUERIES = 1.2   # seconds between individual queries
DELAY_BETWEEN_KOLS    = 2.0   # seconds between KOLs

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "kol_posts.json"


def search_kol(kol: dict) -> list[dict]:
    """Run all queries for one KOL and return deduplicated post dicts."""
    posts_seen_urls: set[str] = set()
    posts: list[dict] = []

    for query in kol["queries"]:
        if len(posts) >= MAX_POSTS_PER_KOL:
            break
        try:
            results = DDGS().text(query, max_results=5)
            for r in results:
                if len(posts) >= MAX_POSTS_PER_KOL:
                    break
                url = r.get("href") or r.get("url", "")
                if not url or url in posts_seen_urls:
                    continue
                posts_seen_urls.add(url)
                posts.append({
                    "title":   r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url":     url,
                    "date":    r.get("published", "None"),
                })
        except Exception as e:
            print(f"  [WARN] Query failed for '{query}': {e}")
        time.sleep(DELAY_BETWEEN_QUERIES)

    return posts


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    kol_data = []
    for i, kol in enumerate(KOLS):
        print(f"[{i+1}/{len(KOLS)}] Searching posts for: {kol['name']}...")
        posts = search_kol(kol)
        print(f"       Found {len(posts)} post(s).")
        kol_entry = {k: v for k, v in kol.items() if k != "queries"}
        kol_entry["posts"] = posts
        kol_data.append(kol_entry)
        if i < len(KOLS) - 1:
            time.sleep(DELAY_BETWEEN_KOLS)

    payload = {"kols": kol_data}
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\nSaved {len(kol_data)} KOL profiles to {OUTPUT_PATH}")
    total_posts = sum(len(k["posts"]) for k in kol_data)
    print(f"Total posts collected: {total_posts}")


if __name__ == "__main__":
    main()
