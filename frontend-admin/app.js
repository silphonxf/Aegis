const $ = (id) => document.getElementById(id);
window.AegisAdmin = window.AegisAdmin || {};

const ns = window.AegisAdmin;
ns.state = ns.state || {
  token: '',
  dashboardTimer: null,
  autoRefreshEnabled: true,
  trendSeries: { cpu: [], mem: [], disk: [] },
  latestMonitoringItems: [],
  selectedSystemCode: 'HOST-LOCAL-001',
  activeView: 'view-dashboard-overview',
  activeGroup: 'dashboard',
};

function formatError(moduleName, e) {
  const msg = e?.message || String(e) || '未知错误';
  return `【${moduleName}】请求失败\n原因：${msg}\n建议：请检查登录状态或稍后重试。`;
}

function setHeaderByView(viewId) {
  const panel = document.getElementById(viewId);
  const title = panel?.dataset.viewTitle || '管理工作台';
  const desc = panel?.dataset.viewDesc || '请选择左侧功能继续操作。';
  const titleHost = document.querySelector('.workspace-header h1');
  const descHost = document.getElementById('currentViewDesc');
  if (titleHost) titleHost.innerHTML = `${title} <span class="badge">v2.1 Tech</span>`;
  if (descHost) descHost.textContent = desc;
}

function switchView(viewId, groupId) {
  ns.state.activeView = viewId;
  ns.state.activeGroup = groupId;

  document.querySelectorAll('.view-panel').forEach((panel) => panel.classList.remove('active'));
  document.querySelectorAll('.submenu-btn').forEach((btn) => btn.classList.remove('active'));
  document.querySelectorAll('.group-btn').forEach((btn) => btn.classList.remove('active'));
  document.querySelectorAll('.submenu-list').forEach((list) => list.classList.remove('active'));

  document.getElementById(viewId)?.classList.add('active');
  document.querySelector(`.submenu-btn[data-view="${viewId}"]`)?.classList.add('active');
  document.querySelector(`.menu-group[data-group="${groupId}"] .group-btn`)?.classList.add('active');
  document.querySelector(`.menu-group[data-group="${groupId}"] .submenu-list`)?.classList.add('active');

  setHeaderByView(viewId);

  if (viewId === 'view-dashboard-overview' && ns.state.token) {
    ns.dashboard?.startDashboardAutoRefresh?.();
  } else {
    ns.dashboard?.stopDashboardAutoRefresh?.();
  }
}

function openGroup(groupId) {
  document.querySelectorAll('.menu-group').forEach((group) => {
    const isActive = group.dataset.group === groupId;
    group.classList.toggle('active', isActive);
    group.querySelector('.submenu-list')?.classList.toggle('active', isActive);
    group.querySelector('.group-btn')?.classList.toggle('active', isActive);
  });
}

$('btnLogin').onclick = async () => {
  try {
    await ns.auth.login($('username').value, $('password').value);
    $('state').textContent = '登录成功';
    ns.auth.setAuthView(true);
    ns.debug?.syncDebugMeta?.();
    switchView('view-dashboard-overview', 'dashboard');
    await ns.dashboard?.refreshDashboard?.();
  } catch (e) {
    $('state').textContent = `登录失败: ${e.message}`;
  }
};

$('btnLogout').onclick = () => {
  ns.auth.logout();
};

$('btnRefreshDashboard').onclick = () => ns.dashboard?.refreshDashboard?.();
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

$('btnRefreshHistory').onclick = () => ns.api.renderHistory();
$('btnClearHistory').onclick = () => ns.debug.clearHistory();
$('btnDebugHealthz').onclick = () => ns.debug.checkHealthz().catch((e) => { $('debugPanelResult').textContent = e.message; });
$('btnDebugMe').onclick = () => ns.debug.loadCurrentUser().catch((e) => { $('debugPanelResult').textContent = e.message; });
$('btnThreatbookQuery').onclick = () => ns.threatbook.queryThreatbook().catch((e) => { $('threatbookResult').textContent = formatError('高危IP研判', e); });
$('btnThreatbookFillDemo').onclick = () => ns.threatbook.fillDemo();
$('btnThreatbookUploadExcel').onclick = () => ns.threatbook.uploadExcel().catch((e) => { $('threatbookResult').textContent = formatError('Excel导入研判', e); });
$('btnThreatbookApplyFilter').onclick = () => ns.threatbook.applyFilter();
$('btnThreatbookResetFilter').onclick = () => ns.threatbook.resetFilter();
$('btnThreatbookBlock').onclick = () => ns.threatbook.blockIp().catch((e) => { $('threatbookResult').textContent = formatError('模拟封禁', e); });
$('btnThreatbookBatchBlock').onclick = () => ns.threatbook.batchBlockAutoCandidates().catch((e) => { $('threatbookResult').textContent = formatError('批量模拟封禁', e); });
$('btnThreatbookExport').onclick = () => ns.threatbook.exportJson();

$('btnToggleAutoRefresh').onclick = () => {
  ns.state.autoRefreshEnabled = !ns.state.autoRefreshEnabled;
  if (ns.state.autoRefreshEnabled && ns.state.activeView === 'view-dashboard-overview') ns.dashboard?.startDashboardAutoRefresh?.();
  else ns.dashboard?.stopDashboardAutoRefresh?.();
  ns.dashboard?.setLiveStatus?.(ns.state.autoRefreshEnabled && Boolean(ns.state.dashboardTimer));
};

Array.from(document.querySelectorAll('.group-btn')).forEach((btn) => {
  btn.addEventListener('click', () => {
    const groupId = btn.dataset.groupTarget;
    openGroup(groupId);
    const firstView = document.querySelector(`.menu-group[data-group="${groupId}"] .submenu-btn`)?.dataset.view;
    if (firstView) switchView(firstView, groupId);
  });
});

Array.from(document.querySelectorAll('.submenu-btn')).forEach((btn) => {
  btn.addEventListener('click', () => {
    const viewId = btn.dataset.view;
    const group = btn.closest('.menu-group')?.dataset.group;
    if (viewId && group) switchView(viewId, group);
  });
});

ns.api.renderHistory();
ns.debug?.syncDebugMeta?.();
ns.auth.setAuthView(false);
openGroup('dashboard');
switchView('view-dashboard-overview', 'dashboard');
ns.users?.findUsers?.('').catch(() => {});
ns.systems?.findSystems?.('').catch(() => {});
ns.assets?.listAssets?.().catch(() => {});
