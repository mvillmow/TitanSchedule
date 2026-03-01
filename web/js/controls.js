/* controls.js — UI controls: team dropdown, day filter, zoom */

'use strict';

// Track active filters
let _activeDates = new Set();      // set of ISO date strings that are "active" (selected) days
let _dateToPhases = new Map();     // Map<ISO-date-string, Set<number>> — date → phase numbers
let _activeTeamIds = [];           // array of active team IDs
let _positionsCompacted = false;   // true when relayoutVisible() has moved nodes
let _highlightedTeamIds = [];      // team IDs currently highlighted (node-click only)

/**
 * Initialize all UI controls and bind events to the Cytoscape instance.
 * @param {Object} cy - Cytoscape instance
 * @param {Object} metadata - Tournament metadata from JSON
 */
function initControls(cy, metadata) {
  _initDayFilter(cy, metadata);
  _initTeamDropdown(cy, metadata);
  _initZoomControls(cy);
  _initNodeClickHandler(cy);
}

// ------------------------------------------------------------------ //
// Day filter                                                           //
// ------------------------------------------------------------------ //

function _initDayFilter(cy, metadata) {
  const phases = metadata.phases || [];

  _dateToPhases.clear();

  // First pass: assign match phases to their date
  phases.forEach(p => {
    if (p.type === 'match' && p.date) {
      if (!_dateToPhases.has(p.date)) _dateToPhases.set(p.date, new Set());
      _dateToPhases.get(p.date).add(p.phase);
    }
  });

  // Second pass: assign ranking_intermediate phases to BOTH adjacent dates.
  const sortedMatchDates = Array.from(_dateToPhases.keys()).sort();
  phases.forEach(p => {
    if (p.type === 'ranking_intermediate' && p.date) {
      // Add to the preceding day (phase's own date)
      if (!_dateToPhases.has(p.date)) _dateToPhases.set(p.date, new Set());
      _dateToPhases.get(p.date).add(p.phase);
      // Also add to the next date after p.date
      const nextDate = sortedMatchDates.find(d => d > p.date);
      if (nextDate && _dateToPhases.has(nextDate)) {
        _dateToPhases.get(nextDate).add(p.phase);
      }
    }
  });

  const sortedDates = Array.from(_dateToPhases.keys()).sort();

  const container = document.getElementById('day-filter-row');
  if (!container) return;

  // "All" button
  const allBtn = document.createElement('button');
  allBtn.className = 'day-filter active';
  allBtn.textContent = 'All';
  allBtn.dataset.dayAll = '1';
  allBtn.addEventListener('click', () => {
    _activeDates.clear();
    container.querySelectorAll('.day-filter').forEach(b => b.classList.remove('active'));
    allBtn.classList.add('active');
    _clearHighlight(cy);
    _applyFilters(cy);
  });
  container.appendChild(allBtn);

  // One button per unique date
  sortedDates.forEach(date => {
    const btn = document.createElement('button');
    btn.className = 'day-filter';
    btn.textContent = _fmtDate(date);
    btn.dataset.date = date;
    btn.addEventListener('click', () => {
      if (_activeDates.has(date)) {
        _activeDates.delete(date);
        btn.classList.remove('active');
      } else {
        _activeDates.add(date);
        btn.classList.add('active');
      }
      const allSelected = _activeDates.size === 0;
      allBtn.classList.toggle('active', allSelected);
      _clearHighlight(cy);
      _applyFilters(cy);
    });
    container.appendChild(btn);
  });
}

function _fmtDate(iso) {
  const d = new Date(iso + 'T12:00:00');
  return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
}

// ------------------------------------------------------------------ //
// Combined filter application                                          //
// ------------------------------------------------------------------ //

/**
 * Single function that owns visibility state. Steps:
 *   1. Reset all visibility + remove classes
 *   2. Day filter (hide nodes outside selected phases; always show phase 0 + max phase)
 *   3. Hide edges where source or target is hidden
 *   4. activateTrajectory — layers team path on top of day filter
 *   5. Relayout if any filter active, else fit
 */
