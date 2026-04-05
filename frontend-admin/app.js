const $ = (id) => document.getElementById(id);
window.AegisAdmin = window.AegisAdmin || {};

const ns = window.AegisAdmin;
ns.state = ns.state || {
  token: '',
  requestHistory: [],
};

function setAuthView(isLoggedIn) {
  $('loginView').classList.toggle('hidden', isLoggedIn);
  $('appView').classList.toggle('hidden', !isLoggedIn);
  ns.debug?.syncDebugMeta?.();
}

function base() {
  const protocol = window.location.protocol && window.location.protocol.startsWith('http') ? window.location.protocol : 'http:';
  const host = window.location.hostname || '127.0.0.1';
  return `${protocol}//${host}:8000`;
}

function getHistory() {
  try { return JSON.parse(localStorage.getItem('aegis_admin_request_history') || '[]'); }
  catch { return []; }
}

function pushHistory(item) {
  const arr = getHistory();
  arr.unshift(item);
  localStorage.setItem('aegis_admin_request_history', JSON.stringify(arr.slice(0, 20)));
  ns.debug?.renderHistorySummary?.();
}

function renderHistory() {
  $('requestHistory').textContent = JSON.stringify(getHistory(), null, 2);
  ns.debug?.renderHistorySummary?.();
}

async function request(path, options = {}) {
  const startedAt = new Date().toISOString();
  const method = options.method || 'GET';
  const headers = options.headers || { 'Content-Type': 'application/json' };
  if (ns.state.token && !headers.Authorization) headers.Authorization = `Bearer ${ns.state.token}`;
  const resp = await fetch(`${base()}${path}`, { ...options, headers });
  const data = await resp.json().catch(() => ({}));
  pushHistory({ startedAt, method, path, ok: resp.ok, status: resp.status });
  renderHistory();
  if (!resp.ok) throw new Error(data?.message || `HTTP ${resp.status}`);
  return data;
}

$('btnLogin').onclick = async () => {
  try {
    const d = await request('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $('username').value, password: $('password').value }),
    });
    ns.state.token = d.access_token;
    $('state').textContent = '登录成功';
    setAuthView(true);
    ns.debug?.syncDebugMeta?.();
  } catch (e) {
    $('state').textContent = `登录失败: ${e.message}`;
  }
};

$('btnLogout').onclick = () => {
  ns.state.token = '';
  $('state').textContent = '已退出登录';
  setAuthView(false);
};

$('btnRefreshHistory').onclick = () => renderHistory();
$('btnClearHistory').onclick = () => ns.debug.clearHistory();
$('btnDebugHealthz').onclick = () => ns.debug.checkHealthz().catch((e) => { $('debugPanelResult').textContent = e.message; });
$('btnDebugMe').onclick = () => ns.debug.loadCurrentUser().catch((e) => { $('debugPanelResult').textContent = e.message; });

renderHistory();
ns.debug?.syncDebugMeta?.();
setAuthView(false);
