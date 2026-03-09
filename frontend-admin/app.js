const $ = (id) => document.getElementById(id);
let token = '';

const REQ_HISTORY_KEY = 'aegis_admin_request_history';
const TOOL_TAB_KEY = 'aegis_admin_tool_tab';
let dashboardTimer = null;
let autoRefreshEnabled = true;
const trendSeries = { cpu: [], mem: [], disk: [] };
let latestMonitoringItems = [];
let selectedSystemCode = 'HOST-LOCAL-001';

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

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function statusChip(color) {
  const v = String(color || 'unknown').toLowerCase();
  const cls = ['green', 'yellow', 'red'].includes(v) ? v : 'unknown';
  return `<span class="status-chip ${cls}">${escapeHtml(v)}</span>`;
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

function drawSparkline(canvasId, values, stroke = '#38bdf8') {
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
  drawSparkline('sparkCpu', trendSeries.cpu, '#38bdf8');
  drawSparkline('sparkMem', trendSeries.mem, '#2dd4bf');
  drawSparkline('sparkDisk', trendSeries.disk, '#7dd3fc');
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
      <td>${escapeHtml(i.system_id ?? '-')}</td>
      <td>${escapeHtml(i.system_code || '-')} / ${escapeHtml(i.system_name || '-')}</td>
      <td>${escapeHtml(i.env || '-')}</td>
      <td>${statusChip(i.status_color)}</td>
      <td>${escapeHtml(i.cpu_usage ?? '-')}% (${statusChip(i.cpu_level || 'unknown')})</td>
      <td>${escapeHtml(i.mem_usage ?? '-')}% (${statusChip(i.mem_level || 'unknown')})</td>
      <td>${escapeHtml(i.disk_usage ?? '-')}% (${statusChip(i.disk_level || 'unknown')})</td>
      <td>${escapeHtml(i.captured_at || '-')}</td>
    </tr>
  `).join('');
  $('abnormalTbody').innerHTML = rows || '<tr><td colspan="8">暂无符合筛选条件的数据</td></tr>';
}

function renderSelectedSystem(items) {
  if (!items.length) {
    setNumber($('kpiGreen'), 0);
    setNumber($('kpiYellow'), 0);
    setNumber($('kpiRed'), 0);
    setNumber($('kpiTotal'), 0);
    setTechMetric('metricCpu', 0);
    setTechMetric('metricMem', 0);
    setTechMetric('metricDisk', 0);
    return;
  }

  let selected = items.find((i) => i.system_code === selectedSystemCode);
  if (!selected) {
    selected = items.find((i) => i.system_code === 'HOST-LOCAL-001') || items[0];
    selectedSystemCode = selected.system_code;
  }

  const color = String(selected.status_color || '').toLowerCase();
  setNumber($('kpiGreen'), color === 'green' ? 1 : 0);
  setNumber($('kpiYellow'), color === 'yellow' ? 1 : 0);
  setNumber($('kpiRed'), color === 'red' ? 1 : 0);
  setNumber($('kpiTotal'), 1);

  setTechMetric('metricCpu', Number(selected.cpu_usage) || 0);
  setTechMetric('metricMem', Number(selected.mem_usage) || 0);
  setTechMetric('metricDisk', Number(selected.disk_usage) || 0);
}

function refreshSystemOptions() {
  const select = $('systemSelect');
  if (!select) return;

  const keyword = ($('systemSearchKeyword')?.value || '').trim().toLowerCase();
  const candidates = latestMonitoringItems.filter((i) => {
    if (!keyword) return true;
    const text = `${i.system_code || ''} ${i.system_name || ''}`.toLowerCase();
    return text.includes(keyword);
  });

  select.innerHTML = candidates
    .map((i) => `<option value="${escapeHtml(i.system_code)}">${escapeHtml(i.system_code)} / ${escapeHtml(i.system_name || '-')}</option>`)
    .join('');

  if (!candidates.length) return;
  if (!candidates.some((i) => i.system_code === selectedSystemCode)) {
    selectedSystemCode = candidates[0].system_code;
  }
  select.value = selectedSystemCode;
}

function applySystemSearch() {
  refreshSystemOptions();
  renderSelectedSystem(latestMonitoringItems);
  const selected = latestMonitoringItems.find((i) => i.system_code === selectedSystemCode);
  pushTrend('cpu', Number(selected?.cpu_usage) || 0);
  pushTrend('mem', Number(selected?.mem_usage) || 0);
  pushTrend('disk', Number(selected?.disk_usage) || 0);
  renderSparklines();
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

function formatSuccess(moduleName, message, data = null) {
  const base = `【${moduleName}】${message}`;
  return data ? `${base}\n${JSON.stringify(data, null, 2)}` : base;
}

function renderUserResultBoard(items, message = '') {
  const rows = (items || []).map((u, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td>${escapeHtml(u.username || '-')}</td>
      <td>${u.role_code === 'super_admin' ? '超级管理员' : u.role_code === 'admin' ? '管理员' : '巡检员'}</td>
      <td>${escapeHtml(u.id ?? '-')}</td>
    </tr>
  `).join('');
  $('userListSummary').textContent = message || `匹配 ${items.length} 条`;
  $('userListTbody').innerHTML = rows || '<tr><td colspan="4">暂无匹配用户</td></tr>';
}

