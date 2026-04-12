/**
 * VenueFlow AI — Operator Dashboard
 * Real-time analytics view for venue operators.
 */

const Dashboard = (() => {

    function init(data) {
        if (!data) return;
        renderStats(data);
        renderZoneTable(data.zones_by_density || []);
        renderGates(data.gates || []);
        renderParking(data.parking || []);
    }

    function update(wsData) {
        // Quick update from WebSocket ticks
        if (wsData.crowd) {
            const occ = document.getElementById('dash-occupancy');
            const occPct = document.getElementById('dash-occupancy-pct');
            if (occ) occ.textContent = wsData.crowd.total_occupancy?.toLocaleString() || '—';
            if (occPct) occPct.textContent = `${wsData.crowd.occupancy_percentage || 0}%`;
        }
        if (wsData.timeline) {
            const phase = document.getElementById('dash-phase');
            const elapsed = document.getElementById('dash-elapsed');
            if (phase) phase.textContent = wsData.timeline.phase_label || '—';
            if (elapsed) elapsed.textContent = `${wsData.timeline.elapsed_display || '0m'} elapsed`;
        }
        if (wsData.queues) {
            const foodQueues = wsData.queues.filter(q => q.service_type === 'food');
            const avgWait = foodQueues.length
                ? (foodQueues.reduce((s, q) => s + q.wait_time_minutes, 0) / foodQueues.length).toFixed(1)
                : '0';
            const totalInQueues = wsData.queues.reduce((s, q) => s + q.queue_length, 0);

            const avgEl = document.getElementById('dash-avg-wait');
            const queueEl = document.getElementById('dash-in-queues');
            if (avgEl) avgEl.textContent = avgWait;
            if (queueEl) queueEl.textContent = totalInQueues.toLocaleString();

            // Update zone table from heatmap
            if (wsData.crowd?.heatmap) renderZoneTable(wsData.crowd.heatmap);
        }
        if (wsData.gates) renderGates(wsData.gates);
    }

    function renderStats(data) {
        const occ = document.getElementById('dash-occupancy');
        const occPct = document.getElementById('dash-occupancy-pct');
        const phase = document.getElementById('dash-phase');
        const elapsed = document.getElementById('dash-elapsed');
        const avgWait = document.getElementById('dash-avg-wait');
        const inQueues = document.getElementById('dash-in-queues');

        if (occ) occ.textContent = data.total_occupancy?.toLocaleString() || '—';
        if (occPct) occPct.textContent = `${data.occupancy_percentage || 0}%`;
        if (phase) phase.textContent = data.event_phase?.phase_label || '—';
        if (elapsed) elapsed.textContent = `${data.event_phase?.elapsed_display || '0m'} elapsed`;
        if (avgWait) avgWait.textContent = data.service_summary?.avg_food_wait || '—';
        if (inQueues) inQueues.textContent = data.service_summary?.total_in_queues?.toLocaleString() || '—';
    }

    function renderZoneTable(zones) {
        const tbody = document.getElementById('zone-table-body');
        if (!tbody) return;

        const sorted = [...zones].sort((a, b) => (b.density || 0) - (a.density || 0));

        tbody.innerHTML = sorted.map(z => {
            const density = z.density || 0;
            const status = z.status || 'low';
            const statusColors = { low: 'var(--density-low)', moderate: 'var(--density-moderate)', high: 'var(--density-high)', critical: 'var(--density-critical)' };

            return `
                <tr>
                    <td style="font-weight:500">${z.name || z.id}</td>
                    <td style="color:var(--text-secondary)">${z.zone_type || '—'}</td>
                    <td style="font-family:var(--font-mono)">${(z.occupancy || z.current_occupancy || 0).toLocaleString()}</td>
                    <td style="font-family:var(--font-mono);color:var(--text-tertiary)">${(z.capacity || 0).toLocaleString()}</td>
                    <td>
                        <div style="display:flex;align-items:center;gap:8px">
                            <div style="flex:1;height:6px;background:var(--bg-tertiary);border-radius:99px;overflow:hidden">
                                <div style="height:100%;width:${Math.round(density * 100)}%;background:${statusColors[status]};border-radius:99px;transition:width 1s ease"></div>
                            </div>
                            <span style="font-family:var(--font-mono);font-size:0.75rem;min-width:35px">${Math.round(density * 100)}%</span>
                        </div>
                    </td>
                    <td><span class="zone-density-badge ${status}">${status}</span></td>
                </tr>
            `;
        }).join('');
    }

    function renderGates(gates) {
        const container = document.getElementById('dash-gates');
        if (!container) return;

        container.innerHTML = gates.map(g => {
            const statusColors = { clear: 'var(--density-low)', busy: 'var(--density-moderate)', congested: 'var(--density-high)', closed: 'var(--text-tertiary)' };
            return `
                <div class="dash-gate-item">
                    <div class="label"><span class="gate-status-dot ${g.status}" style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${statusColors[g.status]};margin-right:6px"></span>${g.name.split('—')[0]}</div>
                    <div class="value">${g.status} • ${Math.round(g.congestion * 100)}% flow</div>
                </div>
            `;
        }).join('');
    }

    function renderParking(lots) {
        const container = document.getElementById('dash-parking');
        if (!container) return;

        container.innerHTML = lots.map(p => `
            <div class="dash-parking-item">
                <div class="label">🅿️ ${p.name.split('—')[0]}</div>
                <div class="value">${Math.round(p.availability * 100)}% available • ${p.current_vehicles} vehicles</div>
            </div>
        `).join('');
    }

    return { init, update };
})();
