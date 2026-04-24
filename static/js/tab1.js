/**
 * tab1.js — Pipeline & Sources tab
 * Fetches /api/articles and populates the two dynamic stat cards.
 * "Relevant Articles" uses the frontend threshold of score >= 8.
 */
(async function initTab1() {
  const THRESHOLD = 8;

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
})();
