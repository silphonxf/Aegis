const $ = (id) => document.getElementById(id);
const bindClick = (id, handler) => {
  const el = $(id);
  if (!el) return false;
  el.onclick = handler;
  return true;
};
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

  document.querySelectorAll('.view-panel').forEach((panel) => {
    panel.classList.remove('active');
    panel.style.display = 'none';
  });
  document.querySelectorAll('.submenu-btn').forEach((btn) => btn.classList.remove('active'));
  document.querySelectorAll('.group-btn').forEach((btn) => btn.classList.remove('active'));
  document.querySelectorAll('.submenu-list').forEach((list) => list.classList.remove('active'));
  document.querySelectorAll('.menu-group').forEach((group) => group.classList.remove('active'));

  const activePanel = document.getElementById(viewId);
  if (activePanel) {
    activePanel.classList.add('active');
    activePanel.style.display = 'grid';
  }
  document.querySelector(`.submenu-btn[data-view="${viewId}"]`)?.classList.add('active');
  document.querySelector(`.menu-group[data-group="${groupId}"]`)?.classList.add('active');
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

bindClick('btnLogin', async () => {
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
});

bindClick('btnLogout', () => {
  ns.auth.logout();
});

bindClick('btnRefreshDashboard', () => ns.dashboard?.refreshDashboard?.());
bindClick('btnToolTaskList', () => ns.toolbox.listTasks().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); }));
bindClick('btnToolTaskUpdate', () => ns.toolbox.updateTask().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); }));
bindClick('btnListAssets', () => ns.assets.listAssets().catch((e) => { $('assetListResult').textContent = formatError('资产列表', e); }));
bindClick('btnFindUsers', () => ns.users.findUsers($('userSearchKeyword').value.trim()).catch((e) => {
  $('userListSummary').textContent = formatError('用户查询', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';
}));
bindClick('btnFindSystems', () => ns.systems.findSystems($('systemSearchKeyword2').value.trim()).catch((e) => {
  $('systemListSummary').textContent = formatError('系统查询', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';
}));
bindClick('btnLoadRules', () => ns.rulesAudit.loadRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); }));
bindClick('btnSaveRules', () => ns.rulesAudit.saveRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); }));
bindClick('btnAudit', () => ns.rulesAudit.loadAudit().catch((e) => { $('audit').textContent = formatError('审计日志', e); }));
bindClick('btnCreateTemplate', () => ns.templates.createTemplate().catch((e) => { $('templateCreateResult').textContent = formatError('创建模板', e); }));
bindClick('btnListTemplates', () => ns.templates.listTemplates().catch((e) => { $('templateListResult').textContent = formatError('模板列表', e); }));
bindClick('btnCreateSnapshot', () => ns.templates.createSnapshot().catch((e) => { $('snapshotResult').textContent = formatError('状态快照', e); }));

bindClick('btnOpenCreateUserModal', () => ns.modals.openModal('createUserModal'));
bindClick('btnCloseCreateUserModal', () => ns.modals.closeModal('createUserModal'));
bindClick('btnOpenCreateSystemModal', () => ns.modals.openModal('createSystemModal'));
bindClick('btnCloseCreateSystemModal', () => ns.modals.closeModal('createSystemModal'));
bindClick('btnOpenCreateAssetModal', () => ns.modals.openModal('createAssetModal'));
bindClick('btnCloseCreateAssetModal', () => ns.modals.closeModal('createAssetModal'));
bindClick('btnOpenAssetImportModal', () => ns.modals.openModal('assetImportModal'));
bindClick('btnCloseAssetImportModal', () => ns.modals.closeModal('assetImportModal'));
bindClick('btnSubmitCreateUser', () => ns.modals.submitCreateUser().catch((e) => {
  $('userListSummary').textContent = formatError('创建用户', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';
}));
bindClick('btnSubmitCreateSystem', () => ns.modals.submitCreateSystem().catch((e) => {
  $('systemListSummary').textContent = formatError('创建系统', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';
}));
bindClick('btnSubmitCreateAsset', () => ns.modals.submitCreateAsset().catch((e) => {
  $('assetResult').textContent = formatError('资产操作', e);
}));
bindClick('btnBatchAssets', () => ns.assets.batchAssets().catch((e) => {
  $('assetResult').textContent = formatError('资产导入', e);
}));

bindClick('btnRefreshHistory', () => ns.api.renderHistory());
bindClick('btnClearHistory', () => ns.debug.clearHistory());
bindClick('btnDebugHealthz', () => ns.debug.checkHealthz().catch((e) => { $('debugPanelResult').textContent = e.message; }));
bindClick('btnDebugMe', () => ns.debug.loadCurrentUser().catch((e) => { $('debugPanelResult').textContent = e.message; }));
bindClick('btnThreatbookQuery', () => ns.threatbook.queryThreatbook().catch((e) => { $('threatbookResult').textContent = formatError('高危IP研判', e); }));
bindClick('btnThreatbookFillDemo', () => ns.threatbook.fillDemo());
bindClick('btnThreatbookUploadExcel', () => ns.threatbook.uploadExcel().catch((e) => { $('threatbookResult').textContent = formatError('Excel导入研判', e); }));
bindClick('btnThreatbookApplyFilter', () => ns.threatbook.applyFilter());
bindClick('btnThreatbookResetFilter', () => ns.threatbook.resetFilter());
bindClick('btnThreatbookBlock', () => ns.threatbook.blockIp().catch((e) => { $('threatbookResult').textContent = formatError('模拟封禁', e); }));
bindClick('btnThreatbookBatchBlock', () => ns.threatbook.batchBlockAutoCandidates().catch((e) => { $('threatbookResult').textContent = formatError('批量模拟封禁', e); }));
bindClick('btnThreatbookExport', () => ns.threatbook.exportJson());

bindClick('btnToggleAutoRefresh', () => {
  ns.state.autoRefreshEnabled = !ns.state.autoRefreshEnabled;
  if (ns.state.autoRefreshEnabled && ns.state.activeView === 'view-dashboard-overview') ns.dashboard?.startDashboardAutoRefresh?.();
  else ns.dashboard?.stopDashboardAutoRefresh?.();
  ns.dashboard?.setLiveStatus?.(ns.state.autoRefreshEnabled && Boolean(ns.state.dashboardTimer));
});

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
