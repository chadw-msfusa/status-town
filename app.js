const DATA_URL = "./data/status.json";

const sourceCards = document.querySelector("#source-cards");
const incidentList = document.querySelector("#incident-list");
const lastRefresh = document.querySelector("#last-refresh");
const messages = document.querySelector("#messages");
const sourceFilter = document.querySelector("#source-filter");
const reloadButton = document.querySelector("#reload-button");

let dashboardData = null;

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, character => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;"
  })[character]);
}

function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : "#";
  } catch {
    return "#";
  }
}

function formatDate(value) {
  if (!value) return "Unknown time";
  const date = new Date(value);
  return Number.isNaN(date.valueOf())
    ? "Unknown time"
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: "medium",
        timeStyle: "short"
      }).format(date);
}

function incidentTimestamp(value) {
  const timestamp = new Date(value || "").valueOf();
  return Number.isNaN(timestamp) ? Number.NEGATIVE_INFINITY : timestamp;
}

function severityDisplay(item) {
  const rawLevel = item?.severity;
  const suppliedLabel = String(item?.severity_label || "").trim();
  const numericLevel = Number(rawLevel);
  const isUnspecified =
    rawLevel === null ||
    rawLevel === undefined ||
    rawLevel === "" ||
    !Number.isFinite(numericLevel) ||
    numericLevel < 1 ||
    /^(unspecified|unknown)$/i.test(suppliedLabel);

  if (isUnspecified) {
    return {
      ariaLabel: "Severity unspecified",
      icons: `<span class="unspecified-icon" aria-hidden="true">🤔</span>`,
      label: "Unspecified"
    };
  }

  const count = Math.max(1, Math.min(5, Math.round(numericLevel)));
  const icons = Array.from(
    { length: count },
    () => `<img class="severity-icon" src="dumpster-fire.png" alt="">`
  ).join("");

  return {
    ariaLabel: `Severity ${count} out of 5`,
    icons: `<span class="severity-icons" aria-hidden="true">${icons}</span>`,
    label: count === 1 ? "Low" : suppliedLabel || "Mapped severity"
  };
}

function renderSources(sources) {
  sourceCards.innerHTML = sources.map(source => {
    const status = source.retrieval_status || "unknown";
    return `
      <article class="source-card">
        <header>
          <h3>${escapeHtml(source.name)}</h3>
          <span class="status-pill status-${escapeHtml(status)}">${escapeHtml(status)}</span>
        </header>
        <p class="source-detail">${escapeHtml(source.message || "No retrieval detail supplied.")}</p>
        <a href="${safeUrl(source.status_page_url)}" rel="noopener noreferrer">Open original status page</a>
      </article>`;
  }).join("");
}

function renderFilter(sources) {
  const current = sourceFilter.value;
  sourceFilter.innerHTML =
    `<option value="all">All sources</option>` +
    sources.map(source =>
      `<option value="${escapeHtml(source.id)}">${escapeHtml(source.name)}</option>`
    ).join("");

  sourceFilter.value = [...sourceFilter.options].some(
    option => option.value === current
  ) ? current : "all";
}

function renderIncidents() {
  const filter = sourceFilter.value;
  const incidents = [...(dashboardData?.incidents || [])]
    .filter(item => filter === "all" || item.source_id === filter)
    .sort((a, b) =>
      incidentTimestamp(b.published_at) - incidentTimestamp(a.published_at)
    );

  if (!incidents.length) {
    const availableCount = (dashboardData?.sources || []).filter(
      source => source.retrieval_status === "available"
    ).length;
    const wording = availableCount
      ? "No incident updates were returned by the selected successfully retrieved source(s). Check unavailable source cards separately."
      : "No incident data is available. This must not be interpreted as all services being healthy.";

    incidentList.innerHTML = "";
    messages.innerHTML = `<p class="message">${escapeHtml(wording)}</p>`;
    return;
  }

  messages.innerHTML = "";
  incidentList.innerHTML = incidents.map(item => {
    const severity = severityDisplay(item);

    return `
      <li class="incident">
        <article>
          <div class="incident-top">
            <div>
              <div class="incident-source">${escapeHtml(item.source_name)}</div>
              <h3>${escapeHtml(item.title || "Untitled vendor incident")}</h3>
            </div>
            <div class="severity" aria-label="${escapeHtml(severity.ariaLabel)}">
              ${severity.icons}
              <span class="severity-label">${escapeHtml(severity.label)}</span>
            </div>
          </div>
          <p class="update-body">${escapeHtml(item.body || "No update text supplied by the source.")}</p>
          <div class="meta">
            <time datetime="${escapeHtml(item.published_at || "")}">${escapeHtml(formatDate(item.published_at))}</time>
            <span>Vendor status: ${escapeHtml(item.vendor_status || "unknown")}</span>
            <a href="${safeUrl(item.source_url)}" rel="noopener noreferrer">Original source</a>
          </div>
        </article>
      </li>`;
  }).join("");
}

async function loadData() {
  messages.innerHTML = `<p class="message">Loading dashboard data…</p>`;

  try {
    const response = await fetch(`${DATA_URL}?cache=${Date.now()}`, {
      cache: "no-store"
    });

    if (!response.ok) {
      throw new Error(`Dashboard data returned HTTP ${response.status}`);
    }

    dashboardData = await response.json();
    lastRefresh.textContent = formatDate(dashboardData.generated_at);
    renderSources(dashboardData.sources || []);
    renderFilter(dashboardData.sources || []);
    renderIncidents();
  } catch (error) {
    dashboardData = null;
    lastRefresh.textContent = "Unavailable";
    sourceCards.innerHTML = "";
    incidentList.innerHTML = "";
    messages.innerHTML = `
      <p class="message">
        <strong>Dashboard data unavailable.</strong>
        ${escapeHtml(error.message)}. This is not a healthy-status indication.
      </p>`;
  }
}

const AUTO_REFRESH_INTERVAL_MS = 5 * 60 * 1000;

sourceFilter.addEventListener("change", renderIncidents);
reloadButton.addEventListener("click", loadData);

// Load the newest deployed status data when the page opens.
loadData();

// Check for newly deployed data every five minutes while the tab is visible.
setInterval(() => {
  if (!document.hidden) {
    loadData();
  }
}, AUTO_REFRESH_INTERVAL_MS);

// Refresh immediately when the user returns to the tab.
document.addEventListener("visibilitychange", () => {
  if (!document.hidden) {
    loadData();
  }
});
