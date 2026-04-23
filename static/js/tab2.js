/**
 * tab2.js — Relevance Scoring tab
 * Fetches /api/stats (distribution bar + filter counts)
 * and /api/articles (full article card list with filtering).
 */
(async function initTab2() {

  let allArticles  = [];
  let currentFilter = 'all';

  // ── Criteria tag inference ──────────────────────────────────────────────────
  // Scans relevance_reason text and returns up to 2 matching category labels.

  function inferCriteriaTags(reason) {
    if (!reason) return ['General Relevance'];
    const r = reason.toLowerCase();
    const tags = [];

    if (/strategy|market position/.test(r))                    tags.push('Strategic Impact');
    if (/revenue|cost|pricing|savings|roi/.test(r))            tags.push('Revenue / Cost');
    if (/compet/.test(r))                                       tags.push('Competitive Advantage');
    if (/operat|workflow|automat|productiv|efficiency/.test(r)) tags.push('Operational Efficiency');
    if (/regulat|governance|policy|compliance|ethics/.test(r))  tags.push('Regulatory & Governance');

    const unique = [...new Set(tags)];
    return unique.length ? unique.slice(0, 2) : ['General Relevance'];
  }

  // ── Score badge CSS class ────────────────────────────────────────────────────

  function scoreBadgeClass(score) {
    if (score === null || score === undefined) return 'score-badge-low';
    if (score >= 7) return 'score-badge-high';
    if (score >= 4) return 'score-badge-mid';
    return 'score-badge-low';
  }

  // ── Date formatter ───────────────────────────────────────────────────────────

  function fmtDate(str) {
    if (!str) return '';
    try {
      return new Date(str).toLocaleDateString('en-US', {
        year: 'numeric', month: 'short', day: 'numeric',
      });
    } catch { return str; }
  }

  // ── Render a single article card ─────────────────────────────────────────────

  function renderCard(a) {
    const score      = a.relevance_score;
    const isRelevant = a.is_relevant === 1 || a.is_relevant === true;
    const reason     = a.relevance_reason || 'No explanation recorded.';
    const tags       = inferCriteriaTags(reason);
    const badgeClass = scoreBadgeClass(score);
    const scoreText  = (score !== null && score !== undefined) ? `Score: ${score}/10` : 'Unscored';

    const tagsHtml = tags
      .map(t => `<span class="criteria-tag">${t}</span>`)
      .join('');

    const pillHtml = isRelevant
      ? `<span class="relevance-pill relevance-pill-yes">&#10003; Relevant</span>`
      : `<span class="relevance-pill relevance-pill-no">&#10007; Below Threshold</span>`;

    const title = (a.title || '(No title)')
      .replace(/&#\d+;/g, c => { const tmp = document.createElement('textarea'); tmp.innerHTML = c; return tmp.value; });

    return `
      <div class="article-card ${isRelevant ? '' : 'faded'}" data-relevant="${isRelevant ? '1' : '0'}">
        <div class="article-card-top">
          <span class="score-badge ${badgeClass}">${scoreText}</span>
          <span class="article-source">${a.source_name || ''}</span>
        </div>
        <p class="article-title">${a.title || '(No title)'}</p>
        <p class="article-reason">${reason}</p>
        <div class="criteria-tags">${tagsHtml}</div>
        <div class="article-card-bottom">
          <span class="article-date">${fmtDate(a.published_date)}</span>
          ${pillHtml}
        </div>
      </div>`;
  }

  // ── Render filtered list ─────────────────────────────────────────────────────

  function renderList(filter) {
    const listEl = document.getElementById('article-list');
    if (!listEl) return;

    const filtered = filter === 'relevant'
      ? allArticles.filter(a => a.is_relevant === 1 || a.is_relevant === true)
      : allArticles;

    if (!filtered.length) {
      listEl.innerHTML = '<p class="placeholder-msg">No articles match this filter.</p>';
      return;
    }

    listEl.innerHTML = `<div class="article-list">${filtered.map(renderCard).join('')}</div>`;
  }

  // ── Update filter button labels with live counts ─────────────────────────────

  function updateFilterBtns(stats) {
    const allBtn = document.querySelector('.filter-btn[data-filter="all"]');
    const relBtn = document.querySelector('.filter-btn[data-filter="relevant"]');
    if (allBtn) allBtn.textContent = `All (${stats.total})`;
    if (relBtn) relBtn.textContent = `Relevant Only (${stats.relevant})`;
  }

  // ── Render score distribution bar ────────────────────────────────────────────

  function renderDistBar(stats) {
    const total  = stats.total || 1;
    const relPct = Math.round((stats.relevant / total) * 100);
    const notPct = 100 - relPct;

    const relFill  = document.getElementById('bar-relevant-fill');
    const notFill  = document.getElementById('bar-not-fill');
    const relLabel = document.getElementById('bar-relevant-label');
    const notLabel = document.getElementById('bar-not-label');

    if (relFill)  relFill.style.width  = `${relPct}%`;
    if (notFill)  notFill.style.width  = `${notPct}%`;
    if (relLabel) relLabel.textContent = `${stats.relevant} Relevant (${relPct}%)`;
    if (notLabel) notLabel.textContent = `${stats.not_relevant} Not Relevant (${notPct}%)`;
  }

  // ── Wire filter buttons ──────────────────────────────────────────────────────

  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      renderList(currentFilter);
    });
  });

  // ── Fetch data and render ────────────────────────────────────────────────────

  try {
    const [stats, articles] = await Promise.all([
      window.fetchData('/api/stats'),
      window.fetchData('/api/articles'),
    ]);

    allArticles = articles;

    renderDistBar(stats);
    updateFilterBtns(stats);
    renderList(currentFilter);

  } catch (err) {
    console.error('[Tab 2] Failed to load data:', err);
    const listEl = document.getElementById('article-list');
    if (listEl) {
      listEl.innerHTML =
        '<p class="placeholder-msg">Failed to load articles. Check the browser console for details.</p>';
    }
  }

})();
