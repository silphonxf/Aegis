const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('aegis_admin_token') || '';

function base(){ return $('apiBase').value.trim().replace(/\/$/, ''); }
function headers(){ const h = {'Content-Type':'application/json'}; if(token) h.Authorization = `Bearer ${token}`; return h; }

async function request(path, options={}){
  const r = await fetch(`${base()}${path}`, options);
  const d = await r.json().catch(()=>({}));
  if(!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
  return d;
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
  try { $('monitoring').textContent = JSON.stringify(await request('/api/v1/monitoring/overview',{headers:headers()}), null, 2); }
  catch(e){ $('monitoring').textContent = e.message; }
};

$('btnCreateUser').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/users', {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        username: $('newUserName').value,
        password: $('newUserPassword').value,
        role_code: $('newUserRole').value,
      })
    });
    $('userCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('userCreateResult').textContent = e.message; }
};

$('btnCreateSystem').onclick = async () => {
  try {
    const d = await request('/api/v1/admin/systems', {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        system_code: $('newSystemCode').value,
        name: $('newSystemName').value,
        env: $('newSystemEnv').value || 'prod'
      })
    });
    $('systemCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('systemCreateResult').textContent = e.message; }
};

$('btnCreateTemplate').onclick = async () => {
  try {
    const d = await request('/api/v1/selfchecks/templates', {
      method:'POST', headers:headers(),
      body: JSON.stringify({
        system_id: Number($('tplSystemId').value),
        check_type: $('tplCheckType').value,
        name: $('tplName').value,
      })
    });
    $('templateCreateResult').textContent = JSON.stringify(d, null, 2);
  } catch(e){ $('templateCreateResult').textContent = e.message; }
};

$('btnLoadRules').onclick = async () => {
  try {
    const r = await request('/api/v1/monitoring/rules', { headers: headers() });
    $('cpuWarn').value = r.cpu_warn;
    $('cpuCritical').value = r.cpu_critical;
    $('memWarn').value = r.mem_warn;
    $('memCritical').value = r.mem_critical;
    $('diskWarn').value = r.disk_warn;
    $('diskCritical').value = r.disk_critical;
    $('ruleResult').textContent = JSON.stringify(r, null, 2);
  } catch (e) { $('ruleResult').textContent = e.message; }
};

$('btnSaveRules').onclick = async () => {
  try {
    const payload = {
      cpu_warn: Number($('cpuWarn').value),
      cpu_critical: Number($('cpuCritical').value),
      mem_warn: Number($('memWarn').value),
      mem_critical: Number($('memCritical').value),
      disk_warn: Number($('diskWarn').value),
      disk_critical: Number($('diskCritical').value),
    };
    const d = await request('/api/v1/monitoring/rules', {
      method: 'PUT',
      headers: headers(),
      body: JSON.stringify(payload),
    });
    $('ruleResult').textContent = JSON.stringify({ ...d, payload }, null, 2);
  } catch (e) { $('ruleResult').textContent = e.message; }
};

$('btnAudit').onclick = async () => {
  try { $('audit').textContent = JSON.stringify(await request('/api/v1/admin/audit-logs?page=1&size=20',{headers:headers()}), null, 2); }
  catch(e){ $('audit').textContent = e.message; }
};

$('state').textContent = token ? '已加载本地Token' : '未登录';
