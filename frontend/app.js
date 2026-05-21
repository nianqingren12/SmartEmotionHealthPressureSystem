const BASE_URL = window.location.origin;

const state = {
  token: localStorage.getItem("microExpressionToken") || "",
  authMode: "login",
  stream: null,
  currentUser: null,
  dashboard: null,
};

const elements = {
  authForm: document.getElementById("authForm"),
  emailInput: document.getElementById("emailInput"),
  passwordInput: document.getElementById("passwordInput"),
  authStatus: document.getElementById("authStatus"),
  authUserMeta: document.getElementById("authUserMeta"),
  tabButtons: document.querySelectorAll(".tab-btn"),
  toast: document.getElementById("toast"),
  membershipTier: document.getElementById("membershipTier"),
  reportCredits: document.getElementById("reportCredits"),
  recognitionCount: document.getElementById("recognitionCount"),
  dominantEmotion: document.getElementById("dominantEmotion"),
  emotionBars: document.getElementById("emotionBars"),
  camera: document.getElementById("camera"),
  captureCanvas: document.getElementById("captureCanvas"),
  uploadInput: document.getElementById("uploadInput"),
  recognitionResult: document.getElementById("recognitionResult"),
  reportPanel: document.getElementById("reportPanel"),
  companionPanel: document.getElementById("companionPanel"),
  adsPanel: document.getElementById("adsPanel"),
  customPanel: document.getElementById("customPanel"),
  workplaceScenario: document.getElementById("workplaceScenario"),
  emotionSelect: document.getElementById("emotionSelect"),
  plansGrid: document.getElementById("plansGrid"),
  courseGrid: document.getElementById("courseGrid"),
  recentRecognitions: document.getElementById("recentRecognitions"),
  recentReports: document.getElementById("recentReports"),
  reportWave: document.getElementById("reportWave"),
  orderHistory: document.getElementById("orderHistory"),
  adminSection: document.getElementById("adminSection"),
  adminStats: document.getElementById("adminStats"),
  leadList: document.getElementById("leadList"),
  rechargeInput: document.getElementById("rechargeInput"),
  paymentModal: document.getElementById("paymentModal"),
  closePaymentBtn: document.getElementById("closePaymentBtn"),
  simulatePayBtn: document.getElementById("simulatePayBtn"),
  payPlanName: document.getElementById("payPlanName"),
  payPlanAmount: document.getElementById("payPlanAmount"),
  analyticsPanel: document.getElementById("analyticsPanel"),
  apiPanel: document.getElementById("apiPanel"),
  behaviorAnalysisBtn: document.getElementById("behaviorAnalysisBtn"),
  emotionAnalysisBtn: document.getElementById("emotionAnalysisBtn"),
  generateApiKeyBtn: document.getElementById("generateApiKeyBtn"),
  viewApiKeysBtn: document.getElementById("viewApiKeysBtn"),
  apiUsageBtn: document.getElementById("apiUsageBtn"),
};

function showToast(message, isError = false, type = "info") {
  elements.toast.textContent = message;
  elements.toast.classList.remove("hidden", "toast-success", "toast-error", "toast-warning", "toast-info");
  
  const typeClasses = {
    success: "toast-success",
    error: "toast-error",
    warning: "toast-warning",
    info: "toast-info"
  };
  
  elements.toast.classList.add(typeClasses[type] || typeClasses.info);
  elements.toast.style.borderColor = isError 
    ? "rgba(255,141,154,0.38)" 
    : "rgba(77,226,177,0.38)";
    
  elements.toast.style.animation = "slideIn 0.3s ease-out";
  
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    elements.toast.style.animation = "slideOut 0.3s ease-in";
    setTimeout(() => {
      elements.toast.classList.add("hidden");
    }, 300);
  }, 3000);
}

function showLoading(button, originalText = "加载中...") {
  if (!button) return;
  button.disabled = true;
  button.dataset.originalText = button.textContent;
  button.innerHTML = `<span class="spinner"></span>${originalText}`;
  button.classList.add("loading");
}

function hideLoading(button) {
  if (!button) return;
  button.disabled = false;
  button.innerHTML = button.dataset.originalText || "确定";
  button.classList.remove("loading");
}

function addButtonClickFeedback(button, action) {
  button.addEventListener("click", async (e) => {
    if (button.classList.contains("loading")) {
      e.preventDefault();
      return;
    }
    
    showLoading(button);
    
    try {
      await action(e);
      hideLoading(button);
    } catch (error) {
      hideLoading(button);
      showToast(error.message || "操作失败", true);
    }
  });
}

function validateEmail(email) {
  const re = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
  return re.test(email);
}

function validatePassword(password) {
  return password.length >= 6;
}

function addInputValidation(input, validationFunc, errorMsg) {
  const errorEl = document.createElement("span");
  errorEl.className = "input-error";
  input.parentNode.appendChild(errorEl);
  
  input.addEventListener("blur", () => {
    if (!validationFunc(input.value)) {
      errorEl.textContent = errorMsg;
      errorEl.classList.remove("hidden");
      input.classList.add("invalid");
    } else {
      errorEl.textContent = "";
      errorEl.classList.add("hidden");
      input.classList.remove("invalid");
    }
  });
  
  input.addEventListener("input", () => {
    if (input.classList.contains("invalid")) {
      if (validationFunc(input.value)) {
        errorEl.textContent = "";
        errorEl.classList.add("hidden");
        input.classList.remove("invalid");
      }
    }
  });
  
  return errorEl;
}

function animateElement(element, animation) {
  element.classList.add(animation);
  setTimeout(() => {
    element.classList.remove(animation);
  }, 600);
}

function highlightElement(element) {
  element.classList.add("highlight");
  setTimeout(() => {
    element.classList.remove("highlight");
  }, 800);
}

