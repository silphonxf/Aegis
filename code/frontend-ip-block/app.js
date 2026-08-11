const TOKEN_KEY = 'aegis_admin_token';

const state = {
  token: '',
  user: null,
  queryItems: [],
  queryInvalidInputs: [],
  selectedQueryIps: new Set(),
  batchItems: [],
  invalidRows: [],
  selectedIps: new Set(),
  file: null,
};

const $ = (id) => document.getElementById(id);
const apiBase = () => `https://${window.location.hostname || '127.0.0.1'}:8000`;

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function detailMessage(data, status) {
  return data?.message || data?.detail?.message || data?.detail || `请求失败（HTTP ${status}）`;
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
  const response = await fetch(`${apiBase()}${path}`, { ...options, headers });
  const contentType = response.headers.get('content-type') || '';
  const data = contentType.includes('application/json') ? await response.json().catch(() => ({})) : null;
  if (!response.ok) {
    if (response.status === 401) logout('登录已失效，请重新登录');
    throw new Error(detailMessage(data, response.status));
  }
  return data;
}

function jsonOptions(body, method = 'POST') {
  return {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  };
}

function setAuth(loggedIn) {
  $('loginView').classList.toggle('hidden', loggedIn);
  $('appView').classList.toggle('hidden', !loggedIn);
  $('loginView').toggleAttribute('hidden', loggedIn);
  $('appView').toggleAttribute('hidden', !loggedIn);
}

function saveToken(token) {
  state.token = token;
  localStorage.setItem(TOKEN_KEY, token);
  sessionStorage.setItem(TOKEN_KEY, token);
}

function logout(message = '') {
  state.token = '';
  state.user = null;
  localStorage.removeItem(TOKEN_KEY);
  sessionStorage.removeItem(TOKEN_KEY);
  setAuth(false);
  if (message) $('loginMessage').textContent = message;
}

function toast(message, type = 'info') {
  const item = document.createElement('div');
  item.className = `toast ${type === 'error' ? 'error' : ''}`;
  item.textContent = message;
  $('toastRegion').appendChild(item);
  setTimeout(() => item.remove(), 4200);
}

function setBusy(button, busy, text) {
  if (!button) return;
  if (busy) {
    button.dataset.originalText = button.textContent;
    button.textContent = text || '处理中…';
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalText || button.textContent;
    button.disabled = false;
  }
}

function isIpv4(value) {
  const parts = String(value).trim().split('.');
  return parts.length === 4 && parts.every((part) => /^\d{1,3}$/.test(part) && Number(part) >= 0 && Number(part) <= 255 && String(Number(part)) === part);
}

function locationText(item) {
  const location = item?.basic?.location || {};
  return [location.country || item?.country, location.province, location.city].filter(Boolean).join(' / ') || '未知';
}

function dangerousTypes(item) {
  const values = item?.malicious_judgments?.length ? item.malicious_judgments : item?.judgments;
  return Array.isArray(values) && values.length ? values.join('、') : '未命中危险类型';
}

function verdict(item) {
  if (!item?.verified) return { text: '未验证 · 人工确认', cls: 'risk-warning', chip: 'unknown' };
  if (item.is_malicious) return { text: '恶意 IP', cls: 'risk-danger', chip: 'danger' };
  return { text: '未发现恶意', cls: 'risk-safe', chip: 'safe' };
}

async function login(event) {
  event.preventDefault();
  const button = event.submitter;
  $('loginMessage').textContent = '';
  setBusy(button, true, '正在验证…');
  try {
    const data = await api('/api/v1/auth/login', jsonOptions({
      username: $('username').value.trim(),
      password: $('password').value,
    }));
    saveToken(data.access_token);
    await initializeApp();
  } catch (error) {
    $('loginMessage').textContent = error.message;
  } finally {
    setBusy(button, false);
  }
}

async function initializeApp() {
  const user = await api('/api/v1/auth/me');
  if (!['admin', 'super_admin'].includes(user.role)) {
    logout('当前账号没有 IP 封禁权限');
    return;
  }
  state.user = user;
  $('userBadge').textContent = `${user.nickname || user.username} · ${user.role}`;
  $('apiState').className = 'status-pill ok';
  $('apiState').innerHTML = '<i></i>后端已连接';
  setAuth(true);
  await loadFirewallConfig();
}

