const bundled = window.SVEA_SITE_DATA || {};
const state = {
  catalog: bundled.catalog || null,
  results: bundled.results?.runs || [],
  detail: { runIndex: 0, domain: "all", filter: "all", itemId: null },
};

const percent = value => value == null ? "—" : `${(Number(value) * 100).toFixed(1)}%`;
const shortModel = value => String(value || "").split("/").at(-1);

async function loadData() {
  if (state.catalog) {
    renderCatalog();
    renderResults();
    return;
  }
  try {
    const [catalogResponse, resultsResponse] = await Promise.all([
      fetch("data/catalog.json"),
      fetch("data/results.json"),
    ]);
    if (!catalogResponse.ok || !resultsResponse.ok) throw new Error("Project data unavailable");
    state.catalog = await catalogResponse.json();
    state.results = (await resultsResponse.json()).runs || [];
    renderCatalog();
    renderResults();
  } catch (error) {
    document.querySelector("#domain-grid").innerHTML = `<article class="domain-card"><span>!</span><h3>Capability data could not be loaded.</h3><p>${escapeHtml(error.message)}</p></article>`;
  }
}

function renderCatalog() {
  const suite = state.catalog.suite;
  document.querySelector('[data-stat="items"]').textContent = suite.items;
  document.querySelector('[data-stat="domains"]').textContent = suite.domains.length;
  document.querySelector('[data-stat="task-types"]').textContent = suite.task_types.length;
  document.querySelector('[data-stat="pairs"]').textContent = suite.pairs;

  document.querySelector("#domain-grid").innerHTML = suite.domains.map((domain, index) => `
    <article class="domain-card">
      <span>${String(index + 1).padStart(2, "0")}</span>
      <h3>${escapeHtml(domain.name)}</h3>
      <p>${escapeHtml(domain.description)}</p>
      <small>${domain.item_count} pilot items · ${domain.capabilities.length} capabilities</small>
    </article>
  `).join("");

  document.querySelector("#task-types").innerHTML = suite.task_types
    .map(task => `<span>${escapeHtml(task.name)}</span>`)
    .join("");

  document.querySelector("#integration-list").innerHTML = state.catalog.integrations.map((item, index) => `
    <a href="${escapeAttribute(item.url)}" target="_blank" rel="noopener noreferrer">
      <span>${String(index + 1).padStart(2, "0")}</span>
      <strong>${escapeHtml(item.name)}</strong>
      <p>${escapeHtml(item.role)}</p>
      <i aria-hidden="true">↗</i>
    </a>
  `).join("");
}

function renderResults() {
  if (!state.results.length) return;
  state.results.sort((left, right) =>
    Number(right.summary?.overall?.score || 0) - Number(left.summary?.overall?.score || 0));
  const view = document.querySelector("#results-view");
  view.className = "result-cards";
  view.innerHTML = state.results.map((run, index) => {
    const profile = run.summary.capability_profile || {};
    const domains = (run.summary.domains || []).map(domain => `
      <div class="domain-bar">
        <span>${escapeHtml(label(domain.id))}</span>
        <i><span style="width:${Math.max(0, Math.min(100, Number(domain.score) * 100))}%"></span></i>
        <b>${percent(domain.score)}</b>
      </div>
    `).join("");
    return `<article class="result-card">
      <header><h3>${escapeHtml(shortModel(run.model.id))}</h3><span>${escapeHtml(shortRevision(run.model.revision))}</span></header>
      <div class="judge-line"><span>JUDGE</span><strong>${escapeHtml(run.judge ? shortModel(run.judge.id) : "No LLM judge")}</strong><small>${escapeHtml(run.judge?.revision ? shortRevision(run.judge.revision) : "deterministic only")}</small></div>
      <div class="result-main">
        <div><strong>${percent(profile.macro_domain_score)}</strong><span>macro domain</span></div>
        <div><strong>${percent(profile.minimum_domain_score)}</strong><span>weakest domain</span></div>
      </div>
      <div class="result-domains">${domains}</div>
      <button class="inspect-button" type="button" data-run-index="${index}">Inspect ${run.items?.length || 0} answers <span aria-hidden="true">→</span></button>
    </article>`;
  }).join("");
  setupDeepDive();
}

