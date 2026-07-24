const TRANSFORM_TIMEOUT_MS = 55000;

const state = {
  categories: [],
  presets: [],
  providers: [],
  providerId: "local",
  categoryId: null,
  styleId: null,
  file: null,
  abortController: null,
  profileMode: false,
  lastResultUrl: null,
  lastInputUrl: null,
  usage: {
    jobs: 0,
    tokens: 0,
    usd: 0,
    last: null,
  },
};

const els = {
  errorBanner: document.getElementById("errorBanner"),
  mainHeader: document.getElementById("mainHeader"),
  mainDefault: document.getElementById("mainDefault"),
  mainFooter: document.getElementById("mainFooter"),
  profileRoot: document.getElementById("profileRoot"),
  profileBack: document.getElementById("profileBack"),
  profileChips: document.getElementById("profileChips"),
  profileDropzone: document.getElementById("profileDropzone"),
  profileFileInput: document.getElementById("profileFileInput"),
  profileUploadEmpty: document.getElementById("profileUploadEmpty"),
  profilePreview: document.getElementById("profilePreview"),
  profileRun: document.getElementById("profileRun"),
  profileLoader: document.getElementById("profileLoader"),
  profileLoaderText: document.getElementById("profileLoaderText"),
  profileProgressBar: document.getElementById("profileProgressBar"),
  profilePlaceholder: document.getElementById("profilePlaceholder"),
  profileResult: document.getElementById("profileResult"),
  profileDownload: document.getElementById("profileDownload"),
  profileCompare: document.getElementById("profileCompare"),
  profileResultInput: document.getElementById("profileResultInput"),
  categoryGrid: document.getElementById("categoryGrid"),
  styleGrid: document.getElementById("styleGrid"),
  toUpload: document.getElementById("toUpload"),
  backCategory: document.getElementById("backCategory"),
  stepCategory: document.getElementById("step-category"),
  stepStyle: document.getElementById("step-style"),
  stepUpload: document.getElementById("step-upload"),
  stepResult: document.getElementById("step-result"),
  categoryLabel: document.getElementById("categoryLabel"),
  selectedStyleLabel: document.getElementById("selectedStyleLabel"),
  dropzone: document.getElementById("dropzone"),
  fileInput: document.getElementById("fileInput"),
  previewRow: document.getElementById("previewRow"),
  previewImg: document.getElementById("previewImg"),
  placeField: document.getElementById("placeField"),
  placeInput: document.getElementById("placeInput"),
  seedInput: document.getElementById("seedInput"),
  startJob: document.getElementById("startJob"),
  backStyle: document.getElementById("backStyle"),
  jobStatus: document.getElementById("jobStatus"),
  progressBar: document.getElementById("progressBar"),
  compare: document.getElementById("compare"),
  resultInput: document.getElementById("resultInput"),
  resultOutput: document.getElementById("resultOutput"),
  downloadBtn: document.getElementById("downloadBtn"),
  retryBtn: document.getElementById("retryBtn"),
  newJobBtn: document.getElementById("newJobBtn"),
  jobMeta: document.getElementById("jobMeta"),
  stepIndicator: document.getElementById("stepIndicator"),
  providerSeg: document.getElementById("providerSeg"),
  apiUsageNow: document.getElementById("apiUsageNow"),
  apiUsageSession: document.getElementById("apiUsageSession"),
  footerHint: document.getElementById("footerHint"),
  brandHome: document.getElementById("brandHome"),
};

let bannerTimer = null;

function showError(message) {
  const text = String(message || "알 수 없는 오류가 발생했습니다");
  if (!els.errorBanner) {
    window.alert(text);
    return;
  }
  els.errorBanner.textContent = text;
  els.errorBanner.classList.remove("hidden");
  els.errorBanner.classList.add("is-visible");
  if (bannerTimer) clearTimeout(bannerTimer);
  bannerTimer = setTimeout(hideError, 8000);
}

function hideError() {
  if (!els.errorBanner) return;
  els.errorBanner.classList.add("hidden");
  els.errorBanner.classList.remove("is-visible");
  els.errorBanner.textContent = "";
}

els.errorBanner?.addEventListener("click", hideError);