async function restoreSession() {
  state.token = localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY) || '';
  if (!state.token) {
    setAuth(false);
    return;
  }
  try {
    await initializeApp();
  } catch (error) {
    $('apiState').className = 'status-pill bad';
    logout(error.message);
  }
}

async function loadFirewallConfig() {
  const button = $('refreshConfig');
  setBusy(button, true, '…');
  try {
    const data = await api('/api/v1/admin/threat-intel/firewall-config');
    $('firewallName').textContent = data.target_name || data.target_code || '默认山石设备';
    $('firewallHost').textContent = data.firewall_ip ? `${data.scheme || 'https'}://${data.firewall_ip}:${data.port || 443}` : '未配置';
    $('firewallBook').textContent = data.address_book_name || '未配置';
    const ready = data.enabled && data.has_username && data.has_password && data.firewall_ip && data.address_book_name;
    $('firewallState').textContent = ready ? '可执行' : data.enabled ? '配置不完整' : '已停用';
    $('firewallState').className = ready ? 'risk-safe' : 'risk-warning';
  } catch (error) {
    $('firewallState').textContent = '读取失败';
    $('firewallState').className = 'risk-danger';
    toast(error.message, 'error');
  } finally {
    setBusy(button, false);
  }
}

function updateVerificationControls() {
  const enabled = $('verifyThreatbook').checked;
  $('realtimeVerdict').disabled = !enabled;
  $('checkIpList').textContent = enabled ? '生成 IP 情报清单' : '生成未验证 IP 清单';
}

function updateDryRunHint() {
  const dryRun = $('dryRun').checked;
  $('dryRunHint').textContent = dryRun ? '不会写入防火墙' : '真实写入并回读核验';
  $('dryRunHint').className = dryRun ? '' : 'risk-danger';
}

function parseIpList(rawInput) {
  const tokens = String(rawInput || '').split(/[\s,，;；]+/).map((value) => value.trim()).filter(Boolean);
  const uniqueTokens = [...new Set(tokens)];
  const ips = uniqueTokens.filter(isIpv4);
  const invalid = uniqueTokens.filter((value) => !isIpv4(value));
  if (ips.length > 100) throw new Error('单次最多查询 100 个 IPv4');
  return { ips, invalid };
}

function updateQueryStats() {
  $('queryValidCount').textContent = state.queryItems.length;
  $('queryMaliciousCount').textContent = state.queryItems.filter((item) => item.is_malicious === true).length;
  $('querySelectedCount').textContent = state.selectedQueryIps.size;
  $('queryInvalidCount').textContent = state.queryInvalidInputs.length;
  $('blockQueryList').disabled = !state.selectedQueryIps.size;
}

function renderQueryList() {
  $('singleEmpty').classList.add('hidden');
  $('singleResult').classList.remove('hidden');
  $('singleResult').removeAttribute('hidden');
  const body = $('queryTable');
  body.innerHTML = state.queryItems.map((item) => {
    const itemVerdict = verdict(item);
    return `<tr>
      <td class="check-cell"><input type="checkbox" data-query-ip="${escapeHtml(item.ip)}" ${state.selectedQueryIps.has(item.ip) ? 'checked' : ''} /></td>
      <td><strong>${escapeHtml(item.ip)}</strong></td>
      <td><span class="verdict-chip ${itemVerdict.chip}">${escapeHtml(itemVerdict.text)}</span></td>
      <td>${escapeHtml(locationText(item))}</td>
      <td>${escapeHtml(dangerousTypes(item))}</td>
      <td>${escapeHtml(item.severity || item.risk_level || '未知')}</td>
      <td>${escapeHtml(item.confidence_level || '未知')}</td>
      <td>${escapeHtml(item.summary || '等待人工确认')}</td>
    </tr>`;
  }).join('') || '<tr><td colspan="8" class="table-empty">没有可处理的有效 IP</td></tr>';
  body.querySelectorAll('input[data-query-ip]').forEach((checkbox) => {
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) state.selectedQueryIps.add(checkbox.dataset.queryIp);
      else state.selectedQueryIps.delete(checkbox.dataset.queryIp);
      updateQueryStats();
    });
  });

  if (state.queryInvalidInputs.length) {
    $('queryInvalidInputs').innerHTML = `<strong>以下输入不是合法 IPv4，未加入清单：</strong><br />${state.queryInvalidInputs.map(escapeHtml).join('、')}`;
    $('queryInvalidInputs').classList.remove('hidden');
    $('queryInvalidInputs').removeAttribute('hidden');
  } else {
    $('queryInvalidInputs').classList.add('hidden');
    $('queryInvalidInputs').setAttribute('hidden', '');
  }
  updateQueryStats();
}

