"use strict";

// ---------- state ----------
let D = null;                 // current case bundle
let IDX = {};                 // derived indexes for the current case
let sel = null;               // selected claim id
let tab = "cruxes";
const filt = { side: "all", kind: "all", q: "" };

const $ = (id) => document.getElementById(id);
const esc = (s) => (s == null ? "" : String(s).replace(/[&<>"]/g,
  (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c])));

const SIDE_CLASS = { zoonosis: "zoo", lab_leak: "lab" };
const SUPPORT_TYPES = new Set(["supports", "is_evidence_for", "depends_on"]);

// ---------- boot ----------
init();
async function init() {
  const manifest = await fetch("data/manifest.json").then((r) => r.json());
  const sel = $("caseSelect");
  manifest.forEach((m) => {
    const o = document.createElement("option");
    o.value = m.case;
    o.textContent = m.case.toUpperCase() + (m.has_data ? "" : " — (not yet run)");
    o.disabled = !m.has_data;
    sel.appendChild(o);
  });
  sel.onchange = () => loadCase(sel.value);
  const first = manifest.find((m) => m.has_data);
  if (first) { sel.value = first.case; loadCase(first.case); }
  else { $("detail").innerHTML = '<div class="notrun">No case has been run yet.</div>'; }

  $("search").oninput = (e) => { filt.q = e.target.value.toLowerCase().trim(); renderList(); };
  document.querySelectorAll("#tabs button").forEach((b) => {
    b.onclick = () => { tab = b.dataset.tab;
      document.querySelectorAll("#tabs button").forEach((x) => x.classList.toggle("on", x === b));
      renderPanel(); };
  });
}

// ---------- load a case ----------
async function loadCase(name) {
  D = await fetch(`data/${name}.json`).then((r) => r.json());
  sel = null;
  const claimById = {}, outE = {}, inE = {}, srcById = {};
  (D.sources || []).forEach((s) => (srcById[s.id] = s));
  D.claims.forEach((c) => { claimById[c.id] = c; outE[c.id] = []; inE[c.id] = []; });
  D.edges.forEach((e) => { (outE[e.from] || (outE[e.from] = [])).push(e);
    (inE[e.to] || (inE[e.to] = [])).push(e); });
  const cruxByClaim = {};
  (D.assessment?.cruxes || []).forEach((c) => (cruxByClaim[c.claim_id] = c));
  const concById = {};
  (D.concentration || []).forEach((r) => (concById[r.conclusion] = r));
  IDX = { claimById, outE, inE, srcById, cruxByClaim, concById };

  $("question").textContent = D.question || "";
  $("counts").innerHTML =
    `<span><b>${D.claims.length}</b> claims</span><span><b>${D.edges.length}</b> edges</span>` +
    `<span><b>${(D.sources || []).length}</b> sources</span>` +
    `<span><b>${(D.assessment?.cruxes || []).length}</b> cruxes</span>`;
  $("method").textContent = D.assessment?.method ? "Method: " + D.assessment.method : "";

  buildFilters();
  renderList();
  renderPanel();
  $("detail").innerHTML =
    '<div class="empty">Select a claim, crux, or conclusion to trace its provenance and dependencies.</div>';
}

function sideOf(c) {
  const a = c.attestations && c.attestations[0];
  const s = a && IDX.srcById[a.source_id];
  return s ? (s.side || "neutral") : "neutral";
}

// ---------- left: filters + list ----------
function buildFilters() {
  const sides = ["all", ...new Set((D.sources || []).map((s) => s.side).filter(Boolean))];
  $("sideChips").innerHTML = sides.map((s) =>
    `<button data-side="${esc(s)}" class="${filt.side === s ? "on" : ""}">${esc(s)}</button>`).join("");
  const kinds = ["all", "crux", "conclusion", "evidence", "inference", "assumption", "methodological"];
  $("kindChips").innerHTML = kinds.map((k) =>
    `<button data-kind="${k}" class="${filt.kind === k ? "on" : ""}">${k}</button>`).join("");
  $("sideChips").querySelectorAll("button").forEach((b) =>
    (b.onclick = () => { filt.side = b.dataset.side; buildFilters(); renderList(); }));
  $("kindChips").querySelectorAll("button").forEach((b) =>
    (b.onclick = () => { filt.kind = b.dataset.kind; buildFilters(); renderList(); }));
}