function showStep(n) {
  state.profileMode = false;
  document.body.classList.remove("profile-mode");
  els.mainHeader.classList.remove("hidden");
  els.mainDefault.classList.remove("hidden");
  els.mainFooter.classList.remove("hidden");
  els.profileRoot.classList.add("hidden");

  els.stepCategory.classList.toggle("active", n === 1);
  els.stepStyle.classList.toggle("active", n === 2);
  els.stepUpload.classList.toggle("active", n === 3);
  els.stepResult.classList.toggle("active", n === 4);
  els.stepIndicator.querySelectorAll("span").forEach((s) => {
    s.classList.toggle("on", Number(s.dataset.step) === n);
  });
}

function showProfileStudio() {
  state.profileMode = true;
  document.body.classList.add("profile-mode");
  els.mainHeader.classList.add("hidden");
  els.mainDefault.classList.add("hidden");
  els.mainFooter.classList.add("hidden");
  els.profileRoot.classList.remove("hidden");
  updateProfileRunState();
}

function selectedCategory() {
  return state.categories.find((c) => c.id === state.categoryId) || null;
}

function selectedPreset() {
  return state.presets.find((p) => p.id === state.styleId) || null;
}

function renderCategories() {
  els.categoryGrid.innerHTML = "";
  state.categories.forEach((c) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "category-card" + (c.id === "person" ? " category-card-profile" : "");
    btn.innerHTML = `
      <span class="emoji">${c.emoji}</span>
      <strong>${c.name}</strong>
      <span class="engine-pill">모델 ${c.engine_label}</span>
      <span>${c.description}</span>
    `;
    btn.addEventListener("click", () => selectCategory(c.id));
    els.categoryGrid.appendChild(btn);
  });
}

async function selectCategory(categoryId) {
  state.categoryId = categoryId;
  state.styleId = null;
  els.toUpload.disabled = true;

  try {
    const res = await fetch(`/api/presets?category=${encodeURIComponent(categoryId)}`);
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      showError(err.detail || `프리셋을 불러오지 못했습니다 (${res.status})`);
      return;
    }
    const data = await res.json();
    state.presets = data.presets || [];
  } catch (e) {
    showError(e.message || "프리셋을 불러오지 못했습니다");
    return;
  }

  if (categoryId === "person") {
    renderProfileChips();
    showProfileStudio();
    return;
  }

  const cat = selectedCategory();
  els.categoryLabel.textContent = cat
    ? `카테고리: ${cat.emoji} ${cat.name} · 모델 ${cat.engine_label}`
    : "카테고리: -";
  showStep(2);
  renderPresets();
}

function renderProfileChips() {
  els.profileChips.innerHTML = "";
  state.presets.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "profile-chip" + (state.styleId === p.id ? " selected" : "");
    btn.textContent = `${p.emoji} ${p.name}`;
    btn.title = p.description;
    btn.addEventListener("click", () => {
      state.styleId = p.id;
      renderProfileChips();
      updateProfileRunState();
    });
    els.profileChips.appendChild(btn);
  });
}

function updateProfileRunState() {
  els.profileRun.disabled = !(state.file && state.styleId);
}

function renderPresets() {
  els.styleGrid.innerHTML = "";
  if (!state.presets.length) {
    els.styleGrid.innerHTML = `<p class="muted">이 카테고리에 스타일이 없습니다.</p>`;
    return;
  }
  state.presets.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "style-card" + (state.styleId === p.id ? " selected" : "");
    btn.innerHTML = `<span class="emoji">${p.emoji}</span><strong>${p.name}</strong><span>${p.description}</span>`;
    btn.addEventListener("click", () => {
      state.styleId = p.id;
      renderPresets();
      els.toUpload.disabled = false;
    });
    els.styleGrid.appendChild(btn);
  });
}

function selectedProvider() {
  return state.providers.find((p) => p.id === state.providerId) || null;
}

function formatTokens(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return Number(n).toLocaleString("ko-KR");
}

function formatUsd(n) {
  if (n == null || Number.isNaN(Number(n))) return null;
  const v = Number(n);
  if (v < 0.01) return `$${v.toFixed(4)}`;
  return `$${v.toFixed(3)}`;
}

