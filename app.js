/**
 * Groww HDFC Mutual Fund Facts Assistant — Frontend Client
 * Communicates with Railway FastAPI backend via /api/* endpoints
 */
// Relative path on Vercel reverse proxy (/api/*); fallback to localhost:8000 for local dev
const API_BASE = (window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1") && window.location.port !== "8000"
    ? "http://localhost:8000"
    : "";

let activeThreadId = null;
let isSubmitting = false;

// DOM Elements
const chatViewport = document.getElementById("chatViewport");
const chatMessages = document.getElementById("chatMessages");
const welcomeHero = document.getElementById("welcomeHero");
const schemesSection = document.getElementById("schemesSection");
const schemesGrid = document.getElementById("schemesGrid");
const chatInput = document.getElementById("chatInput");
const sendBtn = document.getElementById("sendBtn");
const threadList = document.getElementById("threadList");
const newThreadBtn = document.getElementById("newThreadBtn");
const backendStatusText = document.getElementById("backendStatusText");

// Initialize on page load
document.addEventListener("DOMContentLoaded", () => {
  initHealthCheck();
  loadSchemesOverview();
  loadSavedSessions();

  // Send message events
  sendBtn.addEventListener("click", handleUserSubmit);
  chatInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleUserSubmit();
    }
  });

  // New Thread event
  newThreadBtn.addEventListener("click", () => {
    resetToNewThread();
  });
});

/**
 * 1. Health check & status monitoring
 */
async function initHealthCheck() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      const data = await res.json();
      backendStatusText.textContent = `Online (${data.chunks_indexed} chunks)`;
    } else {
      backendStatusText.textContent = "Connecting...";
    }
  } catch (err) {
    console.warn("Health check failed:", err);
    backendStatusText.textContent = "Connecting to Railway...";
  }
}

/**
 * 2. Fetch and render 5 Covered HDFC Schemes
 */
async function loadSchemesOverview() {
  try {
    const res = await fetch(`${API_BASE}/api/schemes`);
    if (!res.ok) return;
    const schemes = await res.json();
    if (!schemes || schemes.length === 0) return;

    schemesGrid.innerHTML = "";
    schemes.forEach((s) => {
      const card = document.createElement("div");
      card.className = "scheme-card";
      card.innerHTML = `
        <div>
          <div class="card-top">
            <span class="category-tag">${s.category.replace("Equity: ", "")}</span>
            <span class="risk-tag">${s.risk_level}</span>
          </div>
          <div class="scheme-name">${s.scheme_name}</div>
          <div style="font-size: 11px; color: var(--text-muted); margin-bottom: 8px;">Direct Plan • Growth</div>
          <div>
            <span class="scheme-nav">${s.nav}</span>
            <span class="scheme-nav-change">${s.change_pct}</span>
          </div>
        </div>
        <div class="metric-grid">
          <div class="metric-row"><span>Direct TER</span><span>${s.expense_ratio}</span></div>
          <div class="metric-row"><span>Exit Load</span><span>${s.exit_load}</span></div>
          <div class="metric-row"><span>Fund Size</span><span style="color: var(--accent-primary);">${s.fund_size}</span></div>
        </div>
        <button class="btn-card-query" onclick="populateAndSend('What is the exit load and expense ratio of ${s.scheme_name}?')">
          Query Scheme →
        </button>
      `;
      schemesGrid.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load schemes:", err);
  }
}

/**
 * 3. Fetch and render conversation sessions
 */
async function loadSavedSessions() {
  try {
    const res = await fetch(`${API_BASE}/api/sessions`);
    if (!res.ok) return;
    const threads = await res.json();
    renderThreadList(threads);
  } catch (err) {
    console.error("Failed to load sessions:", err);
  }
}

function renderThreadList(threads) {
  threadList.innerHTML = "";
  if (!threads || threads.length === 0) {
    threadList.innerHTML = `<div style="font-size: 12px; color: var(--text-muted); padding: 8px;">No saved threads</div>`;
    return;
  }

  threads.forEach((t) => {
    const item = document.createElement("div");
    item.className = `thread-item ${t.thread_id === activeThreadId ? "active" : ""}`;
    item.innerHTML = `
      <div class="thread-title" title="${t.title}">💬 ${t.title}</div>
      <button class="btn-delete-thread" title="Delete thread" onclick="deleteThread(event, '${t.thread_id}')">✕</button>
    `;
    item.addEventListener("click", () => switchThread(t.thread_id));
    threadList.appendChild(item);
  });
}

async function switchThread(threadId) {
  try {
    const res = await fetch(`${API_BASE}/api/sessions/${threadId}`);
    if (!res.ok) return;
    const threadData = await res.json();
    activeThreadId = threadId;

    // Hide hero and schemes overview when viewing active conversation
    welcomeHero.style.display = "none";
    schemesSection.style.display = "none";
    chatMessages.innerHTML = "";

    threadData.messages.forEach((m) => {
      if (m.role === "user") {
        renderUserMessage(m.content);
      } else {
        renderAssistantMessage({
          content: m.content,
          citation_url: m.citation_url,
          is_refusal: m.is_refusal,
          last_updated: m.last_updated || new Date().toISOString().slice(0, 10),
        });
      }
    });

    loadSavedSessions();
    scrollToBottom();
  } catch (err) {
    console.error("Failed to switch thread:", err);
  }
}

async function deleteThread(e, threadId) {
  e.stopPropagation();
  try {
    await fetch(`${API_BASE}/api/sessions/${threadId}`, { method: "DELETE" });
    if (activeThreadId === threadId) {
      resetToNewThread();
    } else {
      loadSavedSessions();
    }
  } catch (err) {
    console.error("Failed to delete thread:", err);
  }
}

function resetToNewThread() {
  activeThreadId = null;
  chatMessages.innerHTML = "";
  welcomeHero.style.display = "block";
  schemesSection.style.display = "block";
  chatInput.value = "";
  chatInput.focus();
  loadSavedSessions();
}

/**
 * 4. User Submission & RAG Execution
 */
async function handleUserSubmit() {
  const query = chatInput.value.trim();
  if (!query || isSubmitting) return;

  isSubmitting = true;
  sendBtn.disabled = true;
  chatInput.value = "";

  // Hide welcome hero and scheme cards once chat starts
  welcomeHero.style.display = "none";
  schemesSection.style.display = "none";

  renderUserMessage(query);
  scrollToBottom();

  const thinkingEl = renderThinkingIndicator();
  scrollToBottom();

  try {
    const res = await fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query, thread_id: activeThreadId }),
    });

    thinkingEl.remove();

    if (!res.ok) {
      throw new Error(`Server returned HTTP ${res.status}`);
    }

    const data = await res.json();
    activeThreadId = data.thread_id;

    renderAssistantMessage(data);
    loadSavedSessions();
  } catch (err) {
    thinkingEl.remove();
    renderAssistantMessage({
      content: "Unable to reach the facts database at this moment. Please verify the backend connection.",
      is_refusal: true,
      citation_url: "https://groww.in/mutual-funds",
      last_updated: new Date().toISOString().slice(0, 10),
    });
  } finally {
    isSubmitting = false;
    sendBtn.disabled = false;
    chatInput.focus();
    scrollToBottom();
  }
}