function passesFilter(c) {
  if (filt.side !== "all" && sideOf(c) !== filt.side) return false;
  if (filt.kind === "crux") { if (!IDX.cruxByClaim[c.id]) return false; }
  else if (filt.kind !== "all" && c.kind !== filt.kind) return false;
  if (filt.q) {
    const hay = (c.id + " " + c.text + " " +
      (c.attestations || []).map((a) => a.source_id).join(" ")).toLowerCase();
    if (!hay.includes(filt.q)) return false;
  }
  return true;
}

function renderList() {
  const box = $("claimList");
  const rows = D.claims.filter(passesFilter);
  box.innerHTML = rows.map((c) => {
    const side = SIDE_CLASS[sideOf(c)] || "";
    const crux = IDX.cruxByClaim[c.id];
    return `<div class="row ${c.id === sel ? "sel" : ""}" data-id="${c.id}">
      <span class="dot ${side}"></span>
      <span class="rtext">${esc(c.text.slice(0, 120))}
        <span class="rid">${c.id} · ${esc(c.kind)}</span></span>
      ${crux ? '<span class="star">★</span>' : ""}</div>`;
  }).join("") || '<div class="muted" style="padding:14px">No claims match.</div>';
  box.querySelectorAll(".row").forEach((r) => (r.onclick = () => select(r.dataset.id)));
}

// ---------- center: claim detail ----------
function select(id) {
  const c = IDX.claimById[id];
  if (!c) return;
  sel = id;
  renderList();
  const row = $("claimList").querySelector(`.row[data-id="${id}"]`);
  if (row) row.scrollIntoView({ block: "nearest" });

  const side = sideOf(c), sc = SIDE_CLASS[side] || "";
  const crux = IDX.cruxByClaim[id];
  const atts = (c.attestations || []).map((a) => {
    const s = IDX.srcById[a.source_id] || {};
    const who = [s.title, s.author].filter(Boolean).join(" · ") || a.source_id;
    return `<div class="span">“${esc(a.verbatim_span || "(no verbatim span captured)")}”
      <span class="attr">— ${esc(who)}${s.url ? ` · <a href="${esc(s.url)}" target="_blank" rel="noopener">source</a>` : ""}</span></div>
      ${a.framing ? `<div class="framing"><b>framing:</b> ${esc(a.framing)}</div>` : ""}`;
  }).join("");

  const est = (c.probability_estimates || []).filter((p) => p.value);
  const estHtml = est.length
    ? `<div class="rel"><h3>Probability estimates</h3>${est.map((p) =>
        `<div>${esc(p.value)} <span class="muted">— ${esc(IDX.srcById[p.source_id]?.author || p.source_id)}</span></div>`).join("")}</div>`
    : "";

  $("detail").innerHTML = `<div class="detail">
    <div class="pills">
      <span class="pill ${sc}">${esc(side)}</span>
      <span class="pill kind">${esc(c.kind)}</span>
      ${crux ? `<span class="pill crux">CRUX · score ${crux.score ?? "?"} · sens ${crux.sensitivity ?? "?"}</span>` : ""}
      <code>${c.id}</code>
    </div>
    <h2>${esc(c.text)}</h2>
    ${atts}
    ${estHtml}
    ${relBlock("Points to — this claim supports / depends on / relates to", IDX.outE[id], "to")}
    ${relBlock("Pointed to by — claims that rest on or relate to this", IDX.inE[id], "from")}
  </div>`;
  $("detail").querySelectorAll(".edge").forEach((el) => (el.onclick = () => select(el.dataset.go)));
}

function relBlock(title, edges, endKey) {
  edges = edges || [];
  if (!edges.length) return "";
  // strongest/most-structural first
  const order = { depends_on: 0, is_evidence_for: 1, supports: 2, contradicts: 3, restates: 4, caveats: 5 };
  edges = edges.slice().sort((a, b) => (order[a.type] ?? 9) - (order[b.type] ?? 9));
  return `<div class="rel"><h3>${esc(title)} (${edges.length})</h3>` + edges.map((e) => {
    const other = IDX.claimById[e[endKey]];
    return `<div class="edge" data-go="${esc(e[endKey])}">
      <span class="etype ${esc(e.type)}">${esc(e.type)}${e.strength ? " · " + esc(e.strength) : ""}</span>
      <span class="etext">${esc(other ? other.text.slice(0, 110) : e[endKey])}
        <span class="eid">${esc(e[endKey])}</span></span></div>`;
  }).join("") + "</div>";
}

