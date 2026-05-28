const languageNames = {
  "en-US": "English",
  "pt-BR": "Portuguese",
  "es-MX": "Spanish",
  "ko-KR": "Korean",
  "zh-CN": "Chinese",
};

const artifactLabels = {
  html: "HTML",
  pptx: "PPTX",
  pdf: "PDF",
  slide_plan: "Slide Plan",
};

const healthPill = document.querySelector("#health-pill");
const templateSelect = document.querySelector("#template-id");
const templateStatus = document.querySelector("#template-status");
const languageOptions = document.querySelector("#language-options");
const generateButton = document.querySelector("#generate-button");
const createDeckButton = document.querySelector("#create-deck-button");
const deckStatus = document.querySelector("#deck-status");
const runSummary = document.querySelector("#run-summary");
const batchLogLink = document.querySelector("#batch-log-link");
const resultsList = document.querySelector("#results-list");
const resultTemplate = document.querySelector("#result-template");
const useLlmCheckbox = document.querySelector("#use-llm");
const requireLlmCheckbox = document.querySelector("#require-llm");

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    let message = text || `${response.status} ${response.statusText}`;
    try {
      const payload = JSON.parse(text);
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      // Keep the raw response text when the error body is not JSON.
    }
    throw new Error(message);
  }
  return response.json();
}

function editorTokenHeaders() {
  const token = window.localStorage.getItem("deck-editor-token");
  return token ? { "X-Deck-Edit-Token": token } : {};
}

function artifactUrl(path) {
  const filename = path.split("/").pop();
  return `/artifacts/${filename}`;
}

function selectedLanguages() {
  return [...languageOptions.querySelectorAll("input:checked")].map((input) => input.value);
}

function resultRow(language) {
  const fragment = resultTemplate.content.cloneNode(true);
  const row = fragment.querySelector(".result-row");
  row.dataset.language = language;
  row.querySelector(".result-language").textContent = languageNames[language] || language;
  row.querySelector(".result-status").textContent = "Queued";
  return fragment;
}

function updateRow(language, status, artifacts = {}, warnings = [], logsUrl = "") {
  const row = resultsList.querySelector(`[data-language="${language}"]`);
  if (!row) {
    return;
  }

  const statusNode = row.querySelector(".result-status");
  statusNode.textContent = status;
  statusNode.className = `result-status ${status.toLowerCase()}`;

  const artifactNode = row.querySelector(".result-artifacts");
  artifactNode.innerHTML = "";
  Object.entries(artifacts).forEach(([kind, path]) => {
    const link = document.createElement("a");
    link.href = artifactUrl(path);
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = artifactLabels[kind] || kind.toUpperCase();
    artifactNode.append(link);
  });
  if (logsUrl) {
    const logLink = document.createElement("a");
    logLink.href = logsUrl;
    logLink.target = "_blank";
    logLink.rel = "noreferrer";
    logLink.textContent = "Log";
    artifactNode.append(logLink);
  }

  const warningNode = row.querySelector(".result-warning");
  warningNode.textContent = warnings.join(" ");
}

async function loadHealth() {
  try {
    await fetchJson("/health");
    healthPill.textContent = "API ready";
    healthPill.classList.add("ok");
  } catch {
    healthPill.textContent = "API offline";
    healthPill.classList.add("bad");
  }
}

async function loadTemplates() {
  const data = await fetchJson("/api/v1/templates");
  templateSelect.innerHTML = "";

  data.templates.forEach((template) => {
    const option = document.createElement("option");
    option.value = template.template_id;
    option.textContent = template.template_id;
    templateSelect.append(option);
  });

  if ([...templateSelect.options].some((option) => option.value === "client_cvc_master")) {
    templateSelect.value = "client_cvc_master";
  }

  await inspectTemplate();
}

