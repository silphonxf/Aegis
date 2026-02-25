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

$('btnOverview').onclick = async () => {
  try { $('overview').textContent = JSON.stringify(await request('/api/v1/systems/status/overview',{headers:headers()}), null, 2); }
  catch(e){ $('overview').textContent = e.message; }
};

$('btnAudit').onclick = async () => {
  try { $('audit').textContent = JSON.stringify(await request('/api/v1/admin/audit-logs?page=1&size=20',{headers:headers()}), null, 2); }
  catch(e){ $('audit').textContent = e.message; }
};

function loadRules(){
  const raw = localStorage.getItem('aegis_status_rules');
  if(!raw) return;
  try {
    const r = JSON.parse(raw);
    ['cpuWarn','cpuCritical','memWarn','memCritical','diskWarn','diskCritical'].forEach(k => {
      if (r[k] !== undefined) $(k).value = r[k];
    });
  } catch {}
}

$('btnSaveRules').onclick = () => {
  const rules = {
    cpuWarn: Number($('cpuWarn').value),
    cpuCritical: Number($('cpuCritical').value),
    memWarn: Number($('memWarn').value),
    memCritical: Number($('memCritical').value),
    diskWarn: Number($('diskWarn').value),
    diskCritical: Number($('diskCritical').value),
  };
  localStorage.setItem('aegis_status_rules', JSON.stringify(rules));
  $('ruleResult').textContent = JSON.stringify({ message: '已保存到本地（后续接后端配置）', rules }, null, 2);
};

$('state').textContent = token ? '已加载本地Token' : '未登录';
loadRules();
