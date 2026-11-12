const state = {
  providers: [],
  projects: [],
  project: null,
  task: "task1",
  pendingImageIds: [],
  draftMode: "edit",
  busy: false,
};

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const documentRoleLabels = {
  customer: "Customer evidence",
  brief: "Task instructions",
  reference: "Reference material",
  feedback: "Assessor feedback",
  review_only: "Prior submission — review only",
  template_task1: "Task 1 template",
  template_task2: "Task 2 template",
  discovery_approved: "Approved discovery",
};

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function renderInlineMarkdown(value) {
  const codeSpans = [];
  let text = String(value ?? "").replace(/`([^`]+)`/g, (_match, code) => {
    codeSpans.push(`<code>${escapeHtml(code)}</code>`);
    return `\u0000CODE${codeSpans.length - 1}\u0000`;
  });
  text = escapeHtml(text)
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/__([^_]+)__/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<em>$2</em>")
    .replace(/(^|[^_])_([^_\n]+)_/g, "$1<em>$2</em>");
  return text.replace(/\u0000CODE(\d+)\u0000/g, (_match, index) => codeSpans[Number(index)]);
}

function splitTableRow(line) {
  return line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => cell.trim());
}

function isTableDivider(line) {
  const cells = splitTableRow(line);
  return cells.length > 1 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function renderMarkdown(value) {
  const lines = String(value ?? "").replace(/<!--[^]*?-->/g, "").replace(/\r\n?/g, "\n").split("\n");
  const output = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) {
      index += 1;
      continue;
    }

    const fence = line.match(/^\s*```([^\s]*)\s*$/);
    if (fence) {
      const code = [];
      index += 1;
      while (index < lines.length && !/^\s*```/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      const language = fence[1] ? ` class="language-${escapeHtml(fence[1])}"` : "";
      output.push(`<pre><code${language}>${escapeHtml(code.join("\n"))}</code></pre>`);
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      const level = heading[1].length;
      output.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`);
      index += 1;
      continue;
    }

    if (/^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(line)) {
      output.push("<hr>");
      index += 1;
      continue;
    }

    if (index + 1 < lines.length && line.includes("|") && isTableDivider(lines[index + 1])) {
      const headers = splitTableRow(line);
      const rows = [];
      index += 2;
      while (index < lines.length && lines[index].includes("|") && lines[index].trim()) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      output.push(`<div class="table-scroll"><table><thead><tr>${headers.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead><tbody>${rows.map((row) => `<tr>${headers.map((_header, cellIndex) => `<td>${renderInlineMarkdown(row[cellIndex] || "")}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`);
      continue;
    }

    if (/^\s*[-*+]\s+/.test(line) || /^\s*\d+\.\s+/.test(line)) {
      const ordered = /^\s*\d+\.\s+/.test(line);
      const pattern = ordered ? /^\s*\d+\.\s+(.+)$/ : /^\s*[-*+]\s+(.+)$/;
      const items = [];
      while (index < lines.length) {
        const match = lines[index].match(pattern);
        if (!match) break;
        items.push(`<li>${renderInlineMarkdown(match[1])}</li>`);
        index += 1;
      }
      output.push(`<${ordered ? "ol" : "ul"}>${items.join("")}</${ordered ? "ol" : "ul"}>`);
      continue;
    }

    if (/^\s*>\s?/.test(line)) {
      const quote = [];
      while (index < lines.length && /^\s*>\s?/.test(lines[index])) {
        quote.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      output.push(`<blockquote>${renderInlineMarkdown(quote.join(" "))}</blockquote>`);
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim()) {
      const next = lines[index];
      if (/^(#{1,6})\s+/.test(next) || /^\s*```/.test(next) || /^\s*[-*+]\s+/.test(next) || /^\s*\d+\.\s+/.test(next) || /^\s*>\s?/.test(next) || /^\s*(?:-{3,}|\*{3,}|_{3,})\s*$/.test(next)) break;
      if (index + 1 < lines.length && next.includes("|") && isTableDivider(lines[index + 1])) break;
      paragraph.push(next.trim());
      index += 1;
    }
    output.push(`<p>${paragraph.map(renderInlineMarkdown).join("<br>")}</p>`);
  }

  return output.join("");
}

function setDraftMode(mode) {
  state.draftMode = mode === "preview" ? "preview" : "edit";
  const previewing = state.draftMode === "preview";
  $("#draftEditor").classList.toggle("hidden", previewing);
  $("#draftPreview").classList.toggle("hidden", !previewing);
  $("#editDraftButton").classList.toggle("active", !previewing);
  $("#previewDraftButton").classList.toggle("active", previewing);
  $("#editDraftButton").setAttribute("aria-pressed", String(!previewing));
  $("#previewDraftButton").setAttribute("aria-pressed", String(previewing));
  $("#draftMode").textContent = previewing ? "Rendered preview" : "Markdown source";
  if (previewing) {
    const content = $("#draftEditor").value.trim();
    $("#draftPreview").innerHTML = content
      ? renderMarkdown(content)
      : '<p class="preview-empty">Generate or write a draft to preview it here.</p>';
  }
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      message = body.detail || message;
    } catch (_) {}
    throw new Error(message);
  }
  const type = response.headers.get("content-type") || "";
  return type.includes("application/json") ? response.json() : response.text();
}

function toast(message, kind = "info") {
  const node = $("#toast");
  node.textContent = message;
  node.className = `toast visible ${kind}`;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (node.className = "toast"), 4200);
}

