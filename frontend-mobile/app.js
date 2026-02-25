const $ = (id) => document.getElementById(id);
const state = { token: localStorage.getItem('aegis_token') || '' };

function getBase() {
  return $('apiBase').value.trim().replace(/\/$/, '');
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  if (state.token) headers.Authorization = `Bearer ${state.token}`;
  return headers;
}

function setLoginState(text) {
  $('loginState').textContent = text;
}

function show(id, data) {
  $(id).textContent = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
}

function parseError(respData, fallback) {
  if (!respData) return fallback;
  if (typeof respData === 'string') return respData;
  if (respData.message) return `${respData.code || 'ERROR'}: ${respData.message}`;
  if (respData.detail && typeof respData.detail === 'string') return respData.detail;
  return fallback;
}

async function api(path, options = {}) {
  const resp = await fetch(`${getBase()}${path}`, options);
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    throw new Error(parseError(data, `HTTP ${resp.status}`));
  }
  return data;
}

$('btnPing').onclick = async () => {
  try {
    const data = await api('/api/v1/health');
    alert(`后端可用：${data.status || 'ok'}`);
  } catch (e) {
    alert(`连通失败：${e.message}`);
  }
};

$('btnLogin').onclick = async () => {
  try {
    const data = await api('/api/v1/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        username: $('username').value.trim(),
        password: $('password').value,
      }),
    });
    state.token = data.access_token;
    localStorage.setItem('aegis_token', state.token);
    setLoginState('登录成功，Token 已保存');
  } catch (e) {
    setLoginState(`登录失败：${e.message}`);
  }
};

$('btnMe').onclick = async () => {
  try {
    const data = await api('/api/v1/auth/me', { headers: authHeaders() });
    show('meResult', data);
  } catch (e) {
    show('meResult', e.message);
  }
};

$('btnResolve').onclick = async () => {
  try {
    const qr = encodeURIComponent($('qrContent').value.trim());
    const data = await api(`/api/v1/inspections/points/resolve?qr_content=${qr}`, { headers: authHeaders() });
    show('resolveResult', data);
    $('insSystemId').value = data.system_id;
    $('insPointId').value = data.point_id;
    if (!$('scSystemId').value) $('scSystemId').value = data.system_id;
  } catch (e) {
    show('resolveResult', e.message);
  }
};

$('btnCreateInspection').onclick = async () => {
  try {
    const data = await api('/api/v1/inspections/records', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        system_id: Number($('insSystemId').value),
        point_id: Number($('insPointId').value),
        result: $('insResult').value,
        note: $('insNote').value || null,
        inspected_at: new Date().toISOString(),
      }),
    });
    show('inspectionResult', data);
  } catch (e) {
    show('inspectionResult', e.message);
  }
};

$('btnLoadInspectionHistory').onclick = async () => {
  try {
    const systemId = $('insSystemId').value.trim();
    const query = systemId ? `?system_id=${encodeURIComponent(systemId)}&page=1&size=20` : '?page=1&size=20';
    const data = await api(`/api/v1/inspections/records${query}`, { headers: authHeaders() });
    show('inspectionHistory', data);
  } catch (e) {
    show('inspectionHistory', e.message);
  }
};

$('btnCreateSelfcheck').onclick = async () => {
  try {
    const data = await api('/api/v1/selfchecks/records', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        system_id: Number($('scSystemId').value),
        template_id: Number($('scTemplateId').value),
        result: $('scResult').value,
        summary: $('scSummary').value || null,
        checked_at: new Date().toISOString(),
      }),
    });
    show('selfcheckResult', data);
  } catch (e) {
    show('selfcheckResult', e.message);
  }
};

$('btnLoadSelfcheckHistory').onclick = async () => {
  try {
    const systemId = $('scSystemId').value.trim();
    const query = systemId ? `?system_id=${encodeURIComponent(systemId)}&page=1&size=20` : '?page=1&size=20';
    const data = await api(`/api/v1/selfchecks/records${query}`, { headers: authHeaders() });
    show('selfcheckHistory', data);
  } catch (e) {
    show('selfcheckHistory', e.message);
  }
};

$('btnLoadOverview').onclick = async () => {
  try {
    const data = await api('/api/v1/monitoring/overview', { headers: authHeaders() });
    show('overviewResult', data);
  } catch (e) {
    show('overviewResult', e.message);
  }
};

$('btnLoadRules').onclick = async () => {
  try {
    const data = await api('/api/v1/monitoring/rules', { headers: authHeaders() });
    show('rulesResult', data);
  } catch (e) {
    show('rulesResult', e.message);
  }
};

setLoginState(state.token ? '已加载本地 Token（可直接联调）' : '未登录');
