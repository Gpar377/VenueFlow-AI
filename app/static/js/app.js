/**
 * VenueFlow AI — Main Application Controller
 * Manages tabs, WebSocket connection, state, and global event handling.
 */

const App = (() => {
    // ── State ────────────────────────────────────────────────
    let ws = null;
    let wsReconnectAttempts = 0;
    const MAX_RECONNECT = 10;
    let activeTab = 'map';

    // Global state store — updated by WebSocket
    const state = {
        crowd: { heatmap: [], danger_zones: [], total_occupancy: 0, occupancy_percentage: 0 },
        queues: [],
        gates: [],
        timeline: {},
        alerts: [],
    };

    // ── Initialize ───────────────────────────────────────────
    function init() {
        setupTabs();
        setupThemeToggle();
        connectWebSocket();
        fetchInitialData();
        setupSpeedSlider();
        setupPhaseJump();
        console.log('🏟️ VenueFlow AI initialized');
    }

    // ── Tab Navigation ───────────────────────────────────────
    function setupTabs() {
        document.querySelectorAll('.nav-tab').forEach(tab => {
            tab.addEventListener('click', () => switchTab(tab.dataset.tab));
        });
    }

    function switchTab(tabId) {
        activeTab = tabId;
        document.querySelectorAll('.nav-tab').forEach(t => {
            const isActive = t.dataset.tab === tabId;
            t.classList.toggle('active', isActive);
            t.setAttribute('aria-selected', isActive);
        });
        document.querySelectorAll('.tab-panel').forEach(p => {
            const isActive = p.id === `panel-${tabId}`;
            p.classList.toggle('active', isActive);
            p.hidden = !isActive;
        });

        // Fetch tab-specific data
        if (tabId === 'alerts') fetchAlerts();
        if (tabId === 'dashboard') fetchDashboard();
    }

    // ── Theme Toggle ─────────────────────────────────────────
    function setupThemeToggle() {
        const btn = document.getElementById('btn-theme-toggle');
        const saved = localStorage.getItem('vf-theme') || 'dark';
        document.documentElement.setAttribute('data-theme', saved);

        btn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('vf-theme', next);
        });
    }

    // ── WebSocket Connection ─────────────────────────────────
    function connectWebSocket() {
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        const url = `${protocol}//${location.host}/ws`;

        ws = new WebSocket(url);

        ws.addEventListener('open', () => {
            wsReconnectAttempts = 0;
            document.getElementById('ticker-ws').textContent = '🟢';
            document.getElementById('ticker-ws').style.color = 'var(--accent-primary)';
        });

        ws.addEventListener('message', (event) => {
            try {
                const data = JSON.parse(event.data);
                handleWSMessage(data);
            } catch (e) { /* ignore parse errors */ }
        });

        ws.addEventListener('close', () => {
            document.getElementById('ticker-ws').textContent = '🔴';
            if (wsReconnectAttempts < MAX_RECONNECT) {
                wsReconnectAttempts++;
                const delay = Math.min(1000 * Math.pow(2, wsReconnectAttempts), 30000);
                setTimeout(connectWebSocket, delay);
            }
        });

        ws.addEventListener('error', () => { ws.close(); });

        // Keep alive ping every 25s
        setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'ping' }));
            }
        }, 25000);
    }

    function handleWSMessage(data) {
        if (data.type !== 'tick') return;

        // Update global state
        if (data.crowd) state.crowd = data.crowd;
        if (data.queues) state.queues = data.queues;
        if (data.gates) state.gates = data.gates;
        if (data.timeline) state.timeline = data.timeline;

        // Update ticker
        updateTicker(data);

        // Dispatch to active tab handlers
        if (typeof VenueMap !== 'undefined') VenueMap.update(data.crowd);
        if (typeof QueueBoard !== 'undefined') QueueBoard.update(data.queues);
        if (typeof Dashboard !== 'undefined' && activeTab === 'dashboard') Dashboard.update(data);

        // Update gate status on map panel
        if (data.gates) updateGateStatus(data.gates);

        // Handle phase change
        if (data.phase_change) {
            showToast(`Phase: ${data.phase_change.label}`, data.phase_change.description, 'info');
        }

        // Handle alerts
        if (data.alert) {
            showToast('⚠️ Crowd Alert', data.alert.message, 'warning');
            const badge = document.getElementById('alert-badge');
            const count = parseInt(badge.textContent || '0') + 1;
            badge.textContent = count;
            badge.hidden = false;
        }

        // Update phase display
        if (data.timeline) {
            updatePhaseDisplay(data.timeline);
            if (data.timeline.current_phase === 'emergency') {
                document.body.classList.add('emergency-mode');
            } else {
                document.body.classList.remove('emergency-mode');
            }
        }
    }

    // ── Ticker Update ────────────────────────────────────────
    function updateTicker(data) {
        if (data.timeline) {
            animateValue('ticker-phase', data.timeline.phase_label || '—');
            animateValue('ticker-elapsed', data.timeline.elapsed_display || '—');
        }
        if (data.crowd) {
            animateValue('ticker-occupancy', `${data.crowd.occupancy_percentage}%`);
        }
    }

    function updatePhaseDisplay(timeline) {
        const label = document.getElementById('phase-label');
        const desc = document.getElementById('phase-description');
        const progress = document.getElementById('phase-progress');
        if (label) label.textContent = timeline.phase_label || '—';
        if (desc) desc.textContent = timeline.phase_description || '';
        if (progress) progress.style.width = `${(timeline.phase_progress || 0) * 100}%`;
    }

    function updateGateStatus(gates) {
        const container = document.getElementById('gate-status');
        if (!container) return;
        container.innerHTML = gates.map(g => `
            <div class="gate-item">
                <span><span class="gate-status-dot ${g.status}" aria-hidden="true"></span>${g.name.split('—')[0]}</span>
                <span style="color:var(--text-tertiary);font-size:0.72rem">${Math.round(g.congestion * 100)}%</span>
            </div>
        `).join('');
    }

    // ── Fetch Initial Data ───────────────────────────────────
    async function fetchInitialData() {
        try {
            const [venue, crowd, queues] = await Promise.all([
                api('/api/venue'),
                api('/api/crowd'),
                api('/api/queues'),
            ]);

            state.crowd = crowd;
            state.queues = queues.queues || [];

            // Initialize Map
            if (typeof VenueMap !== 'undefined') {
                VenueMap.init(venue.zones);
                VenueMap.update(crowd);
            }

            // Initialize Queue Board
            if (typeof QueueBoard !== 'undefined') {
                QueueBoard.init(queues.queues || []);
            }

            // Update zone details sidebar
            updateZoneDetails(crowd.heatmap || []);

        } catch (e) {
            console.error('Failed to fetch initial data:', e);
            showToast('Connection Error', 'Unable to load venue data. Retrying...', 'critical');
            setTimeout(fetchInitialData, 3000);
        }
    }

    function updateZoneDetails(heatmap) {
        const container = document.getElementById('zone-details');
        if (!container || !heatmap.length) return;

        const sorted = [...heatmap].sort((a, b) => b.density - a.density);
        container.innerHTML = sorted.map(z => `
            <div class="zone-detail-item" role="listitem">
                <span>${z.name}</span>
                <span class="zone-density-badge ${z.status}">${Math.round(z.density * 100)}%</span>
            </div>
        `).join('');
    }

    // ── Fetch Alerts ─────────────────────────────────────────
    async function fetchAlerts() {
        try {
            const data = await api('/api/alerts');
            if (typeof AlertsPanel !== 'undefined') AlertsPanel.update(data);
        } catch (e) { console.error('Failed to fetch alerts:', e); }
    }

    // ── Fetch Dashboard ──────────────────────────────────────
    async function fetchDashboard() {
        try {
            const data = await api('/api/stats');
            if (typeof Dashboard !== 'undefined') Dashboard.init(data);
        } catch (e) { console.error('Failed to fetch dashboard:', e); }
    }

    // ── Simulation Controls ──────────────────────────────────
    function setupSpeedSlider() {
        const slider = document.getElementById('speed-slider');
        const display = document.getElementById('speed-value');
        if (!slider) return;

        slider.addEventListener('input', () => {
            display.textContent = `${slider.value}x`;
        });
        slider.addEventListener('change', async () => {
            await api(`/api/simulate/speed?speed=${slider.value}`, { method: 'POST' });
        });
    }

    function setupPhaseJump() {
        document.querySelectorAll('.phase-jump-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const phase = btn.dataset.phase;
                btn.disabled = true;
                btn.textContent = '⏳';
                try {
                    await api('/api/simulate/phase', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ phase }),
                    });
                    showToast('Phase Jump', `Jumped to ${phase.replace(/_/g, ' ')}`, 'success');
                } catch (e) {
                    showToast('Error', 'Failed to jump phase', 'critical');
                }
                btn.disabled = false;
                if (phase === 'emergency') {
                    btn.textContent = '🚨 TRIGGER EMERGENCY';
                } else {
                    btn.textContent = btn.dataset.phase.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()).replace('Pre Event','Pre-Event').replace('Near Kickoff','Rush Hour').replace('First Half','1st Half').replace('Post Event','Post-Event');
                }
            });
        });
    }

    // ── Toast Notifications ──────────────────────────────────
    function showToast(title, message, level = 'info') {
        const container = document.getElementById('toast-container');
        const toast = document.createElement('div');
        toast.className = `toast ${level}`;
        toast.innerHTML = `<strong>${title}</strong><br><span style="font-size:0.8rem;color:var(--text-secondary)">${message}</span>`;
        container.appendChild(toast);
        setTimeout(() => toast.remove(), 5000);
    }

    // ── API Helper (Enterprise Standard with Retries) ───────
    async function api(url, options = {}, retries = 3) {
        for (let i = 0; i <= retries; i++) {
            try {
                const res = await fetch(url, options);
                if (!res.ok) {
                    const err = await res.json().catch(() => ({}));
                    throw new Error(err.detail || `HTTP ${res.status}`);
                }
                return await res.json();
            } catch (e) {
                const isTransient = i < retries && (e.message.includes('50') || e.message.includes('Failed to fetch'));
                if (isTransient) {
                    const delay = Math.pow(2, i) * 1000;
                    console.warn(`Transient API error. Retrying in ${delay}ms...`, e.message);
                    await new Promise(r => setTimeout(r, delay));
                    continue;
                }
                throw e;
            }
        }
    }

    // ── Animate Value ────────────────────────────────────────
    function animateValue(elementId, newValue) {
        const el = document.getElementById(elementId);
        if (!el || el.textContent === String(newValue)) return;
        el.textContent = newValue;
        el.style.transition = 'none';
        el.style.transform = 'scale(1.1)';
        requestAnimationFrame(() => {
            el.style.transition = 'transform 0.3s var(--ease-spring)';
            el.style.transform = 'scale(1)';
        });
    }

    // ── Public API ───────────────────────────────────────────
    return { init, state, api, showToast, switchTab, updateZoneDetails };
})();

// Boot
document.addEventListener('DOMContentLoaded', App.init);