function setBusy(value, label = "Working…") {
  state.busy = value;
  ["#sendButton", "#generateButton", "#reviewButton", "#saveDraftButton", "#deleteProjectButton"].forEach((id) => {
    const node = $(id);
    if (node) node.disabled = value;
  });
  $("#serverStatus").classList.toggle("working", value);
  $("#serverStatus").lastChild.textContent = value ? ` ${label}` : " Local service ready";
}

function providerOptions(select, selected) {
  select.innerHTML = "";
  state.providers.forEach((provider) => {
    const option = document.createElement("option");
    option.value = provider.id;
    option.textContent = `${provider.label}${provider.configured ? "" : " — not configured"}`;
    option.selected = provider.id === selected;
    select.appendChild(option);
  });
}

function renderProjects() {
  const list = $("#projectList");
  list.innerHTML = "";
  if (!state.projects.length) {
    list.innerHTML = '<p class="sidebar-empty">No projects yet.</p>';
    return;
  }
  state.projects.forEach((project) => {
    const button = document.createElement("button");
    button.className = `project-item${state.project?.id === project.id ? " active" : ""}`;
    const title = document.createElement("strong");
    title.textContent = project.name;
    const meta = document.createElement("span");
    const provider = state.providers.find((item) => item.id === project.provider);
    meta.textContent = provider?.label || project.provider;
    button.append(title, meta);
    button.addEventListener("click", () => openProject(project.id));
    list.appendChild(button);
  });
}

function renderDocuments() {
  const docs = state.project?.documents || [];
  $("#sourceCount").textContent = docs.length;
  const list = $("#documentList");
  list.innerHTML = "";
  if (!docs.length) {
    list.innerHTML = '<div class="document-empty">Your evidence library is empty.</div>';
    return;
  }
  docs.forEach((doc) => {
    const item = document.createElement("div");
    item.className = "document-item";
    const icon = document.createElement("span");
    icon.className = "file-icon";
    icon.textContent = doc.mime_type?.startsWith("image/") ? "IMG" : "DOC";
    const text = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = doc.filename;
    const meta = document.createElement("small");
    meta.textContent = `${documentRoleLabels[doc.kind] || "Supporting document"} · ${doc.extracted_chars.toLocaleString()} chars`;
    text.append(name, meta);
    item.append(icon, text);
    list.appendChild(item);
  });
}

