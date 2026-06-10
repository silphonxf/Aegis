const $ = (id) => document.getElementById(id);
const onClick = (id, handler) => {
  const el = $(id);
  if (el) el.onclick = handler;
};
const onEvent = (id, eventName, handler) => {
  const el = $(id);
  if (el) el.addEventListener(eventName, handler);
};
const DEFAULT_AVATAR = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="%230f2c44"/><circle cx="32" cy="24" r="12" fill="%236bd5ff"/><path d="M12 56c4-10 12-16 20-16s16 6 20 16" fill="%2338bdf8"/></svg>';
const AI_CHAT_HISTORY_KEY = 'aegis_ai_chat_history';
const AI_CHAT_CONVERSATION_KEY = 'aegis_ai_chat_conversation';
const AI_CHAT_SIDEBAR_COLLAPSED_KEY = 'aegis_ai_chat_sidebar_collapsed';
const ACTIVE_TAB_KEY = 'aegis_mobile_active_tab';
const AUTH_TOKEN_KEY = 'aegis_mobile_token';
const AI_SELFCHECK_TIMER_KEY = 'aegis_mobile_ai_selfcheck_timer';
const AI_MAX_ATTACHMENTS = 4;
const AI_MAX_FILE_SIZE = 2 * 1024 * 1024;
const DEFAULT_AI_MESSAGES = [
  {
    role: 'ai',
    text: '你好，我是 Aegis AI 助手。你可以直接提问，也可以上传图片或文件让我一起分析。',
    welcome: true,
  },
];

function buildDefaultAiMessages() {
  return DEFAULT_AI_MESSAGES.map((item) => ({ ...item }));
}

function loadAiMessages() {
  try {
    const raw = JSON.parse(sessionStorage.getItem(AI_CHAT_HISTORY_KEY) || 'null');
    if (Array.isArray(raw) && raw.length) {
      return raw.filter((item) => item && typeof item.text === 'string').slice(-80);
    }
  } catch {}
  return buildDefaultAiMessages();
}

function loadAiConversationId() {
  return sessionStorage.getItem(AI_CHAT_CONVERSATION_KEY) || '';
}

function loadActiveTab() {
  const value = sessionStorage.getItem(ACTIVE_TAB_KEY) || '';
  return value || 'tab-workbench';
}

function loadAiSidebarCollapsed() {
  return localStorage.getItem(AI_CHAT_SIDEBAR_COLLAPSED_KEY) === '1';
}

function mapConversationMessagesToUi(messages) {
  if (!Array.isArray(messages) || !messages.length) return buildDefaultAiMessages();
  return messages
    .filter((item) => item && typeof item.content === 'string')
    .map((item) => ({
      role: item.role === 'assistant' ? 'ai' : 'user',
      text: item.content,
    }));
}

const state = {
  token: loadStoredToken(),
  requestLogs: JSON.parse(localStorage.getItem('aegis_request_logs') || '[]'),
  selectedQuickRange: '1h',
  isCustomLogTimeRange: false,
  metricSeries: { cpu: [], mem: [], disk: [] },
  chartTimer: null,
  extractedErrors: [],
  profile: JSON.parse(localStorage.getItem('aegis_profile') || '{}'),
  statusSystems: [],
  selectedStatusSystemId: null,
  pendingSelfcheckPageOpen: false,
  logConfigsBySystem: {},
  selectedLogSystemId: null,
  selectedLogConfig: null,
  errorSystemsLoadedAt: 0,
  errorSystemsLoading: null,
  logConfigsLoadingBySystem: {},
  nfcTagText: 'NFC://DEMO-SYS-001/P-002',
  qrScanText: '',
  qrResolvedPoint: null,
  aiAttachments: [],
  aiMessages: loadAiMessages(),
  aiConversationId: loadAiConversationId(),
  aiConversationItems: [],
  aiSidebarCollapsed: loadAiSidebarCollapsed(),
  activeTab: loadActiveTab(),
  activeDetailPage: '',
  emergencyActions: { server_actions: [], process_actions: [], database_actions: [], submenus: [] },
  activeEmergencySection: '',
  isAnalyzingErrors: false,
  isAnalyzingCapture: false,
  isSendingAiMessage: false,
  aiSelfcheckTimer: null,
  aiSelfcheckTimerHandle: null,
  isRunningScheduledSelfcheck: false,
  latestSelfcheckReports: [],
  lastAiRequestPayload: null,
};

function loadStoredToken() {
  try { return localStorage.getItem(AUTH_TOKEN_KEY) || sessionStorage.getItem(AUTH_TOKEN_KEY) || ''; }
  catch {
    try { return sessionStorage.getItem(AUTH_TOKEN_KEY) || ''; }
    catch { return ''; }
  }
}

function storeToken(token) {
  try { localStorage.setItem(AUTH_TOKEN_KEY, token); }
  catch {}
  try { sessionStorage.setItem(AUTH_TOKEN_KEY, token); }
  catch {}
}

function clearStoredToken() {
  try { localStorage.removeItem(AUTH_TOKEN_KEY); }
  catch {}
  try { sessionStorage.removeItem(AUTH_TOKEN_KEY); }
  catch {}
}

function getDefaultBase() {
  const protocol = window.location.protocol === 'http:' ? 'http:' : 'https:';
  const host = window.location.hostname || '127.0.0.1';
  return `${protocol}//${host}:8000`;
}

function getBase() {
  return getDefaultBase();
}

function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}
function show(id, data) {
  const el = $(id);
  if (!el) return;
  el.textContent = typeof data === 'string' ? data : '操作已完成。';
}
function setButtonLoading(id, loading, loadingText) {
  const btn = $(id);
  if (!btn) return;
  if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
  btn.disabled = loading;
  btn.classList.toggle('secondary', loading);
  btn.textContent = loading ? (loadingText || '处理中...') : btn.dataset.originalText;
}

let toastTimer = null;
function showToast(message, type = 'info') {
  const el = $('toast');
  if (!el) return;
  el.textContent = message || '';
  el.className = `app-toast ${type}`;
  el.classList.remove('hidden');
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => {
    el.classList.add('hidden');
  }, 2200);
}

function explainActionError(error, featureName, roleHint) {
  const msg = error?.message || '操作失败';
  if (msg.includes('未登录或登录已过期')) {
    return `${featureName}失败：请先登录，再重试。`;
  }
  if (msg.includes('当前账号权限不足')) {
    return `${featureName}失败：当前账号权限不足，通常需要 ${roleHint}。`;
  }
  if (msg.includes('请求发送失败')) {
    return `${featureName}失败：接口请求未发出。请检查后端是否可达，或确认手机浏览器没有拦截 HTTPS 页面访问 HTTP 接口。`;
  }
  if (msg.includes('请求超时')) {
    return `${featureName}失败：接口响应超时，请稍后重试。`;
  }
  return `${featureName}失败：${msg}`;
}

function formatCaptureAiResult(data) {
  if (!data || typeof data !== 'object') return '暂无分析结果';
  const lines = [];
  if (data.summary) lines.push(`分析结果：${data.summary}`);
  if (Array.isArray(data.matched_rules) && data.matched_rules.length) {
    lines.push('', '命中特征：');
    data.matched_rules.forEach((item, idx) => lines.push(`${idx + 1}. ${item.code || 'UNKNOWN'} (${item.severity || 'unknown'})`));
  }
  if (Array.isArray(data.suggestions) && data.suggestions.length) {
    lines.push('', '建议动作：');
    data.suggestions.forEach((item, idx) => lines.push(`${idx + 1}. ${item}`));
  }
  return lines.join('\n');
}

function formatErrorAiResult(data) {
  if (!data || typeof data !== 'object') return '暂无分析结果';
  const lines = [];
  if (data.summary) lines.push(`分析结果：${data.summary}`);
  if (Array.isArray(data.suggestions) && data.suggestions.length) {
    lines.push('', '建议动作：');
    data.suggestions.forEach((item, idx) => lines.push(`${idx + 1}. ${item}`));
  }
  return lines.join('\n');
}

function formatAiReply(result) {
  if (!result || typeof result !== 'object') return 'AI 暂未返回有效内容。';
  return result.reply || result.summary || 'AI 暂未返回有效内容。';
}
function setLoginState(text) { $('loginState').textContent = text; }

