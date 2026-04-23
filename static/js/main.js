/**
 * main.js — Tab switching + API fetch utility for AI News Pipeline
 */

// ── Tab configuration ──────────────────────────────────────────────────────────

const TABS = [
  { id: 1, label: "01  Pipeline & Sources" },
  { id: 2, label: "02  Relevance Scoring"  },
  { id: 3, label: "03  Classification"     },
  { id: 4, label: "04  KOL Research"       },
  { id: 5, label: "05  LinkedIn Content"   },
  { id: 6, label: "06  Progress Report"    },
];

const STORAGE_KEY = "ai_pipeline_active_tab";


// ── Tab switching ──────────────────────────────────────────────────────────────

/**
 * Activate a tab by number (1–6).
 * Hides all other tab-content divs, marks the correct nav button as active,
 * and persists the selection to localStorage.
 */
function activateTab(tabId) {
  // Hide all panels
  document.querySelectorAll(".tab-content").forEach(el => {
    el.classList.remove("active");
  });

  // Deactivate all nav buttons
  document.querySelectorAll(".nav-tabs button").forEach(btn => {
    btn.classList.remove("active");
  });

  // Show the selected panel
  const panel = document.getElementById(`tab-${tabId}`);
  if (panel) panel.classList.add("active");

  // Mark the correct button active
  const btn = document.querySelector(`.nav-tabs button[data-tab="${tabId}"]`);
  if (btn) btn.classList.add("active");

  // Persist selection
  localStorage.setItem(STORAGE_KEY, tabId);
}


// ── API fetch utility ──────────────────────────────────────────────────────────

/**
 * Fetch data from a Flask /api/* endpoint and return parsed JSON.
 * Used by all tab-specific scripts.
 *
 * @param {string} endpoint - e.g. "/api/stats" or "/api/articles"
 * @returns {Promise<any>} Parsed JSON response
 */
async function fetchData(endpoint) {
  const response = await fetch(endpoint);
  if (!response.ok) {
    throw new Error(`API error: ${response.status} ${response.statusText} (${endpoint})`);
  }
  return response.json();
}

// Expose globally so tab-specific scripts can use it
window.fetchData = fetchData;


// ── Init ───────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Wire up nav button click handlers
  document.querySelectorAll(".nav-tabs button").forEach(btn => {
    btn.addEventListener("click", () => {
      const tabId = parseInt(btn.dataset.tab, 10);
      activateTab(tabId);
    });
  });

  // Restore last active tab from localStorage, default to tab 1
  const saved = parseInt(localStorage.getItem(STORAGE_KEY), 10);
  const initial = (saved >= 1 && saved <= TABS.length) ? saved : 1;
  activateTab(initial);
});