async function checkIpList() {
  const button = $('checkIpList');
  let parsed;
  try {
    parsed = parseIpList($('ipListInput').value);
  } catch (error) {
    toast(error.message, 'error');
    return;
  }
  if (!parsed.ips.length) {
    toast('请输入至少一个合法的 IPv4 地址', 'error');
    return;
  }
  setBusy(button, true, $('verifyThreatbook').checked ? `正在查询 ${parsed.ips.length} 个 IP…` : '正在生成清单…');
  try {
    state.queryInvalidInputs = parsed.invalid;
    if (!$('verifyThreatbook').checked) {
      state.queryItems = parsed.ips.map((ip) => ({
        ip,
        verified: false,
        risk_level: 'unverified',
        summary: '已跳过微步验证，请确认来源和封禁依据。',
      }));
      state.selectedQueryIps = new Set(parsed.ips);
      renderQueryList();
      return;
    }
    const data = await api('/api/v1/admin/threat-intel/ip-reputation', jsonOptions({
      ips: parsed.ips,
      lang: 'zh',
      realtime_verdict: $('realtimeVerdict').value === 'true',
    }));
    const returnedItems = new Map((data.items || []).map((item) => [item.ip || item.resource, item]));
    state.queryItems = parsed.ips.map((ip) => {
      const item = returnedItems.get(ip);
      return item
        ? { ...item, ip, verified: true }
        : { ip, verified: false, risk_level: 'unverified', summary: '威胁情报未返回该 IP，请人工确认。' };
    });
    state.selectedQueryIps = new Set(
      state.queryItems.filter((item) => item.verified ? item.should_block : false).map((item) => item.ip),
    );
    renderQueryList();
    toast(`已形成 ${state.queryItems.length} 条 IP 情报清单`);
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(button, false);
    updateVerificationControls();
  }
}

