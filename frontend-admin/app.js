const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('aegis_admin_token') || '';

const REQ_HISTORY_KEY = 'aegis_admin_request_history';
const TOOL_TAB_KEY = 'aegis_admin_tool_tab';
let dashboardTimer = null;
let autoRefreshEnabled = true;
const trendSeries = { cpu: [], mem: [], disk: [] };
let latestMonitoringItems = [];

function base() {
  const protocol = window.location.protocol && window.location.protocol.startsWith('http')
    ? window.location.protocol
    : 'http:';
  const host = window.location.hostname || '127.0.0.1';
  return `${protocol}//${host}:8000`;
}
function headers(){ const h = {'Content-Type':'application/json'}; if(token) h.Authorization = `Bearer ${token}`; return h; }

function setAuthView(isLoggedIn) {
  $('loginView').classList.toggle('hidden', isLoggedIn);
  $('appView').classList.toggle('hidden', !isLoggedIn);
}

function switchPanel(sectionId) {
  document.querySelectorAll('.panel').forEach((panel) => panel.classList.remove('active'));
  document.querySelectorAll('.menu-btn').forEach((btn) => btn.classList.remove('active'));
  document.getElementById(sectionId)?.classList.add('active');
  document.querySelector(`.menu-btn[data-section="${sectionId}"]`)?.classList.add('active');

  if (sectionId === 'panel-dashboard' && token) {
    startDashboardAutoRefresh();
  } else {
    stopDashboardAutoRefresh();
  }
}

function setNumber(el, target) {
  if (!el) return;
  const end = Number(target) || 0;
  el.textContent = String(end);
  el.dataset.value = String(end);
}

function setTechMetric(prefix, value) {
  const safe = Math.max(0, Math.min(100, Number(value) || 0));
  const textEl = $(`${prefix}Text`);
  const barEl = $(`${prefix}Bar`);
  if (textEl) textEl.textContent = `${safe.toFixed(0)}%`;
  if (barEl) {
    barEl.style.width = `${safe}%`;
    barEl.style.filter = safe >= 85 ? 'hue-rotate(-35deg) saturate(1.2)' : 'none';
  }
}

function statusChip(color) {
  const v = String(color || 'unknown').toLowerCase();
  const cls = ['green', 'yellow', 'red'].includes(v) ? v : 'unknown';
  return `<span class="status-chip ${cls}">${v}</span>`;
}

function setLastUpdated(ok = true) {
  const ts = new Date().toLocaleTimeString('zh-CN', { hour12: false });
  if ($('lastUpdated')) $('lastUpdated').textContent = `最近更新：${ts}${ok ? '' : '（失败）'}`;
}

function setLiveStatus(on) {
  const el = $('liveStatus');
  if (!el) return;
  el.classList.toggle('on', on);
  el.classList.toggle('off', !on);
  el.textContent = on ? '● 自动刷新开启' : '● 手动刷新模式';
  if ($('btnToggleAutoRefresh')) $('btnToggleAutoRefresh').textContent = on ? '切换手动刷新' : '切换自动刷新';
}

function pushTrend(key, value) {
  const arr = trendSeries[key];
  if (!arr) return;
  arr.push(Math.max(0, Math.min(100, Number(value) || 0)));
  if (arr.length > 24) arr.shift();
}

function drawSparkline(canvasId, values, stroke = '#c48a42') {
  const canvas = $(canvasId);
  if (!canvas || !canvas.getContext) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (!values.length) return;

  ctx.strokeStyle = stroke;
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = (i / Math.max(values.length - 1, 1)) * (w - 6) + 3;
    const y = h - 4 - (v / 100) * (h - 8);
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();
}

function renderSparklines() {
  drawSparkline('sparkCpu', trendSeries.cpu, '#c48a42');
  drawSparkline('sparkMem', trendSeries.mem, '#b97736');
  drawSparkline('sparkDisk', trendSeries.disk, '#a8642d');
}

