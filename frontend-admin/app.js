const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('aegis_admin_token') || '';

function base(){ return $('apiBase').value.trim().replace(/\/$/, ''); }
function headers(){
  const h = {'Content-Type':'application/json'};
  if(token) h.Authorization = `Bearer ${token}`;
  return h;
}

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

$('btnOverview').onclick = async () => {
  try { $('overview').textContent = JSON.stringify(await request('/api/v1/systems/status/overview',{headers:headers()}), null, 2); }
  catch(e){ $('overview').textContent = e.message; }
};

$('btnAudit').onclick = async () => {
  try { $('audit').textContent = JSON.stringify(await request('/api/v1/admin/audit-logs?page=1&size=20',{headers:headers()}), null, 2); }
  catch(e){ $('audit').textContent = e.message; }
};

$('state').textContent = token ? '已加载本地Token' : '未登录';
