(function () {
  "use strict";

  const form = document.getElementById("brief-form");
  if (!form) return;

  const roleEl = document.getElementById("role");
  const langEl = document.getElementById("language");
  const levelEl = document.getElementById("reading_level");
  const fileEl = document.getElementById("file-upload");
  const tableEl = document.getElementById("raw_table");
  const charCountEl = document.getElementById("char-count");
  const tableErrorEl = document.getElementById("table-error");
  const submitBtn = document.getElementById("submit-btn");
  const clearBtn = document.getElementById("clear-btn");
  const retryBtn = document.getElementById("retry-btn");
  const copyBtn = document.getElementById("copy-advisory-btn");
  const copyStatusEl = document.getElementById("copy-status");
  const outputHeading = document.getElementById("output-heading");

  const stateEmpty = document.getElementById("state-empty");
  const stateLoading = document.getElementById("state-loading");
  const stateError = document.getElementById("state-error");
  const stateResult = document.getElementById("state-result");
  const errorMessageEl = document.getElementById("error-message");

  let lastAdvisoryText = "";

  function updateCharCount() {
    const len = tableEl.value.length;
    charCountEl.textContent = len + " / 2000";
  }

  function clearFieldError() {
    tableEl.removeAttribute("aria-invalid");
    tableErrorEl.textContent = "";
    tableErrorEl.hidden = true;
  }

  function showFieldError(msg) {
    tableEl.setAttribute("aria-invalid", "true");
    tableErrorEl.textContent = msg;
    tableErrorEl.hidden = false;
  }

  function showState(name) {
    stateEmpty.hidden = name !== "empty";
    stateLoading.hidden = name !== "loading";
    stateError.hidden = name !== "error";
    stateResult.hidden = name !== "result";
  }

  function appendCitedBadges(parent, citedRows) {
    if (!Array.isArray(citedRows) || citedRows.length === 0) return;
    const span = document.createElement("span");
    span.className = "cite-tag";
    span.textContent = "[" + citedRows.join(", ") + "]";
    parent.appendChild(span);
  }

  function renderResult(data) {
    document.getElementById("result-role-label").textContent =
      "Briefing for: " + (data.role_label || "");
    document.getElementById("headline-verdict").textContent =
      data.headline_verdict || "";

    const m = data.metrics || {};
    const statsParts = [
      (m.valid_count || 0) + " valid readings",
      (m.flagged_count || 0) + " flagged",
    ];
    if (m.mean_reading !== null && m.mean_reading !== undefined) {
      statsParts.push("Mean: " + m.mean_reading);
    }
    if (m.max_reading !== null && m.max_reading !== undefined) {
      statsParts.push("Peak: " + m.max_reading);
    }
    if (m.mixed_units) {
      statsParts.push("Mixed units detected");
    }
    document.getElementById("metrics-line").textContent = statsParts.join(" · ");

    const trendsList = document.getElementById("trends-list");
    trendsList.textContent = "";
    (data.trends_and_hotspots || []).forEach(function (item) {
      const li = document.createElement("li");
      li.textContent = item.finding || "";
      appendCitedBadges(li, item.cited_rows);
      trendsList.appendChild(li);
    });

    const gapsList = document.getElementById("gaps-list");
    gapsList.textContent = "";
    const gaps = data.data_gaps_summary || [];
    if (gaps.length === 0) {
      const li = document.createElement("li");
      li.textContent = "No data gaps or unreliable readings flagged.";
      gapsList.appendChild(li);
    } else {
      gaps.forEach(function (g) {
        const li = document.createElement("li");
        li.textContent = g.issue || "";
        appendCitedBadges(li, g.cited_rows);
        gapsList.appendChild(li);
      });
    }

    const actionsList = document.getElementById("actions-list");
    actionsList.textContent = "";
    (data.prioritized_actions || []).forEach(function (act) {
      const li = document.createElement("li");
      const strong = document.createElement("strong");
      strong.textContent = act.action || "";
      li.appendChild(strong);
      if (act.reason) {
        const reasonSpan = document.createElement("span");
        reasonSpan.textContent = " — " + act.reason;
        li.appendChild(reasonSpan);
      }
      appendCitedBadges(li, act.cited_rows);
      actionsList.appendChild(li);
    });

    document.getElementById("what-changed-text").textContent =
      data.what_changed || "";

    const unlockedEl = document.getElementById("internal-note-unlocked");
    const lockedEl = document.getElementById("internal-note-locked");
    if (data.is_staff && data.internal_briefing_note) {
      document.getElementById("internal-note-text").textContent =
        data.internal_briefing_note;
      unlockedEl.hidden = false;
      lockedEl.hidden = true;
    } else {
      unlockedEl.hidden = true;
      lockedEl.hidden = false;
    }

    const adv = data.citizen_advisory || {};
    const vg = adv.vulnerable_groups || {};
    document.getElementById("advisory-title").textContent =
      adv.title || "Citizen Advisory";
    document.getElementById("advisory-meta").textContent =
      (adv.language || "") + " · " + (adv.reading_level || "") + " reading level";
    document.getElementById("advisory-general").textContent =
      adv.general_guidance || "";
    document.getElementById("adv-children").textContent = vg.children || "";
    document.getElementById("adv-older").textContent = vg.older_adults || "";
    document.getElementById("adv-sensitive").textContent =
      vg.sensitive_people || "";

    lastAdvisoryText = [
      adv.title || "Citizen Advisory",
      adv.general_guidance || "",
      "Children: " + (vg.children || ""),
      "Older adults: " + (vg.older_adults || ""),
      "Sensitive groups: " + (vg.sensitive_people || ""),
    ].join("\n\n");

    copyStatusEl.textContent = "";
    showState("result");
    outputHeading.focus();
  }

  async function submitBrief() {
    clearFieldError();
    const raw = tableEl.value.trim();
    if (!raw) {
      showFieldError("Please paste or upload an air quality data table.");
      tableEl.focus();
      return;
    }
    if (raw.length > 2000) {
      showFieldError("Data table must be 2,000 characters or fewer.");
      tableEl.focus();
      return;
    }

    submitBtn.disabled = true;
    showState("loading");

    try {
      const resp = await fetch("/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          role: roleEl.value,
          language: langEl.value,
          reading_level: levelEl.value,
          raw_table: raw,
        }),
      });
      const data = await resp.json();
      if (!resp.ok) {
        if (data.field_errors && data.field_errors.raw_table) {
          showFieldError(data.field_errors.raw_table);
          showState("empty");
          tableEl.focus();
          return;
        }
        errorMessageEl.textContent =
          data.error || "The analysis could not run right now. Please try again in a minute.";
        showState("error");
        return;
      }
      renderResult(data);
    } catch (_err) {
      errorMessageEl.textContent =
        "The analysis could not run right now. Please try again in a minute.";
      showState("error");
    } finally {
      submitBtn.disabled = false;
    }
  }

  document.querySelectorAll(".example-chip").forEach(function (btn) {
    btn.addEventListener("click", function () {
      clearFieldError();
      roleEl.value = btn.dataset.role || "ward_officer";
      langEl.value = btn.dataset.language || "English";
      levelEl.value = btn.dataset.readingLevel || "Standard";
      tableEl.value = btn.dataset.table || "";
      updateCharCount();
      tableEl.focus();
    });
  });

  if (fileEl) {
    fileEl.addEventListener("change", function () {
      const file = fileEl.files && fileEl.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = function (ev) {
        const text = String(ev.target.result || "").slice(0, 2000);
        tableEl.value = text;
        clearFieldError();
        updateCharCount();
      };
      reader.readAsText(file);
    });
  }

  tableEl.addEventListener("input", function () {
    clearFieldError();
    updateCharCount();
  });

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    submitBrief();
  });

  clearBtn.addEventListener("click", function () {
    tableEl.value = "";
    if (fileEl) fileEl.value = "";
    clearFieldError();
    updateCharCount();
    showState("empty");
    tableEl.focus();
  });

  retryBtn.addEventListener("click", function () {
    submitBrief();
  });

  copyBtn.addEventListener("click", async function () {
    if (!lastAdvisoryText) return;
    try {
      await navigator.clipboard.writeText(lastAdvisoryText);
      copyStatusEl.textContent = "Advisory copied to clipboard.";
    } catch (_err) {
      copyStatusEl.textContent = "Could not copy automatically; please select and copy the text.";
    }
  });

  updateCharCount();
})();