function escapeHtml(value) {
  return String(value || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
function formatFileSize(bytes) {
  const size = Number(bytes || 0);
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function saveProfileState() {
  localStorage.setItem('aegis_profile', JSON.stringify(state.profile));
}

function applyProfileUI() {
  const avatar = state.profile.avatar || DEFAULT_AVATAR;
  const nickname = state.profile.nickname || '未设置昵称';
  const username = state.profile.username || $('username').value.trim() || 'admin';
  if ($('headerAvatar')) $('headerAvatar').src = avatar;
  if ($('profileAvatarPreview')) $('profileAvatarPreview').src = avatar;
  if ($('profileAvatarUrl')) $('profileAvatarUrl').value = state.profile.avatar || '';
  if ($('profileNickname')) $('profileNickname').value = state.profile.nickname || '';
  if ($('profileUsername')) $('profileUsername').value = username;
  if ($('profileSummaryName')) $('profileSummaryName').textContent = nickname;
  if ($('profileSummaryUser')) $('profileSummaryUser').textContent = username;
}

function summarizeBody(body) {
  if (body == null) return null;
  if (typeof body !== 'string') return body;
  try {
    const parsed = JSON.parse(body);
    if (parsed && typeof parsed === 'object') {
      const summary = { ...parsed };
      if (Array.isArray(summary.attachments)) {
        summary.attachments = summary.attachments.map((item) => ({
          name: item?.name,
          type: item?.type,
          size: item?.size,
          has_data_url: Boolean(item?.data_url),
        }));
      }
      return summary;
    }
    return parsed;
  } catch {
    return body.length > 200 ? `${body.slice(0, 200)}...` : body;
  }
}

function rememberLog(log) {
  state.requestLogs.unshift(log);
  if (state.requestLogs.length > 120) state.requestLogs = state.requestLogs.slice(0, 120);
  try {
    localStorage.setItem('aegis_request_logs', JSON.stringify(state.requestLogs));
  } catch {
    state.requestLogs = state.requestLogs.slice(0, 40);
    try {
      localStorage.setItem('aegis_request_logs', JSON.stringify(state.requestLogs));
    } catch {}
  }
}

function normalizeApiError(error, resp, data, url) {
  if (resp) {
    if (resp.status === 401) {
      state.token = '';
      clearStoredToken();
      return new Error('未登录或登录已过期，请重新登录后再试。');
    }
    if (resp.status === 403) return new Error('当前账号权限不足，无法执行该操作。');
    if (resp.status === 404) return new Error(`接口不存在：${url}`);
    return new Error((data && (data.message || data.detail)) || `HTTP ${resp.status}`);
  }

  if (error?.name === 'AbortError') {
    return new Error('请求超时，请稍后重试。');
  }

  const raw = error?.message || 'fetch failed';
  if (/Failed to fetch|NetworkError|Load failed|fetch failed/i.test(raw)) {
    return new Error('请求发送失败：请检查后端是否可达，或确认手机浏览器没有拦截 HTTPS 页面访问 HTTP 接口。');
  }

  return error instanceof Error ? error : new Error(String(raw));
}

async function api(path, options = {}) {
  const method = options.method || 'GET';
  const url = `${getBase()}${path}`;
  const started = Date.now();
  const timeoutMs = options.timeoutMs || 0;
  const controller = timeoutMs ? new AbortController() : null;
  const timeoutId = controller ? setTimeout(() => controller.abort(), timeoutMs) : null;
  try {
    const resp = await fetch(url, { ...options, signal: controller?.signal });
    const data = await resp.json().catch(() => ({}));
    rememberLog({ at: new Date().toISOString(), method, url, status: resp.status, ok: resp.ok, body: summarizeBody(options.body), response: data, duration_ms: Date.now() - started });
    if (!resp.ok) throw normalizeApiError(null, resp, data, url);
    return data;
  } catch (e) {
    if (e instanceof Error && /未登录或登录已过期|当前账号权限不足|接口不存在：|HTTP\s\d+/u.test(e.message || '')) {
      throw e;
    }
    const normalized = normalizeApiError(e, null, null, url);
    rememberLog({ at: new Date().toISOString(), method, url, status: 0, ok: false, network_error: normalized.message || 'fetch failed', duration_ms: Date.now() - started });
    throw normalized;
  } finally {
    if (timeoutId) clearTimeout(timeoutId);
  }
}

function switchScreen(loggedIn) {
  $('loginScreen').classList.toggle('active', !loggedIn);
  $('appScreen').classList.toggle('active', loggedIn);
}

const TAB_META = {
  'tab-workbench': { title: '工作台', subtitle: '今日待办、快捷操作与辅助工具' },
  'tab-inspection': { title: '巡检', subtitle: '扫码巡检、NFC 巡检与最近记录' },
  'tab-selfcheck': { title: '自检', subtitle: '系统自检与错误日志分析' },
  'tab-me': { title: '我的', subtitle: '账号信息、密码修改与登录设置' },
};

const DETAIL_PAGE_META = {
  'page-me-profile': '账号信息',
  'page-me-password': '修改密码',
  'page-inspection-qr': '扫码巡检',
  'page-inspection-nfc': 'NFC 巡检',
  'page-inspection-records': '最近巡检记录',
  'page-selfcheck-run': '系统自检',
  'page-selfcheck-errors': '错误日志分析',
  'page-tool-aiqa': 'AI 问答',
  'page-tool-ping': 'Ping 工具',
  'page-tool-capture': '抓包分析',
  'page-tool-emergency': '应急处置',
  'page-tool-tasks': '工具任务',
};

function updateTopbarByTab(tabId) {
  const meta = TAB_META[tabId] || TAB_META['tab-workbench'];
  if ($('appTopTitle')) $('appTopTitle').innerHTML = `${meta.title} <span class="badge">v2 UI</span>`;
  if ($('appTopSubtitle')) $('appTopSubtitle').textContent = meta.subtitle;
}

function switchTab(tabId) {
  state.activeTab = tabId;
  try {
    sessionStorage.setItem(ACTIVE_TAB_KEY, tabId);
  } catch {}
  document.querySelectorAll('.tab-screen').forEach((el) => el.classList.add('hidden'));
  document.querySelectorAll('.bottom-tab').forEach((el) => el.classList.remove('active'));
  $(tabId)?.classList.remove('hidden');
  document.querySelector(`.bottom-tab[data-tab="${tabId}"]`)?.classList.add('active');
  if (!state.activeDetailPage) {
    updateTopbarByTab(tabId);
  }
}

function getDetailPageTitle(pageId) {
  return document.querySelector(`#${pageId} .detail-topbar h2`)?.textContent?.trim()
    || DETAIL_PAGE_META[pageId]
    || '';
}

function openDetailPage(pageId) {
  state.activeDetailPage = pageId;
  document.querySelectorAll('.detail-screen').forEach((el) => el.classList.add('hidden'));
  $(pageId)?.classList.remove('hidden');
  const title = getDetailPageTitle(pageId);
  if (title && $('appTopTitle')) {
    $('appTopTitle').innerHTML = `${title} <span class="badge">v2 UI</span>`;
  }
  if ($('appTopSubtitle')) {
    $('appTopSubtitle').textContent = '功能页 · 点击返回回到上一层';
  }
}

function closeDetailPages() {
  state.activeDetailPage = '';
  document.querySelectorAll('.detail-screen').forEach((el) => el.classList.add('hidden'));
  updateTopbarByTab(state.activeTab || 'tab-workbench');
}

function saveAiMessages() {
  try {
    sessionStorage.setItem(AI_CHAT_HISTORY_KEY, JSON.stringify(state.aiMessages.slice(-80)));
    if (state.aiConversationId) {
      sessionStorage.setItem(AI_CHAT_CONVERSATION_KEY, state.aiConversationId);
    }
  } catch {}
}

function updateAiConversationMeta() {
  const el = $('aiConversationMeta');
  if (!el) return;
  const count = state.aiMessages.filter((item) => !item.welcome).length;
  const shortId = state.aiConversationId ? state.aiConversationId.slice(-6) : '------';
  const listCount = state.aiConversationItems.length;
  el.textContent = count
    ? `会话 ${shortId} · 当前已记录 ${count} 条消息 · 最近会话 ${listCount} 条。`
    : `会话 ${shortId} · 关闭应用后将自动清空，本次打开期间会保留当前对话 · 最近会话 ${listCount} 条。`;
}

function formatConversationTime(value) {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  return `${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function applyAiSidebarState() {
  const shell = $('aiChatShell');
  const toggleBtn = $('btnToggleAiSidebar');
  const showBtn = $('btnShowAiSidebar');
  if (!shell) return;
  const isMobile = window.innerWidth <= 640;
  shell.classList.toggle('sidebar-collapsed', state.aiSidebarCollapsed && !isMobile);
  shell.classList.toggle('sidebar-expanded-mobile', !state.aiSidebarCollapsed && isMobile);
  if (toggleBtn) {
    toggleBtn.textContent = state.aiSidebarCollapsed ? '显示历史' : '隐藏历史';
    toggleBtn.setAttribute('aria-expanded', String(!state.aiSidebarCollapsed));
  }
  if (showBtn) {
    showBtn.classList.toggle('hidden', !state.aiSidebarCollapsed);
    showBtn.setAttribute('aria-expanded', String(!state.aiSidebarCollapsed));
  }
}

function setAiSidebarCollapsed(collapsed) {
  state.aiSidebarCollapsed = Boolean(collapsed);
  localStorage.setItem(AI_CHAT_SIDEBAR_COLLAPSED_KEY, state.aiSidebarCollapsed ? '1' : '0');
  applyAiSidebarState();
}

function renderAiConversationList() {
  const box = $('aiConversationList');
  if (!box) return;
  if (!state.aiConversationItems.length) {
    box.classList.add('hidden');
    box.innerHTML = '';
    updateAiConversationMeta();
    return;
  }
  box.classList.remove('hidden');
  box.innerHTML = state.aiConversationItems.map((item) => {
    const active = item.conversation_id === state.aiConversationId ? ' active' : '';
    const preview = item.last_message || item.preview || item.summary || '暂无消息';
    return `
      <div class="ai-conversation-item${active}" data-ai-open-conversation="${escapeHtml(item.conversation_id)}">
        <div class="ai-conversation-item-head">
          <div class="ai-conversation-title">${escapeHtml(item.title || '新会话')}</div>
        </div>
        <div class="ai-conversation-preview">${escapeHtml(preview)}</div>
        <div class="ai-conversation-meta">${escapeHtml(formatConversationTime(item.updated_at) || '')}</div>
      </div>
    `;
  }).join('');
  box.querySelectorAll('[data-ai-open-conversation]').forEach((itemEl) => {
    itemEl.onclick = async () => {
      state.aiConversationId = itemEl.dataset.aiOpenConversation || '';
      saveAiMessages();
      await restoreAiConversationFromServer();
      renderAiConversationList();
      if (window.innerWidth <= 640) setAiSidebarCollapsed(true);
    };
  });
  updateAiConversationMeta();
}

function renderKeyValueRows(items = []) {
  return (items || []).map((item) => `
    <div class="assistant-card-row">
      <strong>${escapeHtml(item.label || item.system_name || item.result || '-')}</strong>
      <span>${escapeHtml(item.value || item.status_color || item.inspected_at || item.checked_at || '-')}</span>
    </div>
  `).join('');
}

function renderAssistantCards(cards = []) {
  if (!Array.isArray(cards) || !cards.length) return '';
  return `<div class="assistant-cards">${cards.map((card, cardIndex) => {
    const htmlButton = card.html_report
      ? `<button type="button" class="ghost small ai-html-card-btn" data-ai-html-card="${cardIndex}">打开 HTML 报告</button>`
      : '';
    if (card.type === 'system_status_overview') {
      const items = (card.items || []).map((item) => `
        <div class="assistant-card-row">
          <strong>${escapeHtml(item.system_name || '-')}</strong>
          <span>${escapeHtml(item.status_color || 'unknown')}</span>
        </div>
      `).join('');
      return `<div class="assistant-card"><div class="assistant-card-title">${escapeHtml(card.title || '系统状态')}</div><div class="assistant-card-desc">${escapeHtml(card.summary || '')}</div>${items}${htmlButton}</div>`;
    }
    if (card.type === 'system_detail') {
      const detail = card.detail || {};
      const snap = detail.status_snapshot || {};
      return `<div class="assistant-card"><div class="assistant-card-title">${escapeHtml(card.title || detail.system_name || '系统详情')}</div><div class="assistant-card-desc">编码：${escapeHtml(detail.system_code || '-')} · 环境：${escapeHtml(detail.env || '-')}</div>${renderKeyValueRows([
        { label: '状态', value: snap.status_color || 'unknown' },
        { label: 'CPU', value: snap.cpu_usage ?? '-' },
        { label: '内存', value: snap.mem_usage ?? '-' },
        { label: '磁盘', value: snap.disk_usage ?? '-' },
      ])}${htmlButton}</div>`;
    }
    if (card.type === 'inspection_records' || card.type === 'selfcheck_records' || card.type === 'system_selfcheck_report' || card.type === 'log_suggestions' || card.type === 'assistant_capabilities' || card.type === 'log_analysis') {
      const items = renderKeyValueRows(card.items || []);
      return `<div class="assistant-card"><div class="assistant-card-title">${escapeHtml(card.title || '记录')}</div><div class="assistant-card-desc">${escapeHtml(card.summary || '')}</div>${items || '<div class="assistant-card-desc">暂无内容</div>'}${htmlButton}</div>`;
    }
    if (card.type === 'pending_confirmation' || card.type === 'tool_task') {
      const detail = card.detail || {};
      return `<div class="assistant-card"><div class="assistant-card-title">${escapeHtml(card.title || '任务')}</div><div class="assistant-card-desc">${escapeHtml(JSON.stringify(detail))}</div>${htmlButton}</div>`;
    }
    return `<div class="assistant-card"><div class="assistant-card-title">${escapeHtml(card.title || '助手卡片')}</div>${htmlButton}</div>`;
  }).join('')}</div>`;
}

function renderAssistantActions(actions = []) {
  if (!Array.isArray(actions) || !actions.length) return '';
  return `<div class="assistant-actions">${actions.map((action, index) => `<button class="ghost small" data-assistant-action="${index}">${escapeHtml(action.label || action.type || '操作')}</button>`).join('')}</div>`;
}

function renderAiMessages() {
  const box = $('aiChatMessages');
  if (!box) return;
  box.innerHTML = state.aiMessages.map((item, index) => {
    const cls = item.role === 'user' ? 'user' : 'ai';
    const welcome = item.welcome ? ' welcome' : '';
    const pending = item.pending ? ' pending' : '';
    const attachments = Array.isArray(item.attachments) && item.attachments.length
      ? `<div class="hint" style="margin-top:8px;">附件：${item.attachments.map((f) => escapeHtml(f.name)).join('、')}</div>`
      : '';
    const retry = item.failed && index === state.aiMessages.length - 1
      ? '<div style="margin-top:8px;"><button class="ghost small" id="btnRetryAiMessage">重试</button></div>'
      : '';
    const cards = item.role === 'ai' ? renderAssistantCards(item.cards) : '';
    const actions = item.role === 'ai' ? renderAssistantActions(item.actions) : '';
    const htmlReport = item.role === 'ai' && !pending
      ? `<div class="ai-report-actions"><button type="button" class="ghost small" data-ai-open-html-report="${index}">打开 HTML 报告</button></div>`
      : '';
    return `<div class="chat-bubble ${cls}${welcome}${pending}">${escapeHtml(item.text)}${attachments}${cards}${actions}${htmlReport}${retry}</div>`;
  }).join('');
  const retryBtn = $('btnRetryAiMessage');
  if (retryBtn) retryBtn.onclick = retryLastAiMessage;
  box.querySelectorAll('[data-assistant-action]').forEach((btn) => {
    btn.onclick = async () => {
      const idx = Number(btn.dataset.assistantAction);
      const aiItems = state.aiMessages.filter((item) => item.role === 'ai' && Array.isArray(item.actions) && item.actions.length);
      const last = aiItems[aiItems.length - 1];
      const action = last?.actions?.[idx];
      if (!action) return;
      if (action.type === 'confirm_action') {
        await confirmAssistantAction(action.payload.action_id, true);
      } else if (action.type === 'cancel_action') {
        await confirmAssistantAction(action.payload.action_id, false);
      } else {
        await runAssistantOpenAction(action);
      }
    };
  });
  box.querySelectorAll('[data-ai-open-html-report]').forEach((btn) => {
    btn.onclick = () => {
      const item = state.aiMessages[Number(btn.dataset.aiOpenHtmlReport)];
      openAiHtmlReport(item);
    };
  });
  box.querySelectorAll('[data-ai-html-card]').forEach((btn) => {
    btn.onclick = () => {
      const bubble = btn.closest('.chat-bubble');
      const bubbleIndex = Array.from(box.querySelectorAll('.chat-bubble')).indexOf(bubble);
      const item = state.aiMessages[bubbleIndex];
      const card = item?.cards?.[Number(btn.dataset.aiHtmlCard)];
      openHtmlDocument(card?.html_report || buildAiHtmlReport(item));
    };
  });
  saveAiMessages();
  updateAiConversationMeta();
  requestAnimationFrame(() => {
    box.scrollTop = box.scrollHeight;
  });
}

function buildAiHtmlReport(item) {
  const title = 'Aegis AI 分析报告';
  const cardHtml = (item?.cards || []).map((card) => {
    const rows = (card.items || []).map((row) => `<tr><th>${escapeHtml(row.label || row.system_name || row.result || '-')}</th><td>${escapeHtml(row.value || row.status_color || row.inspected_at || row.checked_at || '-')}</td></tr>`).join('');
    return `<section><h2>${escapeHtml(card.title || '分析卡片')}</h2><p>${escapeHtml(card.summary || '')}</p>${rows ? `<table>${rows}</table>` : ''}</section>`;
  }).join('');
  return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${title}</title><style>body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;background:#f5f7fb;color:#162b3f}main{max-width:960px;margin:0 auto;padding:24px}section{background:#fff;border:1px solid #dce6f0;border-radius:12px;padding:18px;margin:14px 0}pre{white-space:pre-wrap;line-height:1.7}table{width:100%;border-collapse:collapse}th,td{text-align:left;border-bottom:1px solid #edf2f7;padding:10px;vertical-align:top}</style></head><body><main><h1>${title}</h1><section><h2>AI 回复</h2><pre>${escapeHtml(item?.text || '')}</pre></section>${cardHtml}</main></body></html>`;
}

function openHtmlDocument(html) {
  const blob = new Blob([html || '<!doctype html><html><body>暂无报告</body></html>'], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank', 'noopener');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

function openAiHtmlReport(item) {
  const cardWithHtml = (item?.cards || []).find((card) => card.html_report);
  openHtmlDocument(cardWithHtml?.html_report || buildAiHtmlReport(item));
}

function renderAiAttachmentList() {
  const box = $('aiAttachmentList');
  if (!box) return;
  box.innerHTML = state.aiAttachments.map((file, index) => {
    const preview = file.previewUrl && file.type?.startsWith('image/')
      ? `<img class="ai-attachment-preview" src="${file.previewUrl}" alt="${escapeHtml(file.name)}" />`
      : '';
    const warnClass = file.invalid ? ' warn' : '';
    const warnText = file.invalid ? `<div class="attachment-size" style="color:#ffd79a;">${escapeHtml(file.invalid)}</div>` : '';
    return `
      <div class="attachment-chip${warnClass}">
        <div class="attachment-meta">
          <div class="attachment-name">${escapeHtml(file.name)}</div>
          <div class="attachment-size">${escapeHtml(file.type || '未知类型')} · ${formatFileSize(file.size)}</div>
          ${warnText}
          ${preview}
        </div>
        <button class="attachment-remove" data-ai-remove="${index}">移除</button>
      </div>
    `;
  }).join('');

  box.querySelectorAll('[data-ai-remove]').forEach((btn) => {
    btn.onclick = () => {
      const idx = Number(btn.dataset.aiRemove);
      const item = state.aiAttachments[idx];
      if (item?.previewUrl) URL.revokeObjectURL(item.previewUrl);
      state.aiAttachments.splice(idx, 1);
      renderAiAttachmentList();
    };
  });
}

async function compressImageFile(file) {
  if (!file.type?.startsWith('image/') || file.size <= AI_MAX_FILE_SIZE) return file;
  return new Promise((resolve) => {
    const img = new Image();
    const reader = new FileReader();
    reader.onload = () => {
      img.onload = () => {
        const canvas = document.createElement('canvas');
        const maxWidth = 1600;
        const scale = Math.min(1, maxWidth / img.width);
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => {
          if (!blob) return resolve(file);
          const compressed = new File([blob], file.name, { type: 'image/jpeg' });
          resolve(compressed);
        }, 'image/jpeg', 0.78);
      };
      img.onerror = () => resolve(file);
      img.src = reader.result;
    };
    reader.onerror = () => resolve(file);
    reader.readAsDataURL(file);
  });
}

async function handleAiFileChange(event) {
  const files = Array.from(event.target.files || []);
  if (!files.length) return;

  const remainSlots = Math.max(0, AI_MAX_ATTACHMENTS - state.aiAttachments.length);
  const accepted = files.slice(0, remainSlots);
  const droppedCount = Math.max(0, files.length - accepted.length);

  for (const originalFile of accepted) {
    const processedFile = await compressImageFile(originalFile);
    state.aiAttachments.push({
      file: processedFile,
      name: processedFile.name,
      size: processedFile.size,
      type: processedFile.type,
      invalid: processedFile.size > AI_MAX_FILE_SIZE ? `附件过大，建议控制在 ${formatFileSize(AI_MAX_FILE_SIZE)} 以内` : '',
      previewUrl: processedFile.type?.startsWith('image/') ? URL.createObjectURL(processedFile) : '',
    });
  }

  if (droppedCount > 0) {
    $('aiQaResult').textContent = `最多支持 ${AI_MAX_ATTACHMENTS} 个附件，其余 ${droppedCount} 个未加入。`;
  } else {
    $('aiQaResult').textContent = `已选择 ${accepted.length} 个附件，发送时将一并提交给 AI。`;
  }
  renderAiAttachmentList();
  event.target.value = '';
}

async function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error(`读取文件失败：${file.name}`));
    reader.readAsDataURL(file);
  });
}

