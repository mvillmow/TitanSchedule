/* app.js — Application entry point: fetch JSON, wire up all modules */

'use strict';

async function showLandingPage(container) {
  document.getElementById('cy-wrap').style.display = 'none';
  document.getElementById('bottom-toolbar').style.display = 'none';
  document.getElementById('division-name').textContent = '';
  document.getElementById('event-name').textContent = 'TitanSchedule';
  container.classList.remove('hidden');

  try {
    const response = await fetch('data/index.json');
    if (!response.ok) throw new Error('No index');
    const index = await response.json();
    const divisions = index.divisions || [];

    if (divisions.length === 0) throw new Error('empty');

    // Build DOM safely — no innerHTML with user data
    const wrapper = document.createElement('div');
    wrapper.className = 'max-w-4xl mx-auto py-8 px-4';

    const h1 = document.createElement('h1');
    h1.className = 'text-2xl font-bold text-gray-900 mb-6';
    h1.textContent = 'TitanSchedule \u2014 Tournaments';
    wrapper.appendChild(h1);

    const grid = document.createElement('div');
    grid.className = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4';

    divisions.forEach(function(div) {
      var card = document.createElement('a');
      card.href = '?div=' + encodeURIComponent(div.slug);
      card.className = 'division-card';

      var h2 = document.createElement('h2');
      h2.className = 'font-semibold text-gray-900 text-sm';
      h2.textContent = div.event_name;
      card.appendChild(h2);

      var name = document.createElement('p');
      name.className = 'text-blue-600 text-sm mt-1';
      name.textContent = div.division_name;
      card.appendChild(name);

      var time = document.createElement('p');
      time.className = 'text-gray-400 text-xs mt-2';
      time.textContent = 'Updated: ' + (div.scraped_at ? new Date(div.scraped_at).toLocaleString() : 'Unknown');
      card.appendChild(time);

      grid.appendChild(card);
    });

    wrapper.appendChild(grid);
    container.appendChild(wrapper);

  } catch (err) {
    var msg = document.createElement('div');
    msg.className = 'text-center py-20 text-gray-500';
    msg.textContent = 'No tournament data found. Run ./scripts/scrape.sh <URL> to scrape a division.';
    container.appendChild(msg);
  }
}

(async function () {
  const loadingEl   = document.getElementById('loading');
  const errorBanner = document.getElementById('error-banner');
  const errorMsg    = document.getElementById('error-msg');
  const landingEl   = document.getElementById('landing');

  function showError(msg) {
    loadingEl.style.display = 'none';
    errorBanner.classList.remove('hidden');
    errorMsg.textContent = msg;
  }

  const params = new URLSearchParams(window.location.search);
  const divSlug = params.get('div');

  if (!divSlug) {
    loadingEl.style.display = 'none';
    await showLandingPage(landingEl);
    return;
  }

  try {
    // 1. Fetch tournament data
    const response = await fetch('data/' + encodeURIComponent(divSlug) + '/tournament.json');
    if (!response.ok) throw new Error('Division "' + divSlug + '" not found (HTTP ' + response.status + ')');
    const jsonData = await response.json();
    const metadata = jsonData.metadata || {};

    // 2. Add "Back to All Divisions" link in header
    const backLink = document.createElement('a');
    backLink.href = './';
    backLink.textContent = '\u2190 All Divisions';
    backLink.className = 'text-xs text-blue-600 hover:underline';
    document.querySelector('header > div').prepend(backLink);

    // 3. Populate header
    document.getElementById('event-name').textContent    = metadata.event_name || 'TitanSchedule';
    document.getElementById('division-name').textContent = metadata.division_name || '';
    if (metadata.scraped_at) {
      document.getElementById('scraped-at').textContent =
        'Updated: ' + new Date(metadata.scraped_at).toLocaleString();
    }
    if (metadata.aes_url) {
      const aesLink = document.getElementById('aes-link');
      aesLink.href = metadata.aes_url;
      aesLink.classList.remove('hidden');
    }

    // 4. #cy fills its parent via CSS (width/height: 100%) — no explicit sizing needed

    // 5. Initialize graph
    const cytoscapeInstance = initGraph(jsonData);

    // Hide all edges at baseline — only shown when a team is selected
    cytoscapeInstance.edges().style('display', 'none');

    // 6. Initialize tooltips
    initTooltips(cytoscapeInstance);

    // 7. Initialize controls
    initControls(cytoscapeInstance, metadata);

    // 8. Initialize export
    initExport(cytoscapeInstance, metadata.division_name);

    // 9. Hide loading overlay
    loadingEl.style.display = 'none';

    // 10. Fit view to initial content
    fitToVisible(40);

  } catch (err) {
    console.error('Failed to load tournament data:', err);
    showError(err.message || 'Unknown error. Check browser console for details.');
  }
})();
