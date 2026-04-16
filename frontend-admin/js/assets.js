window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function buildAssetQuery() {
    const params = new URLSearchParams({ page: '1', size: '50' });
    const mappings = [
      ['assetFilterKeyword', 'keyword'],
      ['assetFilterSystemId', 'system_id'],
      ['assetFilterCategory', 'category'],
      ['assetFilterStatus', 'status'],
    ];
    mappings.forEach(([id, key]) => {
      const value = document.getElementById(id)?.value.trim();
      if (value) params.set(key, value);
    });
    return params.toString();
  }

  function renderAssetTable(items) {
    const tbody = document.getElementById('assetListTbody');
    if (!tbody) return;
    const rows = (items || []).map((item, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${ns.toolbox.escapeHtml(item.asset_code || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.name || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.category || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.system_id ?? '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.location || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.status || '-')}</td>
      </tr>
    `).join('');
    tbody.innerHTML = rows || '<tr><td colspan="7">暂无资产数据</td></tr>';
  }

  async function listAssets() {
    const d = await ns.api.request(`/api/v1/admin/assets?${buildAssetQuery()}`, { headers: ns.api.headers() });
    renderAssetTable(d.items || []);
    const summary = document.getElementById('assetListSummary');
    if (summary) summary.textContent = `当前共 ${d.total ?? d.items?.length ?? 0} 条资产记录`;
    const el = document.getElementById('assetListResult');
    if (el) el.textContent = JSON.stringify(d, null, 2);
    return d;
  }

  async function createAsset(payload) {
    const d = await ns.api.request('/api/v1/admin/assets', { method: 'POST', headers: ns.api.headers(), body: JSON.stringify(payload) });
    const el = document.getElementById('assetResult');
    if (el) el.textContent = `创建成功\n${JSON.stringify(d, null, 2)}`;
    await listAssets();
    return d;
  }

  function clearFilters() {
    ['assetFilterKeyword', 'assetFilterSystemId', 'assetFilterCategory', 'assetFilterStatus'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
  }

  ns.assets = { buildAssetQuery, renderAssetTable, listAssets, createAsset, clearFilters };
})(window.AegisAdmin);
