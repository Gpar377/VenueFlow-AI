/**
 * VenueFlow AI — SVG Stadium Heatmap
 * Renders an interactive, animated crowd density visualization.
 * GPU-accelerated transitions. Color-coded zones with hover details.
 */

const VenueMap = (() => {
    let svgEl = null;
    let zones = {};
    let tooltipEl = null;

    // Zone polygon paths for a stadium shape
    const ZONE_PATHS = {
        north:       { d: 'M120,40 L380,40 L360,100 L140,100 Z', cx: 250, cy: 65 },
        south:       { d: 'M140,400 L360,400 L380,460 L120,460 Z', cx: 250, cy: 435 },
        east:        { d: 'M400,140 L460,120 L460,380 L400,360 Z', cx: 435, cy: 250 },
        west:        { d: 'M40,120 L100,140 L100,360 L40,380 Z', cx: 65, cy: 250 },
        ne:          { d: 'M360,100 L380,40 L460,120 L400,140 Z', cx: 400, cy: 100 },
        nw:          { d: 'M40,120 L120,40 L140,100 L100,140 Z', cx: 100, cy: 100 },
        se:          { d: 'M400,360 L460,380 L380,460 L360,400 Z', cx: 400, cy: 400 },
        sw:          { d: 'M100,360 L40,380 L120,460 L140,400 Z', cx: 100, cy: 400 },
        concourse_n: { d: 'M140,100 L360,100 L340,140 L160,140 Z', cx: 250, cy: 118 },
        concourse_s: { d: 'M160,360 L340,360 L360,400 L140,400 Z', cx: 250, cy: 382 },
        concourse_e: { d: 'M360,160 L400,140 L400,360 L360,340 Z', cx: 382, cy: 250 },
        concourse_w: { d: 'M100,140 L140,160 L140,340 L100,360 Z', cx: 118, cy: 250 },
    };

    // Density to color mapping
    function densityColor(d) {
        if (d < 0.3) return '#06d6a0';
        if (d < 0.5) return '#6ee7b0';
        if (d < 0.65) return '#ffd166';
        if (d < 0.8) return '#f4845f';
        if (d < 0.9) return '#ef476f';
        return '#d62828';
    }

    function densityOpacity(d) {
        return 0.3 + d * 0.6;
    }

    function init(zoneData) {
        zones = zoneData || {};
        const container = document.getElementById('venue-map');
        if (!container) return;

        // Create SVG
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('viewBox', '0 0 500 500');
        svg.setAttribute('width', '100%');
        svg.setAttribute('height', '100%');
        svg.style.cssText = 'display:block;border-radius:12px;';

        // Background
        const bg = createSVGEl('rect', { x: 0, y: 0, width: 500, height: 500, fill: '#0d1321', rx: 12 });
        svg.appendChild(bg);

        // Field (center)
        const field = createSVGEl('rect', {
            x: 160, y: 160, width: 180, height: 180, rx: 8,
            fill: '#0f4c2d', stroke: '#1a7a47', 'stroke-width': 1.5, opacity: 0.7
        });
        svg.appendChild(field);

        // Field markings
        const fieldCenter = createSVGEl('circle', { cx: 250, cy: 250, r: 30, fill: 'none', stroke: '#1a7a47', 'stroke-width': 1 });
        svg.appendChild(fieldCenter);
        const fieldLine = createSVGEl('line', { x1: 250, y1: 160, x2: 250, y2: 340, stroke: '#1a7a47', 'stroke-width': 1 });
        svg.appendChild(fieldLine);

        // Field label
        const fieldText = createSVGEl('text', { x: 250, y: 254, 'text-anchor': 'middle', fill: '#1a7a47', 'font-size': 11, 'font-family': 'Outfit, sans-serif' });
        fieldText.textContent = '⚽ PITCH';
        svg.appendChild(fieldText);

        // Create zone polygons
        for (const [id, path] of Object.entries(ZONE_PATHS)) {
            const group = createSVGEl('g', { class: 'zone-group', 'data-zone': id, style: 'cursor:pointer' });

            const polygon = createSVGEl('path', {
                d: path.d,
                fill: '#1a2332',
                stroke: 'rgba(255,255,255,0.1)',
                'stroke-width': 1,
                class: 'zone-polygon',
                style: 'transition: fill 0.8s ease, opacity 0.8s ease; will-change: fill, opacity;',
            });

            // Label
            const label = createSVGEl('text', {
                x: path.cx, y: path.cy - 6,
                'text-anchor': 'middle',
                fill: 'rgba(255,255,255,0.8)',
                'font-size': id.startsWith('concourse') ? 7 : 9,
                'font-family': 'Inter, sans-serif',
                'font-weight': 600,
                'pointer-events': 'none',
            });
            label.textContent = (zones[id]?.name || id).replace('Concourse', 'Conc.');

            // Density percentage label
            const densityLabel = createSVGEl('text', {
                x: path.cx, y: path.cy + 10,
                'text-anchor': 'middle',
                fill: 'rgba(255,255,255,0.6)',
                'font-size': 10,
                'font-family': 'JetBrains Mono, monospace',
                'font-weight': 600,
                'pointer-events': 'none',
                class: 'density-label',
            });
            densityLabel.textContent = '0%';

            group.appendChild(polygon);
            group.appendChild(label);
            group.appendChild(densityLabel);

            // Hover effects
            group.addEventListener('mouseenter', () => {
                polygon.setAttribute('stroke', '#06d6a0');
                polygon.setAttribute('stroke-width', '2.5');
            });
            group.addEventListener('mouseleave', () => {
                polygon.setAttribute('stroke', 'rgba(255,255,255,0.1)');
                polygon.setAttribute('stroke-width', '1');
            });

            // Click for details
            group.addEventListener('click', () => showZonePopup(id));

            svg.appendChild(group);
        }

        // Gate indicators
        const gatePositions = {
            gate_a: { x: 250, y: 20 }, gate_b: { x: 380, y: 25 },
            gate_c: { x: 478, y: 250 }, gate_d: { x: 380, y: 475 },
            gate_e: { x: 250, y: 478 }, gate_f: { x: 22, y: 250 },
            gate_g: { x: 22, y: 350 }, gate_h: { x: 478, y: 150 },
        };

        for (const [id, pos] of Object.entries(gatePositions)) {
            const dot = createSVGEl('circle', {
                cx: pos.x, cy: pos.y, r: 6,
                fill: '#06d6a0', stroke: '#0d1321', 'stroke-width': 2,
                class: 'gate-dot', 'data-gate': id,
                style: 'transition: fill 0.5s ease;'
            });
            svg.appendChild(dot);

            const lbl = createSVGEl('text', {
                x: pos.x, y: pos.y - 10,
                'text-anchor': 'middle', fill: 'rgba(255,255,255,0.5)',
                'font-size': 7, 'font-family': 'Inter, sans-serif',
            });
            lbl.textContent = id.replace('gate_', 'G').toUpperCase();
            svg.appendChild(lbl);
        }

        container.innerHTML = '';
        container.appendChild(svg);
        svgEl = svg;
    }

    function update(crowdData) {
        if (!svgEl || !crowdData) return;

        const heatmap = crowdData.heatmap || [];

        heatmap.forEach(zone => {
            const group = svgEl.querySelector(`[data-zone="${zone.id}"]`);
            if (!group) return;

            const polygon = group.querySelector('.zone-polygon');
            const densityLabel = group.querySelector('.density-label');

            if (polygon) {
                polygon.setAttribute('fill', densityColor(zone.density));
                polygon.setAttribute('opacity', densityOpacity(zone.density));
            }
            if (densityLabel) {
                densityLabel.textContent = `${Math.round(zone.density * 100)}%`;
            }
        });

        // Update gate dots
        if (App.state.gates) {
            App.state.gates.forEach(gate => {
                const dot = svgEl.querySelector(`[data-gate="${gate.id}"]`);
                if (dot) {
                    const colors = { clear: '#06d6a0', busy: '#ffd166', congested: '#ef476f', closed: '#5a6478' };
                    dot.setAttribute('fill', colors[gate.status] || '#06d6a0');
                }
            });
        }

        // Update zone details sidebar
        if (typeof App !== 'undefined') App.updateZoneDetails(heatmap);
    }

    function showZonePopup(zoneId) {
        const data = (App.state.crowd.heatmap || []).find(z => z.id === zoneId);
        if (!data) return;

        const container = document.getElementById('zone-details');
        if (!container) return;

        container.innerHTML = `
            <div class="zone-detail-item" style="flex-direction:column;align-items:stretch;padding:16px;background:var(--accent-primary-dim);border:1px solid var(--accent-primary)">
                <strong style="font-size:1rem;margin-bottom:8px">${data.name}</strong>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.82rem">
                    <div>Density: <span class="zone-density-badge ${data.status}">${Math.round(data.density * 100)}%</span></div>
                    <div>Occupancy: ${data.occupancy.toLocaleString()}</div>
                    <div>Capacity: ${data.capacity.toLocaleString()}</div>
                    <div>Type: ${data.zone_type}</div>
                </div>
            </div>
        `;
    }

    // SVG element helper
    function createSVGEl(tag, attrs = {}) {
        const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
        for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
        return el;
    }

    return { init, update };
})();
