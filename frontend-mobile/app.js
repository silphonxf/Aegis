const $ = (id) => document.getElementById(id);
const state = {
  token: localStorage.getItem('aegis_token') || '',
  requestLogs: JSON.parse(localStorage.getItem('aegis_request_logs') || '[]'),
};

const ERROR_CODE_DOC = {
  AUTH_INVALID: '用户名或密码错误，请检查账号或重置密码。',
  USER_EXISTS: '用户名已存在，请更换用户名。',
  ROLE_NOT_FOUND: '角色不存在，请联系管理员检查角色配置。',
  VALIDATION_ERROR: '请求参数校验失败，请检查必填项与字段格式。',
  HTTP_ERROR: '通用请求错误，请查看请求历史中的响应详情。',
};

function getBase() { return $('apiBase').value.trim().replace(/\/$/, ''); }
function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  return headers;
}
function setLoginState(text) { $('loginState').textContent = text; }
function show(id, data) { $(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2); }

function switchScreen(loggedIn) {
  $('loginScreen').classList.toggle('active', !loggedIn);
  $('appScreen').classList.toggle('active', loggedIn);
}

function switchPanel(panelId) {
  document.querySelectorAll('.panel').forEach((p) => p.classList.remove('active'));
  document.querySelectorAll('.menu-tabs .tab').forEach((t) => t.classList.remove('active'));
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.add('active');
  const tab = document.querySelector(`.menu-tabs .tab[data-panel="${panelId}"]`);
  if (tab) tab.classList.add('active');
}

function initMenu() {
  document.querySelectorAll('.menu-tabs .tab').forEach((tab) => {
    tab.addEventListener('click', () => switchPanel(tab.dataset.panel));
  });
}

function upsertErrorDoc() {
  const lines = Object.entries(ERROR_CODE_DOC).map(([code, desc]) => `- ${code}: ${desc}`).join('\n');
  show('errorCodeDoc', `常见错误码说明：\n${lines}`);
}

function rememberLog(log) {
  state.requestLogs.unshift(log);
  if (state.requestLogs.length > 200) state.requestLogs = state.requestLogs.slice(0, 200);
  localStorage.setItem('aegis_request_logs', JSON.stringify(state.requestLogs));
  renderHistory();
}
function renderHistory() {
  show('requestHistory', { total: state.requestLogs.length, latest: state.requestLogs.slice(0, 30) });
}

function parseError(respData, fallback) {
  if (!respData) return { code: 'HTTP_ERROR', message: fallback };
  if (typeof respData === 'string') return { code: 'HTTP_ERROR', message: respData };
  if (respData.code || respData.message) return { code: respData.code || 'HTTP_ERROR', message: respData.message || fallback };
  if (respData.detail && typeof respData.detail === 'string') return { code: 'HTTP_ERROR', message: respData.detail };
  return { code: 'HTTP_ERROR', message: fallback };
}

async function api(path, options = {}) {
  const method = options.method || 'GET';
  const url = `${getBase()}${path}`;
  const started = Date.now();
  try {
    const resp = await fetch(url, options);
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) {
      const errObj = parseError(data, `HTTP ${resp.status}`);
      const help = ERROR_CODE_DOC[errObj.code];
      rememberLog({ at: new Date().toISOString(), ok: false, method, url, status: resp.status, duration_ms: Date.now() - started, request_body: options.body ? JSON.parse(options.body) : null, response: data, error: errObj });
      throw new Error(help ? `${errObj.code}: ${errObj.message}\n建议：${help}` : `${errObj.code}: ${errObj.message}`);
    }
    rememberLog({ at: new Date().toISOString(), ok: true, method, url, status: resp.status, duration_ms: Date.now() - started, request_body: options.body ? JSON.parse(options.body) : null, response: data });
    return data;
  } catch (e) {
    if (!String(e.message || '').includes(':')) rememberLog({ at: new Date().toISOString(), ok: false, method, url, status: 0, duration_ms: Date.now() - started, request_body: options.body ? JSON.parse(options.body) : null, network_error: e.message || 'fetch failed' });
    throw e;
  }
}