function renderSystemResultBoard(items, message = '') {
  const rows = (items || []).map((s, idx) => `
    <tr>
      <td>${idx + 1}</td>
      <td>${escapeHtml(s.system_code || '-')}</td>
      <td>${escapeHtml(s.name || '-')}</td>
      <td>${escapeHtml(s.env === 'prod' ? '生产' : s.env === 'test' ? '测试' : s.env === 'dev' ? '开发' : (s.env || '-'))}</td>
    </tr>
  `).join('');
  $('systemListSummary').textContent = message || `匹配 ${items.length} 条`;
  $('systemListTbody').innerHTML = rows || '<tr><td colspan="4">暂无匹配系统</td></tr>';
}

function forceRelogin(message = '登录已失效，请重新登录') {
  token = '';
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
  const items = data.items || [];
  

  latestMonitoringItems = items;
  refreshSystemOptions();
  renderSelectedSystem(items);

  const selected = items.find((i) => i.system_code === selectedSystemCode);
  const cpu = Number(selected?.cpu_usage) || 0;
  const mem = Number(selected?.mem_usage) || 0;
  const disk = Number(selected?.disk_usage) || 0;

  pushTrend('cpu', cpu);
  pushTrend('mem', mem);
  pushTrend('disk', disk);
  renderSparklines();

  applyAbnormalFilters();
}

function renderAssetSummary(data) {
  const byStatus = Object.fromEntries((data.by_status || []).map(i => [i.status, i.count]));
  const total = data.total ?? 0;
  const inUse = byStatus.in_use ?? 0;
  const repair = byStatus.repair ?? 0;
  const retired = byStatus.retired ?? 0;

  setNumber($('assetTotal'), total);
  setNumber($('assetInUse'), inUse);
  setNumber($('assetRepair'), repair);
  setNumber($('assetRetired'), retired);

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
  setLiveStatus(false);
}

$('btnLogin').onclick = async () => {
  try {
    const d = await request('/api/v1/auth/login', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({username:$('username').value, password:$('password').value})
    });
    token = d.access_token;
    $('state').textContent = '登录成功（刷新页面后需重新登录）';
    setAuthView(true);
    switchPanel('panel-dashboard');
    $('btnRefreshDashboard').click();
  } catch(e){ $('state').textContent = `登录失败: ${e.message}`; }
};

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
    
    setLastUpdated(false);
  }
};

$('btnCollectLocal').onclick = async () => {
  try {
    const code = 'HOST-LOCAL-001';
    await request(`/api/v1/monitoring/collect/local?system_code=${encodeURIComponent(code)}`, {
      method: 'POST',
      headers: headers(),
    });
    $('btnRefreshDashboard').click();
  } catch (e) {
    // dashboard text panel removed
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
  } catch (e) {  }
};

function openCreateUserModal() {
  $('createUserModal').classList.remove('hidden');
}

function closeCreateUserModal() {
  $('createUserModal').classList.add('hidden');
}

$('btnSubmitCreateUser').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/users', {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        username: $('modalUserName').value.trim(),
        password: $('modalUserPassword').value,
        role_code: $('modalUserRole').value,
      })
    });
    renderUserResultBoard([d], '新增成功，已创建 1 个用户');
    closeCreateUserModal();
    $('modalUserName').value = '';
    $('modalUserPassword').value = '';
  } catch(e){ $('userListSummary').textContent = formatError('创建用户', e); $('userListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';  }
};

function openCreateSystemModal() {
  $('createSystemModal').classList.remove('hidden');
}

function closeCreateSystemModal() {
  $('createSystemModal').classList.add('hidden');
}

$('btnSubmitCreateSystem').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/systems', {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        system_code: $('modalSystemCode').value.trim(),
        name: $('modalSystemName').value.trim(),
        env: $('modalSystemEnv').value || 'prod',
      })
    });
    renderSystemResultBoard([d], '新增成功，已创建 1 个系统');
    closeCreateSystemModal();
    $('modalSystemCode').value = '';
    $('modalSystemName').value = '';
  } catch(e){ $('systemListSummary').textContent = formatError('创建系统', e); $('systemListTbody').innerHTML = '<tr><td colspan="4">操作失败</td></tr>';  }
};

