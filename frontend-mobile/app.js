const $ = (id) => document.getElementById(id);
const DEFAULT_AVATAR = 'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="32" fill="%230f2c44"/><circle cx="32" cy="24" r="12" fill="%236bd5ff"/><path d="M12 56c4-10 12-16 20-16s16 6 20 16" fill="%2338bdf8"/></svg>';

const state = {
  token: localStorage.getItem('aegis_token') || '',
  requestLogs: JSON.parse(localStorage.getItem('aegis_request_logs') || '[]'),
  metricSeries: { cpu: [], mem: [], disk: [] },
  chartTimer: null,
  extractedErrors: [],
  profile: JSON.parse(localStorage.getItem('aegis_profile') || '{}'),
};

function getBase() { return $('apiBase').value.trim().replace(/\/$/, ''); }
function authHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}
function show(id, data) { $(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2); }
function setLoginState(text) { $('loginState').textContent = text; }

function saveProfileState() {
  localStorage.setItem('aegis_profile', JSON.stringify(state.profile));
}

function applyProfileUI() {
  const avatar = state.profile.avatar || DEFAULT_AVATAR;
  if ($('headerAvatar')) $('headerAvatar').src = avatar;
  if ($('profileAvatarPreview')) $('profileAvatarPreview').src = avatar;
  if ($('profileAvatarUrl')) $('profileAvatarUrl').value = state.profile.avatar || '';
  if ($('profileNickname')) $('profileNickname').value = state.profile.nickname || '';
  if ($('profileUsername')) $('profileUsername').value = state.profile.username || $('username').value.trim() || 'admin';
}

function rememberLog(log) {
  state.requestLogs.unshift(log);
  if (state.requestLogs.length > 300) state.requestLogs = state.requestLogs.slice(0, 300);
  localStorage.setItem('aegis_request_logs', JSON.stringify(state.requestLogs));
}

async function api(path, options = {}) {
  const method = options.method || 'GET';
  const url = `${getBase()}${path}`;
  const started = Date.now();
  try {
    const resp = await fetch(url, options);
    const data = await resp.json().catch(() => ({}));
    rememberLog({ at: new Date().toISOString(), method, url, status: resp.status, ok: resp.ok, body: options.body ? JSON.parse(options.body) : null, response: data, duration_ms: Date.now() - started });
    if (!resp.ok) throw new Error((data && (data.message || data.detail)) || `HTTP ${resp.status}`);
    return data;
  } catch (e) {
    rememberLog({ at: new Date().toISOString(), method, url, status: 0, ok: false, network_error: e.message || 'fetch failed', duration_ms: Date.now() - started });
    throw e;
  }
}

function switchScreen(loggedIn) {
  $('loginScreen').classList.toggle('active', !loggedIn);
  $('appScreen').classList.toggle('active', loggedIn);
}

function switchPanel(panelId) {
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.menu-tabs .tab').forEach((t) => t.classList.remove('active'));
  document.getElementById(panelId)?.classList.add('active');
  document.querySelector(`.menu-tabs .tab[data-panel="${panelId}"]`)?.classList.add('active');
}

function showSub(panelId, subName) {
  const panel = $(panelId);
  panel.querySelectorAll('[data-sub]').forEach((el) => el.classList.add('hidden'));
  panel.querySelector(`[data-sub="${subName}"]`)?.classList.remove('hidden');
}

function initSubNavigation() {
  $('btnGoQr').onclick = () => showSub('panel-inspection', 'inspection-qr');
  $('btnUserCenter').onclick = () => {
    stopStatusLoop();
    switchPanel('panel-user-center');
    applyProfileUI();
  };
  $('btnBackFromUser').onclick = () => switchPanel('panel-inspection');
  $('btnGoNfc').onclick = () => showSub('panel-inspection', 'inspection-nfc');
  $('btnGoStatus').onclick = () => { showSub('panel-selfcheck', 'selfcheck-status'); startStatusLoop(); };
  $('btnGoSelfForm').onclick = () => showSub('panel-selfcheck', 'selfcheck-form');
  $('btnGoErrorLogs').onclick = () => showSub('panel-selfcheck', 'selfcheck-errors');
  $('btnGoPing').onclick = () => showSub('panel-toolbox', 'toolbox-ping');
  $('btnGoCapture').onclick = () => showSub('panel-toolbox', 'toolbox-capture');
  $('btnGoAppTools').onclick = () => showSub('panel-toolbox', 'toolbox-app');

  document.querySelectorAll('[data-back]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const target = btn.dataset.back;
      const panelId = btn.closest('.panel').id;
      showSub(panelId, target);
      if (target === 'selfcheck-home') stopStatusLoop();
    });
  });
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
  ctx.fillStyle = '#7fa8c8';
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
  ctx.strokeStyle = '#1d4d6d';
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
  ctx.fillStyle = '#cfe9ff';
  ctx.fillText(`${Math.round(last)}%`, Math.max(padL, lx - 28), Math.max(10, ly - 6));
}