function estimateOpenAIUsd(usage) {
  if (!usage) return null;
  if (usage.est_usd != null) return Number(usage.est_usd);
  const textIn = 5;
  const imageIn = 10;
  const imageOut = 40;
  const textTokens = usage.text_tokens;
  const imageTokens = usage.image_tokens;
  const inputTokens = usage.input_tokens;
  const outputTokens = usage.output_tokens || 0;
  if (textTokens == null && imageTokens == null && inputTokens == null) return null;
  let tin = 0;
  let iin = 0;
  if (textTokens != null || imageTokens != null) {
    tin = Number(textTokens || 0);
    iin = Number(imageTokens || 0);
  } else {
    iin = Number(inputTokens || 0);
  }
  return (tin / 1e6) * textIn + (iin / 1e6) * imageIn + (Number(outputTokens) / 1e6) * imageOut;
}

function updateUsagePanel(lastOverride) {
  const p = selectedProvider();
  const last = lastOverride || state.usage.last;
  if (els.apiUsageNow) {
    if (last && last.provider === state.providerId) {
      if (last.total_tokens != null || last.input_tokens != null) {
        const parts = [];
        if (last.total_tokens != null) parts.push(`합계 ${formatTokens(last.total_tokens)}`);
        if (last.input_tokens != null) parts.push(`입력 ${formatTokens(last.input_tokens)}`);
        if (last.output_tokens != null) parts.push(`출력 ${formatTokens(last.output_tokens)}`);
        const usd = estimateOpenAIUsd(last);
        let line = `방금 · ${parts.join(" · ")}`;
        if (usd != null) line += ` · 약 ${formatUsd(usd)}`;
        els.apiUsageNow.textContent = line;
      } else if (last.est_usd_per_image != null) {
        els.apiUsageNow.textContent = `방금 약 $${Number(last.est_usd_per_image).toFixed(2)} 상당 · ${last.note || "장당 과금"}`;
      } else if (last.note) {
        els.apiUsageNow.textContent = last.note;
      } else {
        els.apiUsageNow.textContent = p?.cost_hint || "사용량 정보 없음";
      }
    } else {
      els.apiUsageNow.textContent = p
        ? `${p.name} · ${p.cost_hint || "사용량 정보 없음"}`
        : "API를 선택하면 예상 과금이 표시됩니다";
    }
  }
  if (els.apiUsageSession) {
    const usdPart = state.usage.usd > 0 ? ` · 약 ${formatUsd(state.usage.usd)}` : "";
    els.apiUsageSession.textContent =
      `세션 · ${state.usage.jobs}장 · 토큰 ${formatTokens(state.usage.tokens)}${usdPart}`;
  }
}

function recordUsage(provider, usage) {
  const last = {
    provider,
    ...(usage || {}),
  };
  if (provider === "openai" && last.est_usd == null) {
    const est = estimateOpenAIUsd(last);
    if (est != null) last.est_usd = est;
  }
  state.usage.jobs += 1;
  if (typeof usage?.total_tokens === "number") {
    state.usage.tokens += usage.total_tokens;
  }
  if (typeof last.est_usd === "number") {
    state.usage.usd += last.est_usd;
  } else if (typeof last.est_usd_per_image === "number") {
    state.usage.usd += Number(last.est_usd_per_image);
  }
  state.usage.last = last;
  updateUsagePanel(last);
}