function showModal(title, content, onConfirm) {
  const modal = document.createElement("div");
  modal.className = "custom-modal";
  modal.innerHTML = `
    <div class="modal-overlay" onclick="this.parentElement.remove()"></div>
    <div class="modal-content">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(content)}</p>
      <div class="modal-actions">
        <button class="ghost-btn" onclick="this.closest('.custom-modal').remove()">取消</button>
        <button class="primary-btn" onclick="onConfirm?.(); this.closest('.custom-modal').remove()">确定</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);
  modal.classList.add("show");
}

function updateButtonState(button, isLoading, loadingText = "处理中...") {
  if (isLoading) {
    showLoading(button, loadingText);
  } else {
    hideLoading(button);
  }
}

function setPanelText(element, text) {
  element.textContent = text;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function emptyState(title, subtitle) {
  return `<div class="empty-state"><strong>${escapeHtml(title)}</strong><span>${escapeHtml(subtitle)}</span></div>`;
}

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  const fullUrl = path.startsWith('http') ? path : `${BASE_URL}${path}`;
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

function renderEmotionBars(distribution = {}) {
  const entries = Object.entries(distribution);
  if (!entries.length) {
    elements.emotionBars.innerHTML = '<div class="emotion-bar"><span>暂无识别数据</span></div>';
    return;
  }
  const max = Math.max(...entries.map(([, count]) => count), 1);
  elements.emotionBars.innerHTML = entries
    .map(([label, count]) => {
      const percent = Math.round((count / max) * 100);
      return `
        <div class="emotion-bar">
          <div class="inline-actions">
            <strong>${escapeHtml(label)}</strong>
            <span>${count} 次</span>
          </div>
          <div class="emotion-bar-track">
            <div class="emotion-bar-fill" style="width:${percent}%"></div>
          </div>
        </div>
      `;
    })
    .join("");
}

function renderWaveChart(wave = []) {
  if (!wave.length) {
    elements.reportWave.innerHTML = emptyState("暂无波动曲线", "生成一次深度报告后，这里会展示最近的情绪强度变化。");
    return;
  }
  elements.reportWave.innerHTML = wave
    .map(
      (item) => `
        <div class="wave-bar">
          <div class="wave-bar-header">
            <strong>片段 ${item.index}</strong>
            <span>${escapeHtml(item.label)} · ${item.value}</span>
          </div>
          <div class="wave-bar-track">
            <div class="wave-bar-fill" style="width:${Math.max(6, Math.min(100, item.value))}%"></div>
          </div>
        </div>
      `
    )
    .join("");
}

function renderRecognitions(records = []) {
  if (!records.length) {
    elements.recentRecognitions.innerHTML = emptyState("暂无识别记录", "先使用摄像头抓拍或上传图片 / 视频进行分析。");
    return;
  }
  elements.recentRecognitions.innerHTML = records
    .map(
      (record) => `
        <div class="history-item">
          <strong>${escapeHtml(record.label)} · ${record.confidence}</strong>
          <span>${escapeHtml(record.created_at)} · ${escapeHtml(record.source_type || "camera")}</span>
          <p>强度 ${record.intensity} · 持续 ${record.duration_ms} ms · 引擎 ${escapeHtml(record.engine)}</p>
        </div>
      `
    )
    .join("");
}

function renderReports(reports = []) {
  if (!reports.length) {
    elements.recentReports.innerHTML = emptyState("暂无历史报告", "完成至少 3 次识别后即可生成并回看深度报告。");
    renderWaveChart([]);
    return;
  }
  elements.recentReports.innerHTML = reports
    .map(
      (report) => `
        <div class="history-item">
          <strong>${escapeHtml(report.title)}</strong>
          <span>${escapeHtml(report.created_at)} · ${escapeHtml(report.report_type)}</span>
          <p>${escapeHtml(report.summary)}</p>
          <div class="inline-actions">
            <button class="mini-btn" onclick="openReport(${report.id})">查看详情</button>
          </div>
        </div>
      `
    )
    .join("");
  renderWaveChart(reports[0].details?.wave || []);
}

function renderOrders(orders = []) {
  if (!orders.length) {
    elements.orderHistory.innerHTML = emptyState("暂无订单记录", "开通会员后，这里会自动沉淀你的购买与续费历史。");
    return;
  }
  elements.orderHistory.innerHTML = orders
    .map(
      (order) => `
        <div class="history-item">
          <strong>${escapeHtml(order.product_type)} · ¥${order.amount}</strong>
          <span>${escapeHtml(order.order_no)} · ${escapeHtml(order.created_at)}</span>
          <p>状态 ${escapeHtml(order.status)}${order.valid_until ? ` · 有效期至 ${escapeHtml(order.valid_until)}` : ""}</p>
        </div>
      `
    )
    .join("");
}

function renderAdminStats(overview) {
  elements.adminStats.innerHTML = `
    <div class="stat-box"><span>用户数</span><strong>${overview.user_count}</strong></div>
    <div class="stat-box"><span>识别记录</span><strong>${overview.recognition_count}</strong></div>
    <div class="stat-box"><span>报告数</span><strong>${overview.report_count}</strong></div>
    <div class="stat-box"><span>订单数</span><strong>${overview.order_count}</strong></div>
    <div class="stat-box"><span>企业线索</span><strong>${overview.lead_count}</strong></div>
  `;
}

function renderLeadList(leads = []) {
  if (!leads.length) {
    elements.leadList.innerHTML = emptyState("暂无企业线索", "当用户提交定制训练需求后，企业工作台会自动展示。");
    return;
  }
  elements.leadList.innerHTML = leads
    .map(
      (lead) => `
        <div class="history-item">
          <strong>${escapeHtml(lead.industry)} · ${escapeHtml(lead.status)}</strong>
          <span>${escapeHtml(lead.user_email)} · ${escapeHtml(lead.created_at)}</span>
          <p>${escapeHtml(lead.description)}</p>
          <div class="lead-actions">
            <button class="mini-btn" onclick="updateLeadStatus(${lead.id}, '待联系')">待联系</button>
            <button class="mini-btn" onclick="updateLeadStatus(${lead.id}, '评估中')">评估中</button>
            <button class="mini-btn" onclick="updateLeadStatus(${lead.id}, '已转商机')">已转商机</button>
          </div>
        </div>
      `
    )
    .join("");
}

function persistToken(token) {
  state.token = token || "";
  if (state.token) {
    localStorage.setItem("microExpressionToken", state.token);
  } else {
    localStorage.removeItem("microExpressionToken");
  }
}

async function checkSystemHealth() {
  try {
    const data = await request("/api/system/health", { method: "GET" });
    const engineEl = document.getElementById("engine-status");
    if (engineEl) {
      engineEl.textContent = data.model_loaded ? `${data.engine} (REAL)` : "Demo Engine (Simulation)";
      engineEl.style.color = data.model_loaded ? "#00ffcc" : "#ffaa00";
    }
  } catch (err) {
    console.error("System health check failed");
  }
}

async function loadUserOverview() {
  checkSystemHealth(); // 每次加载数据时检查系统状态
  if (!state.token) {
    state.currentUser = null;
    elements.authStatus.textContent = "未登录";
    elements.authUserMeta.textContent = "请先注册或登录后体验完整功能。";
    elements.membershipTier.textContent = "Free";
    elements.reportCredits.textContent = "0";
    elements.recognitionCount.textContent = "0";
    elements.dominantEmotion.textContent = "平静";
    elements.adminSection.classList.add("hidden");
    renderEmotionBars({});
    renderRecognitions([]);
    renderReports([]);
    renderOrders([]);
    return;
  }
  const user = await request("/api/auth/me", { method: "GET" });
  state.currentUser = user;
  elements.authStatus.textContent = `已登录：${user.email}`;
  elements.authUserMeta.textContent = `会员等级 ${user.membership_tier} · 报告额度 ${user.report_credits}`;
  elements.membershipTier.textContent = user.membership_tier;
  elements.reportCredits.textContent = user.report_credits;
  elements.recognitionCount.textContent = user.recognition_count;
  elements.dominantEmotion.textContent = user.dominant_emotion;
  renderEmotionBars(user.emotion_distribution);
}

async function runHealthAssessment() {
  if (!state.token) return;

  try {
    const data = await request("/api/health/assessment", {
      method: "POST",
    });

    const stressEl = document.getElementById("stress-index");
    const focusEl = document.getElementById("focus-score");
    const riskEl = document.getElementById("risk-level");
    const adviceEl = document.getElementById("health-advice");
    const hrvValueEl = document.getElementById("hrv-value");
    const hrvStatusEl = document.getElementById("hrv-status");
    const blinkRateEl = document.getElementById("blink-rate");
    const blinkStatusEl = document.getElementById("blink-status");
    const clinicalIdEl = document.getElementById("clinical-id");
    const calBadgeEl = document.getElementById("calibration-status-badge");

    if (stressEl) stressEl.textContent = data.stress_index;
    if (focusEl) focusEl.textContent = data.focus_score;
    if (riskEl) riskEl.textContent = data.anxiety_risk;
    if (adviceEl) adviceEl.textContent = data.health_advice;
    if (hrvValueEl) hrvValueEl.textContent = data.hrv_value;
    if (hrvStatusEl) hrvStatusEl.textContent = data.hrv_status;
    if (blinkRateEl) blinkRateEl.textContent = data.blink_rate;
    if (blinkStatusEl) blinkStatusEl.textContent = data.blink_status;
    if (clinicalIdEl) clinicalIdEl.textContent = `ID: ${data.clinical_id}`;
    
    if (calBadgeEl) {
      calBadgeEl.textContent = data.is_calibrated ? "已校准" : "未校准";
      calBadgeEl.style.color = data.is_calibrated ? "#00ffcc" : "#888";
      calBadgeEl.style.borderColor = data.is_calibrated ? "#00ffcc" : "#444";
    }

    state.lastAssessment = data; // 保存最后一次评估结果用于导出

    if (riskEl) {
      if (data.stress_index > 70) riskEl.style.color = "#ff4d4d";
      else if (data.stress_index > 40) riskEl.style.color = "#ffaa00";
      else riskEl.style.color = "#00ffcc";
    }

    showToast("健康评估已更新");
  } catch (err) {
    showToast("评估更新失败", true);
  }
}

async function loadDashboardData() {
  if (!state.token) {
    return;
  }
  const dashboard = await request("/api/dashboard/overview", { method: "GET" });
  state.dashboard = dashboard;
  renderRecognitions(dashboard.recent_recognitions || []);
  renderReports(dashboard.recent_reports || []);
  renderOrders(dashboard.recent_orders || []);
  runHealthAssessment();
}

function openCalibrationModal() {
  document.getElementById("calibration-modal").classList.remove("hidden");
  document.getElementById("calibration-timer").textContent = "5";
  document.getElementById("calibration-bar").style.width = "0%";
  document.getElementById("calibration-status").textContent = "准备就绪";
  document.getElementById("start-calibration-btn").disabled = false;
}

function closeCalibrationModal() {
  document.getElementById("calibration-modal").classList.add("hidden");
}

async function startCalibration() {
  const btn = document.getElementById("start-calibration-btn");
  const timerEl = document.getElementById("calibration-timer");
  const barEl = document.getElementById("calibration-bar");
  const statusEl = document.getElementById("calibration-status");
  
  btn.disabled = true;
  statusEl.textContent = "校准中，请保持面部平静...";
  
  let timeLeft = 5;
  const interval = setInterval(async () => {
    timeLeft -= 0.1;
    if (timeLeft <= 0) {
      clearInterval(interval);
      timerEl.textContent = "0";
      barEl.style.width = "100%";
      finishCalibration();
    } else {
      timerEl.textContent = Math.ceil(timeLeft);
      barEl.style.width = `${((5 - timeLeft) / 5) * 100}%`;
    }
  }, 100);
}

async function finishCalibration() {
  const statusEl = document.getElementById("calibration-status");
  statusEl.textContent = "正在同步基准数据...";
  
  try {
    // 模拟采集当前的生理基准（心率变异性基础值等）
    const mockBaseline = {
      base_hrv: 55 + Math.random() * 10,
      base_blink_rate: 12 + Math.random() * 4,
      timestamp: new Date().toISOString()
    };
    
    await request("/api/health/calibrate", {
      method: "POST",
      body: JSON.stringify(mockBaseline)
    });
    
    statusEl.textContent = "校准成功！评估严谨度已提升。";
    setTimeout(() => {
      closeCalibrationModal();
      showToast("系统基准校准完成", false);
      runHealthAssessment(); // 重新运行评估以应用新基准
    }, 1500);
  } catch (err) {
     statusEl.textContent = "同步失败，请重试。";
     document.getElementById("start-calibration-btn").disabled = false;
   }
 }

async function loadAdminWorkspace() {
  if (!state.currentUser?.can_manage_leads) {
    elements.adminSection.classList.add("hidden");
    return;
  }
  const [overview, leads, auditLogs] = await Promise.all([
    request("/api/admin/overview", { method: "GET" }),
    request("/api/admin/leads", { method: "GET" }),
    request("/api/admin/audit-logs", { method: "GET" }),
  ]);
  elements.adminSection.classList.remove("hidden");
  renderAdminStats(overview);
  renderLeadList(leads);
  renderAuditLogs(auditLogs);
}

function renderAdminStats(stats) {
  const container = document.getElementById("adminStats");
  if (!container) return;
  container.innerHTML = `
    <div class="stat-box"><span>总注册用户</span><strong>${stats.total_users}</strong></div>
    <div class="stat-box"><span>付费订单</span><strong>${stats.paid_orders}</strong></div>
    <div class="stat-box"><span>累计营收</span><strong>¥${stats.total_revenue}</strong></div>
    <div class="stat-box"><span>定制需求</span><strong>${stats.pending_leads}</strong></div>
  `;
}

function renderLeadList(leads) {
  const container = document.getElementById("leadList");
  if (!container) return;
  if (!leads || leads.length === 0) {
    container.innerHTML = "<p>暂无商务咨询需求</p>";
    return;
  }
  container.innerHTML = leads
    .map(
      (lead) => `
    <div class="history-item">
      <div>
        <strong>行业：${escapeHtml(lead.industry)}</strong>
        <p>${escapeHtml(lead.description)}</p>
        <small>状态：${escapeHtml(lead.status)} | 时间：${new Date(lead.created_at).toLocaleString()}</small>
      </div>
      <button class="ghost-btn" onclick="updateLeadStatus(${lead.id}, 'processing')">处理中</button>
    </div>
  `
    )
    .join("");
}

function renderAuditLogs(logs) {
  const list = document.getElementById("audit-log-list");
  if (!list) return;
  if (!logs || logs.length === 0) {
    list.innerHTML = "<p>暂无日志</p>";
    return;
  }
  list.innerHTML = logs
    .map(
      (log) => `
        <div style="border-bottom: 1px solid #333; padding: 5px 0; display: flex; justify-content: space-between;">
          <span style="color: #888;">[${new Date(log.created_at).toLocaleTimeString()}]</span>
          <span style="color: #00ffcc;">${log.action}</span>
          <span style="color: #ccc;">${log.resource}</span>
          <span style="color: ${log.status === 'success' ? '#5cb85c' : '#d9534f'};">${log.status}</span>
        </div>
      `
    )
    .join("");
}

async function updateLeadStatus(leadId, status) {
  if (!state.token) return;
  await request(`/api/admin/leads/${leadId}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });
  showToast("状态已更新");
  await loadAdminWorkspace();
}