async function ensureAiConversation() {
  if (state.aiConversationId) return state.aiConversationId;
  const result = await api('/api/v1/ai/conversations', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ title: '新会话', source: 'mobile' }),
  });
  state.aiConversationId = result.conversation_id;
  saveAiMessages();
  updateAiConversationMeta();
  return state.aiConversationId;
}

async function restoreAiConversationFromServer() {
  if (!state.aiConversationId) return;
  try {
    const detail = await api(`/api/v1/ai/conversations/${state.aiConversationId}`, {
      headers: authHeaders(),
      timeoutMs: 15000,
    });
    state.aiMessages = mapConversationMessagesToUi(detail.messages);
    renderAiMessages();
    renderAiConversationList();
    $('aiQaResult').textContent = detail.message_count
      ? `已恢复当前会话，共 ${detail.message_count} 条消息。`
      : '当前会话暂无历史消息。';
  } catch (e) {
    state.aiConversationId = '';
    sessionStorage.removeItem(AI_CHAT_CONVERSATION_KEY);
    state.aiMessages = buildDefaultAiMessages();
    renderAiMessages();
    renderAiConversationList();
    $('aiQaResult').textContent = '之前的会话未恢复成功，已自动切回新会话。';
  }
}

async function refreshAiConversationList() {
  try {
    const result = await api('/api/v1/ai/conversations', {
      headers: authHeaders(),
      timeoutMs: 15000,
    });
    state.aiConversationItems = Array.isArray(result.items)
      ? result.items.filter((item) => Number(item.message_count || 0) > 0)
      : [];
    renderAiConversationList();
    return result.items || [];
  } catch (e) {
    state.aiConversationItems = [];
    renderAiConversationList();
    $('aiQaResult').textContent = '读取最近会话失败，请稍后重试。';
    return [];
  }
}

async function uploadAiAttachment(item) {
  const dataUrl = await fileToDataUrl(item.file);
  const result = await api('/api/v1/ai/files/upload', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      conversation_id: state.aiConversationId,
      name: item.name,
      type: item.type || 'application/octet-stream',
      size: item.size,
      data_url: dataUrl,
    }),
  });
  return result.file;
}

async function appendAssistantResult(result, fallbackText = '操作已完成。') {
  state.aiMessages.push({
    role: 'ai',
    text: result.reply || fallbackText,
    cards: result.cards || [],
    actions: result.actions || [],
    data: result.data || {},
  });
  renderAiMessages();
}

async function confirmAssistantAction(actionId, confirmed) {
  const result = await api('/api/v1/assistant/confirm', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({
      conversation_id: state.aiConversationId,
      action_id: actionId,
      confirmed,
    }),
    timeoutMs: 45000,
  });

  await appendAssistantResult(result, '操作已完成。');
  $('aiQaResult').textContent = confirmed ? '助手已执行确认动作。' : '已取消执行。';
}

async function runAssistantQuickPrompt(message) {
  if (!message) return;
  $('aiQuestionInput').value = message;
  await sendAiQuestion();
}

function resolveAssistantAction(action) {
  const payload = action?.payload || {};
  const type = action?.type || '';
  if ((type === 'open_system_detail' || type === 'open_first_abnormal_system_detail') && payload.system_name) {
    return { kind: 'message', message: `帮我看${payload.system_name}详情` };
  }
  if (type === 'open_inspection_records' && payload.system_name) {
    return { kind: 'message', message: `看看${payload.system_name}最近巡检记录` };
  }
  if (type === 'open_selfcheck_records' && payload.system_name) {
    return { kind: 'message', message: `看看${payload.system_name}最近自检记录` };
  }
  if (type === 'open_abnormal_systems') {
    return { kind: 'message', message: '帮我查今天有哪些异常系统' };
  }
  if (['repeat_intent', 'quick_prompt', 'refresh_abnormal_systems', 'refresh_inspection_records', 'refresh_selfcheck_records'].includes(type) && payload.message) {
    return { kind: 'message', message: payload.message };
  }
  return { kind: 'unsupported', message: '' };
}

async function runAssistantOpenAction(action) {
  const resolved = resolveAssistantAction(action);
  if (resolved.kind === 'message' && resolved.message) {
    await runAssistantQuickPrompt(resolved.message);
    return;
  }
  $('aiQaResult').textContent = `暂未接入动作：${action.label || action.type}`;
}

async function sendAiQuestion(reusePayload = null) {
  if (state.isSendingAiMessage) return;
  const inputEl = $('aiQuestionInput');
  const question = reusePayload?.question ?? inputEl.value.trim();
  if (!question && !state.aiAttachments.length) {
    $('aiQaResult').textContent = '请先输入问题，或至少上传一个附件。';
    return;
  }

  const attachmentsSource = reusePayload?.attachmentsSource ?? state.aiAttachments;
  const invalidAttachment = attachmentsSource.find((item) => item.invalid);
  if (invalidAttachment) {
    $('aiQaResult').textContent = `附件“${invalidAttachment.name}”过大，请先压缩或移除后再发送。`;
    return;
  }

  state.isSendingAiMessage = true;
  setButtonLoading('btnSendAiQuestion', true, 'AI 回复中...');

  const attachmentMeta = attachmentsSource.map((item) => ({
    name: item.name,
    size: item.size,
    type: item.type || 'application/octet-stream',
  }));

  if (!reusePayload) {
    state.aiMessages.push({ role: 'user', text: question || '请帮我分析这些附件。', attachments: attachmentMeta });
  }
  inputEl.value = '';
  state.aiMessages.push({ role: 'ai', text: 'AI 正在思考中，请稍等...', pending: true });
  renderAiMessages();
  $('aiQaResult').textContent = 'AI 正在分析，请稍等...';

  try {
    await ensureAiConversation();
    $('aiQaResult').textContent = attachmentsSource.length ? '正在上传附件，请稍等...' : '正在整理上下文，请稍等...';
    const uploadedFiles = reusePayload?.uploadedFiles ?? await Promise.all(attachmentsSource.map(uploadAiAttachment));

    $('aiQaResult').textContent = uploadedFiles.length ? '附件上传完成，正在整理上下文...' : '正在整理上下文，请稍等...';

    const payload = {
      message: question,
      conversation_id: state.aiConversationId,
      attachments: uploadedFiles.map((item) => ({
        file_id: item.file_id,
        name: item.name,
        type: item.type,
        size: item.size,
      })),
    };
    state.lastAiRequestPayload = {
      question,
      attachmentsSource,
      uploadedFiles,
    };
    $('aiQaResult').textContent = 'AI 助手正在调用移动端能力，请稍等...';
    const result = await api('/api/v1/assistant/chat', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(payload),
      timeoutMs: 45000,
    });
    const reply = formatAiReply(result);
    state.aiMessages = state.aiMessages.filter((item) => !item.pending);
    const hasUserBubble = state.aiMessages.some((item) => item.role === 'user' && item.text === (question || '请帮我分析这些附件。'));
    if (!hasUserBubble) {
      state.aiMessages.push({ role: 'user', text: question || '请帮我分析这些附件。', attachments: attachmentMeta });
    }
    state.aiMessages.push({
      role: 'ai',
      text: reply,
      cards: result.cards || [],
      actions: result.actions || [],
      data: result.data || {},
    });
    renderAiMessages();
    $('aiQaResult').textContent = 'AI 助手已返回结果。';
    state.aiAttachments.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
    state.aiAttachments = [];
    renderAiAttachmentList();
  } catch (e) {
    const msg = e.name === 'AbortError'
      ? 'AI 响应超时，请稍后重试或缩短问题内容。'
      : explainActionError(e, 'AI 问答', 'admin / super_admin');
    state.aiMessages = state.aiMessages.filter((item) => !item.pending);
    const hasUserBubble = state.aiMessages.some((item) => item.role === 'user' && item.text === (question || '请帮我分析这些附件。'));
    if (!hasUserBubble) {
      state.aiMessages.push({ role: 'user', text: question || '请帮我分析这些附件。', attachments: attachmentMeta });
    }
    state.aiMessages.push({ role: 'ai', text: `处理失败：${msg}`, failed: true });
    renderAiMessages();
    $('aiQaResult').textContent = msg;
  } finally {
    state.isSendingAiMessage = false;
    setButtonLoading('btnSendAiQuestion', false);
  }
}

