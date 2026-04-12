/**
 * VenueFlow AI — Live Queue Board
 * Renders sortable, filterable queue cards with wait times and predictions.
 */

const QueueBoard = (() => {
    let currentFilter = 'all';
    let currentSort = 'wait';
    let queues = [];

    function init(data) {
        queues = data || [];
        setupFilters();
        setupSort();
        render();
    }

    function update(data) {
        if (data) queues = data;
        render();
    }

    function setupFilters() {
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentFilter = btn.dataset.filter;
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.toggle('active', b === btn));
                render();
            });
        });
    }

    function setupSort() {
        document.querySelectorAll('.sort-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                currentSort = btn.dataset.sort;
                document.querySelectorAll('.sort-btn').forEach(b => b.classList.toggle('active', b === btn));
                render();
            });
        });
    }

    function render() {
        const grid = document.getElementById('queue-grid');
        if (!grid) return;

        let filtered = currentFilter === 'all'
            ? queues
            : queues.filter(q => q.service_type === currentFilter);

        if (currentSort === 'wait') {
            filtered.sort((a, b) => a.wait_time_minutes - b.wait_time_minutes);
        } else {
            filtered.sort((a, b) => a.name.localeCompare(b.name));
        }

        grid.innerHTML = filtered.map(q => renderCard(q)).join('');
    }

    function renderCard(q) {
        const waitPct = Math.min(100, (q.wait_time_minutes / 30) * 100);
        const barColor = {
            short: 'var(--density-low)',
            moderate: 'var(--density-moderate)',
            long: 'var(--density-high)',
            very_long: 'var(--density-critical)',
        }[q.wait_status] || 'var(--density-low)';

        const trendArrow = { growing: '📈', shrinking: '📉', stable: '➡️' }[q.trend] || '➡️';

        const typeIcon = {
            food: '🍔', restroom: '🚻', merchandise: '🛍️', medical: '🏥'
        }[q.service_type] || '📍';

        return `
            <div class="queue-card" role="listitem" aria-label="${q.name} - ${q.wait_time_minutes} minute wait">
                <div class="queue-card-header">
                    <div>
                        <div class="queue-card-name">${q.name}</div>
                        <div class="queue-card-zone">${typeIcon} ${q.service_type} • ${q.zone_id.replace('concourse_','').toUpperCase()} Concourse</div>
                    </div>
                    <div class="queue-wait-time ${q.wait_status}">
                        ${q.wait_time_minutes.toFixed(0)}<span class="unit"> min</span>
                    </div>
                </div>

                <div class="queue-bar">
                    <div class="queue-bar-fill" style="width:${waitPct}%;background:${barColor}"></div>
                </div>

                <div class="queue-meta">
                    <span>${q.queue_length} in queue • ${q.servers} servers</span>
                    <span class="queue-trend ${q.trend}">${trendArrow} ${q.trend}</span>
                </div>

                ${q.best_time_prediction ? `<div class="queue-prediction">💡 ${q.best_time_prediction}</div>` : ''}

                ${q.menu_items && q.menu_items.length ? `
                    <div style="margin-top:8px;font-size:0.72rem;color:var(--text-tertiary)">
                        ${q.menu_items.slice(0, 4).join(' • ')}${q.menu_items.length > 4 ? ' ...' : ''}
                    </div>
                ` : ''}
            </div>
        `;
    }

    return { init, update };
})();
