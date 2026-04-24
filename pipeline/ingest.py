# Ingestion module — fetches RSS/Atom feeds and stores raw articles in SQLite

import json
import sqlite3
import feedparser
import yaml
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# ── Path constants ─────────────────────────────────────────────────────────────
ROOT_DIR    = Path(__file__).resolve().parent.parent
SOURCES_CFG = ROOT_DIR / "config" / "sources.yaml"
DB_PATH     = ROOT_DIR / "storage" / "articles.db"
SEED_PATH   = ROOT_DIR / "data" / "articles_seed.json"


# ── Database setup ─────────────────────────────────────────────────────────────

def init_db(db_path: Path) -> sqlite3.Connection:
    """Create the database and articles table if they don't already exist."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            title                TEXT,
            summary              TEXT,
            url                  TEXT UNIQUE,          -- deduplication key
            published_date       TEXT,
            source_name          TEXT,
            source_category      TEXT,
            relevance_score      INTEGER,              -- filled by router.py
            is_relevant          BOOLEAN,              -- filled by router.py
            relevance_reason     TEXT,                 -- filled by router.py
            category             TEXT,                 -- filled by classifier.py
            classification_reason TEXT,               -- filled by classifier.py
            ingested_at          TEXT                  -- ISO 8601 UTC timestamp
        )
    """)
    conn.commit()
    return conn


def reset_db(conn: sqlite3.Connection) -> None:
    """Delete all rows from the articles table to start fresh for today's run."""
    conn.execute("DELETE FROM articles")
    conn.commit()


# ── Source loading ─────────────────────────────────────────────────────────────

def load_sources(config_path: Path) -> list[dict]:
    """Return only the feeds marked enabled: true from sources.yaml."""
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [s for s in config.get("feeds", []) if s.get("enabled", False)]


# ── Feed fetching ──────────────────────────────────────────────────────────────

def fetch_feed(source: dict, cutoff: date) -> tuple[list[dict], int]:
    """
    Fetch and parse one RSS/Atom feed.
    Only returns articles published on or after cutoff date.
    Returns (recent_articles, total_entries_fetched).
    """
    name     = source["name"]
    url      = source["url"]
    category = source["category"]

    print(f"  Fetching: {name} ...")
    feed = feedparser.parse(url)

    # feedparser sets bozo=True when the feed is malformed but still parseable;
    # only bail out if we got nothing useful back.
    if feed.get("status", 0) not in (200, 301, 302) and not feed.entries:
        print(f"    [SKIP] {name} — HTTP {feed.get('status', 'N/A')}")
        return [], 0

    total   = len(feed.entries)
    articles = []

    for entry in feed.entries:
        # Use feedparser's pre-parsed time.struct_time — most reliable across feed formats.
        # Fall back to updated_parsed if published_parsed is absent.
        # Skip the entry entirely if neither is available; we can't date it reliably.
        parsed_time = entry.get("published_parsed") or entry.get("updated_parsed")
        if not parsed_time:
            continue

        entry_date = date(parsed_time.tm_year, parsed_time.tm_mon, parsed_time.tm_mday)
        if entry_date < cutoff:
            continue  # Older than 7-day window — skip silently

        url_ = entry.get("link", "").strip()
        if not url_:
            continue  # Can't deduplicate or link back without a URL

        title   = entry.get("title", "").strip()
        summary = (
            entry.get("summary")
            or entry.get("description")
            or entry.get("content", [{}])[0].get("value", "")
        ).strip()

        published_date = datetime(*parsed_time[:6], tzinfo=timezone.utc).isoformat()

        articles.append({
            "title":           title,
            "summary":         summary,
            "url":             url_,
            "published_date":  published_date,
            "source_name":     name,
            "source_category": category,
        })

    return articles, total


# ── Database insertion ─────────────────────────────────────────────────────────

def insert_articles(conn: sqlite3.Connection, articles: list[dict]) -> int:
    """
    Insert articles into the database.
    Skips duplicates via the UNIQUE constraint on url.
    Returns the count of newly inserted rows.
    """
    ingested_at = datetime.now(timezone.utc).isoformat()
    new_count   = 0

    for article in articles:
        try:
            conn.execute(
                """
                INSERT INTO articles
                    (title, summary, url, published_date, source_name,
                     source_category, ingested_at)
                VALUES
                    (:title, :summary, :url, :published_date, :source_name,
                     :source_category, :ingested_at)
                """,
                {**article, "ingested_at": ingested_at},
            )
            new_count += 1
        except sqlite3.IntegrityError:
            # URL already exists — silently skip
            pass

    conn.commit()
    return new_count


# ── Seed loader ────────────────────────────────────────────────────────────────

def load_seed_if_empty() -> None:
    """
    If the articles table is empty, populate it from data/articles_seed.json.
    Called at the top of main() so a fresh clone shows data immediately.
    Skipped entirely if the DB already has rows.
    """
    conn = init_db(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    if count > 0:
        print("Database already populated — skipping seed load.")
        conn.close()
        return

    if not SEED_PATH.exists():
        print("[WARN] Seed file not found and database is empty — starting with no data.")
        conn.close()
        return

    with open(SEED_PATH, "r", encoding="utf-8") as f:
        seed = json.load(f)

    articles = seed.get("articles", [])
    inserted = 0
    for article in articles:
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO articles
                    (id, title, summary, url, published_date, source_name,
                     source_category, relevance_score, is_relevant, relevance_reason,
                     category, classification_reason, ingested_at)
                VALUES
                    (:id, :title, :summary, :url, :published_date, :source_name,
                     :source_category, :relevance_score, :is_relevant, :relevance_reason,
                     :category, :classification_reason, :ingested_at)
                """,
                article,
            )
            inserted += 1
        except Exception:
            pass

    conn.commit()
    conn.close()
    print(f"Seeded database with {inserted} articles from articles_seed.json")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print("=== AI News Pipeline — Ingestion ===\n")

    # Seed from JSON if the database is empty (first-time clone support)
    load_seed_if_empty()

    today  = date.today()
    cutoff = today - timedelta(days=7)
    print(f"Filtering for articles from the last 7 days (on or after {cutoff})\n")

    # Set up database and reset for a fresh daily run
    conn = init_db(DB_PATH)
    reset_db(conn)
    print(f"Database reset. Starting fresh.\n")

    # Load enabled sources
    sources = load_sources(SOURCES_CFG)
    print(f"Loaded {len(sources)} enabled source(s) from {SOURCES_CFG.name}\n")

    total_fetched = 0   # all entries seen across all feeds
    total_today   = 0   # entries that matched today's date
    total_new     = 0   # entries successfully inserted (not duplicates)

    for source in sources:
        articles, fetched = fetch_feed(source, cutoff)
        total_fetched += fetched
        total_today   += len(articles)

        if not articles:
            print(f"    0 from last 7 days (out of {fetched} entries)\n")
            continue

        new = insert_articles(conn, articles)
        total_new += new
        print(f"    {len(articles)} from last 7 days (out of {fetched} entries), {new} new\n")

    conn.close()

    # Final summary
    print("-" * 40)
    print(f"Ingestion complete ({cutoff} to {today}).")
    print(f"  Total entries fetched  : {total_fetched}")
    print(f"  From last 7 days       : {total_today}")
    print(f"  New articles stored    : {total_new}")
    print(f"  Duplicates skipped     : {total_today - total_new}")
    print(f"  Older articles skipped : {total_fetched - total_today}")


if __name__ == "__main__":
    main()