function renderMessages(messages) {
  const container = $("#messages");
  container.innerHTML = "";
  if (!messages.length) {
    const copy = state.task === "task1"
      ? "Start with the source pack. Ask me to extract requirements, identify unknowns, or explain the next discovery step."
      : "I will carry forward the Task 1 draft. Ask me to map requirements, challenge a design decision, or inspect missing controls.";
    container.innerHTML = `<div class="coach-welcome"><span>RAISE</span><p>${copy}</p></div>`;
    return;
  }
  messages.forEach((message) => {
    const wrapper = document.createElement("article");
    wrapper.className = `message ${message.role}`;
    const label = document.createElement("strong");
    label.textContent = message.role === "user" ? "You" : "RAISE coach";
    const content = document.createElement("div");
    content.className = `message-content${message.role === "assistant" ? " markdown-view" : ""}`;
    if (message.role === "assistant") {
      content.innerHTML = renderMarkdown(message.content);
    } else {
      content.textContent = message.content;
    }
    wrapper.append(label, content);
    if (message.sources?.length) {
      const sources = document.createElement("details");
      const summary = document.createElement("summary");
      summary.textContent = `${message.sources.length} grounded source${message.sources.length === 1 ? "" : "s"}`;
      const list = document.createElement("ul");
      message.sources.forEach((source) => {
        const li = document.createElement("li");
        li.textContent = `[${source.id}] ${source.source} — ${source.locator}`;
        list.appendChild(li);
      });
      sources.append(summary, list);
      wrapper.appendChild(sources);
    }
    container.appendChild(wrapper);
  });
  container.scrollTop = container.scrollHeight;
}

function renderPendingImages() {
  const container = $("#pendingImages");
  container.innerHTML = "";
  state.pendingImageIds.forEach((id, index) => {
    const chip = document.createElement("span");
    chip.textContent = `Screenshot ${index + 1}`;
    const remove = document.createElement("button");
    remove.textContent = "×";
    remove.addEventListener("click", () => {
      state.pendingImageIds = state.pendingImageIds.filter((value) => value !== id);
      renderPendingImages();
    });
    chip.appendChild(remove);
    container.appendChild(chip);
  });
}

async function loadTask() {
  if (!state.project) return;
  const [messages, draftData] = await Promise.all([
    api(`/api/projects/${state.project.id}/messages/${state.task}`),
    api(`/api/projects/${state.project.id}/draft/${state.task}`),
  ]);
  renderMessages(messages);
  $("#draftEditor").value = draftData.draft?.content || "";
  setDraftMode(state.draftMode);
  $("#draftStatus").textContent = draftData.draft
    ? `Saved · version ${draftData.draft.version}`
    : "Not saved";
  $("#templateBadge").textContent = draftData.official_template_used ? "Official template loaded" : "Fallback structure";
  $("#templateBadge").classList.toggle("official", draftData.official_template_used);
  $("#coachTitle").textContent = state.task === "task1" ? "Discovery coach" : "Solution design coach";
  $("#draftTitle").textContent = state.task === "task1" ? "discovery.md" : "spec.md";
}

async function refreshProjects() {
  state.projects = await api("/api/projects");
  renderProjects();
}

async function openProject(id) {
  if (state.project && state.project.id !== id && $("#draftStatus").textContent === "Unsaved changes") {
    if (!(await saveDraft())) return;
  }
  state.project = await api(`/api/projects/${id}`);
  $("#emptyState").classList.add("hidden");
  $("#workspace").classList.remove("hidden");
  $("#projectName").value = state.project.name;
  $("#projectDescription").value = state.project.description;
  providerOptions($("#providerSelect"), state.project.provider);
  $("#modelInput").value = state.project.model || "";
  renderProjects();
  renderDocuments();
  await loadTask();
}

function showNewProject() {
  $("#newProjectName").value = "";
  $("#newProjectDescription").value = "";
  const preferred = state.providers.find((item) => item.configured)?.id || "openai";
  providerOptions($("#newProviderSelect"), preferred);
  $("#projectDialog").showModal();
  setTimeout(() => $("#newProjectName").focus(), 60);
}