function applyAbnormalFilters() {
  const colorFilter = $('abnormalColorFilter')?.value || 'all';
  const keyword = ($('abnormalKeyword')?.value || '').trim().toLowerCase();
  const allowed = colorFilter === 'all' ? null : colorFilter.split(',');

  const filtered = latestMonitoringItems.filter((i) => {
    const color = String(i.status_color || '').toLowerCase();
    if (allowed && !allowed.includes(color)) return false;
    if (keyword) {
      const text = `${i.system_code || ''} ${i.system_name || ''}`.toLowerCase();
      if (!text.includes(keyword)) return false;
    }
    return true;
  });

  const rows = filtered.map(i => `
    <tr>
      <td>${i.system_id}</td>
      <td>${i.system_code} / ${i.system_name}</td>
      <td>${i.env}</td>
      <td>${statusChip(i.status_color)}</td>
      <td>${i.cpu_usage ?? '-'}% (${statusChip(i.cpu_level || 'unknown')})</td>
      <td>${i.mem_usage ?? '-'}% (${statusChip(i.mem_level || 'unknown')})</td>
      <td>${i.disk_usage ?? '-'}% (${statusChip(i.disk_level || 'unknown')})</td>
      <td>${i.captured_at || '-'}</td>
    </tr>
  `).join('');
  $('abnormalTbody').innerHTML = rows || '<tr><td colspan="8">暂无符合筛选条件的数据</td></tr>';
}

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
  $('requestHistory').textContent = JSON.stringify(getHistory(), null, 2);
}

function formatError(moduleName, e) {
  const msg = e?.message || String(e) || '未知错误';
  return `【${moduleName}】请求失败\n原因：${msg}\n建议：请检查登录状态或稍后重试。`;
}

function forceRelogin(message = '登录已失效，请重新登录') {
  token = '';
  localStorage.removeItem('aegis_admin_token');
  $('state').textContent = message;
  stopDashboardAutoRefresh();
  setAuthView(false);
}

async function request(path, options={}){
  const startedAt = new Date().toISOString();
  const method = options.method || 'GET';
  const resp = await fetch(`${base()}${path}`, options);
  const data = await resp.json().catch(()=>({}));

  if (!resp.ok) {
    const code = data?.code;
    const msg = data?.message || `HTTP ${resp.status}`;
    pushHistory({ startedAt, method, path, ok: false, status: resp.status, code: code || null, message: msg });
    renderHistory();

    if (code === 'TOKEN_EXPIRED' || code === 'TOKEN_INVALID' || code === 'USER_DISABLED' || code === 'USER_NOT_FOUND') {
      forceRelogin(`${msg}（请重新登录）`);
    }
    throw new Error(`${code ? `[${code}] ` : ''}${msg}`);
  }

  pushHistory({ startedAt, method, path, ok: true, status: resp.status, code: null, message: 'OK' });
  renderHistory();
  return data;
}

function renderMonitoring(data){
  setNumber($('kpiGreen'), data.summary?.green ?? 0);
  setNumber($('kpiYellow'), data.summary?.yellow ?? 0);
  setNumber($('kpiRed'), data.summary?.red ?? 0);
  setNumber($('kpiTotal'), data.summary?.total ?? 0);
  $('monitoring').textContent = JSON.stringify(data.summary, null, 2);

  const items = data.items || [];
  const avg = (key) => {
    const vals = items.map((i) => Number(i?.[key])).filter((v) => Number.isFinite(v));
    if (!vals.length) return 0;
    return vals.reduce((a, b) => a + b, 0) / vals.length;
  };
  const cpuAvg = avg('cpu_usage');
  const memAvg = avg('mem_usage');
  const diskAvg = avg('disk_usage');
  setTechMetric('metricCpu', cpuAvg);
  setTechMetric('metricMem', memAvg);
  setTechMetric('metricDisk', diskAvg);

  pushTrend('cpu', cpuAvg);
  pushTrend('mem', memAvg);
  pushTrend('disk', diskAvg);
  renderSparklines();

  latestMonitoringItems = items;
  applyAbnormalFilters();
}

function renderAssetSummary(data) {
  const byStatus = Object.fromEntries((data.by_status || []).map(i => [i.status, i.count]));
  setNumber($('assetTotal'), data.total ?? 0);
  setNumber($('assetInUse'), byStatus.in_use ?? 0);
  setNumber($('assetRepair'), byStatus.repair ?? 0);
  setNumber($('assetRetired'), byStatus.retired ?? 0);
  $('assetSummary').textContent = JSON.stringify(data, null, 2);
}

function startDashboardAutoRefresh() {
  if (!autoRefreshEnabled) {
    stopDashboardAutoRefresh();
    return;
  }
  if (dashboardTimer) return;
  setLiveStatus(true);
  dashboardTimer = setInterval(() => {
    if (!token || !autoRefreshEnabled) return;
    $('btnRefreshDashboard').click();
  }, 12000);
}

function stopDashboardAutoRefresh() {
  if (dashboardTimer) {
    clearInterval(dashboardTimer);
    dashboardTimer = null;
  }
  setLiveStatus(autoRefreshEnabled ? false : false);
}