function retryLastAiMessage() {
  if (!state.lastAiRequestPayload) {
    $('aiQaResult').textContent = '没有可重试的上一条 AI 请求。';
    return;
  }
  state.aiMessages = state.aiMessages.filter((item) => !item.failed);
  renderAiMessages();
  sendAiQuestion(state.lastAiRequestPayload);
}

function initSubNavigation() {
  onClick('btnUserCenter', () => {
    stopStatusLoop();
    switchTab('tab-me');
    closeDetailPages();
    applyProfileUI();
  });

  document.querySelectorAll('[data-open-page]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      const pageId = btn.dataset.openPage;
      if (!pageId) return;

      if (pageId === 'page-inspection-qr') {
        state.qrScanText = '';
        state.qrResolvedPoint = null;
        if ($('inspectionPointName')) $('inspectionPointName').value = '';
        renderInspectionChecklist([], null);
        setQrScanState('点击“调用相机扫码”，识别后会自动填充机房信息。');
        show('inspectionResult', '');
      }

      if (pageId === 'page-selfcheck-run') {
        await beginSelfcheckFlow();
        return;
      }

      openDetailPage(pageId);

      if (pageId === 'page-selfcheck-errors') {
        $('errorAiView').textContent = '先加载系统日志，再点击“AI 分析”生成结论与建议。';
        renderErrorSystemOptions();
        syncLogFileOptions();
        refreshErrorSystems().catch(() => {});
      }

      if (pageId === 'page-tool-aiqa') {
        $('aiQaResult').textContent = '支持纯文字问答，也支持带附件一起发起分析。';
        renderAiMessages();
        renderAiAttachmentList();
        await refreshAiConversationList();
        if (state.aiConversationId) await restoreAiConversationFromServer();
      }

      if (pageId === 'page-tool-ping') {
        $('pingResult').textContent = '输入目标地址后点击“执行 Ping”，查看网络连通情况。';
      }

      if (pageId === 'page-tool-capture') {
        $('captureResult').textContent = '输入 URL 后点击“抓取 URL”，再点“AI 分析抓包内容”即可。';
      }

      if (pageId === 'page-tool-emergency') {
        await loadEmergencyActions();
      }

      if (pageId === 'page-tool-tasks') {
        $('toolTaskResult').textContent = '正在加载最近工具任务...';
        $('btnRefreshToolTasks')?.click();
      }
    });
  });

  document.querySelectorAll('[data-close-page]').forEach((btn) => {
    btn.addEventListener('click', () => {
      closeDetailPages();
      stopStatusLoop();
      stopQrScanner();
      stopNfcScanner();
    });
  });
}

function bindEmergencyToolActions() {
  document.querySelectorAll('[data-emergency-section]').forEach((btn) => {
    btn.addEventListener('click', () => selectEmergencySection(btn.dataset.emergencySection || 'server'));
  });

  document.addEventListener('click', async (event) => {
    const btn = event.target.closest('[data-emergency-action-code]');
    if (!btn) return;
    const actionCode = btn.dataset.emergencyActionCode;
    const actionName = btn.dataset.emergencyActionName || actionCode;
    if (!actionCode) return;
    if (!window.confirm(`确认发起【${actionName}】？`)) return;
    try {
      const data = await api('/api/v1/emergency/actions/execute', {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ action_code: actionCode }),
      });
      alert(`已提交应急任务\n任务ID：${data.task_id}\n状态：${data.status}\n目标：${data.target || '-'}`);
      showToast('应急任务已提交', 'success');
    } catch (e) {
      alert(`提交失败\n${e.message || e}`);
    }
  });

  onClick('btnOpenFocPasswordQuery', () => {
    $('focPasswordQueryPanel')?.classList.toggle('hidden');
    $('dbEmergencyHint').textContent = $('focPasswordQueryPanel')?.classList.contains('hidden')
      ? '数据库动作后续通过管理端配置 SQL / SSH 命令模板执行。'
      : '请按系统 + 工号发起查询，当前先展示前端流程与弹窗结果。';
  });

  onClick('btnFocDeadlockHandle', () => {
    show('dbEmergencyResult', '已触发【FOC 死锁处理】前端占位流程。后续这里会调用管理端配置的死锁处理脚本。');
    showToast('FOC 死锁处理流程已预留。');
  });

  onClick('btnFocFlashback', () => {
    show('dbEmergencyResult', '已触发【FOC 数据库闪回】前端占位流程。后续这里会调用管理端配置的闪回脚本。');
    showToast('FOC 数据库闪回流程已预留。');
  });

  onClick('btnDbTablespace', () => {
    show('dbEmergencyResult', '已触发【数据库表空间】前端占位流程。后续这里会调用管理端配置的表空间查询命令。');
    showToast('数据库表空间流程已预留。');
  });

  document.querySelectorAll('[data-server-restart]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.serverRestart || '目标服务器';
      show('serverEmergencyResult', `已选择服务器【${name}】执行重启。当前为前端演示流程，后续将通过管理端配置 SSH 命令执行。`);
      showToast(`已发起 ${name} 重启流程`, 'success');
    });
  });

  document.querySelectorAll('[data-process-restart]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.processRestart || '目标进程';
      show('processEmergencyResult', `已选择进程【${name}】执行重启。当前为前端演示流程，后续将通过管理端配置命令执行。`);
      showToast(`已发起 ${name} 重启流程`, 'success');
    });
  });

  document.querySelectorAll('[data-process-stop]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const name = btn.dataset.processStop || '目标进程';
      show('processEmergencyResult', `已选择进程【${name}】执行关闭。当前为前端演示流程，后续将通过管理端配置命令执行。`);
      showToast(`已发起 ${name} 关闭流程`);
    });
  });

  document.querySelectorAll('[data-foc-query]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const idx = btn.dataset.focQuery;
      const system = $(`focSystem${idx}`)?.value || '';
      const emp = $(`focEmp${idx}`)?.value?.trim() || '';
      if (!emp) {
        showToast('请先输入工号', 'error');
        return;
      }
      alert(`查询结果\n系统：${system}\n工号：${emp}\n\n当前为前端演示弹窗。\n后续会通过管理端配置的数据库查询命令返回真实结果。`);
    });
  });
}

async function loadEmergencyActions() {
  state.activeEmergencySection = '';
  setEmergencyCardsVisible('');
  $('emergencyMenuHint').textContent = '正在加载管理端配置...';
  try {
    state.emergencyActions = await api('/api/v1/emergency/actions', { headers: authHeaders() });
    renderEmergencySubmenus();
    renderEmergencyLists();
    $('emergencyMenuHint').textContent = '请选择要处理的应急类型。';
  } catch (e) {
    $('emergencyMenuHint').textContent = explainActionError(e, '应急处置配置', 'admin / super_admin');
  }
}

function setEmergencyCardsVisible(section) {
  const serverCard = $('serverEmergencyList')?.closest('.emergency-card');
  const processCard = $('processEmergencyList')?.closest('.emergency-card');
  const dbCard = $('dbEmergencyList')?.closest('.emergency-card');
  if (serverCard) serverCard.classList.toggle('hidden', section !== 'server');
  if (processCard) processCard.classList.toggle('hidden', section !== 'process');
  if (dbCard) dbCard.classList.toggle('hidden', section !== 'database');
}

function selectEmergencySection(section) {
  state.activeEmergencySection = section;
  setEmergencyCardsVisible(section);
  document.querySelectorAll('[data-emergency-section]').forEach((btn) => {
    btn.classList.toggle('secondary', btn.dataset.emergencySection !== section);
  });
}

function renderEmergencySubmenus() {
  const host = $('emergencySubmenuList');
  if (!host) return;
  const submenus = [
    { section: 'server', label: '系统重启', count: state.emergencyActions.server_actions?.length || 0 },
    { section: 'process', label: '应用重启', count: state.emergencyActions.process_actions?.length || 0 },
    { section: 'database', label: '数据库死锁处理', count: state.emergencyActions.database_actions?.length || 0 },
  ];
  host.innerHTML = submenus.map((item, index) => `
    <button type="button" class="${index ? 'secondary' : ''}" data-emergency-section="${item.section}">
      ${escapeHtml(item.label)}（${item.count}）
    </button>
  `).join('');
  host.querySelectorAll('[data-emergency-section]').forEach((btn) => {
    btn.addEventListener('click', () => selectEmergencySection(btn.dataset.emergencySection || 'server'));
  });
}

function renderEmergencyActionTable(hostId, actions, emptyText, columns) {
  const host = $(hostId);
  if (!host) return;
  if (!actions.length) {
    host.innerHTML = `<div class="hint">${escapeHtml(emptyText)}</div>`;
    return;
  }
  host.innerHTML = `
    ${columns.map((col) => `<div class="emergency-table-head">${escapeHtml(col.label)}</div>`).join('')}
    <div class="emergency-table-head">操作</div>
    ${actions.map((item) => `
      ${columns.map((col) => `<div class="emergency-table-cell">${escapeHtml(col.value(item) || '-')}</div>`).join('')}
      <button class="warn-action emergency-table-btn" data-emergency-action-code="${escapeHtml(item.action_code)}" data-emergency-action-name="${escapeHtml(item.action_name)}">执行</button>
    `).join('')}
  `;
}

function renderEmergencyLists() {
  renderEmergencyActionTable(
    'serverEmergencyList',
    state.emergencyActions.server_actions || [],
    '暂无可执行的系统重启动作。',
    [
      { label: '主机名', value: (item) => item.host_name },
      { label: 'IP', value: (item) => item.host_ip },
      { label: '命令', value: (item) => item.action_name },
    ],
  );
  renderEmergencyActionTable(
    'processEmergencyList',
    state.emergencyActions.process_actions || [],
    '暂无可执行的应用重启动作。',
    [
      { label: '系统', value: (item) => item.system_name },
      { label: '进程', value: (item) => item.process_name || item.action_name },
      { label: '主机', value: (item) => item.host_name },
    ],
  );
  renderEmergencyActionTable(
    'dbEmergencyList',
    state.emergencyActions.database_actions || [],
    '暂无可执行的数据库死锁处理动作。',
    [
      { label: '系统', value: (item) => item.system_name },
      { label: '动作', value: (item) => item.action_name },
      { label: '主机', value: (item) => item.host_name },
    ],
  );
}

function bindCaptureToolActions() {
  const btnFetch = $('btnFetchCaptureUrl');
  const btnAnalyze = $('btnAnalyzeCapture');

  if (btnFetch) {
    btnFetch.onclick = async () => {
      const url = $('captureUrl').value.trim();
      if (!url) {
        $('captureAiStatus').textContent = '请先输入要抓取的 URL。';
        return;
      }
      setButtonLoading('btnFetchCaptureUrl', true, '抓取中...');
      $('captureAiStatus').textContent = '正在抓取 URL，请稍等...';
      try {
        const data = await api('/api/v1/toolbox/capture/fetch', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({
            url,
            note: $('captureNote').value.trim(),
          }),
          timeoutMs: 20000,
        });
        $('captureContent').value = data.content || '';
        $('captureResult').textContent = `抓取完成：HTTP ${data.status_code || '-'} · ${data.elapsed_ms || 0}ms`;
        $('captureAiStatus').textContent = 'URL 抓取完成，可直接点 AI 分析。';
      } catch (e) {
        $('captureResult').textContent = explainActionError(e, 'URL 抓取', 'admin / super_admin');
        $('captureAiStatus').textContent = 'URL 抓取失败，请检查地址后重试。';
      } finally {
        setButtonLoading('btnFetchCaptureUrl', false);
      }
    };
  }

  if (btnAnalyze) {
    btnAnalyze.onclick = async () => {
      if (state.isAnalyzingCapture) return;
      const content = $('captureContent').value.trim();
      if (!content) {
        $('captureAiStatus').textContent = '请先抓取 URL，生成抓取结果。';
        return;
      }
      state.isAnalyzingCapture = true;
      setButtonLoading('btnAnalyzeCapture', true, 'AI 分析中...');
      $('captureAiStatus').textContent = 'AI 正在分析抓包内容，请稍等...';
      try {
        const data = await api('/api/v1/toolbox/capture/analyze', {
          method: 'POST',
          headers: authHeaders(),
          body: JSON.stringify({
            title: '抓包结果分析',
            content,
            severity: $('captureAiSeverity').value,
            source: 'url_fetch',
            note: $('captureNote').value.trim() || $('captureUrl').value.trim(),
          }),
          timeoutMs: 45000,
        });
        $('captureResult').textContent = formatCaptureAiResult(data);
        $('captureAiStatus').textContent = 'AI 分析完成。';
      } catch (e) {
        $('captureResult').textContent = explainActionError(e, '抓包 AI 分析', 'admin / super_admin');
        $('captureAiStatus').textContent = 'AI 分析失败，请稍后重试。';
      } finally {
        state.isAnalyzingCapture = false;
        setButtonLoading('btnAnalyzeCapture', false);
      }
    };
  }
}