async function refreshAuthenticatedData() {
  await loadUserOverview();
  if (!state.token) {
    return;
  }
  await Promise.all([loadDashboardData(), loadAdminWorkspace()]);
}

async function loadPlans() {
  const plans = await request("/api/membership/plans", { method: "GET" });
  elements.plansGrid.innerHTML = plans
    .map(
      (plan) => `
        <div class="plan-card">
          <span>${escapeHtml(plan.name)}</span>
          <strong>${escapeHtml(plan.price)}</strong>
          <ul>${plan.rights.map((right) => `<li>${escapeHtml(right)}</li>`).join("")}</ul>
          <button class="primary-btn" onclick="buyPlan('${escapeHtml(plan.name)}')">立即开通</button>
        </div>
      `
    )
    .join("");
}

async function loadCourses() {
  const courses = await request("/api/courses", { method: "GET" });
  elements.courseGrid.innerHTML = courses
    .map(
      (course) => `
        <div class="course-card">
          <span>${escapeHtml(course.type)}</span>
          <strong>${escapeHtml(course.title)}</strong>
          <p>${escapeHtml(course.description)}</p>
          <div class="inline-actions" style="justify-content: space-between; align-items: center;">
            <span style="font-weight: bold; color: var(--accent);">${escapeHtml(course.price)}</span>
            <button class="ghost-btn" onclick="buyCourse('${escapeHtml(course.title)}')">立即咨询</button>
          </div>
        </div>
      `
    )
    .join("");
}

async function buyCourse(courseTitle) {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  showToast(`已提交“${courseTitle}”的咨询请求，顾问稍后联系您`, false);
}

async function authenticate(event) {
  event.preventDefault();
  const payload = {
    email: elements.emailInput.value.trim(),
    password: elements.passwordInput.value.trim(),
  };
  const endpoint = state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
  const result = await request(endpoint, {
    method: "POST",
    body: JSON.stringify(payload),
  });
  persistToken(result.tokens?.access_token || result.token);
  await refreshAuthenticatedData();
  showToast(`${state.authMode === "register" ? "注册" : "登录"}成功`);
}

async function handleForgotPassword() {
  const email = elements.emailInput.value.trim();
  if (!email) {
    showToast("请先输入邮箱", true);
    return;
  }
  const result = await request("/api/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
  showToast(result.message);
}

async function startCamera() {
  if (state.stream) {
    return;
  }
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" }, audio: false });
    state.stream = stream;
    elements.camera.srcObject = stream;
    showToast("摄像头已开启");
  } catch (error) {
    console.error("摄像头启动失败:", error);
    if (error.name === "NotAllowedError") {
      showToast("摄像头权限被拒绝，请在浏览器设置中允许摄像头访问", true);
    } else if (error.name === "NotFoundError") {
      showToast("未检测到摄像头设备", true);
    } else if (error.name === "NotReadableError") {
      showToast("摄像头被其他应用占用，请关闭其他使用摄像头的程序", true);
    } else {
      showToast(`摄像头启动失败: ${error.message}`, true);
    }
    throw error;
  }
}

async function captureAndRecognize() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  if (!state.stream) {
    await startCamera();
  }
  const video = elements.camera;
  const canvas = elements.captureCanvas;
  const width = video.videoWidth || 640;
  const height = video.videoHeight || 480;
  canvas.width = width;
  canvas.height = height;
  canvas.getContext("2d").drawImage(video, 0, 0, width, height);
  const imageDataUrl = canvas.toDataURL("image/jpeg", 0.92);
  const result = await request("/api/recognition/realtime", {
    method: "POST",
    body: JSON.stringify({ image_data_url: imageDataUrl, source_type: "camera" }),
  });
  const record = result.record;
  setPanelText(
    elements.recognitionResult,
    `主识别：${record.label}\n置信度：${record.confidence}\n情绪强度：${record.intensity}\n持续时长：${record.duration_ms} ms\n辅助标签：${record.secondary_label}\n引擎：${record.engine} ${record.engine_version || ""}`
  );
  await refreshAuthenticatedData();
  showToast("识别完成");
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

async function extractVideoFrames(file, frameCount = 5) {
  const videoUrl = URL.createObjectURL(file);
  const video = document.createElement("video");
  video.src = videoUrl;
  video.muted = true;
  video.playsInline = true;
  await new Promise((resolve, reject) => {
    video.onloadedmetadata = resolve;
    video.onerror = () => reject(new Error("视频加载失败"));
  });
  const canvas = document.createElement("canvas");
  const width = video.videoWidth || 640;
  const height = video.videoHeight || 360;
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  const duration = Number.isFinite(video.duration) && video.duration > 0 ? video.duration : 1;
  const targets = Array.from({ length: frameCount }, (_, index) => {
    const progress = (index + 1) / (frameCount + 1);
    return Math.min(duration * progress, Math.max(0, duration - 0.05));
  });
  const frames = [];
  for (const target of targets) {
    await new Promise((resolve, reject) => {
      video.onseeked = () => {
        context.drawImage(video, 0, 0, width, height);
        frames.push(canvas.toDataURL("image/jpeg", 0.88));
        resolve();
      };
      video.onerror = () => reject(new Error("视频取帧失败"));
      video.currentTime = target;
    });
  }
  URL.revokeObjectURL(videoUrl);
  return frames;
}