async function inspectTemplate() {
  if (!templateSelect.value) {
    return;
  }

  try {
    const data = await fetchJson(`/api/v1/templates/${encodeURIComponent(templateSelect.value)}/inspect`);
    const missing = data.missing_placeholders || [];
    if (missing.length) {
      templateStatus.textContent = `Missing placeholders: ${missing.join(", ")}`;
      templateStatus.className = "hint bad";
    } else if ((data.required_placeholders || []).length) {
      templateStatus.textContent = "Template ready";
      templateStatus.className = "hint ok";
    } else {
      templateStatus.textContent = "No schema attached";
      templateStatus.className = "hint";
    }
  } catch (error) {
    templateStatus.textContent = `Template check failed: ${error.message}`;
    templateStatus.className = "hint bad";
  }
}

async function loadLocales() {
  const data = await fetchJson("/api/v1/locales");
  languageOptions.innerHTML = "";

  data.locales.forEach((locale) => {
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.value = locale;
    input.checked = ["en-US", "pt-BR"].includes(locale);
    label.append(input, document.createTextNode(languageNames[locale] || locale));
    languageOptions.append(label);
  });
}

async function generateReports() {
  const languages = selectedLanguages();
  if (!languages.length) {
    runSummary.textContent = "Choose at least one language";
    return;
  }

  resultsList.innerHTML = "";
  languages.forEach((language) => resultsList.append(resultRow(language)));
  batchLogLink.hidden = true;
  generateButton.disabled = true;
  runSummary.textContent = `${languages.length} run${languages.length === 1 ? "" : "s"} in progress`;

  languages.forEach((language) => updateRow(language, "Running"));

  try {
    const legacyMode = useLlmCheckbox.checked;
    const batch = await fetchJson("/api/v1/batches", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        wave_id: document.querySelector("#wave-id").value.trim() || "demo-wave",
        languages,
        template_id: templateSelect.value || null,
        deck_mode: legacyMode ? "legacy" : "planned",
        use_llm: legacyMode,
        require_llm: legacyMode && requireLlmCheckbox.checked,
        include_pdf: document.querySelector("#include-pdf").checked,
      }),
    });

    batch.children.forEach((child) => {
      updateRow(child.language, child.status, child.artifacts, child.warnings, child.logs_url);
    });

    const completed = batch.children.filter((child) => child.status === "completed").length;
    runSummary.textContent = `${completed}/${batch.children.length} completed`;
    batchLogLink.href = batch.logs_url;
    batchLogLink.hidden = false;
  } catch (error) {
    languages.forEach((language) => updateRow(language, "Failed", {}, [error.message]));
    runSummary.textContent = "Batch failed";
  } finally {
    generateButton.disabled = false;
  }
}

async function createEditableDeck() {
  const waveId = document.querySelector("#wave-id").value.trim() || "demo-wave";
  createDeckButton.disabled = true;
  deckStatus.textContent = "Creating editable deck...";
  deckStatus.className = "hint";

  try {
    const deck = await fetchJson("/api/v1/decks/from-wave", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...editorTokenHeaders(),
      },
      body: JSON.stringify({ wave_id: waveId }),
    });
    const deckId = deck.id || deck.deck_json?.deck_id;
    if (!deckId) {
      throw new Error("Deck API did not return a deck id.");
    }
    deckStatus.textContent = "Deck created. Opening editor...";
    deckStatus.className = "hint ok";
    window.location.href = `/decks/editor/${encodeURIComponent(deckId)}`;
  } catch (error) {
    deckStatus.textContent = `Deck blocked: ${error.message}`;
    deckStatus.className = "hint bad";
  } finally {
    createDeckButton.disabled = false;
  }
}

useLlmCheckbox.addEventListener("change", () => {
  if (!useLlmCheckbox.checked) {
    requireLlmCheckbox.checked = false;
  }
  requireLlmCheckbox.disabled = !useLlmCheckbox.checked;
});

templateSelect.addEventListener("change", inspectTemplate);
generateButton.addEventListener("click", generateReports);
createDeckButton.addEventListener("click", createEditableDeck);

Promise.all([loadHealth(), loadTemplates(), loadLocales()]).catch((error) => {
  runSummary.textContent = error.message;
});
