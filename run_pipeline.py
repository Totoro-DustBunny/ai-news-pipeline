# run_pipeline.py — end-to-end runner for the AI News Pipeline
#
# Executes the three pipeline stages in order:
#   1. ingest     — fetch articles from RSS feeds → store in SQLite
#   2. router     — score each article for relevance via OpenRouter LLM
#   3. classifier — assign a business category to each relevant article
#
# Run with:  python run_pipeline.py

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from dotenv import load_dotenv
import os

# ── Pre-flight checks ──────────────────────────────────────────────────────────

def preflight_checks() -> None:
    """Abort early if required config is missing."""
    root = Path(__file__).resolve().parent
    env_path = root / ".env"

    # Check .env file exists
    if not env_path.exists():
        print("[ERROR] .env file not found. Copy .env.example to .env and add your OPENROUTER_API_KEY.")
        sys.exit(1)

    # Check API key is populated
    load_dotenv(env_path)
    if not os.getenv("OPENROUTER_API_KEY"):
        print("[ERROR] OPENROUTER_API_KEY is missing from .env.")
        sys.exit(1)

    print("Pre-flight checks passed.\n")


# ── Stage runner ───────────────────────────────────────────────────────────────

def run_stage(label: str, fn) -> None:
    """Print a stage header, run the function, print a footer."""
    print("=" * 60)
    print(f"  STAGE: {label}")
    print("=" * 60)
    fn()
    print()


# ── Final DB summary ───────────────────────────────────────────────────────────

def print_final_summary(db_path: Path) -> None:
    """Query the database and print a pipeline-level summary."""
    conn = sqlite3.connect(db_path)

    total_articles = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]
    total_relevant = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant = 1"
    ).fetchone()[0]
    total_not_relevant = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant = 0"
    ).fetchone()[0]
    total_unscored = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant IS NULL"
    ).fetchone()[0]

    # Category breakdown for relevant articles
    rows = conn.execute(
        """
        SELECT   category, COUNT(*) as count
        FROM     articles
        WHERE    is_relevant = 1
        GROUP BY category
        ORDER BY count DESC
        """
    ).fetchall()
    conn.close()

    print("=" * 60)
    print("  PIPELINE SUMMARY")
    print("=" * 60)
    print(f"  Total articles in database : {total_articles}")
    print(f"  Relevant (score >= 7)      : {total_relevant}")
    print(f"  Not relevant (score < 7)   : {total_not_relevant}")
    if total_unscored:
        print(f"  Unscored (errors/skipped)  : {total_unscored}")
    print()
    print("  Relevant articles by category:")
    for category, count in rows:
        bar = "#" * count
        label = category or "(unclassified)"
        print(f"    {count:>3}  {bar:<20}  {label}")
    print("=" * 60)


# ── Entry point ────────────────────────────────────────────────────────────────

def main():
    root    = Path(__file__).resolve().parent
    db_path = root / "storage" / "articles.db"

    print("\n" + "=" * 60)
    print("  AI NEWS PIPELINE — FULL RUN")
    print("=" * 60 + "\n")

    preflight_checks()

    # Import pipeline modules (after preflight so errors surface cleanly)
    from pipeline.ingest     import main as ingest_main
    from pipeline.router     import main as router_main
    from pipeline.classifier import main as classifier_main

    run_stage("1 / 3 — Ingest",      ingest_main)
    run_stage("2 / 3 — Router",      router_main)
    run_stage("3 / 3 — Classifier",  classifier_main)

    print_final_summary(db_path)


if __name__ == "__main__":
    main()
