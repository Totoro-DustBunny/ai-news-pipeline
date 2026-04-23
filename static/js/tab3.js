/**
 * tab3.js — Classification tab
 * Renders category summary cards, an animated bar chart,
 * filter pills, and a classified article list.
 * All data comes from /api/stats and /api/articles.
 */
(async function initTab3() {

  // ── Category config — single source of truth for labels, colors, HW mapping ──

  const CATEGORIES = [
    {
      key:       'New AI Tools & Product Launches',
      shortLabel:'New AI Tools',
      color:     '#6B9BD2',   // --color-blue
      hwLabel:   'Product and Service Innovation',
    },
    {
      key:       'AI Trends & Market Movements',
      shortLabel:'AI Trends',
      color:     '#8B8B35',   // --color-olive
      hwLabel:   'Strategy and Executive Decision-Making',
    },
    {
      key:       'Practical AI Use Cases',
      shortLabel:'Practical Use Cases',
      color:     '#8BBFCC',   // --color-cyan
      hwLabel:   'Industry-Specific AI Use Cases',
    },
    {
      key:       'Foundation Models & Platforms',
      shortLabel:'Foundation Models',
      color:     '#C9B882',   // --color-warm
      hwLabel:   'Infrastructure, Models, and Platforms',
    },
    {
      key:       'AI Governance & Ethics',
      shortLabel:'Governance & Ethics',
      color:     '#8B7FA3',   // --color-violet
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

  function buildCountMap(categories) {
    const map = {};
    categories.forEach(c => { map[c.category] = c.count; });
    return map;
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
        const count  = countMap[cat.key] ?? 0;
        const pct    = Math.round((count / maxCount) * 100);
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

  // Trigger CSS width transition on all bar fills
  function animateBars() {
    document.querySelectorAll('#cat-bar-chart-inner .bar-fill').forEach(bar => {
      // Double rAF + tiny timeout ensures the 0% width has been painted first
      requestAnimationFrame(() => {
        setTimeout(() => { bar.style.width = `${bar.dataset.pct}%`; }, 40);
      });
    });
  }

  // Watch for tab-3 becoming active so bars animate each time it's opened
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

  function renderFilterPills(countMap, totalClassified) {
    const row = document.getElementById('cat-filter-row');
    if (!row) return;

    const allPill  = `<button class="cat-pill active" data-cat="all">All (${totalClassified})</button>`;
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
    const [stats, articles] = await Promise.all([
      window.fetchData('/api/stats'),
      window.fetchData('/api/articles'),
    ]);

    classifiedArticles = articles.filter(a => a.category);
    const countMap     = buildCountMap(stats.categories);

    renderCatCards(countMap);
    renderBarChart(countMap);
    renderFilterPills(countMap, classifiedArticles.length);
    renderArticleList(currentFilter);

    // If already on tab-3 on page load, fire bars immediately
    if (tab3El && tab3El.classList.contains('active')) animateBars();

  } catch (err) {
    console.error('[Tab 3] Failed to load data:', err);
    const c = document.getElementById('classified-list');
    if (c) c.innerHTML = '<p class="placeholder-msg">Failed to load data. Check browser console.</p>';
  }

})();
