/**
 * tab1.js — Pipeline & Sources tab
 * Fetches /api/articles and populates the two dynamic stat cards.
 * Fetches /api/seed-status and renders the data-source banner.
 * "Relevant Articles" uses the frontend threshold of score >= 8.
 */
(async function initTab1() {
  const THRESHOLD = 8;

  // ── Stat cards ──────────────────────────────────────────────────────────────
  try {
    const articles = await window.fetchData('/api/articles');

    const total    = articles.length;
    const relevant = articles.filter(a => (a.relevance_score ?? 0) >= THRESHOLD).length;

    const totalEl    = document.getElementById('stat-total');
    const relevantEl = document.getElementById('stat-relevant');

    if (totalEl)    totalEl.textContent    = total.toLocaleString();
    if (relevantEl) relevantEl.textContent = relevant.toLocaleString();

  } catch (err) {
    console.error('[Tab 1] Failed to load stats:', err);
  }

  // ── Seed-status banner ──────────────────────────────────────────────────────
  const banner = document.getElementById('seed-status-banner');
  if (!banner) return;

  try {
    const s = await fetch('/api/seed-status').then(r => r.json());

    // Determine state: seeded (A) or live (B)
    const isSeeded = s.seed_file_exists &&
                     s.database_article_count === s.seed_article_count;

    // Format the timestamp nicely
    function fmtDate(iso) {
      if (!iso) return 'unknown date';
      try {
        return new Date(iso).toLocaleDateString('en-US',
          { year: 'numeric', month: 'long', day: 'numeric' });
      } catch { return iso; }
    }

    const dateStr = fmtDate(s.pipeline_last_run);

    if (isSeeded) {
      // STATE A — amber — pre-collected data
      banner.innerHTML = `
        <div class="seed-banner seed-banner-amber">
          <span class="seed-banner-icon">&#128230;</span>
          <div class="seed-banner-text">
            <strong>Showing pre-collected data</strong> from ${dateStr}.
            To refresh with live articles, run
            <code>python run_pipeline.py</code> with your own API keys.
          </div>
        </div>`;
    } else {
      // STATE B — green — live pipeline data
      banner.innerHTML = `
        <div class="seed-banner seed-banner-green">
          <span class="seed-banner-icon">&#9989;</span>
          <div class="seed-banner-text">
            <strong>Live data</strong> &mdash; last pipeline run: ${dateStr}.
            ${s.database_article_count.toLocaleString()} articles ingested.
          </div>
        </div>`;
    }
  } catch (err) {
    console.warn('[Tab 1] Could not load seed status:', err);
  }
})();
