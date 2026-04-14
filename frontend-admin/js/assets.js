window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  function buildAssetQuery() {
    const params = new URLSearchParams({ page: '1', size: '50' });
    const mappings = [
      ['assetFilterSystemId', 'system_id'],
      ['assetFilterCategory', 'category'],
      ['assetFilterStatus', 'status'],
      ['assetFilterKeyword', 'keyword'],
    ];
    mappings.forEach(([id, key]) => {
      const value = document.getElementById(id)?.value.trim();
      if (value) params.set(key, value);
    });
    return params.toString();
  }

  async function listAssets() {
    const d = await ns.api.request(`/api/v1/admin/assets?${buildAssetQuery()}`, { headers: ns.api.headers() });
    const el = document.getElementById('assetListResult');
    if (el) el.textContent = `共 ${d.total ?? d.items?.length ?? 0} 条\n${JSON.stringify(d, null, 2)}`;
    return d;
  }

  async function createAsset(payload) {
    const d = await ns.api.request('/api/v1/admin/assets', { method: 'POST', headers: ns.api.headers(), body: JSON.stringify(payload) });
    const el = document.getElementById('assetResult');
    if (el) el.textContent = `创建成功\n${JSON.stringify(d, null, 2)}`;
    return d;
  }

  ns.assets = { buildAssetQuery, listAssets, createAsset };
})(window.AegisAdmin);