function pushMetric(key, val) {
  const arr = state.metricSeries[key];
  arr.push(Math.max(0, Math.min(100, Number(val) || 0)));
  if (arr.length > 24) arr.shift();
}

function drawLine(canvasId, values, color) {
  const canvas = $(canvasId);
  const ctx = canvas.getContext('2d');
  const { width, height } = canvas;
  ctx.clearRect(0, 0, width, height);

  const padL = 34;
  const padR = 8;
  const padT = 10;
  const padB = 20;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  // grid + Y axis percentage labels
  ctx.strokeStyle = '#10324a';
  ctx.fillStyle = '#000000';
  ctx.font = '10px sans-serif';
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i++) {
    const ratio = i / 4;
    const y = padT + plotH * ratio;
    ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(width - padR, y); ctx.stroke();
    const label = `${Math.round((1 - ratio) * 100)}%`;
    ctx.fillText(label, 2, y + 3);
  }

  // X axis time labels
  const now = new Date();
  const t0 = new Date(now.getTime() - Math.max(values.length - 1, 1) * 2500);
  const fmt = (d) => `${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
  ctx.fillText(fmt(t0), padL, height - 4);
  ctx.fillText(fmt(now), width - padR - 30, height - 4);

  // axis lines
  ctx.strokeStyle = '#000000';
  ctx.beginPath(); ctx.moveTo(padL, padT); ctx.lineTo(padL, height - padB); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(padL, height - padB); ctx.lineTo(width - padR, height - padB); ctx.stroke();

  if (!values.length) return;

  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = padL + (i / Math.max(values.length - 1, 1)) * plotW;
    const y = padT + (1 - (v / 100)) * plotH;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // latest point label
  const last = values[values.length - 1];
  const lx = padL + plotW;
  const ly = padT + (1 - (last / 100)) * plotH;
  ctx.fillStyle = color;
  ctx.beginPath(); ctx.arc(lx, ly, 2.5, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#000000';
  ctx.fillText(`${Math.round(last)}%`, Math.max(padL, lx - 28), Math.max(10, ly - 6));
}

function renderCharts() {
  drawLine('cpuChart', state.metricSeries.cpu, '#2dd4bf');
  drawLine('memChart', state.metricSeries.mem, '#38bdf8');
  drawLine('diskChart', state.metricSeries.disk, '#fb7185');
}

function renderStatusSystemOptions() {
  const sel = $('scStatusSystem');
  if (!sel) return;
  const current = state.selectedStatusSystemId;

  sel.innerHTML = '';
  if (!state.statusSystems.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '暂无系统可选';
    sel.appendChild(opt);
    state.selectedStatusSystemId = null;
    if ($('statusSystemHint')) $('statusSystemHint').textContent = '未查询到系统，请先在后台创建系统或采集快照。';
    return;
  }

  state.statusSystems.forEach((item) => {
    const opt = document.createElement('option');
    opt.value = String(item.system_id);
    opt.textContent = `${item.system_name}（${item.system_code || 'N/A'}）`;
    sel.appendChild(opt);
  });

  const hasCurrent = state.statusSystems.some((s) => Number(s.system_id) === Number(current));
  state.selectedStatusSystemId = hasCurrent ? Number(current) : Number(state.statusSystems[0].system_id);
  sel.value = String(state.selectedStatusSystemId);
}

function renderErrorSystemOptions() {
  const sel = $('errorSystem');
  if (!sel) return;
  const current = state.selectedLogSystemId || state.selectedStatusSystemId;
  sel.innerHTML = '';
  if (!state.statusSystems.length) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = '暂无系统可选';
    sel.appendChild(opt);
    state.selectedLogSystemId = null;
    return;
  }

  state.statusSystems.forEach((item) => {
    const opt = document.createElement('option');
    opt.value = String(item.system_id);
    opt.textContent = `${item.system_name}（${item.system_code || 'N/A'}）`;
    sel.appendChild(opt);
  });
  const hasCurrent = state.statusSystems.some((s) => Number(s.system_id) === Number(current));
  state.selectedLogSystemId = hasCurrent ? Number(current) : Number(state.statusSystems[0].system_id);
  sel.value = String(state.selectedLogSystemId);
}

async function refreshStatusBase() {
  try {
    const systemsData = await api('/api/v1/systems/accessible', { headers: authHeaders() });
    renderAccessibleSystems(systemsData.items || []);

    const monitoringData = await api('/api/v1/monitoring/overview', { headers: authHeaders() }).catch(() => ({ items: [] }));
    const monitoringById = new Map((monitoringData.items || []).map((item) => [Number(item.system_id), item]));
    state.statusSystems = state.statusSystems.map((system) => ({
      ...monitoringById.get(Number(system.system_id)),
      ...system,
    }));
    renderStatusSystemOptions();
    renderErrorSystemOptions();
    syncLogFileOptions();

    const selected = state.statusSystems.find((i) => Number(i.system_id) === Number(state.selectedStatusSystemId));
    const target = selected || state.statusSystems[0] || {};

    if ($('statusSystemHint')) {
      $('statusSystemHint').textContent = target.system_id
        ? `当前系统：${target.system_name || target.system_code || target.system_id}`
        : '未查询到系统，请先在后台创建系统或采集快照。';
    }

    const cpu = target?.cpu_usage ?? (Math.random() * 100);
    const mem = target?.mem_usage ?? (Math.random() * 100);
    const disk = target?.disk_usage ?? (Math.random() * 100);
    pushMetric('cpu', cpu); pushMetric('mem', mem); pushMetric('disk', disk);
    renderCharts();
  } catch {
    pushMetric('cpu', 40 + Math.random() * 30);
    pushMetric('mem', 35 + Math.random() * 35);
    pushMetric('disk', 45 + Math.random() * 25);
    if ($('statusSystemHint')) $('statusSystemHint').textContent = '状态接口调用失败，已展示本地模拟曲线。';
    renderCharts();
  }
}

function renderAccessibleSystems(items, options = {}) {
  state.statusSystems = (items || []).map((system) => ({
    system_id: system.system_id,
    system_code: system.system_code,
    system_name: system.system_name,
    host_address: system.host_address,
    env: system.env,
    selfcheck_skill: system.selfcheck_skill,
  }));
  if (options.replaceLogConfigs) {
    const nextConfigs = {};
    (items || []).forEach((system) => {
      nextConfigs[Number(system.system_id)] = Array.isArray(system.log_configs) ? system.log_configs : [];
    });
    state.logConfigsBySystem = nextConfigs;
  }
  renderStatusSystemOptions();
  renderErrorSystemOptions();
}

function closeSelfcheckSystemModal() {
  $('selfcheckSystemModal')?.classList.add('hidden');
}

function renderSelfcheckSystemPicker() {
  const host = $('selfcheckSystemPickerList');
  if (!host) return;
  host.innerHTML = (state.statusSystems || []).map((item) => `
    <button type="button" class="system-picker-row" data-selfcheck-system-id="${escapeHtml(item.system_id)}">
      <strong>${escapeHtml(item.system_name || item.system_code || item.system_id)}</strong>
      <span>${escapeHtml(item.host_address || '未配置 IP')} · ${escapeHtml(item.env || '-')}</span>
    </button>
  `).join('') || '<div class="hint">暂无可选系统</div>';
}

async function beginSelfcheckFlow() {
  stopStatusLoop();
  await refreshStatusBase();
  if (!state.statusSystems.length) {
    openDetailPage('page-selfcheck-run');
    show('selfcheckAiReport', '暂无可用系统，请先在管理端配置系统。');
    return;
  }
  if (state.statusSystems.length === 1) {
    await openSelfcheckPageForSystem(state.statusSystems[0].system_id);
    return;
  }
  renderSelfcheckSystemPicker();
  $('selfcheckSystemModal')?.classList.remove('hidden');
}

async function openSelfcheckPageForSystem(systemId) {
  closeSelfcheckSystemModal();
  state.selectedStatusSystemId = Number(systemId) || null;
  openDetailPage('page-selfcheck-run');
  renderStatusSystemOptions();
  if ($('scStatusSystem')) $('scStatusSystem').value = String(state.selectedStatusSystemId || '');
  show('selfcheckAiReport', '请选择系统后点击“开始 AI 自检”生成报告。');
  syncSelfcheckTimerUi();
  await loadSelfcheckReports({ recent: true }).catch(() => {});
}

function formatUsage(value) {
  return value === null || value === undefined ? '-' : `${Math.round(Number(value))}%`;
}

function renderSelfcheckStatus(data) {
  const latest = data?.status?.latest || null;
  const system = data?.system || {};
  const summary = $('selfcheckStatusSummary');
  if (summary) {
    summary.innerHTML = latest ? `
      <div class="check-row"><span>系统</span><strong>${escapeHtml(system.system_name || '-')}</strong></div>
      <div class="check-row"><span>IP / 地址</span><strong>${escapeHtml(system.host_address || '未配置')}</strong></div>
      <div class="check-row"><span>状态</span><strong>${escapeHtml(latest.status_color || 'unknown')}</strong></div>
      <div class="check-row"><span>CPU</span><strong>${escapeHtml(formatUsage(latest.cpu_usage))}</strong></div>
      <div class="check-row"><span>内存</span><strong>${escapeHtml(formatUsage(latest.mem_usage))}</strong></div>
      <div class="check-row"><span>硬盘</span><strong>${escapeHtml(formatUsage(latest.disk_usage))}</strong></div>
      <div class="check-row"><span>采集时间</span><strong>${escapeHtml(latest.captured_at || '-')}</strong></div>
    ` : '<div class="hint">当前系统暂无状态快照。</div>';
  }
  const series = data?.status?.series || [];
  state.metricSeries = {
    cpu: series.map((item) => Number(item.cpu_usage)).filter((v) => Number.isFinite(v)),
    mem: series.map((item) => Number(item.mem_usage)).filter((v) => Number.isFinite(v)),
    disk: series.map((item) => Number(item.disk_usage)).filter((v) => Number.isFinite(v)),
  };
  renderCharts();
}

function renderSelfcheckAlarms(alarms = []) {
  const host = $('selfcheckAlarmList');
  if (!host) return;
  host.innerHTML = alarms.length ? alarms.map((item) => `
    <div class="check-row">
      <span>${escapeHtml(item.captured_at || '-')}</span>
      <strong>${escapeHtml((item.reasons || []).join('，') || '告警')}</strong>
    </div>
  `).join('') : '<div class="hint">当前时间范围内暂无告警。</div>';
}

function renderSelfcheckAiReport(data) {
  const report = data?.ai_report;
  if (!data?.system?.selfcheck_skill) {
    show('selfcheckAiReport', '暂未配置ai自检项目');
    return;
  }
  if (!report) {
    show('selfcheckAiReport', 'AI 自检报告生成失败，请稍后重试。');
    return;
  }
  const suggestions = Array.isArray(report.suggestions) && report.suggestions.length
    ? `\n\n建议：\n${report.suggestions.map((item, idx) => `${idx + 1}. ${item}`).join('\n')}`
    : '';
  show('selfcheckAiReport', `${report.reply || report.summary || 'AI 已返回自检报告。'}${suggestions}`);
}

function loadSelfcheckTimerConfig() {
  try {
    const data = JSON.parse(localStorage.getItem(AI_SELFCHECK_TIMER_KEY) || 'null');
    if (data && typeof data === 'object') return data;
  } catch {}
  return { interval_minutes: 0, next_at: '', system_id: null, range_minutes: 60 };
}

function saveSelfcheckTimerConfig(config) {
  state.aiSelfcheckTimer = config;
  localStorage.setItem(AI_SELFCHECK_TIMER_KEY, JSON.stringify(config));
  syncSelfcheckTimerUi();
  startSelfcheckTimerLoop();
}

function syncSelfcheckTimerUi() {
  const config = state.aiSelfcheckTimer || loadSelfcheckTimerConfig();
  state.aiSelfcheckTimer = config;
  if ($('selfcheckTimerInterval')) $('selfcheckTimerInterval').value = String(config.interval_minutes || 0);
  if ($('selfcheckTimerNextAt')) $('selfcheckTimerNextAt').value = config.next_at || '';
  const hint = $('selfcheckTimerHint');
  if (!hint) return;
  if (!config.interval_minutes) {
    hint.textContent = '定时 AI 自检已关闭。';
    return;
  }
  hint.textContent = `定时 AI 自检已开启：每 ${config.interval_minutes} 分钟执行一次，下次执行 ${config.next_at || '待设置'}。`;
}

function readSelfcheckTimerForm() {
  const interval = Number($('selfcheckTimerInterval')?.value || 0);
  const nextAt = $('selfcheckTimerNextAt')?.value || '';
  const range = Number(options.rangeMinutes || $('selfcheckRange')?.value || 60);
  return {
    interval_minutes: interval,
    next_at: interval ? (nextAt || formatDateTimeLocalValue(new Date(Date.now() + interval * 60000))) : '',
    system_id: Number($('scStatusSystem')?.value || state.selectedStatusSystemId || 0) || null,
    range_minutes: range,
  };
}

function startSelfcheckTimerLoop() {
  if (state.aiSelfcheckTimerHandle) clearInterval(state.aiSelfcheckTimerHandle);
  state.aiSelfcheckTimerHandle = setInterval(checkScheduledSelfcheck, 30000);
}

async function checkScheduledSelfcheck() {
  const config = state.aiSelfcheckTimer || loadSelfcheckTimerConfig();
  if (!config.interval_minutes || !config.next_at || state.isRunningScheduledSelfcheck) return;
  const dueAt = new Date(config.next_at).getTime();
  if (!Number.isFinite(dueAt) || Date.now() < dueAt) return;
  const systemId = Number(config.system_id || state.selectedStatusSystemId || 0);
  if (!systemId || !state.token) return;
  state.isRunningScheduledSelfcheck = true;
  try {
    if ($('scStatusSystem')) $('scStatusSystem').value = String(systemId);
    state.selectedStatusSystemId = systemId;
    await runSystemSelfcheck({ scheduled: true, rangeMinutes: Number(config.range_minutes || 60) });
    config.next_at = formatDateTimeLocalValue(new Date(Date.now() + Number(config.interval_minutes) * 60000));
    saveSelfcheckTimerConfig(config);
  } finally {
    state.isRunningScheduledSelfcheck = false;
  }
}

function renderSelfcheckReportList(items = []) {
  const host = $('selfcheckReportList');
  if (!host) return;
  state.latestSelfcheckReports = items;
  host.innerHTML = items.length ? items.map((item) => `
    <div class="activity-item">
      <strong>${escapeHtml(item.system_name || item.system_code || item.file_name || 'AI 自检报告')}</strong>
      <span>${escapeHtml(item.checked_at || '-')} · 告警 ${escapeHtml(item.alarm_count ?? 0)} 条 · ${escapeHtml(item.file_name || '-')}</span>
    </div>
  `).join('') : '<div class="hint">暂无匹配的 AI 自检报告。</div>';
}

async function loadSelfcheckReports({ recent = true } = {}) {
  const params = new URLSearchParams({ page: '1', size: '50' });
  const systemId = Number($('scStatusSystem')?.value || state.selectedStatusSystemId || 0);
  if (systemId) params.set('system_id', String(systemId));
  if (!recent) {
    const start = $('selfcheckReportStart')?.value;
    const end = $('selfcheckReportEnd')?.value;
    if (start) params.set('start_at', new Date(start).toISOString());
    if (end) params.set('end_at', new Date(end).toISOString());
  }
  const data = await api(`/api/v1/selfchecks/reports?${params.toString()}`, { headers: authHeaders() });
  renderSelfcheckReportList(data.items || []);
  const hint = $('selfcheckRecentHint');
  if (hint) hint.textContent = recent ? `最近 6 小时内共 ${data.total || 0} 条 AI 自检报告。` : `搜索到 ${data.total || 0} 条 AI 自检报告。`;
  return data;
}

async function runSystemSelfcheck(options = {}) {
  const systemId = Number($('scStatusSystem')?.value || state.selectedStatusSystemId || 0);
  if (!systemId) {
    show('selfcheckAiReport', '请先选择系统。');
    return null;
  }
  state.selectedStatusSystemId = systemId;
  const range = Number(options.rangeMinutes || $('selfcheckRange')?.value || 60);
  const selected = state.statusSystems.find((item) => Number(item.system_id) === Number(systemId));
  if ($('statusSystemHint')) $('statusSystemHint').textContent = selected
    ? `当前系统：${selected.system_name || selected.system_code || systemId} · ${selected.host_address || '未配置 IP'}`
    : '正在读取系统自检数据...';
  show('selfcheckAiReport', options.scheduled ? '定时 AI 自检正在生成报告...' : '正在生成自检报告...');
  renderSelfcheckAlarms([]);
  setButtonLoading('btnRunSelfcheck', true, '自检中...');
  try {
    const data = await api(`/api/v1/selfchecks/run?system_id=${encodeURIComponent(systemId)}&range_minutes=${encodeURIComponent(range)}`, { headers: authHeaders() });
    renderSelfcheckStatus(data);
    renderSelfcheckAlarms(data.alarms || []);
    renderSelfcheckAiReport(data);
    await loadSelfcheckReports({ recent: true }).catch(() => {});
    return data;
  } catch (e) {
    show('selfcheckAiReport', explainActionError(e, '系统自检', 'inspector / admin / super_admin'));
    return null;
  } finally {
    setButtonLoading('btnRunSelfcheck', false);
  }
}

async function refreshErrorSystems({ force = false } = {}) {
  try {
    const now = Date.now();
    if (!force && state.errorSystemsLoadedAt && now - state.errorSystemsLoadedAt < 60000) {
      syncLogFileOptions();
      return;
    }
    if (!force && state.errorSystemsLoading) {
      await state.errorSystemsLoading;
      syncLogFileOptions();
      return;
    }

    state.errorSystemsLoading = api('/api/v1/systems/accessible-log-configs', { headers: authHeaders() });
    const data = await state.errorSystemsLoading;
    state.errorSystemsLoadedAt = Date.now();
    renderAccessibleSystems(data.items || [], { replaceLogConfigs: true });
    syncLogFileOptions();
  } catch (e) {
    if ($('errorAiStatus')) $('errorAiStatus').textContent = `系统列表读取失败：${e.message}`;
  } finally {
    state.errorSystemsLoading = null;
  }
}

function startStatusLoop() {
  if (state.chartTimer) return;
  refreshStatusBase();
  state.chartTimer = setInterval(() => {
    const jitter = (n) => Math.max(0, Math.min(100, n + (Math.random() * 8 - 4)));
    pushMetric('cpu', jitter(state.metricSeries.cpu.at(-1) ?? 50));
    pushMetric('mem', jitter(state.metricSeries.mem.at(-1) ?? 45));
    pushMetric('disk', jitter(state.metricSeries.disk.at(-1) ?? 60));
    renderCharts();
  }, 2500);
}

function stopStatusLoop() {
  if (!state.chartTimer) return;
  clearInterval(state.chartTimer);
  state.chartTimer = null;
}

const qrScan = {
  stream: null,
  timer: null,
  detector: null,
  attempts: 0,
  lastError: '',
};

const nfcScan = {
  reader: null,
  active: false,
  onReading: null,
  onError: null,
};

function setQrScanState(text) {
  if ($('qrScanState')) $('qrScanState').textContent = text;
}

function secureContextHint(feature) {
  const host = window.location.host;
  return `${feature} 需要安全上下文（HTTPS或localhost）。当前是 ${host}，请改用 https:// 或在本机 localhost 打开。`;
}