$('btnLogin').onclick = async () => {
  try {
    const d = await request('/api/v1/auth/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:$('username').value, password:$('password').value})
    });
    token = d.access_token;
    localStorage.setItem('aegis_admin_token', token);
    $('state').textContent = '登录成功';
    setAuthView(true);
    switchPanel('panel-dashboard');
    $('btnRefreshDashboard').click();
  } catch(e){ $('state').textContent = `登录失败: ${e.message}`; }
};

const btnMonitoring = $('btnMonitoring');
if (btnMonitoring) {
  btnMonitoring.onclick = async () => {
    try { renderMonitoring(await request('/api/v1/monitoring/overview',{headers:headers()})); }
    catch(e){ $('monitoring').textContent = formatError('监控总览', e); }
  };
}

const btnAssetSummary = $('btnAssetSummary');
if (btnAssetSummary) {
  btnAssetSummary.onclick = async () => {
    try { renderAssetSummary(await request('/api/v1/admin/assets/summary', { headers: headers() })); }
    catch(e){ $('assetSummary').textContent = formatError('资产概览', e); }
  };
}

$('btnRefreshDashboard').onclick = async () => {
  try {
    const [monitoring, assets] = await Promise.all([
      request('/api/v1/monitoring/overview', { headers: headers() }),
      request('/api/v1/admin/assets/summary', { headers: headers() }),
    ]);
    renderMonitoring(monitoring);
    renderAssetSummary(assets);
    setLastUpdated(true);
  } catch (e) {
    $('monitoring').textContent = formatError('看板刷新', e);
    setLastUpdated(false);
  }
};

$('btnCollectLocal').onclick = async () => {
  try {
    const code = $('localSystemCode').value.trim() || 'HOST-LOCAL-001';
    const d = await request(`/api/v1/monitoring/collect/local?system_code=${encodeURIComponent(code)}`, {
      method: 'POST',
      headers: headers(),
    });
    $('monitoring').textContent = `本机采集成功:\n${JSON.stringify(d, null, 2)}`;
    $('btnRefreshDashboard').click();
  } catch (e) {
    $('monitoring').textContent = formatError('本机采集', e);
  }
};

$('btnExportAbnormal').onclick = async () => {
  const startedAt = new Date().toISOString();
  try {
    const resp = await fetch(`${base()}/api/v1/monitoring/abnormal/export`, { headers: { Authorization: `Bearer ${token}` } });
    if (!resp.ok) {
      const d = await resp.json().catch(()=>({}));
      const code = d?.code;
      const msg = d?.message || `HTTP ${resp.status}`;
      pushHistory({ startedAt, method: 'GET', path: '/api/v1/monitoring/abnormal/export', ok: false, status: resp.status, code: code || null, message: msg });
      renderHistory();
      if (code === 'TOKEN_EXPIRED' || code === 'TOKEN_INVALID' || code === 'USER_DISABLED' || code === 'USER_NOT_FOUND') {
        forceRelogin(`${msg}（请重新登录）`);
      }
      throw new Error(`${code ? `[${code}] ` : ''}${msg}`);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'monitoring_abnormal.csv';
    a.click();
    URL.revokeObjectURL(url);
    pushHistory({ startedAt, method: 'GET', path: '/api/v1/monitoring/abnormal/export', ok: true, status: resp.status, code: null, message: 'CSV downloaded' });
    renderHistory();
  } catch (e) { $('monitoring').textContent = formatError('异常导出', e); }
};

$('btnCreateUser').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/users', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ username: $('newUserName').value, password: $('newUserPassword').value, role_code: $('newUserRole').value })
    });
    $('userCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('userCreateResult').textContent = formatError('创建用户', e); }
};

$('btnCreateSystem').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/systems', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ system_code: $('newSystemCode').value, name: $('newSystemName').value, env: $('newSystemEnv').value || 'prod' })
    });
    $('systemCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('systemCreateResult').textContent = formatError('创建系统', e); }
};

$('btnListUsers').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/users?page=1&size=50', { headers: headers() });
    $('userListResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('userListResult').textContent = formatError('用户列表', e); }
};

$('btnListSystems').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/systems?page=1&size=50', { headers: headers() });
    $('systemListResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('systemListResult').textContent = formatError('系统列表', e); }
};

$('btnCreateTemplate').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ system_id: Number($('tplSystemId').value), check_type: $('tplCheckType').value, name: $('tplName').value })
    });
    $('templateCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('templateCreateResult').textContent = formatError('创建模板', e); }
};

$('btnListTemplates').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates?page=1&size=50', { headers: headers() });
    $('templateListResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('templateListResult').textContent = formatError('模板列表', e); }
};