function _applyFilters(cy) {
  const showAllDays = _activeDates.size === 0;
  const hasTeam = _activeTeamIds.length > 0;

  cy.batch(() => {
    // Step 1: reset visibility and trajectory classes
    cy.elements().removeClass('team-win team-loss edge-highlight dimmed');
    cy.elements().style('display', 'element');

    // Step 2: day filter
    if (!showAllDays) {
      const maxPhase = Math.max(...cy.nodes().map(n => n.data('phase')));
      const visiblePhases = new Set();
      const sortedDates = Array.from(_dateToPhases.keys()).sort();
      const firstDate = sortedDates[0];
      const lastDate = sortedDates[sortedDates.length - 1];
      // Phase 0 (start ranking) only shown when first date is selected
      if (firstDate && _activeDates.has(firstDate)) {
        visiblePhases.add(0);
      }
      // End ranking only shown when last date is selected
      if (lastDate && _activeDates.has(lastDate)) {
        visiblePhases.add(maxPhase);
      }

      _activeDates.forEach(date => {
        const phases = _dateToPhases.get(date);
        if (phases) phases.forEach(p => visiblePhases.add(p));
      });

      cy.nodes().forEach(n => {
        const phase = n.data('phase');
        if (!visiblePhases.has(phase)) {
          n.style('display', 'none');
        }
      });
    }

    // Step 3: hide all edges — only team-selected edges are shown by
    // activateTrajectory (step 4) or _applyHighlight.
    cy.edges().style('display', 'none');
  });
  // ^^^ batch ends here — styles are now recalculated

  // Step 4: team trajectory — OUTSIDE batch so e.visible() is accurate
  if (hasTeam) {
    activateTrajectory(cy, _activeTeamIds);
  }

  // Step 5: layout management
  // Day filter active → compact phases. Returning to All (after compact) → restore.
  // Team-only or no filters → preserve current viewport, don't move nodes.
  if (!showAllDays || hasTeam) {
    relayoutVisible();
    _positionsCompacted = true;
  } else if (_positionsCompacted) {
    rerunLayout();
    _positionsCompacted = false;
  }
  // else: no filters or team-only → preserve current viewport, don't move nodes
}

// ------------------------------------------------------------------ //
// Team dropdown                                                        //
// ------------------------------------------------------------------ //

function _initTeamDropdown(cy, metadata) {
  const select = document.getElementById('team-select');

  const teams = (metadata.teams || []).slice().sort((a, b) => a.name.localeCompare(b.name));
  teams.forEach(team => {
    const option = document.createElement('option');
    option.value = team.id;
    option.textContent = team.name + (team.seed ? ` (#${team.seed})` : '');
    select.appendChild(option);
  });

  select.addEventListener('change', () => {
    _activeTeamIds = select.value ? [parseInt(select.value, 10)] : [];
    _clearHighlight(cy);
    _applyFilters(cy);
  });
}

// ------------------------------------------------------------------ //
// Zoom controls                                                        //
// ------------------------------------------------------------------ //

