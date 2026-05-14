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

  const mockData = {
    sshHosts: [
      { host_code: 'foc-app-01', host_name: '航信应用服务器-01', host_ip: '10.10.1.21', port: 22, auth_type: 'password', enabled: true },
      { host_code: 'foc-app-02', host_name: '离港服务服务器-02', host_ip: '10.10.1.35', port: 22, auth_type: 'private_key', enabled: true },
    ],
    serverActions: [
      { action_code: 'reboot-foc-app-01', action_name: '服务器重启', target_host_code: 'foc-app-01', script_type: 'shell', enabled: true },
      { action_code: 'reboot-foc-app-02', action_name: '服务器重启', target_host_code: 'foc-app-02', script_type: 'shell', enabled: true },
    ],
    dbActions: [
      { action_code: 'foc-password-query', action_name: 'FOC 密码查询', db_type: 'oracle', params: 'system_code, employee_id', enabled: true },
      { action_code: 'foc-deadlock-handle', action_name: 'FOC 死锁处理', db_type: 'oracle', params: '-', enabled: true },
    ],
    processActions: [
      { action_code: 'restart-foc-gateway', process_name: 'foc-gateway', target_host_code: 'foc-app-01', pid_source: 'runtime_detect', enabled: true },
      { action_code: 'restart-dispatch-worker', process_name: 'dispatch-sync-worker', target_host_code: 'foc-app-02', pid_source: 'fixed', enabled: true },
    ],
  };

  function renderRows(tbodyId, rowsHtml, emptyColspan, emptyText) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    tbody.innerHTML = rowsHtml || `<tr><td colspan="${emptyColspan}">${emptyText}</td></tr>`;
  }

  function listSshHosts() {
    const rows = mockData.sshHosts.map((item) => `
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
    if (result) result.textContent = '当前为管理端前端骨架演示，后续这里将读取真实 SSH 主机配置（敏感字段加密存储）。';
  }

  function saveSshHostMock() {
    const result = document.getElementById('emgSshResult');
    if (result) result.textContent = [
      '已触发【SSH 主机配置】前端占位保存。',
      '后续真实实现要点：',
      '1. 密码/私钥/私钥口令必须加密存储',
      '2. 管理端默认不回显敏感字段',
      '3. 主密钥从环境变量读取',
    ].join('\n');
    listSshHosts();
  }

  function listServerActions() {
    const rows = mockData.serverActions.map((item) => `
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
    if (result) result.textContent = '服务器动作当前以“服务器重启”为主，后续按 host_code + action_code 绑定脚本模板执行。';
  }

  function saveServerActionMock() {
    const result = document.getElementById('emgServerResult');
    if (result) result.textContent = '已触发【服务器动作配置】前端占位保存。后续这里会保存 shell 脚本模板和确认文案。';
    listServerActions();
  }

  function listDbActions() {
    const rows = mockData.dbActions.map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.action_name)}</td>
        <td>${escapeHtml(item.db_type)}</td>
        <td>${escapeHtml(item.params)}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgDbTbody', rows, 5, '暂无数据库动作配置');
    const result = document.getElementById('emgDbResult');
    if (result) result.textContent = '数据库动作模板建议支持参数占位符，如 {{system_code}} / {{employee_id}}。';
  }

  function saveDbActionMock() {
    const result = document.getElementById('emgDbResult');
    if (result) result.textContent = '已触发【数据库动作配置】前端占位保存。后续这里会保存 SQL / shell 模板及参数定义。';
    listDbActions();
  }

  function listProcessActions() {
    const rows = mockData.processActions.map((item) => `
      <tr>
        <td>${escapeHtml(item.action_code)}</td>
        <td>${escapeHtml(item.process_name)}</td>
        <td>${escapeHtml(item.target_host_code)}</td>
        <td>${escapeHtml(item.pid_source)}</td>
        <td>${item.enabled ? 'enabled' : 'disabled'}</td>
      </tr>
    `).join('');
    renderRows('emgProcTbody', rows, 5, '暂无进程动作配置');
    const result = document.getElementById('emgProcResult');
    if (result) result.textContent = '进程动作建议优先用脚本运行时解析 PID，不要强依赖前端传入 PID 直接 kill。';
  }

  function saveProcessActionMock() {
    const result = document.getElementById('emgProcResult');
    if (result) result.textContent = '已触发【进程动作配置】前端占位保存。后续这里会保存重启 / 关闭脚本模板。';
    listProcessActions();
  }

  ns.emergencyConfig = {
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