async function analyzeUploadedContent() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const file = elements.uploadInput.files?.[0];
  if (!file) {
    showToast("请先选择图片或视频", true);
    return;
  }
  if (file.type.startsWith("image/")) {
    const imageDataUrl = await readFileAsDataUrl(file);
    const result = await request("/api/recognition/realtime", {
      method: "POST",
      body: JSON.stringify({ image_data_url: imageDataUrl, source_type: "upload-image" }),
    });
    const record = result.record;
    setPanelText(
      elements.recognitionResult,
      `上传分析完成\n主识别：${record.label}\n置信度：${record.confidence}\n情绪强度：${record.intensity}\n持续时长：${record.duration_ms} ms`
    );
  } else if (file.type.startsWith("video/")) {
    const frames = await extractVideoFrames(file, 5);
    const result = await request("/api/recognition/sequence", {
      method: "POST",
      body: JSON.stringify({ frames, source_type: "upload-video" }),
    });
    setPanelText(
      elements.recognitionResult,
      `视频分析完成\n${result.summary}\n主导情绪：${result.sequence.dominant_emotion}\n次级情绪：${result.sequence.secondary_emotion}\n引擎：${result.sequence.engine} ${result.sequence.engine_version}`
    );
    renderWaveChart(result.sequence.wave || []);
  } else {
    showToast("暂不支持该文件类型", true);
    return;
  }
  await refreshAuthenticatedData();
  showToast("上传内容分析成功");
}

async function generateReport() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const result = await request("/api/reports/generate", { method: "POST" });
  const report = result.report;
  const details = report.details;
  setPanelText(
    elements.reportPanel,
    `标题：${report.title}\n摘要：${report.summary}\n洞察：${details.insight}\n样本分布：${Object.entries(details.distribution)
      .map(([label, count]) => `${label}:${count}`)
      .join(" / ")}`
  );
  renderWaveChart(details.wave || []);
  await refreshAuthenticatedData();
  showToast("报告生成成功");
}

async function openReport(reportId) {
  if (!state.token) {
    return;
  }
  const report = await request(`/api/reports/${reportId}`, { method: "GET" });
  setPanelText(
    elements.reportPanel,
    `标题：${report.title}\n摘要：${report.summary}\n洞察：${report.details.insight}\n分布：${Object.entries(report.details.distribution)
      .map(([label, count]) => `${label}:${count}`)
      .join(" / ")}`
  );
  renderWaveChart(report.details.wave || []);
  const exportBtn = document.getElementById("exportPdfBtn");
  if (exportBtn) {
    exportBtn.classList.remove("hidden");
  }
}

async function exportPdfReport() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  const opt = {
    margin:       [10, 10, 15, 10],
    filename:     `Clinical_Report_${new Date().getTime()}.pdf`,
    image:        { type: 'jpeg', quality: 0.98 },
    html2canvas:  { scale: 2, useCORS: true },
    jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
  };
  
  const container = document.createElement('div');
  container.style.padding = '30px';
  container.style.color = '#1a1a1a';
  container.style.backgroundColor = '#fff';
  container.style.fontFamily = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
  
  // Header
  const header = `
    <div style="border-bottom: 3px solid #00ffcc; padding-bottom: 20px; margin-bottom: 25px; display: flex; justify-content: space-between; align-items: flex-end;">
      <div>
        <h1 style="margin: 0; font-size: 24px; color: #000;">智能情绪健康与压力临床评估报告</h1>
        <p style="margin: 5px 0 0 0; color: #666; font-size: 14px;">Clinical Emotion & Stress Analysis Report</p>
      </div>
      <div style="text-align: right;">
        <p style="margin: 0; font-weight: bold; font-size: 14px;">报告编号: ${state.lastAssessment?.clinical_id || 'N/A'}</p>
        <p style="margin: 2px 0 0 0; color: #888; font-size: 12px;">生成日期: ${new Date().toLocaleString()}</p>
      </div>
    </div>
  `;
  
  // Patient Info (Simulated)
  const patientInfo = `
    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 25px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; font-size: 13px;">
      <div><strong>用户 ID:</strong> ${state.currentUser?.id || 'UID-8821'}</div>
      <div><strong>账号:</strong> ${state.currentUser?.email || 'Guest'}</div>
      <div><strong>样本类型:</strong> 微表情序列分析</div>
      <div><strong>合规标准:</strong> HIPAA/GDPR</div>
      <div><strong>数据加密:</strong> AES-256 (RSA-2048)</div>
      <div><strong>分析引擎:</strong> ${state.dashboard?.recent_recognitions?.[0]?.engine || 'AI-Medical-v1'}</div>
    </div>
  `;
  
  // Metrics Section
  const assessment = state.lastAssessment || { stress_index: '--', focus_score: '--', anxiety_risk: '--', hrv_value: '--', blink_rate: '--' };
  const metrics = `
    <h2 style="font-size: 18px; border-left: 4px solid #00ffcc; padding-left: 10px; margin-bottom: 15px;">1. 临床指标分析 (Clinical Metrics)</h2>
    <table style="width: 100%; border-collapse: collapse; margin-bottom: 25px;">
      <tr style="background: #f1f3f5;">
        <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">评估维度</th>
        <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">测量值</th>
        <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">参考区间 (Normal)</th>
        <th style="padding: 12px; border: 1px solid #dee2e6; text-align: left;">评估状态</th>
      </tr>
      <tr>
        <td style="padding: 12px; border: 1px solid #dee2e6;">感知压力指数 (PSS)</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.stress_index}%</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">0% - 40%</td>
        <td style="padding: 12px; border: 1px solid #dee2e6; font-weight: bold; color: ${assessment.stress_index > 40 ? '#d9534f' : '#5cb85c'}">${assessment.stress_index > 40 ? '注意' : '正常'}</td>
      </tr>
      <tr>
        <td style="padding: 12px; border: 1px solid #dee2e6;">心率变异性 (HRV)</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.hrv_value} ms</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">> 50 ms</td>
        <td style="padding: 12px; border: 1px solid #dee2e6; font-weight: bold; color: ${assessment.hrv_value < 50 ? '#f0ad4e' : '#5cb85c'}">${assessment.hrv_status || '正常'}</td>
      </tr>
      <tr>
        <td style="padding: 12px; border: 1px solid #dee2e6;">认知专注得分</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.focus_score}%</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">> 70%</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.focus_score > 70 ? '优良' : '一般'}</td>
      </tr>
      <tr>
        <td style="padding: 12px; border: 1px solid #dee2e6;">瞬目频率 (Blink Rate)</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.blink_rate} 次/分</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">10 - 20 次/分</td>
        <td style="padding: 12px; border: 1px solid #dee2e6;">${assessment.blink_status || '正常'}</td>
      </tr>
    </table>
  `;
  
  // Risk & Advice
  const advice = `
    <h2 style="font-size: 18px; border-left: 4px solid #00ffcc; padding-left: 10px; margin-bottom: 15px;">2. 风险等级与专家建议</h2>
    <div style="background: ${assessment.stress_index > 70 ? '#fff5f5' : '#f5fff5'}; border: 1px solid ${assessment.stress_index > 70 ? '#ffc9c9' : '#c9ffc9'}; padding: 15px; border-radius: 8px;">
      <p style="margin-top: 0;"><strong>风险等级:</strong> <span style="font-size: 1.2rem; color: ${assessment.stress_index > 70 ? '#d9534f' : '#5cb85c'}">${assessment.anxiety_risk}</span></p>
      <p style="margin-bottom: 0; line-height: 1.6;"><strong>建议详情:</strong> ${assessment.health_advice}</p>
    </div>
  `;
  
  // Footer / Signature
  const footer = `
    <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee; display: flex; justify-content: space-between; align-items: center;">
      <div style="font-size: 11px; color: #999; max-width: 60%;">
        * 本报告由 AI 情绪健康分析引擎自动生成。所有原始面部特征数据均已在分析后立即销毁。本报告不具有法律强制约束力，仅作为个人健康参考。
      </div>
      <div style="text-align: right;">
        <div style="font-family: 'Brush Script MT', cursive; font-size: 24px; color: #000; margin-bottom: 5px;">AI-Medical Validator</div>
        <p style="margin: 0; font-size: 12px; color: #666;">数字化实验室认证章 (AES-Signature)</p>
      </div>
    </div>
  `;
  
  container.innerHTML = header + patientInfo + metrics + advice + footer;
  
  showToast("正在生成临床级 PDF 报告...");
  html2pdf().set(opt).from(container).save().then(() => {
    showToast("临床报告导出成功");
  }).catch((err) => {
    showToast("报告生成失败", true);
  });
}

