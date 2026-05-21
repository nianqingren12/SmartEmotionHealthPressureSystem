const BASE_URL = "http://localhost:8000";

const AppState = {
  token: localStorage.getItem("microExpressionToken") || "",
  currentUser: null,
  dashboard: null,
  stream: null,
  authMode: "login",
  pendingPlan: null,
  assessmentAnswers: {},
  currentAssessment: null,
  lastAssessment: null,
  liveSessionId: null,
  liveInterval: null,
};

function showToast(message, type = "info") {
  let container = document.querySelector(".toast-container");
  if (!container) {
    container = document.createElement("div");
    container.className = "toast-container";
    document.body.appendChild(container);
  }

  const icons = {
    success: "✓",
    error: "✕",
    warning: "⚠",
    info: "ℹ"
  };

  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || icons.info}</span>
    <span class="toast-message">${escapeHtml(message)}</span>
  `;

  container.appendChild(toast);

  setTimeout(() => {
    toast.style.animation = "slideOut 0.3s ease forwards";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

function showLoading(button, text = "加载中...") {
  if (!button) return;
  button.disabled = true;
  button.dataset.originalText = button.textContent;
  button.innerHTML = `<span class="loading-spinner"></span>${text}`;
  button.classList.add("loading");
}

function hideLoading(button) {
  if (!button) return;
  button.disabled = false;
  button.innerHTML = button.dataset.originalText || "确定";
  button.classList.remove("loading");
}

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (AppState.token) {
    headers.Authorization = `Bearer ${AppState.token}`;
  }
  const fullUrl = path.startsWith("http") ? path : `${BASE_URL}${path}`;
  const response = await fetch(fullUrl, { ...options, headers });
  let payload = {};
  try {
    payload = await response.json();
  } catch {
    payload = {};
  }
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || "请求失败");
  }
  return payload;
}

function persistToken(token) {
  AppState.token = token || "";
  if (AppState.token) {
    localStorage.setItem("microExpressionToken", AppState.token);
  } else {
    localStorage.removeItem("microExpressionToken");
  }
}

function setAuthUI() {
  const loginBtns = document.querySelectorAll(".require-auth");
  const logoutBtn = document.getElementById("logoutBtn");

  if (AppState.token && AppState.currentUser) {
    document.querySelectorAll(".auth-status-text").forEach(el => {
      el.textContent = `已登录：${AppState.currentUser.email}`;
    });
    document.querySelectorAll(".membership-tier").forEach(el => {
      el.textContent = AppState.currentUser.membership_tier || "Free";
    });
    document.querySelectorAll(".report-credits").forEach(el => {
      el.textContent = AppState.currentUser.report_credits || 0;
    });
  } else {
    document.querySelectorAll(".auth-status-text").forEach(el => {
      el.textContent = "未登录";
    });
  }
}

async function checkSystemHealth() {
  try {
    const data = await request("/api/system/health", { method: "GET" });
    const engineEl = document.getElementById("engine-status");
    if (engineEl) {
      engineEl.textContent = data.model_loaded ? `${data.engine} (REAL)` : "Demo Engine";
      engineEl.style.color = data.model_loaded ? "#00c8b4" : "#ffb84d";
    }
  } catch (err) {
    console.error("System health check failed");
  }
}

async function loadUserOverview() {
  checkSystemHealth();
  if (!AppState.token) {
    AppState.currentUser = null;
    setAuthUI();
    return;
  }
  try {
    const user = await request("/api/auth/me", { method: "GET" });
    AppState.currentUser = user;
    setAuthUI();
  } catch (err) {
    console.error("Failed to load user overview");
    persistToken("");
  }
}

async function refreshAuthenticatedData() {
  await loadUserOverview();
  if (!AppState.token) return;
  try {
    const dashboard = await request("/api/dashboard/overview", { method: "GET" });
    AppState.dashboard = dashboard;
  } catch (err) {
    console.error("Failed to load dashboard data");
  }
}

function navigateTo(page) {
  const pageMap = {
    dashboard: "/index.html",
    detection: "/pages/detection.html",
    profile: "/pages/profile.html",
    history: "/pages/history.html",
    membership: "/pages/membership.html",
    services: "/pages/services.html"
  };

  if (pageMap[page]) {
    window.location.href = BASE_URL + pageMap[page];
  }
}

function highlightElement(element) {
  if (!element) return;
  element.classList.add("highlight");
  setTimeout(() => element.classList.remove("highlight"), 800);
}

function renderEmotionBars(container, distribution = {}) {
  if (!container) return;
  const entries = Object.entries(distribution);
  if (!entries.length) {
    container.innerHTML = '<div class="empty-state"><p class="text-muted">暂无识别数据</p></div>';
    return;
  }
  const max = Math.max(...entries.map(([, count]) => count), 1);
  container.innerHTML = entries
    .map(([label, count]) => {
      const percent = Math.round((count / max) * 100);
      return `
        <div class="emotion-bar">
          <div class="emotion-bar-header">
            <span>${escapeHtml(label)}</span>
            <span class="text-muted">${count} 次</span>
          </div>
          <div class="emotion-bar-track">
            <div class="emotion-bar-fill" style="width:${percent}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderHistoryList(container, records = []) {
  if (!container) return;
  if (!records.length) {
    container.innerHTML = '<div class="empty-state"><p class="text-muted">暂无记录</p></div>';
    return;
  }
  container.innerHTML = records
    .map(
      (record) => `
        <div class="history-item">
          <div class="history-item-header">
            <span class="history-item-title">${escapeHtml(record.label || record.title || "记录")}</span>
            <span class="history-item-meta">${escapeHtml(record.created_at || "")}</span>
          </div>
          <div class="history-item-body">
            ${escapeHtml(record.summary || record.description || record.message || "")}
          </div>
        </div>
      `
    )
    .join("");
}