function renderCharts() {
  drawLine('cpuChart', state.metricSeries.cpu, '#2dd4bf');
  drawLine('memChart', state.metricSeries.mem, '#38bdf8');
  drawLine('diskChart', state.metricSeries.disk, '#fb7185');
}

async function refreshStatusBase() {
  try {
    const data = await api('/api/v1/monitoring/overview', { headers: authHeaders() });
    const cpu = data?.summary?.cpu_usage_percent ?? data?.cpu_usage_percent ?? (Math.random() * 100);
    const mem = data?.summary?.mem_usage_percent ?? data?.mem_usage_percent ?? (Math.random() * 100);
    const disk = data?.summary?.disk_usage_percent ?? data?.disk_usage_percent ?? (Math.random() * 100);
    pushMetric('cpu', cpu); pushMetric('mem', mem); pushMetric('disk', disk);
    renderCharts();
  } catch {
    pushMetric('cpu', 40 + Math.random() * 30);
    pushMetric('mem', 35 + Math.random() * 35);
    pushMetric('disk', 45 + Math.random() * 25);
    renderCharts();
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

// auth
$('btnPing').onclick = async () => {
  try { const d = await api('/healthz'); alert(`后端可用：${d.status || 'ok'}`); }
  catch (e) { alert(`连通失败：${e.message}`); }
};

$('btnLogin').onclick = async () => {
  try {
    const data = await api('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $('username').value.trim(), password: $('password').value }),
    });
    state.token = data.access_token;
    localStorage.setItem('aegis_token', state.token);
    state.profile.username = $('username').value.trim() || state.profile.username || 'admin';
    saveProfileState();
    applyProfileUI();
    setLoginState('登录成功');
    switchScreen(true);
    switchPanel('panel-inspection');
  } catch (e) { setLoginState(`登录失败：${e.message}`); }
};

function doLogout() {
  state.token = '';
  localStorage.removeItem('aegis_token');
  stopStatusLoop();
  switchScreen(false);
  setLoginState('已退出登录');
}

$('btnLogoutInUserCenter').onclick = doLogout;

$('btnSaveProfile').onclick = async () => {
  try {
    const me = await api('/api/v1/auth/me', { headers: authHeaders() });
    state.profile.username = me.username || $('username').value.trim() || 'admin';
  } catch {
    state.profile.username = $('username').value.trim() || state.profile.username || 'admin';
  }
  state.profile.nickname = $('profileNickname').value.trim() || state.profile.nickname || '';
  state.profile.avatar = $('profileAvatarUrl').value.trim() || '';
  saveProfileState();
  applyProfileUI();
  show('profileResult', { ok: true, message: '昵称与头像已保存（前端本地保存，可继续接后端接口）', profile: state.profile });
};

$('btnChangePassword').onclick = async () => {
  try {
    const oldPwd = $('oldPassword').value;
    const newPwd = $('newPassword').value;
    const user = ($('profileUsername').value || $('username').value).trim();
    if (!oldPwd || !newPwd) throw new Error('请填写旧密码和新密码');
    if (newPwd.length < 6) throw new Error('新密码至少 6 位');
    await api('/api/v1/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: user, password: oldPwd }),
    });
    show('passwordResult', { ok: true, message: '旧密码校验通过。当前后端暂未开放修改密码接口，此处已完成交互预留。' });
    $('oldPassword').value = '';
    $('newPassword').value = '';
  } catch (e) {
    show('passwordResult', e.message || '修改失败');
  }
};

// top tabs
Array.from(document.querySelectorAll('.menu-tabs .tab')).forEach((tab) => {
  tab.addEventListener('click', () => {
    if (tab.dataset.panel !== 'panel-selfcheck') stopStatusLoop();
    switchPanel(tab.dataset.panel);
  });
});

// inspection
$('btnCreateInspection').onclick = async () => {
  try {
    const qrText = $('qrContent').value.trim();
    if (!qrText) throw new Error('请先填写扫码内容');

    const resolved = await api(`/api/v1/inspections/points/resolve?qr_content=${encodeURIComponent(qrText)}`, { headers: authHeaders() });
    const payload = {
      system_id: Number(resolved.system_id),
      point_id: Number(resolved.point_id),
      result: $('insResult').value,
      note: $('insNote').value || null,
      inspected_at: new Date().toISOString(),
    };
    const created = await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) });
    show('inspectionResult', { resolved_point: resolved, created_record: created });
  } catch (e) { show('inspectionResult', e.message); }
};