async function createProject(event) {
  event.preventDefault();
  try {
    const project = await api("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: $("#newProjectName").value,
        description: $("#newProjectDescription").value,
        provider: $("#newProviderSelect").value,
      }),
    });
    $("#projectDialog").close();
    await refreshProjects();
    await openProject(project.id);
    toast("Project created", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function saveProject() {
  try {
    state.project = await api(`/api/projects/${state.project.id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: $("#projectName").value,
        description: $("#projectDescription").value,
        provider: $("#providerSelect").value,
        model: $("#modelInput").value,
      }),
    });
    await refreshProjects();
    toast("Project settings saved", "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

async function deleteProject() {
  if (!state.project || state.busy) return;
  const project = state.project;
  const confirmed = window.confirm(
    `Permanently delete “${project.name}”?\n\nThis removes its supporting documents, conversations, drafts, and saved history. This cannot be undone.`
  );
  if (!confirmed) return;

  try {
    setBusy(true, "Deleting project…");
    await api(`/api/projects/${project.id}`, { method: "DELETE" });
    state.project = null;
    state.task = "task1";
    state.pendingImageIds = [];
    state.draftMode = "edit";
    $$(".task-tab").forEach((button) => button.classList.toggle("active", button.dataset.task === "task1"));
    $("#workspace").classList.add("hidden");
    $("#emptyState").classList.remove("hidden");
    await refreshProjects();
    if (state.projects.length) await openProject(state.projects[0].id);
    toast(`“${project.name}” was deleted`, "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function uploadFiles(files, kind = null) {
  if (!state.project || !files.length) return [];
  const form = new FormData();
  form.append("kind", kind || "auto");
  [...files].forEach((file) => form.append("files", file));
  const uploaded = await api(`/api/projects/${state.project.id}/documents`, { method: "POST", body: form });
  state.project = await api(`/api/projects/${state.project.id}`);
  renderDocuments();
  return uploaded;
}

async function addLibraryFiles(files) {
  const selected = [...(files || [])].filter(Boolean);
  if (!selected.length) {
    toast("No local files were detected. Drag files from Finder or use Choose files.", "error");
    return;
  }
  if (state.busy) return;
  const uploadTitle = $("#uploadZone strong");
  const originalTitle = uploadTitle.textContent;
  try {
    uploadTitle.textContent = `Uploading ${selected.length} file${selected.length === 1 ? "" : "s"}…`;
    $("#uploadZone").classList.add("uploading");
    setBusy(true, "Reading evidence…");
    const uploaded = await uploadFiles(selected);
    const warning = uploaded.find((item) => item.warning);
    toast(warning ? `${uploaded.length} file(s) added. ${warning.warning}` : `${uploaded.length} supporting document${uploaded.length === 1 ? "" : "s"} added and organized`, warning ? "error" : "success");
    await loadTask();
  } catch (error) {
    toast(error.message, "error");
  } finally {
    uploadTitle.textContent = originalTitle;
    $("#uploadZone").classList.remove("uploading");
    setBusy(false);
  }
}

async function handleLibraryUpload(event) {
  const files = [...event.target.files];
  event.target.value = "";
  await addLibraryFiles(files);
}

function bindLibraryDropZone() {
  const zone = $("#uploadZone");
  const input = $("#fileInput");
  let dragDepth = 0;

  zone.addEventListener("click", (event) => {
    if (event.target !== input && !state.busy) input.click();
  });
  zone.addEventListener("keydown", (event) => {
    if ((event.key === "Enter" || event.key === " ") && !state.busy) {
      event.preventDefault();
      input.click();
    }
  });

  zone.addEventListener("dragenter", (event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth += 1;
    zone.classList.add("drag-active");
  });
  zone.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer) event.dataTransfer.dropEffect = "copy";
  });
  zone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) zone.classList.remove("drag-active");
  });
  zone.addEventListener("drop", async (event) => {
    event.preventDefault();
    event.stopPropagation();
    dragDepth = 0;
    zone.classList.remove("drag-active");
    const transfer = event.dataTransfer;
    const files = transfer?.files?.length
      ? [...transfer.files]
      : [...(transfer?.items || [])]
          .filter((item) => item.kind === "file")
          .map((item) => item.getAsFile())
          .filter(Boolean);
    await addLibraryFiles(files);
  });
}

async function handleImageUpload(event) {
  try {
    setBusy(true, "Attaching screenshots…");
    const uploaded = await uploadFiles(event.target.files, "customer");
    state.pendingImageIds.push(...uploaded.map((item) => item.id));
    renderPendingImages();
    event.target.value = "";
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function sendMessage() {
  const message = $("#messageInput").value.trim();
  if (!message || state.busy) return;
  try {
    setBusy(true, "Coach is working…");
    await api(`/api/projects/${state.project.id}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task: state.task,
        message,
        provider: $("#providerSelect").value,
        model: $("#modelInput").value || null,
        attachment_ids: state.pendingImageIds,
      }),
    });
    $("#messageInput").value = "";
    state.pendingImageIds = [];
    renderPendingImages();
    renderMessages(await api(`/api/projects/${state.project.id}/messages/${state.task}`));
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function generateDraft() {
  if (state.busy) return;
  if ($("#draftEditor").value.trim()) {
    if (!window.confirm("Generate a new draft? Your current draft will be kept in History.")) return;
    if (!(await saveDraft())) return;
  }
  try {
    setBusy(true, "Building grounded draft…");
    const result = await api(`/api/projects/${state.project.id}/draft/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: state.task, provider: $("#providerSelect").value, model: $("#modelInput").value || null }),
    });
    $("#draftEditor").value = result.content;
    setDraftMode(state.draftMode);
    $("#draftStatus").textContent = `Saved · version ${result.version}`;
    $("#templateBadge").textContent = result.official_template_used ? "Official template loaded" : "Fallback structure";
    $("#templateBadge").classList.toggle("official", result.official_template_used);
    toast("Grounded draft generated", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function saveDraft() {
  try {
    const result = await api(`/api/projects/${state.project.id}/draft`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: state.task, content: $("#draftEditor").value }),
    });
    $("#draftStatus").textContent = `Saved · version ${result.version}`;
    toast("Draft saved", "success");
    return true;
  } catch (error) {
    toast(error.message, "error");
    return false;
  }
}

async function reviewDraft() {
  if (state.busy) return;
  try {
    if (!(await saveDraft())) return;
    setBusy(true, "Reviewing readiness…");
    await api(`/api/projects/${state.project.id}/draft/review`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ task: state.task, provider: $("#providerSelect").value, model: $("#modelInput").value || null }),
    });
    renderMessages(await api(`/api/projects/${state.project.id}/messages/${state.task}`));
    toast("Readiness review added to the coach", "success");
  } catch (error) {
    toast(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function downloadDraft() {
  if (!$("#draftEditor").value.trim()) return toast("There is no draft to download", "error");
  if (!(await saveDraft())) return;
  window.location.href = `/api/projects/${state.project.id}/export/${state.task}`;
}

async function showHistory() {
  if (!state.project) return;
  const task = state.task;
  try {
    if ($("#draftStatus").textContent === "Unsaved changes" && !(await saveDraft())) return;
    const versions = await api(`/api/projects/${state.project.id}/draft/${task}/history`);
    const list = $("#historyList");
    list.innerHTML = "";
    if (!versions.length) {
      list.textContent = "No saved versions yet.";
    }
    versions.forEach((version) => {
      const row = document.createElement("div");
      row.className = "history-row";
      const details = document.createElement("div");
      const title = document.createElement("strong");
      title.textContent = `Version ${version.version}`;
      const meta = document.createElement("small");
      meta.textContent = `${new Date(version.created_at).toLocaleString()} · ${version.characters.toLocaleString()} characters`;
      details.append(title, meta);
      const button = document.createElement("button");
      button.className = "button ghost small";
      button.textContent = "Restore";
      button.addEventListener("click", async () => {
        if (!window.confirm(`Restore version ${version.version}? Your current draft remains in history.`)) return;
        try {
          const result = await api(`/api/projects/${state.project.id}/draft/${task}/restore/${version.version}`, { method: "POST" });
          $("#draftEditor").value = result.content;
          setDraftMode(state.draftMode);
          $("#draftStatus").textContent = `Saved · version ${result.version}`;
          $("#historyDialog").close();
          toast(`Version ${version.version} restored`, "success");
        } catch (error) {
          toast(error.message, "error");
        }
      });
      row.append(details, button);
      list.appendChild(row);
    });
    $("#historyDialog").showModal();
  } catch (error) {
    toast(error.message, "error");
  }
}

function renderProviderCards() {
  const container = $("#providerCards");
  container.innerHTML = "";
  state.providers.forEach((provider) => {
    const card = document.createElement("article");
    card.className = `provider-card ${provider.configured ? "ready" : "missing"}`;
    const content = document.createElement("div");
    const name = document.createElement("strong");
    name.textContent = provider.label;
    const detail = document.createElement("p");
    detail.textContent = provider.detail;
    const model = document.createElement("code");
    model.textContent = provider.default_model;
    content.append(name, detail, model);
    const action = document.createElement("button");
    action.className = "button ghost small";
    action.textContent = provider.configured ? "Test" : "Needs setup";
    action.disabled = !provider.configured;
    action.addEventListener("click", async () => {
      action.disabled = true;
      action.textContent = "Testing…";
      try {
        const result = await api(`/api/providers/${provider.id}/test`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });
        toast(result.ok ? `${provider.label} is working` : `Unexpected response: ${result.response}`, result.ok ? "success" : "error");
      } catch (error) {
        toast(error.message, "error");
      } finally {
        action.disabled = false;
        action.textContent = "Test";
      }
    });
    card.append(content, action);
    container.appendChild(card);
  });
}

function bindEvents() {
  $("#newProjectButton").addEventListener("click", showNewProject);
  $("#emptyCreateButton").addEventListener("click", showNewProject);
  $("#projectForm").addEventListener("submit", createProject);
  $$(".close-dialog").forEach((button) => button.addEventListener("click", () => $("#projectDialog").close()));
  $("#saveProjectButton").addEventListener("click", saveProject);
  $("#deleteProjectButton").addEventListener("click", deleteProject);
  $("#fileInput").addEventListener("change", handleLibraryUpload);
  bindLibraryDropZone();
  $("#imageInput").addEventListener("change", handleImageUpload);
  $("#sendButton").addEventListener("click", sendMessage);
  $("#messageInput").addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") sendMessage();
  });
  $("#clearComposer").addEventListener("click", () => { $("#messageInput").value = ""; });
  $("#generateButton").addEventListener("click", generateDraft);
  $("#saveDraftButton").addEventListener("click", saveDraft);
  $("#historyButton").addEventListener("click", showHistory);
  $("#reviewButton").addEventListener("click", reviewDraft);
  $("#downloadButton").addEventListener("click", downloadDraft);
  $("#editDraftButton").addEventListener("click", () => setDraftMode("edit"));
  $("#previewDraftButton").addEventListener("click", () => setDraftMode("preview"));
  $$(".task-tab").forEach((button) => button.addEventListener("click", async () => {
    if ($("#draftStatus").textContent === "Unsaved changes" && !(await saveDraft())) return;
    state.task = button.dataset.task;
    $$(".task-tab").forEach((node) => node.classList.toggle("active", node === button));
    await loadTask();
  }));
  $("#setupButton").addEventListener("click", () => { renderProviderCards(); $("#setupDialog").showModal(); });
  $$(".close-setup").forEach((button) => button.addEventListener("click", () => $("#setupDialog").close()));
  $$(".close-history").forEach((button) => button.addEventListener("click", () => $("#historyDialog").close()));
  $("#draftEditor").addEventListener("input", () => { $("#draftStatus").textContent = "Unsaved changes"; });
}

async function initialize() {
  bindEvents();
  try {
    await api("/api/health");
    $("#serverStatus").classList.add("ready");
    $("#serverStatus").lastChild.textContent = " Local service ready";
    state.providers = await api("/api/providers");
    providerOptions($("#providerSelect"), "openai");
    providerOptions($("#newProviderSelect"), state.providers.find((item) => item.configured)?.id || "openai");
    await refreshProjects();
    if (state.projects.length) await openProject(state.projects[0].id);
  } catch (error) {
    $("#serverStatus").classList.add("error");
    $("#serverStatus").lastChild.textContent = " Local service unavailable";
    toast(error.message, "error");
  }
}

initialize();

