window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  const TOKEN_KEY = 'aegis_admin_token';

  function readStoredToken() {
    try { return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || ''; }
    catch {
      try { return sessionStorage.getItem(TOKEN_KEY) || ''; }
      catch { return ''; }
    }
  }

  function storeToken(token) {
    try { localStorage.setItem(TOKEN_KEY, token); }
    catch {}
    try { sessionStorage.setItem(TOKEN_KEY, token); }
    catch {}
  }

  function clearStoredToken() {
    try { localStorage.removeItem(TOKEN_KEY); }
    catch {}
    try { sessionStorage.removeItem(TOKEN_KEY); }
    catch {}
  }

  function setRestoring(isRestoring) {
    document.documentElement.classList.toggle('auth-restoring', Boolean(isRestoring));
    document.body?.classList.toggle('auth-restoring', Boolean(isRestoring));
  }

  function setAuthView(isLoggedIn) {
    setRestoring(false);
    const loginView = document.getElementById('loginView');
    const appView = document.getElementById('appView');
    document.body.classList.toggle('is-authenticated', Boolean(isLoggedIn));

    loginView?.classList.toggle('hidden', Boolean(isLoggedIn));
    appView?.classList.toggle('hidden', !isLoggedIn);
    loginView?.toggleAttribute('hidden', Boolean(isLoggedIn));
    appView?.toggleAttribute('hidden', !isLoggedIn);
    loginView?.setAttribute('aria-hidden', String(Boolean(isLoggedIn)));
    appView?.setAttribute('aria-hidden', String(!isLoggedIn));

    if (!isLoggedIn) {
      document.querySelectorAll('.modal').forEach((modal) => {
        modal.classList.add('hidden');
        modal.setAttribute('hidden', '');
        modal.setAttribute('aria-hidden', 'true');
      });
    }
  }

  function forceRelogin(message = '登录已失效，请重新登录') {
    ns.state.token = '';
    clearStoredToken();
    const stateEl = document.getElementById('state');
    if (stateEl) stateEl.textContent = message;
    if (ns.dashboard) ns.dashboard.stopDashboardAutoRefresh();
    setAuthView(false);
  }

  async function login(username, password) {
    const data = await ns.api.request('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    ns.state.token = data.access_token;
    storeToken(ns.state.token);
    setAuthView(true);
    return data;
  }

  async function restoreSession() {
    const token = readStoredToken();
    if (!token) {
      setRestoring(false);
      setAuthView(false);
      return null;
    }

    setRestoring(true);
    ns.state.token = token;
    try {
      const me = await ns.api.request('/api/v1/auth/me', { headers: ns.api.headers() });
      storeToken(token);
      setAuthView(true);
      return me;
    } catch (e) {
      forceRelogin('登录已过期，请重新登录');
      return null;
    }
  }

  function logout() {
    ns.state.token = '';
    clearStoredToken();
    const stateEl = document.getElementById('state');
    if (stateEl) stateEl.textContent = '已退出登录';
    if (ns.dashboard) ns.dashboard.stopDashboardAutoRefresh();
    setAuthView(false);
  }

  ns.auth = { setAuthView, forceRelogin, login, restoreSession, logout };
})(window.AegisAdmin);
