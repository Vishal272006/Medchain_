// MedChain shared utilities
const API = "http://localhost:8000";
async function apiFetch(method, path, body) {
  const r = await fetch(API + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

/**
 * Initialize Role Switcher Dropdown
 * Handles toggling the menu and closing it when clicking outside.
 */
function initRoleSwitcher() {
    const btn = document.getElementById('roleSwitcherBtn');
    const menu = document.getElementById('roleMenu');

    if (!btn || !menu) return;

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        menu.classList.toggle('hidden');
    });

    document.addEventListener('click', (e) => {
        if (!menu.classList.contains('hidden') && !menu.contains(e.target) && e.target !== btn) {
            menu.classList.add('hidden');
        }
    });
}

// Auto-init if DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initRoleSwitcher);
} else {
    initRoleSwitcher();
}
