window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  let cache = { ssh_hosts: [], server_actions: [], database_actions: [], process_actions: [] };
  let systems = [];
  let users = [];

  function escapeHtml(value) {
    return String(value ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#39;');
  }

  function setValue(id, value) {
    const el = document.getElementById(id);
    if (el) el.value = value ?? '';
  }

  function renderRows(tbodyId, rowsHtml, emptyColspan, emptyText) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    tbody.innerHTML = rowsHtml || `<tr><td colspan="${emptyColspan}">${emptyText}</td></tr>`;
  }

  async function loadAll() {
    cache = await ns.api.request('/api/v1/admin/emergency-config', { headers: ns.api.headers() });
    await hydrateSelectors();
    return cache;
  }

  async function hydrateSelectors() {
    const [systemResp, userResp] = await Promise.all([
      ns.api.request('/api/v1/admin/systems?page=1&size=200', { headers: ns.api.headers() }),
      ns.api.request('/api/v1/admin/users?page=1&size=100', { headers: ns.api.headers() }),
    ]).catch(() => [{ items: [] }, { items: [] }]);
    systems = systemResp.items || [];
    users = userResp.items || [];
    const hostOptions = ['<option value="">请选择 SSH 主机</option>']
      .concat((cache.ssh_hosts || []).map((h) => `<option value="${escapeHtml(h.host_code)}">${escapeHtml(h.host_name)} / ${escapeHtml(h.host_ip)}</option>`))
      .join('');
    const systemOptions = ['<option value="">请选择系统</option>']
      .concat(systems.map((s) => `<option value="${escapeHtml(s.id)}">${escapeHtml(s.system_code)} / ${escapeHtml(s.name)}</option>`))
      .join('');
    const userOptions = ['<option value="">请选择管理员</option>']
      .concat(users.filter((u) => ['admin', 'super_admin'].includes(u.role_code || u.role)).map((u) => `<option value="${escapeHtml(u.id)}">${escapeHtml(u.username)} / ${escapeHtml(u.role_code || u.role)}</option>`))
      .join('');
    ['emgServerHostCode', 'emgProcHostCode', 'emgCustomHostCode', 'emgDbHostCode'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = hostOptions;
    });
    ['emgSshSystemId', 'emgServerSystemId', 'emgProcSystemId', 'emgCustomSystemId', 'emgDbSystemId'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = systemOptions;
    });
    ['emgServerAdminUserId', 'emgProcAdminUserId', 'emgCustomAdminUserId', 'emgDbAdminUserId'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = userOptions;
    });
  }

  function systemName(id) {
    return systems.find((s) => Number(s.id) === Number(id))?.name || '-';
  }

  function userName(id) {
    return users.find((u) => Number(u.id) === Number(id))?.username || '-';
  }

  async function importJsonToDb() {
    const data = await ns.api.request('/api/v1/admin/emergency-config/import-json', {
      method: 'POST',
      headers: ns.api.headers(),
    });
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = `JSON 导入完成：SSH ${data.ssh_hosts || 0} 条，服务器动作 ${data.server_actions || 0} 条，数据库动作 ${data.database_actions || 0} 条，进程动作 ${data.process_actions || 0} 条`;
    await listSshHosts();
    return data;
  }

  async function listSshHosts() {
    const data = await loadAll();
    const rows = (data.ssh_hosts || []).map((item) => `
      <tr>
        <td>${escapeHtml(item.host_code)}</td>
        <td>${escapeHtml(item.host_name)}</td>
        <td>${escapeHtml(item.host_ip)}</td>
        <td>${escapeHtml(item.port)}</td>
        <td>${escapeHtml(item.username)}</td>
        <td>${item.has_password ? '已配置' : '未配置'}</td>
        <td>${item.enabled ? '启用' : '停用'}</td>
        <td><button class="toolbar-btn small" data-emg-edit-ssh="${escapeHtml(item.host_code)}">编辑</button></td>
      </tr>
    `).join('');
    renderRows('emgSshTbody', rows, 8, '暂无 SSH 主机配置');
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = `已读取 ${data.ssh_hosts?.length || 0} 条 SSH 主机配置。密码不回显。`;
  }

  async function saveSshHostMock() {
    const payload = {
      host_code: document.getElementById('emgSshHostCode')?.value.trim(),
      host_name: document.getElementById('emgSshHostName')?.value.trim(),
      host_ip: document.getElementById('emgSshHostIp')?.value.trim(),
      port: Number(document.getElementById('emgSshPort')?.value || 22),
      username: document.getElementById('emgSshUser')?.value.trim(),
      auth_type: 'password',
      connect_timeout_ms: 5000,
      system_id: Number(document.getElementById('emgSshSystemId')?.value || 0) || null,
      enabled: true,
      remark: document.getElementById('emgSshRemark')?.value.trim() || null,
    };
    const secret = document.getElementById('emgSshSecret')?.value || '';
    if (secret) payload.password_plaintext = secret;
    await ns.api.request('/api/v1/admin/emergency-config/ssh-hosts', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    setValue('emgSshSecret', '');
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = `SSH 主机配置已保存：${payload.host_code}`;
    await listSshHosts();
  }

  function buildServerPayload(prefix, category) {
    return {
      action_code: document.getElementById(`${prefix}ActionCode`)?.value.trim(),
      action_name: document.getElementById(`${prefix}ActionName`)?.value.trim(),
      target_host_code: document.getElementById(`${prefix}HostCode`)?.value.trim(),
      module_type: 'server',
      action_category: category,
      system_id: Number(document.getElementById(`${prefix}SystemId`)?.value || 0) || null,
      admin_user_id: Number(document.getElementById(`${prefix}AdminUserId`)?.value || 0) || null,
      script_type: 'shell',
      script_body: document.getElementById(`${prefix}Script`)?.value || '',
      confirm_text: document.getElementById(`${prefix}ConfirmText`)?.value.trim() || null,
      enabled: true,
      remark: document.getElementById(`${prefix}Remark`)?.value.trim() || null,
    };
  }

  async function listServerActions() {
    const data = await loadAll();
    const rows = (data.server_actions || []).filter((item) => item.action_category !== 'custom_command').map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(systemName(item.system_id))}</td>
        <td>${escapeHtml(userName(item.admin_user_id))}</td>
        <td>${item.enabled ? '启用' : '停用'}</td>
        <td><button class="toolbar-btn small" data-emg-edit-server="${escapeHtml(item.action_code)}">编辑</button></td>
      </tr>
    `).join('');
    renderRows('emgServerTbody', rows, 7, '暂无服务器动作配置');
  }

  async function saveServerActionMock() {
    const payload = buildServerPayload('emgServer', 'reboot_host');
    await ns.api.request('/api/v1/admin/emergency-config/server-actions', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
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
        <td>${item.enabled ? '启用' : '停用'}</td>
      </tr>
    `).join('');
    renderRows('emgDbTbody', rows, 5, '暂无数据库动作配置');
  }

  async function saveDbActionMock() {
    const raw = document.getElementById('emgDbParamSchema')?.value.trim() || '';
    const params = raw ? raw.split(',').map((x) => x.trim()).filter(Boolean) : [];
    const payload = {
      action_code: document.getElementById('emgDbActionCode')?.value.trim(),
      action_name: document.getElementById('emgDbActionName')?.value.trim(),
      module_type: 'database',
      db_type: document.getElementById('emgDbType')?.value || 'oracle',
      system_id: Number(document.getElementById('emgDbSystemId')?.value || 0) || null,
      admin_user_id: Number(document.getElementById('emgDbAdminUserId')?.value || 0) || null,
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
    await listDbActions();
  }

  async function listProcessActions() {
    const data = await loadAll();
    const rows = (data.process_actions || []).filter((item) => item.action_category !== 'custom_command').map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.process_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(systemName(item.system_id))}</td>
        <td>${escapeHtml(userName(item.admin_user_id))}</td>
        <td>${item.enabled ? '启用' : '停用'}</td>
        <td><button class="toolbar-btn small" data-emg-edit-process="${escapeHtml(item.action_code)}">编辑</button></td>
      </tr>
    `).join('');
    renderRows('emgProcTbody', rows, 8, '暂无进程动作配置');
  }

  async function saveProcessActionMock() {
    const payload = {
      action_code: document.getElementById('emgProcActionCode')?.value.trim(),
      action_name: document.getElementById('emgProcActionName')?.value.trim(),
      module_type: 'process',
      action_category: 'restart_process',
      system_id: Number(document.getElementById('emgProcSystemId')?.value || 0) || null,
      admin_user_id: Number(document.getElementById('emgProcAdminUserId')?.value || 0) || null,
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
    await listProcessActions();
  }

  async function listCustomActions() {
    const data = await loadAll();
    const rows = (data.server_actions || []).filter((item) => item.action_category === 'custom_command').map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(systemName(item.system_id))}</td>
        <td>${escapeHtml(userName(item.admin_user_id))}</td>
        <td>${item.enabled ? '启用' : '停用'}</td>
        <td><button class="toolbar-btn small" data-emg-edit-custom="${escapeHtml(item.action_code)}">编辑</button></td>
      </tr>
    `).join('');
    renderRows('emgCustomTbody', rows, 7, '暂无自定义命令配置');
  }

  async function saveCustomAction() {
    const payload = buildServerPayload('emgCustom', 'custom_command');
    await ns.api.request('/api/v1/admin/emergency-config/server-actions', {
      method: 'POST',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    await listCustomActions();
  }

  function bindEditDelegates() {
    document.addEventListener('click', (event) => {
      const btn = event.target.closest('[data-emg-edit-ssh],[data-emg-edit-server],[data-emg-edit-process],[data-emg-edit-custom]');
      if (!btn) return;
      const ssh = btn.dataset.emgEditSsh;
      const server = btn.dataset.emgEditServer;
      const process = btn.dataset.emgEditProcess;
      const custom = btn.dataset.emgEditCustom;
      if (ssh) {
        const item = (cache.ssh_hosts || []).find((x) => x.host_code === ssh);
        if (!item) return;
        setValue('emgSshHostCode', item.host_code);
        setValue('emgSshHostName', item.host_name);
        setValue('emgSshHostIp', item.host_ip);
        setValue('emgSshPort', item.port || 22);
        setValue('emgSshUser', item.username);
        setValue('emgSshSystemId', item.system_id);
        setValue('emgSshRemark', item.remark);
        setValue('emgSshSecret', '');
      }
      if (server || custom) {
        const item = (cache.server_actions || []).find((x) => x.action_code === (server || custom));
        if (!item) return;
        const prefix = server ? 'emgServer' : 'emgCustom';
        setValue(`${prefix}ActionCode`, item.action_code);
        setValue(`${prefix}ActionName`, item.action_name);
        setValue(`${prefix}HostCode`, item.target_host_code);
        setValue(`${prefix}SystemId`, item.system_id);
        setValue(`${prefix}AdminUserId`, item.admin_user_id);
        setValue(`${prefix}Script`, item.script_body);
        setValue(`${prefix}ConfirmText`, item.confirm_text);
        setValue(`${prefix}Remark`, item.remark);
      }
      if (process) {
        const item = (cache.process_actions || []).find((x) => x.action_code === process);
        if (!item) return;
        setValue('emgProcActionCode', item.action_code);
        setValue('emgProcActionName', item.action_name);
        setValue('emgProcHostCode', item.target_host_code);
        setValue('emgProcSystemId', item.system_id);
        setValue('emgProcAdminUserId', item.admin_user_id);
        setValue('emgProcName', item.process_name);
        setValue('emgProcIdSource', item.process_id_source);
        setValue('emgProcDefaultPid', item.default_process_id);
        setValue('emgProcScript', item.script_body);
        setValue('emgProcRemark', item.remark);
      }
    });
  }

  bindEditDelegates();

  ns.emergencyConfig = {
    loadAll,
    importJsonToDb,
    listSshHosts,
    saveSshHostMock,
    listServerActions,
    saveServerActionMock,
    listDbActions,
    saveDbActionMock,
    listProcessActions,
    saveProcessActionMock,
    listCustomActions,
    saveCustomAction,
  };
})(window.AegisAdmin);
