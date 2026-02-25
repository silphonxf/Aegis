const $ = (id) => document.getElementById(id);

const state = {
  token: localStorage.getItem('aegis_token') || '',
};

function getBase() {
  return $('apiBase').value.trim().replace(/\/$/, '');
}

function headers() {
  const h = { 'Content-Type': 'application/json' };
  if (state.token) h.Authorization = `Bearer ${state.token}`;
  return h;
}

function setLoginState(text) {
  $('loginState').textContent = text;
}

async function api(path, options = {}) {
  const resp = await fetch(`${getBase()}${path}`, options);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.detail || `HTTP ${resp.status}`);
  return data;
}

$('btnLogin').onclick = async () => {
  try {
    const data = await api('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: $('username').value, password: $('password').value }),
    });
    state.token = data.access_token;
    localStorage.setItem('aegis_token', state.token);
    setLoginState('登录成功，Token 已保存');
  } catch (e) {
    setLoginState(`登录失败：${e.message}`);
  }
};

$('btnResolve').onclick = async () => {
  try {
    const qr = encodeURIComponent($('qrContent').value.trim());
    const data = await api(`/api/v1/inspections/points/resolve?qr_content=${qr}`, {
      headers: headers(),
    });
    $('resolveResult').textContent = JSON.stringify(data, null, 2);
    $('insSystemId').value = data.system_id;
    $('insPointId').value = data.point_id;
  } catch (e) {
    $('resolveResult').textContent = e.message;
  }
};

$('btnCreateInspection').onclick = async () => {
  try {
    const data = await api('/api/v1/inspections/records', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({
        system_id: Number($('insSystemId').value),
        point_id: Number($('insPointId').value),
        result: $('insResult').value,
        note: $('insNote').value || null,
        inspected_at: new Date().toISOString(),
      }),
    });
    $('inspectionResult').textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    $('inspectionResult').textContent = e.message;
  }
};

$('btnCreateSelfcheck').onclick = async () => {
  try {
    const data = await api('/api/v1/selfchecks/records', {
      method: 'POST',
      headers: headers(),
      body: JSON.stringify({
        system_id: Number($('scSystemId').value),
        template_id: Number($('scTemplateId').value),
        result: $('scResult').value,
        summary: $('scSummary').value || null,
        checked_at: new Date().toISOString(),
      }),
    });
    $('selfcheckResult').textContent = JSON.stringify(data, null, 2);
  } catch (e) {
    $('selfcheckResult').textContent = e.message;
  }
};

setLoginState(state.token ? '已加载本地 Token（可直接联调）' : '未登录');