async function loadProviders() {
  const res = await fetch("/api/providers");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    showError(err.detail || `API 목록을 불러오지 못했습니다 (${res.status})`);
    return;
  }
  const data = await res.json();
  state.providers = data.providers || [];
  if (data.default) state.providerId = data.default;
  if (!els.providerSeg) return;

  const shortName = {
    local: "Local",
    fal: "Fal",
    openai: "OpenAI",
  };

  const ready = state.providers.find((p) => p.id === state.providerId && p.ready)
    || state.providers.find((p) => p.ready);
  if (ready) state.providerId = ready.id;

  els.providerSeg.innerHTML = "";
  state.providers.forEach((p) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "api-chip" + (p.id === state.providerId ? " on" : "");
    btn.dataset.provider = p.id;
    btn.disabled = !p.ready;
    btn.title = p.ready
      ? (p.cost_hint || p.recommended_for || p.description || p.name)
      : `${p.name} — API 키 필요`;
    btn.innerHTML = `<span>${shortName[p.id] || p.name}</span>`;
    if (!p.ready) btn.innerHTML += `<em>off</em>`;
    btn.addEventListener("click", () => {
      if (!p.ready) return;
      state.providerId = p.id;
      els.providerSeg.querySelectorAll(".api-chip").forEach((c) => {
        c.classList.toggle("on", c.dataset.provider === state.providerId);
      });
      updateUsagePanel();
    });
    els.providerSeg.appendChild(btn);
  });

  updateUsagePanel();
  if (els.footerHint) {
    const names = state.providers.map((p) => `${p.name}${p.ready ? "" : "✗"}`).join(" · ");
    els.footerHint.textContent = `${names} · 작업은 한 장씩`;
  }
}

async function loadBootstrap() {
  await loadProviders();
  const res = await fetch("/api/presets");
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `카테고리를 불러오지 못했습니다 (${res.status})`);
  }
  const data = await res.json();
  state.categories = data.categories || [];
  renderCategories();
}

function validateImageFile(file) {
  if (!file) return false;
  if (!/^image\/(jpeg|png|webp)/i.test(file.type) && !/\.(jpe?g|png|webp)$/i.test(file.name)) {
    showError("JPEG / PNG / WebP 만 지원합니다");
    return false;
  }
  if (file.size > 12 * 1024 * 1024) {
    showError("파일이 너무 큽니다 (최대 12MB)");
    return false;
  }
  return true;
}

function setFile(file) {
  if (!validateImageFile(file)) return;
  state.file = file;
  const url = URL.createObjectURL(file);
  els.previewImg.src = url;
  els.previewRow.classList.remove("hidden");
}

function setProfileFile(file) {
  if (!validateImageFile(file)) return;
  state.file = file;
  const url = URL.createObjectURL(file);
  els.profilePreview.src = url;
  els.profilePreview.classList.remove("hidden");
  els.profileUploadEmpty.classList.add("hidden");
  els.profileResult.classList.add("hidden");
  els.profilePlaceholder.classList.remove("hidden");
  els.profileDownload.classList.add("hidden");
  els.profileCompare.classList.add("hidden");
  updateProfileRunState();
}

function wireDropzone(zone, input, onFile) {
  zone.addEventListener("click", () => input.click());
  input.addEventListener("change", () => onFile(input.files?.[0]));
  ["dragenter", "dragover"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.add("drag");
    });
  });
  ["dragleave", "drop"].forEach((ev) => {
    zone.addEventListener(ev, (e) => {
      e.preventDefault();
      zone.classList.remove("drag");
    });
  });
  zone.addEventListener("drop", (e) => onFile(e.dataTransfer.files?.[0]));
}

wireDropzone(els.dropzone, els.fileInput, setFile);
wireDropzone(els.profileDropzone, els.profileFileInput, setProfileFile);

els.backCategory.addEventListener("click", () => {
  state.styleId = null;
  els.toUpload.disabled = true;
  showStep(1);
});

els.profileBack.addEventListener("click", () => {
  if (state.abortController) state.abortController.abort();
  state.styleId = null;
  state.file = null;
  els.profileFileInput.value = "";
  els.profilePreview.classList.add("hidden");
  els.profileUploadEmpty.classList.remove("hidden");
  showStep(1);
});

els.toUpload.addEventListener("click", () => {
  const p = selectedPreset();
  const c = selectedCategory();
  if (!p || !c) {
    showError("스타일을 먼저 선택해 주세요");
    return;
  }
  els.selectedStyleLabel.textContent = `선택한 스타일: ${c.emoji} ${c.name} · ${p.emoji} ${p.name}`;
  els.placeField.classList.toggle("hidden", !p.needs_place);
  showStep(3);
});

els.backStyle.addEventListener("click", () => showStep(2));

