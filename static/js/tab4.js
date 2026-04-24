/**
 * tab4.js — KOL Research tab
 * Fetches /api/kol-posts and renders:
 *   B. Profile cards grid
 *   C. Accordion post analysis per KOL (posts + dynamic writing_style from JSON)
 * Section D (checklist) is static HTML.
 */
(async function initTab4() {

  // ── Section B: KOL profile cards ─────────────────────────────────────────────

  function renderProfileCards(kols) {
    const grid = document.getElementById('kol-cards-grid');
    if (!grid) return;

    grid.innerHTML = kols.map(kol => {
      const pills = (kol.focus_areas || [])
        .map(f => `<span class="kol-focus-pill">${f}</span>`)
        .join('');
      return `
        <div class="kol-profile-card">
          <p class="kol-name">${kol.name}</p>
          <p class="kol-role">${kol.title}</p>
          <div class="kol-focus-pills">${pills}</div>
          <a class="kol-linkedin-link" href="${kol.linkedin_url}" target="_blank" rel="noopener">
            View on LinkedIn ↗
          </a>
        </div>`;
    }).join('');
  }

  // ── Section C: Post cards ─────────────────────────────────────────────────────

  function renderPostCard(post) {
    const date        = post.date && post.date !== 'None' ? post.date : 'Recent';
    const isPlaceholder = !!post.is_placeholder;

    const banner = isPlaceholder
      ? `<div class="kol-placeholder-banner">&#9888; Direct LinkedIn post not retrievable — visit profile for latest posts</div>`
      : '';

    const linkText = isPlaceholder ? 'Visit LinkedIn Profile ↗' : 'View Source ↗';

    return `
      <div class="kol-post-card${isPlaceholder ? ' is-placeholder' : ''}">
        ${banner}
        <div class="kol-post-meta">
          <span class="kol-post-title">${post.title || 'Untitled'}</span>
          <span class="kol-post-date">${date}</span>
        </div>
        <blockquote class="kol-post-snippet">${post.snippet || '(No preview available)'}</blockquote>
        <a class="kol-post-source-link" href="${post.url}" target="_blank" rel="noopener">${linkText}</a>
      </div>`;
  }

  // ── Section C: Writing style analysis block ───────────────────────────────────

  function renderAnalysis(style) {
    if (!style) return '<p class="placeholder-msg" style="padding:12px 0">No analysis available.</p>';

    const isDynamic = style.source === 'dynamic';
    const sourceBadge = isDynamic
      ? `<span class="kol-style-source-badge kol-style-source-dynamic">Extracted from posts</span>`
      : `<span class="kol-style-source-badge kol-style-source-fallback">Estimated style</span>`;

    const confidence = style.confidence != null
      ? `<span class="kol-style-confidence">Confidence: ${style.confidence}/10</span>`
      : '';

    const rows = [
      { label: 'Hook Style',   value: style.hook_style   },
      { label: 'Structure',    value: style.structure    },
      { label: 'Credibility',  value: style.credibility  },
      { label: 'Engagement',   value: style.engagement   },
    ];
    const rowsHtml = rows.map(r => `
      <div class="kol-analysis-row">
        <span class="kol-analysis-label">${r.label}</span>
        <span class="kol-analysis-value">${r.value || '—'}</span>
      </div>`).join('');

    return `
      <div class="kol-analysis-block">
        <div class="kol-style-tag-row">
          <span class="kol-style-tag">${style.style_tag || '—'}</span>
          ${sourceBadge}
          ${confidence}
        </div>
        <div class="kol-analysis-grid">${rowsHtml}</div>
      </div>`;
  }

  // ── Section C: Accordions ─────────────────────────────────────────────────────

  function renderAccordions(kols) {
    const container = document.getElementById('kol-accordions');
    if (!container) return;

    container.innerHTML = kols.map((kol, i) => {
      const posts     = kol.posts || [];
      const realCount = posts.filter(p => !p.is_placeholder).length;
      const metaLabel = `${realCount} Real Post${realCount !== 1 ? 's' : ''} Retrieved`;
      const postsHtml = posts.length
        ? posts.map(renderPostCard).join('')
        : '<p class="placeholder-msg" style="padding:12px 0;">No posts found for this KOL.</p>';

      return `
        <div class="kol-accordion" id="kol-accordion-${i}">
          <button class="kol-accordion-header" data-idx="${i}" aria-expanded="false">
            <span class="kol-acc-name">${kol.name}</span>
            <span class="kol-acc-meta">${metaLabel}</span>
            <span class="kol-acc-chevron">▾</span>
          </button>
          <div class="kol-accordion-body" id="kol-body-${i}">
            <div class="kol-accordion-inner">

              <p class="kol-subsection-title">Recent Posts</p>
              <div class="kol-posts-list">${postsHtml}</div>

              <div class="kol-subsection-divider"></div>

              <p class="kol-subsection-title">Content Style Analysis</p>
              ${renderAnalysis(kol.writing_style)}

            </div>
          </div>
        </div>`;
    }).join('');

    container.querySelectorAll('.kol-accordion-header').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx    = btn.dataset.idx;
        const body   = document.getElementById(`kol-body-${idx}`);
        const isOpen = btn.getAttribute('aria-expanded') === 'true';

        btn.setAttribute('aria-expanded', !isOpen);
        btn.querySelector('.kol-acc-chevron').textContent = isOpen ? '▾' : '▴';
        body.style.maxHeight = isOpen ? '0' : `${body.scrollHeight}px`;
        body.classList.toggle('open', !isOpen);
      });
    });
  }

  // ── Fetch and render ──────────────────────────────────────────────────────────

  try {
    const data = await window.fetchData('/api/kol-posts');

    if (data.status === 'not_generated') {
      const grid = document.getElementById('kol-cards-grid');
      if (grid) grid.innerHTML =
        '<p class="placeholder-msg">KOL data not yet generated. Run <code>python scripts/fetch_kol_posts.py</code> first.</p>';
      return;
    }

    const kols = data.data?.kols || data.kols || [];
    renderProfileCards(kols);
    renderAccordions(kols);

  } catch (err) {
    console.error('[Tab 4] Failed to load KOL data:', err);
    const grid = document.getElementById('kol-cards-grid');
    if (grid) grid.innerHTML = '<p class="placeholder-msg">Failed to load KOL data. Check browser console.</p>';
  }

})();
