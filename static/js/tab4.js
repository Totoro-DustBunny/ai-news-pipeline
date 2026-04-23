/**
 * tab4.js — KOL Research tab
 * Fetches /api/kol-posts and renders:
 *   B. Profile cards grid
 *   C. Accordion post analysis per KOL (posts from API + hardcoded style analysis)
 * Section D (checklist) is static HTML.
 */
(async function initTab4() {

  // ── Hardcoded content-style analysis per KOL ────────────────────────────────
  // Keyed by KOL name for lookup when rendering accordions.

  const KOL_ANALYSIS = {
    "Cassie Kozyrkov": {
      hook:        "Opens with a bold counter-intuitive claim or rhetorical question that challenges mainstream assumptions",
      structure:   "Short punchy paragraphs, heavy use of line breaks, numbered insights, emoji for visual scanning",
      credibility: "Draws on Google-scale experience, statistical rigor, and named research — speaks with authoritative clarity",
      engagement:  "Ends with a provocative question or a direct challenge to the reader's thinking",
      styleTag:    "Contrarian + Instructional",
    },
    "Andrew Ng": {
      hook:        "Opens with a concrete observation from the field or a surprising data point about AI adoption",
      structure:   "Narrative flow with clear sections, often uses analogies to simplify complex ideas",
      credibility: "Cites real course data, student outcomes, and industry partnerships; name-drops collaborators naturally",
      engagement:  "Closes with an invitation to learn more — often links to a course, paper, or resource",
      styleTag:    "Instructional + Narrative",
    },
    "Allie K. Miller": {
      hook:        "Opens with a punchy stat, a product launch hook, or a first-person observation about a market shift",
      structure:   "Scannable bullet lists, bold keyword highlighting, very mobile-optimized formatting",
      credibility: "References specific companies, tools, and dollar figures; grounds claims in market reality",
      engagement:  "Direct CTAs — asks followers to share, comment with their take, or tag someone",
      styleTag:    "Concise + Data-driven",
    },
    "Kirk Borne": {
      hook:        "Leads with a thought-provoking quote, fascinating data point, or trending AI topic of the week",
      structure:   "Curated list format, thread-style posts with emoji bullets, high information density",
      credibility: "Astrophysics and data science background lends cross-domain authority; cites academic and industry sources",
      engagement:  "Uses hashtag strategy and retweet-style sharing; asks community for their take",
      styleTag:    "Curated + Educational",
    },
    "Steve Nouri": {
      hook:        "Opens with a bold statement about where AI is heading or what most people are getting wrong",
      structure:   "Clean numbered lists, visual metaphors, accessible language for broad audiences",
      credibility: "Founder narrative, large following as social proof, references to AI tools by name",
      engagement:  "Ends with a community question or invitation to follow for more AI insights",
      styleTag:    "Visionary + Accessible",
    },
  };

  // ── Section B: KOL profile cards ─────────────────────────────────────────────

  function renderProfileCards(kols) {
    const grid = document.getElementById('kol-cards-grid');
    if (!grid) return;

    grid.innerHTML = kols.map(kol => {
      const pills = kol.focus_areas
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

  // ── Section C: Accordion per KOL ─────────────────────────────────────────────

  function renderPostCard(post) {
    const date = post.date && post.date !== 'None' ? post.date : 'Recent';
    return `
      <div class="kol-post-card">
        <div class="kol-post-meta">
          <span class="kol-post-title">${post.title || 'Untitled'}</span>
          <span class="kol-post-date">${date}</span>
        </div>
        <blockquote class="kol-post-snippet">${post.snippet || '(No preview available)'}</blockquote>
        <a class="kol-post-source-link" href="${post.url}" target="_blank" rel="noopener">View Source ↗</a>
      </div>`;
  }

  function renderAnalysis(analysis) {
    if (!analysis) return '<p class="placeholder-msg" style="padding:12px 0">No analysis available.</p>';
    const rows = [
      { label: 'Hook Style',        value: analysis.hook        },
      { label: 'Structure',         value: analysis.structure   },
      { label: 'Credibility',       value: analysis.credibility },
      { label: 'Engagement',        value: analysis.engagement  },
    ];
    const rowsHtml = rows.map(r => `
      <div class="kol-analysis-row">
        <span class="kol-analysis-label">${r.label}</span>
        <span class="kol-analysis-value">${r.value}</span>
      </div>`).join('');

    return `
      <div class="kol-analysis-block">
        <div class="kol-style-tag-row">
          <span class="kol-style-tag">${analysis.styleTag}</span>
        </div>
        <div class="kol-analysis-grid">${rowsHtml}</div>
      </div>`;
  }

  function renderAccordions(kols) {
    const container = document.getElementById('kol-accordions');
    if (!container) return;

    container.innerHTML = kols.map((kol, i) => {
      const analysis  = KOL_ANALYSIS[kol.name];
      const postCount = kol.posts ? kol.posts.length : 0;
      const postsHtml = postCount
        ? kol.posts.map(renderPostCard).join('')
        : '<p class="placeholder-msg" style="padding:12px 0;">No posts found for this KOL.</p>';

      return `
        <div class="kol-accordion" id="kol-accordion-${i}">
          <button class="kol-accordion-header" data-idx="${i}" aria-expanded="false">
            <span class="kol-acc-name">${kol.name}</span>
            <span class="kol-acc-meta">${postCount} Recent Post${postCount !== 1 ? 's' : ''} Analyzed</span>
            <span class="kol-acc-chevron">▾</span>
          </button>
          <div class="kol-accordion-body" id="kol-body-${i}">
            <div class="kol-accordion-inner">

              <p class="kol-subsection-title">Recent Posts</p>
              <div class="kol-posts-list">${postsHtml}</div>

              <div class="kol-subsection-divider"></div>

              <p class="kol-subsection-title">Content Style Analysis</p>
              ${renderAnalysis(analysis)}

            </div>
          </div>
        </div>`;
    }).join('');

    // Wire accordion toggle handlers
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
