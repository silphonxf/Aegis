window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function setAuthView(isLoggedIn) {
    document.getElementById('loginView').classList.toggle('hidden', isLoggedIn);
    document.getElementById('appView').classList.toggle('hidden', !isLoggedIn);
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
