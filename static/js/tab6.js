/**
 * tab6.js — Progress Report tab
 * Wires the static accordion panels (B–F) in Tab 6.
 * All panels start open (class "open" + aria-expanded="true" in HTML).
 * Clicking a header toggles it closed/open.
 */
(function initTab6() {

  document.querySelectorAll('#tab-6 .pr-accordion-header').forEach(btn => {
    btn.addEventListener('click', () => {
      const accordion = btn.closest('.pr-accordion');
      const body      = accordion.querySelector('.pr-accordion-body');
      const chevron   = btn.querySelector('.pr-chevron');
      const isOpen    = body.classList.contains('open');

      body.classList.toggle('open', !isOpen);
      chevron.classList.toggle('closed', isOpen);   // closed = rotated = pointing down
      btn.setAttribute('aria-expanded', String(!isOpen));
    });
  });

})();