function exportDebugLogs() {
  const payload = { exported_at: new Date().toISOString(), api_base: getBase(), request_logs: state.requestLogs };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `aegis-mobile-debug-${Date.now()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

$('btnPing').onclick = async () => {
  try { const data = await api('/healthz'); alert(`后端可用：${data.status || 'ok'}`); }
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
    setLoginState('登录成功，已进入主界面');
    switchScreen(true);
    switchPanel('panel-overview');
  } catch (e) { setLoginState(`登录失败：${e.message}`); }
};

$('btnLogout').onclick = () => {
  state.token = '';
  localStorage.removeItem('aegis_token');
  switchScreen(false);
  setLoginState('已退出登录');
};

$('btnMe').onclick = async () => { try { show('meResult', await api('/api/v1/auth/me', { headers: authHeaders() })); } catch (e) { show('meResult', e.message); } };
$('btnResolve').onclick = async () => { try { const qr = encodeURIComponent($('qrContent').value.trim()); const data = await api(`/api/v1/inspections/points/resolve?qr_content=${qr}`, { headers: authHeaders() }); show('resolveResult', data); $('insSystemId').value = data.system_id; $('insPointId').value = data.point_id; if (!$('scSystemId').value) $('scSystemId').value = data.system_id; } catch (e) { show('resolveResult', e.message); } };
$('btnCreateInspection').onclick = async () => { try { show('inspectionResult', await api('/api/v1/inspections/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ system_id: Number($('insSystemId').value), point_id: Number($('insPointId').value), result: $('insResult').value, note: $('insNote').value || null, inspected_at: new Date().toISOString() }) })); } catch (e) { show('inspectionResult', e.message); } };
$('btnLoadInspectionHistory').onclick = async () => { try { const sid = $('insSystemId').value.trim(); const q = sid ? `?system_id=${encodeURIComponent(sid)}&page=1&size=20` : '?page=1&size=20'; show('inspectionHistory', await api(`/api/v1/inspections/records${q}`, { headers: authHeaders() })); } catch (e) { show('inspectionHistory', e.message); } };
$('btnCreateSelfcheck').onclick = async () => { try { show('selfcheckResult', await api('/api/v1/selfchecks/records', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ system_id: Number($('scSystemId').value), template_id: Number($('scTemplateId').value), result: $('scResult').value, summary: $('scSummary').value || null, checked_at: new Date().toISOString() }) })); } catch (e) { show('selfcheckResult', e.message); } };
$('btnLoadSelfcheckHistory').onclick = async () => { try { const sid = $('scSystemId').value.trim(); const q = sid ? `?system_id=${encodeURIComponent(sid)}&page=1&size=20` : '?page=1&size=20'; show('selfcheckHistory', await api(`/api/v1/selfchecks/records${q}`, { headers: authHeaders() })); } catch (e) { show('selfcheckHistory', e.message); } };
$('btnLoadOverview').onclick = async () => { try { show('overviewResult', await api('/api/v1/monitoring/overview', { headers: authHeaders() })); } catch (e) { show('overviewResult', e.message); } };
$('btnLoadRules').onclick = async () => { try { show('rulesResult', await api('/api/v1/monitoring/rules', { headers: authHeaders() })); } catch (e) { show('rulesResult', e.message); } };
$('btnToolPing').onclick = async () => { try { show('toolboxResult', await api('/api/v1/toolbox/ping', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ host: $('tbPingHost').value.trim(), count: 1 }) })); } catch (e) { show('toolboxResult', e.message); } };
$('btnToolPort').onclick = async () => { try { show('toolboxResult', await api('/api/v1/toolbox/port-check', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ host: $('tbPortHost').value.trim(), port: Number($('tbPort').value), timeout_ms: 1200 }) })); } catch (e) { show('toolboxResult', e.message); } };
$('btnToolRestart').onclick = async () => { try { show('toolboxResult', await api('/api/v1/toolbox/restart-task', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ target: $('tbRestartTarget').value.trim(), reason: 'mobile-toolbox-mock' }) })); } catch (e) { show('toolboxResult', e.message); } };
$('btnTaskList').onclick = async () => { try { const s = $('taskStatusFilter').value; const q = s ? `?page=1&size=20&status=${encodeURIComponent(s)}` : '?page=1&size=20'; show('taskResult', await api(`/api/v1/toolbox/tasks${q}`, { headers: authHeaders() })); } catch (e) { show('taskResult', e.message); } };
$('btnTaskUpdate').onclick = async () => { try { const taskId = Number($('taskId').value); show('taskResult', await api(`/api/v1/toolbox/tasks/${taskId}/status`, { method: 'PUT', headers: authHeaders(), body: JSON.stringify({ status: $('taskToStatus').value, note: $('taskNote').value || null }) })); } catch (e) { show('taskResult', e.message); } };
$('btnAiDiagnose').onclick = async () => { try { show('aiResult', await api('/api/v1/ai/diagnose', { method: 'POST', headers: authHeaders(), body: JSON.stringify({ title: $('aiTitle').value.trim(), detail: $('aiDetail').value.trim(), severity: $('aiSeverity').value }) })); } catch (e) { show('aiResult', e.message); } };
$('btnAiHistory').onclick = async () => { try { const sev = $('aiSeverity').value; show('aiHistory', await api(`/api/v1/ai/diagnoses?page=1&size=20&severity=${encodeURIComponent(sev)}`, { headers: authHeaders() })); } catch (e) { show('aiHistory', e.message); } };

$('btnExportLogs').onclick = exportDebugLogs;
$('btnClearLogs').onclick = () => { state.requestLogs = []; localStorage.removeItem('aegis_request_logs'); renderHistory(); };

setLoginState(state.token ? '已加载本地 Token，可直接进入主界面' : '未登录');
upsertErrorDoc();
renderHistory();
initMenu();
switchScreen(Boolean(state.token));
switchPanel('panel-overview');