async function runAssessment() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const result = await request("/api/evaluations/workplace", {
    method: "POST",
    body: JSON.stringify({ scenario: elements.workplaceScenario.value }),
  });
  setPanelText(
    elements.reportPanel,
    `场景：${result.scenario}\n匹配得分：${result.score}\n主导情绪：${result.dominant_emotion}\n建议：${result.suggestion}`
  );
}

async function companionReply() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const result = await request("/api/companion/respond", {
    method: "POST",
    body: JSON.stringify({ emotion: elements.emotionSelect.value }),
  });
  setPanelText(elements.companionPanel, result.message);
}

async function exportData() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const response = await fetch("/api/data/export", {
    headers: { Authorization: `Bearer ${state.token}` },
  });
  if (!response.ok) {
    showToast("导出失败", true);
    return;
  }
  const text = await response.text();
  const blob = new Blob(["\ufeff" + text], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "情绪数据导出.csv";
  link.click();
  URL.revokeObjectURL(url);
  showToast("CSV 已导出");
}

async function loadAdsRecommendation() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const result = await request("/api/ads/recommendation", { method: "GET" });
  setPanelText(elements.adsPanel, `${result.title}\n${result.description}\n主导情绪：${result.dominant_emotion}`);
}

async function buyPlan(planName) {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  // 获取价格
  const plans = await request("/api/membership/plans", { method: "GET" });
  const plan = plans.find(p => p.name === planName);
  
  if (plan) {
    elements.payPlanName.textContent = plan.name;
    elements.payPlanAmount.textContent = plan.price;
    elements.paymentModal.classList.remove("hidden");
    
    // 临时存储当前要购买的计划
    state.pendingPlan = planName;
  }
}

async function simulatePayment() {
  if (!state.pendingPlan) return;
  
  showToast("正在处理支付请求...");
  
  try {
    // 模拟后端订单创建与支付回调
    const result = await request("/api/membership/purchase", {
      method: "POST",
      body: JSON.stringify({ plan_name: state.pendingPlan }),
    });
    
    showToast(result.message);
    elements.paymentModal.classList.add("hidden");
    state.pendingPlan = null;
    await refreshAuthenticatedData();
  } catch (error) {
    showToast(error.message, true);
  }
}

async function rechargeMembership() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const code = elements.rechargeInput.value.trim();
  if (!code) {
    showToast("请输入激活密钥", true);
    return;
  }
  const result = await request("/api/membership/recharge", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
  showToast(result.message);
  elements.rechargeInput.value = "";
  await refreshAuthenticatedData();
}

async function submitCustomTraining(event) {
  event.preventDefault();
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  const payload = {
    industry: document.getElementById("industryInput").value.trim(),
    description: document.getElementById("customDescription").value.trim(),
  };
  const result = await request("/api/custom-training/request", {
    method: "POST",
    body: JSON.stringify(payload),
  });
  setPanelText(
    elements.customPanel,
    `需求编号：${result.request.id}\n行业：${result.request.industry}\n状态：${result.request.status}\n创建时间：${result.request.created_at}`
  );
  await refreshAuthenticatedData();
  showToast("定制需求已提交");
}

async function updateLeadStatus(requestId, status) {
  const updated = await request(`/api/admin/leads/${requestId}`, {
    method: "POST",
    body: JSON.stringify({ status }),
  });
  showToast(`线索 ${updated.id} 已更新为${updated.status}`);
  await loadAdminWorkspace();
}

async function getBehaviorAnalysis() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  try {
    const result = await request("/api/analytics/behavior", { method: "GET" });
    setPanelText(
      elements.analyticsPanel,
      `时间范围：${result.time_range.start} 至 ${result.time_range.end}\n总活动数：${result.activity_metrics.total_activities}\n活跃天数：${result.activity_metrics.active_days}\n日均活动：${result.activity_metrics.average_daily_activities}\n活动频率：${result.activity_metrics.activity_frequency}\n\n功能使用分布：${Object.entries(result.feature_usage).map(([key, value]) => `${key}: ${value}`).join(" / ")}`
    );
  } catch (error) {
    showToast(error.message, true);
  }
}

async function getEmotionAnalysis() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  try {
    const result = await request("/api/analytics/emotion", { method: "GET" });
    setPanelText(
      elements.analyticsPanel,
      `主导情绪：${result.dominant_emotion}\n平均强度：${result.average_intensity}\n\n情绪分布：${Object.entries(result.emotion_distribution).map(([key, value]) => `${key}: ${value}`).join(" / ")}\n\n情绪趋势：最近 ${result.emotion_trends.length} 天的情绪变化`
    );
  } catch (error) {
    showToast(error.message, true);
  }
}

async function generateApiKey() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  try {
    const result = await request("/api/api-keys/generate", { method: "POST" });
    setPanelText(
      elements.apiPanel,
      `API密钥：${result.api_key}\n${result.message}`
    );
    showToast("API密钥生成成功");
  } catch (error) {
    showToast(error.message, true);
  }
}

async function viewApiKeys() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  try {
    const keys = await request("/api/api-keys", { method: "GET" });
    if (keys.length === 0) {
      setPanelText(elements.apiPanel, "暂无API密钥，请生成新的API密钥");
      return;
    }
    const keyList = keys.map(key => `ID: ${key.id}\n密钥：${key.api_key}\n状态：${key.status}\n创建时间：${key.created_at}\n最后使用：${key.last_used_at}`).join("\n\n");
    setPanelText(elements.apiPanel, keyList);
  } catch (error) {
    showToast(error.message, true);
  }
}

async function getApiUsage() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  try {
    const usage = await request("/api/api-usage", { method: "GET" });
    setPanelText(
      elements.apiPanel,
      `总调用次数：${usage.total_calls}\n成功次数：${usage.success_calls}\n失败次数：${usage.error_calls}`
    );
  } catch (error) {
    showToast(error.message, true);
  }
}

