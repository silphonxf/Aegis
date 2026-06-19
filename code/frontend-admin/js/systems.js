window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  ns.state = ns.state || {};

  function envLabel(env) {
    if (env === 'prod') return '生产';
    if (env === 'test') return '测试';
    if (env === 'dev') return '开发';
    return env || '-';
  }

  function buildSystemQuery() {
    const params = new URLSearchParams({ page: '1', size: '200' });
    const keyword = document.getElementById('systemSearchKeyword2')?.value.trim();
    const env = document.getElementById('systemFilterEnv')?.value;
    const active = document.getElementById('systemFilterActive')?.value;
    const sortBy = document.getElementById('systemSortBy')?.value || 'updated_at';
    const sortOrder = document.getElementById('systemSortOrder')?.value || 'desc';
    if (keyword) params.set('keyword', keyword);
    if (env) params.set('env', env);
    if (active) params.set('is_active', active);
    if (sortBy) params.set('sort_by', sortBy);
    if (sortOrder) params.set('sort_order', sortOrder);
    return params.toString();
  }

  function renderLogConfigs(logConfigs) {
    if (!Array.isArray(logConfigs) || !logConfigs.length) return '-';
    return logConfigs
      .map((item) => item.absolute_path || item.log_name || '-')
      .filter(Boolean)
      .map((item) => ns.toolbox.escapeHtml(item))
      .join('<br />');
  }

  function renderSystemResultBoard(items, message = '') {
    const tbody = document.getElementById('systemListTbody');
    const summary = document.getElementById('systemListSummary');
    const list = items || [];
    ns.state.latestSystems = list;
    const rows = list.map((s, idx) => {
      const ownerText = Array.isArray(s.owner_user_ids) && s.owner_user_ids.length
        ? s.owner_user_ids.join(', ')
        : (s.owner_user_id ?? '-');
      return `
      <tr>
        <td>${idx + 1}</td>
        <td>${ns.toolbox.escapeHtml(s.system_code || '-')}</td>
        <td>${ns.toolbox.escapeHtml(s.name || '-')}</td>
        <td>${ns.toolbox.escapeHtml(s.host_address || '-')}</td>
        <td>${ns.toolbox.escapeHtml(envLabel(s.env))}</td>
        <td>${ns.toolbox.escapeHtml(ownerText)}</td>
        <td>${renderLogConfigs(s.log_configs)}</td>
        <td>${s.is_active === false ? '停用' : '启用'}</td>
        <td>
          <button class="table-action-btn" type="button" data-system-action="edit" data-system-id="${ns.toolbox.escapeHtml(s.id)}">编辑</button>
          <button class="table-action-btn" type="button" data-system-action="toggle" data-system-id="${ns.toolbox.escapeHtml(s.id)}" data-system-active="${s.is_active === false ? 'true' : 'false'}">${s.is_active === false ? '启用' : '停用'}</button>
          <button class="table-action-btn danger" type="button" data-system-action="delete" data-system-id="${ns.toolbox.escapeHtml(s.id)}">删除</button>
        </td>
      </tr>
    `}).join('');
    if (summary) summary.textContent = message || `匹配 ${list.length} 条`;
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="9">暂无匹配系统</td></tr>';
  }

  async function findSystems() {
    const d = await ns.api.request(`/api/v1/admin/systems?${buildSystemQuery()}`, { headers: ns.api.headers() });
    const items = Array.isArray(d.items) ? d.items : [];
    renderSystemResultBoard(items, `匹配 ${d.total ?? items.length} 条`);
    return items;
  }

  function findSystem(systemId) {
    return (ns.state.latestSystems || []).find((item) => String(item.id) === String(systemId));
  }

  function openEditSystem(systemId) {
    const item = findSystem(systemId);
    if (!item) return;
    ns.modals?.openEditSystemModal?.(item);
  }

  async function setSystemActive(systemId, isActive) {
    const d = await ns.api.request(`/api/v1/admin/systems/${systemId}/active?is_active=${isActive ? 'true' : 'false'}`, {
      method: 'PATCH',
      headers: ns.api.headers(),
    });
    await findSystems();
    return d;
  }

  async function deleteSystem(systemId) {
    if (!window.confirm('确认删除该系统？当前会执行停用，数据保留用于历史追溯。')) return null;
    const d = await ns.api.request(`/api/v1/admin/systems/${systemId}`, {
      method: 'DELETE',
      headers: ns.api.headers(),
    });
    await findSystems();
    return d;
  }

  document.getElementById('systemListTbody')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-system-action]');
    if (!btn) return;
    if (btn.dataset.systemAction === 'edit') openEditSystem(btn.dataset.systemId);
    if (btn.dataset.systemAction === 'toggle') setSystemActive(btn.dataset.systemId, btn.dataset.systemActive === 'true').catch((e) => {
      const el = document.getElementById('systemListSummary');
      if (el) el.textContent = e.message;
    });
    if (btn.dataset.systemAction === 'delete') deleteSystem(btn.dataset.systemId).catch((e) => {
      const el = document.getElementById('systemListSummary');
      if (el) el.textContent = e.message;
    });
  });

  ns.systems = { buildSystemQuery, renderSystemResultBoard, findSystems, findSystem, openEditSystem, setSystemActive, deleteSystem };
})(window.AegisAdmin);