$('btnCreateSnapshot').onclick = async () => {
  try {
    const sid = Number($('snapSystemId').value);
    const d = await request(`/api/v1/systems/${sid}/status/snapshot`, {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        host_online: $('snapHostOnline').value || 'unknown',
        port_ok: $('snapPortOk').value || 'unknown',
        cpu_usage: Number($('snapCpu').value),
        mem_usage: Number($('snapMem').value),
        disk_usage: Number($('snapDisk').value),
        last_inspection_result: 'normal',
        last_selfcheck_result: $('snapSelfcheck').value || 'unknown'
      })
    });
    $('snapshotResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('snapshotResult').textContent = formatError('状态快照', e); }
};

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
    const d = await request('/api/v1/admin/assets', { method: 'POST', headers: headers(), body: JSON.stringify(payload) });
    $('assetResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('assetResult').textContent = formatError('资产操作', e); }
};

function buildAssetQuery() {
  const params = new URLSearchParams({ page: '1', size: '50' });
  const systemId = $('assetFilterSystemId').value.trim();
  const category = $('assetFilterCategory').value.trim();
  const status = $('assetFilterStatus').value.trim();
  const keyword = $('assetFilterKeyword').value.trim();

  if (systemId) params.set('system_id', systemId);
  if (category) params.set('category', category);
  if (status) params.set('status', status);
  if (keyword) params.set('keyword', keyword);
  return params.toString();
}