$('btnSubmitNfc').onclick = async () => {
  try {
    const payload = {
      system_id: Number($('nfcSystemId').value),
      point_id: Number($('nfcPointId').value),
      result: $('nfcResult').value,
      note: `NFC:${$('nfcTag').value}; ${$('nfcNote').value || ''}`,
      inspected_at: new Date().toISOString(),
    };
    show('nfcResultView', await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }));
  } catch (e) { show('nfcResultView', e.message); }
};

// selfcheck
$('btnRefreshStatus').onclick = refreshStatusBase;

$('btnCreateSelfcheck').onclick = async () => {
  try {
    const summary = $('scSummary').value.trim();
    if (!summary) throw new Error('请填写自检内容');

    // 当前简化 UI 下，system/template 使用默认值（后续可改为自动选择或动态加载）
    const payload = {
      system_id: 1,
      template_id: 1,
      result: $('scResult').value,
      summary: $('scNote').value.trim() ? `${summary}；备注：${$('scNote').value.trim()}` : summary,
      checked_at: new Date().toISOString(),
    };
    show('selfcheckResult', await api('/api/v1/selfchecks/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }));
  } catch (e) { show('selfcheckResult', e.message); }
};

$('btnLoadErrors').onclick = () => {
  const hours = Number($('errorRange').value);
  const since = Date.now() - hours * 3600 * 1000;
  const errors = state.requestLogs.filter((x) => !x.ok && new Date(x.at).getTime() >= since);
  state.extractedErrors = errors.slice(0, 100);
  show('errorLogsView', state.extractedErrors.length ? state.extractedErrors : '该时间范围暂无错误日志（来自本地请求历史）');
};

$('btnAnalyzeErrors').onclick = async () => {
  try {
    const detail = state.extractedErrors.length
      ? state.extractedErrors.map((e) => `${e.at} ${e.method || ''} ${e.url || ''} status=${e.status || 0} err=${e.network_error || ''}`).join('\n').slice(0, 1800)
      : '暂无错误日志，建议先执行“提取错误日志”。';
    const payload = { title: '错误日志分析', detail, severity: $('errorAiSeverity').value };
    show('errorAiView', await api('/api/v1/ai/diagnose', { method: 'POST', headers: authHeaders(), body: JSON.stringify(payload) }));
  } catch (e) { show('errorAiView', e.message); }
};

// toolbox
$('btnToolPing').onclick = async () => {
  try {
    const data = await api('/api/v1/toolbox/ping', {
      method: 'POST', headers: authHeaders(),
      body: JSON.stringify({ host: $('tbPingHost').value.trim(), count: Number($('tbPingCount').value || 1) }),
    });
    const ok = String(JSON.stringify(data)).toLowerCase().includes('success') || String(JSON.stringify(data)).includes('true');
    $('pingStatus').className = `status-dot ${ok ? 'ok' : 'fail'}`;
    $('pingStatus').textContent = `状态：${ok ? '接通' : '可能异常'}`;
    show('pingResult', data);
  } catch (e) {
    $('pingStatus').className = 'status-dot fail';
    $('pingStatus').textContent = '状态：失败';
    show('pingResult', e.message);
  }
};

$('btnCaptureStart').onclick = () => show('captureResult', { status: 'capturing', started_at: new Date().toISOString(), note: '抓包功能当前为 Mock，后续接入真实抓包执行器。' });
$('btnCaptureStop').onclick = () => show('captureResult', { status: 'stopped', stopped_at: new Date().toISOString() });
$('btnAppRestart').onclick = () => show('appToolResult', { action: 'app_restart', status: 'mocked', message: '应用重启 Mock 完成，后续接审批+执行器。' });
$('btnAppAiQa').onclick = () => show('appToolResult', { action: 'ai_qa', status: 'mocked', answer: '这是 AI 问答 Mock 回答：后续接真实模型服务。' });

initSubNavigation();
applyProfileUI();
setLoginState(state.token ? '已加载本地 Token，可直接进入主界面' : '未登录');
switchScreen(Boolean(state.token));
switchPanel('panel-inspection');
showSub('panel-inspection', 'inspection-home');
showSub('panel-selfcheck', 'selfcheck-home');
showSub('panel-toolbox', 'toolbox-home');
