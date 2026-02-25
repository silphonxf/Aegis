const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('aegis_admin_token') || '';

const REQ_HISTORY_KEY = 'aegis_admin_request_history';

function base(){ return $('apiBase').value.trim().replace(/\/$/, ''); }
function headers(){ const h = {'Content-Type':'application/json'}; if(token) h.Authorization = `Bearer ${token}`; return h; }

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

function forceRelogin(message = '登录已失效，请重新登录') {
  token = '';
  localStorage.removeItem('aegis_admin_token');
  $('state').textContent = message;
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
  $('kpiGreen').textContent = data.summary?.green ?? 0;
  $('kpiYellow').textContent = data.summary?.yellow ?? 0;
  $('kpiRed').textContent = data.summary?.red ?? 0;
  $('kpiTotal').textContent = data.summary?.total ?? 0;
  $('monitoring').textContent = JSON.stringify(data.summary, null, 2);

  const rows = (data.abnormal_items || []).map(i => `
    <tr>
      <td>${i.system_id}</td>
      <td>${i.system_code} / ${i.system_name}</td>
      <td>${i.env}</td>
      <td>${i.status_color}</td>
      <td>${i.cpu_level}</td>
      <td>${i.mem_level}</td>
      <td>${i.disk_level}</td>
    </tr>
  `).join('');
  $('abnormalTbody').innerHTML = rows || '<tr><td colspan="7">暂无异常系统</td></tr>';
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
  } catch(e){ $('state').textContent = `登录失败: ${e.message}`; }
};

$('btnMonitoring').onclick = async () => {
  try { renderMonitoring(await request('/api/v1/monitoring/overview',{headers:headers()})); }
  catch(e){ $('monitoring').textContent = e.message; }
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
  } catch (e) { $('monitoring').textContent = `导出失败: ${e.message}`; }
};

$('btnCreateUser').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/users', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ username: $('newUserName').value, password: $('newUserPassword').value, role_code: $('newUserRole').value })
    });
    $('userCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('userCreateResult').textContent = e.message; }
};

$('btnCreateSystem').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/systems', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ system_code: $('newSystemCode').value, name: $('newSystemName').value, env: $('newSystemEnv').value || 'prod' })
    });
    $('systemCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('systemCreateResult').textContent = e.message; }
};

$('btnCreateTemplate').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates', {
      method:'POST', headers:headers(),
      body: JSON.stringify({ system_id: Number($('tplSystemId').value), check_type: $('tplCheckType').value, name: $('tplName').value })
    });
    $('templateCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('templateCreateResult').textContent = e.message; }
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
  } catch (e) { $('snapshotResult').textContent = e.message; }
};

$('btnLoadRules').onclick = async () => {
  try {
    const r = await request('/api/v1/monitoring/rules', { headers: headers() });
    $('cpuWarn').value = r.cpu_warn; $('cpuCritical').value = r.cpu_critical;
    $('memWarn').value = r.mem_warn; $('memCritical').value = r.mem_critical;
    $('diskWarn').value = r.disk_warn; $('diskCritical').value = r.disk_critical;
    $('ruleResult').textContent = JSON.stringify(r, null, 2);
  } catch (e) { $('ruleResult').textContent = e.message; }
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
  } catch (e) { $('ruleResult').textContent = e.message; }
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
  } catch(e){ $('audit').textContent = e.message; }
};

$('btnAuditClear').onclick = () => {
  ['auditAction','auditUsername','auditResource','auditStartAt','auditEndAt','auditKeyword'].forEach(id => $(id).value = '');
  $('audit').textContent = '已清空筛选条件';
};

$('btnRefreshHistory').onclick = () => renderHistory();
$('btnClearHistory').onclick = () => { localStorage.removeItem(REQ_HISTORY_KEY); renderHistory(); };

$('state').textContent = token ? '已加载本地Token' : '未登录';
renderHistory();
