window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  const REQ_HISTORY_KEY = 'aegis_admin_request_history';

  function getHistory() {
    try { return JSON.parse(localStorage.getItem(REQ_HISTORY_KEY) || '[]'); }
    catch { return []; }
  }

  function pushHistory(item) {
    const arr = getHistory();
    arr.unshift(item);
    localStorage.setItem(REQ_HISTORY_KEY, JSON.stringify(arr.slice(0, 20)));
  }

  function renderHistory() {
    const el = document.getElementById('requestHistory');
    if (el) el.textContent = JSON.stringify(getHistory(), null, 2);
  }

  function base() {
    const host = window.location.hostname || '127.0.0.1';
    return `https://${host}:8000`;
  }

  function headers() {
    const h = { 'Content-Type': 'application/json' };
    if (ns.state.token) h.Authorization = `Bearer ${ns.state.token}`;
    return h;
  }

  async function request(path, options = {}) {
    const startedAt = new Date().toISOString();
    const method = options.method || 'GET';
    const resp = await fetch(`${base()}${path}`, options);
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const code = data?.code;
      const msg = data?.message || `HTTP ${resp.status}`;
      pushHistory({ startedAt, method, path, ok: false, status: resp.status, code: code || null, message: msg });
      renderHistory();

      if (ns.auth && (code === 'TOKEN_EXPIRED' || code === 'TOKEN_INVALID' || code === 'USER_DISABLED' || code === 'USER_NOT_FOUND')) {
        ns.auth.forceRelogin(`${msg}（请重新登录）`);
      }
      throw new Error(`${code ? `[${code}] ` : ''}${msg}`);
    }

    pushHistory({ startedAt, method, path, ok: true, status: resp.status, code: null, message: 'OK' });
    renderHistory();
    return data;
  }

  async function loadOptions(path, mapper = (x) => x) {
    const data = await request(path, { headers: headers() });
    const items = Array.isArray(data.items) ? data.items : [];
    return items.map(mapper);
  }

  ns.api = { base, headers, request, getHistory, pushHistory, renderHistory, loadOptions };
})(window.AegisAdmin);
