const bundled = window.SVEA_SITE_DATA || {};
const state = {
  catalog: bundled.catalog || null,
  results: bundled.results?.runs || [],
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
  const view = document.querySelector("#results-view");
  view.className = "result-cards";
  view.innerHTML = state.results.map(run => {
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
      <div class="result-main">
        <div><strong>${percent(profile.macro_domain_score)}</strong><span>macro domain</span></div>
        <div><strong>${percent(profile.minimum_domain_score)}</strong><span>weakest domain</span></div>
      </div>
      <div class="result-domains">${domains}</div>
    </article>`;
  }).join("");
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

function shortRevision(value) {
  return value ? String(value).slice(0, 10) : "revision not supplied";
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
