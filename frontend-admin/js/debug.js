window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function syncDebugMeta() {
    setText('debugApiBase', ns.api.base());
    setText('debugTokenState', ns.state.token ? '已登录' : '未登录');
  }

  function renderHistorySummary() {
    const history = ns.api.getHistory();
    const latest = history[0];
    setText('debugLastRequestAt', latest?.startedAt || '--');
  }

  async function checkHealthz() {
    syncDebugMeta();
    renderHistorySummary();
    const data = await fetch(`${ns.api.base()}/healthz`).then((r) => r.json());
    setText('debugPanelResult', JSON.stringify(data, null, 2));
    return data;
  }

  async function loadCurrentUser() {
    syncDebugMeta();
    renderHistorySummary();
    if (!ns.state.token) {
      setText('debugCurrentUser', '--');
      setText('debugPanelResult', '当前未登录，无法读取 /auth/me');
      return null;
    }
    const data = await ns.api.request('/api/v1/auth/me', { headers: ns.api.headers() });
    setText('debugCurrentUser', `${data.username || '--'} / ${data.role || '--'}`);
    setText('debugPanelResult', JSON.stringify(data, null, 2));
    renderHistorySummary();
    return data;
  }

  function clearHistory() {
    localStorage.removeItem('aegis_admin_request_history');
    ns.api.renderHistory();
    renderHistorySummary();
  }

  ns.debug = { syncDebugMeta, renderHistorySummary, checkHealthz, loadCurrentUser, clearHistory };
})(window.AegisAdmin);
