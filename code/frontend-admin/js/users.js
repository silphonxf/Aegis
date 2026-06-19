window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function renderUserResultBoard(items, message = '') {
    const tbody = document.getElementById('userListTbody');
    const summary = document.getElementById('userListSummary');
    const rows = (items || []).map((u, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${ns.toolbox.escapeHtml(u.username || '-')}</td>
        <td>${u.role_code === 'super_admin' ? '超级管理员' : u.role_code === 'admin' ? '管理员' : '巡检员'}</td>
        <td>${ns.toolbox.escapeHtml(u.id ?? '-')}</td>
      </tr>
    `).join('');
    if (summary) summary.textContent = message || `匹配 ${items.length} 条`;
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="4">暂无匹配用户</td></tr>';
  }

  async function findUsers(keyword) {
    const d = await ns.api.request('/api/v1/admin/users?page=1&size=200', { headers: ns.api.headers() });
    const items = Array.isArray(d.items) ? d.items : [];
    ns.state.latestUsers = items;
    const filtered = keyword ? items.filter((u) => String(u.username || '').toLowerCase().includes(keyword.toLowerCase())) : items;
    renderUserResultBoard(filtered, `匹配 ${filtered.length} 条`);
    return filtered;
  }

  ns.users = { renderUserResultBoard, findUsers };
})(window.AegisAdmin);
