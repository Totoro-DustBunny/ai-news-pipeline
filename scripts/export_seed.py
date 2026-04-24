"""
export_seed.py — Export current articles.db to a JSON seed file.

Allows the project to be cloned and run without API keys:
the seed data is committed to the repo and loaded automatically
on first run if the database is empty.

Usage:
    python scripts/export_seed.py
Output:
    data/articles_seed.json
"""

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR    = Path(__file__).parent.parent
DB_PATH     = ROOT_DIR / "storage" / "articles.db"
OUTPUT_PATH = ROOT_DIR / "data" / "articles_seed.json"

RELEVANCE_THRESHOLD = 8


def main():
    if not DB_PATH.exists():
        print(f"[ERROR] Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        "SELECT * FROM articles ORDER BY ingested_at DESC"
    ).fetchall()
    conn.close()

    articles = [dict(r) for r in rows]

    payload = {
        "exported_at":    datetime.now(timezone.utc).isoformat(),
        "article_count":  len(articles),
        "articles":       articles,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    relevant = [a for a in articles if (a.get("relevance_score") or 0) >= RELEVANCE_THRESHOLD]
    cat_counts = Counter(
        a["category"] for a in relevant if a.get("category")
    )

    print(f"\n{'='*56}")
    print(f"Seed export complete")
    print(f"{'='*56}")
    print(f"  Total articles exported : {len(articles)}")
    print(f"  Relevant (score >= {RELEVANCE_THRESHOLD})  : {len(relevant)}")
    print(f"\n  Breakdown by category:")
    for cat, count in cat_counts.most_common():
        print(f"    {count:>3}  {cat}")
    print(f"\n  Saved to: {OUTPUT_PATH}")
    print(f"{'='*56}\n")


if __name__ == "__main__":
    main()
