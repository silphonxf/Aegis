window.AegisAdmin = window.AegisAdmin || {};

(function (ns) {
  async function fillSelect(selectId, path, mapLabel, includeEmpty = true) {
    const el = document.getElementById(selectId);
    if (!el) return [];
    const items = await ns.api.loadOptions(path);
    const options = [];
    if (includeEmpty) options.push('<option value="">请选择</option>');
    items.forEach((item) => {
      options.push(`<option value="${ns.toolbox.escapeHtml(item.id)}">${ns.toolbox.escapeHtml(mapLabel(item))}</option>`);
    });
    el.innerHTML = options.join('');
    return items;
  }

  async function hydrateAdminSelectors() {
    await Promise.all([
      fillSelect('modalAssetSystemId', '/api/v1/admin/systems?page=1&size=200', (item) => `${item.system_code} / ${item.name}`),
      fillSelect('modalAssetRoomId', '/api/v1/admin/rooms', (item) => `${item.room_code} / ${item.room_name}`),
    ]).catch(() => {});
  }

  ns.sharedData = { fillSelect, hydrateAdminSelectors };
})(window.AegisAdmin);