function renderWaveChart(container, wave = []) {
  if (!container) return;
  if (!wave || !wave.length) {
    container.innerHTML = '<div class="empty-state"><p class="text-muted">暂无波动数据</p></div>';
    return;
  }
  container.innerHTML = wave
    .map(
      (item) => `
        <div class="wave-bar">
          <div class="wave-bar-header">
            <span class="wave-bar-label">片段 ${item.index || item.label || ""}</span>
            <span class="wave-bar-value">${item.value || ""}</span>
          </div>
          <div class="wave-bar-track">
            <div class="wave-bar-fill" style="width:${Math.max(6, Math.min(100, item.value || 50))}%"></div>
          </div>
        </div>
      `
    )
    .join("");
}

function renderPlansGrid(container, plans = []) {
  if (!container) return;
  if (!plans.length) {
    container.innerHTML = '<div class="empty-state"><p class="text-muted">暂无套餐信息</p></div>';
    return;
  }
  container.innerHTML = plans
    .map(
      (plan, index) => `
        <div class="plan-card ${index === 1 ? "featured" : ""}">
          <div class="plan-name">${escapeHtml(plan.name)}</div>
          <div class="plan-price">¥${escapeHtml(plan.price)}<span>/${plan.duration || "月"}</span></div>
          <ul class="plan-features">
            ${(plan.rights || plan.features || []).map((right) => `<li>${escapeHtml(right)}</li>`).join("")}
          </ul>
          <button class="btn btn-primary" onclick="buyPlan('${escapeHtml(plan.name)}')">立即开通</button>
        </div>
      `
    )
    .join("");
}

function renderCoursesGrid(container, courses = []) {
  if (!container) return;
  if (!courses.length) {
    container.innerHTML = '<div class="empty-state"><p class="text-muted">暂无课程信息</p></div>';
    return;
  }
  container.innerHTML = courses
    .map(
      (course) => `
        <div class="course-card">
          <span class="course-type">${escapeHtml(course.type || "课程")}</span>
          <h3 class="course-title">${escapeHtml(course.title)}</h3>
          <p class="course-desc">${escapeHtml(course.description || "")}</p>
          <div class="course-footer">
            <span class="course-price">${escapeHtml(course.price || "免费")}</span>
            <button class="btn btn-secondary btn-sm" onclick="buyCourse('${escapeHtml(course.title)}')">立即咨询</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function buyPlan(planName) {
  if (!AppState.token) {
    showToast("请先登录", "warning");
    return;
  }
  try {
    const plans = await request("/api/membership/plans", { method: "GET" });
    const plan = plans.find((p) => p.name === planName);
    if (plan) {
      AppState.pendingPlan = planName;
      const payPlanName = document.getElementById("payPlanName");
      const payPlanAmount = document.getElementById("payPlanAmount");
      const paymentModal = document.getElementById("paymentModal");
      if (payPlanName) payPlanName.textContent = plan.name;
      if (payPlanAmount) payPlanAmount.textContent = plan.price;
      if (paymentModal) {
        paymentModal.classList.add("active");
      }
    }
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function buyCourse(courseTitle) {
  if (!AppState.token) {
    showToast("请先登录", "warning");
    return;
  }
  showToast(`已提交"${courseTitle}"的咨询请求`, "success");
}

async function startCamera(videoElement) {
  if (AppState.stream) return;
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    AppState.stream = stream;
    if (videoElement) {
      videoElement.srcObject = stream;
    }
    showToast("摄像头已开启", "success");
  } catch (error) {
    console.error("Camera start failed:", error);
    if (error.name === "NotAllowedError") {
      showToast("摄像头权限被拒绝", "error");
    } else if (error.name === "NotFoundError") {
      showToast("未检测到摄像头设备", "error");
    } else {
      showToast(`摄像头启动失败: ${error.message}`, "error");
    }
    throw error;
  }
}

function stopCamera() {
  if (AppState.stream) {
    AppState.stream.getTracks().forEach((track) => track.stop());
    AppState.stream = null;
  }
}

async function captureFrame(videoElement, canvasElement) {
  if (!videoElement || !canvasElement) return null;
  const video = videoElement;
  const canvas = canvasElement;
  const width = video.videoWidth || 640;
  const height = video.videoHeight || 480;
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(video, 0, 0, width, height);
  return canvas.toDataURL("image/jpeg", 0.92);
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function logout() {
  persistToken("");
  stopCamera();
  AppState.currentUser = null;
  AppState.dashboard = null;
  showToast("已安全退出", "info");
  setAuthUI();
  if (window.location.pathname !== "/index.html" && window.location.pathname !== "/") {
    window.location.href = BASE_URL + "/index.html";
  }
}

window.AppState = AppState;
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.escapeHtml = escapeHtml;
window.request = request;
window.persistToken = persistToken;
window.loadUserOverview = loadUserOverview;
window.refreshAuthenticatedData = refreshAuthenticatedData;
window.navigateTo = navigateTo;
window.highlightElement = highlightElement;
window.renderEmotionBars = renderEmotionBars;
window.renderHistoryList = renderHistoryList;
window.renderWaveChart = renderWaveChart;
window.renderPlansGrid = renderPlansGrid;
window.renderCoursesGrid = renderCoursesGrid;
window.buyPlan = buyPlan;
window.buyCourse = buyCourse;
window.startCamera = startCamera;
window.stopCamera = stopCamera;
window.captureFrame = captureFrame;
window.readFileAsDataUrl = readFileAsDataUrl;
window.logout = logout;
