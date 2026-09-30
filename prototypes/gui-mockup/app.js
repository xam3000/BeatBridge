(function () {
  "use strict";

  const data = window.BeatBridgeMockData;
  const state = {
    activeEdgeId: data.edges[1].id,
    method: "model",
    tab: "analysis",
    playing: false,
    loop: true,
    playheadSeconds: 0,
    timer: null,
    search: ""
  };

  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => [...document.querySelectorAll(selector)];
  const getTrack = (id) => data.tracks.find((track) => track.id === id);
  const getSection = (id) => data.sections.find((section) => section.id === id);
  const getEdge = () => data.edges.find((edge) => edge.id === state.activeEdgeId);
  const trackForSection = (sectionId) => getTrack(getSection(sectionId).trackId);

  function escapeHtml(value) {
    return String(value).replace(/[&<>'"]/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", '"': "&quot;" })[char]);
  }

  function colorFor(track) {
    return ({ cyan: "#29d4f0", coral: "#ff5f88", violet: "#9a78ff", amber: "#f7bd55", blue: "#4aa8ff", green: "#42d890" })[track.color] || "#89a0ad";
  }

  function renderLibrary() {
    const edge = getEdge();
    const aTrack = trackForSection(edge.fromSectionId);
    const bTrack = trackForSection(edge.toSectionId);
    const term = state.search.trim().toLowerCase();
    const tracks = data.tracks.filter((track) => `${track.title} ${track.artist}`.toLowerCase().includes(term));

    $("#trackList").innerHTML = tracks.map((track) => {
      const uses = data.sections.filter((section) => section.trackId === track.id).length;
      const pairClass = track.id === aTrack.id ? "is-pair-a" : track.id === bTrack.id ? "is-pair-b" : "";
      const role = track.id === aTrack.id ? "A · " : track.id === bTrack.id ? "B · " : "";
      const statusClass = track.status === "Warnung" ? "warning" : "";
      return `<article class="track-item ${pairClass}" style="--track-color:${colorFor(track)}">
        <div class="track-art" aria-hidden="true">${escapeHtml(track.title.slice(0, 2))}</div>
        <div class="track-copy">
          <strong>${role}${escapeHtml(track.title)}</strong>
          <small>${escapeHtml(track.artist)} · ${track.bpm.toFixed(1)} BPM · ${escapeHtml(track.key)}</small>
          <span class="track-state ${statusClass}"><i></i>${escapeHtml(track.status)} · ${uses}× verwendet</span>
        </div>
        <button class="track-add" type="button" data-add-track="${track.id}" aria-label="${escapeHtml(track.title)} zur Sequenz hinzufügen">＋</button>
      </article>`;
    }).join("");
  }

  function renderSequence() {
    const edge = getEdge();
    const cells = [];
    data.sections.forEach((section, index) => {
      const track = getTrack(section.trackId);
      const activeClass = section.id === edge.fromSectionId ? "active-a" : section.id === edge.toSectionId ? "active-b" : "";
      cells.push(`<article class="sequence-card ${activeClass}" style="--section-color:${colorFor(track)}" data-section="${section.id}">
        <span class="sequence-index">${String(index + 1).padStart(2, "0")}</span>
        <strong>${escapeHtml(track.title)}</strong>
        <small>${escapeHtml(section.label)} · ${escapeHtml(section.range)}</small>
        <footer><span class="track-state"><i></i>${escapeHtml(track.status)}</span><span><button class="section-move" type="button" data-move="-1" data-section-id="${section.id}" aria-label="Nach links">←</button> <button class="section-move" type="button" data-move="1" data-section-id="${section.id}" aria-label="Nach rechts">→</button></span></footer>
      </article>`);
      if (index < data.sections.length - 1) {
        const next = data.sections[index + 1];
        const transition = data.edges.find((candidate) => candidate.fromSectionId === section.id && candidate.toSectionId === next.id);
        const status = transition ? transition.status : "stale";
        const label = ({ ready: "bereit", editing: "bearbeiten", open: "offen", stale: "veraltet" })[status];
        cells.push(`<button class="sequence-edge ${status} ${transition && transition.id === state.activeEdgeId ? "is-active" : ""}" type="button" ${transition ? `data-edge-id="${transition.id}"` : "disabled"} aria-label="Übergang ${index + 1}: ${label}"><span>${label}</span></button>`);
      }
    });
    const columns = data.sections.map((_, index) => index === data.sections.length - 1 ? "minmax(130px,1fr)" : "minmax(130px,1fr) 66px").join(" ");
    $("#sequenceStrip").style.gridTemplateColumns = columns;
    $("#sequenceStrip").innerHTML = cells.join("");
    $("#sequenceTitle").textContent = `${data.sections.length} Abschnitte · ${Math.max(0, data.sections.length - 1)} Paarübergänge`;
  }

  function waveformPath(seed, intensity) {
    const points = [];
    const mid = 60;
    for (let x = 0; x <= 1000; x += 6) {
      const envelope = 17 + 26 * (0.5 + 0.5 * Math.sin((x + seed * 19) / 127));
      const noise = Math.abs(Math.sin((x + seed) * 0.13) * Math.cos((x + seed * 7) * 0.047));
      points.push([x, mid - (envelope * (0.35 + noise) * intensity)]);
    }
    for (let index = points.length - 1; index >= 0; index -= 1) {
      const [x, y] = points[index];
      points.push([x, mid + (mid - y)]);
    }
    return `M${points.map((point) => point.map((number) => number.toFixed(1)).join(" ")).join("L")}Z`;
  }

  function linePath(seed, invert) {
    const points = [];
    for (let x = 0; x <= 900; x += 15) {
      const trend = invert ? 105 - x * 0.055 : 50 + x * 0.05;
      const movement = Math.sin((x + seed * 8) / 45) * 10 + Math.sin((x + seed) / 17) * 4;
      points.push(`${x},${Math.max(18, Math.min(125, trend + movement)).toFixed(1)}`);
    }
    return `M${points.join(" L")}`;
  }

  function renderVocalBars(groupSelector, seed, yBase, direction) {
    const bars = [];
    for (let x = 12; x < 890; x += 18) {
      const activity = Math.max(0, Math.sin((x + seed * 13) / 88) + Math.sin((x + seed) / 31) * .35);
      const height = 2 + activity * 17;
      const y = direction < 0 ? yBase - height : yBase;
      bars.push(`<rect x="${x}" y="${y.toFixed(1)}" width="8" height="${height.toFixed(1)}"></rect>`);
    }
    $(groupSelector).innerHTML = bars.join("");
  }

  function renderPair() {
    const edge = getEdge();
    const sectionA = getSection(edge.fromSectionId);
    const sectionB = getSection(edge.toSectionId);
    const trackA = getTrack(sectionA.trackId);
    const trackB = getTrack(sectionB.trackId);
    const statusLabel = ({ ready: "Bereit", editing: "In Bearbeitung", open: "Offen", stale: "Veraltet" })[edge.status];

    $("#pairTitle").textContent = `${trackA.title} → ${trackB.title}`;
    $("#pairStatus").textContent = statusLabel;
    $("#pairStatus").className = `status-chip ${edge.status}`;
    $("#laneATitle").textContent = trackA.title;
    $("#laneBTitle").textContent = trackB.title;
    $("#laneAMeta").textContent = `${trackA.bpm.toFixed(1)} BPM · ${trackA.key}`;
    $("#laneBMeta").textContent = `${trackB.bpm.toFixed(1)} BPM · ${trackB.key}`;
    $("#legendA").textContent = `A · ${trackA.title}`;
    $("#legendB").textContent = `B · ${trackB.title}`;
    $("#harmonyA").textContent = trackA.key;
    $("#harmonyB").textContent = trackB.key;
    $("#sourceCue").value = edge.cueA;
    $("#targetCue").value = edge.cueB;
    $("#cueA").textContent = `A OUT · ${edge.cueA.split(" · ")[0]}`;
    $("#cueB").textContent = `B IN · ${edge.cueB.split(" · ")[0]}`;
    $("#lengthSelect").value = edge.config.bars;
    $("#tempoInput").value = edge.config.targetBpm;
    $("#vocalCheck").checked = edge.config.avoidVocals;
    $("#stretchRange").value = edge.config.maxStretch;
    $("#stretchValue").textContent = `${edge.config.maxStretch} %`;
    $("#energyRange").value = edge.config.energyPriority;
    $("#energyValue").textContent = `${edge.config.energyPriority} %`;
    $("#transitionLabel").textContent = `Übergang · ${edge.config.bars} Takte`;
    $("#toolbarTempo").textContent = `${edge.config.targetBpm.toFixed(1).replace(".", ",")} BPM`;

    $$("#rendererControl button").forEach((button) => {
      const active = button.dataset.renderer === edge.config.renderer;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    });

    $("#waveformA").setAttribute("d", waveformPath(trackA.seed, 1));
    $("#waveformB").setAttribute("d", waveformPath(trackB.seed, .95));
    $("#energyA").setAttribute("d", linePath(trackA.seed, false));
    $("#energyB").setAttribute("d", linePath(trackB.seed, true));
    renderVocalBars("#vocalBarsA", trackA.seed, 154, -1);
    renderVocalBars("#vocalBarsB", trackB.seed, 158, 1);
    renderScores();
    renderVariants();
    renderDetails();
    updateSelectionSummary();
  }

  function renderScores() {
    const edge = getEdge();
    const scores = data.scoreProfiles[state.method].map((entry, index) => ({ ...entry, value: Math.max(40, Math.min(99, entry.value + ((edge.id.length + index * 3) % 7) - 3)) }));
    const total = Math.round(scores.reduce((sum, entry) => sum + entry.value, 0) / scores.length);
    $("#scoreType").textContent = state.method === "model" ? "MODELLSCORE" : "TECHNISCHE MESSUNG";
    $("#totalScore").textContent = total;
    $("#scoreBars").innerHTML = scores.map((entry) => `<div class="score-row"><span>${escapeHtml(entry.label)}</span><div class="score-track"><div class="score-fill" style="width:${entry.value}%"></div></div><output>${entry.value}</output></div>`).join("");
  }

  function renderVariants() {
    const edge = getEdge();
    $("#alternativeCount").textContent = edge.variants.length;
    $("#variantGrid").innerHTML = edge.variants.map((variant) => `<article class="variant-card ${variant.id === edge.selectedVariantId ? "is-selected" : ""}">
      <div class="variant-head"><span class="variant-rank">${String(variant.rank).padStart(2, "0")}</span><span class="variant-score">Score ${variant.score}</span></div>
      <div class="mini-wave" aria-hidden="true"></div>
      <dl><div><dt>Methode</dt><dd>${escapeHtml(variant.method)}</dd></div><div><dt>Länge</dt><dd>${variant.bars} Takte</dd></div><div><dt>Zieltempo</dt><dd>${variant.bpm.toFixed(1).replace(".", ",")} BPM</dd></div><div><dt>Status</dt><dd>Gerendert</dd></div></dl>
      <div class="variant-actions"><button class="variant-action" type="button" data-audition="${variant.id}">▶ Anhören</button><button class="variant-action primary" type="button" data-select-variant="${variant.id}">Auswählen</button></div>
    </article>`).join("");
  }

  function renderDetails() {
    const edge = getEdge();
    const rows = [
      ["Kanten-ID", edge.id], ["Candidate-ID", edge.candidateId], ["Quelle", edge.fromSectionId], ["Ziel", edge.toSectionId],
      ["Candidate-Protokoll", "mock-candidate-v2"], ["Rendering-Protokoll", "mock-render-v6"], ["Rankingmethode", state.method === "model" ? "learned_cue_ranker_v1 (Mock)" : "feature_baseline_v3 (Mock)"],
      ["Datenquelle", "mock-data.js · keine Manifestbindung"], ["Fehler / Backfill", "Keine gemockten Fehler für diese Kante"]
    ];
    $("#detailsGrid").innerHTML = rows.map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
  }

  function updateSelectionSummary() {
    const edge = getEdge();
    const selected = edge.variants.find((variant) => variant.id === edge.selectedVariantId) || edge.variants[0];
    $("#selectionSummary").innerHTML = `<strong>Variante ${String(selected.rank).padStart(2, "0")}</strong><span>${escapeHtml(selected.method)} · Score ${selected.score}</span>`;
  }

  function selectEdge(edgeId) {
    if (!data.edges.some((edge) => edge.id === edgeId)) return;
    state.activeEdgeId = edgeId;
    state.playheadSeconds = 0;
    stopPlayback();
    renderAll();
    showToast("Paarübergang im Editor geöffnet.");
  }

  function showTab(tab) {
    state.tab = tab;
    $$(".tab-button").forEach((button) => {
      const active = button.dataset.tab === tab;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-selected", String(active));
    });
    $("#analysisTab").hidden = tab !== "analysis";
    $("#alternativesTab").hidden = tab !== "alternatives";
    $("#detailsTab").hidden = tab !== "details";
  }

  function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const rest = (seconds % 60).toFixed(1).padStart(4, "0");
    return `${String(minutes).padStart(2, "0")}:${rest}`;
  }

  function updatePlayhead() {
    const percent = Math.max(0, Math.min(100, state.playheadSeconds / 20 * 100));
    const timelineWidth = $("#timelineStage").clientWidth - 174;
    $("#playhead").style.left = `${174 + timelineWidth * percent / 100}px`;
    $("#chartPlayhead").setAttribute("x1", String(900 * percent / 100));
    $("#chartPlayhead").setAttribute("x2", String(900 * percent / 100));
    $("#timeDisplay").textContent = `${formatTime(state.playheadSeconds)} / 00:20.0`;
  }

  function startPlayback() {
    if (state.playing) return;
    state.playing = true;
    $("#playPause").textContent = "Ⅱ";
    $("#playPause").setAttribute("aria-label", "Wiedergabe pausieren");
    state.timer = window.setInterval(() => {
      state.playheadSeconds += .1;
      if (state.playheadSeconds >= 20) state.playheadSeconds = state.loop ? 0 : 20;
      if (state.playheadSeconds >= 20 && !state.loop) stopPlayback();
      updatePlayhead();
    }, 100);
  }

  function stopPlayback() {
    state.playing = false;
    window.clearInterval(state.timer);
    state.timer = null;
    $("#playPause").textContent = "▶";
    $("#playPause").setAttribute("aria-label", "Wiedergabe starten");
  }

  function togglePlayback() { state.playing ? stopPlayback() : startPlayback(); }

  function markActiveEdgeEditing(message) {
    const edge = getEdge();
    if (edge.status === "ready") edge.status = "editing";
    renderSequence();
    $("#pairStatus").textContent = "In Bearbeitung";
    $("#pairStatus").className = "status-chip editing";
    showToast(message);
  }

  function acceptTransition() {
    const edge = getEdge();
    edge.status = "ready";
    renderAll();
    showToast("Übergang wurde an dieser Sequenzkante übernommen.");
  }

  function exportPreflight() {
    const unresolved = data.edges.filter((edge) => edge.status !== "ready");
    if (unresolved.length) {
      showToast(`Export blockiert: ${unresolved.length} von ${data.edges.length} Paarübergängen sind noch offen oder in Bearbeitung.`);
      return;
    }
    showToast("Export-Preflight bestanden. Im Prototyp wird keine Audiodatei erzeugt.");
  }

  function showToast(message) {
    const toast = $("#toast");
    toast.textContent = message;
    toast.hidden = false;
    window.clearTimeout(showToast.timer);
    showToast.timer = window.setTimeout(() => { toast.hidden = true; }, 3500);
  }

  function addTrackToSequence(trackId) {
    const track = getTrack(trackId);
    const suffix = Date.now().toString(36).slice(-5);
    const section = { id: `section-${track.id}-${suffix}`, trackId: track.id, label: "Neuer Abschnitt", range: "00:32–01:08" };
    const previous = data.sections[data.sections.length - 1];
    data.sections.push(section);
    data.edges.push({
      id: `edge-${previous.id}-${section.id}`, fromSectionId: previous.id, toSectionId: section.id, status: "open",
      config: { bars: 4, targetBpm: Number(((trackForSection(previous.id).bpm + track.bpm) / 2).toFixed(1)), renderer: "Equal Power", maxStretch: 8, energyPriority: 75, avoidVocals: true },
      cueA: "Takt 80 · 02:02.0", cueB: "Takt 33 · 00:49.0", candidateId: `mock-candidate-${suffix}`,
      variants: [
        { id: `v-${suffix}-01`, rank: 1, score: 83, method: "Equal Power", bars: 4, bpm: track.bpm, status: "rendered" },
        { id: `v-${suffix}-02`, rank: 2, score: 78, method: "ML Control", bars: 4, bpm: track.bpm, status: "rendered" },
        { id: `v-${suffix}-03`, rank: 3, score: 71, method: "Equal Power", bars: 2, bpm: track.bpm, status: "rendered" }
      ], selectedVariantId: `v-${suffix}-01`
    });
    state.activeEdgeId = data.edges[data.edges.length - 1].id;
    renderAll();
    showToast(`${track.title} wurde als neuer Abschnitt hinzugefügt.`);
  }

  function moveSection(sectionId, direction) {
    const index = data.sections.findIndex((section) => section.id === sectionId);
    const targetIndex = index + direction;
    if (index < 0 || targetIndex < 0 || targetIndex >= data.sections.length) return;
    [data.sections[index], data.sections[targetIndex]] = [data.sections[targetIndex], data.sections[index]];
    renderSequence();
    showToast("Reihenfolge geändert. Nicht passende Kanten werden als veraltet dargestellt.");
  }

  function renderAll() {
    renderLibrary();
    renderSequence();
    renderPair();
    showTab(state.tab);
    updatePlayhead();
  }

  document.addEventListener("click", (event) => {
    const edgeButton = event.target.closest("[data-edge-id]");
    if (edgeButton) selectEdge(edgeButton.dataset.edgeId);

    const tabButton = event.target.closest("[data-tab]");
    if (tabButton) showTab(tabButton.dataset.tab);

    const methodButton = event.target.closest("[data-method]");
    if (methodButton) {
      state.method = methodButton.dataset.method;
      $$("[data-method]").forEach((button) => { const active = button.dataset.method === state.method; button.classList.toggle("is-active", active); button.setAttribute("aria-pressed", String(active)); });
      renderScores(); renderDetails();
    }

    const rendererButton = event.target.closest("[data-renderer]");
    if (rendererButton) {
      getEdge().config.renderer = rendererButton.dataset.renderer;
      $$("[data-renderer]").forEach((button) => { const active = button === rendererButton; button.classList.toggle("is-active", active); button.setAttribute("aria-pressed", String(active)); });
      markActiveEdgeEditing("Methode für diesen Paarübergang geändert.");
    }

    const addButton = event.target.closest("[data-add-track]");
    if (addButton) addTrackToSequence(addButton.dataset.addTrack);

    const moveButton = event.target.closest("[data-move]");
    if (moveButton) moveSection(moveButton.dataset.sectionId, Number(moveButton.dataset.move));

    const selectVariant = event.target.closest("[data-select-variant]");
    if (selectVariant) {
      getEdge().selectedVariantId = selectVariant.dataset.selectVariant;
      getEdge().status = "editing";
      renderVariants(); updateSelectionSummary(); renderSequence();
      showToast("Variante lokal ausgewählt. Noch nicht übernommen.");
    }

    const audition = event.target.closest("[data-audition]");
    if (audition) {
      getEdge().selectedVariantId = audition.dataset.audition;
      state.playheadSeconds = 0; renderVariants(); updateSelectionSummary(); startPlayback();
    }
  });

  $("#trackSearch").addEventListener("input", (event) => { state.search = event.target.value; renderLibrary(); });
  $("#playPause").addEventListener("click", togglePlayback);
  $("#jumpStart").addEventListener("click", () => { state.playheadSeconds = 0; updatePlayhead(); });
  $("#loopToggle").addEventListener("click", () => { state.loop = !state.loop; $("#loopToggle").classList.toggle("is-active", state.loop); $("#loopToggle").setAttribute("aria-pressed", String(state.loop)); });
  $("#acceptTransition").addEventListener("click", acceptTransition);
  $("#exportButton").addEventListener("click", exportPreflight);
  $("#compareButton").addEventListener("click", () => showTab("alternatives"));
  $("#mockImport").addEventListener("click", () => showToast("Dateiimport ist in diesem isolierten Prototyp bewusst gemockt."));
  $("#zoomRange").addEventListener("input", (event) => $("#timelineStage").style.setProperty("--timeline-scale", Number(event.target.value) / 100));
  $("#lengthSelect").addEventListener("change", (event) => { getEdge().config.bars = Number(event.target.value); $("#transitionLabel").textContent = `Übergang · ${event.target.value} Takte`; markActiveEdgeEditing("Übergangslänge geändert."); });
  $("#tempoInput").addEventListener("change", (event) => { getEdge().config.targetBpm = Number(event.target.value); $("#toolbarTempo").textContent = `${Number(event.target.value).toFixed(1).replace(".", ",")} BPM`; markActiveEdgeEditing("Zieltempo geändert."); });
  $("#vocalCheck").addEventListener("change", (event) => { getEdge().config.avoidVocals = event.target.checked; markActiveEdgeEditing("Vocal-Präferenz geändert."); });
  $("#stretchRange").addEventListener("input", (event) => { getEdge().config.maxStretch = Number(event.target.value); $("#stretchValue").textContent = `${event.target.value} %`; markActiveEdgeEditing("Time-Stretch-Grenze geändert."); });
  $("#energyRange").addEventListener("input", (event) => { getEdge().config.energyPriority = Number(event.target.value); $("#energyValue").textContent = `${event.target.value} %`; markActiveEdgeEditing("Energie-Präferenz geändert."); });

  document.addEventListener("keydown", (event) => {
    const typing = ["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName);
    if (event.code === "Space" && !typing) { event.preventDefault(); togglePlayback(); }
    if (event.key.toLowerCase() === "l" && !typing) { $("#loopToggle").click(); }
    if (event.key === "Home" && !typing) { state.playheadSeconds = 0; updatePlayhead(); }
    if (["1", "2", "3"].includes(event.key) && !typing) {
      const variant = getEdge().variants[Number(event.key) - 1];
      if (variant) { getEdge().selectedVariantId = variant.id; renderVariants(); updateSelectionSummary(); }
    }
  });

  window.addEventListener("resize", updatePlayhead);
  renderAll();
}());
