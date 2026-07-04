window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
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
    const resp = await fetch(`${base()}${path}`, options);
    const data = await resp.json().catch(() => ({}));

    if (!resp.ok) {
      const code = data?.code;
      const msg = data?.message || `HTTP ${resp.status}`;
      if (ns.auth && (resp.status === 401 || code === 'TOKEN_EXPIRED' || code === 'TOKEN_INVALID' || code === 'USER_DISABLED' || code === 'USER_NOT_FOUND')) {
        ns.auth.forceRelogin(`${msg}（请重新登录）`);
      }
      throw new Error(`${code ? `[${code}] ` : ''}${msg}`);
    }

    return data;
  }

  async function loadOptions(path, mapper = (x) => x) {
    const data = await request(path, { headers: headers() });
    const items = Array.isArray(data.items) ? data.items : [];
    return items.map(mapper);
  }

  ns.api = { base, headers, request, loadOptions };
})(window.AegisAdmin);