els.newJobBtn.addEventListener("click", () => {
  if (state.abortController) state.abortController.abort();
  state.file = null;
  state.styleId = null;
  els.fileInput.value = "";
  els.previewRow.classList.add("hidden");
  els.compare.classList.add("hidden");
  els.downloadBtn.classList.add("hidden");
  els.retryBtn.classList.add("hidden");
  els.jobMeta.classList.add("hidden");
  els.progressBar.style.width = "0%";
  els.toUpload.disabled = true;
  showStep(1);
});

function goHome(e) {
  if (e) e.preventDefault();
  if (state.abortController) state.abortController.abort();
  hideError();
  state.file = null;
  state.styleId = null;
  state.categoryId = null;
  if (els.fileInput) els.fileInput.value = "";
  if (els.profileFileInput) els.profileFileInput.value = "";
  els.previewRow?.classList.add("hidden");
  els.compare?.classList.add("hidden");
  els.downloadBtn?.classList.add("hidden");
  els.retryBtn?.classList.add("hidden");
  els.jobMeta?.classList.add("hidden");
  if (els.progressBar) els.progressBar.style.width = "0%";
  if (els.toUpload) els.toUpload.disabled = true;
  els.profilePreview?.classList.add("hidden");
  els.profileUploadEmpty?.classList.remove("hidden");
  els.profileResult?.classList.add("hidden");
  els.profilePlaceholder?.classList.remove("hidden");
  els.profileDownload?.classList.add("hidden");
  els.profileCompare?.classList.add("hidden");
  showStep(1);
}

els.brandHome?.addEventListener("click", goHome);
els.retryBtn.addEventListener("click", () => {
  if (state.file) startJob();
  else showStep(3);
});

function detailFromErrorBody(err) {
  if (!err) return null;
  if (typeof err.detail === "string") return err.detail;
  if (Array.isArray(err.detail)) {
    return err.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
  }
  if (err.message) return err.message;
  return null;
}