/**
 * Render message elements
 */
function renderUserMessage(text) {
  const wrapper = document.createElement("div");
  wrapper.className = "user-bubble-container";
  wrapper.innerHTML = `
    <div class="user-bubble">${escapeHtml(text)}</div>
  `;
  chatMessages.appendChild(wrapper);
}

function renderAssistantMessage(data) {
  const wrapper = document.createElement("div");
  wrapper.className = "assistant-card-container";

  if (data.is_refusal) {
    wrapper.innerHTML = `
      <div class="assistant-badge" style="color: var(--alert-warning);">
        <span>⚠️</span> <span>Compliance Notice</span>
      </div>
      <div class="refusal-card">
        ${formatBodyText(data.content)}
      </div>
    `;
  } else {
    const citationHtml = data.citation_url
      ? `<a href="${data.citation_url}" target="_blank" rel="noopener noreferrer" class="citation-btn">
           <span>Verified Source</span> ↗
         </a>`
      : "";

    wrapper.innerHTML = `
      <div class="assistant-badge">
        <span>📈</span> <span>Groww Facts Engine</span>
      </div>
      <div class="answer-card">
        <div>${formatBodyText(data.content)}</div>
        <div class="card-footer">
          <div>${citationHtml}</div>
          <div>Last updated from sources: ${data.last_updated || "October 2026"}</div>
        </div>
      </div>
    `;
  }

  chatMessages.appendChild(wrapper);
}

function renderThinkingIndicator() {
  const wrapper = document.createElement("div");
  wrapper.className = "assistant-card-container";
  wrapper.innerHTML = `
    <div class="thinking-card">
      <div class="spinner"></div>
      <span>Looking up official HDFC scheme factsheets...</span>
    </div>
  `;
  chatMessages.appendChild(wrapper);
  return wrapper;
}

function populateAndSend(promptText) {
  chatInput.value = promptText;
  handleUserSubmit();
}

function scrollToBottom() {
  setTimeout(() => {
    chatViewport.scrollTop = chatViewport.scrollHeight;
  }, 50);
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function formatBodyText(text) {
  // Strip duplicate markdown source lines or brackets if already present
  let clean = text.replace(/\[GrowwPage\]\([^)]+\)/gi, "");
  clean = clean.replace(/\*\*Source\*\*:\s*\[[^\]]+\]\([^)]+\)/gi, "");
  clean = clean.replace(/\*Last updated from sources:.*?\*/gi, "");
  clean = clean.trim();

  // Basic bolding
  clean = clean.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  return clean.replace(/\n\n/g, "<br/><br/>");
}
