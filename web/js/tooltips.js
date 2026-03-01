/* tooltips.js — Mouse-following tooltip for each node (no external bridge needed) */

'use strict';

let _tooltipEl = null;

function _getTooltipEl() {
  if (!_tooltipEl) {
    _tooltipEl = document.createElement('div');
    _tooltipEl.id = 'cy-tooltip';
    document.body.appendChild(_tooltipEl);
  }
  return _tooltipEl;
}

/**
 * Initialize mouse-following tooltips for all Cytoscape nodes.
 * @param {Object} cy - Cytoscape instance
 */
function initTooltips(cy) {
  const tip = _getTooltipEl();

  cy.on('mouseover', 'node', function(evt) {
    const node = evt.target;
    const data = node.data();

    // Skip invisible port nodes — no tooltip needed
    if (data.type === 'port') return;

    _renderTooltip(tip, data);
    tip.style.display = 'block';
  });

  cy.on('mousemove', 'node', function(evt) {
    const e = evt.originalEvent;
    if (!e) return;
    const x = e.clientX + 16;
    const y = e.clientY + 16;
    const w = tip.offsetWidth || 220;
    const h = tip.offsetHeight || 80;
    tip.style.left = (x + w > window.innerWidth ? x - w - 32 : x) + 'px';
    tip.style.top  = (y + h > window.innerHeight ? y - h - 32 : y) + 'px';
  });

  cy.on('mouseout', 'node', function() {
    tip.style.display = 'none';
  });

  cy.on('tap', function(evt) {
    if (evt.target === cy) tip.style.display = 'none';
  });

  cy.on('viewport', function() {
    tip.style.display = 'none';
  });
}

/** Build tooltip DOM from node data (no innerHTML with untrusted content). */
function _renderTooltip(container, data) {
  container.textContent = '';  // clear

  const type = data.type;

  if (type === 'ranking') {
    _row(container, null, data.label, 'tooltip-title');
    if (data.ranking) _row(container, 'Rank', `#${data.ranking}`);
    if (data.record) _row(container, 'Record', data.record);
    else if (data.sublabel) _row(container, 'Seed', data.sublabel);
    if (data.aesUrl) {
      const link = document.createElement('a');
      link.className = 'tooltip-link';
      link.href = data.aesUrl;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.textContent = 'View on AES \u2197';
      container.appendChild(link);
    }
    return;
  }

  // match node
  const teams = data.teams || [];
  const home = teams.find(t => t.role === 'home');
  const away = teams.find(t => t.role === 'away');
  const work = teams.find(t => t.role === 'work');

  const homeName = home ? home.name : (data.homePlaceholder || 'TBD');
  const awayName = away ? away.name : (data.awayPlaceholder || 'TBD');

  _row(container, null, homeName + ' vs ' + awayName, 'tooltip-title');

  const statusText = {
    scheduled: '\u23F3 Scheduled',
    in_progress: '\u25CF In Progress',
    finished: '\u2713 Finished',
  }[data.status] || data.status;
  _row(container, 'Status', statusText);

  if (data.time) _row(container, 'Time', _formatTime(data.time));
  if (data.court) _row(container, 'Court', data.court);

  const scores = (data.setScores || []).map(s => s.text).filter(Boolean).join('  |  ');
  if (scores) {
    const scoreEl = document.createElement('div');
    scoreEl.className = 'tooltip-scores';
    scoreEl.textContent = scores;
    container.appendChild(scoreEl);
  }

  if (work) _row(container, 'Work', work.name);
  if (data.poolName) _row(container, 'Pool', data.poolName);
  if (data.bracketName) _row(container, 'Bracket', data.bracketName);
  if (data.roundName) _row(container, 'Round', data.roundName);

  if (data.aesUrl) {
    const link = document.createElement('a');
    link.className = 'tooltip-link';
    link.href = data.aesUrl;
    link.target = '_blank';
    link.rel = 'noopener noreferrer';
    link.textContent = 'View on AES \u2197';
    container.appendChild(link);
  }
}

/** Append a label/value row (or a single-span title row) to the container. */
function _row(container, label, value, extraClass) {
  if (!value && value !== 0) return;
  if (!label) {
    const el = document.createElement('div');
    el.className = extraClass || 'tooltip-row';
    el.textContent = value;
    container.appendChild(el);
    return;
  }
  const row = document.createElement('div');
  row.className = 'tooltip-row';
  const lbl = document.createElement('span');
  lbl.className = 'tooltip-label';
  lbl.textContent = label;
  const val = document.createElement('span');
  val.className = 'tooltip-value';
  val.textContent = value;
  row.appendChild(lbl);
  row.appendChild(val);
  container.appendChild(row);
}

function _formatTime(isoString) {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
           + ' ' + d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch {
    return isoString;
  }
}
