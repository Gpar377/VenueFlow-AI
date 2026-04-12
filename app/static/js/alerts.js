/**
 * VenueFlow AI — Alerts Panel
 * Displays AI crowd analysis, insights, predictions, and active alerts.
 */

const AlertsPanel = (() => {
    function update(data) {
        if (!data) return;

        const analysis = data.analysis || {};

        // Crowd health score
        const healthScore = document.getElementById('crowd-health-score');
        const healthBar = document.getElementById('crowd-health-bar');
        if (healthScore) healthScore.textContent = analysis.crowd_health_score || '—';
        if (healthBar) healthBar.style.width = `${analysis.crowd_health_score || 0}%`;

        // Risk level
        const riskEl = document.getElementById('risk-level');
        if (riskEl) {
            const level = analysis.risk_level || 'low';
            riskEl.textContent = level.toUpperCase();
            const colors = { low: 'var(--accent-primary)', moderate: 'var(--accent-warning)', high: 'var(--accent-danger)', critical: '#d62828' };
            riskEl.style.color = colors[level] || 'var(--text-primary)';
        }

        // Danger zone count
        const dangerCount = document.getElementById('danger-zone-count');
        if (dangerCount) dangerCount.textContent = (data.danger_zones || []).length;

        // Insights
        renderList('insight-list', analysis.insights || []);
        renderList('prediction-list', analysis.predictions || []);
        renderList('recommendation-list', analysis.recommendations || []);

        // Active alerts
        const alertsContainer = document.getElementById('active-alerts-list');
        if (alertsContainer) {
            const zones = data.danger_zones || [];
            if (zones.length === 0) {
                alertsContainer.innerHTML = '<p class="placeholder-text">No active alerts — all clear! ✅</p>';
            } else {
                alertsContainer.innerHTML = zones.map(z => `
                    <div class="alert-item warning" role="alert">
                        <strong>⚠️ ${z.name}</strong> — Density at ${Math.round(z.density * 100)}% (above 85% threshold)
                    </div>
                `).join('');
            }
        }
    }

    function renderList(containerId, items) {
        const el = document.getElementById(containerId);
        if (!el) return;
        el.innerHTML = items.length
            ? items.map(item => `<li>${item}</li>`).join('')
            : '<li style="color:var(--text-tertiary)">No data available yet</li>';
    }

    return { update };
})();