$('btnFindUsers').onclick = async () => {
  try {
    const keyword = $('userSearchKeyword').value.trim().toLowerCase();
    const d = await request('/api/v1/admin/users?page=1&size=200', { headers: headers() });
    const items = Array.isArray(d.items) ? d.items : [];
    const filtered = keyword
      ? items.filter((u) => String(u.username || '').toLowerCase().includes(keyword))
      : items;
    renderUserResultBoard(filtered, `匹配 ${filtered.length} 条`);
  } catch (e) { $('userListSummary').textContent = formatError('用户查询', e); $('userListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';  }
};

$('btnFindSystems').onclick = async () => {
  try {
    const keyword = $('systemSearchKeyword2').value.trim().toLowerCase();
    const d = await request('/api/v1/admin/systems?page=1&size=200', { headers: headers() });
    const items = Array.isArray(d.items) ? d.items : [];
    const filtered = keyword
      ? items.filter((s) => `${s.system_code || ''} ${s.name || ''}`.toLowerCase().includes(keyword))
      : items;
    renderSystemResultBoard(filtered, `匹配 ${filtered.length} 条`);
  } catch (e) { $('systemListSummary').textContent = formatError('系统查询', e); $('systemListTbody').innerHTML = '<tr><td colspan="4">查询失败</td></tr>';  }
};

$('btnCreateTemplate').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ system_id: Number($('tplSystemId').value), check_type: $('tplCheckType').value, name: $('tplName').value })
    });
    $('templateCreateResult').textContent = formatSuccess('创建模板', '操作成功', d);
  } catch(e){ $('templateCreateResult').textContent = formatError('创建模板', e); }
};

$('btnListTemplates').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates?page=1&size=50', { headers: headers() });
    $('templateListResult').textContent = formatSuccess('模板列表', `共 ${d.total ?? d.items?.length ?? 0} 条`, d);
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
    $('snapshotResult').textContent = formatSuccess('状态快照', '提交成功', d);
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
    $('assetResult').textContent = formatSuccess('资产操作', '操作成功', d);
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
    $('assetListResult').textContent = formatSuccess('资产列表', `共 ${d.total ?? d.items?.length ?? 0} 条`, d);
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
    $('assetResult').textContent = formatSuccess('资产操作', '操作成功', d);
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
    $('ruleResult').textContent = formatSuccess('规则配置', '保存成功', { ...d, payload });
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
    $('toolTaskResult').textContent = formatSuccess('工具任务', '操作成功', d);
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
    $('toolTaskResult').textContent = formatSuccess('工具任务', '操作成功', d);
  } catch (e) { $('toolTaskResult').textContent = formatError('工具任务', e); }
};

$('btnDiagList').onclick = async () => {
  try {
    const s = $('diagSeverityFilter').value.trim();
    const q = s ? `?page=1&size=20&severity=${encodeURIComponent(s)}` : '?page=1&size=20';
    const d = await request(`/api/v1/ai/diagnoses${q}`, { headers: headers() });
    $('diagListResult').textContent = formatSuccess('AI诊断记录', `共 ${d.total ?? d.items?.length ?? 0} 条`, d);
  } catch (e) { $('diagListResult').textContent = formatError('AI诊断记录', e); }
};

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

function initDashboardBindings() {
  $('btnToggleAutoRefresh').onclick = () => {
    autoRefreshEnabled = !autoRefreshEnabled;
    if (autoRefreshEnabled) startDashboardAutoRefresh();
    else stopDashboardAutoRefresh();
    setLiveStatus(autoRefreshEnabled && Boolean(dashboardTimer));
  };

  $('abnormalColorFilter').onchange = applyAbnormalFilters;
  $('abnormalKeyword').oninput = applyAbnormalFilters;

  $('btnSystemSearch').onclick = applySystemSearch;
  $('btnSystemReset').onclick = () => {
    $('systemSearchKeyword').value = '';
    refreshSystemOptions();
    applySystemSearch();
  };
  $('systemSearchKeyword').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      applySystemSearch();
    }
  });
  $('systemSelect').onchange = () => {
    selectedSystemCode = $('systemSelect').value;
    applySystemSearch();
  };
}

function initAdvancedToolsBindings() {
  $('btnRefreshHistory').onclick = () => renderHistory();
  $('btnClearHistory').onclick = () => { localStorage.removeItem(REQ_HISTORY_KEY); renderHistory(); };

  Array.from(document.querySelectorAll('.tool-tab')).forEach((btn) => {
    btn.addEventListener('click', () => activateToolTab(btn.dataset.tool));
  });
}

function initGlobalBindings() {
  Array.from(document.querySelectorAll('.menu-btn')).forEach((btn) => {
    btn.addEventListener('click', () => switchPanel(btn.dataset.section));
  });

  $('btnOpenCreateUserModal').onclick = openCreateUserModal;
  $('btnCloseCreateUserModal').onclick = closeCreateUserModal;
  $('btnOpenCreateSystemModal').onclick = openCreateSystemModal;
  $('btnCloseCreateSystemModal').onclick = closeCreateSystemModal;

  $('btnLogout').onclick = () => {
    token = '';
    $('state').textContent = '已退出登录';
    stopDashboardAutoRefresh();
    setAuthView(false);
  };
}

function initUiBindings() {
  initDashboardBindings();
  initAdvancedToolsBindings();
  initGlobalBindings();
}

function initViewState() {
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
}

initUiBindings();
initViewState();
