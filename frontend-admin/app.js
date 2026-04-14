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
  dashboardTimer: null,
  autoRefreshEnabled: true,
  trendSeries: { cpu: [], mem: [], disk: [] },
  latestMonitoringItems: [],
  selectedSystemCode: 'HOST-LOCAL-001',
};

function formatError(moduleName, e) {
  const msg = e?.message || String(e) || '未知错误';
  return `【${moduleName}】请求失败\n原因：${msg}\n建议：请检查登录状态或稍后重试。`;
}

function switchPanel(sectionId) {
  document.querySelectorAll('.panel').forEach((panel) => panel.classList.remove('active'));
  document.querySelectorAll('.menu-btn').forEach((btn) => btn.classList.remove('active'));
  document.getElementById(sectionId)?.classList.add('active');
  document.querySelector(`.menu-btn[data-section="${sectionId}"]`)?.classList.add('active');

  if (sectionId === 'panel-dashboard' && ns.state.token) ns.dashboard.startDashboardAutoRefresh();
  else ns.dashboard.stopDashboardAutoRefresh();
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
    await ns.auth.login($('username').value, $('password').value);
    $('state').textContent = '登录成功（刷新页面后需重新登录）';
    ns.auth.setAuthView(true);
    switchPanel('panel-dashboard');
    await ns.dashboard.refreshDashboard();
  } catch (e) {
    $('state').textContent = `登录失败: ${e.message}`;
  }
};

$('btnRefreshDashboard').onclick = () => ns.dashboard.refreshDashboard();
$('btnToolTaskList').onclick = () => ns.toolbox.listTasks().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); });
$('btnToolTaskUpdate').onclick = () => ns.toolbox.updateTask().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); });
$('btnListAssets').onclick = () => ns.assets.listAssets().catch((e) => { $('assetListResult').textContent = formatError('资产列表', e); });
$('btnFindUsers').onclick = () => ns.users.findUsers($('userSearchKeyword').value.trim()).catch((e) => {
  $('userListSummary').textContent = formatError('用户查询', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';
});
$('btnFindSystems').onclick = () => ns.systems.findSystems($('systemSearchKeyword2').value.trim()).catch((e) => {
  $('systemListSummary').textContent = formatError('系统查询', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';
});
$('btnLoadRules').onclick = () => ns.rulesAudit.loadRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); });
$('btnSaveRules').onclick = () => ns.rulesAudit.saveRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); });
$('btnAudit').onclick = () => ns.rulesAudit.loadAudit().catch((e) => { $('audit').textContent = formatError('审计日志', e); });
$('btnCreateTemplate').onclick = () => ns.templates.createTemplate().catch((e) => { $('templateCreateResult').textContent = formatError('创建模板', e); });
$('btnListTemplates').onclick = () => ns.templates.listTemplates().catch((e) => { $('templateListResult').textContent = formatError('模板列表', e); });
$('btnCreateSnapshot').onclick = () => ns.templates.createSnapshot().catch((e) => { $('snapshotResult').textContent = formatError('状态快照', e); });
$('btnCreateAsset').onclick = async () => {
  try {
    const payload = {
      asset_code: $('assetCode').value.trim(),
      name: $('assetName').value.trim(),
      category: $('assetCategory').value.trim() || 'server',
      system_id: $('assetSystemId').value.trim() ? Number($('assetSystemId').value) : null,
      location: $('assetLocation').value.trim() || null,
      status: $('assetStatus').value.trim() || 'in_use',
    };
    await ns.assets.createAsset(payload);
  } catch (e) {
    $('assetResult').textContent = formatError('资产操作', e);
  }
};

$('btnOpenCreateUserModal').onclick = () => ns.modals.openModal('createUserModal');
$('btnCloseCreateUserModal').onclick = () => ns.modals.closeModal('createUserModal');
$('btnOpenCreateSystemModal').onclick = () => ns.modals.openModal('createSystemModal');
$('btnCloseCreateSystemModal').onclick = () => ns.modals.closeModal('createSystemModal');
$('btnSubmitCreateUser').onclick = () => ns.modals.submitCreateUser().catch((e) => {
  $('userListSummary').textContent = formatError('创建用户', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';
});
$('btnSubmitCreateSystem').onclick = () => ns.modals.submitCreateSystem().catch((e) => {
  $('systemListSummary').textContent = formatError('创建系统', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';
});

$('btnAssetFilterClear').onclick = () => ns.debug.clearAssetFilters();
$('btnAuditClear').onclick = () => ns.debug.clearAuditFilters();
$('btnRefreshHistory').onclick = () => ns.api.renderHistory();
$('btnClearHistory').onclick = () => ns.debug.clearHistory();

$('btnToggleAutoRefresh').onclick = () => {
  ns.state.autoRefreshEnabled = !ns.state.autoRefreshEnabled;
  if (ns.state.autoRefreshEnabled) ns.dashboard.startDashboardAutoRefresh();
  else ns.dashboard.stopDashboardAutoRefresh();
  ns.dashboard.setLiveStatus(ns.state.autoRefreshEnabled && Boolean(ns.state.dashboardTimer));
};

Array.from(document.querySelectorAll('.menu-btn')).forEach((btn) => {
  btn.addEventListener('click', () => switchPanel(btn.dataset.section));
});

Array.from(document.querySelectorAll('.tool-tab')).forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tool-tab').forEach((b) => b.classList.remove('active'));
    document.querySelectorAll('.tool-pane').forEach((p) => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById(btn.dataset.tool)?.classList.add('active');
    const hint = document.getElementById('toolHint');
    if (hint) hint.textContent = btn.dataset.desc || '';
  });
});

$('btnLogout').onclick = () => ns.auth.logout();
ns.api.renderHistory();
ns.auth.setAuthView(false);
