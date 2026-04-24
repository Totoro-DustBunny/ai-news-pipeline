/**
 * tab3.js — Classification tab
 * Renders category summary cards, an animated bar chart,
 * filter pills, and a classified article list.
 * Only articles with relevance_score >= THRESHOLD are shown.
 * Counts are derived from /api/articles directly (not /api/stats).
 */
(async function initTab3() {

  const THRESHOLD = 8;

  // ── Category config — single source of truth for labels, colors, HW mapping ──

  const CATEGORIES = [
    {
      key:       'New AI Tools & Product Launches',
      shortLabel:'New AI Tools',
      color:     '#6B9BD2',
      hwLabel:   'Product and Service Innovation',
    },
    {
      key:       'AI Trends & Market Movements',
      shortLabel:'AI Trends',
      color:     '#8B8B35',
      hwLabel:   'Strategy and Executive Decision-Making',
    },
    {
      key:       'Practical AI Use Cases',
      shortLabel:'Practical Use Cases',
      color:     '#8BBFCC',
      hwLabel:   'Industry-Specific AI Use Cases',
    },
    {
      key:       'Foundation Models & Platforms',
      shortLabel:'Foundation Models',
      color:     '#C9B882',
      hwLabel:   'Infrastructure, Models, and Platforms',
    },
    {
      key:       'AI Governance & Ethics',
      shortLabel:'Governance & Ethics',
      color:     '#8B7FA3',
      hwLabel:   'Governance, Ethics, and Regulation',
    },
  ];

  let classifiedArticles = [];
  let currentFilter      = 'all';

  // ── Helpers ──────────────────────────────────────────────────────────────────

  function getCat(key) {
    return CATEGORIES.find(c => c.key === key)
      || { shortLabel: key, color: '#aaa', hwLabel: key };
  }

  function fmtDate(str) {
    if (!str) return '';
    try {
      return new Date(str).toLocaleDateString('en-US',
        { year: 'numeric', month: 'short', day: 'numeric' });
    } catch { return str; }
  }

  // Build {category: count} map directly from the filtered article array
  function buildCountMap(articles) {
    const map = {};
    articles.forEach(a => {
      if (a.category) map[a.category] = (map[a.category] || 0) + 1;
    });
    return map;
  }

  // ── Section A: Dynamic subtitle count ────────────────────────────────────────

  function updateSubtitle(count) {
    const el = document.getElementById('tab3-article-count');
    if (el) el.textContent = count;
  }

  // ── Section B: Category cards ─────────────────────────────────────────────────

  function renderCatCards(countMap) {
    const row = document.getElementById('cat-cards-row');
    if (!row) return;
    row.innerHTML = CATEGORIES.map(cat => `
      <div class="cat-card" style="border-top-color:${cat.color}">
        <div class="cat-card-count">${countMap[cat.key] ?? 0}</div>
        <div class="cat-card-name">${cat.key}</div>
      </div>`).join('');
  }

  // ── Section C: Bar chart ──────────────────────────────────────────────────────

  function renderBarChart(countMap) {
    const inner = document.getElementById('cat-bar-chart-inner');
    if (!inner) return;

    const maxCount = Math.max(...CATEGORIES.map(c => countMap[c.key] ?? 0), 1);

    inner.innerHTML = `<div class="bar-chart-rows">${
      CATEGORIES.map(cat => {
        const count = countMap[cat.key] ?? 0;
        const pct   = Math.round((count / maxCount) * 100);
        return `
          <div class="bar-chart-row">
            <span class="bar-label">${cat.shortLabel}</span>
            <div class="bar-track">
              <div class="bar-fill"
                   data-pct="${pct}"
                   style="background:${cat.color}; width:0%"></div>
            </div>
            <span class="bar-count">${count}</span>
          </div>`;
      }).join('')
    }</div>`;
  }

  function animateBars() {
    document.querySelectorAll('#cat-bar-chart-inner .bar-fill').forEach(bar => {
      requestAnimationFrame(() => {
        setTimeout(() => { bar.style.width = `${bar.dataset.pct}%`; }, 40);
      });
    });
  }

  const tab3El = document.getElementById('tab-3');
  if (tab3El) {
    new MutationObserver(mutations => {
      mutations.forEach(m => {
        if (m.type === 'attributes' && tab3El.classList.contains('active')) {
          animateBars();
        }
      });
    }).observe(tab3El, { attributes: true, attributeFilter: ['class'] });
  }

  // ── Section D: Filter pills ───────────────────────────────────────────────────

  function renderFilterPills(countMap, total) {
    const row = document.getElementById('cat-filter-row');
    if (!row) return;

    const allPill  = `<button class="cat-pill active" data-cat="all">All (${total})</button>`;
    const catPills = CATEGORIES.map(cat =>
      `<button class="cat-pill" data-cat="${cat.key}">${cat.shortLabel} (${countMap[cat.key] ?? 0})</button>`
    ).join('');

    row.innerHTML = allPill + catPills;

    row.querySelectorAll('.cat-pill').forEach(pill => {
      pill.addEventListener('click', () => {
        row.querySelectorAll('.cat-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');
        currentFilter = pill.dataset.cat;
        renderArticleList(currentFilter);
      });
    });
  }

  // ── Section E: Classified article cards ──────────────────────────────────────

  function renderCard(a) {
    const cat = getCat(a.category);
    return `
      <div class="classified-card">
        <div class="classified-card-top">
          <div>
            <span class="cat-badge" style="background:${cat.color}">${a.category || ''}</span>
            <p class="hw-category-label">HW Category: ${cat.hwLabel}</p>
          </div>
        </div>
        <p class="classified-title">${a.title || '(No title)'}</p>
        <p class="classified-reason">${a.classification_reason || 'No explanation recorded.'}</p>
        <div class="classified-card-bottom">
          <span class="source-pill">${a.source_name || ''}</span>
          <span class="classified-date">${fmtDate(a.published_date)}</span>
          ${a.url ? `<a class="article-read-link" href="${a.url}" target="_blank" rel="noopener noreferrer">Read Article →</a>` : ''}
        </div>
      </div>`;
  }

  function renderArticleList(filter) {
    const container = document.getElementById('classified-list');
    if (!container) return;

    const filtered = filter === 'all'
      ? classifiedArticles
      : classifiedArticles.filter(a => a.category === filter);

    if (!filtered.length) {
      container.innerHTML = '<p class="placeholder-msg">No articles in this category.</p>';
      return;
    }
    container.innerHTML = `<div class="classified-list">${filtered.map(renderCard).join('')}</div>`;
  }

  // ── Fetch and render ──────────────────────────────────────────────────────────

  try {
    const articles = await window.fetchData('/api/articles');

    // Apply the same frontend threshold as Tabs 1 & 2
    classifiedArticles = articles.filter(
      a => a.category && (a.relevance_score ?? 0) >= THRESHOLD
    );

    const countMap = buildCountMap(classifiedArticles);

    updateSubtitle(classifiedArticles.length);
    renderCatCards(countMap);
    renderBarChart(countMap);
    renderFilterPills(countMap, classifiedArticles.length);
    renderArticleList(currentFilter);

    if (tab3El && tab3El.classList.contains('active')) animateBars();

  } catch (err) {
    console.error('[Tab 3] Failed to load data:', err);
    const c = document.getElementById('classified-list');
    if (c) c.innerHTML = '<p class="placeholder-msg">Failed to load data. Check browser console.</p>';
  }

})();
