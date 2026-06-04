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

const VIEW_GROUP_MAP = {
  'view-dashboard-overview': 'dashboard',
  'view-ops-workbench': 'ops-workbench',
  'view-systems': 'ops-workbench',
  'view-assets': 'ops-workbench',
  'view-users': 'ops-workbench',
  'view-tool-template': 'ops-workbench',
  'view-runbook-console': 'runbook',
  'view-emergency-ssh': 'runbook',
  'view-emergency-server': 'runbook',
  'view-emergency-db': 'runbook',
  'view-emergency-process': 'runbook',
  'view-tool-ops': 'approval-audit',
  'view-tool-rules': 'approval-audit',
  'view-tool-ai': 'approval-audit',
  'view-tool-threatbook': 'approval-audit',
  'view-tool-debug': 'approval-audit',
};

function formatError(moduleName, e) {
  const msg = e?.message || String(e) || '未知错误';
  return `【${moduleName}】请求失败\n原因：${msg}\n建议：请检查登录状态或稍后重试。`;
}

function setHeaderByView(viewId) {
  const isDashboard = viewId === 'view-dashboard-overview';
  document.getElementById('workspaceHeader')?.classList.toggle('hidden', !isDashboard);
  document.getElementById('controlStrip')?.classList.toggle('hidden', !isDashboard);

  const panel = document.getElementById(viewId);
  const title = panel?.dataset.viewTitle || '管理工作台';
  const desc = panel?.dataset.viewDesc || '请选择左侧功能继续操作。';
  const titleHost = document.querySelector('.workspace-header h1');
  const descHost = document.getElementById('currentViewDesc');
  const stripView = document.getElementById('controlStripView');
  if (titleHost) titleHost.innerHTML = `${title} <span class="badge">v2.1 Tech</span>`;
  if (descHost) descHost.textContent = desc;
  if (stripView) stripView.textContent = title;
}

function switchView(viewId, groupId) {
  if (!ns.state.token) {
    ns.auth?.setAuthView?.(false);
    return;
  }

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

  if (viewId === 'view-emergency-ssh') ns.emergencyConfig?.listSshHosts?.();
  if (viewId === 'view-emergency-server') ns.emergencyConfig?.listServerActions?.();
  if (viewId === 'view-emergency-db') ns.emergencyConfig?.listDbActions?.();
  if (viewId === 'view-emergency-process') ns.emergencyConfig?.listProcessActions?.();
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
    ns.debug?.syncDebugMeta?.();
    openGroup('dashboard');
    switchView('view-dashboard-overview', 'dashboard');
    Promise.allSettled([
      ns.sharedData?.hydrateAdminSelectors?.(),
      ns.dashboard?.refreshDashboard?.(),
    ]);
  } catch (e) {
    $('state').textContent = `登录失败: ${e.message}`;
  }
});

bindClick('btnLogout', () => {
  ns.auth.logout();
});

bindClick('btnRefreshDashboard', () => ns.dashboard?.refreshDashboard?.());
bindClick('btnEmergencySshMockSave', () => ns.emergencyConfig?.saveSshHostMock?.());
bindClick('btnEmergencySshMockList', () => ns.emergencyConfig?.listSshHosts?.());
bindClick('btnEmergencyImportJson', () => ns.emergencyConfig?.importJsonToDb?.());
bindClick('btnEmergencyServerMockSave', () => ns.emergencyConfig?.saveServerActionMock?.());
bindClick('btnEmergencyServerMockList', () => ns.emergencyConfig?.listServerActions?.());
bindClick('btnEmergencyDbMockSave', () => ns.emergencyConfig?.saveDbActionMock?.());
bindClick('btnEmergencyDbMockList', () => ns.emergencyConfig?.listDbActions?.());
bindClick('btnEmergencyProcessMockSave', () => ns.emergencyConfig?.saveProcessActionMock?.());
bindClick('btnEmergencyProcessMockList', () => ns.emergencyConfig?.listProcessActions?.());
bindClick('btnToolTaskList', () => ns.toolbox.listTasks().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); }));
bindClick('btnToolTaskUpdate', () => ns.toolbox.updateTask().catch((e) => { $('toolTaskResult').textContent = formatError('工具任务', e); }));
bindClick('btnListAssets', () => ns.assets.listAssets().catch((e) => { $('assetListResult').textContent = formatError('资产列表', e); }));
bindClick('btnAssetFilterClear', () => {
  ns.assets?.clearFilters?.();
  ns.assets?.listAssets?.().catch((e) => { $('assetListResult').textContent = formatError('资产列表', e); });
});
bindClick('btnAssetExport', async () => {
  try {
    const url = `${ns.api.base()}/api/v1/admin/assets/export?${ns.assets.buildAssetQuery()}`;
    window.open(url, '_blank', 'noopener');
  } catch (e) {
    $('assetResult').textContent = formatError('资产导出', e);
  }
});
bindClick('btnFindUsers', () => ns.users.findUsers($('userSearchKeyword').value.trim()).catch((e) => {
  $('userListSummary').textContent = formatError('用户查询', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';
}));
bindClick('btnFindSystems', () => ns.systems.findSystems($('systemSearchKeyword2').value.trim()).catch((e) => {
  $('systemListSummary').textContent = formatError('系统查询', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="9">查询失败</td></tr>';
}));
bindClick('btnLoadRules', () => ns.rulesAudit.loadRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); }));
bindClick('btnSaveRules', () => ns.rulesAudit.saveRules().catch((e) => { $('ruleResult').textContent = formatError('规则配置', e); }));
bindClick('btnAudit', () => ns.rulesAudit.loadAudit().catch((e) => { $('audit').textContent = formatError('审计日志', e); }));
bindClick('btnAuditClear', () => {
  ['auditAction', 'auditUsername', 'auditResource', 'auditStartAt', 'auditEndAt', 'auditKeyword'].forEach((id) => {
    const el = $(id);
    if (el) el.value = '';
  });
  $('audit').textContent = '';
});
bindClick('btnCreateTemplate', () => ns.templates.createTemplate().catch((e) => { $('templateCreateResult').textContent = formatError('创建模板', e); }));
bindClick('btnListTemplates', () => ns.templates.listTemplates().catch((e) => { $('templateListResult').textContent = formatError('模板列表', e); }));
bindClick('btnCreateSnapshot', () => ns.templates.createSnapshot().catch((e) => { $('snapshotResult').textContent = formatError('状态快照', e); }));

