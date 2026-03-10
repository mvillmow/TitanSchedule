// TitanSchedule — vanilla JS frontend
(function () {
  "use strict";

  // --- State ---
  let divisions = [];
  let tournamentData = null;
  let currentDivision = null; // slug
  let currentTeamId = null;   // null = all teams
  let currentDate = null;

  // --- DOM refs ---
  const divisionSelect = document.getElementById("division-select");
  const teamSearch = document.getElementById("team-search");
  const teamListbox = document.getElementById("team-listbox");
  const teamContainer = document.getElementById("team-search-container");
  const dayTabs = document.getElementById("day-tabs");
  const cards = document.getElementById("cards");
  const loading = document.getElementById("loading");
  const emptyState = document.getElementById("empty-state");
  const emptyMessage = document.getElementById("empty-message");

  let listboxIndex = -1;

  // --- Sanitization ---
  // All user-supplied strings are escaped via esc() before DOM insertion.
  // esc() uses textContent assignment which converts special chars to entities,
  // preventing XSS. Only static/controlled markup uses innerHTML.
  function esc(str) {
    const el = document.createElement("span");
    el.textContent = str;
    return el.innerHTML;
  }

  // --- Init ---
  async function init() {
    const hash = parseHash();
    await loadDivisions();
    if (hash.division) {
      divisionSelect.value = hash.division;
      currentTeamId = hash.teamId;
      currentDate = hash.date;
    }
    const slug = divisionSelect.value;
    if (slug) await loadDivision(slug);
    bindEvents();
  }

  // --- Data loading ---
  async function loadDivisions() {
    try {
      const res = await fetch("data/index.json");
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      divisions = Array.isArray(data) ? data : (data.divisions || []);
    } catch {
      divisions = [];
    }
    divisionSelect.textContent = "";
    if (divisions.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No divisions available";
      divisionSelect.appendChild(opt);
      return;
    }
    divisions.forEach((d) => {
      const opt = document.createElement("option");
      opt.value = d.slug;
      opt.textContent = d.name;
      divisionSelect.appendChild(opt);
    });
  }

  async function loadDivision(slug) {
    currentDivision = slug;
    showLoading();
    try {
      const res = await fetch(`data/${encodeURIComponent(slug)}/tournament.json`);
      if (!res.ok) throw new Error(res.statusText);
      tournamentData = await res.json();
    } catch {
      tournamentData = null;
      hideLoading();
      showEmpty("Could not load tournament data");
      return;
    }
    hideLoading();

    if (!currentDate || !tournamentData.dates.includes(currentDate)) {
      currentDate = tournamentData.dates[0] || null;
    }

    renderDayTabs(tournamentData.dates);
    populateTeamList();
    renderTeamCards();
    updateHash();
  }

  // --- Team combobox ---
  function populateTeamList() {
    if (!tournamentData) return;
    teamSearch.value = currentTeamId ? getTeamName(currentTeamId) : "";
  }

  function getTeamName(id) {
    if (!tournamentData) return "";
    const t = tournamentData.teams[id];
    return t ? t.name : "";
  }

  function buildTeamOptions(filter) {
    teamListbox.textContent = "";
    if (!tournamentData) return;

    const allOpt = document.createElement("li");
    allOpt.role = "option";
    allOpt.dataset.id = "";
    allOpt.className = "px-4 py-2 text-sm cursor-pointer hover:bg-indigo-50";
    allOpt.textContent = "All Teams";
    teamListbox.appendChild(allOpt);

    const lc = (filter || "").toLowerCase();
    const sorted = Object.entries(tournamentData.teams)
      .sort((a, b) => a[1].name.localeCompare(b[1].name));

    for (const [id, team] of sorted) {
      if (lc && !team.name.toLowerCase().includes(lc)) continue;
      const li = document.createElement("li");
      li.role = "option";
      li.dataset.id = id;
      li.className = "px-4 py-2 text-sm cursor-pointer hover:bg-indigo-50";
      li.textContent = team.name;
      teamListbox.appendChild(li);
    }
  }

  function openListbox() {
    buildTeamOptions(teamSearch.value);
    teamListbox.classList.remove("hidden");
    teamContainer.setAttribute("aria-expanded", "true");
    listboxIndex = -1;
  }

  function closeListbox() {
    teamListbox.classList.add("hidden");
    teamContainer.setAttribute("aria-expanded", "false");
    listboxIndex = -1;
  }

  function selectTeam(id) {
    currentTeamId = id || null;
    teamSearch.value = id ? getTeamName(id) : "";
    closeListbox();
    renderTeamCards();
    updateHash();
  }

  // --- Day tabs ---
  function renderDayTabs(dates) {
    dayTabs.textContent = "";
    if (!dates || dates.length === 0) return;

    dates.forEach((d) => {
      const btn = document.createElement("button");
      btn.role = "tab";
      btn.setAttribute("aria-selected", d === currentDate ? "true" : "false");
      btn.dataset.date = d;
      btn.className = tabClasses(d === currentDate);
      btn.textContent = formatDate(d);
      dayTabs.appendChild(btn);
    });
  }

  function tabClasses(active) {
    const base = "px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-colors";
    return active
      ? `${base} bg-indigo-600 text-white shadow`
      : `${base} bg-white text-gray-600 border border-gray-200 hover:bg-gray-50`;
  }

  // --- Card rendering ---
  function renderTeamCards() {
    cards.textContent = "";
    emptyState.classList.add("hidden");
    if (!tournamentData) return showEmpty("No data loaded");

    const teams = tournamentData.teams;
    const entries = Object.entries(teams)
      .filter(([id]) => !currentTeamId || id === currentTeamId)
      .sort((a, b) => a[1].name.localeCompare(b[1].name));

    if (entries.length === 0) {
      return showEmpty("No teams match your selection");
    }

    let anyCards = false;
    let delay = 0;
    for (const [, team] of entries) {
      const games = (team.games || []).filter((g) => g.date === currentDate);
      if (games.length === 0 && currentTeamId === null) continue;
      anyCards = true;
      cards.appendChild(renderCard(team, games, delay));
      delay += 50;
    }

    if (!anyCards) {
      showEmpty("No games scheduled for this date");
    }
  }

  function renderCard(team, games, delay) {
    const card = document.createElement("article");
    card.className = "card-enter bg-white rounded-xl shadow-md overflow-hidden border border-gray-100 hover:shadow-lg transition-shadow";
    card.style.animationDelay = `${delay}ms`;

    // Header
    const header = document.createElement("div");
    header.className = "px-4 py-3 bg-gradient-to-r from-indigo-50 to-purple-50 border-b border-gray-100";

    const headerRow = document.createElement("div");
    headerRow.className = "flex items-center justify-between";

    const leftDiv = document.createElement("div");
    const nameEl = document.createElement("h2");
    nameEl.className = "font-semibold text-gray-900 text-sm";
    nameEl.textContent = team.name;
    leftDiv.appendChild(nameEl);

    const subEl = document.createElement("p");
    subEl.className = "text-xs text-gray-500";
    subEl.textContent = (team.club || "") + (team.seed ? ` · Seed ${team.seed}` : "");
    leftDiv.appendChild(subEl);

    const rightDiv = document.createElement("div");
    rightDiv.className = "text-right";
    const recordEl = document.createElement("span");
    recordEl.className = "text-sm font-bold text-gray-700";
    recordEl.textContent = team.record || "";
    rightDiv.appendChild(recordEl);
    if (team.rank) {
      const rankEl = document.createElement("p");
      rankEl.className = "text-xs text-gray-400";
      rankEl.textContent = `Rank #${team.rank}`;
      rightDiv.appendChild(rankEl);
    }

    headerRow.appendChild(leftDiv);
    headerRow.appendChild(rightDiv);
    header.appendChild(headerRow);
    card.appendChild(header);

    // Games
    if (games.length === 0) {
      const noGames = document.createElement("div");
      noGames.className = "px-4 py-6 text-center text-sm text-gray-400";
      noGames.textContent = "No games on this date";
      card.appendChild(noGames);
    } else {
      const list = document.createElement("div");
      list.className = "divide-y divide-gray-50";
      games.forEach((g, i) => list.appendChild(renderGameRow(g, i)));
      card.appendChild(list);
    }

    return card;
  }

  function renderGameRow(game, index) {
    const row = document.createElement("div");
    const statusCls = getStatusClasses(game);
    const borderCls = getStatusBorder(game);
    const altBg = index % 2 === 1 ? " even-row" : "";
    row.className = `px-4 py-2.5 flex items-center gap-3 text-sm ${borderCls}${statusCls ? " " + statusCls : ""}${altBg}`;

    // Time + court column
    const timeCol = document.createElement("div");
    timeCol.className = "w-14 shrink-0";
    const timeEl = document.createElement("p");
    timeEl.className = "font-medium text-gray-900";
    timeEl.textContent = formatTime(game.time);
    timeCol.appendChild(timeEl);
    const courtEl = document.createElement("p");
    courtEl.className = "text-xs text-gray-400";
    courtEl.textContent = game.court || "";
    timeCol.appendChild(courtEl);

    // Opponent column
    const oppCol = document.createElement("div");
    oppCol.className = "flex-1 min-w-0";
    const oppRow = document.createElement("div");
    oppRow.className = "flex items-center gap-1.5";

    const roleLabel = game.role === "home" ? "H" : game.role === "away" ? "A" : game.role === "work" ? "W" : "";
    if (roleLabel) {
      const badge = document.createElement("span");
      badge.className = "inline-block rounded-full px-2 py-0.5 text-[10px] text-center bg-gray-200 text-gray-600 font-medium";
      badge.textContent = roleLabel;
      oppRow.appendChild(badge);
    }

    const opponentName = game.opponent || game.opponent_text || "TBD";
    const oppName = document.createElement("span");
    oppName.className = game.opponent ? "truncate text-gray-800" : "truncate text-gray-400 italic";
    oppName.textContent = opponentName;
    oppRow.appendChild(oppName);
    oppCol.appendChild(oppRow);

    if (game.round) {
      const roundEl = document.createElement("p");
      roundEl.className = "text-xs text-gray-400 mt-0.5";
      roundEl.textContent = game.round + (game.group ? ` · ${game.group}` : "");
      oppCol.appendChild(roundEl);
    }

    // Score/status column
    const scoreCol = document.createElement("div");
    scoreCol.className = "shrink-0 text-right text-xs font-medium";

    if ((game.status === "final" || game.status === "in_progress") && game.scores && game.scores.length > 0) {
      const scoreEl = document.createElement("p");
      const prefix = game.won === true ? "W " : game.won === false ? "L " : "";
      const sets = game.scores.map(([a, b]) => `${a}-${b}`).join(", ");
      scoreEl.textContent = prefix + sets;
      if (game.won === true) scoreEl.className = "text-green-600";
      else if (game.won === false) scoreEl.className = "text-red-500";
      scoreCol.appendChild(scoreEl);
    } else {
      const statusEl = document.createElement("p");
      statusEl.className = "text-gray-400";
      statusEl.textContent = statusLabel(game.status);
      scoreCol.appendChild(statusEl);
    }

    row.appendChild(timeCol);
    row.appendChild(oppCol);
    row.appendChild(scoreCol);

    return row;
  }

  // --- Formatting helpers ---
  function formatTime(t) {
    if (!t) return "";
    const [h, m] = t.split(":");
    const hour = parseInt(h, 10);
    if (hour === 0) return `12:${m}a`;
    if (hour < 12) return `${hour}:${m}a`;
    if (hour === 12) return `12:${m}p`;
    return `${hour - 12}:${m}p`;
  }

  function formatDate(dateStr) {
    const d = new Date(dateStr + "T12:00:00");
    const days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
    const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return `${days[d.getDay()]} ${months[d.getMonth()]} ${d.getDate()}`;
  }

  function getStatusClasses(game) {
    switch (game.status) {
      case "final":
        return game.won ? "bg-green-50/60" : "bg-red-50/40";
      case "in_progress":
        return "bg-yellow-50/60";
      case "conditional":
        return "bg-purple-50/40";
      default:
        return "";
    }
  }

  function getStatusBorder(game) {
    switch (game.status) {
      case "final":
        return game.won ? "border-l-4 border-green-500" : "border-l-4 border-red-400";
      case "in_progress":
        return "border-l-4 border-yellow-400";
      case "conditional":
        return "border-l-4 border-dashed border-purple-500";
      case "scheduled":
        return "border-l-4 border-gray-300";
      default:
        return "";
    }
  }

  function statusLabel(status) {
    switch (status) {
      case "scheduled": return "Upcoming";
      case "conditional": return "TBD";
      case "in_progress": return "Live";
      case "final": return "Final";
      default: return status || "";
    }
  }

  // --- URL hash ---
  // Format: #division-slug/team-id/date
  // "all" sentinel used when no specific team is selected
  function updateHash() {
    const parts = [currentDivision || ""];
    parts.push(currentTeamId || "all");
    if (currentDate) parts.push(currentDate);
    location.hash = parts.join("/");
  }

  function parseHash() {
    const h = location.hash.replace(/^#/, "");
    if (!h) return {};
    const parts = h.split("/");
    const teamId = parts[1] && parts[1] !== "all" ? parts[1] : null;
    return {
      division: parts[0] || null,
      teamId: teamId,
      date: parts[2] || null,
    };
  }

  // --- Loading / empty ---
  function showLoading() {
    loading.classList.remove("hidden");
    cards.textContent = "";
    emptyState.classList.add("hidden");
  }

  function hideLoading() {
    loading.classList.add("hidden");
  }

  function showEmpty(message) {
    emptyState.classList.remove("hidden");
    emptyMessage.textContent = message;
  }

  // --- Events ---
  function bindEvents() {
    divisionSelect.addEventListener("change", () => {
      currentTeamId = null;
      currentDate = null;
      loadDivision(divisionSelect.value);
    });

    dayTabs.addEventListener("click", (e) => {
      const btn = e.target.closest("[data-date]");
      if (!btn) return;
      currentDate = btn.dataset.date;
      renderDayTabs(tournamentData.dates);
      renderTeamCards();
      updateHash();
    });

    teamSearch.addEventListener("focus", openListbox);
    teamSearch.addEventListener("input", () => {
      buildTeamOptions(teamSearch.value);
      teamListbox.classList.remove("hidden");
      teamContainer.setAttribute("aria-expanded", "true");
    });

    teamSearch.addEventListener("keydown", (e) => {
      const items = teamListbox.querySelectorAll("li");
      if (e.key === "ArrowDown") {
        e.preventDefault();
        listboxIndex = Math.min(listboxIndex + 1, items.length - 1);
        highlightItem(items);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        listboxIndex = Math.max(listboxIndex - 1, 0);
        highlightItem(items);
      } else if (e.key === "Enter") {
        e.preventDefault();
        if (listboxIndex >= 0 && items[listboxIndex]) {
          selectTeam(items[listboxIndex].dataset.id);
        }
      } else if (e.key === "Escape") {
        closeListbox();
        teamSearch.blur();
      }
    });

    teamListbox.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (li) selectTeam(li.dataset.id);
    });

    document.addEventListener("click", (e) => {
      if (!teamContainer.contains(e.target)) closeListbox();
    });

    window.addEventListener("hashchange", () => {
      const hash = parseHash();
      if (hash.division && hash.division !== currentDivision) {
        divisionSelect.value = hash.division;
        currentTeamId = hash.teamId;
        currentDate = hash.date;
        loadDivision(hash.division);
      } else {
        if (hash.teamId !== currentTeamId || hash.date !== currentDate) {
          currentTeamId = hash.teamId;
          currentDate = hash.date || currentDate;
          populateTeamList();
          if (tournamentData) {
            renderDayTabs(tournamentData.dates);
            renderTeamCards();
          }
        }
      }
    });
  }

  function highlightItem(items) {
    items.forEach((li, i) => {
      li.classList.toggle("bg-indigo-100", i === listboxIndex);
    });
    if (items[listboxIndex]) {
      items[listboxIndex].scrollIntoView({ block: "nearest" });
    }
  }

  // --- Start ---
  init();
})();
