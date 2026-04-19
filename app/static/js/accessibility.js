/**
 * VenueFlow AI — Accessibility Enhancement Layer
 * Handles high-contrast mode, focus management, and screen reader announcements.
 */

const Accessibility = (() => {
    let highContrastMode = false;

    function init() {
        setupAriaAnnouncements();
        setupHighContrastToggle();
        setupKeyboardNavigation();
        enhanceMapAccessibility();
        console.log('♿ Accessibility engine active');
    }

    // ── High Contrast ────────────────────────────────────────
    function setupHighContrastToggle() {
        const btn = document.getElementById('btn-accessibility');
        if (!btn) return;

        btn.addEventListener('click', () => {
            highContrastMode = !highContrastMode;
            document.body.classList.toggle('high-contrast', highContrastMode);
            
            const status = highContrastMode ? 'High contrast enabled' : 'High contrast disabled';
            announce(status);
            
            btn.setAttribute('aria-pressed', highContrastMode);
            btn.title = highContrastMode ? 'Disable High Contrast' : 'Enable High Contrast';
        });
    }

    // ── Screen Reader Announcements ─────────────────────────
    function announce(message, priority = 'polite') {
        let announcer = document.getElementById('aria-announcer');
        if (!announcer) {
            announcer = document.createElement('div');
            announcer.id = 'aria-announcer';
            announcer.setAttribute('aria-live', priority);
            announcer.style.position = 'absolute';
            announcer.style.width = '1px';
            announcer.style.height = '1px';
            announcer.style.padding = '0';
            announcer.style.margin = '-1px';
            announcer.style.overflow = 'hidden';
            announcer.style.clip = 'rect(0,0,0,0)';
            announcer.style.border = '0';
            document.body.appendChild(announcer);
        }
        
        // Brief timeout to ensure DOM update is registered
        announcer.textContent = '';
        setTimeout(() => {
            announcer.textContent = message;
        }, 100);
    }

    function setupAriaAnnouncements() {
        // Listen for specific app events to announce
        window.addEventListener('vf-emergency-start', () => {
            announce('CRITICAL ALERT: Emergency evacuation in progress. Please proceed to the nearest exit immediately.', 'assertive');
        });

        window.addEventListener('vf-phase-change', (e) => {
            announce(`Event phase updated to: ${e.detail.label}`);
        });
    }

    // ── Keyboard Navigation ───────────────────────────────────
    function setupKeyboardNavigation() {
        // Ensure buttons have role and tabIndex if not native
        document.querySelectorAll('.nav-tab, .quick-btn, .filter-btn, .phase-jump-btn').forEach(el => {
            if (el.tagName !== 'BUTTON') {
                el.setAttribute('role', 'button');
                el.tabIndex = 0;
            }
        });

        // Handle Enter/Space for non-button interactive elements
        document.addEventListener('keydown', (e) => {
            if ((e.key === 'Enter' || e.key === ' ') && e.target.getAttribute('role') === 'button') {
                e.preventDefault();
                e.target.click();
            }
        });
    }

    // ── Map ARIA ──────────────────────────────────────────────
    function enhanceMapAccessibility() {
        const mapContainer = document.getElementById('map-container');
        if (mapContainer) {
            mapContainer.setAttribute('aria-label', 'Static map of Titan Arena showing crowd density across 12 zones.');
        }
    }

    return { init, announce };
})();

// Export to window for access from other scripts
window.VenueAccessibility = Accessibility;
document.addEventListener('DOMContentLoaded', Accessibility.init);
