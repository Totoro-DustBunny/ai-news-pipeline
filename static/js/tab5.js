/**
 * tab5.js — LinkedIn Content Generation tab
 * Fetches /api/linkedin-posts and renders 3 post cards with:
 *   - Coloured top bar + category badge
 *   - Audience & tone metadata row
 *   - Post content box (with hashtag highlighting)
 *   - Image brief box
 *   - Collapsible source articles list
 *   - Copy-to-clipboard button
 */
(async function initTab5() {

  // ── Hashtag highlighter ───────────────────────────────────────────────────
  // Wraps #Hashtag tokens in a styled span.

  function highlightHashtags(text) {
    return text.replace(/(#\w+)/g, '<span class="li-hashtag">$1</span>');
  }

  // ── Render a single post card ─────────────────────────────────────────────

  function renderPostCard(post, idx) {
    const color       = post.color || '#aaa';
    const category    = post.category || 'Uncategorized';
    const content     = post.content  || '';
    const imageBrief  = post.image_brief     || '';
    const imagePath   = post.image_path      || null;
    const audience    = post.target_audience || '';
    const tone        = post.tone            || '';
    const sources     = post.source_articles || [];

    // Escape HTML then highlight hashtags
    const escapedContent = content
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const contentHtml = highlightHashtags(escapedContent);

    // Source pills — items are {title, url} objects (enriched by API) or legacy strings
    const sourcePills = sources.length
      ? sources.map(s => {
          const title = typeof s === 'string' ? s : (s.title || '');
          const url   = typeof s === 'string' ? null : s.url;
          return url
            ? `<a class="li-source-pill li-source-link" href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>`
            : `<span class="li-source-pill">${title}</span>`;
        }).join('')
      : '<span class="li-source-pill">No source articles recorded</span>';

    return `
      <div class="li-post-card">

        <div class="li-card-topbar" style="background:${color}"></div>

        <div class="li-card-header">
          <span class="li-category-badge" style="background:${color}">${category}</span>
        </div>

        <div class="li-card-meta">
          &#128100; ${audience || '—'} &nbsp;·&nbsp; &#127919; ${tone || '—'}
        </div>

        <div class="li-card-body">

          <div class="li-content-box">${contentHtml}</div>

          ${imagePath
            ? `<div class="li-post-image-wrap">
                 <img class="li-post-image" src="${imagePath}" alt="AI-generated visual for ${category}" loading="lazy">
                 <p class="li-image-caption">&#10024; AI-generated image · Gemini</p>
               </div>`
            : `<p class="li-image-brief-label">&#128444;&#65039; Image / Visual Brief</p>
               <div class="li-image-brief-box">
                 ${imageBrief || '(No image brief provided)'}
                 <p class="li-image-brief-note">&#9888;&#65039; Image not generated — run <code>python scripts/generate_linkedin.py</code> with <code>GOOGLE_AI_STUDIO_KEY</code> set.</p>
               </div>`
          }

          <button class="li-sources-toggle" data-idx="${idx}" aria-expanded="false">
            &#128240; Source Articles Used (${sources.length})
            <span class="li-sources-chevron" id="li-chevron-${idx}">&#9660;</span>
          </button>
          <div class="li-sources-list" id="li-sources-${idx}">
            ${sourcePills}
          </div>

        </div>

        <div class="li-card-footer">
          <button class="li-copy-btn" data-idx="${idx}">Copy Post</button>
        </div>

      </div>`;
  }

  // ── Wire interactive behaviours ───────────────────────────────────────────

  function wireCards(posts) {
    // Source toggle
    document.querySelectorAll('.li-sources-toggle').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx      = btn.dataset.idx;
        const list     = document.getElementById(`li-sources-${idx}`);
        const chevron  = document.getElementById(`li-chevron-${idx}`);
        const isOpen   = list.classList.contains('open');
        list.classList.toggle('open', !isOpen);
        chevron.classList.toggle('open', !isOpen);
        btn.setAttribute('aria-expanded', !isOpen);
      });
    });

    // Copy button
    document.querySelectorAll('.li-copy-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const idx     = parseInt(btn.dataset.idx, 10);
        const content = posts[idx]?.content || '';
        navigator.clipboard.writeText(content).then(() => {
          btn.textContent = '✓ Copied!';
          btn.classList.add('copied');
          setTimeout(() => {
            btn.textContent = 'Copy Post';
            btn.classList.remove('copied');
          }, 2000);
        }).catch(err => {
          console.error('[Tab 5] Clipboard write failed:', err);
        });
      });
    });
  }

  // ── Fetch and render ──────────────────────────────────────────────────────

  try {
    const data = await window.fetchData('/api/linkedin-posts');

    if (data.status === 'not_generated') {
      const container = document.getElementById('li-posts-container');
      if (container) container.innerHTML =
        '<p class="placeholder-msg">Posts not yet generated. Run <code>python scripts/generate_linkedin.py</code> first.</p>';
      return;
    }

    const posts     = data.data?.posts || data.posts || [];
    const container = document.getElementById('li-posts-container');
    if (!container) return;

    if (!posts.length) {
      container.innerHTML = '<p class="placeholder-msg">No posts found in the data file.</p>';
      return;
    }

    container.innerHTML = `
      <div class="li-posts-list">
        ${posts.map((p, i) => renderPostCard(p, i)).join('')}
      </div>`;

    wireCards(posts);

  } catch (err) {
    console.error('[Tab 5] Failed to load LinkedIn posts:', err);
    const container = document.getElementById('li-posts-container');
    if (container) container.innerHTML =
      '<p class="placeholder-msg">Failed to load posts. Check browser console.</p>';
  }

})();