function stopQrScanner() {
  if (qrScan.timer) {
    clearInterval(qrScan.timer);
    qrScan.timer = null;
  }
  if (qrScan.stream) {
    qrScan.stream.getTracks().forEach((t) => t.stop());
    qrScan.stream = null;
  }
  qrScan.attempts = 0;
  qrScan.lastError = '';
  const video = $('qrVideo');
  if (video) {
    video.pause();
    video.srcObject = null;
  }
  $('qrScannerOverlay')?.classList.add('hidden');
}

function decodeWithJsQR(ctx, canvas) {
  if (typeof window.jsQR !== 'function') return '';
  try {
    const image = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const code = window.jsQR(image.data, image.width, image.height, { inversionAttempts: 'attemptBoth' });
    return code?.data || '';
  } catch {
    return '';
  }
}

function loadScriptOnce(src, globalName) {
  if (globalName && window[globalName]) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.querySelector(`script[data-dynamic-src="${src}"]`);
    if (existing) {
      existing.addEventListener('load', () => resolve(), { once: true });
      existing.addEventListener('error', () => reject(new Error('脚本加载失败')), { once: true });
      return;
    }
    const script = document.createElement('script');
    script.src = src;
    script.async = true;
    script.dataset.dynamicSrc = src;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('脚本加载失败'));
    document.head.appendChild(script);
  });
}

async function startQrScanner() {
  if (!window.isSecureContext) {
    setQrScanState(secureContextHint('相机扫码'));
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    setQrScanState('当前浏览器不支持相机调用，请更换浏览器或设备后重试。');
    return;
  }

  try {
    // BarcodeDetector 若可用则优先使用；否则自动降级到 jsQR
    qrScan.detector = null;
    if ('BarcodeDetector' in window) {
      try {
        if (window.BarcodeDetector.getSupportedFormats) {
          const formats = await window.BarcodeDetector.getSupportedFormats();
          if (!formats.includes('qr_code')) {
            setQrScanState('当前设备原生二维码识别能力受限，已切换兼容识别模式。');
          } else {
            qrScan.detector = new window.BarcodeDetector({ formats: ['qr_code'] });
          }
        } else {
          qrScan.detector = new window.BarcodeDetector({ formats: ['qr_code'] });
        }
      } catch {
        qrScan.detector = null;
      }
    }

    if (!qrScan.detector && typeof window.jsQR !== 'function') {
      setQrScanState('正在加载二维码识别引擎...');
      try {
        await loadScriptOnce('https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js', 'jsQR');
      } catch {
        setQrScanState('二维码识别引擎加载失败，请检查网络后重试。');
        return;
      }
    }

    qrScan.stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } },
      audio: false,
    });

    const video = $('qrVideo');
    video.srcObject = qrScan.stream;
    $('qrScannerOverlay')?.classList.remove('hidden');
    await video.play();
    setQrScanState('相机已开启，请将二维码放入画面中央。');

    const canvas = $('qrCanvas');
    const ctx = canvas.getContext('2d');

    qrScan.timer = setInterval(async () => {
      if (!video.videoWidth || !video.videoHeight) return;
      qrScan.attempts += 1;
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      try {
        let value = '';

        if (qrScan.detector) {
          // 先直接识别 video，再识别 canvas，提升兼容性
          let barcodes = await qrScan.detector.detect(video);
          if (!barcodes?.length) {
            barcodes = await qrScan.detector.detect(canvas);
          }
          value = barcodes?.[0]?.rawValue || '';
        }

        if (!value) {
          value = decodeWithJsQR(ctx, canvas);
        }

        if (value) {
          state.qrScanText = value;
          setQrScanState('正在匹配机房配置...');
          stopQrScanner();
          try {
            await resolveQrPoint(value);
            setQrScanState('已识别机房，请完成检查项并提交。');
          } catch (e) {
            const msg = e?.message || '找不到巡检点';
            if ($('inspectionPointName')) $('inspectionPointName').value = '';
            state.qrResolvedPoint = null;
            show('inspectionResult', msg);
            setQrScanState(`未匹配到机房配置：${msg}`);
          }
          return;
        }

        if (qrScan.attempts % 12 === 0) {
          setQrScanState('正在识别二维码…请保持光线充足并将二维码放入框内。');
        }
      } catch (e) {
        const msg = e?.message || '识别异常';
        if (msg !== qrScan.lastError) {
          qrScan.lastError = msg;
          setQrScanState(`识别中断，正在重试：${msg}`);
        }
      }
    }, 280);
  } catch (e) {
    stopQrScanner();
    setQrScanState(`相机调用失败：${e.message || '未知错误'}`);
  }
}

function setNfcScanState(text) {
  if ($('nfcScanState')) $('nfcScanState').textContent = text;
}

function decodeNfcRecord(record) {
  try {
    if (record.recordType === 'text') {
      return new TextDecoder(record.encoding || 'utf-8').decode(record.data);
    }
    if (record.recordType === 'url' || record.recordType === 'absolute-url') {
      return new TextDecoder('utf-8').decode(record.data);
    }
    if (record.recordType === 'unknown' || record.recordType === 'mime') {
      return new TextDecoder('utf-8').decode(record.data);
    }
  } catch {
    return '';
  }
  return '';
}