function setupDeepDive() {
  const deepDive = document.querySelector("#deep-dive");
  const modelSelect = document.querySelector("#detail-model");
  const domainSelect = document.querySelector("#detail-domain");
  const filterSelect = document.querySelector("#detail-filter");
  deepDive.hidden = false;
  modelSelect.innerHTML = state.results.map((run, index) =>
    `<option value="${index}">${escapeHtml(shortModel(run.model.id))}</option>`).join("");
  domainSelect.innerHTML = `<option value="all">All domains</option>${state.catalog.suite.domains.map(domain =>
    `<option value="${escapeAttribute(domain.id)}">${escapeHtml(domain.name)}</option>`).join("")}`;
  modelSelect.value = String(state.detail.runIndex);
  domainSelect.value = state.detail.domain;
  filterSelect.value = state.detail.filter;
  modelSelect.onchange = event => {
    state.detail.runIndex = Number(event.target.value);
    state.detail.itemId = null;
    renderDeepDive();
  };
  domainSelect.onchange = event => {
    state.detail.domain = event.target.value;
    state.detail.itemId = null;
    renderDeepDive();
  };
  filterSelect.onchange = event => {
    state.detail.filter = event.target.value;
    state.detail.itemId = null;
    renderDeepDive();
  };
  document.querySelectorAll("[data-run-index]").forEach(button => {
    button.addEventListener("click", () => {
      state.detail.runIndex = Number(button.dataset.runIndex);
      state.detail.domain = "all";
      state.detail.filter = "all";
      state.detail.itemId = null;
      modelSelect.value = String(state.detail.runIndex);
      domainSelect.value = "all";
      filterSelect.value = "all";
      renderDeepDive();
      deepDive.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
  renderDeepDive();
}

function renderDeepDive() {
  const run = state.results[state.detail.runIndex];
  if (!run) return;
  const judge = run.judge;
  const backendSettings = run.protocol?.backend_settings || {};
  const think = backendSettings.think;
  const protocolMode = think === false
    ? "Thinking off"
    : think === true
      ? "Thinking on"
      : backendSettings.resolved_device
        ? `Transformers · ${String(backendSettings.resolved_device).toUpperCase()}`
        : "Provider default";
  document.querySelector("#deep-protocol").innerHTML = `
    <div><span>TARGET MODEL</span><strong>${escapeHtml(run.model.id)}</strong><code title="${escapeAttribute(run.model.revision || "")}">${escapeHtml(shortRevision(run.model.revision))}</code></div>
    <div><span>LLM JUDGE</span><strong>${escapeHtml(judge?.id || "Not configured")}</strong><code title="${escapeAttribute(judge?.revision || "")}">${escapeHtml(judge?.revision ? shortRevision(judge.revision) : "—")}</code></div>
    <div><span>SUITE</span><strong>${escapeHtml(run.suite.id)} v${escapeHtml(run.suite.version)}</strong><code>${run.items?.length || 0} items</code></div>
    <div><span>PROTOCOL</span><strong>${escapeHtml(protocolMode)}</strong><code>temp ${escapeHtml(run.protocol?.temperature ?? "—")}</code></div>`;
  const caveats = Array.isArray(run.limitations) ? run.limitations : [];
  const rescoring = run.rescoring_history?.at(-1);
  const judging = run.judging_history?.at(-1);
  const rescoringHtml = rescoring ? `<div class="rescore-note"><span>SCORING REVISION</span><p><strong>v${escapeHtml(rescoring.source_suite_version)} → v${escapeHtml(rescoring.target_suite_version)}</strong> ${escapeHtml(rescoring.reason)}</p><small>Saved model responses and judge outputs were reused; no inference was repeated.</small></div>` : "";
  const judgingHtml = judging ? `<div class="rescore-note"><span>OFFLINE JUDGE PASS</span><p><strong>${escapeHtml(judging.judge?.id || judge?.id || "Named judge")}</strong> scored ${(judging.judged_item_ids || []).length} preserved open answers.</p><small>Target responses were reused unchanged; target generation was not repeated.</small></div>` : "";
  const caveatHtml = caveats.length ? `<details><summary>Run limitations and comparability (${caveats.length})</summary><ul>${caveats.map(caveat => `<li>${escapeHtml(caveat)}</li>`).join("")}</ul></details>` : "";
  document.querySelector("#deep-caveats").innerHTML = rescoringHtml + judgingHtml + caveatHtml;

  const entries = (run.items || []).filter(entry => {
    if (state.detail.domain !== "all" && entry.item.domain !== state.detail.domain) return false;
    if (state.detail.filter === "attention") return entry.sample.error || entry.sample.score == null || entry.sample.score < 1 || !entry.sample.passed;
    if (state.detail.filter === "judged") return Boolean(entry.sample.judgment);
    if (state.detail.filter === "deterministic") return !entry.sample.judgment;
    return true;
  });
  if (!entries.some(entry => entry.item.id === state.detail.itemId)) {
    state.detail.itemId = entries[0]?.item.id || null;
  }
  const itemList = document.querySelector("#detail-items");
  if (!entries.length) {
    itemList.innerHTML = `<p class="no-items">No answers match these filters.</p>`;
    document.querySelector("#detail-answer").innerHTML = `<p class="no-items">Choose another filter to inspect evidence.</p>`;
    return;
  }
  itemList.innerHTML = entries.map((entry, index) => {
    const selected = entry.item.id === state.detail.itemId;
    const status = entry.sample.score == null ? "missing" : entry.sample.score >= 1 ? "perfect" : "partial";
    return `<button type="button" role="listitem" class="item-row ${selected ? "selected" : ""}" data-item-id="${escapeAttribute(entry.item.id)}" aria-pressed="${selected}">
      <span>${String(index + 1).padStart(2, "0")}</span>
      <div><strong>${escapeHtml(label(entry.item.capability))}</strong><small>${escapeHtml(domainName(entry.item.domain))} · ${escapeHtml(label(entry.item.task_type))}</small></div>
      <b class="item-score ${status}">${percent(entry.sample.score)}</b>
    </button>`;
  }).join("");
  itemList.querySelectorAll("[data-item-id]").forEach(button => {
    button.addEventListener("click", () => {
      state.detail.itemId = button.dataset.itemId;
      renderDeepDive();
    });
  });
  const selected = entries.find(entry => entry.item.id === state.detail.itemId) || entries[0];
  renderAnswer(run, selected);
}

function renderAnswer(run, entry) {
  const { item, sample } = entry;
  const dimensions = sample.judgment && sample.parsed && typeof sample.parsed === "object"
    ? Object.entries(sample.parsed).filter(([, value]) => Number.isFinite(Number(value)))
    : [];
  const dimensionHtml = dimensions.length ? `<div class="dimension-grid">${dimensions.map(([name, value]) => `
    <div><span>${escapeHtml(label(name))}</span><i><span style="width:${Math.max(0, Math.min(100, Number(value) * 25))}%"></span></i><b>${escapeHtml(value)}/4</b></div>`).join("")}</div>` : "";
  const context = item.context ? `<div class="question-context"><span>UNDERLAG</span><p>${escapeHtml(item.context)}</p></div>` : "";
  const options = item.options?.length ? `<ul class="answer-options">${item.options.map(option => `<li>${escapeHtml(option)}</li>`).join("")}</ul>` : "";
  const rationale = sample.score_details?.reason;
  const rubric = item.rubric;
  const rubricHtml = rubric ? `<details class="rubric-details"><summary>Rubric and reference answer</summary><div>
    <p><strong>Pass threshold</strong> ${percent(rubric.pass_threshold)}</p>
    <p><strong>Reference answer</strong><br>${escapeHtml(rubric.reference_answer || "No reference answer supplied.")}</p>
    <p><strong>Required points</strong></p><ul>${(rubric.required_points || []).map(point => `<li>${escapeHtml(point)}</li>`).join("")}</ul>
    <p><strong>Scoring dimensions</strong></p><dl>${Object.entries(rubric.dimensions || {}).map(([name, description]) => `<dt>${escapeHtml(label(name))}</dt><dd>${escapeHtml(description)}</dd>`).join("")}</dl>
  </div></details>` : "";
  const judgePanel = sample.judgment ? `
    <section class="judge-rationale">
      <div class="answer-subhead"><span>LLM JUDGE RATIONALE</span><strong>${escapeHtml(sample.judgment.model)}</strong></div>
      ${dimensionHtml}
      <blockquote>${escapeHtml(rationale || "The judge returned scores without a written rationale.")}</blockquote>
      <p class="reasoning-note">Published score rationale supplied by the judge; not hidden chain-of-thought.</p>
      ${rubricHtml}
      <details><summary>Raw judge output</summary><pre>${escapeHtml(sample.judgment.response)}</pre></details>
    </section>` : `
    <section class="deterministic-score">
      <div class="answer-subhead"><span>SCORING DECISION</span><strong>Deterministic · ${escapeHtml(sample.scorer)}</strong></div>
      <p>No LLM judge was used for this item. The answer was checked by the declared scorer.</p>
      <details><summary>Scorer details</summary><pre>${escapeHtml(JSON.stringify(sample.score_details || {}, null, 2))}</pre></details>
    </section>`;
  document.querySelector("#detail-answer").innerHTML = `
    <header class="answer-header">
      <div><span>${escapeHtml(domainName(item.domain))}</span><h4>${escapeHtml(label(item.capability))}</h4><code>${escapeHtml(item.id)}</code></div>
      <div class="answer-score"><strong>${percent(sample.score)}</strong><span>${sample.passed ? "passed" : sample.passed === false ? "did not pass" : "unscored"}</span></div>
    </header>
    <section class="question-block">${context}<span>UPPGIFT</span><p>${escapeHtml(item.prompt)}</p>${options}</section>
    <section class="model-answer"><div class="answer-subhead"><span>MODEL ANSWER</span><strong>${escapeHtml(shortModel(run.model.id))}</strong></div><pre>${escapeHtml(sample.response ?? "No response")}</pre></section>
    ${judgePanel}
    <div class="answer-meta"><span>${escapeHtml(label(item.task_type))}</span><span>${Math.round(Number(sample.latency_ms || 0))} ms</span><span>${sample.output_tokens ?? "—"} output tokens</span><a href="${escapeAttribute(item.source.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(item.source.title)} ↗</a></div>`;
}

function setupTabs() {
  const buttons = document.querySelectorAll(".runner-tabs button");
  buttons.forEach(button => button.addEventListener("click", () => {
    buttons.forEach(candidate => candidate.setAttribute("aria-selected", String(candidate === button)));
    document.querySelectorAll(".command").forEach(command => command.classList.remove("active"));
    document.querySelector(`#command-${button.dataset.tab}`).classList.add("active");
  }));
  document.querySelector("#copy-command").addEventListener("click", async event => {
    const command = document.querySelector(".command.active").innerText;
    try {
      await navigator.clipboard.writeText(command);
      event.currentTarget.textContent = "Copied";
      window.setTimeout(() => { event.currentTarget.textContent = "Copy"; }, 1300);
    } catch {
      event.currentTarget.textContent = "Select text";
    }
  });
}

function label(value) {
  return String(value || "").replaceAll("_", " ").replace(/\b\w/g, character => character.toUpperCase());
}

function domainName(value) {
  return state.catalog?.suite?.domains?.find(domain => domain.id === value)?.name || label(value);
}

function shortRevision(value) {
  if (!value) return "revision not supplied";
  const revision = String(value);
  return revision.startsWith("sha256:") ? revision.slice(7, 19) : revision.slice(0, 12);
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[character]);
}

function escapeAttribute(value) {
  return escapeHtml(value);
}

setupTabs();
loadData();