async function transformImage(onProgress) {
  const p = selectedPreset();
  if (!state.file) {
    showError("사진을 먼저 업로드해 주세요");
    return null;
  }
  if (!p && !state.styleId) {
    showError("스타일을 먼저 선택해 주세요");
    return null;
  }

  const styleId = p?.id || state.styleId;
  const preset = p || state.presets.find((x) => x.id === styleId);

  const fd = new FormData();
  fd.append("style_id", styleId);
  fd.append("image", state.file, state.file.name || "upload.jpg");
  fd.append("provider", state.providerId || "local");
  if (preset?.needs_place) fd.append("place", els.placeInput?.value?.trim() || "");
  const seedRaw = els.seedInput?.value?.trim();
  if (seedRaw) fd.append("seed", seedRaw);

  if (state.abortController) state.abortController.abort();
  const controller = new AbortController();
  state.abortController = controller;
  const timer = setTimeout(() => controller.abort(), TRANSFORM_TIMEOUT_MS);

  if (onProgress) onProgress({ status: "running", progress: 15 });

  try {
    const res = await fetch("/api/transform", {
      method: "POST",
      body: fd,
      signal: controller.signal,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      const msg = detailFromErrorBody(err) || res.statusText || `서버 오류 (${res.status})`;
      showError(msg);
      if (onProgress) onProgress({ failed: true, error: msg });
      return null;
    }

    const data = await res.json();
    if (!data.ok || !data.image_base64) {
      const msg = data.detail || "변환 결과가 비어 있습니다";
      showError(msg);
      if (onProgress) onProgress({ failed: true, error: msg });
      return null;
    }

    const mime = data.mime || "image/png";
    const resultUrl = `data:${mime};base64,${data.image_base64}`;
    const inputUrl = URL.createObjectURL(state.file);
    state.lastResultUrl = resultUrl;
    state.lastInputUrl = inputUrl;

    const usage = data.usage || (data.meta && data.meta.usage) || {};
    recordUsage(data.provider || state.providerId, usage);

    const done = {
      status: "done",
      progress: 100,
      resultUrl,
      inputUrl,
      elapsed_sec: data.elapsed_sec,
      meta: data.meta,
      usage,
      provider: data.provider || state.providerId,
    };
    if (onProgress) onProgress(done);
    return done;
  } catch (e) {
    if (e?.name === "AbortError") {
      const msg = "요청 시간이 초과되었습니다. 잠시 후 다시 시도해 주세요. (약 55초)";
      showError(msg);
      if (onProgress) onProgress({ failed: true, error: msg });
      return null;
    }
    const msg = e?.message || "네트워크 오류가 발생했습니다";
    showError(msg);
    if (onProgress) onProgress({ failed: true, error: msg });
    return null;
  } finally {
    clearTimeout(timer);
    if (state.abortController === controller) state.abortController = null;
  }
}

async function startJob() {
  if (!state.file) {
    showError("사진을 먼저 업로드해 주세요");
    return;
  }
  if (!state.styleId) {
    showError("스타일을 먼저 선택해 주세요");
    return;
  }

  showStep(4);
  hideError();
  els.compare.classList.add("hidden");
  els.downloadBtn.classList.add("hidden");
  els.retryBtn.classList.add("hidden");
  els.jobMeta.classList.add("hidden");
  els.progressBar.style.width = "8%";
  els.jobStatus.textContent = "변환 요청 중…";

  await transformImage((j) => {
    if (j.failed) {
      els.jobStatus.textContent = `실패: ${j.error}`;
      els.retryBtn.classList.remove("hidden");
      els.progressBar.style.width = "100%";
      return;
    }
    if (j.status === "running") {
      els.progressBar.style.width = `${j.progress || 20}%`;
      els.jobStatus.textContent = "AI가 변환하는 중…";
    }
    if (j.status === "done") {
      els.progressBar.style.width = "100%";
      els.jobStatus.textContent = j.elapsed_sec ? `완료 · ${j.elapsed_sec}s` : "완료";
      els.compare.classList.remove("hidden");
      els.resultInput.src = j.inputUrl;
      els.resultOutput.src = j.resultUrl;
      els.downloadBtn.href = j.resultUrl;
      els.downloadBtn.classList.remove("hidden");
      els.retryBtn.classList.remove("hidden");
      if (j.meta) {
        els.jobMeta.classList.remove("hidden");
        els.jobMeta.textContent = JSON.stringify(j.meta, null, 2);
      }
    }
  });
}

els.startJob.addEventListener("click", startJob);

els.profileRun.addEventListener("click", async () => {
  if (!state.file) {
    showError("사진을 먼저 업로드해 주세요");
    return;
  }
  if (!state.styleId) {
    showError("스타일을 먼저 선택해 주세요");
    return;
  }

  hideError();
  els.profileRun.disabled = true;
  els.profileLoader.classList.remove("hidden");
  els.profilePlaceholder.classList.add("hidden");
  els.profileResult.classList.add("hidden");
  els.profileDownload.classList.add("hidden");
  els.profileCompare.classList.add("hidden");
  els.profileProgressBar.style.width = "8%";
  els.profileLoaderText.textContent = "변환 요청 중…";

  await transformImage((j) => {
    if (j.failed) {
      els.profileLoader.classList.add("hidden");
      els.profilePlaceholder.classList.remove("hidden");
      els.profileLoaderText.textContent = `실패: ${j.error}`;
      updateProfileRunState();
      return;
    }
    if (j.status === "running") {
      els.profileProgressBar.style.width = `${j.progress || 20}%`;
      els.profileLoaderText.textContent = "AI가 만드는 중…";
    }
    if (j.status === "done") {
      els.profileLoader.classList.add("hidden");
      els.profileResult.src = j.resultUrl;
      els.profileResult.classList.remove("hidden");
      els.profileDownload.href = j.resultUrl;
      els.profileDownload.classList.remove("hidden");
      els.profileResultInput.src = j.inputUrl;
      els.profileCompare.classList.remove("hidden");
      els.profileLoaderText.textContent = j.elapsed_sec ? `완료 · ${j.elapsed_sec}s` : "완료";
      updateProfileRunState();
    }
  });

  updateProfileRunState();
});

loadBootstrap().catch((e) => {
  showError(e.message || "초기 로드 실패");
  els.categoryGrid.innerHTML = `<p style="color:#5c534c">로드 실패: ${e.message}</p>`;
});