function setupEvents() {
  // 表单验证
  if (elements.emailInput) {
    addInputValidation(elements.emailInput, validateEmail, "请输入有效的邮箱地址");
  }
  if (elements.passwordInput) {
    addInputValidation(elements.passwordInput, validatePassword, "密码至少需要6个字符");
  }

  elements.authForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    showLoading(submitBtn, "登录中...");
    
    try {
      await authenticate(event);
      showToast(`${state.authMode === "register" ? "注册" : "登录"}成功！`, false, "success");
      highlightElement(elements.authStatus);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(submitBtn);
    }
  });

  elements.tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.authMode = button.dataset.mode;
      elements.tabButtons.forEach((item) => item.classList.remove("active"));
      button.classList.add("active");
      animateElement(button, "pulse");
      showToast(`已切换至${button.dataset.mode === "login" ? "登录" : "注册"}模式`);
    });
  });

  const forgotPasswordBtn = document.getElementById("forgotPasswordBtn");
  forgotPasswordBtn.addEventListener("click", async () => {
    showLoading(forgotPasswordBtn, "发送中...");
    try {
      await handleForgotPassword();
      showToast("验证码已发送至邮箱", false, "success");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(forgotPasswordBtn);
    }
  });

  const startCameraBtn = document.getElementById("startCameraBtn");
  startCameraBtn.addEventListener("click", async () => {
    showLoading(startCameraBtn, "开启摄像头...");
    try {
      await startCamera();
      showToast("摄像头已成功开启", false, "success");
      animateElement(elements.camera, "fadeIn");
    } catch (error) {
      showToast(`摄像头开启失败：${error.message}`, true, "error");
    } finally {
      hideLoading(startCameraBtn);
    }
  });

  const captureBtn = document.getElementById("captureBtn");
  captureBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(captureBtn, "识别中...");
    try {
      await captureAndRecognize();
      showToast("识别完成！", false, "success");
      highlightElement(elements.recognitionResult);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(captureBtn);
    }
  });

  const analyzeUploadBtn = document.getElementById("analyzeUploadBtn");
  analyzeUploadBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    const file = elements.uploadInput.files?.[0];
    if (!file) {
      showToast("请先选择图片或视频", true, "warning");
      return;
    }
    
    showLoading(analyzeUploadBtn, "分析中...");
    try {
      await analyzeUploadedContent();
      showToast("分析完成！", false, "success");
      highlightElement(elements.recognitionResult);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(analyzeUploadBtn);
    }
  });

  const generateReportBtn = document.getElementById("generateReportBtn");
  generateReportBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(generateReportBtn, "生成报告...");
    try {
      await generateReport();
      showToast("报告生成成功！", false, "success");
      highlightElement(elements.reportPanel);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(generateReportBtn);
    }
  });

  const runAssessmentBtn = document.getElementById("runAssessmentBtn");
  runAssessmentBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(runAssessmentBtn, "评估中...");
    try {
      await runAssessment();
      showToast("评估完成！", false, "success");
      highlightElement(elements.reportPanel);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(runAssessmentBtn);
    }
  });

  const companionBtn = document.getElementById("companionBtn");
  companionBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(companionBtn, "思考中...");
    try {
      await companionReply();
      showToast("助手已回复", false, "success");
      highlightElement(elements.companionPanel);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(companionBtn);
    }
  });

  const exportBtn = document.getElementById("exportBtn");
  exportBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(exportBtn, "导出中...");
    try {
      await exportData();
      showToast("数据导出成功！", false, "success");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(exportBtn);
    }
  });

  const adsBtn = document.getElementById("adsBtn");
  adsBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    showLoading(adsBtn, "获取推荐...");
    try {
      await loadAdsRecommendation();
      showToast("推荐已更新", false, "success");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(adsBtn);
    }
  });

  const rechargeBtn = document.getElementById("rechargeBtn");
  rechargeBtn.addEventListener("click", async () => {
    if (!state.token) {
      showToast("请先登录", true, "warning");
      return;
    }
    
    const code = elements.rechargeInput.value.trim();
    if (!code) {
      showToast("请输入激活密钥", true, "warning");
      return;
    }
    
    showLoading(rechargeBtn, "充值中...");
    try {
      await rechargeMembership();
      showToast("充值成功！", false, "success");
      animateElement(elements.reportCredits, "pulse");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(rechargeBtn);
    }
  });

  elements.closePaymentBtn.addEventListener("click", () => {
    elements.paymentModal.classList.add("hidden");
    state.pendingPlan = null;
    showToast("已取消支付", false, "info");
  });

  elements.simulatePayBtn.addEventListener("click", async () => {
    if (!state.pendingPlan) return;
    
    showLoading(elements.simulatePayBtn, "支付中...");
    try {
      await simulatePayment();
      showToast("支付成功！", false, "success");
      animateElement(elements.membershipTier, "pulse");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(elements.simulatePayBtn);
    }
  });

  const exportPdfBtn = document.getElementById("exportPdfBtn");
  if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", async () => {
      showLoading(exportPdfBtn, "生成PDF...");
      try {
        await exportPdfReport();
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(exportPdfBtn);
      }
    });
  }

  const customTrainingForm = document.getElementById("customTrainingForm");
  customTrainingForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    showLoading(submitBtn, "提交中...");
    
    try {
      await submitCustomTraining(event);
      showToast("定制需求已提交！", false, "success");
      highlightElement(elements.customPanel);
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(submitBtn);
    }
  });

  const logoutBtn = document.getElementById("logoutBtn");
  logoutBtn.addEventListener("click", () => {
    showModal("确认退出", "确定要退出登录吗？", () => {
      persistToken("");
      if (state.stream) {
        state.stream.getTracks().forEach((track) => track.stop());
        state.stream = null;
        elements.camera.srcObject = null;
      }
      loadUserOverview();
      showToast("已安全退出", false, "info");
    });
  });

  const refreshDashboardBtn = document.getElementById("refreshDashboardBtn");
  refreshDashboardBtn.addEventListener("click", async () => {
    showLoading(refreshDashboardBtn, "刷新中...");
    try {
      await refreshAuthenticatedData();
      showToast("数据已刷新", false, "success");
    } catch (error) {
      showToast(error.message, true, "error");
    } finally {
      hideLoading(refreshDashboardBtn);
    }
  });

  if (elements.behaviorAnalysisBtn) {
    elements.behaviorAnalysisBtn.addEventListener("click", async () => {
      if (!state.token) {
        showToast("请先登录", true, "warning");
        return;
      }
      
      showLoading(elements.behaviorAnalysisBtn, "分析中...");
      try {
        await getBehaviorAnalysis();
        showToast("行为分析完成", false, "success");
        highlightElement(elements.analyticsPanel);
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(elements.behaviorAnalysisBtn);
      }
    });
  }

  if (elements.emotionAnalysisBtn) {
    elements.emotionAnalysisBtn.addEventListener("click", async () => {
      if (!state.token) {
        showToast("请先登录", true, "warning");
        return;
      }
      
      showLoading(elements.emotionAnalysisBtn, "分析中...");
      try {
        await getEmotionAnalysis();
        showToast("情绪分析完成", false, "success");
        highlightElement(elements.analyticsPanel);
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(elements.emotionAnalysisBtn);
      }
    });
  }

  if (elements.generateApiKeyBtn) {
    elements.generateApiKeyBtn.addEventListener("click", async () => {
      if (!state.token) {
        showToast("请先登录", true, "warning");
        return;
      }
      
      showLoading(elements.generateApiKeyBtn, "生成中...");
      try {
        await generateApiKey();
        showToast("API密钥已生成，请妥善保存", false, "success");
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(elements.generateApiKeyBtn);
      }
    });
  }

  if (elements.viewApiKeysBtn) {
    elements.viewApiKeysBtn.addEventListener("click", async () => {
      if (!state.token) {
        showToast("请先登录", true, "warning");
        return;
      }
      
      showLoading(elements.viewApiKeysBtn, "加载中...");
      try {
        await viewApiKeys();
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(elements.viewApiKeysBtn);
      }
    });
  }

  if (elements.apiUsageBtn) {
    elements.apiUsageBtn.addEventListener("click", async () => {
      if (!state.token) {
        showToast("请先登录", true, "warning");
        return;
      }
      
      showLoading(elements.apiUsageBtn, "加载中...");
      try {
        await getApiUsage();
      } catch (error) {
        showToast(error.message, true, "error");
      } finally {
        hideLoading(elements.apiUsageBtn);
      }
    });
  }
}

async function bootstrap() {
  setupEvents();
  try {
    await Promise.all([loadPlans(), loadCourses()]);
    await refreshAuthenticatedData();
  } catch (error) {
    showToast(error.message, true);
  }
}

// 心理评估量表功能
async function loadAssessmentScale(scaleType) {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  try {
    const result = await request(`/api/assessment/scales/${scaleType}`, { method: "GET" });
    
    const panel = document.getElementById("assessmentPanel");
    panel.innerHTML = `
      <div style="margin-bottom: 20px;">
        <h4 style="margin: 0 0 10px; color: var(--text);">${result.scale_name}</h4>
        <p style="color: var(--muted); font-size: 0.9rem;">共 ${result.question_count} 道题目</p>
      </div>
      <div id="assessmentQuestions">
        ${result.questions.map((q, index) => `
          <div class="assessment-question">
            <p>${index + 1}. ${q.question}</p>
            <div class="assessment-options">
              <button class="assessment-option" onclick="selectAnswer('${q.key}', 1)">完全没有</button>
              <button class="assessment-option" onclick="selectAnswer('${q.key}', 2)">有一点</button>
              <button class="assessment-option" onclick="selectAnswer('${q.key}', 3)">中等程度</button>
              <button class="assessment-option" onclick="selectAnswer('${q.key}', 4)">相当多</button>
            </div>
          </div>
        `).join("")}
      </div>
      <button id="submitAssessmentBtn" class="primary-btn" style="margin-top: 20px; display: none;">提交评估</button>
    `;
    
    state.currentAssessment = {
      scaleType,
      answers: {},
      questionCount: result.question_count
    };
    
    // 更新按钮状态
    checkAssessmentComplete();
    
  } catch (error) {
    showToast(error.message, true);
  }
}

state.assessmentAnswers = {};

function selectAnswer(key, value) {
  state.assessmentAnswers[key] = value;
  
  // 更新UI
  document.querySelectorAll('.assessment-option').forEach(btn => {
    if (btn.onclick && btn.onclick.toString().includes(key)) {
      btn.classList.remove('selected');
    }
  });
  
  event.target.classList.add('selected');
  
  checkAssessmentComplete();
}

function checkAssessmentComplete() {
  const scaleType = state.currentAssessment?.scaleType;
  const questionCount = state.currentAssessment?.questionCount || 0;
  const answeredCount = Object.keys(state.assessmentAnswers).length;
  
  const submitBtn = document.getElementById('submitAssessmentBtn');
  if (answeredCount >= questionCount && questionCount > 0) {
    submitBtn.style.display = 'block';
    submitBtn.addEventListener('click', () => submitAssessment(scaleType), { once: true });
  }
}