function showOperation(data) {
  $('operationResult').textContent = JSON.stringify(data, null, 2);
  $('operationPanel').classList.remove('hidden');
  $('operationPanel').removeAttribute('hidden');
  $('operationPanel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function executeBlock(ips, reason, button) {
  const dryRun = $('dryRun').checked;
  const action = dryRun ? '执行演练' : '永久写入山石地址簿';
  if (!window.confirm(`确认${action}？\n\n目标 IP 数量：${ips.length}\n${ips.join(', ')}`)) return;
  setBusy(button, true, dryRun ? '演练中…' : '正在封禁…');
  try {
    const data = await api('/api/v1/admin/threat-intel/block-ips', jsonOptions({
      ips,
      reason: reason || null,
      source: 'ip-block-console',
      dry_run: dryRun,
    }));
    showOperation(data);
    toast(dryRun ? '演练完成，未写入防火墙' : `封禁完成，已核验 ${data.verified_ips?.length || 0} 个 IP`);
  } catch (error) {
    toast(error.message, 'error');
    showOperation({ status: 'failed', message: error.message, ips });
  } finally {
    setBusy(button, false);
  }
}

function selectQueryCandidates() {
  state.selectedQueryIps = new Set(
    state.queryItems.filter((item) => item.verified ? item.should_block : false).map((item) => item.ip),
  );
  renderQueryList();
}

function selectQueryAll() {
  state.selectedQueryIps = new Set(state.queryItems.map((item) => item.ip));
  renderQueryList();
}

function clearQuerySelection() {
  state.selectedQueryIps = new Set();
  renderQueryList();
}

function blockQueryList() {
  const ips = [...state.selectedQueryIps];
  if (!ips.length) return;
  const reason = $('queryReason').value.trim() || '根据 Aegis IP 情报清单人工选择封禁';
  executeBlock(ips, reason, $('blockQueryList'));
}

function switchTab(name) {
  document.querySelectorAll('.tab').forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
  $('singlePanel').classList.toggle('hidden', name !== 'single');
  $('batchPanel').classList.toggle('hidden', name !== 'batch');
  $('singlePanel').toggleAttribute('hidden', name !== 'single');
  $('batchPanel').toggleAttribute('hidden', name !== 'batch');
}

function chooseFile(file) {
  if (!file) return;
  if (!/\.(xlsx|xlsm|xltx|xltm)$/i.test(file.name)) {
    toast('请选择 .xlsx 类 Excel 文件', 'error');
    return;
  }
  state.file = file;
  $('selectedFile').textContent = `${file.name} · ${(file.size / 1024).toFixed(1)} KB`;
  $('importExcel').disabled = false;
}

async function downloadTemplate() {
  const button = $('downloadTemplate');
  setBusy(button, true, '正在生成…');
  try {
    const response = await fetch(`${apiBase()}/api/v1/admin/threat-intel/ip-block-template`, {
      headers: { Authorization: `Bearer ${state.token}` },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(detailMessage(data, response.status));
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'aegis-ip-block-template.xlsx';
    link.click();
    URL.revokeObjectURL(url);
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(button, false);
  }
}

function updateBatchStats() {
  $('validCount').textContent = state.batchItems.length;
  $('maliciousCount').textContent = state.batchItems.filter((item) => item.is_malicious === true).length;
  $('selectedCount').textContent = state.selectedIps.size;
  $('invalidCount').textContent = state.invalidRows.length;
  $('blockBatch').disabled = !state.selectedIps.size;
}

function renderBatch() {
  const body = $('batchTable');
  if (!state.batchItems.length) {
    body.innerHTML = '<tr><td colspan="8" class="table-empty">没有可处理的有效 IP</td></tr>';
  } else {
    body.innerHTML = state.batchItems.map((item) => {
      const itemVerdict = verdict(item);
      return `<tr>
        <td class="check-cell"><input type="checkbox" data-ip="${escapeHtml(item.ip)}" ${state.selectedIps.has(item.ip) ? 'checked' : ''} /></td>
        <td><strong>${escapeHtml(item.ip)}</strong></td>
        <td><span class="verdict-chip ${itemVerdict.chip}">${escapeHtml(itemVerdict.text)}</span></td>
        <td>${escapeHtml(locationText(item))}</td>
        <td>${escapeHtml(dangerousTypes(item))}</td>
        <td>${escapeHtml(item.severity || item.risk_level || '未知')}</td>
        <td>${escapeHtml(item.confidence_level || '未知')}</td>
        <td>${escapeHtml(item.import_reason || '—')}</td>
      </tr>`;
    }).join('');
    body.querySelectorAll('input[data-ip]').forEach((checkbox) => {
      checkbox.addEventListener('change', () => {
        if (checkbox.checked) state.selectedIps.add(checkbox.dataset.ip);
        else state.selectedIps.delete(checkbox.dataset.ip);
        updateBatchStats();
      });
    });
  }

  if (state.invalidRows.length) {
    $('invalidRows').innerHTML = `<strong>以下行未导入：</strong><br />${state.invalidRows.map((row) => `${escapeHtml(row.sheet)} 第 ${row.row} 行：${escapeHtml(row.ip)}（${escapeHtml(row.error)}）`).join('<br />')}`;
    $('invalidRows').classList.remove('hidden');
    $('invalidRows').removeAttribute('hidden');
  } else {
    $('invalidRows').classList.add('hidden');
    $('invalidRows').setAttribute('hidden', '');
  }
  $('selectCandidates').disabled = !state.batchItems.length;
  $('selectAll').disabled = !state.batchItems.length;
  updateBatchStats();
}

async function importExcel() {
  if (!state.file) return;
  const button = $('importExcel');
  setBusy(button, true, $('verifyThreatbook').checked ? '解析并查询微步…' : '正在解析…');
  const form = new FormData();
  form.append('file', state.file);
  form.append('verify_with_threatbook', String($('verifyThreatbook').checked));
  form.append('realtime_verdict', $('realtimeVerdict').value);
  try {
    const data = await api('/api/v1/admin/threat-intel/ip-block-import', { method: 'POST', body: form });
    state.batchItems = data.items || [];
    state.invalidRows = data.invalid_rows || [];
    state.selectedIps = new Set(
      state.batchItems
        .filter((item) => item.verified ? item.should_block : true)
        .map((item) => item.ip),
    );
    renderBatch();
    toast(`已导入 ${state.batchItems.length} 个有效 IP`);
  } catch (error) {
    toast(error.message, 'error');
  } finally {
    setBusy(button, false);
  }
}

function selectCandidates() {
  state.selectedIps = new Set(
    state.batchItems
      .filter((item) => item.verified ? item.should_block : true)
      .map((item) => item.ip),
  );
  renderBatch();
}

function selectAll() {
  state.selectedIps = new Set(state.batchItems.map((item) => item.ip));
  renderBatch();
}

function blockBatch() {
  const ips = [...state.selectedIps];
  if (!ips.length) return;
  const reasons = [...new Set(
    state.batchItems
      .filter((item) => state.selectedIps.has(item.ip) && item.import_reason)
      .map((item) => item.import_reason),
  )];
  const reason = reasons.length ? `Excel批量封禁：${reasons.slice(0, 5).join('；')}` : 'Excel 批量导入封禁';
  executeBlock(ips, reason, $('blockBatch'));
}

function bindEvents() {
  $('loginForm').addEventListener('submit', login);
  $('logoutButton').addEventListener('click', () => logout());
  $('refreshConfig').addEventListener('click', loadFirewallConfig);
  $('verifyThreatbook').addEventListener('change', updateVerificationControls);
  $('dryRun').addEventListener('change', updateDryRunHint);
  $('checkIpList').addEventListener('click', checkIpList);
  $('ipListInput').addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) checkIpList();
  });
  $('selectQueryCandidates').addEventListener('click', selectQueryCandidates);
  $('selectQueryAll').addEventListener('click', selectQueryAll);
  $('clearQuerySelection').addEventListener('click', clearQuerySelection);
  $('blockQueryList').addEventListener('click', blockQueryList);
  document.querySelectorAll('.tab').forEach((tab) => tab.addEventListener('click', () => switchTab(tab.dataset.tab)));
  $('downloadTemplate').addEventListener('click', downloadTemplate);
  $('dropZone').addEventListener('click', () => $('excelFile').click());
  $('dropZone').addEventListener('keydown', (event) => { if (event.key === 'Enter' || event.key === ' ') $('excelFile').click(); });
  $('dropZone').addEventListener('dragover', (event) => { event.preventDefault(); $('dropZone').classList.add('dragging'); });
  $('dropZone').addEventListener('dragleave', () => $('dropZone').classList.remove('dragging'));
  $('dropZone').addEventListener('drop', (event) => {
    event.preventDefault();
    $('dropZone').classList.remove('dragging');
    chooseFile(event.dataTransfer.files?.[0]);
  });
  $('excelFile').addEventListener('change', () => chooseFile($('excelFile').files?.[0]));
  $('importExcel').addEventListener('click', importExcel);
  $('selectCandidates').addEventListener('click', selectCandidates);
  $('selectAll').addEventListener('click', selectAll);
  $('blockBatch').addEventListener('click', blockBatch);
  $('closeOperation').addEventListener('click', () => {
    $('operationPanel').classList.add('hidden');
    $('operationPanel').setAttribute('hidden', '');
  });
}

bindEvents();
updateVerificationControls();
updateDryRunHint();
restoreSession();