$('btnListAssets').onclick = async () => {
  try {
    const d = await request(`/api/v1/admin/assets?${buildAssetQuery()}`, { headers: headers() });
    $('assetListResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('assetListResult').textContent = formatError('资产列表', e); }
};

$('btnAssetExport').onclick = async () => {
  const startedAt = new Date().toISOString();
  const path = `/api/v1/admin/assets/export?${buildAssetQuery()}`;
  try {
    const resp = await fetch(`${base()}${path}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!resp.ok) {
      const d = await resp.json().catch(()=>({}));
      const code = d?.code;
      const msg = d?.message || `HTTP ${resp.status}`;
      pushHistory({ startedAt, method: 'GET', path, ok: false, status: resp.status, code: code || null, message: msg });
      renderHistory();
      throw new Error(`${code ? `[${code}] ` : ''}${msg}`);
    }
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'assets.csv';
    a.click();
    URL.revokeObjectURL(url);
    pushHistory({ startedAt, method: 'GET', path, ok: true, status: resp.status, code: null, message: 'CSV downloaded' });
    renderHistory();
  } catch (e) {
    $('assetResult').textContent = formatError('资产导出', e);
  }
};

$('btnAssetFilterClear').onclick = () => {
  ['assetFilterSystemId', 'assetFilterCategory', 'assetFilterStatus', 'assetFilterKeyword'].forEach((id) => $(id).value = '');
  $('assetResult').textContent = '已清空资产筛选条件';
};

$('btnBatchAssets').onclick = async () => {
  try {
    const items = JSON.parse($('assetBatchJson').value);
    const d = await request('/api/v1/admin/assets/batch', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({ items }),
    });
    $('assetResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('assetResult').textContent = formatError('资产批量导入', e); }
};

$('btnLoadRules').onclick = async () => {
  try {
    const r = await request('/api/v1/monitoring/rules', { headers: headers() });
    $('cpuWarn').value = r.cpu_warn; $('cpuCritical').value = r.cpu_critical;
    $('memWarn').value = r.mem_warn; $('memCritical').value = r.mem_critical;
    $('diskWarn').value = r.disk_warn; $('diskCritical').value = r.disk_critical;
    $('ruleResult').textContent = JSON.stringify(r, null, 2);
  } catch (e) { $('ruleResult').textContent = formatError('规则配置', e); }
};

$('btnSaveRules').onclick = async () => {
  try {
    const payload = {
      cpu_warn: Number($('cpuWarn').value), cpu_critical: Number($('cpuCritical').value),
      mem_warn: Number($('memWarn').value), mem_critical: Number($('memCritical').value),
      disk_warn: Number($('diskWarn').value), disk_critical: Number($('diskCritical').value),
    };
    const d = await request('/api/v1/monitoring/rules', { method: 'PUT', headers: headers(), body: JSON.stringify(payload) });
    $('ruleResult').textContent = JSON.stringify({ ...d, payload }, null, 2);
  } catch (e) { $('ruleResult').textContent = formatError('规则配置', e); }
};

function buildAuditQuery() {
  const params = new URLSearchParams({ page: '1', size: '20' });
  const action = $('auditAction').value.trim();
  const username = $('auditUsername').value.trim();
  const resource = $('auditResource').value.trim();
  const startAt = $('auditStartAt').value.trim();
  const endAt = $('auditEndAt').value.trim();
  const keyword = $('auditKeyword').value.trim();

  if (action) params.set('action', action);
  if (username) params.set('username', username);
  if (resource) params.set('resource', resource);
  if (startAt) params.set('start_at', startAt);
  if (endAt) params.set('end_at', endAt);
  if (keyword) params.set('keyword', keyword);

  return params.toString();
}

$('btnAudit').onclick = async () => {
  try {
    const qs = buildAuditQuery();
    const data = await request(`/api/v1/admin/audit-logs?${qs}`, {headers:headers()});
    $('audit').textContent = JSON.stringify(data, null, 2);
  } catch(e){ $('audit').textContent = formatError('审计日志', e); }
};

$('btnAuditClear').onclick = () => {
  ['auditAction','auditUsername','auditResource','auditStartAt','auditEndAt','auditKeyword'].forEach(id => $(id).value = '');
  $('audit').textContent = '已清空筛选条件';
};

$('btnToolTaskList').onclick = async () => {
  try {
    const s = $('toolTaskStatusFilter').value.trim();
    const q = s ? `?page=1&size=50&status=${encodeURIComponent(s)}` : '?page=1&size=50';
    const d = await request(`/api/v1/toolbox/tasks${q}`, { headers: headers() });
    $('toolTaskResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('toolTaskResult').textContent = formatError('工具任务', e); }
};

$('btnToolTaskUpdate').onclick = async () => {
  try {
    const taskId = Number($('toolTaskId').value);
    const d = await request(`/api/v1/toolbox/tasks/${taskId}/status`, {
      method: 'PUT',
      headers: headers(),
      body: JSON.stringify({ status: $('toolTaskActionStatus').value, note: $('toolTaskNote').value || null }),
    });
    $('toolTaskResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('toolTaskResult').textContent = formatError('工具任务', e); }
};

$('btnDiagList').onclick = async () => {
  try {
    const s = $('diagSeverityFilter').value.trim();
    const q = s ? `?page=1&size=20&severity=${encodeURIComponent(s)}` : '?page=1&size=20';
    const d = await request(`/api/v1/ai/diagnoses${q}`, { headers: headers() });
    $('diagListResult').textContent = JSON.stringify(d, null, 2);
  } catch (e) { $('diagListResult').textContent = formatError('AI诊断记录', e); }
};

$('btnRefreshHistory').onclick = () => renderHistory();
$('btnClearHistory').onclick = () => { localStorage.removeItem(REQ_HISTORY_KEY); renderHistory(); };
$('btnToggleAutoRefresh').onclick = () => {
  autoRefreshEnabled = !autoRefreshEnabled;
  if (autoRefreshEnabled) startDashboardAutoRefresh();
  else stopDashboardAutoRefresh();
  setLiveStatus(autoRefreshEnabled && Boolean(dashboardTimer));
};

$('abnormalColorFilter').onchange = applyAbnormalFilters;
$('abnormalKeyword').oninput = applyAbnormalFilters;

function activateToolTab(toolId) {
  const targetBtn = document.querySelector(`.tool-tab[data-tool="${toolId}"]`) || document.querySelector('.tool-tab');
  if (!targetBtn) return;
  document.querySelectorAll('.tool-tab').forEach((b) => b.classList.remove('active'));
  document.querySelectorAll('.tool-pane').forEach((p) => p.classList.remove('active'));
  targetBtn.classList.add('active');
  document.getElementById(targetBtn.dataset.tool)?.classList.add('active');
  localStorage.setItem(TOOL_TAB_KEY, targetBtn.dataset.tool);
  if ($('toolHint')) $('toolHint').textContent = targetBtn.dataset.desc || '';
}

Array.from(document.querySelectorAll('.tool-tab')).forEach((btn) => {
  btn.addEventListener('click', () => activateToolTab(btn.dataset.tool));
});

Array.from(document.querySelectorAll('.menu-btn')).forEach((btn) => {
  btn.addEventListener('click', () => switchPanel(btn.dataset.section));
});

$('btnLogout').onclick = () => {
  token = '';
  localStorage.removeItem('aegis_admin_token');
  $('state').textContent = '已退出登录';
  stopDashboardAutoRefresh();
  setAuthView(false);
};

activateToolTab(localStorage.getItem(TOOL_TAB_KEY) || 'tool-ops');

if (token) {
  setAuthView(true);
  switchPanel('panel-dashboard');
  $('btnRefreshDashboard').click();
} else {
  stopDashboardAutoRefresh();
  setAuthView(false);
  $('state').textContent = '未登录';
}
renderHistory();