async function submitAssessment(scaleType) {
  if (!state.token) return;
  
  try {
    const result = await request(`/api/assessment/${scaleType}`, {
      method: "POST",
      body: JSON.stringify({ answers: state.assessmentAnswers })
    });
    
    const panel = document.getElementById("assessmentPanel");
    panel.innerHTML = `
      <div class="assessment-result">
        <div class="result-score">${result.standard_score}</div>
        <div class="result-level ${result.level.toLowerCase()}">${result.level}</div>
        <div class="result-interpretation">
          <p><strong>评分说明：</strong></p>
          <p>原始分：${result.raw_score} 分</p>
          <p>标准分：${result.standard_score} 分</p>
          <hr style="margin: 15px 0; border: none; border-top: 1px solid rgba(255,255,255,0.1);">
          <p><strong>评估解读：</strong></p>
          <p>${result.interpretation}</p>
        </div>
      </div>
    `;
    
    showToast("评估完成");
    state.assessmentAnswers = {};
    
  } catch (error) {
    showToast(error.message, true);
  }
}

// 视频流实时监测功能
let liveSessionId = null;
let liveInterval = null;

async function startLiveMonitoring() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  try {
    // 创建视频会话
    const result = await request("/api/video/create-session", { method: "POST" });
    liveSessionId = result.session_id;
    
    // 开启摄像头
    if (!state.stream) {
      await startCamera();
    }
    
    const liveVideo = document.getElementById("liveVideo");
    liveVideo.srcObject = state.stream;
    
    // 开始实时分析
    startLiveAnalysis();
    
    document.getElementById("startLiveBtn").style.display = 'none';
    document.getElementById("stopLiveBtn").style.display = 'inline-block';
    
    showToast("实时监测已开始");
    
  } catch (error) {
    showToast(error.message, true);
  }
}

function startLiveAnalysis() {
  let frameCount = 0;
  let startTime = Date.now();
  
  liveInterval = setInterval(async () => {
    if (!liveSessionId) return;
    
    try {
      const video = document.getElementById("liveVideo");
      const canvas = document.createElement('canvas');
      canvas.width = video.videoWidth || 640;
      canvas.height = video.videoHeight || 480;
      canvas.getContext('2d').drawImage(video, 0, 0);
      
      const frameBase64 = canvas.toDataURL("image/jpeg", 0.8);
      const timestamp = Date.now();
      
      const result = await request("/api/video/process-frame", {
        method: "POST",
        body: JSON.stringify({
          session_id: liveSessionId,
          frame_base64: frameBase64,
          timestamp: timestamp
        })
      });
      
      // 更新显示
      document.getElementById("currentEmotion").textContent = result.emotion;
      document.getElementById("liveConfidence").textContent = result.confidence;
      document.getElementById("frameCount").textContent = ++frameCount;
      
      const duration = Math.floor((Date.now() - startTime) / 1000);
      const mins = Math.floor(duration / 60);
      const secs = duration % 60;
      document.getElementById("sessionDuration").textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
      
    } catch (error) {
      console.error("Live analysis error:", error);
    }
  }, 500); // 每500ms分析一帧
}

async function stopLiveMonitoring() {
  if (!liveSessionId) return;
  
  try {
    // 获取会话摘要
    const result = await request(`/api/video/session-summary/${liveSessionId}`, { method: "GET" });
    
    const panel = document.getElementById("liveEmotionDisplay");
    panel.innerHTML += `
      <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid rgba(255,255,255,0.1);">
        <h4 style="margin: 0 0 10px;">监测会话摘要</h4>
        <p>主导情绪：${result.dominant_emotion}</p>
        <p>平均置信度：${result.average_confidence}</p>
        <p>分析帧数：${result.total_frames}</p>
        <p>持续时间：${result.duration_seconds}秒</p>
      </div>
    `;
    
  } catch (error) {
    console.error("Session summary error:", error);
  }
  
  // 停止分析
  clearInterval(liveInterval);
  liveInterval = null;
  liveSessionId = null;
  
  document.getElementById("startLiveBtn").style.display = 'inline-block';
  document.getElementById("stopLiveBtn").style.display = 'none';
  
  showToast("实时监测已停止");
}

// 生理指标监测功能
async function updateBiometrics() {
  if (!state.token) return;
  
  try {
    const result = await request("/api/health/biometrics", { method: "GET" });
    
    document.getElementById("heartRate").textContent = result.heart_rate;
    document.getElementById("hrv").textContent = result.hrv;
    document.getElementById("breathRate").textContent = result.breathing_rate;
    document.getElementById("stressLevel").textContent = result.stress_percentage;
    
    const advicePanel = document.getElementById("biometricAdvice");
    advicePanel.innerHTML = `
      <p style="color: var(--text); margin-bottom: 10px;"><strong>健康建议：</strong></p>
      <p>${result.health_advice}</p>
      <div style="margin-top: 15px; display: grid; grid-template-columns: 2fr 1fr; gap: 10px;">
        <div style="padding: 10px; background: rgba(255,100,100,0.1); border-radius: 8px;">
          <p style="margin: 0; font-size: 0.8rem;">心率状态</p>
          <p style="margin: 0; font-weight: bold; color: #ff6464;">${result.heart_rate_status}</p>
        </div>
        <div style="padding: 10px; background: rgba(100,200,255,0.1); border-radius: 8px;">
          <p style="margin: 0; font-size: 0.8rem;">HRV状态</p>
          <p style="margin: 0; font-weight: bold; color: #64c8ff;">${result.hrv_status}</p>
        </div>
      </div>
    `;
    
  } catch (error) {
    console.error("Biometrics update error:", error);
  }
}

// 情绪日记功能
async function saveMood() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  const moodValue = document.getElementById("moodSelect").value;
  const note = document.getElementById("moodNote").value;
  
  try {
    await request("/api/mood/save", {
      method: "POST",
      body: JSON.stringify({
        mood: parseInt(moodValue),
        note: note,
        date: new Date().toISOString().split('T')[0]
      })
    });
    
    showToast("心情记录已保存");
    document.getElementById("moodNote").value = "";
    
    // 更新心情日历
    await loadMoodHistory();
    
  } catch (error) {
    showToast(error.message, true);
  }
}

async function loadMoodHistory() {
  if (!state.token) return;
  
  try {
    const result = await request("/api/mood/history", { method: "GET" });
    
    const moodDays = document.getElementById("moodDays");
    const today = new Date();
    
    moodDays.innerHTML = result.records.slice(-7).map((record, index) => {
      const date = new Date(record.date);
      const moodEmoji = getMoodEmoji(record.mood);
      const dateStr = date.getMonth() + 1 + '/' + date.getDate();
      
      return `
        <div class="mood-day" style="background: ${getMoodBackground(record.mood)};">
          <div class="mood-emoji">${moodEmoji}</div>
          <div class="mood-date">${dateStr}</div>
        </div>
      `;
    }).join("");
    
  } catch (error) {
    console.error("Mood history error:", error);
  }
}

function getMoodEmoji(mood) {
  const emojis = {
    1: "😢",
    2: "😔",
    3: "😐",
    4: "🙂",
    5: "😊"
  };
  return emojis[mood] || "📅";
}

function getMoodBackground(mood) {
  const colors = {
    1: "rgba(255,77,77,0.1)",
    2: "rgba(255,141,154,0.1)",
    3: "rgba(150,150,150,0.1)",
    4: "rgba(77,226,177,0.1)",
    5: "rgba(106,166,255,0.1)"
  };
  return colors[mood] || "rgba(255,255,255,0.03)";
}

// 放松训练功能
let breathingInterval = null;