async function resolveNfcLocation(tagText) {
  const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(tagText)}`, { headers: authHeaders() });
  show('nfcResultView', `NFC 读取成功，已定位到：${resolved.point_name || resolved.location || resolved.point_code || '未命名点位'}。`);
  return resolved;
}

function renderInspectionChecklist(checkItems = [], monitoring = null) {
  const host = $('inspectionCheckItems');
  if (host) {
    const rows = (checkItems || []).map((item, index) => `
      <div class="check-row" data-check-index="${index}">
        <span>${escapeHtml(item)}</span>
        <select data-check-result>
          <option value="normal">正常</option>
          <option value="abnormal">异常</option>
        </select>
      </div>
    `).join('');
    host.innerHTML = rows || '<div class="hint">该机房暂未配置检查项。</div>';
  }

  const monitorHost = $('inspectionMonitoringItem');
  if (monitorHost) {
    const options = monitoring?.options || [{ value: 'monitoring_no_alarm', label: '监控无异常' }];
    monitorHost.innerHTML = `
      <div class="check-row">
        <span>${escapeHtml(monitoring?.label || '监控无异常')}</span>
        <select id="inspectionMonitoringConfirm">
          ${options.map((item) => `<option value="${escapeHtml(item.value)}">${escapeHtml(item.label)}</option>`).join('')}
        </select>
      </div>
    `;
  }
}

function collectInspectionCheckResults() {
  return Array.from(document.querySelectorAll('#inspectionCheckItems .check-row')).map((row) => ({
    item: row.querySelector('span')?.textContent || '',
    result: row.querySelector('[data-check-result]')?.value || 'normal',
  }));
}

async function resolveQrPoint(tagText) {
  const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(tagText)}`, { headers: authHeaders() });
  state.qrResolvedPoint = resolved;
  const roomName = resolved.room_name || resolved.point_name || resolved.location || resolved.point_code || '';
  if ($('inspectionPointName')) $('inspectionPointName').value = roomName;
  renderInspectionChecklist(resolved.check_items || [], resolved.monitoring_confirmation || null);
  show('inspectionResult', '');
  return resolved;
}

function stopNfcScanner() {
  nfcScan.active = false;
  if (nfcScan.reader && nfcScan.onReading) {
    nfcScan.reader.onreading = null;
  }
  if (nfcScan.reader && nfcScan.onError) {
    nfcScan.reader.onerror = null;
  }
  nfcScan.reader = null;
  nfcScan.onReading = null;
  nfcScan.onError = null;
}

async function startNfcScanner() {
  if (!window.isSecureContext) {
    setNfcScanState(secureContextHint('NFC 读取'));
    return;
  }
  if (!('NDEFReader' in window)) {
    setNfcScanState('当前设备/浏览器不支持 Web NFC。建议使用 Android Chrome 最新版并开启 NFC。');
    return;
  }

  try {
    stopNfcScanner();
    const reader = new window.NDEFReader();
    await reader.scan();
    nfcScan.reader = reader;
    nfcScan.active = true;
    setNfcScanState('NFC 已开启，请将手机靠近标签。');

    nfcScan.onReading = async ({ serialNumber, message }) => {
      if (!nfcScan.active) return;
      const fromRecords = (message?.records || []).map((r) => decodeNfcRecord(r)).find(Boolean);
      const tagText = (fromRecords || serialNumber || '').trim();
      if (!tagText) {
        setNfcScanState('读取到 NFC，但未解析出标签内容。');
        return;
      }

      state.nfcTagText = tagText;
      setNfcScanState('NFC 读取成功，正在解析机房位置...');
      try {
        const resolved = await resolveNfcLocation(tagText);
        setNfcScanState(`NFC 读取成功：${resolved.location || '位置未配置'}`);
      } catch (e) {
        setNfcScanState(`NFC 已读取，但点位未匹配：${e.message}`);
        show('nfcResultView', `已读取 NFC 标签，但暂未找到对应巡检点：${e.message}`);
      }
    };

    nfcScan.onError = (event) => {
      setNfcScanState(`NFC 读取异常：${event?.message || '未知错误'}`);
    };

    reader.onreading = nfcScan.onReading;
    reader.onerror = nfcScan.onError;
  } catch (e) {
    stopNfcScanner();
    setNfcScanState(`NFC 启动失败：${e.message || '未知错误'}`);
  }
}

// auth
onClick('btnPing', async () => {
  try {
    const d = await api('/healthz');
    alert(`后端可用：${d.status || 'ok'}\n当前地址：${getBase()}`);
  }
  catch (e) { alert(`连通失败：${e.message}`); }
});

onClick('btnLogin', async () => {
  try {
    const data = await api('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $('username').value.trim(), password: $('password').value }),
    });
    state.token = data.access_token;
    storeToken(state.token);
    state.profile.username = $('username').value.trim() || state.profile.username || 'admin';
    applyProfileUI();
    setLoginState('登录成功');
    switchScreen(true);
    closeDetailPages();
    switchTab(state.activeTab || 'tab-workbench');
    api('/api/v1/auth/me', { headers: authHeaders() }).then((me) => {
      state.profile.username = me.username || state.profile.username || 'admin';
      state.profile.nickname = me.nickname || '';
      state.profile.avatar = me.avatar_url || '';
      saveProfileState();
      applyProfileUI();
    }).catch(() => {});
    refreshErrorSystems().catch(() => {});
  } catch (e) { setLoginState(`登录失败：${e.message}`); }
});

function doLogout() {
  state.token = '';
  clearStoredToken();
  state.activeDetailPage = '';
  state.activeTab = 'tab-workbench';
  try {
    sessionStorage.removeItem(ACTIVE_TAB_KEY);
  } catch {}
  stopStatusLoop();
  stopQrScanner();
  stopNfcScanner();
  closeDetailPages();
  switchScreen(false);
  setLoginState('已退出登录');
}

onClick('btnLogout', doLogout);

async function restoreSession() {
  if (!state.token) {
    setLoginState('未登录');
    switchScreen(false);
    return false;
  }

  try {
    const me = await api('/api/v1/auth/me', { headers: authHeaders() });
    state.profile.username = me.username || state.profile.username || 'admin';
    state.profile.nickname = me.nickname || '';
    state.profile.avatar = me.avatar_url || '';
    saveProfileState();
    applyProfileUI();
    setLoginState(`已恢复登录：${state.profile.username}`);
    switchScreen(true);
    closeDetailPages();
    switchTab(state.activeTab || 'tab-workbench');
    refreshErrorSystems().catch(() => {});
    return true;
  } catch (e) {
    state.token = '';
    clearStoredToken();
    setLoginState('登录已过期，请重新登录');
    switchScreen(false);
    return false;
  }
}

onClick('btnSaveProfile', async () => {
  try {
    const payload = {
      nickname: $('profileNickname').value.trim() || null,
      avatar_url: $('profileAvatarUrl').value.trim() || null,
    };
    const data = await api('/api/v1/auth/profile', { method: 'PUT', headers: authHeaders(), body: JSON.stringify(payload) });
    state.profile.username = data.username || state.profile.username || $('username').value.trim() || 'admin';
    state.profile.nickname = data.nickname || '';
    state.profile.avatar = data.avatar_url || '';
    saveProfileState();
    applyProfileUI();
    show('profileResult', '');
    showToast('账号信息已更新。', 'success');
  } catch (e) {
    show('profileResult', e.message || '保存失败');
  }
});

onClick('btnChangePassword', async () => {
  try {
    const oldPwd = $('oldPassword').value;
    const newPwd = $('newPassword').value;
    if (!oldPwd || !newPwd) throw new Error('请填写旧密码和新密码');
    if (newPwd.length < 6) throw new Error('新密码至少 6 位');

    const data = await api('/api/v1/auth/change-password', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ old_password: oldPwd, new_password: newPwd }),
    });
    show('passwordResult', '');
    showToast('密码修改成功。', 'success');
    $('oldPassword').value = '';
    $('newPassword').value = '';
  } catch (e) {
    show('passwordResult', e.message || '修改失败');
  }
});

// bottom tabs
Array.from(document.querySelectorAll('.bottom-tab')).forEach((tab) => {
  tab.addEventListener('click', () => {
    stopStatusLoop();
    stopQrScanner();
    stopNfcScanner();
    closeDetailPages();
    switchTab(tab.dataset.tab);
  });
});

// inspection
onClick('btnStartQrScan', startQrScanner);
onClick('btnCloseScanner', () => {
  stopQrScanner();
  setQrScanState('已关闭扫码。');
});

onClick('btnCreateInspection', async () => {
  try {
    const qrText = (state.qrScanText || '').trim();
    if (!qrText) throw new Error('请先调用相机完成二维码扫描');

    const resolved = state.qrResolvedPoint || await resolveQrPoint(qrText);
    const checkResults = collectInspectionCheckResults();
    const monitoringConfirmation = $('inspectionMonitoringConfirm')?.value || 'monitoring_no_alarm';
    const hasAbnormal = checkResults.some((item) => item.result === 'abnormal') || monitoringConfirmation === 'alarm_abnormal_processing';
    const payload = {
      system_id: resolved.system_id ? Number(resolved.system_id) : null,
      point_id: Number(resolved.point_id),
      room_id: resolved.room_id ? Number(resolved.room_id) : null,
      result: hasAbnormal ? 'abnormal' : 'normal',
      note: $('insNote').value || null,
      check_results: checkResults,
      monitoring_confirmation: monitoringConfirmation,
      inspected_at: new Date().toISOString(),
    };
    await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    const targetName = resolved.room_name || resolved.point_name || resolved.location || resolved.point_code || '当前机房';
    show('inspectionResult', '');
    setQrScanState('巡检已提交。');
    window.alert(`巡检提交成功：${targetName}。`);
  } catch (e) { show('inspectionResult', explainActionError(e, '提交巡检记录', 'inspector / admin / super_admin')); }
});

onClick('btnStartNfcScan', startNfcScanner);
onClick('btnStopNfcScan', () => {
  stopNfcScanner();
  setNfcScanState('已停止 NFC 读取。');
});

