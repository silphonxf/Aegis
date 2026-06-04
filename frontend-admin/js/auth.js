window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function setAuthView(isLoggedIn) {
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
    setAuthView(true);
    return data;
  }

  function logout() {
    ns.state.token = '';
    const stateEl = document.getElementById('state');
    if (stateEl) stateEl.textContent = '已退出登录';
    if (ns.dashboard) ns.dashboard.stopDashboardAutoRefresh();
    setAuthView(false);
  }

  ns.auth = { setAuthView, forceRelogin, login, logout };
})(window.AegisAdmin);