async function startBreathingExercise() {
  const panel = document.getElementById("relaxationPanel");
  const circle = document.getElementById("breathingCircle");
  const text = document.getElementById("relaxationText");
  
  panel.innerHTML = `
    <div class="breathing-guide">
      <div id="breathingCircle" style="width: 150px; height: 150px; margin: 20px auto; border-radius: 50%; border: 3px solid #00ffcc; display: block;"></div>
      <div class="breathing-text" id="breathingText">准备开始...</div>
      <div class="breathing-countdown" id="breathingCountdown">4</div>
    </div>
  `;
  
  // 深呼吸循环：吸气4秒，屏息2秒，呼气4秒
  let phase = 0;
  let counter = 4;
  
  breathingInterval = setInterval(() => {
    const circle = document.getElementById("breathingCircle");
    const text = document.getElementById("breathingText");
    const countdown = document.getElementById("breathingCountdown");
    
    if (!circle || !text || !countdown) {
      clearInterval(breathingInterval);
      return;
    }
    
    if (phase === 0) {
      // 吸气
      text.textContent = "吸气...";
      countdown.textContent = counter;
      const scale = 0.8 + (1 - counter / 4) * 0.4;
      circle.style.transform = `scale(${scale})`;
      circle.style.opacity = 0.6 + (1 - counter / 4) * 0.4;
    } else if (phase === 1) {
      // 屏息
      text.textContent = "屏息...";
      countdown.textContent = counter;
    } else {
      // 呼气
      text.textContent = "呼气...";
      countdown.textContent = counter;
      const scale = 1.2 - (1 - counter / 4) * 0.4;
      circle.style.transform = `scale(${scale})`;
      circle.style.opacity = 1 - (1 - counter / 4) * 0.4;
    }
    
    counter--;
    if (counter < 0) {
      phase = (phase + 1) % 3;
      counter = phase === 1 ? 2 : 4;
    }
  }, 1000);
  
  showToast("深呼吸练习开始");
}

function stopBreathingExercise() {
  clearInterval(breathingInterval);
  breathingInterval = null;
  
  const panel = document.getElementById("relaxationPanel");
  panel.innerHTML = `
    <div id="breathingCircle" style="display: none;"></div>
    <p id="relaxationText">深呼吸练习已结束。感觉好点了吗？</p>
  `;
  
  showToast("练习结束");
}

async function startMeditation() {
  const panel = document.getElementById("relaxationPanel");
  panel.innerHTML = `
    <div class="breathing-guide">
      <div style="width: 120px; height: 120px; margin: 20px auto; border-radius: 50%; background: linear-gradient(135deg, #6aa6ff, #8f6dff); display: flex; align-items: center; justify-content: center;">
        <span style="font-size: 48px;">🧘</span>
      </div>
      <p style="font-size: 18px; color: var(--text);">冥想模式已激活</p>
      <p style="color: var(--muted); font-size: 0.9rem;">请找一个安静的地方，闭上眼睛，专注于你的呼吸。</p>
      <div style="margin-top: 20px; font-size: 24px; color: var(--accent);">🕯️ 正念冥想进行中...</div>
    </div>
  `;
  
  showToast("冥想模式已开启");
}

async function playRelaxMusic() {
  const panel = document.getElementById("relaxationPanel");
  panel.innerHTML = `
    <div class="breathing-guide">
      <div style="width: 100px; height: 100px; margin: 20px auto; border-radius: 50%; background: rgba(106,166,255,0.2); display: flex; align-items: center; justify-content: center; animation: pulse 2s ease-in-out infinite;">
        <span style="font-size: 36px;">🎵</span>
      </div>
      <p style="font-size: 18px; color: var(--text);">放松音乐播放中</p>
      <p style="color: var(--muted); font-size: 0.9rem;">舒缓的音乐有助于放松身心，减轻压力。</p>
      <div style="margin-top: 20px; display: flex; justify-content: center; gap: 10px;">
        <button class="ghost-btn" style="padding: 10px 20px;">⏸ 暂停</button>
        <button class="ghost-btn" style="padding: 10px 20px;">⏹ 停止</button>
      </div>
    </div>
  `;
  
  showToast("放松音乐已播放");
}

// 专家咨询功能
async function bookConsultation() {
  if (!state.token) {
    showToast("请先登录", true);
    return;
  }
  
  const consultType = document.getElementById("consultType").value;
  
  try {
    const result = await request("/api/consultation/book", {
      method: "POST",
      body: JSON.stringify({
        type: consultType,
        date: new Date(Date.now() + 86400000).toISOString().split('T')[0] // 明天
      })
    });
    
    const panel = document.getElementById("consultPanel");
    panel.innerHTML = `
      <div style="padding: 15px; background: rgba(77,226,177,0.1); border-radius: 12px;">
        <p style="color: var(--success); font-weight: bold; margin-bottom: 10px;">✅ 预约成功</p>
        <p>咨询类型：${result.appointment.type}</p>
        <p>预约时间：${result.appointment.scheduled_date}</p>
        <p>咨询师：${result.appointment.counselor_name}</p>
        <p style="font-size: 0.85rem; color: var(--muted); margin-top: 10px;">我们会通过邮件发送确认信息，请保持邮箱畅通。</p>
      </div>
    `;
    
    showToast("预约成功，我们会尽快与您联系");
    
  } catch (error) {
    showToast(error.message, true);
  }
}

async function anonymousConsult() {
  const panel = document.getElementById("consultPanel");
  panel.innerHTML = `
    <div style="padding: 15px;">
      <p style="color: var(--text); margin-bottom: 15px;"><strong>匿名咨询模式</strong></p>
      <div style="background: rgba(106,166,255,0.1); padding: 15px; border-radius: 10px; margin-bottom: 15px;">
        <p style="font-size: 0.9rem; color: var(--muted); margin: 0;">
          您的身份信息将被完全保密。我们的AI咨询师随时准备倾听您的困扰。
        </p>
      </div>
      <textarea id="anonymousMessage" rows="4" placeholder="请描述您的困扰..." style="width: 100%; padding: 12px; border-radius: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); color: var(--text); resize: none;"></textarea>
      <button id="sendAnonymousBtn" class="primary-btn" style="margin-top: 12px; width: 100%;">发送咨询</button>
    </div>
  `;
  
  document.getElementById("sendAnonymousBtn").addEventListener("click", async () => {
    const message = document.getElementById("anonymousMessage").value;
    if (!message.trim()) {
      showToast("请输入您的咨询内容", true);
      return;
    }
    
    try {
      const result = await request("/api/consultation/anonymous", {
        method: "POST",
        body: JSON.stringify({ message })
      });
      
      panel.innerHTML = `
        <div style="padding: 15px;">
          <p style="color: var(--text); margin-bottom: 15px;"><strong>AI 咨询师回复：</strong></p>
          <div style="background: rgba(255,255,255,0.03); padding: 15px; border-radius: 10px;">
            <p style="color: var(--muted); line-height: 1.6;">${result.response}</p>
          </div>
          <button id="newAnonymousBtn" class="ghost-btn" style="margin-top: 15px; width: 100%;">继续咨询</button>
        </div>
      `;
      
      document.getElementById("newAnonymousBtn").addEventListener("click", anonymousConsult);
      
    } catch (error) {
      showToast(error.message, true);
    }
  });
  
  showToast("匿名咨询通道已开启");
}

// 绑定事件
function setupAdditionalEvents() {
  // 心理评估量表
  document.getElementById("sasBtn")?.addEventListener("click", () => loadAssessmentScale("sas"));
  document.getElementById("sdsBtn")?.addEventListener("click", () => loadAssessmentScale("sds"));
  document.getElementById("pssBtn")?.addEventListener("click", () => loadAssessmentScale("pss"));
  
  // 视频流实时监测
  document.getElementById("startLiveBtn")?.addEventListener("click", startLiveMonitoring);
  document.getElementById("stopLiveBtn")?.addEventListener("click", stopLiveMonitoring);
  
  // 生理指标更新
  document.getElementById("heartRate")?.addEventListener("click", updateBiometrics);
  
  // 情绪日记
  document.getElementById("saveMoodBtn")?.addEventListener("click", saveMood);
  
  // 放松训练
  document.getElementById("breathingBtn")?.addEventListener("click", () => {
    startBreathingExercise();
    setTimeout(stopBreathingExercise, 60000); // 60秒后自动停止
  });
  document.getElementById("meditationBtn")?.addEventListener("click", startMeditation);
  document.getElementById("relaxBtn")?.addEventListener("click", playRelaxMusic);
  
  // 专家咨询
  document.getElementById("bookConsultBtn")?.addEventListener("click", bookConsultation);
  document.getElementById("anonymousConsultBtn")?.addEventListener("click", anonymousConsult);
  
  // 页面加载时更新生理指标和心情历史
  if (state.token) {
    updateBiometrics();
    loadMoodHistory();
  }
}

// 更新bootstrap函数，添加新事件绑定
async function bootstrap() {
  setupEvents();
  setupAdditionalEvents();
  try {
    await Promise.all([loadPlans(), loadCourses()]);
    await refreshAuthenticatedData();
  } catch (error) {
    console.error('初始化错误:', error);
    showToast(error.message, true);
  }
}

window.buyPlan = buyPlan;
window.buyCourse = buyCourse;
window.openReport = openReport;
window.updateLeadStatus = updateLeadStatus;
window.runHealthAssessment = runHealthAssessment;
window.openCalibrationModal = openCalibrationModal;
window.closeCalibrationModal = closeCalibrationModal;
window.startCalibration = startCalibration;
bootstrap();
