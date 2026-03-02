/* graph.js — Cytoscape.js initialization with court-slot packing layout */

'use strict';

// Layout constants
const MATCH_H     = 44;   // match card height
const PORT_H      = 14;   // height per port row (edge alignment)
const MATCH_W     = 150;  // match card width
const PHASE_WIDTH = 180;  // px between phase columns
const SLOT_GAP    = 10;   // vertical gap between time slots
const RANKING_ROW_H = 18; // vertical spacing between ranking nodes
const RANKING_W   = 110;  // ranking node width

let cy = null;
let _courtColorMap = null;
let _highlightState = { active: false, teamIds: new Set() };

// HTML-escape helper
function esc(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Build the rich match card HTML for a parent match node.
 */
function buildMatchCardHTML(data) {
  const teams = data.teams || [];
  const home = teams.find(t => t.role === 'home');
  const away = teams.find(t => t.role === 'away');
  const work = teams.find(t => t.role === 'work');
  const scores = data.setScores || [];

  const homeName = home ? home.name : (data.homePlaceholder || 'TBD');
  const awayName = away ? away.name : (data.awayPlaceholder || 'TBD');

  const homeScores = scores.map(s => s.home).join('|');
  const awayScores = scores.map(s => s.away).join('|');

  const homeWinClass = (data.homeWon === true) ? ' match-winner' : '';
  const awayWinClass = (data.homeWon === false) ? ' match-winner' : '';

  const courtColor = _courtColorMap ? _courtColorMap.get(data.court) : null;
  const styleParts = [];
  if (courtColor) {
    styleParts.push(`background:${courtColor.bg}`, `border-color:${courtColor.border}`);
  }
  if (_highlightState.active) {
    const isTeamNode = teams.some(t => t.role !== 'work' && _highlightState.teamIds.has(t.id));
    // Don't dim nodes that are follow-on targets (empty teams but in trajectory)
    if (!isTeamNode && teams.length > 0) styleParts.push('opacity:0.15');
  }
  const styleAttr = styleParts.length > 0 ? ` style="${styleParts.join(';')}"` : '';
  let html = `<div class="match-card"${styleAttr}>`;
  html += `<div class="match-row home${homeWinClass}">`;
  html += `<span class="team-name">${esc(homeName)}</span>`;
  if (homeScores) html += `<span class="set-scores">${esc(homeScores)}</span>`;
  html += '</div>';

  html += `<div class="match-row away${awayWinClass}">`;
  html += `<span class="team-name">${esc(awayName)}</span>`;
  if (awayScores) html += `<span class="set-scores">${esc(awayScores)}</span>`;
  html += '</div>';

  if (work) {
    html += `<div class="match-row work"><span class="team-name">\u2692 ${esc(work.name)}</span></div>`;
  }
  html += '</div>';
  return html;
}

/**
 * Build the ranking card HTML (start/end/intermediate columns).
 */
function buildRankingCardHTML(data) {
  const label = data.label || '';
  const rank = data.ranking;
  const record = data.record;
  const sub = data.sublabel;

  let dimStyle = '';
  if (_highlightState.active) {
    const nodeTeams = data.teams || [];
    const isTeamNode = nodeTeams.some(t => _highlightState.teamIds.has(t.id));
    if (!isTeamNode) dimStyle = ' style="opacity:0.15"';
  }
  let html = `<div class="ranking-card"${dimStyle}>`;
  if (rank) html += `<span class="rank-badge">#${esc(rank)}</span>`;
  html += `<span class="rank-name">${esc(label)}</span>`;
  if (record) html += `<span class="rank-record">${esc(record)}</span>`;
  else if (sub) html += `<span class="rank-sub">${esc(sub)}</span>`;
  html += '</div>';
  return html;
}

/**
 * Shared layout helper: court-slot packing for match phases, centered for ranking phases.
 *
 * @param {Array} nodes - non-port node descriptors: {id, type, phase, time, court, globalRow}
 * @param {Array} portNodes - port node descriptors: {id, parentId, portRole}
 * @param {Map|null} phaseRemap - Map<originalPhase, compactIndex> or null to use raw phase
 * @returns {Object} positions: {id: {x, y}}
 */
function _computePackedPositions(nodes, portNodes, phaseRemap) {
  const positions = {};
  const parentPositions = {};

  // Separate match nodes and ranking nodes by phase
  const matchPhases = {};   // compactPhase -> [{id, time, court}]
  const rankingPhases = {}; // compactPhase -> [{id, globalRow}]

  nodes.forEach(n => {
    const rawPhase = n.phase;
    const compactPhase = phaseRemap ? (phaseRemap.get(rawPhase) != null ? phaseRemap.get(rawPhase) : rawPhase) : rawPhase;

    if (n.type === 'match') {
      if (!matchPhases[compactPhase]) matchPhases[compactPhase] = [];
      matchPhases[compactPhase].push({ id: n.id, time: n.time || '', court: n.court || '', compactPhase });
    } else {
      // ranking nodes
      if (!rankingPhases[compactPhase]) rankingPhases[compactPhase] = [];
      rankingPhases[compactPhase].push({ id: n.id, globalRow: n.globalRow || 0, compactPhase });
    }
  });

  // Compute match phase heights (for centering ranking phases)
  // Phase height = sum of (numCourts * MATCH_H + SLOT_GAP) per time slot
  const phaseHeights = {};

  Object.entries(matchPhases).forEach(([compactPhase, matchNodes]) => {
    // Group by time slot, sort chronologically
    const byTime = {};
    matchNodes.forEach(m => {
      const t = m.time || '';
      if (!byTime[t]) byTime[t] = [];
      byTime[t].push(m);
    });

    const sortedTimes = Object.keys(byTime).sort();
    let cumOffset = 0;
    const nodeY = {};

    sortedTimes.forEach(t => {
      const slotMatches = byTime[t].slice().sort((a, b) => a.court.localeCompare(b.court));
      slotMatches.forEach((m, courtIdx) => {
        nodeY[m.id] = cumOffset + courtIdx * MATCH_H;
      });
      cumOffset += slotMatches.length * MATCH_H + SLOT_GAP;
    });

    // Store height (remove trailing gap)
    phaseHeights[compactPhase] = Math.max(0, cumOffset - SLOT_GAP);

    // Assign positions for match nodes
    matchNodes.forEach(m => {
      const x = Number(compactPhase) * PHASE_WIDTH;
      const y = nodeY[m.id] || 0;
      parentPositions[m.id] = { x, y };
      positions[m.id] = { x, y };
    });
  });

  // Max column height across all match phases (used to center ranking nodes)
  const maxMatchHeight = Object.values(phaseHeights).reduce((max, h) => Math.max(max, h), 0);

  // Ranking phases: center vertically, sort by globalRow
  Object.entries(rankingPhases).forEach(([compactPhase, rankNodes]) => {
    const count = rankNodes.length;
    const totalHeight = count * RANKING_ROW_H;
    const startY = (maxMatchHeight - totalHeight) / 2;

    rankNodes.sort((a, b) => a.globalRow - b.globalRow);
    rankNodes.forEach((r, idx) => {
      const x = Number(compactPhase) * PHASE_WIDTH;
      const y = startY + idx * RANKING_ROW_H;
      parentPositions[r.id] = { x, y };
      positions[r.id] = { x, y };
    });
  });

  // Port nodes: relative to parent
  portNodes.forEach(p => {
    const parentPos = parentPositions[p.parentId];
    if (parentPos) {
      let yOffset = 0;
      if (p.portRole === 'home') yOffset = -PORT_H;
      else if (p.portRole === 'away') yOffset = 0;
      else if (p.portRole === 'work') yOffset = PORT_H;
      positions[p.id] = { x: parentPos.x, y: parentPos.y + yOffset };
    } else {
      positions[p.id] = { x: 0, y: 0 };
    }
  });

  return positions;
}

/**
 * Compute preset positions for all nodes from JSON elements.
 */
function computePositions(elements) {
  const allNodes = elements.nodes || [];

  const nodes = [];
  const portNodes = [];

  allNodes.forEach(n => {
    const d = n.data;
    if (d.type === 'port') {
      portNodes.push({ id: d.id, parentId: d.parentId, portRole: d.portRole });
    } else {
      nodes.push({ id: d.id, type: d.type, phase: d.phase, time: d.time, court: d.court, globalRow: d.globalRow });
    }
  });

  return _computePackedPositions(nodes, portNodes, null);
}

/**
 * Build a map from court string → {bg, border} color values based on venue.
 * Venues share a hue family; courts within a venue vary in lightness.
 * @param {Object} cy - Cytoscape instance
 * @returns {Map<string, {bg: string, border: string}>}
 */
function buildCourtColorMap(cy) {
  const HUE_PALETTE = [210, 150, 30, 270, 340, 60, 180, 0]; // blue, green, orange, purple, pink, yellow, teal, red
  const SAT = 60;

  // Collect unique courts and parse venue prefix
  const venueToCourtSet = new Map(); // venue → Set of court strings (ordered by first seen)
  const courtToVenueIdx = new Map(); // court → index within venue

  cy.nodes('[type="match"]').forEach(n => {
    const court = n.data('court');
    if (!court) return;
    // Split on " Ct." to get venue prefix; handles "VDL Ct. 1", "VDL AUX Ct. 2", etc.
    const parts = court.split(' Ct.');
    const venue = parts.length > 1 ? parts[0].trim() : court;
    if (!venueToCourtSet.has(venue)) venueToCourtSet.set(venue, []);
    const courts = venueToCourtSet.get(venue);
    if (!courts.includes(court)) courts.push(court);
  });

  // Build court → {bg, border}
  const colorMap = new Map();
  let venueIdx = 0;
  venueToCourtSet.forEach((courts, venue) => {
    const hue = HUE_PALETTE[venueIdx % HUE_PALETTE.length];
    courts.forEach((court, courtIdx) => {
      const bgLight = Math.max(92 - courtIdx * 3, 30);
      const borderLight = Math.max(55 - courtIdx * 3, 20);
      colorMap.set(court, {
        bg: `hsl(${hue},${SAT}%,${bgLight}%)`,
        border: `hsl(${hue},${SAT}%,${borderLight}%)`,
      });
    });
    venueIdx++;
  });

  return colorMap;
}

/**
 * Initialize the Cytoscape graph with tournament elements.
 * @param {Object} jsonData - Parsed tournament.json data
 * @returns {Object} cytoscape instance
 */
function initGraph(jsonData) {
  const positions = computePositions(jsonData.elements);

  cy = cytoscape({
    container: document.getElementById('cy'),
    elements: jsonData.elements,
    userZoomingEnabled: true,
    userPanningEnabled: true,
    boxSelectionEnabled: false,
    autoungrabify: true,
    autounselectify: true,
    minZoom: 0.05,
    maxZoom: 3,

    layout: {
      name: 'preset',
      positions: node => positions[node.id()] || { x: 0, y: 0 },
      fit: true,
      padding: 40,
    },

    style: [
      // --- BASE NODE ---
      {
        selector: 'node',
        style: {
          'label': '',
          'width': RANKING_W,
          'height': RANKING_ROW_H,
          'border-width': 1,
          'background-color': '#f1f5f9',
          'border-color': '#94a3b8',
        },
      },

      // --- RANKING NODES ---
      {
        selector: 'node[type="ranking"]',
        style: {
          'shape': 'round-tag',
          'background-color': '#f1f5f9',
          'border-color': '#94a3b8',
          'width': RANKING_W,
          'height': RANKING_ROW_H,
          'background-opacity': 0,
          'border-width': 0,
        },
      },

      // --- MATCH PARENT NODES — invisible container, HTML overlay renders card ---
      {
        selector: 'node[type="match"]',
        style: {
          'shape': 'roundrectangle',
          'width': MATCH_W,
          'height': MATCH_H,
          'background-opacity': 0,
          'border-width': 0,
          'label': '',
        },
      },

      // --- PORT NODES — tiny invisible for edge routing ---
      {
        selector: 'node[type="port"]',
        style: {
          'width': 1,
          'height': 1,
          'background-opacity': 0,
          'border-width': 0,
          'label': '',
          'padding': 0,
        },
      },

      // --- EDGES (base) ---
      {
        selector: 'edge',
        style: {
          'width': 1,
          'curve-style': 'bezier',
          'target-arrow-shape': 'none',
          'line-color': '#cbd5e1',
          'opacity': 0.6,
        },
      },

      // Home team edges — solid blue
      {
        selector: 'edge[role="home"]',
        style: {
          'line-color': '#3b82f6',
          'width': 1.5,
          'opacity': 0.6,
        },
      },
      // Away team edges — solid orange
      {
        selector: 'edge[role="away"]',
        style: {
          'line-color': '#f97316',
          'width': 1.5,
          'opacity': 0.6,
        },
      },
      // Work team edges — dashed gray
      {
        selector: 'edge[role="work"]',
        style: {
          'line-color': '#94a3b8',
          'width': 1,
          'opacity': 0.3,
          'line-style': 'dashed',
        },
      },

      // Follow-on (potential path) edges — dashed light blue, dimmed
      {
        selector: 'edge[type="follow_on"]',
        style: {
          'line-color': '#93c5fd',
          'width': 1,
          'opacity': 0.25,
          'line-style': 'dashed',
          'line-dash-pattern': [4, 4],
          'target-arrow-shape': 'triangle',
          'target-arrow-color': '#93c5fd',
          'arrow-scale': 0.5,
        },
      },

      // --- EDGE HIGHLIGHT CLASS ---
      {
        selector: 'edge.edge-highlight',
        style: {
          'opacity': 1.0,
          'width': 2.5,
        },
      },

      // --- TRAJECTORY WIN/LOSS CLASSES ---
      {
        selector: 'node.team-win',
        style: {
          'background-opacity': 0.1,
          'background-color': '#22c55e',
          'border-width': 2,
          'border-color': '#16a34a',
        },
      },
      {
        selector: 'node.team-loss',
        style: {
          'background-opacity': 0.1,
          'background-color': '#ef4444',
          'border-width': 2,
          'border-color': '#dc2626',
        },
      },

      // --- DIMMED (highlight mode — non-team elements) ---
      { selector: 'node.dimmed', style: { 'opacity': 0.15 } },
      { selector: 'edge.dimmed', style: { 'opacity': 0.08 } },

      // --- SELECTED ---
      {
        selector: 'node:selected',
        style: { 'border-width': 2, 'border-color': '#2563eb' },
      },
    ],
  });

  // Register HTML label extension for rich node rendering
  if (typeof cy.nodeHtmlLabel === 'function') {
    cy.nodeHtmlLabel([
      {
        query: 'node[type="match"]',
        halign: 'center',
        valign: 'center',
        tpl: function(data) {
          return buildMatchCardHTML(data);
        },
      },
      {
        query: 'node[type="ranking"]',
        halign: 'center',
        valign: 'center',
        tpl: function(data) {
          return buildRankingCardHTML(data);
        },
      },
      {
        query: 'node:hidden',
        halign: 'center',
        valign: 'center',
        tpl: function() { return ''; },
      },
    ]);
  }

  _courtColorMap = buildCourtColorMap(cy);

  return cy;
}

/**
 * Re-run the preset layout using all nodes (resets positions from data).
 */
function rerunLayout() {
  if (!cy) return;

  const nodes = [];
  const portNodes = [];

  cy.nodes().forEach(n => {
    const d = n.data();
    if (d.type === 'port') {
      portNodes.push({ id: n.id(), parentId: d.parentId, portRole: d.portRole });
    } else {
      nodes.push({ id: n.id(), type: d.type, phase: d.phase, time: d.time, court: d.court, globalRow: d.globalRow });
    }
  });

  const allPositions = _computePackedPositions(nodes, portNodes, null);

  const layout = cy.layout({
    name: 'preset',
    positions: node => allPositions[node.id()] || { x: 0, y: 0 },
    fit: false,
    animate: true,
    animationDuration: 300,
  });
  layout.one('layoutstop', () => fitToVisible(40));
  layout.run();
}

/**
 * Fit the viewport to visible elements only.
 * @param {number} [padding=40] - padding in pixels
 */
function fitToVisible(padding) {
  if (!cy) return;
  const pad = padding != null ? padding : 40;
  const visible = cy.elements().filter(e => e.visible());
  if (visible.length > 0) {
    cy.fit(visible, pad);
  } else {
    cy.fit(pad);
  }
}

/**
 * Relayout visible nodes into compact sequential columns (no gaps from hidden phases).
 * Animates the transition and fits to visible content when done.
 */
function relayoutVisible() {
  if (!cy) return;

  const nodes = [];
  const portNodes = [];

  cy.nodes().forEach(n => {
    const d = n.data();
    if (!n.visible()) return;
    if (d.type === 'port') {
      portNodes.push({ id: n.id(), parentId: d.parentId, portRole: d.portRole });
    } else {
      nodes.push({ id: n.id(), type: d.type, phase: d.phase, time: d.time, court: d.court, globalRow: d.globalRow });
    }
  });

  // Build phase remap: keep start/end ranking separated by a gap from match phases
  // Use visible nodes only so end-ranking phase is correctly identified when some phases are hidden
  const globalMaxPhase = nodes.length > 0 ? Math.max(...nodes.map(n => n.phase)) : 0;
  const uniquePhases = [...new Set(nodes.map(n => n.phase))].sort((a, b) => a - b);
  const phaseRemap = new Map();
  let compactIdx = 0;
  uniquePhases.forEach(phase => {
    if (phase === 0) {
      phaseRemap.set(phase, compactIdx++);
      compactIdx++; // gap after start ranking
      return;
    }
    if (phase === globalMaxPhase) return; // handled after loop
    phaseRemap.set(phase, compactIdx++);
  });
  if (uniquePhases.includes(globalMaxPhase)) {
    compactIdx++; // gap before terminal ranking
    phaseRemap.set(globalMaxPhase, compactIdx);
  }

  const allPositions = _computePackedPositions(nodes, portNodes, phaseRemap);

  const layout = cy.layout({
    name: 'preset',
    positions: node => allPositions[node.id()] || node.position(),
    fit: false,
    animate: true,
    animationDuration: 300,
  });
  layout.one('layoutstop', () => fitToVisible(40));
  layout.run();
}
