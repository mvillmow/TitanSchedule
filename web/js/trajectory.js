/* trajectory.js — Team path highlighting via team_flow edges */

'use strict';

/**
 * Show only the trajectories of given teams through the tournament.
 * Hides all visible elements not on any team's path. Colors wins/losses on match nodes.
 *
 * @param {Object} cy - Cytoscape instance
 * @param {Array<number>} teamIds - Array of team IDs to highlight
 */
function activateTrajectory(cy, teamIds, visiblePhases) {
  // Do NOT call clearTrajectory here — _applyFilters already reset visibility.
  if (!teamIds || teamIds.length === 0) return;

  const teamIdSet = new Set(teamIds);

  // All edges belonging to any of the selected teams
  const teamEdges = cy.edges().filter(e => teamIdSet.has(e.data('teamId')));
  if (teamEdges.length === 0) return;

  // All port/ranking nodes connected by those edges
  const teamPortNodes = teamEdges.connectedNodes();

  // For port nodes, also include their parent match nodes
  const parentIds = new Set();
  teamPortNodes.filter(n => n.data('type') === 'port' && n.data('parentId'))
    .forEach(n => parentIds.add(n.data('parentId')));
  let teamParentNodes = cy.collection();
  parentIds.forEach(id => { teamParentNodes = teamParentNodes.union(cy.$id(id)); });

  const teamCollection = teamEdges.union(teamPortNodes).union(teamParentNodes);

  // Re-show team-path nodes, but only if their phase is allowed by the day filter.
  // When visiblePhases is null, all phases are visible (no day filter active).
  if (visiblePhases) {
    teamCollection.nodes().forEach(n => {
      if (visiblePhases.has(n.data('phase'))) {
        n.style('display', 'element');
      }
    });
  } else {
    teamCollection.nodes().style('display', 'element');
  }

  // Hide CURRENTLY VISIBLE nodes not in any team's path.
  // Preserves day filter state set by _applyFilters.
  cy.nodes().filter(n => n.visible()).difference(teamCollection).style('display', 'none');

  // Show only the team's edges (all edges start hidden per _applyFilters step 3)
  teamEdges.style('display', 'element');

  // Highlight team edges
  teamEdges.addClass('edge-highlight');

  // Win/loss coloring per team
  teamIds.forEach(teamId => {
    teamParentNodes.filter('[type="match"][status="finished"]').forEach(node => {
      const teams = node.data('teams') || [];
      const homeTeam = teams.find(t => t.role === 'home');
      const awayTeam = teams.find(t => t.role === 'away');

      // Skip if both home and away are selected for this match (ambiguous win/loss)
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
}

/**
 * Clear all trajectory highlighting, restoring normal appearance.
 * @param {Object} cy - Cytoscape instance
 */
function clearTrajectory(cy) {
  cy.elements().removeClass('team-win team-loss edge-highlight');
  cy.nodes().style('display', 'element');
  cy.edges().style('display', 'none');
}
