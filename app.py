# app.py — Flask entry point for the AI News Pipeline web interface

import json
import sqlite3
from pathlib import Path
from flask import Flask, jsonify, render_template

app = Flask(__name__)

# ── Path constants ─────────────────────────────────────────────────────────────
ROOT_DIR   = Path(__file__).resolve().parent
DB_PATH    = ROOT_DIR / "storage" / "articles.db"
KOL_PATH   = ROOT_DIR / "data" / "kol_posts.json"
LI_PATH    = ROOT_DIR / "data" / "linkedin_posts.json"


# ── DB helper ──────────────────────────────────────────────────────────────────

def get_db():
    """Open a SQLite connection with row-as-dict factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/articles")
def api_articles():
    """Return all articles from the database as a JSON array."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM articles ORDER BY ingested_at DESC").fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/stats")
def api_stats():
    """
    Return summary statistics computed directly from the database:
      - total articles
      - relevant count
      - category breakdown (relevant articles only)
      - source breakdown (all articles)
    """
    conn = get_db()

    total = conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0]

    relevant = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant = 1"
    ).fetchone()[0]

    not_relevant = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant = 0"
    ).fetchone()[0]

    unscored = conn.execute(
        "SELECT COUNT(*) FROM articles WHERE is_relevant IS NULL"
    ).fetchone()[0]

    # Category breakdown — relevant articles only
    cat_rows = conn.execute(
        """
        SELECT   category, COUNT(*) AS count
        FROM     articles
        WHERE    is_relevant = 1
        GROUP BY category
        ORDER BY count DESC
        """
    ).fetchall()

    # Source breakdown — all ingested articles
    src_rows = conn.execute(
        """
        SELECT   source_name, source_category, COUNT(*) AS count
        FROM     articles
        GROUP BY source_name
        ORDER BY count DESC
        """
    ).fetchall()

    # Relevance score distribution (buckets 1–3, 4–6, 7–10)
    score_rows = conn.execute(
        """
        SELECT   relevance_score, COUNT(*) AS count
        FROM     articles
        WHERE    relevance_score IS NOT NULL
        GROUP BY relevance_score
        ORDER BY relevance_score
        """
    ).fetchall()

    conn.close()

    return jsonify({
        "total":        total,
        "relevant":     relevant,
        "not_relevant": not_relevant,
        "unscored":     unscored,
        "categories":   [dict(r) for r in cat_rows],
        "sources":      [dict(r) for r in src_rows],
        "score_dist":   [dict(r) for r in score_rows],
    })


@app.route("/api/kol-posts")
def api_kol_posts():
    """Return KOL posts from data/kol_posts.json, or a placeholder if not yet generated."""
    if not KOL_PATH.exists():
        return jsonify({"status": "not_generated", "data": []})
    with open(KOL_PATH, "r", encoding="utf-8") as f:
        return jsonify({"status": "ok", "data": json.load(f)})


@app.route("/api/linkedin-posts")
def api_linkedin_posts():
    """Return LinkedIn posts from data/linkedin_posts.json, or a placeholder if not yet generated."""
    if not LI_PATH.exists():
        return jsonify({"status": "not_generated", "data": []})
    with open(LI_PATH, "r", encoding="utf-8") as f:
        return jsonify({"status": "ok", "data": json.load(f)})


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)