bindClick('btnOpenCreateUserModal', () => ns.modals.openModal('createUserModal'));
bindClick('btnCloseCreateUserModal', () => ns.modals.closeModal('createUserModal'));
bindClick('btnOpenCreateSystemModal', () => ns.modals.openCreateSystemModal());
bindClick('btnCloseCreateSystemModal', () => ns.modals.closeModal('createSystemModal'));
bindClick('btnTestSystemHost', () => ns.modals.testSystemHost().catch((e) => {
  const el = $('systemHostTestResult');
  if (el) el.textContent = `检测失败：${e.message}`;
}));
bindClick('btnOpenSystemOwnerPicker', () => ns.modals.openSystemOwnerPicker().catch((e) => {
  const el = $('modalSystemOwnerSummary');
  if (el) el.textContent = `用户列表读取失败：${e.message}`;
}));
bindClick('btnSearchSystemOwners', () => ns.modals.renderSystemOwnerPicker($('systemOwnerSearchKeyword')?.value || ''));
bindClick('btnConfirmSystemOwners', () => ns.modals.confirmSystemOwners());
bindClick('btnCloseSystemOwnerPicker', () => ns.modals.closeModal('systemOwnerPickerModal'));
bindClick('btnOpenCreateAssetModal', () => ns.modals.openCreateAssetModal());
bindClick('btnCloseCreateAssetModal', () => ns.modals.closeModal('createAssetModal'));
bindClick('btnOpenAssetImportModal', () => ns.modals.openModal('assetImportModal'));
bindClick('btnCloseAssetImportModal', () => ns.modals.closeModal('assetImportModal'));
bindClick('btnSubmitCreateUser', () => ns.modals.submitCreateUser().catch((e) => {
  $('userListSummary').textContent = formatError('创建用户', e);
  $('userListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';
}));
bindClick('btnSubmitCreateSystem', () => ns.modals.submitCreateSystem().catch((e) => {
  $('systemListSummary').textContent = formatError('系统操作', e);
  $('systemListTbody').innerHTML = '<tr><td colspan="9">操作失败</td></tr>';
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
  const refreshHost = document.getElementById('controlStripRefresh');
  if (refreshHost) refreshHost.textContent = ns.state.autoRefreshEnabled ? '自动刷新' : '手动刷新';
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

Array.from(document.querySelectorAll('[data-jump-view]')).forEach((btn) => {
  btn.addEventListener('click', () => {
    const viewId = btn.dataset.jumpView;
    const group = VIEW_GROUP_MAP[viewId] || ns.state.activeGroup;
    if (viewId) switchView(viewId, group);
  });
});

Array.from(document.querySelectorAll('.ops-tab')).forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.ops-tab').forEach((tab) => tab.classList.remove('active'));
    btn.classList.add('active');
    const viewId = btn.dataset.targetView;
    const group = VIEW_GROUP_MAP[viewId] || 'ops-workbench';
    if (viewId) switchView(viewId, group);
  });
});

function safeBoot(task, onError) {
  try {
    const result = task?.();
    if (result && typeof result.catch === 'function') result.catch(onError || (() => {}));
  } catch (e) {
    (onError || console.error)(e);
  }
}

ns.api.renderHistory();
safeBoot(() => ns.debug?.syncDebugMeta?.(), console.error);
safeBoot(async () => {
  const me = await ns.auth.restoreSession();
  if (!me) return;

  const stateEl = $('state');
  if (stateEl) stateEl.textContent = `已恢复登录：${me.username || 'admin'}`;
  ns.debug?.syncDebugMeta?.();
  openGroup('dashboard');
  switchView('view-dashboard-overview', 'dashboard');
  Promise.allSettled([
    ns.sharedData?.hydrateAdminSelectors?.(),
    ns.dashboard?.refreshDashboard?.(),
  ]);
}, console.error);
