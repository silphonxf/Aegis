window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  ns.state = ns.state || {};

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
    ns.state.latestAssets = items || [];
    const rows = (items || []).map((item, idx) => `
      <tr>
        <td>${idx + 1}</td>
        <td>${ns.toolbox.escapeHtml(item.asset_code || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.name || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.category || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.system_id ?? '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.room_id ?? '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.location || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.ip_address || '-')}</td>
        <td>${ns.toolbox.escapeHtml(item.status || '-')}</td>
        <td>
          <button class="table-action-btn" type="button" data-asset-action="edit" data-asset-id="${ns.toolbox.escapeHtml(item.id)}">编辑</button>
          <button class="table-action-btn danger" type="button" data-asset-action="retire" data-asset-id="${ns.toolbox.escapeHtml(item.id)}">停用</button>
        </td>
      </tr>
    `).join('');
    tbody.innerHTML = rows || '<tr><td colspan="10">暂无资产数据</td></tr>';
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

  async function updateAsset(assetId, payload) {
    const d = await ns.api.request(`/api/v1/admin/assets/${assetId}`, {
      method: 'PUT',
      headers: ns.api.headers(),
      body: JSON.stringify(payload),
    });
    const el = document.getElementById('assetResult');
    if (el) el.textContent = `更新成功\n${JSON.stringify(d, null, 2)}`;
    await listAssets();
    return d;
  }

  async function retireAsset(assetId) {
    if (!window.confirm('确认停用该资产？')) return null;
    const d = await ns.api.request(`/api/v1/admin/assets/${assetId}`, {
      method: 'DELETE',
      headers: ns.api.headers(),
    });
    const el = document.getElementById('assetResult');
    if (el) el.textContent = `已停用\n${JSON.stringify(d, null, 2)}`;
    await listAssets();
    return d;
  }

  function findAsset(assetId) {
    return (ns.state.latestAssets || []).find((item) => String(item.id) === String(assetId));
  }

  function openEditAsset(assetId) {
    const item = findAsset(assetId);
    if (!item) return;
    ns.modals?.openEditAssetModal?.(item);
  }

  function clearFilters() {
    ['assetFilterKeyword', 'assetFilterSystemId', 'assetFilterCategory', 'assetFilterStatus'].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.value = '';
    });
  }

  document.getElementById('assetListTbody')?.addEventListener('click', (event) => {
    const btn = event.target.closest('[data-asset-action]');
    if (!btn) return;
    const assetId = btn.dataset.assetId;
    if (btn.dataset.assetAction === 'edit') openEditAsset(assetId);
    if (btn.dataset.assetAction === 'retire') retireAsset(assetId).catch((e) => {
      const el = document.getElementById('assetResult');
      if (el) el.textContent = e.message;
    });
  });

  ns.assets = { buildAssetQuery, renderAssetTable, listAssets, createAsset, updateAsset, retireAsset, clearFilters };
})(window.AegisAdmin);
