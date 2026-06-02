window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function renderSystemResultBoard(items, message = '') {
    const tbody = document.getElementById('systemListTbody');
    const summary = document.getElementById('systemListSummary');
    const rows = (items || []).map((s, idx) => {
      const ownerText = Array.isArray(s.owner_user_ids) && s.owner_user_ids.length
        ? s.owner_user_ids.join(', ')
        : (s.owner_user_id ?? '-');
      return `
      <tr>
        <td>${idx + 1}</td>
        <td>${ns.toolbox.escapeHtml(s.system_code || '-')}</td>
        <td>${ns.toolbox.escapeHtml(s.name || '-')}</td>
        <td>${ns.toolbox.escapeHtml(s.env === 'prod' ? '生产' : s.env === 'test' ? '测试' : s.env === 'dev' ? '开发' : (s.env || '-'))}</td>
        <td>${ns.toolbox.escapeHtml(ownerText)}</td>
        <td>${ns.toolbox.escapeHtml(s.check_frequency || '-')}</td>
      </tr>
    `}).join('');
    if (summary) summary.textContent = message || `匹配 ${items.length} 条`;
    if (tbody) tbody.innerHTML = rows || '<tr><td colspan="6">暂无匹配系统</td></tr>';
  }

  async function findSystems(keyword) {
    const d = await ns.api.request('/api/v1/admin/systems?page=1&size=200', { headers: ns.api.headers() });
    const items = Array.isArray(d.items) ? d.items : [];
    const filtered = keyword ? items.filter((s) => `${s.system_code || ''} ${s.name || ''}`.toLowerCase().includes(keyword.toLowerCase())) : items;
    renderSystemResultBoard(filtered, `匹配 ${filtered.length} 条`);
    return filtered;
  }

  ns.systems = { renderSystemResultBoard, findSystems };
})(window.AegisAdmin);
