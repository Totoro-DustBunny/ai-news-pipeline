/**
 * tab1.js — Pipeline & Sources tab
 * Fetches /api/stats and populates the two dynamic stat cards.
 */
(async function initTab1() {
  try {
    const stats = await window.fetchData('/api/stats');

    const totalEl    = document.getElementById('stat-total');
    const relevantEl = document.getElementById('stat-relevant');

    if (totalEl)    totalEl.textContent    = stats.total.toLocaleString();
    if (relevantEl) relevantEl.textContent = stats.relevant.toLocaleString();

  } catch (err) {
    console.error('[Tab 1] Failed to load stats:', err);
  }
})();