// ---------- right: assessment panels ----------
function renderPanel() {
  if (!D) return;
  if (tab === "cruxes") renderCruxes();
  else if (tab === "conclusions") renderConclusions();
  else renderIntegrity();
}

function renderCruxes() {
  const cx = D.assessment?.cruxes || [];
  $("panel").innerHTML = cx.length ? cx.map((c, i) => {
    const cl = IDX.claimById[c.claim_id];
    return `<div class="item click" data-go="${esc(c.claim_id)}">
      <div class="top"><span class="rank">#${i + 1}</span> <code>${esc(c.claim_id)}</code></div>
      <div>${esc(cl ? cl.text.slice(0, 120) : "")}</div>
      <div class="bar"><span style="width:${Math.round((c.sensitivity || 0) * 100)}%"></span></div>
      <div class="aff">sensitivity ${c.sensitivity} · affects: ${esc((c.affects || "").slice(0, 70))}
        ${c.affects_support_count ? `(${c.affects_support_count} supporting claims)` : ""}</div>
      <div class="why">${esc(c.rationale || "")}</div>
      ${c.model_rationale ? `<div class="why"><b>narration:</b> ${esc(c.model_rationale)}</div>` : ""}
    </div>`;
  }).join("") : '<div class="muted">No cruxes ranked.</div>';
  wireGo();
}

function renderConclusions() {
  const rows = (D.concentration || []).filter((r) => r.top_claim)
    .sort((a, b) => (b.supporting_claim_count || 0) - (a.supporting_claim_count || 0));
  $("panel").innerHTML = rows.length ? rows.map((r) => {
    const top = (r.contributions || []).slice(0, 6);
    return `<div class="item">
      <div class="click" data-go="${esc(r.conclusion)}">${esc(r.conclusion_text)}
        <span class="muted">${esc(r.conclusion)}</span></div>
      <div class="metric" style="margin-top:6px">
        <b>${Math.round((r.concentration || 0) * 100)}%</b><small>concentrated on top claim</small>
        <b style="margin-left:auto">~${r.effective_independent_claims}</b>
        <small>eff. independent · ${r.supporting_claim_count} total</small></div>
      <div style="margin-top:8px">${top.map((t) =>
        `<div class="edge" data-go="${esc(t.claim_id)}">
          <span class="etext" style="flex:1">${esc((t.text || IDX.claimById[t.claim_id]?.text || "").slice(0, 80))}
            <span class="eid">${esc(t.claim_id)}</span></span></div>
         <div class="bar blue"><span style="width:${Math.round((t.share || 0) * 100)}%"></span></div>`).join("")}</div>
    </div>`;
  }).join("") : '<div class="muted">No supported conclusions.</div>';
  wireGo();
}

function renderIntegrity() {
  const circ = D.circular_support || [];
  const corr = D.assessment?.correlated_evidence_flags || [];
  let html = `<h3 class="muted" style="margin:2px 0 10px">Circular-support loops (${circ.length})</h3>`;
  html += circ.length ? circ.map((f) => `<div class="item">
      <div class="top"><span class="sev ${esc(f.severity)}">${esc(f.severity)}</span>
        <code>${(f.claim_ids || []).join(" · ")}</code></div>
      <div class="why">${esc(f.rationale || "")}</div>
      ${(f.members || []).map((m) => `<div class="edge" data-go="${esc(m.id)}">
        <span class="etext">${esc(m.text)} <span class="eid">${esc(m.id)}</span></span></div>`).join("")}
    </div>`).join("")
    : '<div class="muted">No circular corroboration detected — support grounds out cleanly.</div>';
  html += `<h3 class="muted" style="margin:18px 0 10px">Correlated-evidence flags (${corr.length})</h3>`;
  html += corr.length ? corr.map((f) => `<div class="item">
      <code>${(f.claim_ids || []).join(" · ")}</code>
      <div class="why">${esc(f.rationale || "")}</div></div>`).join("")
    : '<div class="muted">None flagged.</div>';
  $("panel").innerHTML = html;
  wireGo();
}

function wireGo() {
  $("panel").querySelectorAll("[data-go]").forEach((el) => (el.onclick = () => select(el.dataset.go)));
}
