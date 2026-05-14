window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function renderRows(tbodyId, rowsHtml, emptyColspan, emptyText) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    tbody.innerHTML = rowsHtml || `<tr><td colspan="${emptyColspan}">${emptyText}</td></tr>`;
  }

  async function loadAll() {
    return ns.api.request('/api/v1/admin/emergency-config', { headers: ns.api.headers() });
  }

  async function listSshHosts() {
    const data = await loadAll();
    const rows = (data.ssh_hosts || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.host_code)}</td>
        <td>${escapeHtml(item.host_name)}</td>
        <td>${escapeHtml(item.host_ip)}</td>
        <td>${escapeHtml(item.port)}</td>
        <td>${escapeHtml(item.auth_type)}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgSshTbody', rows, 6, '暂无 SSH 主机配置');
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = `已读取 ${data.ssh_hosts?.length || 0} 条 SSH 主机配置。敏感字段已做脱敏展示。`;
  }

  async function saveSshHostMock() {
    const payload = {
      host_code: document.getElementById('emgSshHostCode')?.value.trim(),
      host_name: document.getElementById('emgSshHostName')?.value.trim(),
      host_ip: document.getElementById('emgSshHostIp')?.value.trim(),
      port: Number(document.getElementById('emgSshPort')?.value || 22),
      username: document.getElementById('emgSshUser')?.value.trim(),
      auth_type: document.getElementById('emgSshAuthType')?.value || 'password',
      connect_timeout_ms: 5000,
      enabled: true,
      remark: document.getElementById('emgSshRemark')?.value.trim() || null,
    };
    const secret = document.getElementById('emgSshSecret')?.value || '';
    if (payload.auth_type === 'password') payload.password_plaintext = secret;
    else payload.private_key_plaintext = secret;
    await ns.api.request('/api/v1/admin/emergency-config/ssh-hosts', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = `SSH 主机配置已保存：${payload.host_code}`;
    await listSshHosts();
  }

  async function listServerActions() {
    const data = await loadAll();
    const rows = (data.server_actions || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(item.script_type)}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgServerTbody', rows, 5, '暂无服务器动作配置');
    const result = document.getElementById('emgServerResult');
    if (result) result.textContent = `已读取 ${data.server_actions?.length || 0} 条服务器动作配置。`;
  }

  async function saveServerActionMock() {
    const payload = {
      action_code: document.getElementById('emgServerActionCode')?.value.trim(),
      action_name: document.getElementById('emgServerActionName')?.value.trim(),
      target_host_code: document.getElementById('emgServerHostCode')?.value.trim(),
      module_type: 'server',
      script_type: 'shell',
      script_body: document.getElementById('emgServerScript')?.value || '',
      confirm_text: document.getElementById('emgServerConfirmText')?.value.trim() || null,
      enabled: true,
      remark: null,
    };
    await ns.api.request('/api/v1/admin/emergency-config/server-actions', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const result = document.getElementById('emgServerResult');
    if (result) result.textContent = `服务器动作配置已保存：${payload.action_code}`;
    await listServerActions();
  }

  async function listDbActions() {
    const data = await loadAll();
    const rows = (data.database_actions || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.db_type)}</td>
        <td>${escapeHtml((item.param_schema || []).join(', ') || '-')}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgDbTbody', rows, 5, '暂无数据库动作配置');
    const result = document.getElementById('emgDbResult');
    if (result) result.textContent = `已读取 ${data.database_actions?.length || 0} 条数据库动作配置。`;
  }

  async function saveDbActionMock() {
    let params = [];
    const raw = document.getElementById('emgDbParamSchema')?.value.trim() || '';
    if (raw) {
      try {
        const parsed = JSON.parse(raw);
        params = Array.isArray(parsed) ? parsed.map((x) => typeof x === 'string' ? x : x?.name).filter(Boolean) : [];
      } catch {
        params = raw.split(',').map((x) => x.trim()).filter(Boolean);
      }
    }
    const payload = {
      action_code: document.getElementById('emgDbActionCode')?.value.trim(),
      action_name: document.getElementById('emgDbActionName')?.value.trim(),
      module_type: 'database',
      db_type: document.getElementById('emgDbType')?.value || 'oracle',
      target_host_code: document.getElementById('emgDbHostCode')?.value.trim() || null,
      script_type: 'sql',
      script_body: document.getElementById('emgDbScript')?.value || '',
      param_schema: params,
      result_mode: 'text',
      enabled: true,
      remark: null,
    };
    await ns.api.request('/api/v1/admin/emergency-config/database-actions', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const result = document.getElementById('emgDbResult');
    if (result) result.textContent = `数据库动作配置已保存：${payload.action_code}`;
    await listDbActions();
  }

  async function listProcessActions() {
    const data = await loadAll();
    const rows = (data.process_actions || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.process_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(item.process_id_source)}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgProcTbody', rows, 5, '暂无进程动作配置');
    const result = document.getElementById('emgProcResult');
    if (result) result.textContent = `已读取 ${data.process_actions?.length || 0} 条进程动作配置。`;
  }

  async function saveProcessActionMock() {
    const payload = {
      action_code: document.getElementById('emgProcActionCode')?.value.trim(),
      action_name: document.getElementById('emgProcActionName')?.value.trim(),
      module_type: 'process',
      target_host_code: document.getElementById('emgProcHostCode')?.value.trim(),
      process_name: document.getElementById('emgProcName')?.value.trim(),
      process_id_source: document.getElementById('emgProcIdSource')?.value || 'runtime_detect',
      default_process_id: document.getElementById('emgProcDefaultPid')?.value.trim() || null,
      script_type: 'shell',
      script_body: document.getElementById('emgProcScript')?.value || '',
      enabled: true,
      remark: document.getElementById('emgProcRemark')?.value.trim() || null,
    };
    await ns.api.request('/api/v1/admin/emergency-config/process-actions', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const result = document.getElementById('emgProcResult');
    if (result) result.textContent = `进程动作配置已保存：${payload.action_code}`;
    await listProcessActions();
  }

  ns.emergencyConfig = {
    loadAll,
    listSshHosts,
    saveSshHostMock,
    listServerActions,
    saveServerActionMock,
    listDbActions,
    saveDbActionMock,
    listProcessActions,
    saveProcessActionMock,
  };
})(window.AegisAdmin);