onClick('btnSubmitNfc', async () => {
  try {
    const nfcText = (state.nfcTagText || '').trim();
    if (!nfcText) throw new Error('请先进行 NFC 碰一碰读取标签内容');

    const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(nfcText)}`, { headers: authHeaders() });
    const payload = {
      system_id: Number(resolved.system_id),
      point_id: Number(resolved.point_id),
      result: $('nfcResult').value,
      note: $('nfcNote').value || null,
      inspected_at: new Date().toISOString(),
    };
    const created = await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    show('nfcResultView', `NFC 巡检提交成功：${resolved.point_name || resolved.location || resolved.point_code || '当前点位'}。`);
  } catch (e) { show('nfcResultView', e.message); }
});

// selfcheck
if ($('scStatusSystem')) {
  $('scStatusSystem').onchange = () => {
    state.selectedStatusSystemId = Number($('scStatusSystem').value || 0) || null;
    show('selfcheckAiReport', '已切换系统，点击“开始 AI 自检”后生成新报告。');
    loadSelfcheckReports({ recent: true }).catch(() => {});
  };
}
onClick('btnRunSelfcheck', runSystemSelfcheck);
onClick('btnSaveSelfcheckTimer', () => {
  const config = readSelfcheckTimerForm();
  saveSelfcheckTimerConfig(config);
  showToast(config.interval_minutes ? '定时 AI 自检配置已保存' : '定时 AI 自检已关闭');
});
onClick('btnSearchSelfcheckReports', () => loadSelfcheckReports({ recent: false }).catch((e) => {
  const hint = $('selfcheckRecentHint');
  if (hint) hint.textContent = explainActionError(e, '搜索自检报告', 'inspector / admin / super_admin');
}));
onClick('btnLoadRecentSelfcheckReports', () => loadSelfcheckReports({ recent: true }).catch((e) => {
  const hint = $('selfcheckRecentHint');
  if (hint) hint.textContent = explainActionError(e, '读取自检报告', 'inspector / admin / super_admin');
}));

$('selfcheckSystemPickerList')?.addEventListener('click', (event) => {
  const btn = event.target.closest('[data-selfcheck-system-id]');
  if (!btn) return;
  openSelfcheckPageForSystem(btn.dataset.selfcheckSystemId);
});

document.querySelectorAll('[data-close-selfcheck-system-modal]').forEach((el) => {
  el.addEventListener('click', () => {
    closeSelfcheckSystemModal();
  });
});

function formatDateTimeLocalValue(date) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function switchResultTab(tab) {
  document.querySelectorAll('.result-tab-btn').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.resultTab === tab);
  });
  $('resultLogsPanel')?.classList.toggle('hidden', tab !== 'logs');
  $('resultAnalysisPanel')?.classList.toggle('hidden', tab !== 'analysis');
}

async function loadSystemLogConfigs(systemId) {
  if (!systemId) return [];
  if (Object.prototype.hasOwnProperty.call(state.logConfigsBySystem, systemId)) {
    return state.logConfigsBySystem[systemId] || [];
  }
  if (state.logConfigsLoadingBySystem[systemId]) {
    return state.logConfigsLoadingBySystem[systemId];
  }
  state.logConfigsLoadingBySystem[systemId] = api(`/api/v1/systems/${systemId}/log-configs`, { headers: authHeaders() })
    .then((data) => {
      const items = Array.isArray(data?.items) ? data.items : [];
      state.logConfigsBySystem[systemId] = items;
      return items;
    })
    .finally(() => {
      delete state.logConfigsLoadingBySystem[systemId];
    });
  return state.logConfigsLoadingBySystem[systemId];
}

function renderLogFileOptionsFromConfigs(systemId, configs) {
  const select = $('errorFileName');
  if (!select) return;

  const options = (configs || []).map((item) => ({
    value: String(item.id),
    label: item.log_name || item.absolute_path || '日志',
    config: item,
  }));

  select.innerHTML = `<option value="" selected disabled>${options.length ? '请选择日志' : '暂无日志配置'}</option>` + options.map((item) => `<option value="${item.value}">${escapeHtml(item.label)}</option>`).join('');
  if (options.length) {
    select.value = options[0].value;
    state.selectedLogConfig = options[0].config || null;
  } else {
    state.selectedLogConfig = null;
  }
}

function syncLogFileOptions() {
  const systemId = Number($('errorSystem')?.value || state.selectedLogSystemId || state.selectedStatusSystemId || 0);
  state.selectedLogSystemId = systemId || null;
  renderLogFileOptionsFromConfigs(systemId, state.logConfigsBySystem[systemId] || []);
}

function updateTimeSummary() {
  const start = $('errorStartAt')?.value || '';
  const end = $('errorEndAt')?.value || '';
  const summary = $('errorTimeSummary');
  const trigger = $('btnOpenTimeFilter');
  if (!summary) return;
  if (state.isCustomLogTimeRange && start && end) {
    const text = `${start.replace('T', ' ')} 至 ${end.replace('T', ' ')}`;
    summary.textContent = text;
    if (trigger) trigger.textContent = text;
    return;
  }
  const labels = { '1h': '最近 1 小时', '3h': '最近 3 小时', '6h': '最近 6 小时', all: '全量日志文件' };
  const text = labels[state.selectedQuickRange || '1h'] || '最近 1 小时';
  summary.textContent = text;
  if (trigger) trigger.textContent = text;
}

function syncQuickRangeInputs(rangeValue) {
  state.isCustomLogTimeRange = false;
  if (rangeValue === 'all') {
    if ($('errorStartAt')) $('errorStartAt').value = '';
    if ($('errorEndAt')) $('errorEndAt').value = '';
    updateTimeSummary();
    return;
  }
  const mapping = { '1h': 1, '3h': 3, '6h': 6 };
  const hours = mapping[rangeValue] || 1;
  const end = new Date();
  const start = new Date(end.getTime() - hours * 60 * 60 * 1000);
  if ($('errorStartAt')) $('errorStartAt').value = formatDateTimeLocalValue(start);
  if ($('errorEndAt')) $('errorEndAt').value = formatDateTimeLocalValue(end);
  updateTimeSummary();
}

document.querySelectorAll('.quick-range-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.selectedQuickRange = btn.dataset.range || '1h';
    document.querySelectorAll('.quick-range-btn').forEach((item) => item.classList.toggle('active', item === btn));
    syncQuickRangeInputs(state.selectedQuickRange);
  });
});

onClick('btnOpenTimeFilter', () => {
  $('errorTimeModal')?.classList.remove('hidden');
});

document.querySelectorAll('[data-close-time-modal]').forEach((el) => {
  el.addEventListener('click', () => {
    $('errorTimeModal')?.classList.add('hidden');
  });
});

onClick('btnApplyTimeFilter', () => {
  updateTimeSummary();
  $('errorTimeModal')?.classList.add('hidden');
});

if ($('errorStartAt') && $('errorEndAt')) {
  $('errorStartAt').addEventListener('change', () => {
    state.isCustomLogTimeRange = true;
    document.querySelectorAll('.quick-range-btn').forEach((item) => item.classList.remove('active'));
    updateTimeSummary();
  });
  $('errorEndAt').addEventListener('change', () => {
    state.isCustomLogTimeRange = true;
    document.querySelectorAll('.quick-range-btn').forEach((item) => item.classList.remove('active'));
    updateTimeSummary();
  });
  syncQuickRangeInputs(state.selectedQuickRange || '1h');
}

if ($('errorSystem')) {
  $('errorSystem').addEventListener('focus', () => {
    renderErrorSystemOptions();
  });
  $('errorSystem').addEventListener('change', async () => {
    state.selectedLogSystemId = Number($('errorSystem').value || 0) || null;
    renderLogFileOptionsFromConfigs(state.selectedLogSystemId, state.logConfigsBySystem[state.selectedLogSystemId] || []);
    try {
      const configs = await loadSystemLogConfigs(state.selectedLogSystemId);
      renderLogFileOptionsFromConfigs(state.selectedLogSystemId, configs);
    } catch (e) {
      state.selectedLogConfig = null;
      if ($('errorAiStatus')) $('errorAiStatus').textContent = `日志配置读取失败：${e.message}`;
    }
  });
}

if ($('errorFileName')) {
  $('errorFileName').addEventListener('focus', () => {
    syncLogFileOptions();
  });
  $('errorFileName').addEventListener('change', () => {
    const systemId = Number($('errorSystem')?.value || state.selectedLogSystemId || 0);
    const configs = state.logConfigsBySystem[systemId] || [];
    state.selectedLogConfig = configs.find((item) => String(item.id) === String($('errorFileName').value)) || null;
  });
}

if ($('errorLogLevel')) {
  $('errorLogLevel').value = 'warning';
}
updateTimeSummary();
document.querySelectorAll('.result-tab-btn').forEach((btn) => {
  btn.addEventListener('click', () => switchResultTab(btn.dataset.resultTab || 'logs'));
});
switchResultTab('logs');

onClick('btnLoadErrors', async () => {
  try {
    const source = 'system';
    const selectedConfig = state.selectedLogConfig;
    const configuredPath = selectedConfig?.absolute_path || '';
    const fileName = selectedConfig ? configuredPath : $('errorFileName').value;
    if (!state.selectedLogSystemId) throw new Error('请先选择系统');
    if (!configuredPath) throw new Error('该系统暂无管理端日志配置');
    const level = $('errorLogLevel').value;
    const startAt = $('errorStartAt').value;
    const endAt = $('errorEndAt').value;
    const quickRange = state.selectedQuickRange || '1h';
    $('errorAiStatus').textContent = configuredPath
      ? `正在提取 ${configuredPath}，请稍等...`
      : '正在提取日志，请稍等...';
    const query = new URLSearchParams({
      source,
      file_name: fileName,
      quick_range: quickRange,
      level,
      lines: quickRange === 'all' ? '20000' : '5000',
    });
    if (quickRange !== 'all' && state.isCustomLogTimeRange && startAt && endAt) {
      query.set('start_at', startAt.replace('T', ' '));
      query.set('end_at', endAt.replace('T', ' '));
    }
    const data = await api(`/api/v1/toolbox/error-logs?${query.toString()}`, { headers: authHeaders() });
    const prefix = configuredPath ? `管理端配置日志地址：${configuredPath}\n\n` : '';
    state.extractedErrors = String(data.content || '').split('\n').filter(Boolean).slice(0, quickRange === 'all' ? 20000 : 5000).map((line) => ({ line }));
    show('errorLogsView', prefix + (data.content || '未读取到日志内容。'));
    show('errorAiView', '');
    switchResultTab('logs');
    $('errorAiStatus').textContent = `已提取 ${data.line_count || state.extractedErrors.length} 行日志，可继续 AI 分析。`;
  } catch (e) {
    $('errorAiStatus').textContent = '日志提取失败，请稍后重试。';
    show('errorLogsView', `读取日志失败：${e.message}`);
  }
});

onClick('btnAnalyzeErrors', async () => {
  if (state.isAnalyzingErrors) return;
  state.isAnalyzingErrors = true;
  setButtonLoading('btnAnalyzeErrors', true, 'AI 分析中...');
  $('errorAiStatus').textContent = 'AI 分析中，请稍等...';
  show('errorAiView', '正在分析当前错误日志，请稍候...');
  try {
    const detail = state.extractedErrors.length
      ? state.extractedErrors.map((e) => e.line || `${e.at} ${e.method || ''} ${e.url || ''} status=${e.status || 0} err=${e.network_error || ''}`).join('\n').slice(0, 20000)
      : '暂无系统日志，建议先执行“提取日志”。';
    const payload = { title: '系统日志分析', detail, severity: $('errorLogLevel').value === 'error' ? 'high' : $('errorLogLevel').value === 'warning' ? 'medium' : 'low' };
    const result = await api('/api/v1/ai/diagnose', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    $('errorAiStatus').textContent = 'AI 分析完成。';
    show('errorAiView', formatErrorAiResult(result));
    switchResultTab('analysis');
  } catch (e) {
    $('errorAiStatus').textContent = 'AI 分析失败，请稍后重试。';
    show('errorAiView', explainActionError(e, '错误日志 AI 分析', 'admin / super_admin'));
  } finally {
    state.isAnalyzingErrors = false;
    setButtonLoading('btnAnalyzeErrors', false);
  }
});

// toolbox
onClick('btnToolPing', async () => {
  try {
    const data = await api('/api/v1/toolbox/ping', {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ host: $('tbPingHost').value.trim(), count: Number($('tbPingCount').value || 1) }),
    });
    const ok = String(JSON.stringify(data)).toLowerCase().includes('success') || String(JSON.stringify(data)).includes('true');
    $('pingStatus').className = `status-dot ${ok ? 'ok' : 'fail'}`;
    $('pingStatus').textContent = `状态：${ok ? '接通' : '可能异常'}`;
    const summary = [];
    if (typeof data?.message === 'string' && data.message) summary.push(data.message);
    if (typeof data?.output === 'string' && data.output) summary.push(data.output);
    if (!summary.length) summary.push(ok ? 'Ping 检测完成，网络可达。' : 'Ping 检测完成，但结果可能异常。');
    show('pingResult', summary.join('\n\n'));
  } catch (e) {
    $('pingStatus').className = 'status-dot fail';
    $('pingStatus').textContent = '状态：失败';
    show('pingResult', explainActionError(e, 'Ping 检测', 'admin / super_admin'));
  }
});

onClick('btnCreateToolTask', async () => {
  try {
    const task = await api('/api/v1/toolbox/restart-task', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ target: 'mobile-selected-app', reason: 'mobile toolbox request' }),
    });
    show('toolTaskResult', `已创建重启审批任务，当前状态：${task.status || 'pending_approval'}。`);
  } catch (e) {
    show('toolTaskResult', explainActionError(e, '创建工具任务', 'admin / super_admin'));
  }
});
onClick('btnRefreshToolTasks', async () => {
  try {
    const tasks = await api('/api/v1/toolbox/tasks?page=1&size=10', { headers: authHeaders() });
    const lines = (tasks.items || []).map((t, idx) => {
      const result = t.result || {};
      return `${idx + 1}. ${t.action || 'task'} · ${t.status || '-'} · ${t.target || '-'}\n时间：${t.finished_at || t.started_at || t.created_at || '-'}\n说明：${result.note || result.reason || '-'}${t.executor || result.executor ? `\n执行人：${t.executor || result.executor}` : ''}`;
    });
    show('toolTaskResult', lines.length ? lines.join('\n\n') : '暂无最近工具任务。');
  } catch (e) {
    show('toolTaskResult', explainActionError(e, '读取工具任务', 'admin / super_admin'));
  }
});
onEvent('aiFileInput', 'change', handleAiFileChange);
onClick('btnSendAiQuestion', sendAiQuestion);
onClick('btnNewAiChat', () => {
  state.aiConversationId = '';
  state.aiMessages = buildDefaultAiMessages();
  state.lastAiRequestPayload = null;
  state.aiAttachments.forEach((item) => item.previewUrl && URL.revokeObjectURL(item.previewUrl));
  state.aiAttachments = [];
  sessionStorage.removeItem(AI_CHAT_HISTORY_KEY);
  sessionStorage.removeItem(AI_CHAT_CONVERSATION_KEY);
  renderAiAttachmentList();
  saveAiMessages();
  renderAiMessages();
  renderAiConversationList();
  if (window.innerWidth <= 640) setAiSidebarCollapsed(true);
  $('aiQaResult').textContent = '已开启新会话。';
});
onClick('btnToggleAiSidebar', () => {
  setAiSidebarCollapsed(!state.aiSidebarCollapsed);
});
onClick('btnShowAiSidebar', () => {
  setAiSidebarCollapsed(false);
});
window.addEventListener('resize', applyAiSidebarState);
onEvent('aiQuestionInput', 'keydown', (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendAiQuestion();
  }
});

initSubNavigation();
bindEmergencyToolActions();
bindCaptureToolActions();
renderAiMessages();
renderAiAttachmentList();
applyAiSidebarState();
applyProfileUI();
closeDetailPages();
switchTab('tab-workbench');
setLoginState(state.token ? '正在恢复登录...' : '未登录');
switchScreen(Boolean(state.token));
state.aiSelfcheckTimer = loadSelfcheckTimerConfig();
syncSelfcheckTimerUi();
startSelfcheckTimerLoop();
restoreSession();