function _initZoomControls(cy) {
  document.getElementById('zoom-fit').addEventListener('click', () => fitToVisible(40));

  document.getElementById('zoom-in').addEventListener('click', () => {
    cy.zoom({ level: cy.zoom() * 1.25, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  });

  document.getElementById('zoom-out').addEventListener('click', () => {
    cy.zoom({ level: cy.zoom() / 1.25, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  });

  document.getElementById('relayout').addEventListener('click', () => {
    _activeTeamIds = [];
    _activeDates.clear();

    // Reset team dropdown
    const select = document.getElementById('team-select');
    if (select) select.value = '';

    // Reset day filter buttons
    const dayRow = document.getElementById('day-filter-row');
    if (dayRow) {
      dayRow.querySelectorAll('.day-filter').forEach(b => b.classList.remove('active'));
      const allBtn = dayRow.querySelector('[data-day-all]');
      if (allBtn) allBtn.classList.add('active');
    }

    _highlightedTeamIds = [];
    _clearHighlight(cy);
    clearTrajectory(cy);
    _applyFilters(cy);
  });
}

// ------------------------------------------------------------------ //
// Node click → team select sync                                        //
// ------------------------------------------------------------------ //

function _initNodeClickHandler(cy) {
  cy.on('tap', 'node', function(evt) {
    const node = evt.target;
    const type = node.data('type');

    // Skip invisible port nodes — clicks go to parent
    if (type === 'port') return;

    let clickedTeamIds = [];

    if (type === 'ranking') {
      const teams = node.data('teams') || [];
      if (teams.length === 0) return;
      clickedTeamIds = [teams[0].id];
    } else if (type === 'match') {
      const teams = node.data('teams') || [];
      if (teams.length === 0) return;
      clickedTeamIds = teams.map(t => t.id);
    }

    // Toggle: if same teams already highlighted, clear; otherwise apply
    const alreadyHighlighted =
      _highlightedTeamIds.length === clickedTeamIds.length &&
      clickedTeamIds.every(id => _highlightedTeamIds.includes(id));

    if (alreadyHighlighted) {
      _clearHighlight(cy);
      if (_activeTeamIds.length > 0) _applyFilters(cy);
    } else {
      _applyHighlight(cy, clickedTeamIds);
    }
  });

  // Click on canvas background → clear highlight only (not filters).
  // If a team trajectory is active, re-apply filters to restore trajectory edges.
  cy.on('tap', function(evt) {
    if (evt.target !== cy) return;
    _clearHighlight(cy);
    if (_activeTeamIds.length > 0) {
      _applyFilters(cy);
    }
  });
}

/**
 * Highlight the trajectory of given teams with dimming of all other elements.
 * Does NOT change _activeTeamIds or filter visibility — visual-only.
 */
function _applyHighlight(cy, teamIds) {
  _clearHighlight(cy);

  _highlightedTeamIds = teamIds;
  _highlightState.active = true;
  _highlightState.teamIds = new Set(teamIds);

  const teamIdSet = new Set(teamIds);

  // Find team edges, port nodes, parent match nodes (same as activateTrajectory)
  const teamEdges = cy.edges().filter(e => teamIdSet.has(e.data('teamId')));
  if (teamEdges.length === 0) {
    _highlightedTeamIds = [];
    _highlightState.active = false;
    _highlightState.teamIds = new Set();
    return;
  }

  const teamPortNodes = teamEdges.connectedNodes();
  const parentIds = new Set();
  teamPortNodes.filter(n => n.data('type') === 'port' && n.data('parentId'))
    .forEach(n => parentIds.add(n.data('parentId')));
  let teamParentNodes = cy.collection();
  parentIds.forEach(id => { teamParentNodes = teamParentNodes.union(cy.$id(id)); });

  const teamCollection = teamEdges.union(teamPortNodes).union(teamParentNodes);

  // Dim visible nodes not in the team's path
  cy.nodes().filter(n => n.visible()).difference(teamCollection).addClass('dimmed');

  // Show only team edges (all edges are hidden at baseline), then highlight them
  cy.edges().style('display', 'none');
  teamEdges.style('display', 'element');
  teamEdges.addClass('edge-highlight');

  // Win/loss coloring
  teamIds.forEach(teamId => {
    teamParentNodes.filter('[type="match"][status="finished"]').forEach(node => {
      const teams = node.data('teams') || [];
      const homeTeam = teams.find(t => t.role === 'home');
      const awayTeam = teams.find(t => t.role === 'away');
      if (homeTeam && awayTeam && teamIdSet.has(homeTeam.id) && teamIdSet.has(awayTeam.id)) return;
      const isHome = homeTeam && homeTeam.id === teamId;
      const isAway = awayTeam && awayTeam.id === teamId;
      if (!isHome && !isAway) return;
      const homeWon = node.data('homeWon');
      if (homeWon === null || homeWon === undefined) return;
      const teamWon = isHome ? homeWon : !homeWon;
      node.addClass(teamWon ? 'team-win' : 'team-loss');
    });
  });

  // Force HTML overlay re-render by nudging node data
  cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
    n.data('_hl', Date.now());
  });
}

/**
 * Clear all highlight state and restore normal appearance.
 */
function _clearHighlight(cy) {
  _highlightedTeamIds = [];
  _highlightState.active = false;
  _highlightState.teamIds = new Set();

  cy.elements().removeClass('dimmed team-win team-loss edge-highlight');
  // Edges are hidden at baseline — only shown when a team is active
  cy.edges().style('display', 'none');

  // Force HTML overlay re-render
  cy.nodes().filter(n => n.visible() && n.data('type') !== 'port').forEach(n => {
    n.data('_hl', 0);
  });
}
